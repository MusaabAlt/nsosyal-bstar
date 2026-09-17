# Baseline working tree — inventory for a reproducible starting point

Verification Gate 0, 2026-09-17. Nothing in this inventory was modified, discarded, staged or
committed by the auditor. Hashes are SHA-256 of the file as it sits on disk (`sha256sum`, Git Bash);
"HEAD" hashes are of `git show HEAD:<path>` and are truncated to 16 hex characters for reading.

## 1. Repository state

| item | value |
|---|---|
| branch | `audit/m1-m6` |
| HEAD | `f063ddf` — 2026-09-16 17:39:41 +0300, "m4 stage 1b measured against stage 1: keep stage 1; m4 adds a C1–C5 note" |
| `master`, `origin/master` | both `f063ddf` (branch has no commits of its own; `git log master..HEAD` is empty) |
| remote | `origin` → `https://github.com/MusaabAlt/nsosyal-bstar.git` |
| stash | empty |
| `AI/contracts/` vs `master` | identical (`git diff --stat master -- AI/contracts/` empty) |
| `core.autocrlf` | `true` (machine setting; the project requires LF via `AI/.gitattributes`, HANDOVER §4.6) |
| tracked under `AI/eval/results/` | `.gitkeep`, `m4_stage1b.json` only (all other result files git-ignored) |

## 2. Environment the previous numbers were produced in

| item | value |
|---|---|
| Python (`AI/.venv`) | 3.14.0 |
| terlik | 0.1.0 (`pip show`) |
| torch | 2.11.0+cpu |
| transformers | 5.15.0 |
| m3 artifact | `AI/artifacts/m3_encoder/berturk_epoch1.pt` present, 442,544,192 bytes, sha256 `43a20d5525aff0a5…` (matches the constant in `m3/module.py`); tokenizer dir present; both git-ignored |
| frozen slice | `AI/eval/frozen/study_slice_dev.json` present, tracked, created 2026-09-15 |
| `diagnosis/data/`, `diagnosis/results/01_baseline_berturk/dev_predictions.csv` | not in git; needed by `eval.m4_stage1b` and `eval.m1_lexicon_dev_labels`; not checked here |

## 3. Modified tracked files

| path | on-disk sha256 | HEAD sha256 | diff | classification | basis |
|---|---|---|---|---|---|
| `AI/docs/HANDOVER.md` | `708bc451cd14ff28…` | `2d8bae3a911134da…` | +4 −3: §2 Contracts bullet now "owned by Musaab"; new m1 "implemented" bullet; m1 removed from the Stubbed list; §4.1 owner Osama → Musaab | **INTENTIONAL_PROJECT_CHANGE** | matches the m1 implementation commit `f9159be` cited in `AI/README.md`; consistent with `docs/team/README.md`. Note: it still lists m3 among the stubs (Q10) — the change is intentional but incomplete |
| `AI/eval/traps/traps.jsonl` | `1d853acf0fc1b7218…` | `3f7d10d5253e89f1…` | +10: traps 024–033 (inflected / uppercase collision words; five with m0 `must: [DOTLESS_I]`) | **INTENTIONAL_PROJECT_CHANGE** | format matches `eval/README.md`; the m1 unit test `test_collision_traps_never_fire` and the local m0 / m1 result files (`traps.n = 33`) were produced against it. Uncommitted, so the committed m2–m6 results (`n = 23`) and `pipeline.json` (`n_traps = 23`) are from a different trap set (Q22) |
| `AI/modules/m1_lexicon/fixtures/cases.jsonl` | `8acde84054c11f6ed…` | `479459dd3a44dc56…` | +6: `m1-long-{clean,adv}-{280,1000,5000}` | **INTENTIONAL_PROJECT_CHANGE** | HANDOVER #44 requires clean and adversarial items per latency band; the local `m1_lexicon.json` result uses them (`clean.n_items = 5`, bands at 280 / 1000 / 5000 present) |
| `AI/modules/m1_lexicon/spec.md` | `f95f5a8461445006…` | `bae001973a731654…` | +9: §1 gains the "two lexicon files, never merged" table (terlik runtime vs karaliste frozen slice) | **INTENTIONAL_PROJECT_CHANGE** | mirrors the `_README` of the frozen slice and the derived file; consistent with protocol §1 / §6. Process note: spec changes are proposed by the module owner and approved by Musaab (HANDOVER #64); m1's owner is Musaab, so approval is the owner's own |
| `AI/modules/m2_deobf/spec.md` | `8b4907d602b378cdc…` | `3c56284082e73a2b…` | 1 line: a `---` horizontal rule became `--` | **ACCIDENTAL_EDIT** (auditor's reading; not reverted) | no other change in the file; a two-dash line is not Markdown; no commit message or doc mentions it |

## 4. Untracked files

| path | sha256 / size | classification | basis |
|---|---|---|---|
| `AI/protocols/m1_lexicon_dev_labels_protocol.md` | `18bd5cfb1de4fc33…`, 6,678 B, 2026-09-16 21:44 | **INTENTIONAL_PROJECT_CHANGE** (pre-registration, not yet committed) | referenced by the HANDOVER m1 bullet and by the derived file header; its sha256 equals the `protocol.sha256` recorded inside the derived file, so the derived file was generated from exactly this text |
| `AI/eval/m1_lexicon_dev_labels.py` | `8d6736fd99096d59…`, 14,925 B, 2026-09-16 21:45 | **INTENTIONAL_PROJECT_CHANGE** (generator script) | named as `generator.script` in the derived file; the derived file lists it under `uncommitted_changes`, so it was untracked at generation time too. Whether the on-disk script is byte-identical to the one that generated the file cannot be verified (no script hash is recorded) — **UNKNOWN** on that one point |
| `AI/eval/derived/m1_lexicon_dev_seed42.json` | `3c57f6e6b184f6837…`, 1,141,466 B, 2026-09-16 21:46 (created_at `2026-09-16T18:46:15+00:00`) | **INTENTIONAL_PROJECT_CHANGE**, sequencing pending | header: `protocol.commit: null`, `committed_and_unchanged: false`, `git_head f063ddf`, `modules_in_order [m0, m2, m6, m1]`, counts `n 4764 / lexicon_hit 459 / lexicon_hit_norm 0 / rows_with_collision 2356`. The protocol's own rule says the file is committed only after the protocol, in a later commit (Q24). Regenerable by design (`_README`) |
| `AI/docs/audit/MODULE_MAP.md` | `7a50ce1a92ed35c2…` | **AUDIT_OUTPUT** | previous session, 2026-09-17 17:42 |
| `AI/docs/audit/MODULE_CONTRACTS.md` | `8a639decaf5b1eb3…` | **AUDIT_OUTPUT** | previous session, 17:45 |
| `AI/docs/audit/PIPELINE_FLOW.md` | `68dc74d07e15a167…` | **AUDIT_OUTPUT** | previous session, 17:47 |
| `AI/docs/audit/OPEN_QUESTIONS.md` | `2d7700b0c09baaf2…` | **AUDIT_OUTPUT** | previous session, 17:48 |
| `AI/docs/audit/ISSUE_TRIAGE.md` | — | **AUDIT_OUTPUT** | this session (Gate 0) |
| `AI/docs/audit/TEST_SYSTEM_AUDIT.md` | — | **AUDIT_OUTPUT** | this session |
| `AI/docs/audit/TEST_ORACLE_MAP.md` | — | **AUDIT_OUTPUT** | this session |
| `AI/docs/audit/VERIFICATION_PLAN.md` | — | **AUDIT_OUTPUT** | this session |
| `AI/docs/audit/BASELINE_WORKTREE.md` | — | **AUDIT_OUTPUT** | this file |

## 5. Git-ignored files that affect what a run observes

Not part of the tree, but part of the baseline's *behaviour*:

| path | state | effect if absent |
|---|---|---|
| `AI/artifacts/m3_encoder/berturk_epoch1.pt` + `tokenizer/` | present, hash verified | m3 `failed` on every request; 5 of 6 m3 behaviour tests skip; `contract_example --check` fails; every `check.sh` run fails at the example gate |
| `AI/eval/results/*.json` (m0, m1, m2, m3, m4, m5, m6, pipeline) | present, produced 2026-09-16 from two different trap-file states and repeat counts (m0: 5 repeats / 33 traps; m1: 20 / 33; m2–m6: 200 / 23; pipeline: 200 / 23 traps, 85 texts) | none on tests; they are not a reference for any comparison (Q22) |
| `AI/.venv/` | Python 3.14.0 | tests need pyyaml, terlik, torch, transformers |

## 6. What a reproducible baseline requires (decisions for the owner, not actions taken)

1. Commit the four intentional tracked changes (HANDOVER, traps, m1 fixture, m1 spec) as the
   project's own change, or set them aside; the m1 unit suite and any eval number depend on the
   trap file and fixture that are chosen.
2. Revert or confirm the `--` line in `AI/modules/m2_deobf/spec.md` (owner: Mohammed for the
   spec, Musaab approves).
3. Commit the protocol and the generator script; then either commit the derived file as is
   (recording that it was generated at `f063ddf` before the protocol was committed) or regenerate
   it after the protocol lands, per the protocol's §7 rule. The auditor does not pick.
4. Decide whether `AI/docs/audit/` is committed on this branch (it is documentation of the audit
   and changes nothing) or kept out of the tree.
5. After 1–4, run `python -m eval.run_all` once on the resulting commit and record HEAD, trap
   count and repeats with the result files; that run is the reference for every later comparison
   (`VERIFICATION_PLAN.md` G0-G).
6. Verify line endings of every file touched in 1–3 are LF before committing (`core.autocrlf`
   is `true` on this machine).

Until 1–5 are done, "the suite passes" and every number in `AI/eval/results/` describe a state
that no commit reproduces.
