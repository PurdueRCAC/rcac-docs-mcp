# SPDX-FileCopyrightText: 2026 Purdue University
# SPDX-License-Identifier: MIT
"""Shared helpers for the rcac-docs-mcp software-factory FSM scripts.

The finite-state machine for a feature lives in the YAML frontmatter of its
``spec/<slug>/TECH.md`` roadmap. These helpers read, validate, mutate, and
re-serialize that frontmatter so the *scripts* (not the model) own the fragile
YAML arithmetic — model in-context YAML editing is the primary FSM-corruption
risk (see ``.agents/factory/methodology.md``).

Requires PyYAML. The entry-point scripts that import this module carry PEP 723
inline metadata declaring it, so ``uv run .agents/factory/bin/<script>.py``
resolves it into a cached ephemeral environment with no project setup.
"""
from __future__ import annotations

# Standard libs
import datetime
import os
import tempfile
from pathlib import Path
from typing import Any

# External libs
try:
    import yaml
except ModuleNotFoundError as exc:  # pragma: no cover - environment guard
    raise SystemExit(
        "PyYAML is required. Run these scripts as `uv run "
        ".agents/factory/bin/<script>.py` so the PEP 723 metadata is honored."
    ) from exc


# Public interface
__all__ = [
    "FSMError",
    "REQUIRED_TOP",
    "PHASE_STATUSES",
    "TOP_STATUSES",
    "FIELD_ORDER",
    "split_frontmatter",
    "dump_document",
    "write_document",
    "validate",
    "compute_next",
    "today",
]


REQUIRED_TOP = ["slug", "kind", "appetite", "status", "branch", "base", "current_phase", "phases"]
PHASE_STATUSES = {"pending", "in_progress", "done", "blocked"}
TOP_STATUSES = {"planned", "in_progress", "blocked", "in_review", "done"}

# Canonical key order for deterministic re-serialization (keys not listed keep
# their existing relative order, appended after these).
FIELD_ORDER = [
    "slug", "title", "kind", "appetite", "status", "branch", "base",
    "current_phase", "last_updated", "phases", "review",
]
PHASE_FIELD_ORDER = [
    "id", "name", "status", "satisfies", "depends_on",
    "parallel", "hammerable", "hill", "attempts", "verify",
]


class FSMError(Exception):
    """Raised on a malformed or invalid TECH.md frontmatter."""


def today() -> str:
    """Return today's date as an ISO-8601 string (local)."""
    return datetime.date.today().isoformat()


def split_frontmatter(text: str) -> tuple[dict[str, Any], str]:
    """Split a markdown document into (frontmatter dict, body string).

    The document must open with a ``---`` fence, contain a YAML block, and close
    the block with a line that is exactly ``---``. Everything after is the body.
    """
    if not text.startswith("---"):
        raise FSMError("TECH.md must begin with a '---' YAML frontmatter fence.")
    lines = text.splitlines(keepends=True)
    # lines[0] is the opening fence; find the closing fence.
    for i in range(1, len(lines)):
        if lines[i].rstrip("\r\n") == "---":
            fm_text = "".join(lines[1:i])
            body = "".join(lines[i + 1:])
            break
    else:
        raise FSMError("Unterminated frontmatter: no closing '---' fence found.")
    try:
        data = yaml.safe_load(fm_text)
    except yaml.YAMLError as exc:
        raise FSMError(f"Frontmatter is not valid YAML: {exc}") from exc
    if not isinstance(data, dict):
        raise FSMError("Frontmatter did not parse to a mapping.")
    return data, body


def _ordered(data: dict[str, Any], order: list[str]) -> dict[str, Any]:
    """Return a new dict with keys in `order` first, then any remaining keys."""
    out: dict[str, Any] = {}
    for key in order:
        if key in data:
            out[key] = data[key]
    for key in data:
        if key not in out:
            out[key] = data[key]
    return out


def dump_document(data: dict[str, Any], body: str) -> str:
    """Re-serialize (frontmatter dict, body) into a full markdown document.

    Serialization is canonical and deterministic: top-level and per-phase keys
    are emitted in a fixed order and formatting is normalized. Inline comments in
    the source frontmatter are dropped — enums are documented in the template and
    in ``methodology.md``. The body is preserved verbatim.
    """
    data = _ordered(dict(data), FIELD_ORDER)
    phases = data.get("phases")
    if isinstance(phases, list):
        data["phases"] = [
            _ordered(dict(p), PHASE_FIELD_ORDER) if isinstance(p, dict) else p
            for p in phases
        ]
    fm = yaml.safe_dump(data, sort_keys=False, allow_unicode=True, default_flow_style=False)
    if not body.startswith("\n"):
        body = "\n" + body
    return f"---\n{fm}---{body}"


def write_document(path: Path, text: str) -> None:
    """Write the document atomically: temp file in the same directory, then replace.

    ``TECH.md`` is the single durable record of where a feature is. A crash
    partway through a plain overwrite truncates it, and the FSM has no second
    copy to reconcile against. ``os.replace`` is atomic within a filesystem, and
    the temp file is created alongside the target so it never crosses one. This
    mirrors how the server publishes its own search index.
    """
    directory = path.parent if str(path.parent) else Path(".")
    fd, tmp = tempfile.mkstemp(dir=directory, prefix=f".{path.name}.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp, path)
    except BaseException:
        # Leaving a stale .TECH.md.*.tmp beside the real file is worse than a
        # failed write: the next reader may glob it up as a spec artifact.
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def _dependency_cycle(phases: list[Any]) -> list[str] | None:
    """Return one dependency cycle as a list of phase ids, or None if acyclic.

    A cycle makes every phase in it permanently unactionable, so ``compute_next``
    returns None and the caller reads ``all_done: true`` — a silent success on an
    FSM that can never be built. Iterative depth-first search with an explicit
    stack; the graph is a handful of nodes, so clarity beats cleverness.
    """
    deps: dict[str, list[str]] = {}
    for p in phases:
        if isinstance(p, dict) and p.get("id"):
            deps[str(p["id"])] = [str(d) for d in (p.get("depends_on") or [])]

    UNVISITED, ACTIVE, DONE = 0, 1, 2
    state = dict.fromkeys(deps, UNVISITED)

    for root in deps:
        if state[root] != UNVISITED:
            continue
        # Each stack frame is (node, iterator over its remaining dependencies).
        path: list[str] = []
        stack: list[tuple[str, list[str]]] = [(root, list(deps[root]))]
        state[root] = ACTIVE
        path.append(root)
        while stack:
            node, remaining = stack[-1]
            if not remaining:
                state[node] = DONE
                stack.pop()
                path.pop()
                continue
            nxt = remaining.pop(0)
            if nxt not in deps:
                continue  # unknown id — already reported by validate()
            if state[nxt] == ACTIVE:
                return path[path.index(nxt):] + [nxt]
            if state[nxt] == UNVISITED:
                state[nxt] = ACTIVE
                path.append(nxt)
                stack.append((nxt, list(deps[nxt])))
    return None


def validate(data: dict[str, Any]) -> list[str]:
    """Return a list of human-readable validation errors (empty means valid)."""
    errors: list[str] = []
    for key in REQUIRED_TOP:
        if key not in data:
            errors.append(f"missing required top-level key: {key}")
    if data.get("status") not in TOP_STATUSES and "status" in data:
        errors.append(f"top-level status {data.get('status')!r} not in {sorted(TOP_STATUSES)}")
    phases = data.get("phases")
    if not isinstance(phases, list) or not phases:
        errors.append("phases must be a non-empty list")
        return errors
    ids: set[str] = set()
    for idx, p in enumerate(phases):
        if not isinstance(p, dict):
            errors.append(f"phase[{idx}] is not a mapping")
            continue
        pid = p.get("id")
        if not pid:
            errors.append(f"phase[{idx}] missing id")
            continue
        if pid in ids:
            errors.append(f"duplicate phase id: {pid}")
        ids.add(pid)
        if p.get("status") not in PHASE_STATUSES:
            errors.append(f"phase {pid} status {p.get('status')!r} not in {sorted(PHASE_STATUSES)}")
    for p in phases:
        if isinstance(p, dict):
            for dep in p.get("depends_on") or []:
                if dep not in ids:
                    errors.append(f"phase {p.get('id')} depends_on unknown phase {dep}")
    cycle = _dependency_cycle(phases)
    if cycle:
        errors.append("dependency cycle: " + " -> ".join(cycle))
    cur = data.get("current_phase")
    if cur and cur not in ids and cur not in ("", "done"):
        errors.append(f"current_phase {cur!r} is not a known phase id")
    return errors


def compute_next(data: dict[str, Any]) -> tuple[dict[str, Any] | None, list[str]]:
    """Compute the next actionable phase from phase statuses (authoritative).

    A phase is actionable if its status is pending/in_progress and every phase in
    its ``depends_on`` is done. Returns (phase_dict_or_None, warnings). Warnings
    flag blocked phases and any drift between the stored ``current_phase`` pointer
    and the computed next phase (the crash-safety reconciliation signal).
    """
    warnings: list[str] = []
    phases = data.get("phases") or []
    status_by_id = {p.get("id"): p.get("status") for p in phases if isinstance(p, dict)}

    for p in phases:
        if isinstance(p, dict) and p.get("status") == "blocked":
            warnings.append(f"phase {p.get('id')} is blocked")

    nxt: dict[str, Any] | None = None
    for p in phases:
        if not isinstance(p, dict):
            continue
        if p.get("status") in ("pending", "in_progress"):
            deps = p.get("depends_on") or []
            unmet = [d for d in deps if status_by_id.get(d) != "done"]
            if unmet:
                continue
            nxt = p
            break

    if nxt is not None:
        # The attempts counter is the durable circuit breaker: it survives context resets.
        attempts = int(nxt.get("attempts") or 0)
        if attempts >= 3:
            warnings.append(
                f"phase {nxt.get('id')} has {attempts} recorded failed verify attempts "
                "(circuit breaker: stop-and-re-shape rather than retry)"
            )

    stored = data.get("current_phase")
    if nxt is not None and stored not in (nxt.get("id"), None, ""):
        warnings.append(
            f"current_phase pointer {stored!r} != computed next {nxt.get('id')!r} "
            "(reconcile before acting)"
        )
    if nxt is None and stored not in ("", "done", None):
        warnings.append(f"no actionable phase but current_phase is {stored!r}")
    return nxt, warnings
