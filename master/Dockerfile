# --- STAGE 1: Build the Admin UI ---
FROM node:20-slim AS ui-builder
WORKDIR /ui

# Copy dependency files first for caching
COPY ui/package*.json ./
# Use cache mount for npm and skip optional/audit for max speed
RUN --mount=type=cache,target=/root/.npm \
    npm install --no-audit --no-fund

# Copy source and build
COPY ui/ ./
RUN npm run build

# --- STAGE 2: Build the Master API ---
FROM python:3.11-slim

# Copy uv binary from official image
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

# IMPORTANT: Copy the UI build FIRST. 
# This forces Docker BuildKit to serialize the stages!
# It will NOT start apt-get or Python installation until the UI is 100% built.
# This prevents SWAP thrashing and OOM crashes on small 1vCPU / 1GB VPS servers.
RUN mkdir -p /app/master/kosatka_master/static/admin
COPY --from=ui-builder /ui/dist /app/master/kosatka_master/static/admin

# Install ONLY Caddy and minimal runtime dependencies (NO build-essential)
RUN apt-get update && apt-get install -y --no-install-recommends \
    debian-keyring \
    debian-archive-keyring \
    apt-transport-https \
    curl \
    ca-certificates \
    gnupg \
    && curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' | gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg \
    && curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' | tee /etc/apt/sources.list.d/caddy-stable.list \
    && apt-get update && apt-get install -y --no-install-recommends caddy \
    && apt-get purge -y gnupg curl apt-transport-https \
    && apt-get autoremove -y \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Copy application code
COPY pyproject.toml uv.lock /app/
COPY master /app/master
COPY agent /app/agent
COPY sdk /app/sdk
COPY cli /app/cli
COPY ansible /app/ansible

# Install Python dependencies (uv uses pre-compiled wheels, no compilation needed)
# Added UV_HTTP_TIMEOUT and UV_RETRIES to handle flaky network on some VPS providers
RUN --mount=type=cache,target=/root/.cache/uv \
    UV_HTTP_TIMEOUT=300 UV_RETRIES=10 \
    uv sync --frozen --no-dev --link-mode=copy

ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONPATH=/app/master
ENV KOSATKA_ANSIBLE_DIR=/app/ansible

# Expose ports for both the API (8000) and Caddy (80, 443)
EXPOSE 8000 80 443

CMD ["uvicorn", "kosatka_master.main:app", "--host", "0.0.0.0", "--port", "8000"]
