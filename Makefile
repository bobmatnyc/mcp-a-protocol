.PHONY: install validate test lint format check

install:
	uv sync

validate:
	uv run pytest tests/test_schemas_wellformed.py tests/test_examples_validate.py tests/test_examples_manifest_complete.py -v

test:
	uv run pytest

lint:
	uv run ruff check .

format:
	uv run ruff format .

check: lint test
