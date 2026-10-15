"""ONE definition of every bot start/end marker — its name, its shape, its parser, its writer
(issue #197).

A marker is a CONTRACT between a writer (a workflow step) and a reader (another bot, hours later,
with no shared state). The failure mode is silent: a renamed or reworded marker raises nothing —
the reader finds no timestamp and concludes "no implementer has started", which is the exact
collision the 3 h quiet window (#179) exists to prevent. This module is the single place that
knows the names and the shapes, so a reader can never drift from a writer (rule 6d).

Registry (AGENTS.md §6j carries the same table for humans):

  bot                 artifact it announces on        markers
  ------------------  ------------------------------  --------------------------------------
  issue-bot           the issue (implementer)         issue-bot-start  (+ issue-bot-skip note)
  issue-review-bot    the issue                       issue-review / issue-review: window
  fix-bot             the PR it repairs               fix-bot-start / fix-bot-end
  refresh-bot         the PR (and gap issue) it opens refresh-bot-run
  qa-validate         the PR it merges                bot-merge

The dedup keys (`data-gap-signature`, `tech-debt-signature`) are NOT bot windows: they are search
keys pinned by `scripts/file_findings.py` and its tests, and their strings must not change. They
are exposed here for reference only.
"""
from __future__ import annotations

import datetime as dt
import re

#: `<bot> -> {kind: marker name}`. The name is the literal inside `<!-- ... -->`, so a reader and a
#: writer that both go through this module can never disagree about it.
REGISTRY: dict[str, dict[str, str]] = {
    "issue-bot":        {"start": "issue-bot-start", "skip": "issue-bot-skip"},
    "issue-review-bot": {"start": "issue-review", "window": "issue-review: window"},
    "fix-bot":          {"start": "fix-bot-start", "end": "fix-bot-end"},
    "refresh-bot":      {"run": "refresh-bot-run"},
    "qa-validate":      {"merge": "bot-merge"},
}

#: Which artifact each bot announces on, before it mutates it (#197's table, for the guard).
ARTIFACTS: dict[str, str] = {
    "issue-bot": "the issue (before `make implement-issue`)",
    "issue-review-bot": "the issue (before its first write)",
    "fix-bot": "the PR (before `scripts/fix_loop.sh` reads the branch)",
    "refresh-bot": "the PR it opens (and the gap issue it files)",
    "qa-validate": "the PR (immediately before the merge)",
}

#: Markers that are dedup keys, not windows — exposed for reference, never rewritten here.
DEDUP_KEYS = ("data-gap-signature", "tech-debt-signature")

#: Markers a writer in the tree emits TODAY. Every one of these must be findable in the repo —
#: a registered marker nobody writes is a promise with no producer, and the test fails on it.
WRITTEN: frozenset = frozenset({
    ("issue-bot", "start"),
    ("issue-bot", "skip"),
    ("issue-review-bot", "start"),
    ("issue-review-bot", "window"),
})

#: Registered but not yet written, with the issue that lands its writer. Declared here so a reader
#: written against the registry is already correct when the writer appears (#198, #199).
DECLARED_BY: dict[tuple[str, str], int] = {
    ("fix-bot", "start"): 198,
    ("fix-bot", "end"): 198,
    ("refresh-bot", "run"): 199,
    ("qa-validate", "merge"): 197,
}

#: An ISO8601Z timestamp as every marker writes it.
TS = r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9:.]+Z"


def marker_name(bot: str, kind: str) -> str:
    """The literal marker name for (bot, kind) — the ONE definition a writer and a reader share."""
    try:
        return REGISTRY[bot][kind]
    except KeyError:
        raise KeyError(f"unknown bot marker {bot}/{kind}; known: {sorted(REGISTRY)}") from None


def start_marker(bot: str, when: dt.datetime, run: str | int | None = None, kind: str = "start") -> str:
    """Write a start marker: `<!-- <name>: <ISO8601Z> run=<id> -->` (run omitted when None)."""
    name = marker_name(bot, kind)
    stamp = when.strftime("%Y-%m-%dT%H:%M:%SZ")
    tail = f" run={run}" if run is not None else ""
    return f"<!-- {name}: {stamp}{tail} -->"


def end_marker(bot: str, when: dt.datetime, run: str | int | None = None, kind: str = "end") -> str:
    """Write an end marker — same shape, the `end` name (the window's close)."""
    return start_marker(bot, when, run, kind)


def parse_markers(text: str) -> list[dict]:
    """Every bot marker in `text` -> [{bot, kind, name, at, run}], in order of appearance.

    One parser for every marker: the reader and the writer cannot drift (rule 6d).
    """
    if not text:
        return []
    out: list[dict] = []
    # The literal is `<!-- <name>: <ISO8601Z> [run=<id>] -->`, and `issue-review: window` is the
    # one name that carries a word of its own — `[:\s]+` accepts the `:` every other name has.
    for bot, kinds in REGISTRY.items():
        for kind, name in kinds.items():
            pat = re.compile(re.escape(f"<!-- {name}") + r"[:\s]+" + f"({TS})"
                             + r"(?:\s+run=([A-Za-z0-9_-]+))?")
            for m in pat.finditer(text):
                out.append({"bot": bot, "kind": kind, "name": name, "at": m.group(1),
                            "run": m.group(2)})
    out.sort(key=lambda r: (r["at"], r["name"]))
    return out


def read_marker(text: str, bot: str, kind: str) -> dict | None:
    """The newest marker of (bot, kind) in `text`, or None — the reader's one call."""
    hits = [r for r in parse_markers(text) if r["bot"] == bot and r["kind"] == kind]
    return hits[-1] if hits else None


def ts_of(text: str, bot: str, kind: str) -> dt.datetime | None:
    """The marker's timestamp as a datetime (UTC), or None — what the 3 h window compares."""
    hit = read_marker(text, bot, kind)
    if not hit:
        return None
    try:
        return dt.datetime.strptime(hit["at"].rstrip("Z"), "%Y-%m-%dT%H:%M:%S").replace(tzinfo=dt.timezone.utc)
    except ValueError:
        try:
            return dt.datetime.fromisoformat(hit["at"].replace("Z", "+00:00"))
        except ValueError:
            return None
