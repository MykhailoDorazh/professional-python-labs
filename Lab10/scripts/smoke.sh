#!/usr/bin/env bash
# Smoke test of the Docker image: start a container, wait for /health, clean up.
set -uo pipefail
image="${1:-bank-account-service:ci}"
docker rm -f api-ci >/dev/null 2>&1
docker run -d --name api-ci -p 8001:8000 "$image" >/dev/null || exit 1
ok=1
for _ in $(seq 1 30); do
    if curl -fsS http://localhost:8001/health; then echo; ok=0; break; fi
    sleep 1
done
docker rm -f api-ci >/dev/null
exit $ok
