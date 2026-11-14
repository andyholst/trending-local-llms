#!/usr/bin/env python3
"""The ONE declared-estimate detector and footprint-field set (rule 6d, issue #936).

``(est)`` / ``(estimated)`` is rule 2's honest placeholder: a projection allowed
into the store precisely because it is MARKED as one. That marker is what this
module reads, and it lives here alone — a second copy of the pattern would let
the validator (which refuses untraceable composites that splice an ``(est)``
marker in) and the gap analysis (which reports re-askable estimates) disagree
about what a declared estimate IS, silently.

Why a module instead of importing ``validate``: ``make data-gap-issue`` runs
``data_gap_analysis.py`` on the runner's host python, which carries no
``jsonschema`` — importing ``validate`` there is an ImportError on the filer's
path. This module is stdlib-only, so both the validator (container) and the
filer (host) can import it.

Stdlib only.
"""
from __future__ import annotations

import re

#: The marker shape, byte-identical to the validator's (issue #788/#933):
#: ``(est)`` / ``(estimated)`` opening a paren, any whitespace, word-boundary,
#: case-insensitive. The ONLY spelling any stage may read.
DECLARED_ESTIMATE = re.compile(r"\(\s*(?:est|estimated)\b", re.I)

#: The ranked footprint dimensions — the fields a footprint query can re-ask a
#: model for (rule 6o). Byte-identical ORDER to ``data_gap_analysis.DIMENSIONS``'
#: keys, pinned by ``tests/test_data_gap_analysis.py`` so the two can never drift.
FOOTPRINT_FIELDS = ("system_ram_min", "weight_gb", "context_tokens",
                    "storage_offload", "engine_min_version")


def has_declared_estimate(value) -> bool:
    """Does this value carry the declared-estimate marker?"""
    return bool(DECLARED_ESTIMATE.search(str(value)))


def footprint_estimates(models: list[dict]) -> dict[str, list[str]]:
    """field -> ``model/engine:field=value`` entries whose footprint value is a DECLARED estimate.

    A value is re-askable by definition: its own marker says it is a projection,
    and the refresh already derives a footprint query naming each trending model
    (rule 6o), so a new search can replace the entry with a measured figure.
    Values are read from the measurement rows (where the footprint lives,
    issues #337/#376) AND from the model row itself (``_stated`` reads both).
    Analysis-only: the store is never touched.
    """
    out: dict[str, list[str]] = {}
    for m in models:
        mid = str(m.get("id") or "?")
        rows: list[tuple[str | None, dict]] = [
            (str(e.get("engine") or "-"), e) for e in (m.get("engines") or [])]
        rows.append((None, m))  # the model row's own values (same shape _stated reads)
        for field in FOOTPRINT_FIELDS:
            for engine, row in rows:
                value = row.get(field)
                if value in (None, "", [], {}):
                    continue
                if has_declared_estimate(value):
                    where = engine if engine is not None else "-"
                    out.setdefault(field, []).append(
                        f"{mid}/{where}:{field}={value}")
    return out
