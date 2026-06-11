.PHONY: check clean coverage demo-api demo-case demo-ui docs fixtures format frontend-build frontend-install lint mcp report test typecheck

REPORT_DOCX ?= tests/fixtures/geodesy_navigation_remote_sensing_thesis_template.docx
REPORT_DIR ?= outputs/extraction-report

fixtures:
	uv run python scripts/download_fixtures.py

demo-api:
	uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

demo-ui:
	cd frontend && npm run dev

demo-case:
	mkdir -p outputs/demo
	uv run python cli.py analyze "$(REPORT_DOCX)" -o outputs/demo/thesis-template-tree.json

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

frontend-install:
	cd frontend && npm install

frontend-build:
	cd frontend && npm run build

mcp:
	uv run --extra mcp docx-style-tree-mcp

docs:
	doxygen Doxyfile

check: lint typecheck test coverage

clean:
	rm -rf .coverage .mypy_cache .pytest_cache .ruff_cache htmlcov docs/api
