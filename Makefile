.PHONY: up down logs migrate revision test test-local health seed-kb eval-retrieval blackbox

up:
	docker compose up -d --build

down:
	docker compose down

logs:
	docker compose logs -f api worker

migrate:
	docker compose exec api alembic upgrade head

revision:
	docker compose exec api alembic revision --autogenerate -m "$(m)"

test:
	docker compose exec api pytest -q

health:
	curl -fsS http://localhost:8000/health
	curl -fsS http://localhost:8000/health/ready

test-local:
	cd backend && .venv/Scripts/python -m pytest

seed-kb:
	backend/.venv/Scripts/python scripts/seed_kb/collect.py
	backend/.venv/Scripts/python scripts/seed_kb/add_documents.py
	backend/.venv/Scripts/python scripts/seed_kb/ingest.py

eval-retrieval:
	backend/.venv/Scripts/python scripts/eval_retrieval.py

blackbox:
	backend/.venv/Scripts/python scripts/blackbox_api_test.py
