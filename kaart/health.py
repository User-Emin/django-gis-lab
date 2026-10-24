"""Health-endpoints (les 25, uitgebreid in les 27).

- ``/health``  liveness: 200 als de database antwoordt, anders 503 (de container-HEALTHCHECK).
- ``/ready``   readiness: controleert database EN Redis (de Celery-broker); 503 zodra er één weg is.
"""

import logging

import redis
from django.conf import settings
from django.db import connection
from django.http import JsonResponse

logger = logging.getLogger(__name__)


def _db_ok() -> bool:
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
    except Exception:  # elke DB-fout betekent: niet gezond
        return False
    return True


def _redis_ok() -> bool:
    try:
        client = redis.Redis.from_url(
            settings.CELERY_BROKER_URL, socket_connect_timeout=2, socket_timeout=2
        )
        return bool(client.ping())
    except Exception:
        return False


def health(request):
    if not _db_ok():
        return JsonResponse({"status": "fout", "db": "onbereikbaar"}, status=503)
    return JsonResponse({"status": "ok", "db": "ok"})


def ready(request):
    db, broker = _db_ok(), _redis_ok()
    status = "ok" if db and broker else "fout"
    body = {
        "status": status,
        "db": "ok" if db else "onbereikbaar",
        "redis": "ok" if broker else "onbereikbaar",
    }
    if status != "ok":
        logger.warning("readiness mislukt", extra={"db": body["db"], "redis": body["redis"]})
    return JsonResponse(body, status=200 if status == "ok" else 503)
