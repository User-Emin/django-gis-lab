#!/usr/bin/env bash
# Rooktest voor een app-image: migrate (one-shot) tegen de PostGIS-service, web starten,
# /health controleren (200 + {"status":"ok","db":"ok"}) en wachten op Health.Status = healthy.
# Gebruik: rooktest.sh <image-of-image@digest> [containernaam]
# Verwacht in de omgeving: DJANGO_SECRET_KEY en DB_PASSWORD (worden alleen als naam doorgegeven,
# dus niet in de argumentenlijst), en een PostGIS op 127.0.0.1:5432 (db ci_gis, gebruiker postgres).
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
docker rm -f "$NAME" >/dev/null 2>&1 || true
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
docker inspect --format 'image-id: {{.Image}}  config-image: {{.Config.Image}}' "$NAME"
docker logs "$NAME" | tail -15

if [ "$code" != "200" ] || [ "$status" != "healthy" ] \
   || ! echo "$body" | grep -q '"status": *"ok"' || ! echo "$body" | grep -q '"db": *"ok"'; then
  echo "ROOKTEST MISLUKT: ${IMAGE} (http=$code, health=$status)"
  exit 1
fi
echo "ROOKTEST OK: ${IMAGE}"
