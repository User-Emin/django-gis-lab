"""gunicorn-configuratie voor Projectkaart (les 34).

Start: gunicorn -c deploy/gunicorn.conf.py projectkaart.wsgi:application
Waarden komen uit omgevingsvariabelen zodat Ansible (les 33) dezelfde file kan neerzetten.
"""

import multiprocessing
import os

# Alleen op loopback: nginx is de enige die van buiten praat.
bind = os.environ.get("GUNICORN_BIND", "127.0.0.1:8701")

# Vuistregel uit de gunicorn-docs: (2 x cores) + 1. Lab: begrensd, de Mac is geen server.
workers = int(os.environ.get("GUNICORN_WORKERS", min(2 * multiprocessing.cpu_count() + 1, 3)))
worker_class = "sync"

# Een request dat langer dan `timeout` seconden niets doet, wordt gedood en de worker herstart.
timeout = int(os.environ.get("GUNICORN_TIMEOUT", 30))
# Bij een graceful reload/stop krijgen lopende requests zoveel seconden om af te ronden.
graceful_timeout = 30
keepalive = 2

# Logs: bij systemd mag dit "-" (stdout/journald) zijn; in het lab naar bestanden.
log_dir = os.environ.get("GUNICORN_LOG_DIR", "-")
accesslog = "-" if log_dir == "-" else f"{log_dir}/gunicorn-access.log"
errorlog = "-" if log_dir == "-" else f"{log_dir}/gunicorn-error.log"
loglevel = "info"
access_log_format = '%(h)s "%(r)s" %(s)s %(b)s %(M)sms xff="%({x-forwarded-for}i)s"'
capture_output = True

pidfile = os.environ.get("GUNICORN_PIDFILE")  # nodig voor `kill -HUP $(cat ...)`
