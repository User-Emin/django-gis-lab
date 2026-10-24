"""Schets view (cad/views.py): start de task en geeft meteen 202 terug."""

from django.http import JsonResponse
from django.views.decorators.http import require_POST

from .tasks import controleer_tekening


@require_POST
def start_controle(request, tekening_id: int):
    controleer_tekening.delay_on_commit(tekening_id)  # Celery >=5.4, feiten-tech §6
    return JsonResponse({"tekening": tekening_id, "status": "gestart"}, status=202)
