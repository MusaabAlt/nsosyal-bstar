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
