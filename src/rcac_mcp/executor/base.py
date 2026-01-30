# SPDX-FileCopyrightText: 2025 Purdue University
# SPDX-License-Identifier: MIT

"""Base executor protocol and result types."""

# Type annotations
from __future__ import annotations
from typing import Protocol, runtime_checkable

# Standard libs
from dataclasses import dataclass

# Public interface
__all__ = ['Executor', 'CommandResult']


@dataclass
class CommandResult:
    """Result of a command execution."""

    stdout: str
    stderr: str
    exit_code: int
    hostname: str


@runtime_checkable
class Executor(Protocol):
    """Protocol for command execution backends."""

    @property
    def hostname(self) -> str:
        """Return the hostname where commands are executed."""
        ...

    def run(
        self,
        command: str,
        cwd: str | None = None,
        timeout: float | None = None,
    ) -> CommandResult:
        """
        Execute a shell command.

        Args:
            command: Shell command to execute.
            cwd: Working directory for command execution.
            timeout: Maximum time in seconds to wait for completion.

        Returns:
            CommandResult with stdout, stderr, exit_code, and hostname.
        """
        ...

    def put(self, local_path: str, remote_path: str) -> None:
        """
        Transfer a file from local to remote.

        Args:
            local_path: Path to local file.
            remote_path: Destination path on remote system.
        """
        ...

    def get(self, remote_path: str, local_path: str) -> None:
        """
        Transfer a file from remote to local.

        Args:
            remote_path: Path to file on remote system.
            local_path: Destination path on local system.
        """
        ...

    def open(self) -> None:
        """Open the connection (if applicable)."""
        ...

    def close(self) -> None:
        """Close the connection and release resources."""
        ...

    def __enter__(self) -> Executor:
        """Context manager entry."""
        ...

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit."""
        ...
