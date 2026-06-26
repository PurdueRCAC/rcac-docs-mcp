# SPDX-FileCopyrightText: 2025 Purdue University
# SPDX-License-Identifier: MIT

"""Tests for rcac_docs_mcp.site — checkout path and URL resolution."""

from __future__ import annotations

import os
from unittest import mock

from rcac_docs_mcp.site import (
    DB_FILENAME,
    DEFAULT_SITE_PATH,
    DEFAULT_SITE_URL,
    REPO_DIRNAME,
    resolve_db_path,
    resolve_repo_path,
    resolve_site_path,
    resolve_site_url,
)


# ---------------------------------------------------------------------------
# Site path resolution
# ---------------------------------------------------------------------------

class TestResolveSitePath:

    def test_explicit_path_wins(self) -> None:
        with mock.patch.dict(os.environ, {'RCAC_DOCS_SITE': '/from/env'}):
            assert resolve_site_path('/explicit/path') == '/explicit/path'

    def test_env_var_used_when_no_explicit(self) -> None:
        with mock.patch.dict(os.environ, {'RCAC_DOCS_SITE': '/from/env'}):
            assert resolve_site_path() == '/from/env'

    def test_default_when_unset(self) -> None:
        with mock.patch.dict(os.environ, {}, clear=True):
            assert resolve_site_path() == DEFAULT_SITE_PATH

    def test_user_home_expanded(self) -> None:
        with mock.patch.dict(os.environ, {}, clear=True):
            resolved = resolve_site_path('~/some/checkout')
        assert '~' not in resolved
        assert resolved.endswith('some/checkout')


# ---------------------------------------------------------------------------
# Site URL resolution
# ---------------------------------------------------------------------------

class TestResolveSiteUrl:

    def test_explicit_url_wins(self) -> None:
        with mock.patch.dict(os.environ, {'RCAC_DOCS_URL': 'https://env.example/repo'}):
            assert resolve_site_url('https://explicit.example/repo') == 'https://explicit.example/repo'

    def test_env_var_used_when_no_explicit(self) -> None:
        with mock.patch.dict(os.environ, {'RCAC_DOCS_URL': 'https://env.example/repo'}):
            assert resolve_site_url() == 'https://env.example/repo'

    def test_default_when_unset(self) -> None:
        with mock.patch.dict(os.environ, {}, clear=True):
            assert resolve_site_url() == DEFAULT_SITE_URL


# ---------------------------------------------------------------------------
# Repo and index paths within the site
# ---------------------------------------------------------------------------

class TestSiteLayout:

    def test_repo_path_under_explicit_site(self) -> None:
        assert resolve_repo_path('/data/site') == os.path.join('/data/site', REPO_DIRNAME)

    def test_db_path_under_explicit_site(self) -> None:
        assert resolve_db_path('/data/site') == os.path.join('/data/site', DB_FILENAME)

    def test_paths_follow_env_site(self) -> None:
        with mock.patch.dict(os.environ, {'RCAC_DOCS_SITE': '/from/env'}):
            assert resolve_repo_path() == os.path.join('/from/env', REPO_DIRNAME)
            assert resolve_db_path() == os.path.join('/from/env', DB_FILENAME)
