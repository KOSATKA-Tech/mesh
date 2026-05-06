.PHONY: master-up master-down agent-up agent-down deploy test lint sync docs clean master agent

# The single docker-compose.yml / docker-compose.prod.yml pair was
# replaced by per-role compose files: master colocates Postgres with
# the API service, agent runs alone and registers with a remote master
# via env-vars (see docker-compose.agent.yml for the required vars).
master-up:
	docker compose -f docker-compose.master.yml up -d --build

master-down:
	docker compose -f docker-compose.master.yml down

agent-up:
	docker compose -f docker-compose.agent.yml up -d --build

agent-down:
	docker compose -f docker-compose.agent.yml down

deploy:
	cd ansible && ./deploy.sh

sync:
	uv sync

install:
	uv pip install -e .

test:
	uv run pytest --cov=kosatka_master --cov=kosatka_agent --cov=KosatkaMesh --cov=kosatka_cli

lint:
	uv run black --check .
	uv run isort --check-only .
	uv run flake8 master agent sdk cli

master:
	uv run kosatka-mesh master run

agent:
	uv run kosatka-mesh agent run

docs:
	@echo "Documentation is available in the docs/ directory."
	@echo "Main entry point: docs/quickstart.md"

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
