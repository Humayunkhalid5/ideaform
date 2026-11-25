.PHONY: up down logs migrate revision test health

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
