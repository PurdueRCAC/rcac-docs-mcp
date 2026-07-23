# syntax=docker/dockerfile:1
# SPDX-FileCopyrightText: 2025 Purdue University
# SPDX-License-Identifier: MIT

# =============================================================================
# Builder — resolve the locked dependencies and install the project into a
# self-contained virtual environment using uv. Nothing from this stage reaches
# the final image except the built /app/.venv.
# =============================================================================
FROM python:3.14-slim AS builder

# Bring in the uv/uvx static binaries from their published image.
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /usr/local/bin/

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=0

WORKDIR /app

# 1) Install only third-party dependencies first, keyed on the lockfile so this
#    (slow) layer stays cached across source-only changes.
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --frozen --no-dev --no-install-project --no-editable

# 2) Copy the source and install the project itself (non-editable, so the
#    runtime needs only the venv — the wheel carries schema.sql and the icon).
COPY . /app
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --no-editable

# =============================================================================
# Runtime — slim image carrying just git + the built venv, run as non-root.
# =============================================================================
FROM python:3.14-slim AS runtime

# `git` is a *runtime* dependency: on startup the server clones / pulls the
# RCAC-Docs repository (--update-site) via subprocess; ca-certificates lets it
# clone over HTTPS.
RUN apt-get update \
    && apt-get install -y --no-install-recommends git ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Unprivileged runtime user (fixed high UID/GID suits k8s runAsNonRoot).
RUN groupadd --gid 10001 app \
    && useradd --uid 10001 --gid app --home-dir /home/app --create-home app

# Copy the fully-built virtual environment from the builder.
COPY --from=builder --chown=app:app /app/.venv /app/.venv

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    # Site container (docs checkout at repo/ + SQLite index.db); rebuilt on
    # every start, so it is intentionally ephemeral.
    RCAC_DOCS_SITE=/data \
    HOST=0.0.0.0 \
    PORT=8000

# Writable, ephemeral site directory owned by the runtime user.
RUN mkdir -p /data && chown app:app /data

COPY docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh
RUN chmod 0755 /usr/local/bin/docker-entrypoint.sh

USER app
WORKDIR /app

EXPOSE 8000

# The favicon custom route returns 200 on a plain GET — a cheap liveness signal
# that the HTTP server is actually serving (the /mcp endpoint needs a handshake,
# so it can't be probed naively). Uses stdlib urllib to avoid shipping curl.
HEALTHCHECK --interval=30s --timeout=5s --start-period=90s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/static/purdue-favicon.ico').read()" || exit 1

# update-site -> index -> serve. See docker-entrypoint.sh.
ENTRYPOINT ["docker-entrypoint.sh"]
