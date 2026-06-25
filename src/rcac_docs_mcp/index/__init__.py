# SPDX-FileCopyrightText: 2025 Purdue University
# SPDX-License-Identifier: MIT

"""Documentation search index backed by SQLite FTS5.

Provides full-text search over RCAC documentation (user guides, software
catalog, datasets, blog posts, workshops) so that agents can consult
authoritative docs before advising users.
"""

# Public interface
__all__ = ['DocsDatabase', 'DocsIndexer', 'DEFAULT_DB_PATH']

# Re-exports
from rcac_docs_mcp.index.database import DocsDatabase, DEFAULT_DB_PATH
from rcac_docs_mcp.index.indexer import DocsIndexer
