# SPDX-FileCopyrightText: 2025 Purdue University
# SPDX-License-Identifier: MIT

"""Delegating executor that runs commands as another user via sudo."""

# Type annotations
from __future__ import annotations
from typing import Dict, Optional, Type
from types import TracebackType

# Standard libs
import os
import socket
import subprocess
import shlex

# Internal libs
from rcac_mcp.executor.base import CommandResult

# Public interface
__all__ = ['DelegatingExecutor', 'load_user_map']


def load_user_map(filepath: str) -> Dict[str, str]:
    """
    Load user mapping from a plain text file.

    File format: one mapping per line, "<id|user|email> <local-user>"

    Args:
        filepath: Path to the user mapping file.

    Returns:
        Dictionary mapping identity claims to local usernames.
    """
    user_map: Dict[str, str] = {}
    with open(filepath, 'r') as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            # Skip empty lines and comments
            if not line or line.startswith('#'):
                continue
            parts = line.split(None, 1)  # Split on first whitespace
            if len(parts) != 2:
                raise ValueError(
                    f'Invalid user map format at line {line_num}: expected "<id> <local-user>"'
                )
            identity, local_user = parts
            user_map[identity] = local_user
    return user_map


class DelegatingExecutor:
    """
    Execute commands as another user via sudo -u.

    Used when running the MCP server as root and delegating commands to
    the authenticated user based on their JWT sub or OIDC email claim.
    """

    _user_map: Dict[str, str]
    _identity: str
    _local_user: str
    _hostname: str
    _shell: str

    def __init__(self, identity: str, user_map: Dict[str, str]) -> None:
        """
        Initialize delegating executor.

        Args:
            identity: The identity claim (sub or email) from authentication.
            user_map: Dictionary mapping identity claims to local usernames.

        Raises:
            KeyError: If identity is not found in user_map.
        """
        if identity not in user_map:
            raise KeyError(f'Identity {identity!r} not found in user map')

        self._identity = identity
        self._user_map = user_map
        self._local_user = user_map[identity]
        self._hostname = socket.gethostname()
        self._shell = os.environ.get('SHELL', '/bin/sh')

    @property
    def hostname(self) -> str:
        """Return the local hostname."""
        return self._hostname

    @property
    def local_user(self) -> str:
        """Return the local user commands are delegated to."""
        return self._local_user

    def open(self) -> None:
        """No-op for delegating executor."""
        pass

    def close(self) -> None:
        """No-op for delegating executor."""
        pass

    def run(
        self,
        command: str,
        cwd: str | None = None,
        timeout: float | None = None,
    ) -> CommandResult:
        """
        Execute a command as the delegated user via sudo.

        Args:
            command: Shell command to execute.
            cwd: Working directory for command execution.
            timeout: Maximum time in seconds to wait for completion.

        Returns:
            CommandResult with stdout, stderr, exit_code, and hostname.
        """
        # Build the sudo command
        # Use sudo -u to run as the target user
        # -n for non-interactive (no password prompt)
        # -H to set HOME to target user's home
        sudo_cmd = ['sudo', '-n', '-H', '-u', self._local_user]

        # If cwd is specified, we need to cd first within the shell
        if cwd:
            cwd = os.path.expanduser(cwd)
            full_command = f'cd {shlex.quote(cwd)} && {command}'
        else:
            full_command = command

        sudo_cmd.extend([self._shell, '-c', full_command])

        try:
            result = subprocess.run(
                sudo_cmd,
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
        Copy a file to a location writable by the delegated user.

        Uses sudo to copy the file and set ownership.

        Args:
            local_path: Source path (readable by root).
            remote_path: Destination path.
        """
        local_path = os.path.expanduser(local_path)
        remote_path = os.path.expanduser(remote_path)

        # Copy file then chown to target user
        subprocess.run(
            ['sudo', '-n', 'cp', local_path, remote_path],
            check=True,
        )
        subprocess.run(
            ['sudo', '-n', 'chown', self._local_user, remote_path],
            check=True,
        )

    def get(self, remote_path: str, local_path: str) -> None:
        """
        Copy a file from a location owned by the delegated user.

        Uses sudo to read the file as the target user.

        Args:
            remote_path: Source path (owned by delegated user).
            local_path: Destination path.
        """
        remote_path = os.path.expanduser(remote_path)
        local_path = os.path.expanduser(local_path)

        # Use sudo to cat the file and write to local path
        result = subprocess.run(
            ['sudo', '-n', '-u', self._local_user, 'cat', remote_path],
            capture_output=True,
            check=True,
        )
        with open(local_path, 'wb') as f:
            f.write(result.stdout)

    def __enter__(self) -> DelegatingExecutor:
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
