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
"$PY" -m eval.run_all --n-boot "${N_BOOT:-1000}"

echo "== contracts/ untouched (git only)"
if git rev-parse --is-inside-work-tree > /dev/null 2>&1; then
  base="${BASE_REF:-origin/main}"
  if git rev-parse --verify --quiet "$base" > /dev/null; then
    if ! git diff --quiet "$base" -- contracts/; then
      echo "contracts/ differs from $base - requires an explicit instruction (CLAUDE.md rule 1)" >&2
      exit 1
    fi
  fi
fi

echo "OK"
