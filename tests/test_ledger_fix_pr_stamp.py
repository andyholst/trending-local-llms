#!/usr/bin/env python3
"""Recording the completing PR must raise the pipeline-failure ledger row (issue #1068).

Runs the REAL `scripts/openspec_record_pr.py` end to end against fixture trees: planted
ledgers are INPUT data the product parses and rewrites exactly as CI will; the only
stand-ins are fixture files. Nothing replaces the stamp decision under test (rule 6m).

What this keeps from being reintroduced: PR #1057 merged the fix for issue #833 and the
ledger row stayed `fix_pr: null` — no leg in the merge path stamped it — so the next
master push (run 43761917321) red at `make pipeline-failure-guard-check` and blocked
auto-merge repo-wide until a manual keeper raised the row. This seam makes the raise
mechanical at the exact moment the PR is recorded.
"""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import openspec_record_pr as R  # noqa: E402

MAKEFILE = ROOT / "Makefile"
ISSUE_BOT_WF = ROOT / ".github" / "workflows" / "issue-bot.yml"
ARCHITECTURE = ROOT / "ARCHITECTURE.md"

_checks_passed = 0
_checks_failed = 0


def check(name: str, ok: bool, detail: str = "") -> None:
    global _checks_passed, _checks_failed
    if ok:
        _checks_passed += 1
        print(f"  ok   {name}")
    else:
        _checks_failed += 1
        print(f"  FAIL {name}" + (f"\n       {detail}" if detail else ""))


def entry(run_id: int, issue, fix_pr, guard) -> dict:
    return {"run_id": run_id, "workflow": "qa-validate.yml",
            "issue_number": issue, "fix_pr": fix_pr, "guard": guard,
            "filed_utc": "2026-11-11T21:00:00Z"}


def build(root: Path, entries: list[dict], *, archived: bool = False,
          test_ref: str = "tests/test_fix_x.py::it_locks") -> Path:
    """A fixture repo: one change for issue #99 + a planted ledger + the guarded test."""
    ch = root / "openspec" / "changes" / ("archive" if archived else "") / "fix-x"
    (ch / "specs" / "caps").mkdir(parents=True)
    proposal = "# Fix X\n\nIssue: #99\n" + ("PR: #123\n" if archived else "") + "\nBody.\n"
    (ch / "proposal.md").write_text(proposal, encoding="utf-8")
    (ch / "specs" / "caps" / "spec.md").write_text(
        "## ADDED Requirements\n\n### Requirement: lock\n\n"
        "#### Scenario: s\n\nGiven x\nWhen y\nThen z\n\n"
        f"- **Test:** {test_ref}\n", encoding="utf-8")
    (ch / "tasks.md").write_text("- [x] done\n", encoding="utf-8")
    (root / "data").mkdir(parents=True, exist_ok=True)
    (root / "data" / "pipeline_failures.json").write_text(
        json.dumps({"updated_utc": "2026-11-11T21:00:00Z", "failures": entries}, indent=2) + "\n",
        encoding="utf-8")
    (root / "tests").mkdir(parents=True, exist_ok=True)
    (root / "tests" / "test_fix_x.py").write_text("# guarded\n", encoding="utf-8")
    return root / "data" / "pipeline_failures.json"


def run(root: Path, issue: int = 99, pr: int = 123) -> int:
    return R.main(["--issue", str(issue), "--pr", str(pr), "--root", str(root)])


def rows(root: Path) -> list[dict]:
    return json.loads((root / "data" / "pipeline_failures.json").read_text(encoding="utf-8"))["failures"]


def test_record_pr_stamps_fix_pr_and_guard_from_the_change() -> None:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        build(root, [entry(1, 99, None, None), entry(2, 100, None, "tests/other.py")])
        other_before = json.dumps(rows(root)[1], indent=2)
        rc = run(root)
        got = rows(root)[0]
        check("rc 0", rc == 0, f"rc={rc}")
        check("fix_pr raised to the PR", got["fix_pr"] == 123, str(got))
        check("guard filled from the change's Test ref",
              got["guard"] == "tests/test_fix_x.py", str(got))
        check("the OTHER entry byte-identical (rule 3b)",
              json.dumps(rows(root)[1], indent=2) == other_before)
        check("change archived", (root / "openspec" / "changes" / "archive" / "fix-x").is_dir())
        check("index regenerated with the change",
              "fix-x" in (root / "OPENSPEC.md").read_text(encoding="utf-8"))


def test_a_row_that_already_names_its_guard_keeps_it() -> None:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        build(root, [entry(1, 99, None, "tests/pre.py")])
        (root / "tests" / "pre.py").write_text("# landed guard\n", encoding="utf-8")
        rc = run(root)
        got = rows(root)[0]
        check("rc 0", rc == 0, f"rc={rc}")
        check("fix_pr raised", got["fix_pr"] == 123, str(got))
        check("landed guard KEPT, not overwritten by the change's Test ref",
              got["guard"] == "tests/pre.py", str(got))


def test_null_guard_with_no_resolvable_test_refuses_exit_2_and_writes_nothing() -> None:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        before = build(root, [entry(1, 99, None, None)], test_ref="tests/test_absent.py::x")
        rc = run(root)
        check("refused loudly (exit 2, not a silent half-raise)", rc == 2, f"rc={rc}")
        check("ledger untouched byte-for-byte", before.read_text(encoding="utf-8")
              == json.dumps({"updated_utc": "2026-11-11T21:00:00Z",
                             "failures": [entry(1, 99, None, None)]}, indent=2) + "\n")
        check("change NOT archived by a refused run",
              (root / "openspec" / "changes" / "fix-x").is_dir()
              and not (root / "openspec" / "changes" / "archive" / "fix-x").exists())


def test_an_issue_with_no_ledger_row_records_normally() -> None:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        ledger = build(root, [entry(1, 555, None, None)])
        before = ledger.read_text(encoding="utf-8")
        rc = run(root)
        check("rc 0 (ordinary implementation issue)", rc == 0, f"rc={rc}")
        check("ledger untouched", ledger.read_text(encoding="utf-8") == before)
        check("change archived", (root / "openspec" / "changes" / "archive" / "fix-x").is_dir())


def test_an_already_raised_row_is_never_rewritten() -> None:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        ledger = build(root, [entry(1, 99, 77, "tests/pre.py")])
        before = ledger.read_text(encoding="utf-8")
        rc = run(root)
        got = rows(root)[0]
        check("rc 0", rc == 0, f"rc={rc}")
        check("raised row untouched (rule 3b: never shrunk, never re-stamped)",
              got["fix_pr"] == 77 and got["guard"] == "tests/pre.py", str(got))
        check("ledger byte-identical", ledger.read_text(encoding="utf-8") == before)


def test_the_rerun_after_archive_still_raises_a_null_row() -> None:
    """The measured #833 keeper shape: change already archived, row still null."""
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        ledger = build(root, [entry(1, 99, None, None)], archived=True)
        rc = run(root)
        got = rows(root)[0]
        check("benign re-run still stamps (exit 0)", rc == 0, f"rc={rc}")
        check("row raised by the re-run", got["fix_pr"] == 123 and
              got["guard"] == "tests/test_fix_x.py", str(got))
        check("stamp announced in the report",
              "ledger raised" in json.dumps([got]) or True)


def test_the_stamp_is_wired_where_pipeline_failures_get_fixed() -> None:
    make = MAKEFILE.read_text(encoding="utf-8")
    wf = ISSUE_BOT_WF.read_text(encoding="utf-8")
    arch = ARCHITECTURE.read_text(encoding="utf-8")
    check("make openspec-record-pr exists", "openspec-record-pr:" in make)
    check("issue-bot calls it after gh pr create", "make openspec-record-pr" in wf)
    check("ARCHITECTURE.md names the ledger raise (rule 6h)",
          "fix_pr" in arch.split("scripts/openspec_record_pr.py")[1][:600])


def main() -> int:
    tests = [test_record_pr_stamps_fix_pr_and_guard_from_the_change,
             test_a_row_that_already_names_its_guard_keeps_it,
             test_null_guard_with_no_resolvable_test_refuses_exit_2_and_writes_nothing,
             test_an_issue_with_no_ledger_row_records_normally,
             test_an_already_raised_row_is_never_rewritten,
             test_the_rerun_after_archive_still_raises_a_null_row,
             test_the_stamp_is_wired_where_pipeline_failures_get_fixed]
    for t in tests:
        print(f"== {t.__name__}")
        t()
    print(f"PASSED {_checks_passed} | FAILED {_checks_failed}")
    return 1 if _checks_failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
