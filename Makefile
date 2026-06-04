.PHONY: check clean coverage docs fixtures format lint report test typecheck

REPORT_DOCX ?= tests/fixtures/geodesy_navigation_remote_sensing_thesis_template.docx
REPORT_DIR ?= outputs/extraction-report

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
	uv run --extra dev coverage html

report: coverage
	uv run python scripts/render_extraction_report.py "$(REPORT_DOCX)" -o "$(REPORT_DIR)"

docs:
	doxygen Doxyfile

check: lint typecheck test coverage

clean:
	rm -rf .coverage .mypy_cache .pytest_cache .ruff_cache htmlcov docs/api
