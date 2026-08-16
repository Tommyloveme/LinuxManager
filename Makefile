PYTHON ?= python
PORT ?= 8080

.PHONY: backend-dev frontend-dev frontend-build test lint run install-dev

backend-dev:
	cd backend && $(PYTHON) -m uvicorn app.main:app --reload --host 0.0.0.0 --port $(PORT)

frontend-dev:
	cd frontend && npm run dev

frontend-build:
	cd frontend && npm install && npm run build

run:
	cd backend && $(PYTHON) -m app.main

test:
	cd backend && $(PYTHON) -m pytest -q

lint:
	cd backend && $(PYTHON) -m ruff check app || true
