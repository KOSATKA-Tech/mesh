# --- STAGE 1: Build the Admin UI ---
FROM node:20-slim AS ui-builder
WORKDIR /ui

# Copy dependency files first for caching
COPY ui/package*.json ./
# Use cache mount for npm
RUN --mount=type=cache,target=/root/.npm \
    npm install

# Copy source and build
COPY ui/ ./
RUN npm run build

# --- STAGE 2: Build the Master API ---
FROM python:3.11-slim

# Copy uv binary from official image
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

# Install system dependencies and Caddy (combined for fewer layers)
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
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# 1. Copy full workspace structure FIRST
# Note: .dockerignore will handle excluding node_modules, .git, etc.
COPY pyproject.toml uv.lock /app/
COPY master /app/master
COPY agent /app/agent
COPY sdk /app/sdk
COPY cli /app/cli
COPY ansible /app/ansible

# 2. Copy the UI build AFTER copying the code
RUN mkdir -p /app/master/kosatka_master/static/admin
COPY --from=ui-builder /ui/dist /app/master/kosatka_master/static/admin

# Install Python dependencies with cache mount
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --link-mode=copy

ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONPATH=/app/master
ENV KOSATKA_ANSIBLE_DIR=/app/ansible

# Expose ports for both the API (8000) and Caddy (80, 443)
EXPOSE 8000 80 443

CMD ["uvicorn", "kosatka_master.main:app", "--host", "0.0.0.0", "--port", "8000"]
