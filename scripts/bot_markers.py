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
  issue-bot           the issue (implementer)         issue-bot-start  (+ issue-bot-skip note,
                                                       + issue-bot-outcome on a DEAD run)
  issue-review-bot    the issue                       issue-review / issue-review: window
  refresh-bot         the PR (and gap issue) it opens refresh-bot-run
  qa-validate         the PR it merges                bot-merge

The dedup keys (`data-gap-signature`, `tech-debt-signature`) are NOT bot windows: they are search
keys pinned by `scripts/file_findings.py` and its tests, and their strings must not change. They
are exposed here for reference only.
"""
from __future__ import annotations

import datetime as dt
import re

#: The re-diagnosis annotation marker's name (issue #987): `<!-- pipeline-rediagnose: <ISO> run=<rid> -->`.
#: REGISTERED in `REGISTRY["queued-alarm"]["rediagnose"]` (its AGENTS.md §6j table row landed
#: through an attended run — the rule 3c sign-off); its SHAPE lives in `rediagnose_marker` /
#: `rediagnose_marker_run` at the bottom of this module so the writer and the reader share ONE
#: spelling (rule 6j). Defined above REGISTRY because the registry names it.
REDIAGNOSE_NAME = "pipeline-rediagnose"

#: `<bot> -> {kind: marker name}`. The name is the literal inside `<!-- ... -->`, so a reader and a
#: writer that both go through this module can never disagree about it.
REGISTRY: dict[str, dict[str, str]] = {
    "issue-bot":        {"start": "issue-bot-start", "skip": "issue-bot-skip",
                         "verdict": "issue-bot-verdict",
                         # The already-fixed notice (issues #520/#522): written by
                         # `.github/workflows/issue-bot.yml` when the issue closed while the run
                         # was in flight. Registered here after #474's reverse guard found it.
                         "already_fixed": "issue-bot-already-fixed",
                         # The sweep's OWN outcome on a run that died before its verdict
                         # (`scripts/sweep_outcome.py`): until it existed, a dead run left the
                         # start marker and nothing else, so the queue item showed an
                         # implementer "in flight" for ever.
                         "outcome": "issue-bot-outcome"},
    "issue-review-bot": {"start": "issue-review", "window": "issue-review: window"},
    "refresh-bot":      {"run": "refresh-bot-run"},
    "qa-validate":      {"merge": "bot-merge"},
    # The failure filer (issue #802): `queued-alarm.yml` announces EACH main-pipeline failure it
    # diagnoses from a failed run's logs by filing an issue that carries this marker — the stamp
    # dates the filing, `run=<id>` dedups it (one run files once, ledger + marker agree).
    "queued-alarm":     {"failure": "pipeline-run-failure",
                         # The re-diagnosis annotation (issue #987): when the filer's re-diagnosis
                         # pass raises a UNDIAGNOSED row, the cited issue's thread gets ONE
                         # marker-deduplicated comment carrying this stamp — the ledger is the
                         # machine's memory, the thread is the human's. Its §6j table row landed
                         # through an attended run (rule 3c sign-off), so it moved out of
                         # UNREGISTERED_OWED into the registry.
                         "rediagnose": REDIAGNOSE_NAME},
}

#: Which artifact each bot announces on, before it mutates it (#197's table, for the guard).
ARTIFACTS: dict[str, str] = {
    "issue-bot": "the issue (before `make implement-issue`)",
    "issue-review-bot": "the issue (before its first write)",
    "refresh-bot": "the PR it opens (and the gap issue it files)",
    "qa-validate": "the PR (immediately before the merge)",
    "queued-alarm": "the issue it files for a diagnosed main-pipeline failure (issue #802), and "
                    "the issue thread of a ledger row its re-diagnosis pass raised (issue #987)",
}

#: The markers whose shape carries a WORD before the stamp (`issue-bot-verdict: refine <TS>`).
#: Everything else is `<name>: <TS>` only — and that is load-bearing: an optional field on
#: EVERY marker made `<!-- issue-review: window <TS> -->` parse as the `issue-review` START
#: marker, the exact confusion #197 exists to prevent (caught by
#: tests/test_bot_markers.py::test_the_two_reviewer_markers_are_not_confused).
FIELDS: frozenset = frozenset({("issue-bot", "verdict")})

#: Markers a WRITER in the tree emits that the registry does NOT declare yet, each with the issue
#: that lands the declaration (issue #474). Declaring one is a two-file change — this registry AND
#: the AGENTS.md §6j table, a protected file — so a marker whose row cannot be written stays here
#: instead of being invented into the registry alone. The list is CLOSED: the guard fails on any
#: other stray, so this can only shrink. It is NOW EMPTY: every owed registration has landed —
#: last was `pipeline-rediagnose` (issue #987), whose AGENTS.md §6j row an attended run wrote.
UNREGISTERED_OWED: dict[str, int] = {}

#: Markers that are dedup keys, not windows — exposed for reference, never rewritten here.
DEDUP_KEYS = ("data-gap-signature", "tech-debt-signature")

#: An issue AUTHOR declares its body follows the MESSAGE PATTERN by carrying this marker (issue
#: #771). Not a bot window and not a dedup key: it is a DECLARATION, like the owed-row marker
#: above — an issue that opts in to the five-section `## Why / What / How / Benefits / Technical
#: Solution` check is REFUSED by `make issue-message-check` the moment it skips, empties or
#: misorders a `##` section, while a structured data-gap/tech-debt issue carries its own schema
#: (## Goal / ## Ranked gaps / the attribution marker) and is never forced through that shape.
#: Its name deliberately starts with no bot-family prefix (`issue-`, `fix-`, …), so the reverse
#: marker guard never reads it as an unregistered window; `scripts/pr_body.py` imports it, so the
#: reader and the writer share ONE spelling (rule 6j).
ISSUE_PATTERN_MARKER = "message-pattern-opt-in"

#: Markers a writer in the tree emits TODAY. Every one of these must be findable in the repo —
#: a registered marker nobody writes is a promise with no producer, and the test fails on it.
WRITTEN: frozenset = frozenset({
    ("issue-bot", "start"),
    ("issue-bot", "skip"),
    # Written by `scripts/issue_verdict.py` since #210 and NOT registered until it became
    # a READER's problem: the decided hold (`agent:refined`) has no timestamp of its own,
    # so the queue reads this marker's stamp to date it (issue #449).
    ("issue-bot", "verdict"),
    ("issue-bot", "already_fixed"),
    # Written by `scripts/sweep_outcome.py` (via `make issue-outcome`): the sweep's own
    # outcome on a run that died BEFORE its verdict step, which used to leave nothing.
    ("issue-bot", "outcome"),
    ("issue-review-bot", "start"),
    ("issue-review-bot", "window"),
    ("refresh-bot", "run"),
    # Written by `scripts/pipeline_failure_issue.py` (via `make pipeline-failure-issue`,
    # issue #802) on the body of every issue it files for a failed main-pipeline run.
    ("queued-alarm", "failure"),
    # Written by the SAME filer's re-diagnosis pass (issue #987) on the ISSUE THREAD of a raised
    # UNDIAGNOSED ledger row: one marker-deduplicated comment, so the thread stops claiming
    # "log unreadable" once the diagnosis landed in the ledger.
    ("queued-alarm", "rediagnose"),
})

#: Registered but not yet written, with the issue that lands its writer. Declared here so a reader
#: written against the registry is already correct when the writer appears.
DECLARED_BY: dict[tuple[str, str], int] = {
    ("qa-validate", "merge"): 197,
}

#: An ISO8601Z timestamp as every marker writes it.
TS = r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9:.]+Z"

# ---------------------------------------------------------------------------
# The owed-row ledger marker (issue #523).
#
# Not a bot window and not a dedup key: it is a DECLARATION an issue carries, naming the AGENTS.md
# section a owed row belongs to and the exact needle that row must contain, so `make
# owed-rows-check` can report the row as landed or outstanding without re-reading a thread. Its
# name and shape live here like every other marker (rule 6j); a reader must not re-spell them.
#
# Shape: `<!-- owed-row: section=<id> needle=<token|"quoted phrase"> -->`
#   section  the AGENTS.md heading id (`8`, `6b`, …) the row is owed to
#   needle   the exact text the landed row must carry; quoted when it contains a space
# ---------------------------------------------------------------------------
OWED_ROW = "owed-row"

#: One regex for every owed-row declaration; a body that fails the grammar is MALFORMED, never
#: silently skipped — a reader that guesses at half-parsed markers is the drift this prevents.
OWED_ROW_RE = re.compile(r"<!-- owed-row:(?P<body>[^>]*)-->")
_OA_SECTION = re.compile(r"section=([A-Za-z0-9]+)")
_OA_NEEDLE = re.compile(r'needle=(?:"([^"]*)"|(\S+))')


def owed_row_marker(section: str, needle: str) -> str:
    """Write an owed-row declaration: the ONE writer-side shape (rule 6d)."""
    quoted = f'"{needle}"' if " " in needle else needle
    return f"<!-- {OWED_ROW}: section={section} needle={quoted} -->"


def parse_owed_rows(text: str) -> dict[str, list]:
    """Every owed-row declaration in `text`.

    -> {"rows": [{section, needle}], "malformed": [raw-marker-string]}
    A declaration missing `section=` or `needle=` lands in `malformed`; the caller must make it
    loud (rule 6d: a marker that fails to parse raises nothing unless a check says so).
    """
    rows: list[dict] = []
    malformed: list[str] = []
    for m in OWED_ROW_RE.finditer(text or ""):
        body = m.group("body")
        sec = _OA_SECTION.search(body)
        need = _OA_NEEDLE.search(body)
        if not sec or not need:
            malformed.append(m.group(0))
            continue
        rows.append({"section": sec.group(1), "needle": need.group(1) or need.group(2)})
    return {"rows": rows, "malformed": malformed}


# ---------------------------------------------------------------------------
# The re-diagnosis annotation marker (issue #987): `<!-- pipeline-rediagnose: <ISO> run=<rid> -->`.
#
# Declared in UNREGISTERED_OWED (its AGENTS.md §6j row is owed to rule 3c — a protected file a
# headless leg cannot write), yet its SHAPE still lives HERE so the writer (the failure filer's
# re-diagnosis pass) and its reader (the same pass' dedup — it must not re-comment a raised row's
# thread that already carries the marker) share ONE spelling (rule 6j: a reader that keeps its own
# copy of a marker string drifts silently). `run=<rid>` is the dedup key.
# ---------------------------------------------------------------------------
REDIAGNOSE_RE = re.compile(
    re.escape(f"<!-- {REDIAGNOSE_NAME}: ") + r"(" + TS + r")\s+run=([A-Za-z0-9_-]+)\s*-->"
)


def rediagnose_marker(when: dt.datetime, run: str | int) -> str:
    """Write a re-diagnosis annotation marker: `<!-- pipeline-rediagnose: <ISO> run=<rid> -->`."""
    stamp = when.strftime("%Y-%m-%dT%H:%M:%SZ")
    return f"<!-- {REDIAGNOSE_NAME}: {stamp} run={run} -->"


def rediagnose_marker_run(text: str) -> str | None:
    """The run id a `pipeline-rediagnose` marker in `text` carries, or None (the dedup key).

    Returns the run of the NEWEST marker (the whole thread is scanned, never a first-page-only
    read — the #662 class): the pass dedups ONE comment per raised row, and a thread carrying
    several raised rows' annotations still reports its newest run.
    """
    hits = [m.group(2) for m in REDIAGNOSE_RE.finditer(text or "")]
    return hits[-1] if hits else None


def rediagnose_marker_runs(text: str) -> set[str]:
    """Every run id the `pipeline-rediagnose` markers in `text` carry (for a per-run dedup)."""
    return {m.group(2) for m in REDIAGNOSE_RE.finditer(text or "")}


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
            # ONLY a marker in FIELDS accepts a word before its stamp; making it optional for
            # every marker let `issue-review: window <TS>` parse as the `issue-review` start.
            field = r"(?:([a-z]+)\s+)?" if (bot, kind) in FIELDS else ""
            pat = re.compile(re.escape(f"<!-- {name}") + r"[:\s]+" + field
                             + f"({TS})" + r"(?:\s+run=([A-Za-z0-9_-]+))?")
            for m in pat.finditer(text):
                if (bot, kind) in FIELDS:
                    hit = {"bot": bot, "kind": kind, "name": name, "field": m.group(1),
                           "at": m.group(2), "run": m.group(3)}
                else:
                    hit = {"bot": bot, "kind": kind, "name": name, "field": None,
                           "at": m.group(1), "run": m.group(2)}
                out.append(hit)
    out.sort(key=lambda r: (r["at"], r["name"]))
    return out


def read_marker(text: str, bot: str, kind: str) -> dict | None:
    """The newest marker of (bot, kind) in `text`, or None — the reader's one call."""
    hits = [r for r in parse_markers(text) if r["bot"] == bot and r["kind"] == kind]
    return hits[-1] if hits else None


def ts_of(text: str, bot: str, kind: str) -> dt.datetime | None:
    """The marker's timestamp as a datetime (UTC), or None — what the 3 h window compares."""
    hit = read_marker(text, bot, kind)
    if hit is None:
        return None
    try:
        return dt.datetime.strptime(hit["at"].rstrip("Z"), "%Y-%m-%dT%H:%M:%S").replace(tzinfo=dt.timezone.utc)
    except ValueError:
        try:
            return dt.datetime.fromisoformat(hit["at"].replace("Z", "+00:00"))
        except ValueError:
            return None


# ---------------------------------------------------------------------------
# Canonical renderings and their acceptance patterns (issue #904).
#
# The skills gate (`scripts/check_agent_skills.py`) scans every agent skill file
# for `<!-- <registered-name> …` comments and must decide, without re-spelling
# any shape (rule 6j), whether an occurrence is exactly what THIS registry
# writes. So the acceptance patterns are derived here, from the same grammar
# `parse_markers` reads: a scanner that kept its own copy of a shape would
# drift from the writers silently — the exact failure this module exists to
# prevent.
# ---------------------------------------------------------------------------

_CANONICAL_TS = "2026-01-01T00:00:00Z"
_CANONICAL_FIELD = {"verdict": "refine"}  # the one marker whose shape carries a word (FIELDS)


def canonical_examples() -> list[str]:
    """One rendering per marker family, written exactly as the registry itself writes it."""
    ref = dt.datetime(2026, 1, 1, tzinfo=dt.timezone.utc)
    out: list[str] = []
    for bot, kinds in REGISTRY.items():
        for kind, name in sorted(kinds.items()):
            if (bot, kind) in FIELDS:
                out.append(f"<!-- {name}: {_CANONICAL_FIELD[kind]} {_CANONICAL_TS} run=7 -->")
            else:
                out.append(start_marker(bot, ref, run=7, kind=kind))
    out.append(owed_row_marker("6b", "make owed-rows-check"))
    out.extend(f"<!-- {key}: example-signature -->" for key in DEDUP_KEYS)
    out.append(f"<!-- {ISSUE_PATTERN_MARKER} -->")
    return out


def marker_acceptance() -> dict[str, re.Pattern]:
    """`marker name -> compiled pattern` accepting ONLY the registry's own rendering.

    The pattern matches the FULL comment starting at `<!-- <name>`; a scanner
    matches it at each occurrence and a miss is a re-spelling (issue #904).
    """
    acc: dict[str, re.Pattern] = {}
    for bot, kinds in REGISTRY.items():
        for kind, name in kinds.items():
            field = r"(?:[a-z]+\s)?" if (bot, kind) in FIELDS else ""
            acc[name] = re.compile(re.escape(f"<!-- {name}") + r"[:\s]+" + field
                                   + TS + r"(?:\s+run=[A-Za-z0-9_-]+)?\s*-->")
    acc[OWED_ROW] = re.compile(r"<!-- owed-row: section=[A-Za-z0-9]+ needle=(?:\"[^\"]*\"|\S+)\s*-->")
    for key in DEDUP_KEYS:
        acc[key] = re.compile(re.escape(f"<!-- {key}: ") + r"[^\s>]+ -->")
    acc[ISSUE_PATTERN_MARKER] = re.compile(re.escape(f"<!-- {ISSUE_PATTERN_MARKER} -->"))
    return acc
