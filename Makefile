.PHONY: install test lint typecheck backend frontend

install:
	python -m pip install -e '.[dev]'

lint:
	ruff check src tests

format-check:
	ruff format --check src tests

typecheck:
	mypy src/rci

test:
	pytest tests/unit tests/contract tests/integration tests/simulation tests/safety

backend:
	python -m rci.app

frontend:
	cd dashboard && npm run dev
