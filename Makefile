.PHONY: check fix test hooks

# Les 29: git-hooks uit scripts/hooks activeren (commit-msg eist een JIRA-key)
hooks:
	git config core.hooksPath scripts/hooks
	@echo "core.hooksPath = $$(git config core.hooksPath)"

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
