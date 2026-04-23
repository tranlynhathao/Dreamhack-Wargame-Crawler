PYTHON ?= $(shell if [ -x .venv/bin/python ]; then echo .venv/bin/python; else echo python3; fi)
NPM_CACHE ?= /tmp/dreamhack-local-npm-cache

.PHONY: install dev-install test api cli venv ui-install ui-dev ui-build ui-test

install:
	$(PYTHON) -m pip install -e .

dev-install:
	$(PYTHON) -m pip install -e ".[dev]"

venv:
	python3 -m venv .venv
	.venv/bin/python -m pip install --upgrade pip
	.venv/bin/python -m pip install -e ".[dev]"

test:
	$(PYTHON) -m pytest

api:
	$(PYTHON) dreamhack_crawler.py serve

cli:
	$(PYTHON) dreamhack_crawler.py --help

ui-install:
	cd frontend && NPM_CONFIG_CACHE=$(NPM_CACHE) npm install

ui-dev:
	cd frontend && npm run dev

ui-build:
	cd frontend && npm run build

ui-test:
	cd frontend && npm run test
