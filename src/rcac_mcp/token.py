# SPDX-FileCopyrightText: 2025 Purdue University
# SPDX-License-Identifier: MIT

"""JWT token generation for RCAC MCP Server."""

from __future__ import annotations

import jwt
from datetime import datetime, timezone, timedelta

__all__ = ['generate_token']

ISSUER = 'rcac-mcp'
AUDIENCE = 'rcac-mcp'
ALGORITHM = 'HS256'


def generate_token(secret: str, lifetime: int = 3600) -> str:
    """
    Generate a JWT token for authenticating with the MCP server.

    Args:
        secret: The shared secret key for HS256 signing.
        lifetime: Token lifetime in seconds (default: 3600 = 1 hour).

    Returns:
        Encoded JWT token string.
    """
    now = datetime.now(timezone.utc)
    payload = {
        'iss': ISSUER,
        'aud': AUDIENCE,
        'iat': now,
        'exp': now + timedelta(seconds=lifetime),
    }
    return jwt.encode(payload, secret, algorithm=ALGORITHM)
