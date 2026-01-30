# SPDX-FileCopyrightText: 2025 Purdue University
# SPDX-License-Identifier: MIT

"""Filesystem tools for directory listing and file operations."""

# Type annotations
from __future__ import annotations
from typing import List, Optional

# Standard libs
from dataclasses import dataclass

# Internal libs
from rcac_mcp.tools import mcp_tool
from rcac_mcp.context import get_executor


@dataclass
class FileInfo:
    """Information about a file or directory entry."""

    name: str
    path: str
    is_dir: bool
    size: int
    permissions: str
    owner: str
    group: str
    modified: str


@mcp_tool
def list_directory(
    path: str = '.',
    show_hidden: bool = False,
) -> List[FileInfo]:
    """
    List contents of a directory.

    Args:
        path: Directory path to list (supports ~ expansion). Defaults to current directory.
        show_hidden: Whether to include hidden files (starting with .).

    Returns:
        List of FileInfo objects with details about each entry.

    Examples:
        list_directory()
        list_directory("~/projects")
        list_directory("/tmp", show_hidden=True)
    """
    executor = get_executor()

    # Use ls with consistent output format
    # -l for long format, -a for all (if show_hidden), --time-style for consistent date
    flags = '-l --time-style=long-iso'
    if show_hidden:
        flags += 'a'

    result = executor.run(f'ls {flags} {path}')

    if result.exit_code != 0:
        raise RuntimeError(f'Failed to list directory: {result.stderr}')

    entries: List[FileInfo] = []
    lines = result.stdout.strip().split('\n')

    for line in lines:
        # Skip the "total" line and empty lines
        if not line or line.startswith('total'):
            continue

        # Parse ls -l output: perms links owner group size date time name
        parts = line.split(None, 7)
        if len(parts) < 8:
            continue

        perms, _, owner, group, size_str, date, time, name = parts

        # Determine if directory from permissions
        is_dir = perms.startswith('d')

        # Build absolute path
        # First resolve ~ in the input path
        if path.startswith('~'):
            # Get home directory from remote
            home_result = executor.run('echo $HOME')
            home = home_result.stdout.strip()
            resolved_path = path.replace('~', home, 1)
        else:
            resolved_path = path

        # Make absolute if not already
        if not resolved_path.startswith('/'):
            pwd_result = executor.run('pwd')
            pwd = pwd_result.stdout.strip()
            resolved_path = f'{pwd}/{resolved_path}'

        # Clean up path
        resolved_path = resolved_path.rstrip('/')
        full_path = f'{resolved_path}/{name}'

        entries.append(FileInfo(
            name=name,
            path=full_path,
            is_dir=is_dir,
            size=int(size_str),
            permissions=perms,
            owner=owner,
            group=group,
            modified=f'{date} {time}',
        ))

    return entries


@mcp_tool
def read_file(
    path: str,
    encoding: str = 'utf-8',
    max_size: Optional[int] = None,
) -> str:
    """
    Read contents of a file.

    Args:
        path: Path to the file (supports ~ expansion).
        encoding: Character encoding (default: utf-8).
        max_size: Maximum bytes to read. If None, reads entire file.

    Returns:
        The file contents as a string.

    Examples:
        read_file("~/.bashrc")
        read_file("/etc/hostname")
        read_file("large_file.log", max_size=10000)
    """
    executor = get_executor()

    if max_size:
        # Use head to limit bytes read
        result = executor.run(f'head -c {max_size} {path}')
    else:
        result = executor.run(f'cat {path}')

    if result.exit_code != 0:
        raise RuntimeError(f'Failed to read file: {result.stderr}')

    return result.stdout


@mcp_tool
def write_file(
    path: str,
    content: str,
    append: bool = False,
    create_dirs: bool = False,
) -> None:
    """
    Write content to a file.

    Args:
        path: Path to the file (supports ~ expansion).
        content: Content to write.
        append: If True, append to file instead of overwriting.
        create_dirs: If True, create parent directories if they don't exist.

    Examples:
        write_file("~/output.txt", "Hello, World!")
        write_file("~/log.txt", "New entry\\n", append=True)
        write_file("~/new/path/file.txt", "content", create_dirs=True)
    """
    executor = get_executor()

    if create_dirs:
        # Create parent directories
        result = executor.run(f'mkdir -p "$(dirname {path})"')
        if result.exit_code != 0:
            raise RuntimeError(f'Failed to create directories: {result.stderr}')

    # Use cat with heredoc to write content safely
    # This handles special characters better than echo
    operator = '>>' if append else '>'
    # Escape any EOF in the content
    safe_content = content.replace("'", "'\"'\"'")
    cmd = f"cat {operator} {path} << 'RCAC_MCP_EOF'\n{content}\nRCAC_MCP_EOF"

    result = executor.run(cmd)

    if result.exit_code != 0:
        raise RuntimeError(f'Failed to write file: {result.stderr}')
