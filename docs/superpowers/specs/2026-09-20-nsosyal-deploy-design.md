# nsosyal-bstar — production deployment design

**Date:** 2026-09-20
**Target:** `tevekkul` (Hetzner CX-class, single-node Docker Swarm, nbg1)
**Public URL:** `https://nsosyal.daqqiq.com`
**Goal:** deploy the full stack with real BERTurk inference, and redeploy automatically on every commit to `master`.

---

## 1. Context

This repo was built for an offline LAN demo. `docs/FULLSTACK.md` states the intended
runtime is one laptop serving ~70 people on room Wi-Fi. Consequently the repo contains
**no Dockerfiles, no CI workflows, no reverse-proxy config, and no deploy scripts** —
all deployment artifacts in this design are new.

Three properties of the existing code shape the design:

1. **The Go binary serves everything.** The Vue SPA is built into `backend/web/dist` and
   embedded via `go:embed` (`backend/web/embed.go`). There is no separate static site, and
   the frontend needs no API base URL because it is same-origin.
2. **Go supervises the Python inference service**, but only when `python.enabled: true`.
   With `enabled: false` the supervisor runs in monitor-only mode
   (`backend/internal/supervisor/python.go:16`, `Manage=false`) and Go simply calls
   `inference.url`. **Verified** — this is what makes a two-container split possible with no
   code changes.
3. **Config is env-overridable.** Env names derive from the YAML path with an `NSOSYAL_`
   prefix (`backend/internal/config/config.go:9`), so every value below is set by env var,
   and no file in the upstream repo is patched.

### Constraints carried into the design

| Constraint | Source | Consequence |
|---|---|---|
| Model weights not in git (~1GB, sha256-pinned) | `AI/artifacts/MANIFEST.md` | Weights delivered out-of-band to a volume |
| No auth anywhere in the app | `backend/internal/http/router.go` | Access control must live in front of the origin |
| `python.command` is a Windows path | `backend/config.yaml` | Irrelevant once `enabled: false`; documented so it isn't re-introduced |
| Rate limits tuned for ~70 LAN users | `backend/config.yaml` | Tightened for public exposure |
| Host RAM 3819MB, ~1175MB committed | measured 2026-09-20 | Hard caps + reservations, larger swap |

---

## 2. Architecture

```
Cloudflare (proxied, Access policy on nsosyal.daqqiq.com)
        │
        ▼
  Traefik (existing traefik stack, certresolver "le")
        │  router: Host(`nsosyal.daqqiq.com`) → nsosyal_app:8080
        ▼
  ┌─────────────────────────────────────────────┐
  │ nsosyal_app        Go + embedded Vue SPA    │  image ~30MB   cap 256MB
  │   NSOSYAL_PYTHON_ENABLED=false              │
  │   NSOSYAL_INFERENCE_URL=http://infer:8001      │
  └───────────────┬─────────────────────────────┘
                  │ overlay net: nsosyal_internal
                  ▼
  ┌─────────────────────────────────────────────┐
  │ nsosyal_infer      FastAPI + torch + BERTurk│  image ~2.5GB  cap 2048MB
  │   uvicorn --host 0.0.0.0 --port 8001        │
  │   /models ← volume nsosyal_models (weights) │
  └─────────────────────────────────────────────┘

  ┌─────────────────────────────────────────────┐
  │ nsosyal-data_postgres   postgres:18-alpine  │  cap 384MB
  │   volume nsosyal_pgdata                     │
  └─────────────────────────────────────────────┘
```

Two stacks, mirroring the existing `sahhil-alsayed` / `sahhil-alsayed-data` convention:
`nsosyal` (app + infer) and `nsosyal-data` (postgres).

### Why two containers rather than one

The upstream design runs one process tree. Splitting costs an overlay network hop and
gains three things that matter here: independent memory caps (torch cannot be capped
separately inside a monolith), a 30MB Go image that redeploys in seconds instead of a
3GB one, and a torch image that only rebuilds when Python dependencies change rather
than on every frontend tweak.

### Why `--host 0.0.0.0` for uvicorn

`backend/config.yaml` passes `--host 127.0.0.1` because Go spawns the service as a local
child. In a separate container the Go process must reach it across the overlay network,
so the inference container's own CMD binds `0.0.0.0`. The service is not published to the
host and is reachable only on the internal overlay network.

---

## 3. Memory budget

Measured on 2026-09-20: 3819MB total, 1175MB committed, 356MB truly free, 2644MB
available after reclaiming page cache.

| Service | Limit | Reservation |
|---|---|---|
| `nsosyal_infer` | 2048MB | 1024MB |
| `nsosyal_app` | 256MB | 64MB |
| `nsosyal-data_postgres` | 384MB | 128MB |
| **new total** | **2688MB** | **1216MB** |

The limit total intentionally exceeds comfortable headroom; limits are ceilings, not
allocations. Steady state for BERTurk FP32 inference is expected around 1.5GB.

Three mitigations, in order of importance:

1. **Add reservations to the existing sahhil services.** Swarm schedules against
   reservations. Without them, the new workload competes with the storefront on equal
   terms. This is the single most important step and touches the existing stack.
2. **Grow swap from 2048MB to 6144MB.** Currently allocated and entirely unused; disk has
   22GB free. Gives torch's cold pages somewhere to go that isn't Postgres's page cache.
3. **Build off-box** (see §6) so `pip install torch` never runs on the host.

**Known residual risk:** torch at its upper range plus page-cache eviction will slow
Postgres reads for both sahhil and workbench before anything OOMs. Degradation, not
outage, and harder to attribute. If inference RSS settles above ~1.8GB, the correct
response is upgrading the Hetzner plan rather than tuning further — the user has
accepted this tradeoff.

---

## 4. Model artifact delivery

Weights are gitignored and pinned by sha256 in `AI/artifacts/MANIFEST.md`. They are
delivered once, by hand, and persist in a Docker volume across deploys.

```
docker volume create nsosyal_models
# from the Mac, over Tailscale:
scp berturk_epoch1.pt root@100.75.227.23:/var/lib/docker/volumes/nsosyal_models/_data/
scp -r tokenizer/      root@100.75.227.23:/var/lib/docker/volumes/nsosyal_models/_data/
# verify against the manifest before first start:
sha256sum /var/lib/docker/volumes/nsosyal_models/_data/berturk_epoch1.pt
```

Consumed via `NSOSYAL_M3_CHECKPOINT=/models/berturk_epoch1.pt` and
`NSOSYAL_M3_TOKENIZER=/models/tokenizer`.

`AI/modules/m3_encoder/module.py` raises `FileNotFoundError` when these are absent and
the pipeline is written to degrade gracefully without m3 (`AI/CLAUDE.md` rule 7). The
deploy must therefore **assert** the model loaded rather than trusting a green container —
see §8.

Out of scope: the `diagnosis/` demo asset bundle (~886MB). `diagnosis/` is the research
track and is not part of the deployed surface.

---

## 5. Ingress, TLS, and access control

**DNS.** One proxied A record, `nsosyal.daqqiq.com` → the host's public IPv4
(`46.224.235.180`). Proxied matters: the host firewall admits only Cloudflare ranges on
443 (`infra/host/allow-cloudflare-web.sh` in the sahhil repo follows the same pattern).

**TLS.** Traefik's existing `le` certresolver issues per-router. The static
`entrypoints.websecure.http.tls.domains[0]` entry is specific to `sahhil.com` and is
left untouched; the new router carries its own `certresolver=le` label.

**Access.** A Cloudflare Access policy on `nsosyal.daqqiq.com`, allowlisting specific
emails. This is the entire authentication story — the application has none. It also
prevents anonymous internet traffic from reaching a torch endpoint, which is a memory
safety property, not only a security one.

**Rate limiting.** `NSOSYAL_RATE_LIMIT_ANALYZE_PER_SECOND` is tuned for a trusted LAN.
Tightened for public exposure as defence in depth behind Access.

---

## 6. CI/CD

Trigger: push to `master`. Two GitHub-hosted build jobs, then a deploy job.

```
push to master
   ├─ build-app    ubuntu-latest   node build → go build → ghcr.io/musaabalt/nsosyal-app:<sha>
   ├─ build-infer  ubuntu-latest   pip install torch → ghcr.io/musaabalt/nsosyal-infer:<sha>
   └─ deploy       ubuntu-latest   tailscale up (ephemeral) → ssh → docker service update
```

**Builds run on GitHub's runners, not on the box.** `pip install torch` unpacks several
GB; doing that on a 4GB host while the storefront serves customers is the most likely way
to cause an incident. The host only ever pulls finished images.

**Deploy reaches the box over Tailscale**, using `tailscale/github-action` with an
ephemeral, tagged auth key, then SSH. This deliberately avoids registering a third
self-hosted runner: the existing two cost 269MB of RSS between them, and a third would
consume headroom this design is already fighting for.

The auth key is scoped to a dedicated ACL tag permitting SSH to `tevekkul` only, and
ephemeral nodes deregister themselves after the run. Repo secrets are not exposed to
fork PRs, so a public repo is not a leak vector for pushes to `master`.

**Rollback:** images are tagged by commit SHA, so rollback is
`docker service update --image ghcr.io/musaabalt/nsosyal-app:<previous-sha>`.

### Build details

Both Dockerfiles build from the **repo root**, not from their subdirectory: the frontend's
production script writes across directory boundaries.

*`nsosyal-app` (multi-stage):*
- Stage 1 `node:22-alpine` — `npm ci` in `frontend/` (lockfile is `package-lock.json`;
  there is no pnpm or yarn lockfile despite pnpm being the house default elsewhere), then
  `npm run build:backend`, which emits to `../backend/web/dist` and runs
  `check-offline.mjs` to assert the bundle references no external hosts.
- Stage 2 `golang:1.27-alpine` — `go build ./cmd/server` with `backend/web/dist` present,
  so `go:embed` picks it up. `go.mod` requires **Go 1.27.0**; an older toolchain fails.
- Stage 3 `alpine` — the static binary plus `config.yaml`.

*`nsosyal-infer`:*
- `python:3.11-slim` — `AI/requirements.txt` plus `AI/modules/m3_encoder/requirements.txt`
  (torch 2.11.0, transformers 5.15.0). Install the **CPU-only** torch wheel index; the
  default wheel pulls CUDA libraries worth several GB that this host will never use.
- CMD: `uvicorn serving.app:create_app --factory --host 0.0.0.0 --port 8001`, workdir `AI/`.
- Weights are **not** in the image; they arrive on the `nsosyal_models` volume (§4).

**Alternative considered:** a third self-hosted runner, matching the existing convention
for `sahhil-alsayed` and `workbench`. Rejected on memory grounds alone; it is the
simpler option and worth revisiting if the host is upgraded.

---

## 7. Database and migrations

New `postgres:18-alpine` in a `nsosyal-data` stack with its own `nsosyal_pgdata` volume —
matching the per-project isolation the box already uses, rather than sharing the sahhil
instance. `NSOSYAL_DATABASE_URL` points at it over the overlay network.

Migrations run automatically at startup via goose (`database.migrate_on_start: true`), so
no separate migration step is needed. `cmd/migrate` exists if manual control is ever
wanted.

**Backups are out of scope for this iteration** and explicitly not wired into
`/srv/backup-db.sh`. This is demo data, not business records. Stated so the omission is a
decision rather than an oversight.

---

## 8. Verification

A deploy is only successful if all of the following hold. The deploy job asserts them and
fails loudly otherwise:

1. `docker service ls` shows `nsosyal_app`, `nsosyal_infer`, `nsosyal-data_postgres` at
   full replicas.
2. `GET /health` on the inference service returns 200 **and reports the m3 encoder as
   loaded** — a healthy container with a missing checkpoint is the failure mode this
   design is most exposed to, because the pipeline degrades silently by design.
3. `curl -H "Host: nsosyal.daqqiq.com" https://127.0.0.1/` returns 200 at the origin.
4. The public URL returns a Cloudflare Access challenge rather than the application.
5. **The existing stacks are unharmed**: sahhil and workbench services still at full
   replicas, and `sahhil.com` still returns 200. Every deploy checks this, because the
   memory budget is shared.

---

## 9. Risks

| Risk | Likelihood | Mitigation |
|---|---|---|
| torch RSS exceeds budget, degrades sahhil | Medium | Caps, reservations, 6GB swap; upgrade plan if sustained |
| Model loads but m3 silently absent | Medium | Verification asserts m3 loaded, not just HTTP 200 |
| First deploy pulls 2.5GB image on a live box | Low | Pull is disk+network, not RAM; off-peak first run |
| Public exposure of an app with no auth | Low | Cloudflare Access is mandatory, not optional |
| Upstream pushes break the build | Medium | Deploys are per-SHA and roll back in one command |

## 10. Out of scope

- `diagnosis/` research track and its ~886MB asset bundle
- Backups of nsosyal's database
- Retraining or producing model weights
- Modifying upstream application code — this design is env-vars and new files only
- The deferred host maintenance window (see `/root/PENDING-MAINTENANCE.md` on the box)
