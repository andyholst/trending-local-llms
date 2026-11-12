#!/usr/bin/env python3
"""Fail when two ACTIVE OpenSpec changes propose the same rule (issue #622).

`openspec validate` checks a change's STRUCTURE and `check_openspec_tasks.py`
its checklist; `openspec_index.py` that it is indexed. None of them notice that
a SECOND change proposes the same edit, so a run can land one rule twice (or
neither, when each change believed the other's file carried the pin). Measured:
`openspec/changes/agents-md-footprint-dimensions/` (issue #375) and
`openspec/changes/the-owed-section-4-sentence/` (issue #371, CLOSED) each
declared an ADDED capability Requirement for the SAME `AGENTS.md` §4 sentence,
with two capability specs and one duplicated Requirement.

This script is the duplicate half of the gate: it fails (exit 1) when two
DIFFERENT active changes each declare a capability Requirement with the SAME
heading under the SAME kind — both `ADDED` (two changes both proposing the same
new rule) or both `MODIFIED` (two changes both rewriting the same existing
rule) — and it names both changes, the capability and the shared heading.

An `ADDED`∩`MODIFIED` pairing of one heading across two changes is a refinement
chain, NOT a duplicate, and is never flagged: that is exactly how
`firecrawl-refusal-is-loud` (ADDED) and `outage-verdict-tolerates-a-failed-query`
(MODIFIED) coexist in this repo today.

Scope: only ACTIVE (non-archived) changes under `openspec/changes/*`. Archived
changes are settled records and never duplicate candidates (rule 3b). A heading
duplicated WITHIN one change is not a duplicate either (two acts in one change
are the change's own business); only two distinct changes collide.

Wired into `make openspec-duplicate-check`, which `make openspec-check` runs so
`qa-validate` executes it on every PR (rules 6d/6f: reachable from a make target
CI runs).

Usage:
    python3 scripts/openspec_duplicate_check.py            # all active changes
    python3 scripts/openspec_duplicate_check.py <name>     # just <name>
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
CHANGES_DIR = REPO_ROOT / "openspec" / "changes"

# The `## ADDED Requirements` / `## MODIFIED Requirements` section markers that
# give a requirement its KIND. Group 1 = the normalized kind.
_KIND = re.compile(r"^\s*##\s+(ADDED|MODIFIED)\s+Requirements", re.IGNORECASE)
# A requirement heading declares a rule. Group 1 = its text.
_REQ = re.compile(r"^\s*###\s+Requirement:\s*(.*?)\s*$", re.IGNORECASE)


def _norm_heading(text: str) -> str:
    """Case- and whitespace-normalize a heading for comparison.

    `§4 Names every …` and `§4 names every …` are the same rule; a trailing
    period and interior whitespace differences must not separate them.
    """
    return re.sub(r"\s+", " ", text.strip().rstrip(".")).lower()


def _requirements(file: Path) -> list[tuple[str, str]]:
    """`(kind, normalized heading)` pairs for every Requirement in *file*.

    The kind is the `## <KIND> Requirements` section the heading sits under
    (ADDED / MODIFIED; other kinds are not duplicate candidates). Never raises
    on a missing or unreadable file (returns []) — the caller decides.
    """
    try:
        lines = file.read_text(encoding="utf-8").splitlines()
    except OSError:
        return []
    kind: str | None = None
    out: list[tuple[str, str]] = []
    for ln in lines:
        m = _KIND.match(ln)
        if m:
            kind = m.group(1).upper()
            continue
        r = _REQ.match(ln)
        if r and kind:
            out.append((kind, _norm_heading(r.group(1))))
    return out


def active_change_names(base: Path = CHANGES_DIR) -> list[str]:
    """All ACTIVE (non-archived) change names that have a specs/ directory."""
    if not base.is_dir():
        return []
    out = []
    for p in sorted(base.iterdir()):
        if not p.is_dir() or p.name == "archive":
            continue
        if (p / "specs").is_dir():
            out.append(p.name)
    return out


def _capabilities_of(change: str, base: Path = CHANGES_DIR) -> list[Path]:
    """Every capability spec path for an ACTIVE change."""
    d = base / change / "specs"
    if not d.is_dir():
        return []
    return sorted(p for p in d.iterdir() if (p / "spec.md").is_file())


def duplicates(base: Path = CHANGES_DIR) -> list[tuple[str, list[tuple[str, str, str]]]]:
    """`(normalized heading, [(change, kind, capability)])` for each collision.

    A collision is a (kind, normalized heading) pair declared by TWO or more
    DIFFERENT active changes. The entries are sorted so the report is stable.
    """
    bucket: dict[tuple[str, str], list[tuple[str, str, str]]] = {}
    for change in active_change_names(base):
        for cap in _capabilities_of(change, base):
            for kind, heading in _requirements(cap / "spec.md"):
                bucket.setdefault((kind, heading), []).append(
                    (change, kind, cap.parent.name)
                )
    out: list[tuple[str, list[tuple[str, str, str]]]] = []
    for (kind, heading), seen in sorted(bucket.items()):
        diffs = {c for c, _, _ in seen}
        if len(diffs) > 1:
            out.append((heading, seen))
    return out


def check_all(
    only: str | None = None, base: Path = CHANGES_DIR, verbose: bool = True
) -> int:
    """Return 1 when a duplicate is found, 0 otherwise."""
    if only:
        # A single named change cannot collide with ITSELF; just validate it
        # parses and report how many requirements it declares.
        if only not in active_change_names(base):
            print(
                f"[openspec-duplicate] FAIL {only}: no active change by that name "
                f"(missing specs/ or unknown)"
            )
            return 1
        n = sum(len(_requirements(c / "spec.md")) for c in _capabilities_of(only, base))
        print(f"[openspec-duplicate] OK {only}: {n} requirement(s) — a single change cannot duplicate itself")
        return 0

    hits = duplicates(base)
    if not hits:
        if verbose:
            print("[openspec-duplicate] OK: every active change proposes a distinct rule")
        return 0

    for heading, seen in hits:
        who = sorted({c for c, _, _ in seen})
        kinds = ", ".join(sorted({k for _, k, _ in seen}))
        print(
            f"[openspec-duplicate] FAIL {who[0]} + {who[1]} "
            f"(and more if present): both declare the requirement "
            f"\"{heading}\" ({kinds}) — one change must propose this rule, "
            f"not {len(who)}"
        )
        for change, kind, cap in seen:
            print(f"    {change} · {kind} · {cap}")
    print(
        f"[openspec-duplicate] {len(hits)} duplicate requirement(s) across {len(hits) + 1} "
        f"active changes — reconcile which change owns the edit"
    )
    return 1


if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else None
    raise SystemExit(1 if check_all(target) > 0 else 0)
