"""Prod-instellingen: `check --deploy` mag niets meer melden (les 27)."""

import os
import subprocess
import sys


def test_check_deploy_prod_geen_waarschuwingen():
    env = {
        **os.environ,
        "DJANGO_SETTINGS_MODULE": "projectkaart.settings.prod",
        "DJANGO_SECRET_KEY": "x" * 20 + "AbCdEfGhIjKlMnOpQrStUvWxYz0123456789" * 2,
        "DJANGO_ALLOWED_HOSTS": "ci.invalid",
    }
    p = subprocess.run(
        [sys.executable, "manage.py", "check", "--deploy", "--fail-level", "WARNING"],
        capture_output=True,
        text=True,
        env=env,
    )
    assert p.returncode == 0, p.stdout + p.stderr
    assert "0 silenced" in p.stdout
