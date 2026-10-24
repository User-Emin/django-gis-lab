#!/usr/bin/env bash
# Rooktest voor een app-image: migrate (one-shot) tegen de PostGIS-service, web starten,
# /health controleren (200 + {"status":"ok","db":"ok"}) en wachten op Health.Status = healthy.
# Gebruik: rooktest.sh <image-of-image@digest> [containernaam]
# Verwacht in de omgeving: DJANGO_SECRET_KEY en DB_PASSWORD (worden alleen als naam doorgegeven,
# dus niet in de argumentenlijst), en een PostGIS op 127.0.0.1:5432 (db ci_gis, gebruiker postgres).
# Les 27: met ROOKTEST_UITGEBREID=1 ook check --deploy, security-headers, /ready, een Redis (zonder
# gepubliceerde poort, bereikt via zijn container-IP) en een Celery-worker met een echte cad.rcs_check.
# Niet voor oudere images (rollback-oefening): die kennen /ready en de worker-instellingen nog niet.
set -euo pipefail

IMAGE="${1:?image ontbreekt}"
NAME="${2:-web}"
: "${DJANGO_SECRET_KEY:?}" "${DB_PASSWORD:?}"

DB_ENV=(
  -e DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1
  -e DB_NAME=ci_gis -e DB_HOST=127.0.0.1 -e DB_PORT=5432 -e DB_USER=postgres
  -e DB_PASSWORD -e DJANGO_SECRET_KEY
)
HDR='X-Forwarded-Proto: https'

echo "== rooktest voor ${IMAGE} (container ${NAME})"
UITGEBREID="${ROOKTEST_UITGEBREID:-0}"
docker rm -f "$NAME" "${NAME}-worker" "${NAME}-redis" >/dev/null 2>&1 || true

if [ "$UITGEBREID" = "1" ]; then
  # Redis alleen op het standaard bridge-netwerk, nooit met -p; web en worker (host-netwerk) gebruiken het IP.
  docker run -d --name "${NAME}-redis" redis:7.4.8-alpine >/dev/null
  REDIS_IP="$(docker inspect --format '{{.NetworkSettings.IPAddress}}' "${NAME}-redis")"
  DB_ENV+=(-e "CELERY_BROKER_URL=redis://${REDIS_IP}:6379/0" -e "CELERY_RESULT_BACKEND=redis://${REDIS_IP}:6379/1")
  echo "== check --deploy (prod-instellingen in de image)"
  docker run --rm --network host "${DB_ENV[@]}" "$IMAGE" python manage.py check --deploy --fail-level WARNING
fi

docker run --rm --network host "${DB_ENV[@]}" "$IMAGE" python manage.py migrate --noinput | tail -5
docker run -d --name "$NAME" --network host "${DB_ENV[@]}" "$IMAGE" >/dev/null

code=000
for i in $(seq 1 30); do
  code="$(curl -s -o /dev/null -w '%{http_code}' -H "$HDR" http://127.0.0.1:8000/health || true)"
  echo "poging $i: /health -> $code"
  [ "$code" = "200" ] && break
  sleep 2
done
body="$(curl -s -H "$HDR" http://127.0.0.1:8000/health || true)"
echo "body: $body"
echo "statisch (whitenoise): $(curl -s -o /dev/null -w '%{http_code}' -H "$HDR" http://127.0.0.1:8000/static/admin/css/base.css)"

status=unknown
for i in $(seq 1 20); do
  status="$(docker inspect --format '{{.State.Health.Status}}' "$NAME")"
  echo "healthcheck-status: $status"
  [ "$status" = "healthy" ] && break
  sleep 5
done
if [ "$UITGEBREID" = "1" ]; then
  echo "== /ready (database en Redis)"
  ready_code="$(curl -s -o /dev/null -w '%{http_code}' -H "$HDR" http://127.0.0.1:8000/ready || true)"
  ready_body="$(curl -s -H "$HDR" http://127.0.0.1:8000/ready || true)"
  echo "/ready -> $ready_code $ready_body"

  echo "== security-headers (curl -sI /health, achter de proxy-header)"
  headers="$(curl -sI -H "$HDR" http://127.0.0.1:8000/health | tr -d '\r')"
  echo "$headers"
  for h in strict-transport-security x-content-type-options x-frame-options referrer-policy \
           content-security-policy-report-only cross-origin-opener-policy; do
    echo "$headers" | grep -qi "^$h:" || { echo "HEADER ONTBREEKT: $h"; exit 1; }
  done
  echo "$headers" | grep -qi '^strict-transport-security:.*includeSubDomains' || { echo "HSTS zonder includeSubDomains"; exit 1; }

  echo "== Celery-worker en een echte cad.rcs_check"
  docker run -d --name "${NAME}-worker" --network host "${DB_ENV[@]}" "$IMAGE" \
    celery -A projectkaart worker -l info --concurrency 1 >/dev/null
  for i in $(seq 1 30); do
    docker logs "${NAME}-worker" 2>&1 | grep -q 'ready\.' && break
    sleep 2
  done
  docker run --rm --network host "${DB_ENV[@]}" "$IMAGE" python -c "
import django; django.setup()
from cad.tasks import rcs_check
r = rcs_check.delay('data/cad/plattegrond-bg-fouten.dxf')
print('taak-id:', r.id)
out = r.get(timeout=90)
print('resultaat:', {k: out[k] for k in ('bestand', 'aantal_bevindingen', 'ruimten')})
"
  echo "-- worker-log"
  docker logs "${NAME}-worker" 2>&1 | grep -E 'Connected to|ready\.|cad\.rcs_check' | sed 's/redis:\/\/[^ ]*/redis:\/\/<ip>:6379\/0/'
  docker logs "${NAME}-worker" 2>&1 | grep -q 'Task cad.rcs_check\[.*succeeded' || { echo "WORKER: taak niet geslaagd"; docker logs "${NAME}-worker" | tail -30; exit 1; }
  [ "$ready_code" = "200" ] || { echo "/ready gaf $ready_code"; exit 1; }
fi
docker inspect --format 'image-id: {{.Image}}  config-image: {{.Config.Image}}' "$NAME"
docker logs "$NAME" | tail -15

if [ "$code" != "200" ] || [ "$status" != "healthy" ] \
   || ! echo "$body" | grep -q '"status": *"ok"' || ! echo "$body" | grep -q '"db": *"ok"'; then
  echo "ROOKTEST MISLUKT: ${IMAGE} (http=$code, health=$status)"
  exit 1
fi
echo "ROOKTEST OK: ${IMAGE}"
