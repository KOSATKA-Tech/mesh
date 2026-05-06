FROM python:3.11-slim

WORKDIR /app

# Build context is the repository root so the entire ``uv`` workspace
# (master/, agent/, sdk/, cli/) plus the top-level ``ansible/`` tree are
# available inside the image. The previous Dockerfile shelled out to a
# requirements.txt that didn't actually exist in the repo, so the image
# wouldn't build at all — switching to uv picks up the lockfile and
# resolves through pyproject.toml directly.
RUN pip install --no-cache-dir uv

COPY pyproject.toml uv.lock README.md /app/
COPY master /app/master
COPY agent /app/agent
COPY sdk /app/sdk
COPY cli /app/cli
COPY ansible /app/ansible

# ``--frozen`` honours uv.lock, ``--no-dev`` drops the test/lint extras.
# Workspace install pulls in the master package and its asyncpg / aiosqlite
# dependencies in one shot.
RUN uv sync --frozen --no-dev

ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONPATH=/app/master
ENV KOSATKA_ANSIBLE_DIR=/app/ansible

EXPOSE 8000

CMD ["uvicorn", "kosatka_master.main:app", "--host", "0.0.0.0", "--port", "8000"]
