# RCAC Docs MCP Server

A single-purpose [FastMCP](https://gofastmcp.com) server that exposes Purdue
RCAC's documentation to AI agents via full-text search. It runs
**unauthenticated** and is hosted at `docs.rcac.purdue.edu/mcp`.

The server provides exactly two tools:

- `doc_search(query, category=None)` — FTS5 / BM25 full-text search over the
  indexed RCAC documentation (user guides, software catalog, datasets, blog
  posts, workshops).
- `doc_load(path)` — return the full rendered markdown of one document by its
  relative path.

Agents use `doc_search` to find relevant pages, then `doc_load` to read the
full content, so advice is grounded in current, authoritative documentation
rather than general knowledge.

## Quick Start (Desktop Clients)

For MCP-enabled desktop applications like Claude Desktop, Cursor, or Warp, add
this server to your MCP configuration to run it locally over `stdio`:

```json
{
  "mcpServers": {
    "rcac-docs": {
      "command": "uvx",
      "args": ["git+https://github.com/PurdueRCAC/rcac-docs-mcp"]
    }
  }
}
```

The server needs a search index to answer queries. Build one first (see
[Building the Search Index](#building-the-search-index)); without it, the
tools return a message explaining how to build it.

## Connecting to the Hosted Server

A shared, no-auth instance is hosted at `docs.rcac.purdue.edu/mcp`. Point an
HTTP-capable MCP client at that URL — no token or credentials are required.

## Transports

The server runs unauthenticated over two transports:

- **`stdio`** (default) — for local MCP clients.
- **`http`** (streamable HTTP) — for hosted deployments.

```bash
rcac-docs-mcp                      # serve over stdio (local clients)
rcac-docs-mcp -t http -H 0.0.0.0   # serve over HTTP (hosted)
```

## The Site

A *site* is a single container directory that holds both the local checkout of
the [RCAC-Docs](https://github.com/PurdueRCAC/RCAC-Docs) repository (under
`repo/`) and the built search index (`index.db`):

```
<site>/
  repo/       # clone of PurdueRCAC/RCAC-Docs
  index.db    # FTS5 search index built from repo/
```

The site location is resolved from `--site`, then the `RCAC_DOCS_SITE`
environment variable, then the default `~/.local/share/rcac-docs-mcp`. The repo
checkout and index path are always derived from it (`<site>/repo` and
`<site>/index.db`).

### Environment Variables

- `RCAC_DOCS_SITE` — path to the local site container. Default:
  `~/.local/share/rcac-docs-mcp`.
- `RCAC_DOCS_URL` — upstream clone URL. Default:
  `https://github.com/PurdueRCAC/RCAC-Docs`.
- `MCP_BASE_URL` — public URL of the server, used to construct absolute icon
  URLs when hosting.

## Building the Search Index

Indexing is a two-step operator flow: fetch the docs, then build the index from
that checkout.

```bash
rcac-docs-mcp --update-site   # clone or git-pull <site>/repo
rcac-docs-mcp --index         # build/refresh <site>/index.db from <site>/repo
```

`--update-site` clones `RCAC_DOCS_URL` into `<site>/repo` when it is missing,
otherwise updates it in place (`git pull --rebase --autostash origin main`).
`--index` walks the checkout and writes `<site>/index.db`. Re-running `--index`
performs an incremental update — only changed files are reprocessed and stale
documents are pruned (SHA-256 hashing).

Use `--site PATH` to override the container location for either command:

```bash
rcac-docs-mcp --index --site /data/rcac-docs
```

## How Indexing Works

The indexing pipeline walks the RCAC-Docs `docs/` tree and, for each page,
parses YAML frontmatter, resolves pymdownx `--8<--` snippet includes, renders
Jinja2 macros/templates (from the docs repo's `main.py` and `mkdocs.yml`
`extra:`), strips the `<!-- more -->` blog marker, chunks the content on `##`
(H2) boundaries, and upserts it into SQLite with SHA-256 incremental hashing
and stale-document pruning.

Search uses an FTS5 virtual table with BM25 ranking and `snippet()`
highlighting; the optional `category` filter is a path-prefix match (e.g.
`userguides`, `software`, `datasets`, `blog`, `workshops`, or a deeper prefix
such as `userguides/gilbreth`). The table is tokenized `porter unicode61`, so
`gpu` and `gpus` are the same token.

A query containing no FTS5 operator is normalized before it reaches the engine:
terms are cut on non-word characters, stopwords are dropped, and the rest are
OR-joined and prefix-matched. Any operator switches that off and the query runs
verbatim, which is how a caller narrows.

## Available Tools

- `doc_search(query, category=None)` — Full-text search over RCAC
  documentation. Keep queries to 2–3 key terms. Plain queries are broadened;
  operators (`"exact phrase"`, `AND`, `NOT`, `NEAR`) are how you narrow.
  Returns up to 20 BM25-ranked results with path, title, heading, and a
  matching snippet.
- `doc_load(path)` — Load the full rendered markdown of a documentation page by
  its relative path (as shown in `doc_search` results).

## Development

```bash
uv sync
uv run pytest -q
```

Many integration tests depend on the RCAC-Docs git submodule fixture at
`tests/fixtures/RCAC-Docs`; when it is not initialized those tests skip
cleanly. To run them:

```bash
git submodule update --init tests/fixtures/RCAC-Docs
```

Serve a local instance during development:

```bash
rcac-docs-mcp           # stdio
rcac-docs-mcp -t http   # streamable HTTP on localhost:8000
```

## License

MIT
