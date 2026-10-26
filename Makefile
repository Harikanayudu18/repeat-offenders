.PHONY: install test lint eval frontend-check run docker

install:
	pip install -r requirements.txt -r requirements-dev.txt
	cd frontend && npm ci

test:
	python -m pytest -q

lint:
	ruff check .

eval:
	python scripts/run_evaluation.py --version v1

frontend-check:
	cd frontend && npm run typecheck && npm test && npm run build

run:
	./scripts/start_unix.sh

docker:
	docker compose up --build
