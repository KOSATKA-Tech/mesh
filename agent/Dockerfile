FROM python:3.11-slim

WORKDIR /app

# Same uv-driven workspace build as master/Dockerfile. The build context
# is the repository root (set in docker-compose.agent.yml) so we can
# COPY the workspace pyproject and lockfile in one step.
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    python3-dev \
    debian-keyring \
    debian-archive-keyring \
    apt-transport-https \
    curl \
    ca-certificates \
    gnupg \
    && curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' | gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg \
    && curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' | tee /etc/apt/sources.list.d/caddy-stable.list \
    && apt-get update && apt-get install -y caddy \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir uv

COPY pyproject.toml uv.lock README.md /app/
COPY master /app/master
COPY agent /app/agent
COPY sdk /app/sdk
COPY cli /app/cli

RUN uv sync --frozen --no-dev

ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONPATH=/app/agent

EXPOSE 8010

CMD ["uvicorn", "kosatka_agent.main:app", "--host", "0.0.0.0", "--port", "8010"]
