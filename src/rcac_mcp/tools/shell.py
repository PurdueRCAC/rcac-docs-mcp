# SPDX-FileCopyrightText: 2025 Purdue University
# SPDX-License-Identifier: MIT

"""Shell command execution tools."""

# Type annotations
from __future__ import annotations
from typing import Optional

# Internal libs
from rcac_mcp.tools import mcp_tool
from rcac_mcp.context import get_executor
from rcac_mcp.executor import CommandResult


@mcp_tool
def run_command(
    command: str,
    cwd: Optional[str] = None,
    timeout: Optional[float] = None,
) -> CommandResult:
    """
    Execute a shell command on the remote system.

    Args:
        command: The shell command to execute.
        cwd: Working directory for command execution (supports ~ expansion).
        timeout: Maximum time in seconds to wait for completion.

    Returns:
        CommandResult containing stdout, stderr, exit_code, and hostname.

    Examples:
        run_command("ls -la")
        run_command("pwd", cwd="~/projects")
        run_command("sleep 5", timeout=10)
    """
    executor = get_executor()
    return executor.run(command, cwd=cwd, timeout=timeout)
