# nsosyal — operations runbook

Read this before touching anything at 3am. It documents the deployment that
actually happened on 2026-09-20, not an idealized version of it.

## 1. What this is and where it runs

Two Docker Swarm stacks on the `tevekkul` VPS:

```bash
ssh root@100.75.227.23   # Tailscale address; this is the ONLY way in
```

- The public IP is `46.224.235.180`. Port 22 is firewalled on it — SSH only
  works over Tailscale.
- **If Tailscale is down, the only fallback is the Hetzner Cloud web VNC
  console.** There is no other out-of-band access to this host. Confirm you
  can reach the Hetzner project before you need it, not during an incident.
- Public URL: `https://nsosyal.daqqiq.com` (Cloudflare-proxied, Traefik on
  the host terminates TLS via its existing DNS-01 certresolver).

**This host also runs `sahhil-alsayed` (a real customer-facing storefront)
and `workbench`.** Every command below — builds, deploys, restarts — must
leave those two alone. `infra/verify-deploy.sh` checks this for you; never
skip that check because "it's just an nsosyal change."

## 2. Architecture, briefly

| Service | Stack | Image | Size (measured) | Memory limit / reservation |
|---|---|---|---|---|
| `nsosyal_app` | `nsosyal` (`infra/docker-stack.yml`) | `nsosyal-app:<sha>` | 42.2MB | 256M / 64M |
| `nsosyal_infer` | `nsosyal` (`infra/docker-stack.yml`) | `nsosyal-infer:<sha>` | 1.99GB | 2048M / 1024M |
| `nsosyal-data_postgres` | `nsosyal-data` (`infra/data-stack.yml`) | `postgres:18-alpine` | — | 384M / 128M |

`nsosyal_app` is the Go binary (`backend/`) with the built Vue SPA embedded
via `go:embed` — one static 42MB binary in an alpine base, nothing else.
`nsosyal_infer` is FastAPI (`AI/serving/app.py`) running CPU-only PyTorch and
the BERTurk encoder (`m3_encoder`).

**Why they're two separate services, not one:**

1. **Independent memory caps.** The Go app is a lightweight HTTP frontend and
   caps at 256M. The inference service loads a full transformer model and
   needs up to 2048M. Bundling them into one container would force both
   caps onto a single process, wasting memory on the small side or starving
   the large one.
2. **Redeploy speed.** `nsosyal-app` is 42MB and redeploys (pull + start) in
   seconds. `nsosyal-infer` is 1.99GB. Keeping them separate means an app-only
   change (the overwhelming majority of changes) never has to touch the
   2GB image at all.

**The Go app does NOT spawn the Python process.** In a normal (non-Docker)
deployment, `backend/internal/supervisor` starts and monitors the FastAPI
service itself. In this stack, `NSOSYAL_PYTHON_ENABLED=false` is set on
`nsosyal_app`, which sets the supervisor's `Manage=false` — it only monitors
health at the configured URL, it never execs anything
(`backend/internal/supervisor/python.go`, see the `start()` closure: `if
!s.cfg.Manage { return }`). The app instead calls out to
`NSOSYAL_INFERENCE_URL=http://infer:8001`, reaching `nsosyal_infer` over the
`nsosyal_internal` overlay network by its Swarm service alias `infer`.

**`NSOSYAL_PYTHON_URL` is NOT a valid environment key. Do not set it.**
Config env vars are derived from the YAML path in `backend/config.yaml`, and
the inference URL lives under the top-level `inference:` section:

```yaml
inference:
  url: "http://127.0.0.1:8001"   # -> NSOSYAL_INFERENCE_URL
python:
  # command/args/workdir for the LOCAL supervisor case; no `url` key here
```

There is no `python.url` key, so `NSOSYAL_PYTHON_URL` matches nothing.
Setting it is **silently ignored** — Go just keeps the config default
`http://127.0.0.1:8001`, which inside the `nsosyal_app` container is itself,
not `nsosyal_infer`. The result is `/api/health` staying green while every
real analyze request fails, because nothing listens on 127.0.0.1:8001 in
that container. If inference calls start failing after a deploy, check this
first: `docker service inspect nsosyal_app --format '{{json
.Spec.TaskTemplate.ContainerSpec.Env}}'` and confirm `NSOSYAL_INFERENCE_URL`
is present, spelled exactly that way.

## 3. Images are built ON THE HOST

There is no registry and no CI pipeline. Two permission facts made GitHub
Actions unreachable for this deployment: the `gh` token in use lacks the
`workflow` scope (so `.github/workflows/*` cannot even be pushed), and the
user is not an admin on the repo (so Actions secrets cannot be configured).
Automatic deployment was also explicitly dropped for this iteration. Until
that changes, images are built directly on `tevekkul` from a source archive.

**Step 1 — ship a clean source tree to the host** (not the working tree —
an archive of `HEAD`, so untracked/dirty local state never leaks in):

```bash
git archive --format=tar HEAD | ssh root@100.75.227.23 \
  "rm -rf /srv/nsosyal/src && mkdir -p /srv/nsosyal/src && tar -x -C /srv/nsosyal/src"
```

**Step 2 — build each image, with a memory cap. Never build without one on
this host** — an uncapped build competes for memory with `sahhil-alsayed`
and `workbench`, which are customer-facing.

```bash
SHA=$(git rev-parse --short HEAD)

# App image: needs 2g, NOT 1g. See explanation below.
ssh root@100.75.227.23 "cd /srv/nsosyal/src && docker build --memory=2g --memory-swap=4g \
  -f infra/app.Dockerfile -t nsosyal-app:$SHA -t nsosyal-app:latest . 2>&1 | tail -20"

# Infer image: 1g is enough.
ssh root@100.75.227.23 "cd /srv/nsosyal/src && docker build --memory=1g --memory-swap=3g \
  -f infra/infer.Dockerfile -t nsosyal-infer:$SHA -t nsosyal-infer:latest . 2>&1 | tail -30"
```

**Why the app image needs `--memory=2g` and the infer image only needs
`--memory=1g`, even though the infer image is 47x bigger on disk:**

The app build's frontend stage runs `vue-tsc -b` (`infra/app.Dockerfile`,
frontend stage). Under `docker build --memory=1g`, Node derives its default
V8 old-space heap from the cgroup memory limit, landing at roughly 512MB —
`vue-tsc` exhausted that heap at **~510MB** and the build aborted with
**exit 134** (`Reached heap limit — JavaScript heap out of memory`). This is
why `infra/app.Dockerfile` also sets, in the frontend stage:

```dockerfile
ENV NODE_OPTIONS=--max-old-space-size=1536
```

That line makes the build correct regardless of the cap a future operator
passes, but the cap still has to be raised to `2g` to give that 1536MB heap
somewhere to live alongside the rest of the build.

**The counterintuitive part:** torch (`infer.Dockerfile`) built fine at
`--memory=1g` on the first try. The build-time memory hog on this host was
TypeScript compilation, not PyTorch — the opposite of what the original
design assumed (off-box builds were originally chosen specifically to keep
`pip install torch` away from this host). Keep that in mind if a future
Dockerfile change makes the frontend build heavier — the app image's cap may
need to grow again before the infer image's does.

If a build gets OOM-killed anyway, only raise the cap after confirming
`sahhil-alsayed` is still serving 200:

```bash
curl -s -o /dev/null -w '%{http_code}\n' https://sahhil.com/
```

**Step 3 — confirm the storefront survived the build:**

```bash
ssh root@100.75.227.23 'free -m; docker service ls --format "{{.Name}} {{.Replicas}}" | grep -E "sahhil|workbench|traefik"'
```

## 4. Deploying and updating

`docker stack deploy` does **not** interpolate `${...}` from the compose
file the way `docker compose` does — Swarm needs `envsubst` to do the
substitution first. Both stacks need `POSTGRES_PASSWORD` (for
`nsosyal-data`) and, for the app stack, `APP_TAG` / `INFER_TAG` naming the
image tags built in §3.

`POSTGRES_PASSWORD` lives in `/srv/nsosyal/db.env` on the host, mode `600`.
**Never print it, never commit it, never put it in a stack file.**

```bash
ssh root@100.75.227.23 "bash -s" <<'EOF'
set -e
chmod +x /srv/verify-deploy.sh
set -a; . /srv/nsosyal/db.env; set +a
export APP_TAG=<sha> INFER_TAG=<sha>
docker stack deploy -c <(envsubst < /srv/docker-stack.yml) nsosyal
EOF
```

The Postgres stack (`nsosyal-data`, deployed from `/srv/nsosyal-data-stack.yml`
on the host) follows the same `set -a; . /srv/nsosyal/db.env; set +a` +
`envsubst` pattern; it rarely needs redeploying since `postgres:18-alpine`
and its config are stable.

Wait for `nsosyal_infer` to converge before gating — BERTurk load can take
up to the `startup_grace: 120s` configured in `backend/config.yaml`:

```bash
ssh root@100.75.227.23 'until docker service ls --filter name=nsosyal_infer \
  --format "{{.Replicas}}" | grep -q "^1/1$"; do sleep 10; done; /srv/verify-deploy.sh'
```

### Rollback

```bash
docker service update --image nsosyal-app:<previous-sha> nsosyal_app
docker service update --image nsosyal-infer:<previous-sha> nsosyal_infer
```

**Rollback has not been rehearsed yet.** This command is the documented
intent, not a verified procedure — the first real rollback should be treated
as a test of this instruction, and this section corrected if anything about
it turns out to be wrong (image pruning, network aliasing, etc.).

## 5. The deploy gate — run it after every change

```bash
ssh root@100.75.227.23 /srv/verify-deploy.sh   # repo copy: infra/verify-deploy.sh
```

This script is the single most important file in this directory. It checks:

1. `nsosyal_app`, `nsosyal_infer`, and `nsosyal-data_postgres` are all at
   full replicas.
2. `nsosyal_infer`'s `/health` reports `status: ok` **and** `m3_encoder` is
   not in `degraded_modules`.
3. The origin serves the public host over HTTPS with a `200`.
4. **`sahhil-alsayed`, `workbench`, and Traefik are unharmed** — full
   replicas plus a `200` from `sahhil.com`. This is not optional
   housekeeping; it is the actual point of the check on a shared host.
5. Reports memory headroom (`free -m`), informational only.

### Why check 2 matters more than any HTTP status code

**This application degrades gracefully instead of failing loudly.** A
deploy with missing or wrong model weights still produces: a green
container, a healthy `1/1` replica count, and `/health` returning HTTP 200
with `"status": "ok"`. The only thing different is a detector that silently
detects nothing — every request still gets answered, just without the
BERTurk signal behind it. **`degraded_modules` in the `/health` body is the
real signal, `status` and the HTTP code are not.** Never read a `200` from
`/health` as "the detector works."

### A real bug this gate had, and how it was found

An earlier version of check 2 was:

```bash
if [ "$status" = "ok" ] && ! printf '%s' "$h" | grep -q 'm3'; then
```

i.e. "healthy AND the whole `/health` body does not contain the substring
`m3`." This is wrong: `AI/serving/capabilities.py`'s `CAPABILITIES` list is
present in **every** `/health` response regardless of model state and
contains an entry for `m3_encoder`. So the payload always contains the
substring `m3`, the negated grep was always false, and **the OK branch was
structurally unreachable** — a fully healthy deploy would have failed this
check forever, and (worse) the `PRE_WEIGHTS=1` branch would mask any
*future*, real m3 failure the same way. The fix parses `degraded_modules`
specifically instead of substring-matching the whole payload:

```bash
degraded=$(printf '%s' "$h" | sed -n 's/.*"degraded_modules"[[:space:]]*:[[:space:]]*\[\([^]]*\)\].*/\1/p')
m3bad=0
printf '%s' "$degraded" | grep -q 'm3_encoder' && m3bad=1
```

The lesson: never substring-match a raw JSON health payload against a
module name that also appears in an always-present field.

### `PRE_WEIGHTS=1`

```bash
PRE_WEIGHTS=1 /srv/verify-deploy.sh
```

This turns the m3-degraded FAIL into a WARN, for the one legitimate case of
deploying wiring before weights exist. **`PRE_WEIGHTS=1` must never be set
once weights are actually present on the box.** It is the only thing
standing between a green gate and a silently blind detector — setting it
unconditionally defeats the entire purpose of check 2.

## 6. Current known state (as of 2026-09-20) — TEMPORARY

These are today's facts, not permanent design. Update this section as each
item resolves; do not let it go stale.

- **Model weights are not delivered.** They are held by the repo owner
  (MusaabAlt), not on this machine. `m3_encoder` is in `degraded_modules`,
  so **the detector is inactive** — the service answers requests, but
  produces no offensive-content signal. The `nsosyal_models` volume exists
  (created empty so `nsosyal_infer` had somewhere to mount without
  crash-looping) but currently holds nothing.
- **`m5_sarcasm` is also in `degraded_modules`. This is not a bug.** It is
  an unimplemented stub upstream: `AI/modules/m5_sarcasm/module.py` sets
  `stub = True` and its output is `notes=["stub: detection not
  implemented"]`. The team is waiting on data access for this module; there
  is nothing to fix here from the infra side.
- **A temporary Traefik basic-auth middleware guards the site**, user
  `nsosyal`. It exists because the app has no authentication of its own and
  the site was briefly reachable by anyone. It was applied out-of-band:
  ```bash
  docker service update --label-add \
    'traefik.http.middlewares.nsosyal_auth.basicauth.users=<htpasswd entry>' \
    --label-add 'traefik.http.routers.nsosyal.middlewares=nsosyal_auth' \
    nsosyal_app
  ```
  **These labels are NOT in `infra/docker-stack.yml`.** A plain
  `docker stack deploy` of that file wipes them, silently re-exposing the
  site with no authentication. Until Cloudflare Access replaces this, check
  for these labels after every deploy (`docker service inspect nsosyal_app`)
  and reapply them if they're gone.
  This middleware must be replaced by Cloudflare Access, not kept
  long-term. Once Access is in front of the origin, `verify-deploy.sh`'s
  origin check goes back to returning `200` on its own — **it currently and
  correctly reports `FAIL (401)`**, because Traefik rejects unauthenticated
  requests by design right now. Do not "fix" the gate to tolerate 401; fix
  the missing Access configuration instead.
- **Cloudflare:** the DNS A record (`nsosyal.daqqiq.com` -> `46.224.235.180`,
  proxied) is done — created via the token already present in the Traefik
  service environment, which is scoped to both `daqqiq.com` and
  `sahhil.com`, so the existing DNS-01 certresolver issues the TLS cert
  automatically. **Cloudflare Access is not configured.** The available
  token is DNS-scoped only (403 on the Access API), so this step requires
  the Cloudflare dashboard and is a manual, human action.

## 7. When the weights arrive

1. Copy `berturk_epoch1.pt` and the `tokenizer/` directory into the
   `nsosyal_models` volume's data directory on the host:
   ```
   /var/lib/docker/volumes/nsosyal_models/_data/berturk_epoch1.pt
   /var/lib/docker/volumes/nsosyal_models/_data/tokenizer/{config.json,tokenizer.json,tokenizer_config.json}
   ```
2. Verify every file's sha256 against `AI/artifacts/MANIFEST.md` /
   `AI/modules/m3_encoder/module.py` before restarting anything:
   ```bash
   sha256sum /var/lib/docker/volumes/nsosyal_models/_data/berturk_epoch1.pt
   # expect: 43a20d5525aff0a57c0bda2be559a5acdf84848cf7cbed844f0c8f5f3024d4ca

   sha256sum /var/lib/docker/volumes/nsosyal_models/_data/tokenizer/config.json
   # expect: 980b01ddb94ee8cc2533e064bdca97584b96bbf9755601217ae3d13460c58f48

   sha256sum /var/lib/docker/volumes/nsosyal_models/_data/tokenizer/tokenizer.json
   # expect: d424e0bceb7f017dfced77157d14647505b28b41bfc8d9bffd5631f1b1fe61e5

   sha256sum /var/lib/docker/volumes/nsosyal_models/_data/tokenizer/tokenizer_config.json
   # expect: d50873edfa649e9950fbfb196da01d0b2b4470a25e2ac711cf5c7022761b0a04
   ```
3. Restart `nsosyal_infer` so it re-reads the volume:
   ```bash
   docker service update --force nsosyal_infer
   ```
4. Run the gate **without** `PRE_WEIGHTS` and require it to pass:
   ```bash
   /srv/verify-deploy.sh
   ```
   Anything other than a clean exit 0 here means do not consider the
   weights live yet.

Note that this checksum step is a safety net, not the only line of defense:
the app verifies the digests itself at load time
(`AI/modules/m3_encoder/module.py`, `_load_binary`, lines ~111-121) and
**refuses to load mismatched files**, raising `ValueError("m3 artifact
sha256 mismatch, not the frozen files: ...")` rather than silently loading
something wrong. A copy error will surface as `nsosyal_infer` failing to
reach `status: ok`, not as a wrong-but-quiet result.

## 8. Memory budget

Host total: **3819MB** (`free -m`, `Mem:` row, total column).

Measured on 2026-09-20 across three gate runs, **with the detector inactive
(m3 degraded, no real BERTurk inference happening — only health checks)**:

| Run | Mem available | Swap used |
|---|---|---|
| Task 7, initial deploy | 2349MB | 79MB |
| Task 7, fix-round gate #1 | 2325MB | 79MB |
| Task 7, fix-round gate #2 | 2339MB | 79MB |

Call this baseline **~2338MB available, 79MB swap used**.

Configured service memory caps:

| Service | Limit | Reservation |
|---|---|---|
| `nsosyal_infer` | 2048M | 1024M |
| `nsosyal_app` | 256M | 64M |
| `nsosyal-data_postgres` | 384M | 128M |

Swap was grown from 2GB to 6GB total (`/swapfile` 2G + new `/swapfile2` 4G,
`swapon --show` reporting 6143MB) specifically to absorb this workload's
build- and runtime-time memory spikes.

**This baseline was measured with the model NOT loaded.** Loading BERTurk
for real inference will consume substantially more than the idle numbers
above — re-measure `mem available` and `swap used` (both are printed by
`verify-deploy.sh`'s last line) once weights are in and the model is
actually loaded and serving traffic, not just idling in a degraded state.

**If `nsosyal_infer`'s resident memory settles above ~1.8GB once real
inference is running, the answer is upgrading the Hetzner plan, not further
tuning.** The service's memory limit is already 2048M; there is very little
headroom below that cap to tune into before hitting OOM kills on the
container, and further squeezing this host risks starving
`sahhil-alsayed` and `workbench`.

## 9. Deliberate omissions

These are decisions, not gaps to fill in later without discussion:

- **nsosyal's database is not backed up.** `infra/data-stack.yml` says so
  explicitly in its header comment — this is demo data, deliberately not
  wired into `/srv/backup-db.sh`.
- **There is no CI/CD.** See §3 — the `gh` token lacks the `workflow` scope
  and the user is not a repo admin, and automatic deployment was explicitly
  dropped for this iteration. Every build and deploy in this document is a
  manual, human-run action.
- **`diagnosis/` and its large asset bundle (reported at ~886MB) are not
  deployed.** It's excluded via `.dockerignore` from both build contexts —
  it is the research/study directory the model was originally derived from,
  not runtime code, and has no business in either image.
