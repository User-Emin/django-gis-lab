.PHONY: check fix

# Les 04 (Zelf): één commando voor stijlcontrole
check:
	uv run ruff check .
	uv run ruff format --check .

fix:
	uv run ruff check --fix .
	uv run ruff format .
