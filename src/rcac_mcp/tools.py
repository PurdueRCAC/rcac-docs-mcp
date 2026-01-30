# SPDX-FileCopyrightText: 2025 Purdue University
# SPDX-License-Identifier: MIT

"""Tool definitions."""


# Type annotations
from __future__ import annotations
from typing import List, Final, Callable, Any

# External libs
from fastmcp.tools import Tool

# Public interface
__all__ = ['TOOL_REGISTRY']


# Pre-computed digits of pi (first 100 decimal digits)
PI_DIGITS: Final[str] = '14159265358979323846264338327950288419716939937510582097494459230781640628620899862803482534211706'


# Registry of tool functions for us to add to server later
TOOL_REGISTRY: List[Tool] = []


def mcp_tool(func: Callable[..., Any]) -> Tool:
    """Decorator to register MCP tool functions."""
    tool = Tool.from_function(func)
    TOOL_REGISTRY.append(tool)
    return tool


# Register tools
@mcp_tool
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


@mcp_tool
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
