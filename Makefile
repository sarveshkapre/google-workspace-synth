PYTHON?=python3
VENV?=.venv
BIN=$(VENV)/bin
PIP=$(BIN)/pip
PY=$(BIN)/python

.PHONY: setup dev seed test lint typecheck build check release

setup:
	$(PYTHON) -m venv $(VENV)
	$(PIP) install --upgrade pip
	$(PIP) install -r requirements.txt -r requirements-dev.txt

dev:
	PYTHONPATH=src $(PY) -m gwsynth.main

seed:
	PYTHONPATH=src $(PY) -m gwsynth.seed

test:
	PYTHONPATH=src $(BIN)/pytest

lint:
	$(BIN)/ruff check src tests

typecheck:
	$(BIN)/mypy src

build:
	PYTHONPATH=src $(PY) -m compileall src

check: lint typecheck test build

release:
	@echo "Cut a GitHub release after updating docs/CHANGELOG.md"
