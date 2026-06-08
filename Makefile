ANTLR_JAR=tools/antlr-4.13.2-complete.jar
GRAMMAR=grammar/Pietto.g4
OUT=src/pietto/generated

.PHONY: help generate-parser format lint test check clean

help:
	@echo "Available commands:"
	@echo "  make generate-parser   Generate ANTLR parser from grammar/Pietto.g4"
	@echo "  make format            Format Python code with Ruff"
	@echo "  make lint              Lint Python code with Ruff"
	@echo "  make test              Run pytest"
	@echo "  make check             Run format, lint, and tests"
	@echo "  make clean             Remove generated/cache files"

generate-parser:
	mkdir -p $(OUT)
	java -jar $(ANTLR_JAR) -Dlanguage=Python3 -visitor -no-listener -Xexact-output-dir -o $(OUT) $(GRAMMAR)
	touch $(OUT)/__init__.py

format:
	uv run ruff format .

lint:
	uv run ruff check .

test:
	uv run pytest

check: format lint test

clean:
	rm -rf $(OUT)
	rm -rf .pytest_cache
	rm -rf .ruff_cache
	rm -rf htmlcov
	rm -rf .coverage
