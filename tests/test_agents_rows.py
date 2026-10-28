#!/usr/bin/env python3
"""The §8 rows a change owed are WRITTEN, not promised (issues #310/#391/#400/#369).

Rule 6c requires a change's guard row in the §8 table in the same change. Four changes could
not write theirs: AGENTS.md writes were gated behind an approval prompt in a headless bot run
("Silence is not consent", #310), so the guards shipped registered in `make test` and
undiscoverable from the rulebook. These tests pin the rows that were owed, so the gap cannot
reopen quietly.

#369 is the `storage_offload` pair: its own body lost the guard's name to a truncated finding
(issue.md lines 5-7 end mid-clause), so the row it owes is derived from the change that added
the guards — `openspec/changes/data-gap-storage-offload` (#364, PR #366), whose tasks 4/5 name
them — and pinned here like the rest.

Run:  python3 tests/test_agents_rows.py   or   make test
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
AGENTS = ROOT / "AGENTS.md"

_PASS = 0
_FAIL = 0


def check(name, cond, detail: object = ""):
    global _PASS, _FAIL
    if cond:
        _PASS += 1
        print(f"  ok  {name}")
    else:
        _FAIL += 1
        print(f"  FAIL {name}" + (f"  [{detail}]" if detail else ""))


def section8() -> str:
    text = AGENTS.read_text(encoding="utf-8")
    return text[text.index("## 8. Regression guards"):]


#: The next rule or section heading at column 0 — the end of the rule being read. Rules are
#: written two ways in the rulebook: `## 6b. <title>` for a section, and a bare `6e. **…**`
#: item, so the slicer accepts both.
_NEXT_RULE = re.compile(r"(?m)^(## |\d+[a-z]?\. )")


def rule_section(rule: str) -> str:
    """The text of ONE rulebook rule (`rule="6j"`), from its heading to the next one."""
    text = AGENTS.read_text(encoding="utf-8")
    # §6b is BOTH a `## 6b.` section and a bare `6b.` rule, so the section form is tried
    # first: a bare match would slice the wrong text entirely.
    m = None
    for pat in (rf"(?m)^## {re.escape(rule)}\.", rf"(?m)^{re.escape(rule)}\. "):
        m = re.search(pat, text)
        if m:
            break
    if not m:
        return ""
    nxt = _NEXT_RULE.search(text, m.end())
    return text[m.start():] if not nxt else text[m.start():nxt.start()]


def test_the_rows_for_the_two_label_queue_and_the_sweep_alarm_are_written():
    """#494 / #497: the rulebook rows those two changes shipped WITHOUT, pinned so the ledger
    cannot rot back to prose.

    #494 put `tech-debt` into `issue_queue.QUEUE_LABELS` (one oldest-first queue) and made
    `scripts/issue_verdict.py` REFUSE an `EVIDENCE:` block that names nothing in the tree;
    #497 added `issue-bot.yml`'s backup slot and the delivery alarm a DROPPED cron needs.
    All of that is in the tree and green, and §6b/§6e/§6j/§8 described the OLD behaviour —
    which an agent reads as authority.
    """
    sec = section8()
    rows = [
        ("#494 the two-label queue",
         "test_the_queue_reads_both_labels_as_one_oldest_first_list",
         "tests/test_issue_review.py", "48 `tech-debt` issues"),
        ("#494 the tree-evidence verdict",
         "test_three_mock_issues_decide_implement_refine_or_close_against_the_tree",
         "tests/test_issue_triage.py", "`EVIDENCE:`"),
        ("#497 the sweep delivery alarm",
         "tests/test_sweep_alarm.py",
         "make sweep-alarm", "24 slots a day"),
    ]
    for label, guard, module, measured in rows:
        row = next((l for l in sec.splitlines() if guard in l), "")
        check(f"rows: {label} has a §8 row", bool(row), f"no row naming {guard}")
        check(f"rows: … naming {module}", module in row, row[:120])
        check(f"rows: … and the measured failure", measured in row, row[:120])

    # The three rule paragraphs the rows describe (§6b slots, §6e verdict, §6j label set).
    b = rule_section("6b")
    check("6b: both cron slots are named", "'19 * * * *'" in b and "'49 * * * *'" in b)
    check("6b: … with the dropped-cron reason", "DROPS on-the-hour crons" in b)
    check("6b: … and the serialising concurrency",
          "concurrency: issue-bot-<issue|sweep>" in b)

    e = rule_section("6e")
    check("6e: the verdict file is named", "`triage.md`" in e)
    check("6e: … its three verdicts", all(v in e for v in ("`implement`", "`refine`", "`close`")))
    check("6e: … the target that applies it", "`make issue-verdict`" in e)
    check("6e: … and the EVIDENCE refusal", "REFUSES one that names nothing in the tree" in e)

    j = rule_section("6j")
    check("6j: both actionable labels", '`("data-gap-analysis", "tech-debt")`' in j)
    check("6j: … read as ONE oldest-first queue", "ONE oldest-first queue" in j)
    check("6j: … and the reviewer's narrower default",
          "keeps its own `data-gap-analysis` default" in j)
def section6b() -> str:
    """The §6b pipelines section, up to the next `## ` heading."""
    text = AGENTS.read_text(encoding="utf-8")
    start = text.index("## 6b.")
    nxt = text.find("\n## ", start + 1)
    return text[start:] if nxt == -1 else text[start:nxt]


def test_the_conflict_repair_path_is_named_in_6b():
    """#476: §6b must name what happens to a bot PR whose base moved.

    The repair shipped in #478 (`scripts/fix_loop.sh` keeps a CONFLICTED base merge and
    hands its hunks to a round; `pr-health` dispatches for a `ci/…` branch only). The
    rulebook said nothing, so a reader could not tell a conflicting bot PR is repaired by
    automation, nor which guard catches a regression in it.
    """
    sec = section6b()
    for phrase, why in (
        ("dispatches `fix-bot` for a `ci/…` branch", "the sweep's dispatch is not named"),
        ("capped at 2 `fix-bot:` commits", "the commit cap is not stated"),
        ("merges the FETCHED base before its first round", "the base merge is not stated"),
        ("CONFLICTED merge is\n  KEPT", "the kept conflict is not stated"),
        ("REGENERATED, never hand-merged", "the regenerate rule is not stated"),
        ("COMPLETED once the index comes back clean", "the completion rule is not stated"),
        ("`--abort`ed only after the last", "the abort rule is not stated"),
        ("nothing half-merged is ever pushed", "the half-merged push is not forbidden"),
        ("A HUMAN's branch is reported", "the human's-branch carve-out is not stated"),
    ):
        check(f"6b: {why}", phrase in sec, phrase)


def test_the_owed_rows_are_present():
    sec = section8()
    # #400: the CI entry point that never ran.
    check("rows: §8 names tests/test_ci_wiring.py", "`tests/test_ci_wiring.py`" in sec)
    check("rows: … and the dead pytest branch it catches",
          "2>/dev/null" in sec and "pytest is absent" in sec)
    # #310: the code-review secret contract.
    check("rows: §8 names tests/test_code_review.py", "`tests/test_code_review.py`" in sec)
    check("rows: … and the four checks it catches",
          "GITHUB_TOKEN" in sec and "COMMENTED reference" in sec)
    # #391: the loop's scratch file.
    check("rows: §8 names the scratch-notes guard",
          "test_scratch_notes_stay_out_of_the_tree" in sec)
    check("rows: … and the measured 0-byte file it catches",
          "qa-report.txt.notes" in sec and "PR #387" in sec)


def test_the_rows_this_session_owed_are_written():
    """The §8 rows that could not be written when their guards shipped (issues #543, #474, #362,
    #580/#583, #592, #522, #547/#548/#539/#578, #544, #563, #363).

    Each of those changes recorded its row as OWED in `findings.md` because `AGENTS.md` is a
    protected file and the approval did not return. They are applied together here, and pinned so
    the ledger cannot rot back to prose.
    """
    sec = section8()
    wanted = {
        "#543": "the bot's working files (",
        "#474": "a marker WRITTEN outside the registry",
        "#362": "a search leg told to make its Firecrawl call",
        "#580/#583": "a re-run's work lost",
        "#592": "resuming a branch that is NOT this run's work",
        "#522": "reading the picked issue's state ONLY in the fail-loud step",
        "#547/#548/#539/#578": "a recipe whose stdout a workflow CAPTURES",
        "#544": "the inventory claiming a target the pipeline never runs",
        "#563": "the fix loop describing a failed base merge",
        "#363": "a refresh search leg given no `HF_TOKEN`",
        "#476": "a bot PR that cannot merge because its base moved",
    }
    for issue, phrase in wanted.items():
        row = next((l for l in sec.splitlines() if issue in l and phrase in l), "")
        check(f"rows: the {issue} row is present and describes the guard", bool(row),
              f"no row naming {issue} + {phrase!r}")

    # And the marker the reverse guard found is REGISTERED (issue #474), not merely allowed
    sys.path.insert(0, str(ROOT / "scripts"))
    import bot_markers as bm  # noqa: E402 — the real registry
    check("rows: issue-bot-already-fixed is registered, not owed",
          "issue-bot-already-fixed" in [n for k in bm.REGISTRY.values() for n in k.values()],
          sorted(bm.REGISTRY))
    check("rows: and nothing is left in the owed list", not bm.UNREGISTERED_OWED, bm.UNREGISTERED_OWED)
def test_the_storage_offload_row_is_written():
    """#369: the row #364's change owed, derived from its own tasks 4/5 rather than guessed.

    A ranked dimension was closed by evidence (#364) and its guards shipped in `make test` with
    no §8 row, so the rulebook could not tell a reader the traceability guard exists."""
    sec = section8()
    check("rows: §8 names the storage_offload traceability guard",
          "test_storage_offload_backfill_traces_to_the_captured_source_text" in sec)
    check("rows: §8 names the storage_offload coverage floor",
          "test_storage_offload_coverage_can_never_shrink" in sec)
    row = next((l for l in sec.splitlines()
                if "test_storage_offload_backfill_traces_to_the_captured_source_text" in l), "")
    check("rows: the row names the module it lives in",
          "`tests/test_data_gap_analysis.py" in row, row[:120])
    check("rows: the row states the invented value it catches",
          "invented" in row or "no captured" in row, row[:120])
    check("rows: the row states the coverage floor it catches",
          "coverage" in row or "reopen" in row, row[:120])
    check("rows: the row cites the change that added the guards",
          "#364" in row and "#366" in row, row[:120])
    check("rows: it sits beside the existing test_data_gap_analysis.py rows",
          "issue #163" in sec.split("test_storage_offload_backfill", 1)[0][-4000:], "not near #163")


def test_the_rows_name_modules_that_exist():
    sec = section8()
    for mod in ("tests/test_ci_wiring.py", "tests/test_code_review.py", "tests/test_fix_loop.py",
                "tests/test_data_gap_analysis.py", "tests/test_issue_review.py",
                "tests/test_issue_triage.py", "tests/test_sweep_alarm.py"):
        check(f"rows: {mod} is a real module", (ROOT / mod).is_file(), mod)
    # #494: the §8 row says the verdict evidence gate exists, so the gate it cites must be REAL
    # in `scripts/issue_verdict.py` — a refusal some other module implements would leave the row
    # describing nothing (the shape #369's pin already uses).
    verdict = (ROOT / "scripts" / "issue_verdict.py").read_text()
    check("rows: the EVIDENCE shape gate the #494 row cites lives in scripts/issue_verdict.py",
          "_EVIDENCE_SHAPES" in verdict and "points at nothing in the tree" in verdict)
    # …and the two guards themselves live in the modules the §8 rows name.
    for mod, guard in (("tests/test_issue_review.py",
                        "def test_the_queue_reads_both_labels_as_one_oldest_first_list("),
                       ("tests/test_issue_triage.py",
                        "def test_three_mock_issues_decide_implement_refine_or_close_against_the_tree(")):
        check(f"rows: {guard.split('(')[0].removeprefix('def ')} lives in the module the row names",
              guard in (ROOT / mod).read_text(), guard)
    check("rows: the guards the rows name live in those modules",
          "test_scratch_notes_stay_out_of_the_tree" in
          (ROOT / "tests" / "test_fix_loop.py").read_text())
    # #369: the row's two guards are FUNCTIONS of the module it names, so renaming or deleting
    # one turns this pin RED instead of leaving a row that describes nothing.
    gap = (ROOT / "tests" / "test_data_gap_analysis.py").read_text()
    for guard in ("def test_storage_offload_backfill_traces_to_the_captured_source_text(",
                  "def test_storage_offload_coverage_can_never_shrink("):
        check(f"rows: {guard.split('(')[0].removeprefix('def ')} lives in the module the row names",
              guard in gap, guard)


def test_the_section_still_parses_as_a_table():
    sec = section8()
    rows = [l for l in sec.splitlines() if l.startswith("|")]
    check("rows: the section is a table with a header", rows and rows[0].startswith("| Guard"), rows[:1])
    bad = [r for r in rows if r.count("|") < 3]
    check("rows: every row has at least a guard and a description", not bad, bad[:2])


def main() -> int:
    print("the owed §8 rows (issues #310/#391/#400/#369)")
    test_the_owed_rows_are_present()
    test_the_rows_for_the_two_label_queue_and_the_sweep_alarm_are_written()
    test_the_conflict_repair_path_is_named_in_6b()
    test_the_rows_this_session_owed_are_written()
    test_the_storage_offload_row_is_written()
    test_the_rows_name_modules_that_exist()
    test_the_section_still_parses_as_a_table()
    print(f"\nPASSED {_PASS} | FAILED {_FAIL}")
    return 1 if _FAIL else 0


if __name__ == "__main__":
    raise SystemExit(main())
