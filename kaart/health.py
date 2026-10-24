"""Health-endpoint voor de container (les 25): 200 als de database antwoordt, anders 503."""

from django.db import connection
from django.http import JsonResponse


def health(request):
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
    except Exception:  # elke DB-fout betekent: niet gezond
        return JsonResponse({"status": "fout", "db": "onbereikbaar"}, status=503)
    return JsonResponse({"status": "ok", "db": "ok"})
