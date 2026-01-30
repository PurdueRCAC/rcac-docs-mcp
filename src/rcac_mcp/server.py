# SPDX-FileCopyrightText: 2025 Purdue University
# SPDX-License-Identifier: MIT

"""Create MCP server instance."""


# Type annotations
from __future__ import annotations
from typing import Dict, Optional, Final, Callable, Awaitable

# Standard libs
from pathlib import Path
import os

# External libs
from fastmcp import FastMCP
from mcp.types import Icon, Request
from starlette.responses import Response, FileResponse

# Internal libs
from rcac_mcp.auth import AUTH_MODES
from rcac_mcp.tools import TOOL_REGISTRY

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
RCAC MCP Server provides tools for interacting with Purdue's
Research Computing resources and HPC clusters.

Currently provides example mathematical tools for testing.\
"""


def create_mcp_server(auth_mode: Optional[str] = None) -> FastMCP:
    """Create and configure the MCP server."""

    server = FastMCP(
        name='RCAC',
        instructions=SERVER_INSTRUCTIONS,
        auth=AUTH_MODES[auth_mode](),
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
