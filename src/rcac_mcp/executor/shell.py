# SPDX-FileCopyrightText: 2025 Purdue University
# SPDX-License-Identifier: MIT

"""Local shell command executor."""

# Type annotations
from __future__ import annotations
from typing import Optional, Type
from types import TracebackType

# Standard libs
import os
import shutil
import socket
import subprocess

# Internal libs
from rcac_mcp.executor.base import CommandResult

# Public interface
__all__ = ['LocalShellExecutor']


class LocalShellExecutor:
    """
    Execute commands locally via subprocess.

    Uses $SHELL for command execution, falling back to /bin/sh if not set.
    """

    _hostname: str
    _shell: str

    def __init__(self) -> None:
        """Initialize local shell executor."""
        self._hostname = socket.gethostname()
        self._shell = os.environ.get('SHELL', '/bin/sh')

    @property
    def hostname(self) -> str:
        """Return the local hostname."""
        return self._hostname

    def open(self) -> None:
        """No-op for local executor."""
        pass

    def close(self) -> None:
        """No-op for local executor."""
        pass

    def run(
        self,
        command: str,
        cwd: str | None = None,
        timeout: float | None = None,
    ) -> CommandResult:
        """
        Execute a command locally.

        Args:
            command: Shell command to execute.
            cwd: Working directory for command execution.
            timeout: Maximum time in seconds to wait for completion.

        Returns:
            CommandResult with stdout, stderr, exit_code, and hostname.
        """
        # Expand ~ in cwd if provided
        if cwd:
            cwd = os.path.expanduser(cwd)

        try:
            result = subprocess.run(
                [self._shell, '-c', command],
                cwd=cwd,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            return CommandResult(
                stdout=result.stdout,
                stderr=result.stderr,
                exit_code=result.returncode,
                hostname=self._hostname,
            )
        except subprocess.TimeoutExpired as exc:
            return CommandResult(
                stdout=exc.stdout or '',
                stderr=exc.stderr or f'Command timed out after {timeout}s',
                exit_code=-1,
                hostname=self._hostname,
            )

    def put(self, local_path: str, remote_path: str) -> None:
        """
        Copy a file locally (local_path -> remote_path).

        For local executor, this is just a file copy.

        Args:
            local_path: Source path.
            remote_path: Destination path.
        """
        local_path = os.path.expanduser(local_path)
        remote_path = os.path.expanduser(remote_path)
        shutil.copy2(local_path, remote_path)

    def get(self, remote_path: str, local_path: str) -> None:
        """
        Copy a file locally (remote_path -> local_path).

        For local executor, this is just a file copy.

        Args:
            remote_path: Source path.
            local_path: Destination path.
        """
        remote_path = os.path.expanduser(remote_path)
        local_path = os.path.expanduser(local_path)
        shutil.copy2(remote_path, local_path)

    def __enter__(self) -> LocalShellExecutor:
        """Context manager entry."""
        self.open()
        return self

    def __exit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[TracebackType],
    ) -> None:
        """Context manager exit."""
        self.close()
