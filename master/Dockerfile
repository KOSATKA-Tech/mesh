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
RUN npx vite build

# --- STAGE 2: Build Python Dependencies ---
FROM python:3.11-slim AS py-builder

# Copy uv binary from official image
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

# Install build dependencies (these will be discarded in the final image)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy full workspace structure required by uv sync
COPY pyproject.toml uv.lock /app/
COPY master /app/master
COPY agent /app/agent
COPY sdk /app/sdk
COPY cli /app/cli
COPY ansible /app/ansible

# Install Python dependencies into /app/.venv
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --link-mode=copy

# --- STAGE 3: Final Production Image ---
FROM python:3.11-slim

WORKDIR /app

# Install ONLY Caddy and minimal runtime dependencies
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

# Copy the pre-built Python environment from Stage 2
COPY --from=py-builder /app/.venv /app/.venv

# Copy application code
COPY pyproject.toml uv.lock /app/
COPY master /app/master
COPY agent /app/agent
COPY sdk /app/sdk
COPY cli /app/cli
COPY ansible /app/ansible

# Copy the UI build from Stage 1
RUN mkdir -p /app/master/kosatka_master/static/admin
COPY --from=ui-builder /ui/dist /app/master/kosatka_master/static/admin

ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONPATH=/app/master
ENV KOSATKA_ANSIBLE_DIR=/app/ansible

# Expose ports for both the API (8000) and Caddy (80, 443)
EXPOSE 8000 80 443

CMD ["uvicorn", "kosatka_master.main:app", "--host", "0.0.0.0", "--port", "8000"]
