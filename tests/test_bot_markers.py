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


#: The recorded #1685 thread (issue #1690's measured defect), captured from GitHub's own API
#: the way `owed_rows_check.read_thread` composes it: body first, every comment oldest-first.
#: It is a FIXTURE on purpose — the module's suite runs inside the TEST image with no network,
#: so the real thread text is recorded rather than fetched. Its genuine declaration lives on the
#: issue BODY (`- **Owed-row:** …`), and its comments QUOTE that marker in prose: one inline code
#: span naming the same needle, one block quote of #1581's malformed `section=6r` marker.
THREAD_1685 = (ROOT / "tests" / "fixtures" / "thread_1685_quoted_markers.txt").read_text(
    encoding="utf-8")

#: The recorded #1581 thread: the ledger's OTHER live problem. Its issue BODY declares
#: `- **Owed-row: <!-- owed-row: section=6r … -->` UNQUOTED (the malformed item this change must
#: NOT delete), and its design comment shows two FURTHER markers inside a fenced EXAMPLE of a
#: proposed edit — which are quotations, not declarations.
THREAD_1581 = (ROOT / "tests" / "fixtures" / "thread_1581_quoted_markers.txt").read_text(
    encoding="utf-8")

def _load_real_finding_marker_line() -> str:
    """The `- **Owed-row:** …` line of the real findings fixture in `tests/test_file_findings.py`."""
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "file_findings_fixture", ROOT / "tests" / "test_file_findings.py")
    assert spec and spec.loader, "cannot load tests/test_file_findings.py"
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return next(ln for ln in mod._OWED_ROW_FINDING.splitlines() if "Owed-row:" in ln) + "\n"


REAL_OWED_ROW_FINDING_MARKER_LINE = _load_real_finding_marker_line()

#: A findings-style body: the SHAPE the ledger's real declarations live in (findings/*.md files
#: carry `- **Owed-row:** <marker>` on their own line, never quoted). Its marker line is read from
#: `tests/test_file_findings.py`'s OWN `_OWED_ROW_FINDING` fixture rather than re-spelled here, so
#: the positive control cannot keep passing while the shipped field drifts.
FINDINGS_BODY = (
    "# Findings\n\n"
    "## The §8 guard row for the new check is owed to a protected AGENTS.md\n\n"
    "- **Signature:** owed-row-protected-rulebook\n"
    "- **Evidence:** a new guard check ships under `make lint`, rule 6c owes the `AGENTS.md` §8 row,\n"
    "  and the headless implement leg is REFUSED the write (protected agent-instruction file,\n"
    "  measured on #654–657: the change died on the bare `- [ ]` the refusal left behind)\n"
    "- **Why:** an undeclared owed row vanishes — the PR goes red on the unticked box, or the rulebook\n"
    "  silently describes the pre-guard behaviour (rule 3c starvation)\n"
    "- **Done when:** an attended run lands the row from the ledger issue\n"
    + REAL_OWED_ROW_FINDING_MARKER_LINE)


def _thread1690() -> dict:
    """The #1685 thread's parsed rows, straight through the product's parser."""
    return bm.parse_owed_rows(THREAD_1685)


def test_a_marker_quoted_in_prose_is_not_a_declaration():
    """Issue #1690: `OWED_ROW_RE` matched the literal substring ANYWHERE, so a marker QUOTED in a
    comment was read as that comment's OWN declaration.

    Measured on the recorded #1685 thread: the parser returned FOUR rows — three `section=8`
    (one real body declaration plus two prose quotations) and a phantom `section=6r` that exists
    nowhere as a declaration (it is #1581's malformed marker, quoted inside a design comment) —
    and `make owed-rows-check REPO=andyholst/trending-local-llms` reported `problems=2`.

    The discriminator: strip fenced code blocks, inline code spans and block-quoted lines BEFORE
    `OWED_ROW_RE` runs, then apply the unchanged grammar. Chosen over "only read `findings/<id>.md`
    bodies" because the ledger reads THREADS, not files — a declaration written by hand on an
    issue body (`- **Owed-row:** …`, the shape `scripts/file_findings.py` stamps) must still
    register, and only the quotation is prose.
    """
    # Given the recorded #1685 thread, whose ONLY genuine declaration is the body marker
    parsed = _thread1690()
    sections = [row["section"] for row in parsed["rows"]]

    # Then  NO phantom `section=6r` row survives — it was a quotation of #1581's malformed marker
    check("owed-row: no phantom section=6r row from a prose quotation",
          "6r" not in sections, sections)
    # And   exactly ONE row remains: the genuine `section=8` declaration on the body
    check("owed-row: exactly one genuine section=8 row registers",
          parsed["rows"] == [{"section": "8",
                             "needle": "test_a_planted_json_projection_path_is_refused"}],
          parsed["rows"])
    # And   nothing is left MALFORMED by the filtering (the quoted shape is dropped, not reported)
    check("owed-row: a quoted marker is not reported as malformed",
          parsed["malformed"] == [], parsed["malformed"])

    # And   the same discrimination holds for each quotation device on its own
    quoted_only = (
        "prose quoting `<!-- owed-row: section=8 needle=quoted_inline -->` inline\n"
        "```\n<!-- owed-row: section=9 needle=fenced_block -->\n```\n"
        "> <!-- owed-row: section=10 needle=block_quote -->\n")
    check("owed-row: an all-quotation thread declares nothing",
          bm.parse_owed_rows(quoted_only)["rows"] == [],
          bm.parse_owed_rows(quoted_only)["rows"])


def test_a_genuine_findings_style_declaration_still_registers():
    """The discriminator must not stop reading REAL declarations (rule 3c's owed rows live in
    `findings/*.md` bodies and on issue bodies, both unquoted)."""
    parsed = bm.parse_owed_rows(FINDINGS_BODY)
    check("owed-row: a findings-style body still registers its row",
          parsed["rows"] == [{"section": "8", "needle": "owed rulebook row"}]
          and parsed["malformed"] == [], parsed)


def test_the_pre_existing_1581_section_6r_item_is_still_reported():
    """#1581 owns its malformed `section=6r` marker; this change must not delete or launder it.

    The recorded #1581 issue BODY carries that marker UNQUOTED (`- **Owed-row:** …`), so the
    parser still reports it as a declared row. `make owed-rows-check` therefore still answers
    `NO SUCH SECTION` for #1581 and still counts it in `problems` — the repair stays #1581's
    (a body edit), not #1690's (a parser fix).

    The same thread also shows WHY the discriminator is right for a fenced EXAMPLE: its design
    comment illustrates a proposed re-declaration with two markers inside a code block. Those
    are proposals about what to write, not declarations on the thread, so they drop.
    """
    parsed = bm.parse_owed_rows(THREAD_1581)
    check("owed-row: #1581's own declaration is still REPORTED (not deleted)",
          parsed["rows"] == [{"section": "6r", "needle": "make pipeline-failure-issue"}],
          parsed["rows"])
    check("owed-row: #1581's fenced PROPOSAL markers are quotations, not declarations",
          all(r["section"] != "2" for r in parsed["rows"]), parsed["rows"])
    check("owed-row: #1581's row parses as well-formed (its defect is the SECTION id)",
          parsed["malformed"] == [], parsed["malformed"])


def main() -> int:
    """Run every test in this file — a test defined but never called passes CI silently."""
    test_every_registered_marker_round_trips()
    test_the_two_reviewer_markers_are_not_confused()
    test_a_placeholder_is_not_a_marker()
    test_every_written_marker_has_a_writer()
    test_every_marker_the_tree_writes_is_registered()
    test_agents_md_table_names_the_same_markers()
    test_a_marker_quoted_in_prose_is_not_a_declaration()
    test_a_genuine_findings_style_declaration_still_registers()
    test_the_pre_existing_1581_section_6r_item_is_still_reported()
    print(f"\nPASSED {PASSED} | FAILED {FAILED}")
    return 1 if FAILED else 0


if __name__ == "__main__":
    sys.exit(main())
