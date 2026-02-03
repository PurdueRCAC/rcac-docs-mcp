# SPDX-FileCopyrightText: 2025 Purdue University
# SPDX-License-Identifier: MIT

"""SSH-based command executor using Fabric."""

# Type annotations
from __future__ import annotations
from typing import Optional, Type
from types import TracebackType

# Standard libs
import time

# External libs
from fabric import Connection
from paramiko.ssh_exception import SSHException

# Internal libs
from rcac_mcp.executor.base import CommandResult

# Public interface
__all__ = ['SSHExecutor']


# Reconnection settings
MAX_RECONNECT_DELAY: float = 10.0  # Maximum delay between reconnect attempts
INITIAL_RECONNECT_DELAY: float = 0.5  # Initial delay for exponential backoff


class SSHExecutor:
    """
    Execute commands on a remote host via SSH.

    Uses Fabric's Connection which auto-loads ~/.ssh/config for host aliases,
    identity files, and proxy commands. Maintains a persistent connection with
    automatic reconnection on failure.
    """

    _host: str
    _conn: Optional[Connection]
    _connect_kwargs: dict

    def __init__(self, host: str, **connect_kwargs) -> None:
        """
        Initialize SSH executor and establish connection.

        Args:
            host: Hostname or SSH config alias to connect to.
            **connect_kwargs: Additional arguments passed to Fabric Connection
                              (e.g., user, port, connect_timeout).
        """
        self._host = host
        self._conn = None
        self._connect_kwargs = connect_kwargs
        # Establish connection immediately
        self.open()

    @property
    def hostname(self) -> str:
        """Return the configured host."""
        return self._host

    def open(self) -> None:
        """Establish SSH connection (single attempt, no retry)."""
        if self._conn is not None and self._conn.is_connected:
            return
        self._conn = Connection(self._host, **self._connect_kwargs)
        self._conn.open()

    def close(self) -> None:
        """Close the SSH connection."""
        if self._conn is not None:
            self._conn.close()
            self._conn = None

    def _ensure_connected(self) -> Connection:
        """
        Ensure connection is open, connecting with exponential backoff if necessary.

        This method lazily establishes the SSH connection on first use and
        automatically reconnects with retry logic if the connection is lost.
        """
        if self._conn is not None and self._conn.is_connected:
            return self._conn

        delay = INITIAL_RECONNECT_DELAY

        while delay <= MAX_RECONNECT_DELAY:
            try:
                self.open()
                return self._conn
            except (SSHException, OSError):
                time.sleep(delay)
                delay = min(delay * 2, MAX_RECONNECT_DELAY)

        # Final attempt after max delay
        try:
            self.open()
            return self._conn
        except (SSHException, OSError) as exc:
            raise ConnectionError(
                f'Failed to connect to {self._host} after exponential backoff: {exc}'
            ) from exc

    def run(
        self,
        command: str,
        cwd: str | None = None,
        timeout: float | None = None,
    ) -> CommandResult:
        """
        Execute a command on the remote host.

        Args:
            command: Shell command to execute.
            cwd: Working directory for command execution.
            timeout: Maximum time in seconds to wait for completion.

        Returns:
            CommandResult with stdout, stderr, exit_code, and hostname.
        """
        conn = self._ensure_connected()

        # Build command with optional cwd
        if cwd:
            # Expand ~ on remote side and cd into directory
            full_command = f'cd {cwd} && {command}'
        else:
            full_command = command

        # Execute with hide=True to capture output instead of printing
        # warn=True prevents exception on non-zero exit code
        result = conn.run(
            full_command,
            hide=True,
            warn=True,
            timeout=timeout,
        )

        return CommandResult(
            stdout=result.stdout,
            stderr=result.stderr,
            exit_code=result.exited,
            hostname=self._host,
        )

    def put(self, local_path: str, remote_path: str) -> None:
        """
        Upload a file to the remote host.

        Args:
            local_path: Path to local file.
            remote_path: Destination path on remote system.
        """
        conn = self._ensure_connected()
        conn.put(local_path, remote_path)

    def get(self, remote_path: str, local_path: str) -> None:
        """
        Download a file from the remote host.

        Args:
            remote_path: Path to file on remote system.
            local_path: Destination path on local system.
        """
        conn = self._ensure_connected()
        conn.get(remote_path, local_path)

    def __enter__(self) -> SSHExecutor:
        """Context manager entry - opens connection."""
        self.open()
        return self

    def __exit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[TracebackType],
    ) -> None:
        """Context manager exit - closes connection."""
        self.close()
