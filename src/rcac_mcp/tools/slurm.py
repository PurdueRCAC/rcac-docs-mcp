# SPDX-FileCopyrightText: 2025 Purdue University
# SPDX-License-Identifier: MIT

"""Slurm workload manager tools.

These tools provide interfaces to standard Slurm commands for job submission,
monitoring, and cluster status queries. Also includes RCAC-specific Slurm
extensions like slist and sfeatures.
"""

# Type annotations
from __future__ import annotations
from typing import Optional, List
import re
from datetime import datetime

# Internal libs
from rcac_mcp.tools import mcp_tool
from rcac_mcp.context import get_executor


# Default directory for job scripts
DEFAULT_JOBS_DIR = '~/jobs'


def _validate_job_id(job_id: int) -> None:
    """Validate that job_id is a positive integer."""
    if not isinstance(job_id, int) or job_id <= 0:
        raise ValueError(f'job_id must be a positive integer, got: {job_id}')


def _build_args(args: List[str]) -> str:
    """Build command argument string from list, filtering None values."""
    return ' '.join(arg for arg in args if arg)


@mcp_tool
def sbatch(
    script_path: Optional[str] = None,
    script_content: Optional[str] = None,
    job_name: Optional[str] = None,
    account: Optional[str] = None,
    partition: Optional[str] = None,
    qos: Optional[str] = None,
    time: Optional[str] = None,
    nodes: Optional[int] = None,
    ntasks: Optional[int] = None,
    cpus_per_task: Optional[int] = None,
    mem: Optional[str] = None,
    gpus: Optional[str] = None,
    constraint: Optional[str] = None,
    output: Optional[str] = None,
    error: Optional[str] = None,
    extra_args: Optional[str] = None,
) -> str:
    """
    Submit a batch job to Slurm.

    Either script_path (existing file on cluster) or script_content
    (script text to write) must be provided. If script_content is given,
    the script is written to ~/jobs/<job_name>_<timestamp>.sh before submission.

    Args:
        script_path: Path to existing job script on the cluster.
        script_content: Job script content to write and submit.
        job_name: Job name (-J/--job-name). Used in script filename if writing.
        account: Slurm account to charge (-A/--account).
        partition: Partition to submit to (-p/--partition).
        qos: Quality of service (-q/--qos), e.g., 'standby'.
        time: Wall time limit (-t/--time), e.g., '01:00:00'.
        nodes: Number of nodes (-N/--nodes).
        ntasks: Number of tasks (-n/--ntasks).
        cpus_per_task: CPUs per task (-c/--cpus-per-task).
        mem: Memory per node (--mem), e.g., '4G'.
        gpus: GPU specification (--gpus), e.g., '1' or 'mi210:2'.
        constraint: Node constraint (-C/--constraint).
        output: Stdout file path (-o/--output).
        error: Stderr file path (-e/--error).
        extra_args: Additional sbatch arguments as a string.

    Returns:
        The submitted job ID as a string.

    Examples:
        sbatch(script_path='~/jobs/my_job.sh')
        sbatch(
            script_content='#!/bin/bash\\n#SBATCH -c 4\\npython train.py',
            job_name='train',
            account='mylab',
            partition='gpu',
            time='02:00:00',
        )
    """
    executor = get_executor()

    if script_path is None and script_content is None:
        raise ValueError('Either script_path or script_content must be provided')

    if script_path is not None and script_content is not None:
        raise ValueError('Provide either script_path or script_content, not both')

    # If script_content provided, write it to a file first
    if script_content is not None:
        # Ensure jobs directory exists
        executor.run(f'mkdir -p {DEFAULT_JOBS_DIR}')

        # Generate script filename
        name = job_name or 'job'
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        script_path = f'{DEFAULT_JOBS_DIR}/{name}_{timestamp}.sh'

        # Write script content
        safe_content = script_content.replace("'", "'\"'\"'")
        write_cmd = f"cat > {script_path} << 'RCAC_MCP_EOF'\n{script_content}\nRCAC_MCP_EOF"
        write_result = executor.run(write_cmd)

        if write_result.exit_code != 0:
            raise RuntimeError(f'Failed to write job script: {write_result.stderr}')

        # Make executable
        executor.run(f'chmod +x {script_path}')

    # Build sbatch command
    args = []
    if job_name:
        args.append(f'-J {job_name}')
    if account:
        args.append(f'-A {account}')
    if partition:
        args.append(f'-p {partition}')
    if qos:
        args.append(f'-q {qos}')
    if time:
        args.append(f'-t {time}')
    if nodes:
        args.append(f'-N {nodes}')
    if ntasks:
        args.append(f'-n {ntasks}')
    if cpus_per_task:
        args.append(f'-c {cpus_per_task}')
    if mem:
        args.append(f'--mem={mem}')
    if gpus:
        args.append(f'--gpus={gpus}')
    if constraint:
        args.append(f'-C {constraint}')
    if output:
        args.append(f'-o {output}')
    if error:
        args.append(f'-e {error}')
    if extra_args:
        args.append(extra_args)

    args.append(script_path)
    cmd = f'sbatch {_build_args(args)}'

    result = executor.run(cmd)

    if result.exit_code != 0:
        raise RuntimeError(f'Failed to submit job: {result.stderr}')

    # Extract job ID from output like "Submitted batch job 19804935"
    match = re.search(r'Submitted batch job (\d+)', result.stdout)
    if match:
        return match.group(1)

    return result.stdout.strip()


@mcp_tool
def squeue(
    user: Optional[str] = None,
    account: Optional[str] = None,
    partition: Optional[str] = None,
    state: Optional[str] = None,
    job_ids: Optional[List[int]] = None,
    me: bool = True,
    extra_args: Optional[str] = None,
) -> str:
    """
    View the Slurm job queue.

    By default shows only the current user's jobs (--me). Set me=False
    and provide user/account to see other jobs.

    Args:
        user: Filter by username (-u/--user).
        account: Filter by account (-A/--account).
        partition: Filter by partition (-p/--partition).
        state: Filter by job state (-t/--states), e.g., 'PENDING', 'RUNNING'.
        job_ids: Specific job IDs to query (-j/--jobs).
        me: Show only current user's jobs (default: True).
        extra_args: Additional squeue arguments.

    Returns:
        Job queue listing.

    Examples:
        squeue()
        squeue(state='PENDING')
        squeue(me=False, account='mylab')
        squeue(job_ids=[19804935, 19804936])
    """
    executor = get_executor()

    args = []

    # Default to --me unless other filters specified
    if me and not user and not account:
        args.append('--me')
    if user:
        args.append(f'-u {user}')
    if account:
        args.append(f'-A {account}')
    if partition:
        args.append(f'-p {partition}')
    if state:
        args.append(f'-t {state}')
    if job_ids:
        args.append(f'-j {",".join(str(j) for j in job_ids)}')
    if extra_args:
        args.append(extra_args)

    cmd = f'squeue {_build_args(args)}'
    result = executor.run(cmd)

    if result.exit_code != 0:
        raise RuntimeError(f'Failed to query queue: {result.stderr}')

    return result.stdout


@mcp_tool
def scancel(
    job_ids: Optional[List[int]] = None,
    user: Optional[str] = None,
    account: Optional[str] = None,
    partition: Optional[str] = None,
    state: Optional[str] = None,
    name: Optional[str] = None,
    me: bool = False,
    extra_args: Optional[str] = None,
) -> str:
    """
    Cancel Slurm jobs.

    Provide job_ids for specific jobs, or use filters to cancel matching jobs.
    Use me=True to cancel all your jobs (equivalent to scancel --me).

    Args:
        job_ids: Specific job IDs to cancel.
        user: Cancel jobs for this user (-u/--user).
        account: Cancel jobs under this account (-A/--account).
        partition: Cancel jobs in this partition (-p/--partition).
        state: Cancel jobs in this state (-t/--state).
        name: Cancel jobs with this name (-n/--name).
        me: Cancel all current user's jobs (--me).
        extra_args: Additional scancel arguments.

    Returns:
        Confirmation message or empty string on success.

    Examples:
        scancel(job_ids=[19804935])
        scancel(me=True)
        scancel(state='PENDING', account='mylab')
    """
    executor = get_executor()

    if not job_ids and not me and not user and not account and not name:
        raise ValueError('Must specify job_ids, me=True, or a filter (user/account/name)')

    args = []
    if job_ids:
        args.append(' '.join(str(j) for j in job_ids))
    if me:
        args.append('--me')
    if user:
        args.append(f'-u {user}')
    if account:
        args.append(f'-A {account}')
    if partition:
        args.append(f'-p {partition}')
    if state:
        args.append(f'-t {state}')
    if name:
        args.append(f'-n {name}')
    if extra_args:
        args.append(extra_args)

    cmd = f'scancel {_build_args(args)}'
    result = executor.run(cmd)

    if result.exit_code != 0:
        raise RuntimeError(f'Failed to cancel jobs: {result.stderr}')

    return result.stdout if result.stdout.strip() else 'Jobs cancelled successfully'


@mcp_tool
def sacct(
    user: Optional[str] = None,
    account: Optional[str] = None,
    job_ids: Optional[List[int]] = None,
    name: Optional[str] = None,
    state: Optional[str] = None,
    starttime: Optional[str] = None,
    endtime: Optional[str] = None,
    format: Optional[str] = None,
    me: bool = True,
    extra_args: Optional[str] = None,
) -> str:
    """
    Query Slurm job accounting history.

    Shows completed and running jobs from the accounting database.
    By default shows only the current user's jobs with -X (no sub-steps).

    Args:
        user: Filter by username (-u/--user).
        account: Filter by account (-A/--account).
        job_ids: Specific job IDs to query (-j/--jobs).
        name: Filter by job name (--name).
        state: Filter by state (-s/--state), e.g., 'COMPLETED', 'FAILED'.
        starttime: Start of time range (-S/--starttime), e.g., '2024-01-01'.
        endtime: End of time range (-E/--endtime).
        format: Output format (-o/--format), e.g., 'JobID,JobName,State,ExitCode'.
        me: Show only current user's jobs (default: True).
        extra_args: Additional sacct arguments.

    Returns:
        Job accounting information.

    Examples:
        sacct()
        sacct(starttime='2024-01-01', state='FAILED')
        sacct(job_ids=[19804935])
        sacct(format='JobID,JobName,State,Elapsed,MaxRSS')
    """
    executor = get_executor()

    args = ['-X']  # Always exclude sub-job steps for cleaner output

    if me and not user and not account:
        # Get current user
        user_result = executor.run('whoami')
        current_user = user_result.stdout.strip()
        args.append(f'-u {current_user}')
    if user:
        args.append(f'-u {user}')
    if account:
        args.append(f'-A {account}')
    if job_ids:
        args.append(f'-j {",".join(str(j) for j in job_ids)}')
    if name:
        args.append(f'--name={name}')
    if state:
        args.append(f'-s {state}')
    if starttime:
        args.append(f'-S {starttime}')
    if endtime:
        args.append(f'-E {endtime}')
    if format:
        args.append(f'-o {format}')
    if extra_args:
        args.append(extra_args)

    cmd = f'sacct {_build_args(args)}'
    result = executor.run(cmd)

    if result.exit_code != 0:
        raise RuntimeError(f'Failed to query job history: {result.stderr}')

    return result.stdout


@mcp_tool
def sinfo(
    partition: Optional[str] = None,
    nodes: Optional[str] = None,
    state: Optional[str] = None,
    format: Optional[str] = None,
    extra_args: Optional[str] = None,
) -> str:
    """
    Show cluster and partition status.

    Displays information about nodes and partitions including
    availability, state, and resources.

    Args:
        partition: Filter by partition (-p/--partition).
        nodes: Filter by node list (-n/--nodes).
        state: Filter by node state (-t/--states), e.g., 'idle', 'alloc'.
        format: Output format (-o/--format).
        extra_args: Additional sinfo arguments.

    Returns:
        Cluster/partition status information.

    Examples:
        sinfo()
        sinfo(partition='gpu')
        sinfo(state='idle')
    """
    executor = get_executor()

    args = []
    if partition:
        args.append(f'-p {partition}')
    if nodes:
        args.append(f'-n {nodes}')
    if state:
        args.append(f'-t {state}')
    if format:
        args.append(f'-o "{format}"')
    if extra_args:
        args.append(extra_args)

    cmd = f'sinfo {_build_args(args)}'
    result = executor.run(cmd)

    if result.exit_code != 0:
        raise RuntimeError(f'Failed to get cluster info: {result.stderr}')

    return result.stdout


@mcp_tool
def scontrol_show_job(job_id: int) -> str:
    """
    Show detailed Slurm job information.

    Returns comprehensive job details directly from Slurm's control
    daemon, including all job parameters and current state.

    Args:
        job_id: The Slurm job ID to query.

    Returns:
        Detailed job information from scontrol.

    Examples:
        scontrol_show_job(19804935)
    """
    _validate_job_id(job_id)
    executor = get_executor()

    result = executor.run(f'scontrol show job {job_id}')

    if result.exit_code != 0:
        raise RuntimeError(f'Failed to get job details: {result.stderr}')

    return result.stdout


@mcp_tool
def scontrol_show_node(node: Optional[str] = None) -> str:
    """
    Show detailed node information for diagnostics.

    Returns comprehensive node details from Slurm including
    state, resources, features, and current load.

    Args:
        node: Specific node name to query. If None, shows all nodes.

    Returns:
        Detailed node information from scontrol.

    Examples:
        scontrol_show_node('a000')
        scontrol_show_node()  # All nodes (may be large output)
    """
    executor = get_executor()

    cmd = 'scontrol show node'
    if node:
        cmd += f' {node}'

    result = executor.run(cmd)

    if result.exit_code != 0:
        raise RuntimeError(f'Failed to get node details: {result.stderr}')

    return result.stdout


@mcp_tool
def slist() -> str:
    """
    Show Slurm accounts and current usage (RCAC-specific).

    Displays accounts the user has access to submit jobs with,
    along with current usage relative to allocation limits.
    Shows CPU partition usage and AI/GPU partition balance.

    Returns:
        Account listing with usage statistics.

    Examples:
        slist()
    """
    executor = get_executor()
    result = executor.run('slist')

    if result.exit_code != 0:
        raise RuntimeError(f'Failed to get account list: {result.stderr}')

    return result.stdout


@mcp_tool
def sfeatures() -> str:
    """
    Show available node features and constraints (RCAC-specific).

    Displays node hardware features that can be used as constraints
    when submitting jobs, including CPU types, memory tiers, and
    GPU models.

    Returns:
        Node features listing with CPUS, MEMORY, AVAIL_FEATURES, and GRES.

    Examples:
        sfeatures()
    """
    executor = get_executor()
    result = executor.run('sfeatures')

    if result.exit_code != 0:
        raise RuntimeError(f'Failed to get node features: {result.stderr}')

    return result.stdout
