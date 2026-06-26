# SPDX-FileCopyrightText: 2025 Purdue University
# SPDX-License-Identifier: MIT


"""Manage the local RCAC-Docs site directory.

A *site* is a single container directory that holds both the cloned
RCAC-Docs documentation repository (under ``repo/``) and the built
search index (``index.db``). This module resolves that container path,
derives the repo and index locations within it, and clones or updates
the repository via ``git`` (invoked through ``subprocess``; no extra
Python dependency). The indexer reads its markdown source from the repo
and writes the index alongside it.
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
    'REPO_DIRNAME',
    'DB_FILENAME',
    'resolve_site_path',
    'resolve_site_url',
    'resolve_repo_path',
    'resolve_db_path',
    'update_site',
]


# XDG-compliant default location for the local site container
DEFAULT_SITE_PATH: Final[str] = os.path.join(
    os.environ.get('XDG_DATA_HOME', os.path.expanduser('~/.local/share')),
    'rcac-docs-mcp',
)


# Upstream repository cloned when the local checkout is missing
DEFAULT_SITE_URL: Final[str] = 'https://github.com/PurdueRCAC/RCAC-Docs'


# Name of the documentation repository checkout within the site container
REPO_DIRNAME: Final[str] = 'repo'


# Name of the built search index within the site container
DB_FILENAME: Final[str] = 'index.db'


def resolve_site_path(path: Optional[str] = None) -> str:
    """
    Resolve the local site container path.

    Precedence: explicit `path`, then the ``RCAC_DOCS_SITE`` environment
    variable, then `DEFAULT_SITE_PATH`. User home (``~``) is expanded.
    """
    resolved = path or os.environ.get('RCAC_DOCS_SITE') or DEFAULT_SITE_PATH
    return os.path.expanduser(resolved)


def resolve_site_url(url: Optional[str] = None) -> str:
    """
    Resolve the upstream RCAC-Docs clone URL.

    Precedence: explicit `url`, then the ``RCAC_DOCS_URL`` environment
    variable, then `DEFAULT_SITE_URL`.
    """
    return url or os.environ.get('RCAC_DOCS_URL') or DEFAULT_SITE_URL


def resolve_repo_path(site_path: Optional[str] = None) -> str:
    """
    Resolve the documentation repository checkout within the site.

    Returns ``<site>/repo`` for the resolved site container.
    """
    return os.path.join(resolve_site_path(site_path), REPO_DIRNAME)


def resolve_db_path(site_path: Optional[str] = None) -> str:
    """
    Resolve the search index database within the site.

    Returns ``<site>/index.db`` for the resolved site container.
    """
    return os.path.join(resolve_site_path(site_path), DB_FILENAME)


def update_site(site_path: Optional[str] = None, site_url: Optional[str] = None) -> str:
    """
    Clone or update the documentation repository within the site.

    Clones `site_url` into ``<site>/repo`` when it does not yet exist,
    otherwise updates it in place with
    ``git -C <repo> pull --rebase --autostash origin main``. Returns the
    resolved repository checkout path.
    """
    repo_path = resolve_repo_path(site_path)
    if os.path.isdir(os.path.join(repo_path, '.git')):
        subprocess.run(
            ['git', '-C', repo_path, 'pull', '--rebase', '--autostash', 'origin', 'main'],
            check=True,
        )
    else:
        url = resolve_site_url(site_url)
        os.makedirs(os.path.dirname(repo_path), exist_ok=True)
        subprocess.run(['git', 'clone', url, repo_path], check=True)
    return repo_path
