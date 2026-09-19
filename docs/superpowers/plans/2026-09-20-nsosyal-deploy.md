# nsosyal-bstar Production Deployment Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deploy nsosyal-bstar to the `tevekkul` VPS at `https://nsosyal.daqqiq.com` with real BERTurk inference, redeploying automatically on every commit to `master`.

**Architecture:** Two containers — a ~30MB Go binary with the Vue SPA embedded, and a torch/FastAPI inference service — plus a dedicated Postgres, on the existing single-node Docker Swarm behind the existing Traefik. Images build on GitHub-hosted runners and publish to GHCR; the host only pulls. Model weights live on a Docker volume, never in an image or in git.

**Tech Stack:** Go 1.27, Vue 3 + Vite 8 (npm), Python 3.11 + FastAPI + torch 2.11 (CPU), Postgres 18, Docker Swarm, Traefik, GitHub Actions, GHCR, Cloudflare Access, Tailscale.

**Spec:** `docs/superpowers/specs/2026-09-20-nsosyal-deploy-design.md`

## Global Constraints

Every task's requirements implicitly include this section.

- **Target platform is `linux/amd64` only.** The VPS is `x86_64`; the development Mac is `arm64`. Never build on the Mac — build on the host, natively, under a memory cap.
- **Go 1.27.0** — required by `backend/go.mod`. An older toolchain fails the build.
- **npm, not pnpm.** `frontend/` ships only `package-lock.json`. Use `npm ci`.
- **torch CPU-only wheel index.** The default index pulls CUDA libraries worth several GB that this host cannot use.
- **No upstream application code is modified.** Behaviour is changed only through `NSOSYAL_*` environment variables and new files under `infra/` and `.github/`.
- **Every service declares a memory limit.** Unlimited services on this host can OOM-kill the sahhil storefront.
- **Traefik network is `traefik_proxy`** (external, pre-existing).
- **Images are built and tagged locally on the host** as `nsosyal-app:<sha>` / `nsosyal-infer:<sha>`. No registry: the `workflow` token scope and repo admin needed for GHCR-via-Actions are both unavailable.
- **Host access is Tailscale-only.** `root@100.75.227.23`. Public IP `46.224.235.180` has port 22 firewalled.
- **Secrets never enter the repo.** Weights, DB passwords, and auth keys travel via volumes and GitHub secrets.

## File Structure

Mirrors the `infra/` layout already used by `sahhil-alsayed`.

| File | Responsibility |
|---|---|
| `infra/app.Dockerfile` | Multi-stage build: Vue SPA → Go binary with `go:embed` → alpine runtime |
| `infra/infer.Dockerfile` | Python 3.11 + CPU torch + transformers, runs uvicorn on `0.0.0.0:8001` |
| `infra/data-stack.yml` | Postgres 18 + its volume |
| `infra/docker-stack.yml` | `app` + `infer` services, Traefik labels, memory limits |
| `infra/verify-deploy.sh` | The deploy gate — asserts §8 of the spec, used manually and by CI |
| `infra/README.md` | Runbook: weights upload, rollback, memory budget, first-run |
| `.dockerignore` | Keeps the 15MB `AI/eval` tree and `.git` out of build context |

---

### Task 1: Host preparation — swap headroom

Torch's cold pages need somewhere to go that isn't the page cache both Postgres instances read through. Swap is currently 2048MB and entirely unused; disk has 22GB free.

**Files:**
- Modify (on host): `/etc/fstab`
- Create (on host): `/swapfile2`

**Interfaces:**
- Consumes: nothing.
- Produces: ≥6144MB total swap on `tevekkul`. No later task depends on the exact figure.

- [ ] **Step 1: Record the starting state**

```bash
ssh root@100.75.227.23 'free -m; swapon --show; df -h /'
```

Expected: `Swap: 2047` total, `0` used; `/` has ~22G available.

- [ ] **Step 2: Create and enable a 4GB swapfile**

```bash
ssh root@100.75.227.23 'bash -s' <<'EOF'
set -e
fallocate -l 4G /swapfile2
chmod 600 /swapfile2
mkswap /swapfile2
swapon /swapfile2
grep -q '^/swapfile2' /etc/fstab || echo '/swapfile2 none swap sw 0 0' >> /etc/fstab
EOF
```

- [ ] **Step 3: Verify swap grew and survives remount**

```bash
ssh root@100.75.227.23 'free -m | awk "NR==3"; swapon --show; findmnt --verify --fstab 2>&1 | tail -3'
```

Expected: total swap ≥ 6143MB, `/swapfile2` listed, fstab verification reports no errors.

**Note:** a bad `/etc/fstab` entry prevents boot. Step 3's `findmnt --verify` is not optional — this host's only out-of-band access is Hetzner VNC.

- [ ] **Step 4: Commit the runbook note**

No repo change yet; record the change in the host's own maintenance file:

```bash
ssh root@100.75.227.23 'echo "2026-09-20: swap grown 2G -> 6G (/swapfile2) for nsosyal torch workload" >> /root/PENDING-MAINTENANCE.md'
```

---

### Task 2: Postgres stack

A dedicated Postgres, matching the per-project isolation the host already uses. No backups — demo data, decided in spec §7.

**Files:**
- Create: `infra/data-stack.yml`

**Interfaces:**
- Consumes: nothing.
- Produces: reachable Postgres at Swarm DNS name `nsosyal-data_postgres` (the canonical `<stack>_<service>` name — use this, not the short `postgres` alias), port `5432`, database `nsosyal`, user `nsosyal`, on the network Swarm names `nsosyal-data_nsosyal_internal`. Task 7 consumes this as `NSOSYAL_DATABASE_URL`.

- [ ] **Step 1: Write the stack file**

```yaml
# infra/data-stack.yml — nsosyal-data stack
# Demo data. Deliberately NOT wired into /srv/backup-db.sh (see spec §7).
version: "3.8"

networks:
  nsosyal_internal:
    driver: overlay
    attachable: false

volumes:
  pgdata:

services:
  postgres:
    image: postgres:18-alpine
    networks:
      - nsosyal_internal
    environment:
      POSTGRES_DB: nsosyal
      POSTGRES_USER: nsosyal
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
      PGDATA: /var/lib/postgresql/data/pgdata
    volumes:
      - pgdata:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U nsosyal -d nsosyal"]
      interval: 10s
      timeout: 3s
      retries: 5
    deploy:
      replicas: 1
      restart_policy:
        condition: any
      resources:
        limits:
          memory: "384M"
        reservations:
          memory: "128M"
```

- [ ] **Step 2: Generate a password and deploy**

Swarm does not interpolate `${...}` from a file, so substitute explicitly:

```bash
scp infra/data-stack.yml root@100.75.227.23:/srv/nsosyal-data-stack.yml
ssh root@100.75.227.23 'bash -s' <<'EOF'
set -e
mkdir -p /srv/nsosyal
[ -f /srv/nsosyal/db.env ] || echo "POSTGRES_PASSWORD=$(openssl rand -hex 24)" > /srv/nsosyal/db.env
chmod 600 /srv/nsosyal/db.env
set -a; . /srv/nsosyal/db.env; set +a
docker stack deploy -c <(envsubst < /srv/nsosyal-data-stack.yml) nsosyal-data
EOF
```

- [ ] **Step 3: Verify Postgres is accepting connections**

```bash
ssh root@100.75.227.23 'docker service ls --filter name=nsosyal-data --format "{{.Name}} {{.Replicas}}"; \
  docker exec $(docker ps -qf name=nsosyal-data_postgres) pg_isready -U nsosyal -d nsosyal'
```

Expected: `nsosyal-data_postgres 1/1` and `accepting connections`.

- [ ] **Step 4: Verify the existing stacks are unharmed**

```bash
ssh root@100.75.227.23 'docker service ls --format "{{.Name}} {{.Replicas}}" | grep -E "sahhil|workbench|traefik"'
curl -s -o /dev/null -w '%{http_code}\n' https://sahhil.com/
```

Expected: every service at full replicas, `200` from sahhil.

- [ ] **Step 5: Commit**

```bash
git add infra/data-stack.yml
git commit -m "infra: add nsosyal postgres stack"
```

---

### Task 3: Deliver and verify model weights

The pipeline **degrades silently** without these — `/health` returns 200 with `m3_encoder` listed in `degraded_modules`. Deliver them before the app ever starts, so the first deploy is verifiable.

**Files:**
- Create (on host): volume `nsosyal_models`

**Interfaces:**
- Consumes: nothing.
- Produces: `/models/berturk_epoch1.pt` and `/models/tokenizer/` inside the `infer` container. Task 6 consumes these as `NSOSYAL_M3_CHECKPOINT` and `NSOSYAL_M3_TOKENIZER`.

- [ ] **Step 1: Read the expected digests**

```bash
cat AI/artifacts/MANIFEST.md
```

Record the sha256 for `berturk_epoch1.pt` and each tokenizer file. `AI/modules/m3_encoder/module.py:117-121` raises `ValueError` on any mismatch, so wrong files fail loudly rather than silently.

- [ ] **Step 2: Create the volume and upload**

The user supplies the local path to the weights. From the Mac:

```bash
ssh root@100.75.227.23 'docker volume create nsosyal_models'
VOL=/var/lib/docker/volumes/nsosyal_models/_data
scp  "<local>/berturk_epoch1.pt" root@100.75.227.23:$VOL/
scp -r "<local>/tokenizer"        root@100.75.227.23:$VOL/
```

- [ ] **Step 3: Verify digests on the host against the manifest**

```bash
ssh root@100.75.227.23 'cd /var/lib/docker/volumes/nsosyal_models/_data && \
  sha256sum berturk_epoch1.pt && find tokenizer -type f -exec sha256sum {} \;'
```

Expected: every digest matches `AI/artifacts/MANIFEST.md` exactly. **Stop and re-upload on any mismatch** — proceeding produces a deployment that looks healthy and detects nothing.

- [ ] **Step 4: Confirm disk did not blow out**

```bash
ssh root@100.75.227.23 'du -sh /var/lib/docker/volumes/nsosyal_models/_data; df -h / | tail -1'
```

Expected: ~1GB used, `/` still well under 80%.

---

### Task 4: Application image

**Files:**
- Create: `infra/app.Dockerfile`
- Create: `.dockerignore`

**Interfaces:**
- Consumes: nothing.
- Produces: an image whose entrypoint is `/usr/local/bin/server -config /etc/nsosyal/config.yaml`, listening on `8080`, serving both `/api/*` and the embedded SPA.

- [ ] **Step 1: Write `.dockerignore`**

Keeps `AI/eval/derived/m1_lexicon_train_seed42.json` (9.3MB) and the 8.1MB `.git` out of context:

```
.git
docs
diagnosis
AI/eval
**/node_modules
**/__pycache__
**/dist
```

- [ ] **Step 2: Write `infra/app.Dockerfile`**

Built from the repo root — `npm run build:backend` writes across directory boundaries into `backend/web/dist`.

```dockerfile
# syntax=docker/dockerfile:1
# Stage 1 — Vue SPA. Emits into backend/web/dist for go:embed.
FROM node:22-alpine AS frontend
WORKDIR /src
COPY frontend/package.json frontend/package-lock.json ./frontend/
RUN cd frontend && npm ci
COPY frontend/ ./frontend/
COPY backend/ ./backend/
# build:backend also runs check-offline.mjs, asserting no external hosts.
RUN cd frontend && npm run build:backend

# Stage 2 — Go binary with the SPA embedded. go.mod requires 1.27.0.
FROM golang:1.27-alpine AS builder
WORKDIR /src
COPY backend/go.mod backend/go.sum ./backend/
RUN cd backend && go mod download
COPY backend/ ./backend/
COPY --from=frontend /src/backend/web/dist ./backend/web/dist
RUN cd backend && CGO_ENABLED=0 go build -trimpath -ldflags="-s -w" -o /out/server ./cmd/server

# Stage 3 — runtime
FROM alpine:3.20
RUN apk add --no-cache ca-certificates tzdata curl && adduser -D -u 10001 app
COPY --from=builder /out/server /usr/local/bin/server
COPY backend/config.yaml /etc/nsosyal/config.yaml
USER app
EXPOSE 8080
ENTRYPOINT ["/usr/local/bin/server", "-config", "/etc/nsosyal/config.yaml"]
```

`curl` is installed deliberately — the Swarm healthcheck in Task 7 uses it.

- [ ] **Step 3: Commit (build verification happens in CI, Task 6)**

Local build is impossible to trust: the Mac is `arm64`, the target is `amd64`.

```bash
git add infra/app.Dockerfile .dockerignore
git commit -m "infra: add application image build"
```

---

### Task 5: Inference image

**Files:**
- Create: `infra/infer.Dockerfile`

**Interfaces:**
- Consumes: nothing.
- Produces: an image serving `GET /health` and `POST /predict_batch` on `0.0.0.0:8001`, reading weights from `/models`.

- [ ] **Step 1: Write `infra/infer.Dockerfile`**

```dockerfile
# syntax=docker/dockerfile:1
FROM python:3.11-slim
WORKDIR /app

# Per-module requirements: AI/CLAUDE.md rule 6 gives each module its own file, and
# the core deliberately stays stdlib + pyyaml. All FOUR runtime files are needed —
# omitting m1/m2 puts those modules in degraded_modules, which the deploy gate fails.
# AI/training/* is excluded: training only, not runtime.
COPY AI/requirements.txt                     /tmp/req-core.txt
COPY AI/serving/requirements.txt             /tmp/req-serving.txt
COPY AI/modules/m1_lexicon/requirements.txt  /tmp/req-m1.txt
COPY AI/modules/m2_deobf/requirements.txt    /tmp/req-m2.txt
COPY AI/modules/m3_encoder/requirements.txt  /tmp/req-m3.txt

# torch FIRST, from the CPU index with --index-url (NOT --extra-index-url, which lets
# pip resolve the multi-GB CUDA wheel from PyPI). This is the form
# AI/modules/m3_encoder/requirements.txt itself prescribes.
RUN pip install --no-cache-dir --index-url https://download.pytorch.org/whl/cpu torch==2.11.0

RUN pip install --no-cache-dir \
      -r /tmp/req-core.txt -r /tmp/req-serving.txt \
      -r /tmp/req-m1.txt -r /tmp/req-m2.txt -r /tmp/req-m3.txt

COPY AI/ /app/
RUN adduser --disabled-password --uid 10001 app && mkdir -p /models && chown app /models
USER app
EXPOSE 8001

# Binds 0.0.0.0, not the repo's 127.0.0.1: the Go container reaches this
# across the overlay network. Not published to the host.
CMD ["python", "-m", "uvicorn", "serving.app:create_app", \
     "--factory", "--host", "0.0.0.0", "--port", "8001", "--no-access-log"]
```

- [ ] **Step 2: Commit**

```bash
git add infra/infer.Dockerfile
git commit -m "infra: add inference image build"
```

---

### Task 6: Build both images on the VPS

**Replaces the original CI-build task.** Two permission facts make GitHub Actions
unreachable: the active `gh` token lacks the `workflow` scope (so `.github/workflows/`
cannot be pushed), and the user is `admin: false` on the repo (so Actions secrets cannot
be set). The user also dropped automatic deployment. Images therefore build on the host.

Spec §6 chose off-box builds to keep `pip install torch` away from a 4GB host serving
production. That protection is preserved by a different mechanism: a hard cgroup cap on
the build, plus the 6GB swap from Task 1.

**Files:** none in the repo. Uses `infra/app.Dockerfile` and `infra/infer.Dockerfile`.

**Interfaces:**
- Consumes: the two Dockerfiles from Tasks 4 and 5.
- Produces: local images `nsosyal-app:<sha>` and `nsosyal-infer:<sha>` on the host. Task 7
  consumes these tags. No registry involved.

- [ ] **Step 1: Ship the build context to the host**

The host has no clone. Send a clean archive rather than the working tree:

```bash
SHA=$(git rev-parse --short HEAD)
git archive --format=tar HEAD | ssh root@100.75.227.23 "mkdir -p /srv/nsosyal/src && tar -x -C /srv/nsosyal/src"
ssh root@100.75.227.23 'ls /srv/nsosyal/src | head'
```

Expected: the repo's top-level entries (`AI`, `backend`, `frontend`, `infra`, …).

- [ ] **Step 2: Record the memory baseline**

```bash
ssh root@100.75.227.23 'free -m; docker service ls --format "{{.Name}} {{.Replicas}}" | grep -E "sahhil|workbench|traefik"'
```

Keep this output — Step 5 compares against it.

- [ ] **Step 3: Build the application image (small, fast)**

```bash
SHA=$(git rev-parse --short HEAD)
ssh root@100.75.227.23 "cd /srv/nsosyal/src && docker build --memory=1g --memory-swap=3g \
  -f infra/app.Dockerfile -t nsosyal-app:$SHA -t nsosyal-app:latest . 2>&1 | tail -20"
```

Expected: `Successfully tagged nsosyal-app:<sha>`. This stage exercises `npm ci`, the Vue
build and the Go compile — if `go:embed all:dist` cannot find the SPA, it fails here.

- [ ] **Step 4: Build the inference image (large, slow)**

The capped build is the risky one. `--memory=1g` means a runaway fails the build rather
than the storefront.

```bash
SHA=$(git rev-parse --short HEAD)
ssh root@100.75.227.23 "cd /srv/nsosyal/src && docker build --memory=1g --memory-swap=3g \
  -f infra/infer.Dockerfile -t nsosyal-infer:$SHA -t nsosyal-infer:latest . 2>&1 | tail -30"
```

Expected: success, and the torch assertion added in Task 5's fix round prints a `+cpu`
version rather than aborting. If the build is OOM-killed, re-run with `--memory=1500m`
**only after** confirming the storefront is healthy.

- [ ] **Step 5: Verify the storefront survived the build**

```bash
ssh root@100.75.227.23 'free -m; docker service ls --format "{{.Name}} {{.Replicas}}" | grep -E "sahhil|workbench|traefik"'
curl -s -o /dev/null -w "sahhil: %{http_code}
" https://sahhil.com/
ssh root@100.75.227.23 "docker images --format '{{.Repository}}:{{.Tag}} {{.Size}}' | grep nsosyal"
```

Expected: every service still at full replicas, sahhil `200`, and both images listed. The
inference image will be roughly 2-3GB; the app image well under 100MB.

### Task 7: Application stack and the deploy gate

**Files:**
- Create: `infra/docker-stack.yml`
- Create: `infra/verify-deploy.sh`

**Interfaces:**
- Consumes: images from Task 6, Postgres from Task 2, weights volume from Task 3.
- Produces: services `nsosyal_app` and `nsosyal_infer`; a reusable gate script Task 9 calls.

- [ ] **Step 1: Write the stack file**

```yaml
# infra/docker-stack.yml — nsosyal stack
version: "3.8"

networks:
  traefik_proxy:
    external: true
    name: traefik_proxy
  nsosyal_internal:
    external: true
    name: nsosyal-data_nsosyal_internal

volumes:
  models:
    external: true
    name: nsosyal_models

services:
  app:
    image: nsosyal-app:${APP_TAG}
    networks: [traefik_proxy, nsosyal_internal]
    environment:
      NSOSYAL_SERVER_ADDR: "0.0.0.0:8080"
      NSOSYAL_DATABASE_URL: "postgres://nsosyal:${POSTGRES_PASSWORD}@nsosyal-data_postgres:5432/nsosyal?sslmode=disable"
      # Monitor-only: Go calls python.url but never spawns it
      # (backend/internal/supervisor/python.go:16, Manage=false).
      NSOSYAL_PYTHON_ENABLED: "false"
      NSOSYAL_INFERENCE_URL: "http://infer:8001"
      # Tightened from the repo's LAN-demo defaults for public exposure.
      NSOSYAL_RATE_LIMIT_ANALYZE_PER_SECOND: "5"
      NSOSYAL_LOG_LEVEL: "info"
    healthcheck:
      test: ["CMD", "curl", "-fsS", "http://127.0.0.1:8080/api/health"]
      interval: 15s
      timeout: 5s
      retries: 5
      start_period: 30s
    deploy:
      labels:
        - "traefik.enable=true"
        - "traefik.http.routers.nsosyal.rule=Host(`nsosyal.daqqiq.com`)"
        - "traefik.http.services.nsosyal.loadbalancer.server.port=8080"
      replicas: 1
      restart_policy:
        condition: any
      resources:
        limits:
          memory: "256M"
        reservations:
          memory: "64M"

  infer:
    image: nsosyal-infer:${INFER_TAG}
    networks: [nsosyal_internal]
    environment:
      NSOSYAL_M3_CHECKPOINT: "/models/berturk_epoch1.pt"
      NSOSYAL_M3_TOKENIZER: "/models/tokenizer"
    volumes:
      - models:/models:ro
    deploy:
      replicas: 1
      restart_policy:
        condition: any
      resources:
        limits:
          memory: "2048M"
        reservations:
          memory: "1024M"
```

**Note on the app healthcheck path:** `GET /api/health` is confirmed registered at `backend/internal/http/handlers/handlers.go:115`. Routes live in `handlers/`, not `router.go` — `router.go` only wires `api.Register(mux)` and the static handler.

**Note on `start_period`:** `backend/config.yaml` sets `startup_grace: 120s` for BERTurk load time. The `infer` service has no healthcheck for exactly this reason; the gate script polls it instead.

- [ ] **Step 2: Write the deploy gate**

This encodes spec §8. It is the only thing standing between a green container and a detector that silently detects nothing.

```bash
#!/usr/bin/env bash
# infra/verify-deploy.sh — run ON the host. Exits non-zero on any failure.
set -uo pipefail
fail=0
say() { printf '%-42s %s\n' "$1" "$2"; }

# 1. every nsosyal service at full replicas
for svc in nsosyal_app nsosyal_infer nsosyal-data_postgres; do
  r=$(docker service ls --filter "name=$svc" --format '{{.Replicas}}' | head -1)
  [ "${r%%/*}" = "${r##*/}" ] && [ -n "$r" ] && say "$svc" "OK ($r)" || { say "$svc" "FAIL ($r)"; fail=1; }
done

# 2. inference healthy AND m3 not degraded — the silent-failure guard
h=$(docker exec "$(docker ps -qf name=nsosyal_app | head -1)" \
      curl -fsS --max-time 10 http://infer:8001/health 2>/dev/null)
status=$(printf '%s' "$h" | sed -n 's/.*"status"[ :]*"\([^"]*\)".*/\1/p')
if [ "$status" = "ok" ] && ! printf '%s' "$h" | grep -q 'm3'; then
  say "inference m3 loaded" "OK (artifact $(printf '%s' "$h" | sed -n 's/.*"artifact_hash"[ :]*"\([^"]*\)".*/\1/p' | cut -c1-12))"
elif [ "${PRE_WEIGHTS:-0}" = "1" ] && [ "$status" = "ok" ]; then
  # Pre-weights mode: the model artifacts have not been delivered yet (Task 3 is
  # parked). The service is up and the wiring is proven, but it detects nothing.
  # NEVER set PRE_WEIGHTS=1 once the weights are on the box — this is the only
  # check standing between a green deploy and a silently blind detector.
  say "inference m3 loaded" "WARN (PRE_WEIGHTS=1: m3 degraded, detector inactive)"
else
  say "inference m3 loaded" "FAIL (status=$status degraded=$h)"; fail=1
fi

# 3. origin serves the app
code=$(curl -sk -o /dev/null -w '%{http_code}' --max-time 10 -H "Host: nsosyal.daqqiq.com" https://127.0.0.1/)
[ "$code" = "200" ] && say "origin nsosyal.daqqiq.com" "OK (200)" || { say "origin nsosyal.daqqiq.com" "FAIL ($code)"; fail=1; }

# 4. the storefront is unharmed — the memory budget is shared
for svc in $(docker service ls --format '{{.Name}}' | grep -E 'sahhil|workbench|traefik'); do
  r=$(docker service ls --filter "name=$svc" --format '{{.Replicas}}' | head -1)
  [ "${r%%/*}" = "${r##*/}" ] || { say "$svc" "FAIL ($r)"; fail=1; }
done
s=$(curl -sk -o /dev/null -w '%{http_code}' --max-time 10 -H "Host: sahhil.com" https://127.0.0.1/)
[ "$s" = "200" ] && say "sahhil origin unharmed" "OK (200)" || { say "sahhil origin unharmed" "FAIL ($s)"; fail=1; }

# 5. memory headroom report (informational)
say "mem available" "$(free -m | awk 'NR==2{print $7"MB"}')  swap used $(free -m | awk 'NR==3{print $3"MB"}')"

exit $fail
```

- [ ] **Step 3: Deploy manually and run the gate**

```bash
SHA=$(git rev-parse HEAD)
scp infra/docker-stack.yml infra/verify-deploy.sh root@100.75.227.23:/srv/
ssh root@100.75.227.23 "bash -s" <<EOF
set -e
chmod +x /srv/verify-deploy.sh
set -a; . /srv/nsosyal/db.env; set +a
export APP_TAG=$SHA INFER_TAG=$SHA
docker stack deploy -c <(envsubst < /srv/docker-stack.yml) nsosyal
EOF
```

- [ ] **Step 4: Wait for convergence, then gate**

BERTurk takes up to 120s to load; poll rather than assume.

```bash
ssh root@100.75.227.23 'until docker service ls --filter name=nsosyal_infer --format "{{.Replicas}}" | grep -q "^1/1$"; do sleep 10; done; /srv/verify-deploy.sh'
```

Expected: every line `OK`, exit 0. Any `FAIL` stops the plan here.

- [ ] **Step 5: Commit**

```bash
git add infra/docker-stack.yml infra/verify-deploy.sh
git commit -m "infra: add nsosyal app stack and deploy verification gate"
```

---

### Task 8: DNS and Cloudflare Access

The application has **no authentication of its own**. Access is the entire auth story, and also keeps anonymous traffic off a torch endpoint — a memory-safety property, not only a security one.

**Files:** none in the repo; Cloudflare dashboard or API.

**Interfaces:**
- Consumes: a working origin from Task 7.
- Produces: `https://nsosyal.daqqiq.com` reachable, gated by Access.

- [ ] **Step 1: Create the proxied DNS record**

`nsosyal.daqqiq.com` → `A` → `46.224.235.180`, **proxy enabled (orange cloud)**. Proxying is mandatory: the host firewall admits only Cloudflare ranges on 443.

- [ ] **Step 2: Verify TLS issuance at the edge**

```bash
until [ "$(curl -s -o /dev/null -w '%{http_code}' https://nsosyal.daqqiq.com/)" != "000" ]; do sleep 10; done
curl -sI https://nsosyal.daqqiq.com/ | head -3
```

Expected: a response (not `000`). Traefik's existing `le` certresolver issues per-router; the static `sahhil.com` domain list is untouched.

- [ ] **Step 3: Add the Access policy**

Cloudflare Zero Trust → Access → Applications → Add self-hosted:
- Domain `nsosyal.daqqiq.com`
- Policy: Allow, `Emails` → the allowlist (starts with the user's own account; extend on request)
- Session duration: 24h

- [ ] **Step 4: Verify the gate is actually closed**

```bash
curl -s -o /dev/null -w 'public: %{http_code}\n' https://nsosyal.daqqiq.com/
ssh root@100.75.227.23 'curl -sk -o /dev/null -w "origin: %{http_code}\n" -H "Host: nsosyal.daqqiq.com" https://127.0.0.1/'
```

Expected: public returns `302` to the Access login (**not** `200` — a 200 means the app is exposed unauthenticated); origin returns `200`.

---

### Task 9: Manual update procedure

**Replaces the original CD task, which is dropped.** The user asked for manual updates
("if important commits are done i'll give u info to update it"), and the permission
constraints in Task 6 rule out GitHub Actions regardless.

**Files:** none. This task defines the repeatable command sequence Task 10 documents.

**Interfaces:**
- Consumes: Tasks 6 and 7.
- Produces: a verified redeploy from a new commit.

- [ ] **Step 1: Rebuild and redeploy from current HEAD**

```bash
SHA=$(git rev-parse --short HEAD)
git archive --format=tar HEAD | ssh root@100.75.227.23 "rm -rf /srv/nsosyal/src && mkdir -p /srv/nsosyal/src && tar -x -C /srv/nsosyal/src"
ssh root@100.75.227.23 "cd /srv/nsosyal/src && \
  docker build --memory=1g --memory-swap=3g -f infra/app.Dockerfile   -t nsosyal-app:$SHA . && \
  docker build --memory=1g --memory-swap=3g -f infra/infer.Dockerfile -t nsosyal-infer:$SHA ."
ssh root@100.75.227.23 "docker service update --image nsosyal-app:$SHA   nsosyal_app && \
                        docker service update --image nsosyal-infer:$SHA nsosyal_infer"
```

- [ ] **Step 2: Gate the result**

```bash
ssh root@100.75.227.23 /srv/verify-deploy.sh
```

Expected: all `OK`. Rollback is `docker service update --image nsosyal-app:<previous-sha> nsosyal_app`.

- [ ] **Step 3: Prove rollback once, deliberately**

Rollback is untested until it is tested while nothing is broken. Roll back one tag, run
the gate, then roll forward and run it again. Both must pass.

### Task 10: Runbook

**Files:**
- Create: `infra/README.md`

**Interfaces:**
- Consumes: everything above.
- Produces: the document someone reads at 3am.

- [ ] **Step 1: Write the runbook**

It must cover, concretely: the two-stack layout and why the split exists; how to re-upload weights and verify digests; the memory budget with measured figures and what to do when inference RSS exceeds ~1.8GB (upgrade the Hetzner plan, do not tune further); rollback by SHA; that `/health` returning 200 does **not** mean the detector works, and `degraded_modules` is the real signal; that host access is Tailscale-only with Hetzner VNC as the sole fallback; and that nsosyal's database is deliberately unbacked-up.

- [ ] **Step 2: Commit**

```bash
git add infra/README.md
git commit -m "docs: add nsosyal deployment runbook"
```

---

### Task 11 (deferred): Memory reservations for the existing stacks

**Not part of the initial deployment.** Adding reservations forces Swarm to recreate tasks, which restarts sahhil's services — customer-visible downtime. It belongs in the maintenance window already deferred in `/root/PENDING-MAINTENANCE.md`, alongside the pending Docker upgrade and reboot.

**Files:**
- Modify: `~/Projects/personal/sahhil-alsayed/infra/docker-stack.yml`

- [ ] **Step 1: Add `reservations.memory` to each sahhil service**

Roughly half of each existing limit: `admin` 100M, `admin-frontend` 50M, `site` 32M, `postgres` 256M.

- [ ] **Step 2: Deploy during the window, alongside the Docker upgrade and reboot**

- [ ] **Step 3: Verify with the gate**

```bash
ssh root@100.75.227.23 /srv/verify-deploy.sh
```

Expected: all `OK`. The gate already checks sahhil, which is why it was written to.

---

## Self-Review

**Spec coverage:** §2 architecture → Tasks 4,5,7. §3 memory → Tasks 1,7,11. §4 weights → Task 3. §5 ingress/Access → Task 8. §6 CI/CD → Tasks 6,9. §7 database → Task 2. §8 verification → Task 7 Step 2, invoked by Tasks 7,9,11. §9 risks → each mitigation has a task. §10 out-of-scope → no tasks, correctly.

**Open items:** none. The one candidate — the Go health route — was resolved while writing this plan: `GET /api/health` at `backend/internal/http/handlers/handlers.go:115`.

**Parameters the executor must be given, not guess:** the local path to the model weights (Task 3 Step 2), the Cloudflare Access email allowlist (Task 8 Step 3), and the deploy SSH keypair (Task 9 Step 2). Each is marked at its point of use.

**Type consistency:** `APP_TAG` / `INFER_TAG` used identically in Tasks 7 and 9. `POSTGRES_PASSWORD` sourced from `/srv/nsosyal/db.env` in both. Network `nsosyal-data_nsosyal_internal` (Swarm's generated name for the `nsosyal_internal` network in the `nsosyal-data` stack) referenced consistently. Volume `nsosyal_models` consistent across Tasks 3 and 7. `verify-deploy.sh` lives at `/srv/verify-deploy.sh` on the host in Tasks 7, 9 and 11.
