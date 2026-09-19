## Analysis (written after inspecting the module traces; evidence per case in `failure_review.json`)

### A. The M3 artifact

The exact Rule-v4 artifact (`m3-berturk-multihead-a-rule-v4-20260918-163728`, weights sha256
`dc7fe306…0b76`) is **not on this machine**. No `weights.pt` of any multi-head artifact exists locally (searched
`C:\Users\HP` and `C:\Projects`; only Rule-v3 *metadata* copies exist). `NSOSYAL_M3_ARTIFACT` is unset, so the
runtime loads its default: the **binary-only baseline** `m3-berturk-pytorch-fp32-epoch1`
(`AI/artifacts/m3_encoder/berturk_epoch1.pt`, sha256 `43a20d55…d4ca`). It has no A head: no M3 content score
exists in any trace. Every M3-dependent scenario is **BLOCKED (BLOCKED_ARTIFACT_NOT_LOCAL)**; nothing was
substituted, downloaded, trained or reconfigured. The baseline's binary probability is recorded in every trace
for information only.

Configuration caveat for installing Rule-v4 later (ARTIFACT/CONFIGURATION, not a failure of this run):
`decision/thresholds.yaml` `binary_offensive` (0.320188) is documented as valid **only** for the baseline
artifact; no binary threshold has been derived for the Rule-v3 or Rule-v4 candidates, and the Rule-v4 handoff
(§6) leaves the Rule-v4 A operating policy to an owner decision (A-OP-1 is scoped to Rule-v3). Pointing
`NSOSYAL_M3_ARTIFACT` at Rule-v4 would therefore apply an underived binary threshold.

### B. Failures by root cause (nothing was fixed)

| root cause | classification | cases | effect |
|---|---|---|---|
| **m6 vowel-harmony check** (`m6_target._harmonic`): rounded stem vowel allows only 2 suffix vowels, so plural + case chains are rejected (`solcuların`, `Türklerin`, `Kürtlerin`, `Rusların`) | PRODUCTION_BUG (DEMO-09: DEMO_BLOCKER) | A-T04, DEMO-09, M6-GRP-001, -002, -003 | group target lost: group-aimed profanity becomes A1 instead of A3 (block -> review/nudge). `Solcular`, `Kadınların` work. |
| **cross-channel collision guard**: m2 PHONETIC `q->k` turns `aq` / `a.q` into the Rule-v4 R8 clean form `ak`; m1's normalized-channel SUBSTRING_COLLISION shares the original span and (guards are per module, not per channel) suppresses the genuine raw-channel `amk` hit | PRODUCTION_BUG | V4-GEN-020, -021, -022, A-AQ-001 | `aq`, `a.q`, `A.q` never fire family A in the full pipeline (`amq`, `amk`, `mk` do). The existing suite checks these lists on m1 alone / on pre-guard `_matches`, so it cannot see this. |
| **m6 gazetteer over-match**: `karası` read as `kar` (snow) + `a` + `sı` | PRODUCTION_BUG (low) | TAX-B1-yuzkarasi-spaced_standard | a spurious non_human target raises NON_HUMAN_TARGET and suppresses a genuine B1 (`yüz karası`). The homograph `kara` (black) does the same (B1-NH-003, limitation). |
| terlik 0.1.0 suffix table has no `-nin/-nın` after a vowel and no k->ğ mutation | KNOWN_LIMITATION | B1-011 | `ibnenin`, `gerizekalının`, `salağın` are not matched. |
| my expectation was wrong | EXPECTATION_WRONG -> EXPECTATION_INVALID | TAX-A-amci-plain/-punct/-upper/-targeted, M6-023 | terlik attributes `amcı` to root `am` (same route A, content correct); `kitap` in M6-023's sentence is a legitimate non_human stem. |

No crash. One handled module exception: a lone surrogate (`abc\ud800def`, M0-MALFORMED-001) makes the BERTurk
tokenizer raise `TypeError` inside m3; the pipeline isolates it (m3 `failed`, result DEGRADED, verdict `review`),
exactly the documented fail-closed behaviour.

### C. Demo-visible behaviour that is by design (not failures, but must be explained or avoided)

1. **`clean` is never returned.** m5 is a declared stub, every result is DEGRADED, and a would-be-clean verdict
   becomes `review` (fail closed). Every clean demo message will show `review` with the explanation
   "Karar verilemedi, içerik temiz sayılmadı…".
2. **Untargeted profanity can look milder than a clean message.** `A1`'s configured action is `nudge`; the
   degraded rule only upgrades *clean* verdicts. When the binary score does not fire, `OROSPU`, `sg`,
   `S İ K T İ R`, `s1kt1r`… end at `nudge` (46 scenarios), while a clean sentence ends at `review`.
3. **The binary score is not guard-suppressible** (open policy Q2). `Bu film tam bir bok.` (DEMO-15): m1's A1 is
   suppressed by NON_HUMAN_TARGET, yet the baseline binary head (0.977) still sends it to `review`.
4. **Target type is resolved per post.** Any non-human noun anywhere in a post (`hava`, `maç`, `film`, `yağmur`)
   makes m1 raise NON_HUMAN_TARGET on all its hits unless a second-person/@mention/vocative target is present:
   `Hava çok soğuk, aptal herif.` (B1 suppressed), `Siktir, yine yağmur yağıyor` (A1 suppressed), and QUOTE-001
   (suppressed through `Maçta`, i.e. the right outcome for the wrong reason).
5. **Any e-mail address is doxing (B4 -> escalate)**, including the writer's own (M6-DOX-005): the declared
   operating point (confidence 0.60 >= B4 threshold 0.50).
6. **With the baseline binary head (not Rule-v4)** — informational only: it fired on 24 of 215 SUPPORTED
   no-content scenarios (mostly bare NONE-route words: `meme`, `fuhuş`, `kaşar`, `dingil`, `kerhane`; plus the
   guarded non-human insults of item 3; 1 of the 70 CLEAN sentences: `Bokser köpekleri çok enerjik.`, 0.421) and
   did not fire on 240 of 738 SUPPORTED offensive scenarios (bare single words such as `sg`, `oç`, `hassiktir`;
   the lexical codes still fired).

### C2. Performance and demo practicality

Cold start 31–42 s over three runs (import + BERTurk load + terlik + zeyrek; faster when the OS file cache is
warm), first inference ≈ 0.2–0.3 s, warm DEMO_CRITICAL texts p50 ≈ 130 ms / p95 ≈ 215–250 ms. m3's CPU forward
pass is ≈ 97 % of request time (m1 ≈ 3 ms, every other module < 1 ms). During the 1,295-request batch a few
isolated multi-second stalls occurred (max 8.1 s on the 15-character `Sen puşt musun?`); re-timed alone, the same
inputs take 105–600 ms, so they are machine stalls, not input cost. Practical for a live demo if the pipeline is
loaded once before the session starts.

### D. Final decision

1. **Does the frozen system run end-to-end without backend/frontend?** Yes. `pipeline.run.Pipeline` was built and
   called directly from Python with `AI/.venv`; all scenarios completed, each with a verdict and a Turkish
   explanation; 0 crashes.
2. **Is the exact Rule-v4 artifact being used?** **No.** The runtime loads the binary-only baseline
   `m3-berturk-pytorch-fp32-epoch1` (sha256 `43a20d5525aff0a57c0bda2be559a5acdf84848cf7cbed844f0c8f5f3024d4ca`).
   Rule-v4 is not on this machine; the runtime would load it only via `NSOSYAL_M3_ARTIFACT=<artifact dir>`
   (weights.pt, heads.json, config.json, tokenizer.json, tokenizer_config.json, sha256.txt), a directory
   currently on Drive at `/content/drive/MyDrive/nsosyal-train/runs/m3_multihead/rule-v4-20260918-163728/artifact/m3-berturk-multihead-a-rule-v4-20260918-163728/`.
3. **Any crashes?** No (one module-level exception on a lone surrogate, isolated and fail-closed).
4. **Any PRODUCTION_BUG failures?** Yes: 9 FAIL cases from 3 root causes (m6 harmony check; cross-channel `aq`
   suppression; m6 `kar` over-match). None was fixed.
5. **Any DEMO_BLOCKER failures?** One: DEMO-09 (`Solcuların hepsi piç.`), caused by the m6 harmony bug. The tested
   wording DEMO-09B (`Solcular hep piç.` -> group -> A3 -> block) avoids it without any code change.
6. **Reliable enough for a jury demo** (every SUPPORTED case of the family passed, except where noted): clean
   text / no false A-B on suspicious substrings (70/70 CLEAN); the whole lexical taxonomy — B1 (all 100 roots
   detected; 488/489 scenarios, the one miss being the m6 `kar` bug), B2 (35/35), B3 (45/45), NONE-route
   vocabulary producing no code (56/56); explicit A profanity with suffixes, punctuation, hashtags,
   brackets, spaced and repeated letters (except `aq`); Rule-v4 precision (all clean forms, homonym guards
   `mal`/`domuz`, `allık`); supported obfuscation (leet, spacing, punctuation split, masking, repeats, phonetic,
   accents, de-ASCII) and Unicode safety (homoglyphs, zero-width, combining marks, fullwidth, styled letters);
   individual targeting (`sen`, `@mention`, vocatives) and A1/A2 assignment; B4 doxing on validated identifiers;
   edge inputs.
7. **Must NOT be claimed:** sarcasm detection (M5 NOT_IMPLEMENTED); implicit / stereotype / incitement detection
   C1-C5 (M4 stage 2 not built — M4 is stage 1 only); anything about the Rule-v4 A head or learned semantic
   detection (Rule-v4 not loaded; the baseline has no A head; the binary threshold is derived for the baseline
   only); A4 sacred profanity and B5 sexual aggression (no producer); threats or curses outside the 7 + 9
   lexical roots (B head untrained); quotation / reported speech / meta-discussion / negation / self-directed
   handling (guard codes without a producer); named-person targeting without `@` (no NER); reliable group
   targeting of inflected group nouns (bug above); `aq` detection (bug above); vowel-drop, abbreviation,
   word-merge, char-drop, dialect and emoji obfuscation (declared unhandled); English profanity; a `clean`
   verdict; and any accuracy figure from this scenario suite.
8. **Live demo cases** (all PASS on the frozen runtime unless stated): DEMO-01 `Siktir git lan!` (A2),
   DEMO-02 `s.i.k.t.i.r git` (obfuscated A1), DEMO-03 `Canım çok sıkıldı, bu akşam sıkı bir antrenman yapacağım.`
   (no false positive), DEMO-04 `Bakanın mal varlığı açıklandı.` (HOMONYM), DEMO-05 `Sen tam bir gerizekalısın.`
   (B1, not A), DEMO-06 `Seni öldürücem.` (B2 -> escalate), DEMO-07 `Allah belanı versin!` (B3),
   DEMO-08 `@ali siktir git` (individual -> A2), DEMO-09B `Solcular hep piç.` (group -> A3 -> block),
   DEMO-11 `Yarın saat 10'da toplantımız var, görüşürüz.` (no content; explain the `review` from the m5 stub),
   DEMO-14 doxing address (B4 -> escalate), DEMO-15 `Bu film tam bir bok.` (NON_HUMAN_TARGET; explain the binary
   `review`), plus two honest limitations: DEMO-12 sarcasm (NOT_IMPLEMENTED) and DEMO-13 `Sen tam bir srfszsn`
   (vowel drop, KNOWN_LIMITATION). DEMO-10 (semantic, no lexical cue) is BLOCKED for Rule-v4; on the current
   runtime only the baseline binary head flags it (0.739), and it may be shown only as the baseline model.
