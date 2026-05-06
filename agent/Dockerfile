FROM python:3.11-slim

WORKDIR /app

# Same uv-driven workspace build as master/Dockerfile. The build context
# is the repository root (set in docker-compose.agent.yml) so we can
# COPY the workspace pyproject and lockfile in one step.
RUN pip install --no-cache-dir uv

COPY pyproject.toml uv.lock README.md /app/
COPY master /app/master
COPY agent /app/agent
COPY sdk /app/sdk
COPY cli /app/cli

RUN uv sync --frozen --no-dev

ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONPATH=/app/agent

EXPOSE 8000

CMD ["uvicorn", "kosatka_agent.main:app", "--host", "0.0.0.0", "--port", "8000"]
