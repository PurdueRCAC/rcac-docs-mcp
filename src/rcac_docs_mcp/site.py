# SPDX-FileCopyrightText: 2025 Purdue University
# SPDX-License-Identifier: MIT


"""Manage the local RCAC-Docs site checkout.

Resolves the path to a local clone of the RCAC-Docs documentation
repository and clones or updates it via ``git`` (invoked through
``subprocess``; no extra Python dependency). The indexer reads its
markdown source from this checkout.
"""


# Type annotations
from __future__ import annotations
from typing import Optional, Final

# Standard libs
import os
import subprocess

# Public interface
__all__ = [
    'DEFAULT_SITE_PATH',
    'DEFAULT_SITE_URL',
    'resolve_site_path',
    'resolve_site_url',
    'update_site',
]


# XDG-compliant default location for the local RCAC-Docs checkout
DEFAULT_SITE_PATH: Final[str] = os.path.join(
    os.environ.get('XDG_DATA_HOME', os.path.expanduser('~/.local/share')),
    'rcac-docs-mcp',
    'RCAC-Docs',
)


# Upstream repository cloned when the local checkout is missing
DEFAULT_SITE_URL: Final[str] = 'https://github.com/PurdueRCAC/RCAC-Docs'


def resolve_site_path(path: Optional[str] = None) -> str:
    """
    Resolve the local RCAC-Docs checkout path.

    Precedence: explicit `path`, then the ``RCAC_DOCS_SITE`` environment
    variable, then `DEFAULT_SITE_PATH`. User home (``~``) is expanded.
    """
    resolved = path or os.environ.get('RCAC_DOCS_SITE') or DEFAULT_SITE_PATH
    return os.path.expanduser(resolved)


def resolve_site_url(url: Optional[str] = None) -> str:
    """
    Resolve the upstream RCAC-Docs clone URL.

    Precedence: explicit `url`, then the ``RCAC_DOCS_SITE_URL`` environment
    variable, then `DEFAULT_SITE_URL`.
    """
    return url or os.environ.get('RCAC_DOCS_SITE_URL') or DEFAULT_SITE_URL


def update_site(site_path: Optional[str] = None, site_url: Optional[str] = None) -> str:
    """
    Clone or update the local RCAC-Docs checkout.

    Clones `site_url` into the resolved checkout path when it does not yet
    exist, otherwise updates it in place with
    ``git -C <site> pull --rebase --autostash origin main``. Returns the
    resolved checkout path.
    """
    path = resolve_site_path(site_path)
    if os.path.isdir(os.path.join(path, '.git')):
        subprocess.run(
            ['git', '-C', path, 'pull', '--rebase', '--autostash', 'origin', 'main'],
            check=True,
        )
    else:
        url = resolve_site_url(site_url)
        parent = os.path.dirname(path)
        if parent:
            os.makedirs(parent, exist_ok=True)
        subprocess.run(['git', 'clone', url, path], check=True)
    return path
