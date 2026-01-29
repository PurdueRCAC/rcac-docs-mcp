# SPDX-FileCopyrightText: 2025 Purdue University
# SPDX-License-Identifier: MIT

"""RCAC MCP Server implementation."""

from __future__ import annotations
from typing import Optional
from pathlib import Path
import os

from fastmcp import FastMCP
from fastmcp.server.auth.providers.jwt import JWTVerifier
from mcp.types import Icon
from starlette.requests import Request
from starlette.responses import FileResponse

from rcac_mcp.token import ISSUER, AUDIENCE, ALGORITHM

# Path to static files directory
STATIC_DIR = Path(__file__).parent / "static"
LOGO_PATH = STATIC_DIR / "purdue-logo.svg"

__all__ = ['mcp', 'create_mcp_server']

# Pre-computed digits of pi (first 100 decimal digits)
PI_DIGITS = "14159265358979323846264338327950288419716939937510582097494459230781640628620899862803482534211706"


def create_auth_provider(auth_mode: str) -> Optional[JWTVerifier]:
    """Create authentication provider based on mode."""
    if auth_mode == 'none':
        return None

    if auth_mode == 'jwt':
        secret = os.environ.get('JWT_SECRET')
        if not secret:
            raise ValueError("JWT_SECRET environment variable required for jwt auth mode")
        if len(secret) < 32:
            raise ValueError("JWT_SECRET must be at least 32 characters")
        return JWTVerifier(
            public_key=secret,
            issuer=ISSUER,
            audience=AUDIENCE,
            algorithm=ALGORITHM,
        )

    if auth_mode == 'oidc':
        # Import here to avoid dependency when not using OIDC
        from fastmcp.server.auth.oidc_proxy import OIDCProxy

        config_url = os.environ.get('OIDC_CONFIG_URL')
        client_id = os.environ.get('OIDC_CLIENT_ID')
        client_secret = os.environ.get('OIDC_CLIENT_SECRET')
        base_url = os.environ.get('MCP_BASE_URL')

        if not all([config_url, client_id, client_secret, base_url]):
            raise ValueError(
                "OIDC auth requires: OIDC_CONFIG_URL, OIDC_CLIENT_ID, "
                "OIDC_CLIENT_SECRET, MCP_BASE_URL"
            )

        return OIDCProxy(
            config_url=config_url,
            client_id=client_id,
            client_secret=client_secret,
            base_url=base_url,
        )

    raise ValueError(f"Unknown auth mode: {auth_mode}")


def create_mcp_server(auth_mode: str = 'none') -> FastMCP:
    """Create and configure the MCP server."""
    auth = create_auth_provider(auth_mode)

    server = FastMCP(
        name="RCAC",
        instructions="""
        RCAC MCP Server provides tools for interacting with Purdue's
        Research Computing resources and HPC clusters.

        Currently provides example mathematical tools for testing.
        """,
        auth=auth,
        icons=[
            Icon(
                src="/static/purdue-logo.svg",
                mimeType="image/svg+xml",
            ),
        ],
    )

    # Serve the logo via custom route
    @server.custom_route("/static/purdue-logo.svg", methods=["GET"])
    async def serve_logo(request: Request) -> FileResponse:
        return FileResponse(LOGO_PATH, media_type="image/svg+xml")

    # Register tools
    @server.tool
    def nth_prime(n: int) -> int:
        """
        Compute the n-th prime number (1-indexed).

        Args:
            n: Which prime to compute (1 = first prime = 2).

        Returns:
            The n-th prime number.

        Examples:
            nth_prime(1) -> 2
            nth_prime(5) -> 11
            nth_prime(100) -> 541
        """
        if n < 1:
            raise ValueError("n must be at least 1")
        if n > 10000:
            raise ValueError("n must be at most 10000 (for performance)")

        primes = []
        candidate = 2
        while len(primes) < n:
            is_prime = True
            for p in primes:
                if p * p > candidate:
                    break
                if candidate % p == 0:
                    is_prime = False
                    break
            if is_prime:
                primes.append(candidate)
            candidate += 1
        return primes[-1]

    @server.tool
    def pi_digit(n: int) -> int:
        """
        Return the n-th digit of pi after the decimal point.

        Args:
            n: Which digit to return (1-indexed, 1 = first digit after decimal = 1).

        Returns:
            The n-th digit of pi after the decimal point.

        Examples:
            pi_digit(1) -> 1  (pi = 3.14159...)
            pi_digit(2) -> 4
            pi_digit(10) -> 5
        """
        if n < 1:
            raise ValueError("n must be at least 1")
        if n > len(PI_DIGITS):
            raise ValueError(f"n must be at most {len(PI_DIGITS)}")

        return int(PI_DIGITS[n - 1])

    return server


# Default server instance (no auth)
mcp = create_mcp_server('none')
