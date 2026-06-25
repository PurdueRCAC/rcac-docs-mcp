-- SPDX-FileCopyrightText: 2025 Purdue University
-- SPDX-License-Identifier: MIT
--
-- Schema for RCAC documentation search index.
-- Uses SQLite FTS5 for full-text search with BM25 ranking.

-- Core document metadata and full content
CREATE TABLE IF NOT EXISTS documents (
    doc_id INTEGER PRIMARY KEY,
    path TEXT UNIQUE NOT NULL,
    title TEXT NOT NULL,
    category TEXT,
    last_updated TEXT,
    source_hash TEXT,
    content TEXT NOT NULL
);

-- Document chunks (H2-level sections within a document)
-- NOTE: title is denormalized from documents so that FTS5 external content
-- reads (used by snippet/highlight) can find all required columns here.
CREATE TABLE IF NOT EXISTS chunks (
    chunk_id INTEGER PRIMARY KEY,
    doc_id INTEGER NOT NULL REFERENCES documents(doc_id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    heading TEXT,
    content TEXT NOT NULL,
    chunk_index INTEGER NOT NULL,
    UNIQUE(doc_id, chunk_index)
);

-- FTS5 virtual table for full-text search
CREATE VIRTUAL TABLE IF NOT EXISTS chunks_fts USING fts5(
    title,
    heading,
    content,
    content='chunks',
    content_rowid='chunk_id',
    tokenize='porter unicode61 remove_diacritics 1'
);

-- Triggers to keep FTS index in sync with chunks table
CREATE TRIGGER IF NOT EXISTS chunks_ai AFTER INSERT ON chunks BEGIN
    INSERT INTO chunks_fts(rowid, title, heading, content)
    VALUES (NEW.chunk_id, NEW.title, NEW.heading, NEW.content);
END;

CREATE TRIGGER IF NOT EXISTS chunks_ad AFTER DELETE ON chunks BEGIN
    INSERT INTO chunks_fts(chunks_fts, rowid, title, heading, content)
    VALUES ('delete', OLD.chunk_id, OLD.title, OLD.heading, OLD.content);
END;

CREATE TRIGGER IF NOT EXISTS chunks_au AFTER UPDATE ON chunks BEGIN
    INSERT INTO chunks_fts(chunks_fts, rowid, title, heading, content)
    VALUES ('delete', OLD.chunk_id, OLD.title, OLD.heading, OLD.content);
    INSERT INTO chunks_fts(rowid, title, heading, content)
    VALUES (NEW.chunk_id, NEW.title, NEW.heading, NEW.content);
END;

-- Index for loading chunks in order by document
CREATE INDEX IF NOT EXISTS idx_chunks_doc_id ON chunks(doc_id, chunk_index);
