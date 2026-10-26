#!/usr/bin/env python3
"""The bot marker registry is ONE definition, and it is the one every reader uses (issue #197).

A marker is a contract between a writer (a workflow step, hours ago) and a reader (another bot,
with no shared state). Neither a renamed marker nor a reworded one raises anything by itself — the
reader simply finds no timestamp and concludes "no implementer has started", which is the exact
collision the 3 h quiet window (#179) exists to prevent. These tests fail closed on that whole
class of drift:

  1. every registered marker round-trips writer -> parser -> timestamp;
  2. the two `issue-review-bot` markers are NOT confused for each other (the old reader matched
     `<!-- issue-review:` as a substring, which is a prefix of the window marker);
  3. a marker whose timestamp is malformed is NOT a marker (a placeholder is not a stamp);
  4. every marker registered as WRITTEN is actually written somewhere in the tree;
  5. the AGENTS.md section-6j table and the registry name exactly the same markers.

Run: python3 tests/test_bot_markers.py   (wired into `make _test`)
"""
from __future__ import annotations

import datetime as dt
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import bot_markers as bm  # noqa: E402

PASSED = FAILED = 0


def check(name: str, ok: bool, detail: object = "") -> None:
    global PASSED, FAILED
    if ok:
        PASSED += 1
        print(f"  ok  {name}")
    else:
        FAILED += 1
        print(f"FAIL {name}  {detail}")


def tree_text() -> str:
    """Every tracked text file that could carry a marker, concatenated (no git: this runs inside
    the test image with the repo mounted, where a worktree's `.git` is a file)."""
    parts = []
    for pattern in (".github/workflows/*.yml", "scripts/*.py", "tests/*.py"):
        for path in sorted(ROOT.glob(pattern)):
            parts.append(path.read_text(encoding="utf-8", errors="replace"))
    for name in ("AGENTS.md", "ARCHITECTURE.md", "Makefile"):
        path = ROOT / name
        if path.exists():
            parts.append(path.read_text(encoding="utf-8", errors="replace"))
    return "\n".join(parts)


WHEN = dt.datetime(2026, 10, 15, 9, 30, 0, tzinfo=dt.timezone.utc)
TREE = tree_text()


def test_every_registered_marker_round_trips() -> None:
    """A writer's output is readable by the parser, for every bot/kind in the registry."""

    # Given the registry
    assert bm.REGISTRY, "the registry is empty"

    for bot, kinds in sorted(bm.REGISTRY.items()):
        for kind in sorted(kinds):
            # When  the writer emits that marker and the reader parses it back
            text = bm.start_marker(bot, WHEN, 4242, kind=kind)
            hit = bm.read_marker(text, bot, kind)

            # Then  the bot, the kind and the timestamp survive the round trip
            check(f"round-trip {bot}/{kind}",
                  hit is not None and hit["bot"] == bot and hit["kind"] == kind,
                  f"wrote {text!r} read {hit}")
            check(f"round-trip timestamp {bot}/{kind}",
                  bm.ts_of(text, bot, kind) == WHEN,
                  f"{bm.ts_of(text, bot, kind)} != {WHEN}")

    # And a run id is optional but preserved when present
    with_run = bm.start_marker("issue-bot", WHEN, 77)
    check("a run id is carried", bm.read_marker(with_run, "issue-bot", "start")["run"] == "77", with_run)
    without_run = bm.start_marker("issue-bot", WHEN, None)
    check("a run id may be absent", bm.read_marker(without_run, "issue-bot", "start")["run"] is None, without_run)


def test_the_two_reviewer_markers_are_not_confused() -> None:
    """`issue-review:` and `issue-review: window` are distinct — the old substring reader was not."""

    # Given a reviewer's window marker (a reply already exists for this window)
    window = "<!-- issue-review: window 2026-10-15T09:30:00Z run=9 -->"
    # And a reviewer's start marker (a review is in flight)
    start = "<!-- issue-review: 2026-10-15T09:30:00Z run=9 -->"

    # When  each is read as both kinds
    # Then  each matches only its own kind
    check("window reads as window", bm.read_marker(window, "issue-review-bot", "window") is not None, window)
    check("window does NOT read as start", bm.read_marker(window, "issue-review-bot", "start") is None, window)
    check("start reads as start", bm.read_marker(start, "issue-review-bot", "start") is not None, start)
    check("start does NOT read as window", bm.read_marker(start, "issue-review-bot", "window") is None, start)


def test_a_placeholder_is_not_a_marker() -> None:
    """A marker whose stamp is malformed is not a marker: `x` is not a timestamp."""

    # Given bodies that LOOK like markers but carry a placeholder stamp
    # When  they are parsed
    # Then  none of them is a marker
    for body in ("<!-- issue-review: x run=otherrun -->",
                 "<!-- issue-review: window x -->",
                 "<!-- issue-bot-start: x -->",
                 "<!-- fix-bot-start: soon -->"):
        check(f"placeholder is not a marker: {body}", bm.parse_markers(body) == [], body)


def test_every_written_marker_has_a_writer() -> None:
    """A registered marker a reader waits for is written by SOMETHING in the tree."""

    # Given the registry's WRITTEN set
    check("WRITTEN is not empty", bool(bm.WRITTEN))

    for key in sorted(bm.WRITTEN):
        # When  we look for that marker's literal in the tree
        name = bm.marker_name(*key)
        # Then  a writer exists
        check(f"written: {name} appears in the tree", name in TREE, f"{name} has no writer")

    # And a declared-but-unwritten marker says which issue lands its writer
    for key in sorted(bm.DECLARED_BY):
        check(f"declared: {key[0]}/{key[1]} names its issue", bm.DECLARED_BY[key] > 0, key)
    check("no key is both written and declared",
          not (set(bm.WRITTEN) & set(bm.DECLARED_BY)),
          sorted(set(bm.WRITTEN) & set(bm.DECLARED_BY)))


def registered_names() -> set[str]:
    """Every marker literal the registry declares, in any bot family."""
    return {name for kinds in bm.REGISTRY.values() for name in kinds.values()}


def families() -> set[str]:
    """The bot families a tree marker must belong to, e.g. ``issue-bot-`` from ``issue-bot-start``.

    Derived, never listed: a new family added to the registry widens the guard by itself.
    """
    out: set[str] = set()
    for name in registered_names():
        head = re.split(r"[:\s]", name)[0]
        out.add(head)
        if "-" in head:
            out.add(head.rsplit("-", 1)[0] + "-")
    return out


def undeclared_markers(text: str) -> list[str]:
    """Marker names in ``text`` that belong to a registered family but are not registered.

    The reverse of ``test_every_written_marker_has_a_writer``: that one proves a registered marker
    has a writer, this one proves a WRITTEN marker is registered (issue #474). A name outside every
    family (a dedup key such as ``tech-debt-signature``, or an alarm marker) is not a bot window and
    is left alone.
    """
    known, fams = registered_names(), families()
    found: list[str] = []
    for m in re.finditer(r"<!--\s*([^>\n]{0,80}?)\s*(?:-->|\s|:|$)", text):
        head = re.split(r"[:\s]", m.group(1).strip())[0].strip()
        if not head or "<" in head or "$" in head or "{" in head:
            continue                      # a placeholder or a shell expression, not a literal
        if head in known:
            continue
        if head in getattr(bm, "UNREGISTERED_OWED", {}):
            continue                      # a known writer whose §6j row is owed (issue #474)
        if any(head.startswith(f) for f in fams) or head in fams:
            found.append(head)
    return sorted(set(found))


def test_every_marker_the_tree_writes_is_registered() -> None:
    """Issue #474: the guard checked registered→written only, so a NEW marker was invisible.

    ``scripts/issue_verdict.py`` had written ``issue-bot-verdict`` since #210 and the registry did
    not know it until #477, when it became a READER's problem (the decided hold in #449 has no
    timestamp of its own). A renamed or newly invented marker raises nothing: the reader simply
    finds no stamp, and concludes the opposite of what happened.
    """

    # Given a tree marker in a registered family that the registry does not declare.
    # Built, never written literally: this file is scanned too, so a literal here would be found
    # as a stray marker in the tree (the same trap the conflict-marker guard had, #588).
    planted = f"<!-- issue-bot-not-a-registered-{'marker'}: 2026-10-15T09:30:00Z -->"

    # Then  the reverse check sees it
    check("markers(registered→written): a planted marker in a known family IS caught",
          "issue-bot-not-a-registered-marker" in undeclared_markers(planted), undeclared_markers(planted))

    # And   a marker outside every family is NOT a bot window and is left alone
    check("markers: a dedup key or an alarm marker is not flagged",
          undeclared_markers("<!-- tech-debt-signature: abc123 -->") == []
          and undeclared_markers("<!-- queued-run-alarm -->") == [],
          undeclared_markers("<!-- tech-debt-signature: abc123 -->"))

    # And   the closed "owed" list still names an issue for every entry (it may only shrink)
    owed = getattr(bm, "UNREGISTERED_OWED", {})
    # The list may be EMPTY (every owed marker registered — issue #474 closed that way); what it may
    # never do is name an entry without the issue that lands its registration.
    check("markers: every owed registration names its issue",
          all(isinstance(n, int) and n > 0 for n in owed.values()), owed)

    # And   the REAL tree declares every marker it writes
    stray = undeclared_markers(TREE)
    check("markers(written→registered): every marker literal in the tree is registered",
          not stray, stray)


def test_agents_md_table_names_the_same_markers() -> None:
    """AGENTS.md section 6j is the human table for the machine registry — they cannot disagree."""

    # Given the AGENTS.md rule-6j table (a numbered hard rule, not a `##` heading)
    agents = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
    section = re.search(r"^6j\..*?(?=^6k\.)", agents, re.S | re.M)
    check("AGENTS.md carries rule 6j", section is not None)

    # When  we collect every marker name the registry knows
    names = {bm.marker_name(bot, kind) for bot, kinds in bm.REGISTRY.items() for kind in kinds}

    # Then  every one of them is named in that section
    for name in sorted(names):
        check(f"AGENTS.md 6j names {name!r}", name in (section.group(0) if section else ""), name)


def main() -> int:
    """Run every test in this file — a test defined but never called passes CI silently."""
    test_every_registered_marker_round_trips()
    test_the_two_reviewer_markers_are_not_confused()
    test_a_placeholder_is_not_a_marker()
    test_every_written_marker_has_a_writer()
    test_every_marker_the_tree_writes_is_registered()
    test_agents_md_table_names_the_same_markers()
    print(f"\nPASSED {PASSED} | FAILED {FAILED}")
    return 1 if FAILED else 0


if __name__ == "__main__":
    sys.exit(main())
