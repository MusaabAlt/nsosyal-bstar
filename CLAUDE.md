# CLAUDE.md

Project-wide notes for agents. `AI/CLAUDE.md` governs the `AI/` tree and takes
precedence there — read it before touching modules.

## What this project is

NSosyal: Turkish offensive-content detection. Three parts — `diagnosis/` (the
research track), `AI/` (a 7-module detection pipeline), and `backend/` (Go) +
`frontend/` (Vue 3) serving a live moderation panel. Docs and comments are
Turkish; keep new user-facing strings Turkish.

**It was designed for an offline LAN demo** — `docs/FULLSTACK.md` says one laptop,
~70 people on room Wi-Fi. That assumption is visible everywhere: no
authentication, rate limits tuned for a trusted room, a Windows path in
`backend/config.yaml`, and localhost-only binding. Anything deployed beyond a
laptop has to account for it.

## The trap that matters most: this system degrades silently

The pipeline is deliberately written to keep running when a module cannot load
(`AI/CLAUDE.md` rule 7). A missing or mismatched model artifact does **not**
crash anything. You get a healthy container, `/health` returning 200, and a
detector that detects nothing.

**`degraded_modules` in the `/health` payload is the real signal. HTTP status is not.**

Never write a check that greps the whole `/health` body for a module name — the
`capabilities` array (`AI/serving/capabilities.py`) always contains
`m3_encoder`, so such a check matches even when m3 is perfectly healthy. Parse
`degraded_modules` specifically. This exact bug shipped once into
`infra/verify-deploy.sh` and made the check unable to ever pass.

Expected entries in `degraded_modules` today:
- `m3_encoder` — its artifacts are gitignored and often absent (see below).
- `m5_sarcasm` — an unimplemented stub (`stub = True`), not a fault.

## Model artifacts are not in git

The repo calls them **artifacts**, listed with sha256 in `AI/artifacts/MANIFEST.md`.
The one that matters at runtime is `m3-berturk-pytorch-fp32-epoch1`
(`artifacts/m3_encoder/berturk_epoch1.pt`) plus `m3-berturk-tokenizer`
(`artifacts/m3_encoder/tokenizer/`). Both originate from the `diagnosis/` study,
not from `AI/`. `m3_encoder` is the only trained model in the pipeline — m1 is a
wordlist, m2 character tables, m6 gazetteers — so without it nothing is scored.

Modules verify their own sha256 and fail loudly on a mismatch, so wrong-but-plausible
files are caught. Missing files are not an error, they are a degradation.

## Configuration

Env names derive from the YAML path in `backend/config.yaml` with an `NSOSYAL_`
prefix (`backend/internal/config/config.go:9`). Precedence: env > `.env` > yaml >
defaults.

**The inference URL lives under `inference:`, not `python:`.** The override is
`NSOSYAL_INFERENCE_URL`. `NSOSYAL_PYTHON_URL` matches no key and is **silently
ignored** — the app then calls the default `127.0.0.1:8001` against itself and
every analyze request fails while `/api/health` stays green. This mistake has
been made once already.

`NSOSYAL_PYTHON_ENABLED=false` puts the Go supervisor in monitor-only mode
(`backend/internal/supervisor/python.go`), so it calls the inference URL instead
of spawning a local Python process. That is what allows the app and the inference
service to run as separate containers with no code changes.

## Building

Package manager is **npm** (`package-lock.json` only — no pnpm/yarn lockfile).
Go 1.27.0 is required by `backend/go.mod`.

The Vue SPA is built into `backend/web/dist` and embedded with `//go:embed all:dist`,
so the Go binary serves both `/api/*` and the UI — there is no separate static
site and the frontend needs no API base URL.

Each module owns its own `requirements.txt` (`AI/CLAUDE.md` rule 6); the core
stays stdlib + pyyaml. A runtime Python environment needs **five** files:
`AI/requirements.txt`, `AI/serving/requirements.txt`, and
`AI/modules/{m1_lexicon,m2_deobf,m3_encoder}/requirements.txt`. Omitting m1
(terlik) or m2 (zeyrek) silently degrades those modules. `AI/training/*` is not
runtime.

Install CPU torch with `--index-url https://download.pytorch.org/whl/cpu`, not
`--extra-index-url`, or pip resolves the multi-GB CUDA wheel from PyPI.

## Deployment

Live at `https://nsosyal.daqqiq.com`, publicly reachable with no authentication —
a deliberate choice for tournament use, not an oversight. Full runbook:
**`infra/README.md`**. Read it before any operational change.

Two things to know before running anything against the host:

1. **The host also runs a customer-facing storefront** (`sahhil-alsayed`) and
   `workbench`. Never `docker stack rm`, never prune, never restart a service you
   did not deploy. `infra/verify-deploy.sh` checks the storefront is unharmed for
   exactly this reason — run it after every change.
2. **It is memory-constrained** (3819MB total, shared three ways). Always pass a
   memory cap to `docker build`. The app image needs `--memory=2g` because
   `vue-tsc` exhausts the default heap at ~510MB and aborts with exit 134; the
   torch image is fine at `--memory=1g`. Counterintuitive, but measured.

There is no CI/CD, and it cannot be added without repo admin plus a `workflow`-scoped
token. Images build on the host; updates are manual.
