# --- STAGE 1: Build the Admin UI ---
FROM node:20-slim AS ui-builder
WORKDIR /ui
COPY ui/package*.json ./
RUN npm install
COPY ui/ ./
RUN npm run build

# --- STAGE 2: Build the Master API ---
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies and Caddy
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

# 1. Copy full workspace structure FIRST
COPY pyproject.toml uv.lock README.md /app/
COPY master /app/master
COPY agent /app/agent
COPY sdk /app/sdk
COPY cli /app/cli
COPY ansible /app/ansible

# 2. Copy the UI build AFTER copying the code to avoid overwriting
# The path must match kosatka_master/main.py expectations
RUN mkdir -p /app/master/kosatka_master/static/admin
COPY --from=ui-builder /ui/dist /app/master/kosatka_master/static/admin

# Install Python dependencies
RUN uv sync --frozen --no-dev

ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONPATH=/app/master
ENV KOSATKA_ANSIBLE_DIR=/app/ansible

# Expose ports for both the API (8000) and Caddy (80, 443)
EXPOSE 8000 80 443

CMD ["uvicorn", "kosatka_master.main:app", "--host", "0.0.0.0", "--port", "8000"]
