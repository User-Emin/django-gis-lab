.PHONY: check fix test

# Les 04 (Zelf): één commando voor stijlcontrole
check:
	uv run ruff check .
	uv run ruff format --check .

fix:
	uv run ruff check --fix .
	uv run ruff format .

# Les 08: tests met coverage-rapport (HTML in htmlcov/)
test:
	uv run pytest --cov --cov-report=term-missing --cov-report=html

# Les 34: lokale proxy-stack (nginx 8793 -> gunicorn 8701), start/stop via ~/django-lab-h/start-nginx-gunicorn.sh
proxy-test:
	curl -fsS http://127.0.0.1:8793/health
