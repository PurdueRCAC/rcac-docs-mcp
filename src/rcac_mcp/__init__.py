# SPDX-FileCopyrightText: 2025 Purdue University
# SPDX-License-Identifier: MIT

"""RCAC MCP Server: Enables agentic development with HPC clusters and storage services."""

from __future__ import annotations
from typing import List
import sys
import os
from functools import partial
from importlib.metadata import version as get_version
from platform import python_version, python_implementation

from cmdkit.app import Application, exit_status
from cmdkit.cli import Interface
from cmdkit.logging import Logger, level_by_name, logging_styles

from rcac_mcp.server import mcp, create_mcp_server
from rcac_mcp.token import generate_token

__all__ = ['mcp', 'main', 'MCPServerApp', '__version__']

try:
    __version__ = get_version('rcac-mcp')
except Exception:
    __version__ = '0.1.0'

__website__ = 'https://github.com/purduercac/rcac-mcp'
__description__ = 'MCP Server for Purdue RCAC: HPC clusters and storage services for AI agents.'


log = Logger.default(name=__name__, level=level_by_name['INFO'], **logging_styles['default'])


def print_exception(exc: Exception, status: int) -> int:
    """Log `exc` and return `status`."""
    log.critical(str(exc))
    return status


# Default configuration values
DEFAULT_HOST = 'localhost'
DEFAULT_PORT = 8000
DEFAULT_TRANSPORT = 'stdio'
DEFAULT_AUTH = 'none'
DEFAULT_LIFETIME = 3600

APP_NAME = 'rcac-mcp'
APP_VERSION = f'RCAC MCP Server v{__version__} ({python_implementation()} {python_version()})'
APP_USAGE = f"""\
Usage:
  {APP_NAME} [-h] [-v] [-t TRANSPORT] [-H HOST] [-p PORT] [-a AUTH] [--generate-token] [--lifetime SECONDS]

  {__description__}\
"""

APP_HELP = f"""\
{APP_USAGE}

  The RCAC MCP Server exposes Purdue Research Computing resources through the
  Model Context Protocol (MCP), enabling AI agents to interact with HPC clusters
  and storage services.

  Transports:
    stdio     Standard I/O (default) - for local MCP clients
    sse       Server-Sent Events over HTTP - for web-based clients
    http      Streamable HTTP - for production deployments

  Authentication:
    none      No authentication (default) - for local development
    jwt       JWT with symmetric key (HS256) - requires JWT_SECRET env var
    oidc      OIDC proxy - requires OIDC_* env vars

Options:
  -t, --transport   TRANSPORT   Transport protocol: stdio, sse, http (default: {DEFAULT_TRANSPORT}).
  -H, --host        HOST        Bind address for HTTP/SSE (default: {DEFAULT_HOST}).
  -p, --port        PORT        Port number for HTTP/SSE (default: {DEFAULT_PORT}).
  -a, --auth        AUTH        Authentication mode: none, jwt, oidc (default: {DEFAULT_AUTH}).
      --generate-token          Generate a JWT token and exit (requires JWT_SECRET).
      --lifetime    SECONDS     Token lifetime in seconds (default: {DEFAULT_LIFETIME}).
  -v, --version                 Show version and exit.
  -h, --help                    Show this message and exit.

Environment Variables:
  JWT_SECRET          Shared secret for JWT signing (min 32 chars, required for jwt auth).
  OIDC_CONFIG_URL     OIDC provider discovery URL (required for oidc auth).
  OIDC_CLIENT_ID      OAuth client ID (required for oidc auth).
  OIDC_CLIENT_SECRET  OAuth client secret (required for oidc auth).
  MCP_BASE_URL        Public URL of this server (required for oidc auth).

Examples:
  {APP_NAME}                              # Run with stdio transport, no auth
  {APP_NAME} -t http -p 8080              # Run HTTP server on port 8080
  {APP_NAME} -a jwt -t http               # Run with JWT auth over HTTP
  {APP_NAME} --generate-token             # Generate a JWT token\
"""


class MCPServerApp(Application):
    """RCAC MCP Server application."""

    interface = Interface(APP_NAME, APP_USAGE, APP_HELP)
    interface.add_argument('-v', '--version', action='version', version=APP_VERSION)

    transport: str = DEFAULT_TRANSPORT
    interface.add_argument('-t', '--transport', default=transport,
                           choices=['stdio', 'sse', 'http'])

    host: str = DEFAULT_HOST
    interface.add_argument('-H', '--host', default=host)

    port: int = DEFAULT_PORT
    interface.add_argument('-p', '--port', type=int, default=port)

    auth: str = DEFAULT_AUTH
    interface.add_argument('-a', '--auth', default=auth,
                           choices=['none', 'jwt', 'oidc'])

    generate_token_flag: bool = False
    interface.add_argument('--generate-token', action='store_true', dest='generate_token_flag')

    lifetime: int = DEFAULT_LIFETIME
    interface.add_argument('--lifetime', type=int, default=lifetime)

    log_critical = log.critical
    log_exception = log.exception
    exceptions = {
        ValueError: partial(print_exception, status=exit_status.bad_argument),
        RuntimeError: partial(print_exception, status=exit_status.runtime_error),
        Exception: partial(print_exception, status=exit_status.uncaught_exception),
    }

    def run(self) -> None:
        """Run the MCP server or generate token."""
        # Handle token generation
        if self.generate_token_flag:
            secret = os.environ.get('JWT_SECRET')
            if not secret:
                raise ValueError("JWT_SECRET environment variable required for token generation")
            if len(secret) < 32:
                raise ValueError("JWT_SECRET must be at least 32 characters")
            token = generate_token(secret, self.lifetime)
            print(token)
            return

        # Create server with auth
        server = create_mcp_server(self.auth)

        # Run with appropriate transport
        if self.transport == 'stdio':
            server.run(transport='stdio')
        elif self.transport == 'sse':
            server.run(transport='sse', host=self.host, port=self.port)
        elif self.transport == 'http':
            server.run(transport='streamable-http', host=self.host, port=self.port)


def main(argv: List[str] | None = None) -> int:
    """Entry point for the rcac-mcp server."""
    return MCPServerApp.main(argv or sys.argv[1:])
