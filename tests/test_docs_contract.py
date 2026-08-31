# SPDX-FileCopyrightText: 2026 Purdue University
# SPDX-License-Identifier: MIT

"""Tests that the copies of the search contract have not drifted apart.

Five places state the tool contract and the same-commit rule says they move
together, but nothing enforced it: a correction to the wildcard advice landed in
`README.md` and `INSTRUCTIONS.md` and missed `SERVER_INSTRUCTIONS`, which is the
only copy an agent ever sees. The two disagreed for four days and no gate
noticed, because a stale sentence breaks no import and fails no assertion.

Grepping for a shared phrase does not work here: all three sources hard-wrap
their prose, so a sentence is split across lines at different points in each
one, and two of the three add markdown backticks. Both are erased before
comparing, which lets the claims below be written once and matched wherever
they appear.
"""

from __future__ import annotations

import re
from pathlib import Path

from rcac_docs_mcp.server import SERVER_INSTRUCTIONS

REPO_ROOT = Path(__file__).resolve().parent.parent

# The substance of the contract, not its phrasing. Each has to appear in every
# copy, so rewording one file alone fails here rather than reaching an agent.
CONTRACT_CLAIMS = [
    'A query with no operator in it is broadened for you: stopwords are dropped '
    'and the remaining terms are OR-joined and prefix-matched',
    'Any FTS5 operator turns normalization off and runs the query verbatim',
    'The index is Porter-stemmed, so gpu/gpus and purge/purged already match '
    'each other and * is rarely needed',
]

# Advice the normalizer made wrong. An agent that follows it opts out of the
# broadening and gets worse recall, so its absence is worth asserting directly.
RETIRED_ADVICE = ['contai*', 'prefix wildcards for variants']


def _normalized(text: str) -> str:
    """Erase hard wrapping and markdown emphasis so prose can be compared."""
    return re.sub(r'\s+', ' ', text.replace('`', ''))


def _sources() -> dict[str, str]:
    return {
        'SERVER_INSTRUCTIONS': SERVER_INSTRUCTIONS,
        'INSTRUCTIONS.md': (REPO_ROOT / 'INSTRUCTIONS.md').read_text(),
        'README.md': (REPO_ROOT / 'README.md').read_text(),
    }


class TestSearchContractAgrees:

    def test_every_copy_states_every_claim(self) -> None:
        missing = [
            f'{name} is missing: {claim!r}'
            for name, text in _sources().items()
            for claim in CONTRACT_CLAIMS
            if _normalized(claim) not in _normalized(text)
        ]
        assert not missing, '\n'.join(missing)

    def test_no_copy_still_recommends_a_wildcard(self) -> None:
        found = [
            f'{name} still advises: {advice!r}'
            for name, text in _sources().items()
            for advice in RETIRED_ADVICE
            if advice in text
        ]
        assert not found, '\n'.join(found)

    def test_the_claims_describe_the_real_tokenizer(self) -> None:
        """Keeps the prose honest about the schema rather than about itself."""
        schema = (REPO_ROOT / 'src' / 'rcac_docs_mcp' / 'index' / 'schema.sql').read_text()
        assert 'porter' in schema, 'the Porter-stemming claim no longer matches schema.sql'
