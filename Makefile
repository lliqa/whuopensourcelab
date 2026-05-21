.PHONY: check clean coverage docs fixtures format lint test typecheck

fixtures:
	uv run python scripts/download_fixtures.py

test:
	uv run python -m unittest discover -s tests

lint:
	uv run --extra dev ruff check .

format:
	uv run --extra dev ruff format .

typecheck:
	uv run --extra dev mypy app docx_style_tree cli.py tests scripts

coverage:
	uv run --extra dev coverage run -m unittest discover -s tests
	uv run --extra dev coverage report

docs:
	doxygen Doxyfile

check: lint typecheck test coverage

clean:
	rm -rf .coverage .mypy_cache .pytest_cache .ruff_cache htmlcov docs/api
