# SPDX-FileCopyrightText: 2025 Purdue University
# SPDX-License-Identifier: MIT

"""RCAC-specific HPC cluster tools.

These tools wrap custom RCAC commands that are not part of standard Slurm.
They provide information about storage quotas, job details, partitions,
and queue statistics specific to Purdue's Research Computing clusters.
"""

# Type annotations
from __future__ import annotations
from typing import Optional

# Internal libs
from rcac_mcp.tools import mcp_tool
from rcac_mcp.context import get_executor


def _validate_job_id(job_id: int) -> None:
    """Validate that job_id is a positive integer."""
    if not isinstance(job_id, int) or job_id <= 0:
        raise ValueError(f'job_id must be a positive integer, got: {job_id}')


@mcp_tool
def myquota() -> str:
    """
    Show storage spaces, usage, and quotas for the current user.

    Displays all storage locations the user has access to (home, scratch,
    depot, etc.) along with current usage and quota limits. Use this to
    discover where data can be read/written.

    Returns:
        Storage quota information showing type, location, size, limit,
        usage percentage, file counts, and file limits.

    Examples:
        myquota()
    """
    executor = get_executor()
    result = executor.run('myquota')

    if result.exit_code != 0:
        raise RuntimeError(f'Failed to get quota info: {result.stderr}')

    return result.stdout


@mcp_tool
def jobinfo(job_id: int) -> str:
    """
    Get detailed information about a Slurm job.

    Shows job parameters including name, user, account, partition, nodes,
    cores, GPUs, state, exit code, timestamps, and resource usage.

    Args:
        job_id: The Slurm job ID to query.

    Returns:
        Detailed job information in key-value format.

    Examples:
        jobinfo(19804935)
    """
    _validate_job_id(job_id)
    executor = get_executor()
    result = executor.run(f'jobinfo {job_id}')

    if result.exit_code != 0:
        raise RuntimeError(f'Failed to get job info: {result.stderr}')

    return result.stdout


@mcp_tool
def jobcmd(job_id: int) -> str:
    """
    Get the command that was submitted for a Slurm job.

    Shows the actual command line or script invocation used when
    the job was submitted.

    Args:
        job_id: The Slurm job ID to query.

    Returns:
        The command that was submitted for the job.

    Examples:
        jobcmd(19804935)
    """
    _validate_job_id(job_id)
    executor = get_executor()
    result = executor.run(f'jobcmd {job_id}')

    if result.exit_code != 0:
        raise RuntimeError(f'Failed to get job command: {result.stderr}')

    return result.stdout


@mcp_tool
def jobenv(job_id: int) -> str:
    """
    Get the environment variables for a Slurm job.

    Shows all environment variables that were set when the job
    was submitted or that Slurm set for the job.

    Args:
        job_id: The Slurm job ID to query.

    Returns:
        Environment variables for the job, one per line.

    Examples:
        jobenv(19804935)
    """
    _validate_job_id(job_id)
    executor = get_executor()
    result = executor.run(f'jobenv {job_id}')

    if result.exit_code != 0:
        raise RuntimeError(f'Failed to get job environment: {result.stderr}')

    return result.stdout


@mcp_tool
def jobscript(job_id: int) -> str:
    """
    Get the full submission script for a Slurm job.

    Returns the complete batch script that was submitted, including
    all SBATCH directives and commands.

    Args:
        job_id: The Slurm job ID to query.

    Returns:
        The full job submission script content.

    Examples:
        jobscript(19804935)
    """
    _validate_job_id(job_id)
    executor = get_executor()
    result = executor.run(f'jobscript {job_id}')

    if result.exit_code != 0:
        raise RuntimeError(f'Failed to get job script: {result.stderr}')

    return result.stdout


@mcp_tool
def showpartitions() -> str:
    """
    Show available partitions and their current status.

    Displays partition statistics including node counts, CPU cores,
    pending jobs, node limits, max job time, cores per node, and
    memory per node.

    Returns:
        Partition statistics table showing availability and limits.

    Examples:
        showpartitions()
    """
    executor = get_executor()
    result = executor.run('showpartitions')

    if result.exit_code != 0:
        raise RuntimeError(f'Failed to get partition info: {result.stderr}')

    return result.stdout


@mcp_tool
def average_wait(
    partition: Optional[str] = None,
    account: Optional[str] = None,
) -> str:
    """
    Show aggregate statistics of queue wait times.

    Displays wait time statistics for jobs, optionally filtered by
    partition or account.

    Args:
        partition: Filter by partition name (e.g., 'cpu', 'gpu').
        account: Filter by Slurm account.

    Returns:
        Queue wait time statistics.

    Examples:
        average_wait()
        average_wait(partition='gpu')
        average_wait(account='mylab')
    """
    executor = get_executor()

    cmd = 'average_wait'
    if partition:
        cmd += f' -p {partition}'
    if account:
        cmd += f' -A {account}'

    result = executor.run(cmd)

    if result.exit_code != 0:
        raise RuntimeError(f'Failed to get wait time stats: {result.stderr}')

    return result.stdout
