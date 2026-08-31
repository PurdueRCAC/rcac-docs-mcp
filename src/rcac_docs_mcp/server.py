# SPDX-FileCopyrightText: 2025 Purdue University
# SPDX-License-Identifier: MIT

"""Create MCP server instance."""


# Type annotations
from __future__ import annotations
from typing import Dict, Final, Callable, Awaitable

# Standard libs
from pathlib import Path
import os

# External libs
from fastmcp import FastMCP
from mcp.types import Icon, Request
from starlette.responses import Response, FileResponse

# Internal libs
from rcac_docs_mcp.tools import TOOL_REGISTRY

# Public interface
__all__ = [
    'create_mcp_server'
]


# Base URL for constructing absolute URLs (icons, etc.)
MCP_BASE_URL = os.environ.get('MCP_BASE_URL', '').rstrip('/')


# Registry for custom routes handled by the server
CUSTOM_ROUTES: Dict[str, Callable[[Request], Awaitable[Response]]] = {}


def custom_route(route: str):
    """Decorator to register custom route handlers."""

    def decorator(func: Callable[[Request], Awaitable[Response]]) -> Callable[[Request], Awaitable[Response]]:
        CUSTOM_ROUTES[route] = func
        return func

    return decorator



# Path to static files directory
STATIC_DIR: Final[Path] = Path(__file__).parent / 'static'
ICON_PATH: Final[Path] = STATIC_DIR / 'purdue-favicon.ico'


ICON_URL = f'{MCP_BASE_URL}/static/purdue-favicon.ico' if MCP_BASE_URL else '/static/purdue-favicon.ico'


# Serve the icon via custom route
@custom_route("/static/purdue-favicon.ico")
async def serve_icon(request: Request) -> FileResponse:
    return FileResponse(ICON_PATH, media_type="image/x-icon")


SERVER_INSTRUCTIONS: Final[str] = """\
RCAC Docs MCP Server provides full-text search over Purdue Research
Computing's official documentation (user guides, software catalog,
datasets, blog posts, and workshops).

IMPORTANT — Documentation Search:
Before advising users on storage policies, job submission, software
usage, or any RCAC-specific topic, use `doc_search` to check the
official RCAC documentation. This prevents outdated or incorrect advice.
After finding a relevant result, use `doc_load` to read the full page.

Tools:
- doc_search: Search RCAC documentation (user guides, software catalog,
  datasets, blog posts, workshops). Keep queries to 2-3 key terms, not
  full sentences. A query with no operator in it is broadened for you:
  stopwords are dropped and the remaining terms are OR-joined and
  prefix-matched, which is recall-heavy enough that most plain queries
  fill all 20 result slots. Any FTS5 operator turns normalization off and
  runs the query verbatim. That is how you narrow: "job array" for an
  exact phrase, gilbreth AND fortress when both terms must appear, NOT to
  exclude, NEAR(scratch purge, 5) for proximity. The index is
  Porter-stemmed, so gpu/gpus and purge/purged already match each other
  and * is rarely needed. Narrow by path with the optional category
  filter: userguides, software, datasets, blog, workshops, or a deeper
  prefix such as userguides/gilbreth, which is sharper still.
- doc_load: Load the full content of a documentation page by its path
  (as shown in doc_search results). Use after identifying a relevant
  document to read it in full.\
"""


def create_mcp_server() -> FastMCP:
    """
    Create and configure the MCP server.

    Returns:
        Configured FastMCP server instance.
    """
    server = FastMCP(
        name='RCAC Docs',
        instructions=SERVER_INSTRUCTIONS,
        icons=[
            Icon(
                src=ICON_URL,
                mimeType="image/x-icon",
            ),
        ],
    )

    for route, impl in CUSTOM_ROUTES.items():
        server.custom_route(route, methods=['GET'])(impl)

    for tool in TOOL_REGISTRY:
        server.add_tool(tool)

    return server
