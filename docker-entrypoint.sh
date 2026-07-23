#!/usr/bin/env sh
# SPDX-FileCopyrightText: 2025 Purdue University
# SPDX-License-Identifier: MIT
#
# Container entrypoint. Refresh the RCAC-Docs checkout and rebuild the search
# index, then serve the MCP server over streamable HTTP.
#
# Running update-site + index on *every* start is deliberate: a Kubernetes
# rolling restart (triggered by a new image OR by newer upstream docs) always
# comes up with a freshly built index before ingress is handed over. If either
# step fails, `set -e` aborts before serving, so the new pod never becomes
# ready and the old one keeps taking traffic.

set -eu

# Escape hatch for ops/debugging: `docker run <image> <cmd...>` runs it verbatim
# (e.g. `... sh`, or `... rcac-docs-mcp --help`) instead of the serve sequence.
if [ "$#" -gt 0 ]; then
    exec "$@"
fi

echo "[entrypoint] Updating RCAC-Docs checkout (--update-site)"
rcac-docs-mcp --update-site

echo "[entrypoint] Building search index (--index)"
rcac-docs-mcp --index

echo "[entrypoint] Serving over HTTP on ${HOST:-0.0.0.0}:${PORT:-8000} (path /mcp)"
exec rcac-docs-mcp --transport http --host "${HOST:-0.0.0.0}" --port "${PORT:-8000}"
