#!/usr/bin/env bash
# infra/verify-deploy.sh — run ON the host. Exits non-zero on any failure.
set -uo pipefail
fail=0
say() { printf '%-42s %s\n' "$1" "$2"; }

# 1. every nsosyal service at full replicas
for svc in nsosyal_app nsosyal_infer nsosyal-data_postgres; do
  r=$(docker service ls --format '{{.Name}} {{.Replicas}}' | awk -v s="$svc" '$1==s {print $2}' | head -1)
  [ "${r%%/*}" = "${r##*/}" ] && [ -n "$r" ] && say "$svc" "OK ($r)" || { say "$svc" "FAIL ($r)"; fail=1; }
done

# 2. inference healthy AND m3 not degraded — the silent-failure guard
h=$(docker exec "$(docker ps -qf name=nsosyal_app | head -1)" \
      curl -fsS --max-time 10 http://infer:8001/health 2>/dev/null)
status=$(printf '%s' "$h" | sed -n 's/.*"status"[ :]*"\([^"]*\)".*/\1/p')
# Extract ONLY degraded_modules. Do not substring-match the whole payload:
# `capabilities` always contains "m3_encoder", so a naive grep matches even when
# m3 is perfectly healthy (AI/serving/capabilities.py).
degraded=$(printf '%s' "$h" | sed -n 's/.*"degraded_modules"[[:space:]]*:[[:space:]]*\[\([^]]*\)\].*/\1/p')
m3bad=0
printf '%s' "$degraded" | grep -q 'm3_encoder' && m3bad=1

if [ "$status" = "ok" ] && [ "$m3bad" = "0" ]; then
  say "inference m3 loaded" "OK (artifact $(printf '%s' "$h" | sed -n 's/.*"artifact_hash"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' | cut -c1-12))"
elif [ "${PRE_WEIGHTS:-0}" = "1" ] && [ "$status" = "ok" ] && [ "$m3bad" = "1" ]; then
  # Pre-weights mode: model artifacts not yet delivered. NEVER set PRE_WEIGHTS=1
  # once weights are on the box — this is the only check standing between a green
  # deploy and a silently blind detector.
  say "inference m3 loaded" "WARN (PRE_WEIGHTS=1: m3 degraded, detector inactive)"
else
  say "inference m3 loaded" "FAIL (status=$status degraded=[$degraded])"; fail=1
fi

# 3. origin serves the app
code=$(curl -sk -o /dev/null -w '%{http_code}' --max-time 10 -H "Host: nsosyal.daqqiq.com" https://127.0.0.1/)
[ "$code" = "200" ] && say "origin nsosyal.daqqiq.com" "OK (200)" || { say "origin nsosyal.daqqiq.com" "FAIL ($code)"; fail=1; }

# 4. the storefront is unharmed — the memory budget is shared
for svc in $(docker service ls --format '{{.Name}}' | grep -E 'sahhil|workbench|traefik'); do
  r=$(docker service ls --format '{{.Name}} {{.Replicas}}' | awk -v s="$svc" '$1==s {print $2}' | head -1)
  [ "${r%%/*}" = "${r##*/}" ] || { say "$svc" "FAIL ($r)"; fail=1; }
done
s=$(curl -sk -o /dev/null -w '%{http_code}' --max-time 10 -H "Host: sahhil.com" https://127.0.0.1/)
[ "$s" = "200" ] && say "sahhil origin unharmed" "OK (200)" || { say "sahhil origin unharmed" "FAIL ($s)"; fail=1; }

# 5. memory headroom report (informational)
say "mem available" "$(free -m | awk 'NR==2{print $7"MB"}')  swap used $(free -m | awk 'NR==3{print $3"MB"}')"

exit $fail
