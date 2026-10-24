# syntax=docker/dockerfile:1
# Les 25: de app in een container. Drie stages: frontend (Vite), builder (uv), runtime.

# --- 1. frontend: Vite-build naar kaart/static/app (vite.config.ts: outDir ../kaart/static/app)
FROM node:22.23.3-bookworm-slim AS frontend
WORKDIR /src/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN mkdir -p /src/kaart/static && npm run build

# --- 2. builder: Python-dependencies in een venv (geen dev-groep)
FROM python:3.13.17-slim-trixie AS builder
COPY --from=ghcr.io/astral-sh/uv:0.13.5 /uv /usr/local/bin/uv
ENV UV_PROJECT_ENVIRONMENT=/opt/venv \
    UV_PYTHON_DOWNLOADS=never \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy
WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --locked --no-dev --no-install-project

# --- 3. runtime: python-slim (Debian 13 trixie) + GDAL/GEOS/PROJ uit apt
FROM python:3.13.17-slim-trixie AS runtime
RUN apt-get update \
    && apt-get install -y --no-install-recommends libgdal36 libgeos-c1t64 libproj25 proj-data \
    && rm -rf /var/lib/apt/lists/* \
    && ln -s "$(ls /usr/lib/*/libgdal.so.36 | head -1)" /usr/local/lib/libgdal.so \
    && ln -s "$(ls /usr/lib/*/libgeos_c.so.1 | head -1)" /usr/local/lib/libgeos_c.so
ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    DJANGO_SETTINGS_MODULE=projectkaart.settings.prod \
    GDAL_LIBRARY_PATH=/usr/local/lib/libgdal.so \
    GEOS_LIBRARY_PATH=/usr/local/lib/libgeos_c.so
RUN groupadd --system --gid 10001 app \
    && useradd --system --uid 10001 --gid app --home-dir /app --shell /usr/sbin/nologin app
WORKDIR /app
COPY --from=builder /opt/venv /opt/venv
COPY . .
COPY --from=frontend /src/kaart/static/app ./kaart/static/app
# collectstatic met alleen dummy build-waarden; die blijven niet in de image (ENV staat in dit RUN).
RUN DJANGO_SECRET_KEY=alleen-voor-de-build DJANGO_ALLOWED_HOSTS=build.invalid \
    python manage.py collectstatic --noinput \
    && chown -R app:app /app/staticfiles \
    && chown app:app /app
USER app
EXPOSE 8000
# Achter een proxy is SECURE_SSL_REDIRECT aan; de healthcheck stuurt daarom X-Forwarded-Proto.
HEALTHCHECK --interval=10s --timeout=5s --start-period=20s --retries=5 \
    CMD ["python", "-c", "import urllib.request as u; r = u.Request('http://127.0.0.1:8000/health', headers={'X-Forwarded-Proto': 'https'}); u.urlopen(r, timeout=4)"]
CMD ["gunicorn", "projectkaart.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3", "--access-logfile", "-"]
