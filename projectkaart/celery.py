"""Celery-app (les 22). Broker en resultaten: eigen Redis op 6390, zie settings/base.py."""

import os

from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "projectkaart.settings.dev")

app = Celery("projectkaart")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()
