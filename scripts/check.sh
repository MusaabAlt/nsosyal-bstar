#!/usr/bin/env bash
# Pre-merge check. Run from anywhere: bash scripts/check.sh
set -euo pipefail

cd "$(dirname "$0")/.."
PY="${PYTHON:-python}"

echo "== unit + architecture tests"
"$PY" -m unittest discover -p "test_*.py"

echo "== pipeline smoke"
"$PY" -m pipeline.run "Bu bir test cumlesi" --compact > /dev/null

echo "== per-module eval (traps, CIs, latency)"
"$PY" -m eval.run_all --n-boot "${N_BOOT:-1000}" --latency-repeats "${LATENCY_REPEATS:-200}"

echo "== contract example current"
# The frozen example is regenerated deterministically (ADR-003 amendment); if the
# config or a module version changed without regenerating it, it is stale.
if ! "$PY" -m pipeline.contract_example --check; then
  echo "FAIL: a contract example in contracts/fixtures/ is not current - regenerate with" >&2
  echo "      python -m pipeline.contract_example --write (explicit instruction required, contracts/ is frozen)" >&2
  exit 1
fi

echo "== contracts/ untouched"
# Never skipped silently: without a base to compare against, this check cannot
# prove anything, so it fails and says how to make it runnable.
if ! git rev-parse --is-inside-work-tree > /dev/null 2>&1; then
  echo "FAIL: not a git work tree - cannot verify contracts/ is unchanged (CLAUDE.md rule 1)" >&2
  exit 1
fi
base="${BASE_REF:-origin/main}"
if ! git rev-parse --verify --quiet "$base^{commit}" > /dev/null; then
  echo "FAIL: base ref '$base' not found - cannot verify contracts/ is unchanged." >&2
  echo "      Fetch it (git fetch origin main) or set BASE_REF=<commit> explicitly." >&2
  exit 1
fi
if ! git diff --quiet "$base" -- contracts/; then
  echo "FAIL: contracts/ differs from $base - requires an explicit instruction and an ADR (CLAUDE.md rule 1)" >&2
  git diff --stat "$base" -- contracts/ >&2
  exit 1
fi

echo "OK"
