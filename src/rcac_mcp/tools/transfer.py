# SPDX-FileCopyrightText: 2025 Purdue University
# SPDX-License-Identifier: MIT

"""File transfer tools."""

# Type annotations
from __future__ import annotations

# Internal libs
from rcac_mcp.tools import mcp_tool
from rcac_mcp.context import get_executor


@mcp_tool
def upload_file(local_path: str, remote_path: str) -> str:
    """
    Upload a file from the local machine to the remote system.

    Args:
        local_path: Path to the local file.
        remote_path: Destination path on the remote system (supports ~ expansion).

    Returns:
        The absolute path of the uploaded file on the remote system.

    Examples:
        upload_file("/tmp/data.csv", "~/data/input.csv")
        upload_file("./script.py", "/home/user/scripts/run.py")
    """
    executor = get_executor()
    executor.put(local_path, remote_path)

    # Return the resolved absolute path
    result = executor.run(f'readlink -f {remote_path}')
    if result.exit_code == 0:
        return result.stdout.strip()
    return remote_path


@mcp_tool
def download_file(remote_path: str, local_path: str) -> str:
    """
    Download a file from the remote system to the local machine.

    Args:
        remote_path: Path to the file on the remote system (supports ~ expansion).
        local_path: Destination path on the local machine.

    Returns:
        The absolute path of the downloaded file on the local machine.

    Examples:
        download_file("~/results/output.csv", "/tmp/output.csv")
        download_file("/var/log/app.log", "./logs/app.log")
    """
    import os

    executor = get_executor()
    executor.get(remote_path, local_path)

    # Return the resolved absolute path
    return os.path.abspath(os.path.expanduser(local_path))
