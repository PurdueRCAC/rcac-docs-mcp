# SPDX-FileCopyrightText: 2025 Purdue University
# SPDX-License-Identifier: MIT

"""RCAC Docs MCP Server: Full-text search over Purdue RCAC documentation for AI agents."""


# Type annotations
from __future__ import annotations
from typing import List, Final

# Standard libs
import sys
import os
from functools import partial
from importlib.metadata import version as get_version
from platform import python_version, python_implementation

# External libs
from cmdkit.app import Application, exit_status
from cmdkit.cli import Interface
from cmdkit.logging import Logger, level_by_name, logging_styles

# Internal libs
from rcac_docs_mcp.server import create_mcp_server
from rcac_docs_mcp.site import update_site, resolve_site_path

# Public interface
__all__ = ['main', 'MCPServerApp', '__version__']
__version__ = get_version('rcac-docs-mcp')
__website__ = 'https://github.com/PurdueRCAC/rcac-docs-mcp'
__description__ = 'MCP Server for Purdue RCAC documentation: full-text docs search for AI agents.'

# Global logger
log = Logger.default(name=__name__, level=level_by_name['INFO'], **logging_styles['default'])


def print_exception(exc: Exception, status: int) -> int:
    """Log `exc` and return `status`."""
    log.critical(str(exc))
    return status


# Default configuration values
DEFAULT_HOST: Final[str] = 'localhost'
DEFAULT_PORT: Final[int] = 8000
DEFAULT_TRANSPORT: Final[str] = 'stdio'


APP_NAME = 'rcac-docs-mcp'
APP_VERSION = f'RCAC Docs MCP Server v{__version__} ({python_implementation()} {python_version()})'
APP_USAGE = f"""\
Usage:
  {APP_NAME} [-h] [-v] [-t TRANSPORT] [-H HOST] [-p PORT]
             [--update-site] [--docs-site PATH]
             [--index-docs] [--docs-path PATH] [--docs-output PATH]

  {__description__}\
"""

APP_HELP = f"""\
{APP_USAGE}

  The RCAC Docs MCP Server exposes Purdue Research Computing's documentation
  through the Model Context Protocol (MCP), enabling AI agents to search and
  read the official docs. It runs unauthenticated over stdio or HTTP.

  Transports:
    stdio     Standard I/O (default) - for local MCP clients
    http      Streamable HTTP - for hosted deployments

Options:
  -t, --transport   TRANSPORT   Transport protocol: stdio, http (default: {DEFAULT_TRANSPORT}).
  -H, --host        HOST        Bind address for HTTP (default: {DEFAULT_HOST}).
  -p, --port        PORT        Port number for HTTP (default: {DEFAULT_PORT}).
  -v, --version                 Show version and exit.
  -h, --help                    Show this message and exit.

Environment Variables:
  MCP_BASE_URL          Public URL of this server (used for absolute icon URLs).
  RCAC_DOCS_DB          Path to the docs database the server reads at query time.
  RCAC_DOCS_SITE        Path to the local RCAC-Docs checkout the indexer reads.
  RCAC_DOCS_SITE_URL    Upstream RCAC-Docs clone URL.

Site Management:
      --update-site             Clone or update the local RCAC-Docs checkout and exit.
      --docs-site   PATH        Path to the local RCAC-Docs checkout
                                (default: $RCAC_DOCS_SITE or ~/.local/share/rcac-docs-mcp/RCAC-Docs).

Documentation Indexing:
      --index-docs              Build/update the documentation search index and exit.
      --docs-path   PATH        Path to the RCAC-Docs repo root (contains main.py, mkdocs.yml, docs/).
                                Defaults to the resolved --docs-site checkout.
      --docs-output PATH        Output path for docs database (default: ~/.config/rcac-docs-mcp/docs.db).

  When --index-docs is set, the server builds the FTS5 search index from the
  RCAC-Docs repository and exits. Use --update-site first to fetch the docs.

Examples:
  {APP_NAME}                                       # Serve over stdio (local clients)
  {APP_NAME} -t http -H 0.0.0.0                    # Serve over HTTP (hosted)
  {APP_NAME} --update-site                         # Clone or update the RCAC-Docs checkout
  {APP_NAME} --index-docs                          # Build the docs index from the checkout
  {APP_NAME} --index-docs --docs-path ../RCAC-Docs # Build from an explicit repo path\
"""


class MCPServerApp(Application):
    """RCAC Docs MCP Server application."""

    interface = Interface(APP_NAME, APP_USAGE, APP_HELP)
    interface.add_argument('-v', '--version', action='version', version=APP_VERSION)
    ALLOW_NOARGS = True  # Run application even when no arguments are given

    transport: str = DEFAULT_TRANSPORT
    interface.add_argument('-t', '--transport', default=transport,
                           choices=['stdio', 'http'])

    host: str = DEFAULT_HOST
    interface.add_argument('-H', '--host', default=host)

    port: int = DEFAULT_PORT
    interface.add_argument('-p', '--port', type=int, default=port)

    update_site_flag: bool = False
    interface.add_argument('--update-site', action='store_true', dest='update_site_flag')

    docs_site: str | None = None
    interface.add_argument('--docs-site', default=docs_site)

    index_docs_flag: bool = False
    interface.add_argument('--index-docs', action='store_true', dest='index_docs_flag')

    docs_path: str | None = None
    interface.add_argument('--docs-path', default=docs_path)

    docs_output: str | None = None
    interface.add_argument('--docs-output', default=docs_output)

    log_critical = log.critical
    log_exception = log.exception
    exceptions = {
        ValueError: partial(print_exception, status=exit_status.bad_argument),
        RuntimeError: partial(print_exception, status=exit_status.runtime_error),
        Exception: partial(print_exception, status=exit_status.uncaught_exception),
    }

    def run(self) -> None:
        """Update the docs site, build the docs index, or serve over stdio/http."""
        if self.update_site_flag:
            self._run_update_site()
            return

        if self.index_docs_flag:
            self._run_index_docs()
            return

        mcp = create_mcp_server()
        if self.transport == 'stdio':
            mcp.run(transport='stdio')
        elif self.transport == 'http':
            mcp.run(transport='streamable-http', host=self.host, port=self.port)

    def _run_update_site(self) -> None:
        """Clone or update the local RCAC-Docs checkout."""
        log.info('Updating RCAC-Docs checkout')
        path = update_site(self.docs_site)
        print(f'RCAC-Docs checkout ready at: {path}')

    def _run_index_docs(self) -> None:
        """Build or update the documentation search index."""
        from rcac_docs_mcp.index import DocsIndexer, DEFAULT_DB_PATH

        docs_path = self.docs_path or resolve_site_path(self.docs_site)
        db_path = self.docs_output or DEFAULT_DB_PATH

        # Create output directory if it doesn't exist
        db_dir = os.path.dirname(db_path)
        if db_dir:
            os.makedirs(db_dir, exist_ok=True)

        log.info('Building docs index from %s', docs_path)
        log.info('Output: %s', db_path)

        indexer = DocsIndexer(docs_path)
        stats = indexer.build(db_path)

        print(f'Documentation index built successfully:')
        print(f'  Indexed:   {stats["indexed"]} documents ({stats["chunks"]} chunks)')
        print(f'  Skipped:   {stats["skipped"]} unchanged')
        print(f'  Removed:   {stats["removed"]} stale')


def main(argv: List[str] | None = None) -> int:
    """Entry point for the rcac-docs-mcp server."""
    return MCPServerApp.main(argv or sys.argv[1:])
