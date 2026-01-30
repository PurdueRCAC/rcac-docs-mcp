# SPDX-FileCopyrightText: 2025 Purdue University
# SPDX-License-Identifier: MIT

"""Command execution abstraction layer."""

# Type annotations
from __future__ import annotations

# Internal libs
from rcac_mcp.executor.base import Executor, CommandResult

# Public interface
__all__ = ['Executor', 'CommandResult']
