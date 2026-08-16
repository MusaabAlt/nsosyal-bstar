# NSosyal B* — offline demo

One local screen. Paste Turkish text, see all three systems side by side plus
the review-layer routing decision. Runs with networking disabled.

```
python demo/app.py --assets /path/to/demo_assets
# -> http://127.0.0.1:8000/
```

---

## Checkpoint sizes and where they must live

The demo needs **885.9 MB** on local disk. Nothing is fetched at runtime.

```
demo_assets/                              885.9 MB total
├── checkpoints/
│   ├── raw.pt                            442.5 MB   BERTurk raw  (= 01_baseline_berturk/best.pt)
│   └── 1a1b_d.pt                         442.5 MB   +1a+1b+D     (= 03_defense/1a1b_d/best.pt)
├── tokenizer/
│   ├── tokenizer.json                      0.8 MB   fast-tokenizer vocabulary
│   ├── tokenizer_config.json              ~1 KB
│   └── config.json                        ~1 KB     BertConfig, num_labels=2
├── lexicon/karaliste.txt                  ~9 KB     the frozen 695-entry lexicon
├── operating_point.json                   ~1 KB     the phase-04 threshold, 0.6632
└── manifest.json                          ~2 KB     sha256 of every file above
```

The two checkpoints are the whole story: 442.5 MB each is a 110M-parameter
BERTurk in fp32 (110M × 4 bytes ≈ 440 MB). They are *not* in git — they are
gitignored, and on Colab they live at

```
MyDrive/nsosyal-bstar/checkpoints/01_baseline_berturk/best.pt
MyDrive/nsosyal-bstar/checkpoints/03_defense/1a1b_d/best.pt
```

`--assets` can point anywhere; the default is `<repo>/demo_assets`.

## Building the bundle (once, with network)

The tokenizer vocabulary and model config come from the HF Hub. That fetch is
allowed in exactly one place and never at demo time:

```
python demo/build_assets.py \
    --raw_ckpt     <drive>/checkpoints/01_baseline_berturk/best.pt \
    --defense_ckpt <drive>/checkpoints/03_defense/1a1b_d/best.pt \
    --out demo_assets
```

Then copy the whole `demo_assets/` directory to the demo machine. After that the
machine can stay offline forever.

## Why not Gradio or Streamlit

Both fetch web fonts and telemetry from CDNs when the page loads, so a "runs
offline" demo built on either fails the moment it is genuinely disconnected —
and fails at the worst time, in front of an audience, as a blank page. This is
`http.server` from the standard library with inline CSS and inline JS. No
dependency, no external asset, offline by construction.

Belt and braces on top of that: `HF_HUB_OFFLINE=1` and `TRANSFORMERS_OFFLINE=1`
are set **before** `transformers` is imported, every `from_pretrained` call
passes `local_files_only=True` against a local directory, and the model is built
with `from_config` (structure only) before the trained weights are loaded from
the checkpoint. A missing asset aborts at startup with the list of what is
missing, rather than hanging on a socket.

## What the screen shows

| column | meaning |
|---|---|
| keyword filter | the frozen Day 1 lexicon, agglutination-aware root matching. Decision comes from `lexicon.hit_root` itself; the matched roots are shown for display only |
| BERTurk raw | the shipped model, with P(OFF) |
| BERTurk +1a+1b+D | the defense variant, with P(OFF) |
| review layer | AUTO-RESOLVE or DEFER, at confidence threshold **0.6632** |

That threshold was selected on the dev calibration half in phase 04 and never
re-derived. On the official test set it achieved 90.2% coverage at 0.8485
macro-F1 / 8.52% error, concentrating errors 3.59× into the deferred queue.

## The pre-loaded examples

Eight real dev rows from the phase 02 failure analysis, carrying the function
tag we assigned them, four from each error direction:

* **implicit offense, no profanity token** — gold OFF, raw BERTurk said NOT
* **profanity token present, no offensive act** — gold NOT, raw BERTurk said OFF

They are chosen to make the project's central claim visible rather than to
flatter it. The `NONDIR` example is deferred to review — the layer catches it.
The `IMPLICIT` examples are auto-resolved, wrongly, which is precisely the phase
04 finding that confidence-based deferral is error-selective but **slice-blind**:
it does not preferentially route the lexicon-free failures to a human. The demo
shows the limitation as readily as the capability.

Gold labels follow Çöltekin's annotation convention, adopted as given. Nothing
was relabelled.

## Robustness

`python demo/app.py --assets <dir> --selftest` classifies the hostile set and
exits without starting a server. Verified with **all outbound sockets blocked**
(a `sitecustomize` shim that raises on any non-loopback `connect`/`getaddrinfo`),
on two consecutive cold starts, for both the selftest and the live server:

| input | behaviour |
|---|---|
| empty / whitespace only | rejected with a message, no model call |
| emoji only | classified, flagged that confidence is not meaningful |
| English | classified normally |
| 100k characters | truncated to 4,000 chars, then to 128 wordpiece tokens |
| control characters (`\x00`, `\x07`, `\x1b`) | stripped, noted; tabs and newlines kept |
| `<script>alert(1)</script>` | HTML-escaped in the response |
| malformed JSON POST | error message returned, server stays up |

`allow_reuse_address` is set so a second cold start is not blocked by a socket in
`TIME_WAIT` from the first.

## Known limitations

* **CPU works but is slow to load.** ~885 MB of fp32 weights take a while to
  read from disk; on CUDA it is a few seconds. The demo picks CUDA if available.
* **No batching, no persistence.** One request at a time, nothing is stored.
* **Not a product.** Legibility only — no styling work, no auth, binds to
  `127.0.0.1` by design.
