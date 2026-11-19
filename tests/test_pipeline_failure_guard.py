#!/usr/bin/env python3
"""The ledger gate: a diagnosed pipeline failure cannot close without its guard (issue #802).

Runs the REAL `scripts/pipeline_failure_guard_check.py` — its ledger reader, its guard-test
lookup, its verdict over planted ledgers, and its end-to-end exit codes against real files. A
planted ledger is INPUT data (the product parses and judges it exactly as CI will); the only
external stand-in is the issue-state map, fed through the script's own `marker_issue_states`
shape. Nothing replaces the decision logic under test (rule 6m).

What this keeps from being reintroduced: the measured chain — qa-validate master run 43088760321
red on `openspec-archive-check` → issue #800 → fix PR #808 → guard
`tests/test_openspec_archive_check.py` — was closed successfully only because a guard test
landed. Without this gate, the next diagnosed pipeline failure could be closed with no test at
all, and the same error class would return silently on the next master push.
"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import pipeline_failure_guard_check as G  # noqa: E402

GUARD_SCRIPT = ROOT / "scripts" / "pipeline_failure_guard_check.py"
MAKEFILE = ROOT / "Makefile"
QA_WF = ROOT / ".github" / "workflows" / "qa-validate.yml"
COMMITTED_LEDGER = ROOT / "data" / "pipeline_failures.json"

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


# The fixture helper carries its diagnosis (issue #1136, rule 6c's one-place fixture rule): a
# stamped row is DIAGNOSED unless a test asks for the errorless shape with excerpt=None, which is
# the five rows the filer's re-diagnosis pass now owes a log re-read.
DEFAULT_EXCERPT = "make: *** [Makefile:1384: sweep-alarm] Error 2"


def entry(run_id: int, issue, fix_pr, guard, undiagnosed: bool = False,
          excerpt=DEFAULT_EXCERPT) -> dict:
    return {"run_id": run_id, "workflow": "qa-validate.yml", "job": "validate",
            "issue_number": issue, "fix_pr": fix_pr, "guard": guard,
            "undiagnosed": undiagnosed, "filed_utc": "2026-11-11T21:00:00Z",
            "error_excerpt": excerpt}


def states(pairs: list[tuple[int, int, str]]) -> dict:
    """{run_id: {number, state}} — the exact shape marker_issue_states returns."""
    return {str(run): {"number": num, "state": state} for run, num, state in pairs}


def verdict(ledger_entries: list[dict], marker_states: dict, repo: str | None = "octo/repo"):
    return G.verdict({"failures": ledger_entries}, repo, marker_states)


def test_closed_without_guard_is_red() -> None:
    print("\nclosed-without-guard: the refusal the gate exists for")
    rc, lines = verdict([entry(100, 51, None, None)], states([(100, 51, "CLOSED")]))
    check("CLOSED issue + no fix PR + no guard -> exit 1", rc == 1, str(lines))
    check("the refusal names the missing fix PR/guard",
          any("CLOSED without a fix PR or a guard test" in line for line in lines), str(lines))
    # Closing without a guard is red EVEN WHEN a fix PR is claimed but its test never landed.
    rc2, lines2 = verdict([entry(101, 52, 900, "tests/test_never_landed.py")],
                          states([(101, 52, "CLOSED")]))
    check("fix PR whose guard test is not on disk -> exit 1", rc2 == 1, str(lines2))
    check("the refusal names the missing guard test",
          any("guard" in line and "never" in line.lower() or "unguarded" in line
              for line in lines2), str(lines2))
    rc3, lines3 = verdict([entry(102, 53, 901, None)], states([(102, 53, "CLOSED")]))
    check("fix PR with NO guard named at all -> exit 1", rc3 == 1, str(lines3))


def test_closed_with_landed_fix_and_guard_is_green() -> None:
    print("\nguarded close: fix PR + a real collected test passes (the #800/#808 shape)")
    rc, lines = verdict([entry(103, 54, 902, "tests/test_pipeline_failure_guard.py")],
                        states([(103, 54, "CLOSED")]))
    check("CLOSED + fix PR + guard test on disk -> exit 0", rc == 0, str(lines))
    check("the green report counts the guarded close",
          any("1 diagnosed failure" in line for line in lines), str(lines))
    # The real seeded row must pass the gate exactly as written.
    committed = json.loads(COMMITTED_LEDGER.read_text())
    rc4, lines4 = verdict(committed["failures"], states([(43088760321, 800, "CLOSED")]))
    check("the committed ledger (run 43088760321, issue #800, PR #808, real guard) is green",
          rc4 == 0, str(lines4))


def test_run_41788683672_is_rediagnosed_with_its_landed_guard() -> None:
    print("\nrediagnosed row: the undiagnosed sweep-alarm run carries its diagnosis + guard (issue #820)")
    committed = json.loads(COMMITTED_LEDGER.read_text())
    row = [e for e in committed["failures"] if e["run_id"] == 41788683672]
    check("the row exists in the committed ledger", len(row) == 1, str(row))
    if not row:
        return
    e = row[0]
    check("the row names fix PR #806 (the #801 in-flight misgrade fix)",
          e.get("fix_pr") == 806, str(e.get("fix_pr")))
    check("the row names a guard test that exists on disk",
          G.guard_test_exists(e.get("guard") or "") and e.get("guard") == "tests/test_sweep_alarm.py",
          str(e.get("guard")))
    check("the diagnosis names the measured in-flight verdict line",
          "in_progress" in (e.get("error_excerpt") or ""), str(e.get("error_excerpt")))
    check("the diagnosis names the target the log names",
          e.get("targets") == ["sweep-alarm"], str(e.get("targets")))
    check("the original undiagnosed field is KEPT (append-only, rule 3b)",
          "undiagnosed" in e, "")
    # The exact post-merge gate shape: issue CLOSED, row names fix PR + real guard -> green.
    rc, lines = verdict(committed["failures"],
                        states([(41788683672, 820, "CLOSED"), (43088760321, 800, "CLOSED")]))
    check("the committed ledger with issue #820 CLOSED passes the gate", rc == 0, str(lines))


def test_run_41860616772_is_rediagnosed_with_its_landed_guard() -> None:
    print("\nrediagnosed row: the second undiagnosed sweep-alarm run carries its diagnosis + guard (issue #821)")
    committed = json.loads(COMMITTED_LEDGER.read_text())
    row = [e for e in committed["failures"] if e["run_id"] == 41860616772]
    check("the row exists in the committed ledger", len(row) == 1, str(row))
    if not row:
        return
    e = row[0]
    check("the row names fix PR #806 (the #801 in-flight misgrade fix)",
          e.get("fix_pr") == 806, str(e.get("fix_pr")))
    check("the row names a guard test that exists on disk",
          G.guard_test_exists(e.get("guard") or "") and e.get("guard") == "tests/test_sweep_alarm.py",
          str(e.get("guard")))
    check("the diagnosis names the measured in-flight verdict line",
          "in_progress" in (e.get("error_excerpt") or ""), str(e.get("error_excerpt")))
    check("the diagnosis names the target the log names",
          e.get("targets") == ["sweep-alarm"], str(e.get("targets")))
    check("the original undiagnosed field is KEPT (append-only, rule 3b)",
          "undiagnosed" in e, "")
    # The exact post-merge gate shape: issue CLOSED, row names fix PR + real guard -> green.
    rc, lines = verdict(committed["failures"],
                        states([(41860616772, 821, "CLOSED"), (43088760321, 800, "CLOSED")]))
    check("the committed ledger with issue #821 CLOSED passes the gate", rc == 0, str(lines))


def test_run_41922211098_is_rediagnosed_with_its_landed_guard() -> None:
    print("\nrediagnosed row: the undiagnosed sweep-alarm run 41922211098 carries its diagnosis + guard (issue #822)")
    committed = json.loads(COMMITTED_LEDGER.read_text())
    row = [e for e in committed["failures"] if e["run_id"] == 41922211098]
    check("the row exists in the committed ledger", len(row) == 1, str(row))
    if not row:
        return
    e = row[0]
    check("the row names fix PR #806 (the #801 in-flight misgrade fix)",
          e.get("fix_pr") == 806, str(e.get("fix_pr")))
    check("the row names a guard test that exists on disk",
          G.guard_test_exists(e.get("guard") or "") and e.get("guard") == "tests/test_sweep_alarm.py",
          str(e.get("guard")))
    check("the diagnosis names the measured in-flight verdict line",
          "in_progress" in (e.get("error_excerpt") or ""), str(e.get("error_excerpt")))
    check("the diagnosis names the target the log names",
          e.get("targets") == ["sweep-alarm"], str(e.get("targets")))
    check("the original undiagnosed field is KEPT (append-only, rule 3b)",
          "undiagnosed" in e, "")
    # The exact post-merge gate shape: the re-diagnosed issues CLOSED, rows named -> green.
    rc, lines = verdict(committed["failures"],
                        states([(41922211098, 822, "CLOSED"), (41788683672, 820, "CLOSED"),
                                (43088760321, 800, "CLOSED")]))
    check("the committed ledger with issue #822 CLOSED passes the gate", rc == 0, str(lines))
def test_run_41956933757_and_43049550731_are_rediagnosed_onto_the_landed_sweep_alarm_fix() -> None:
    print("\nrediagnosed rows: the two same-class sweep-alarm runs name the landed fix PR + guard (issue #976)")
    committed = json.loads(COMMITTED_LEDGER.read_text())
    for run_id, issue in ((41956933757, 824), (43049550731, 829)):
        row = [e for e in committed["failures"] if e["run_id"] == run_id]
        check(f"row {run_id} exists in the committed ledger", len(row) == 1, str(row))
        if not row:
            continue
        e = row[0]
        check(f"row {run_id} names fix PR #806 (the #801 in-flight misgrade fix)",
              e.get("fix_pr") == 806, str(e.get("fix_pr")))
        check(f"row {run_id} names a guard test that exists on disk",
              G.guard_test_exists(e.get("guard") or "") and e.get("guard") == "tests/test_sweep_alarm.py",
              str(e.get("guard")))
        check(f"row {run_id} diagnosis names the measured in-flight verdict line",
              "in_progress" in (e.get("error_excerpt") or ""), str(e.get("error_excerpt")))
        check(f"row {run_id} diagnosis names the target the log names",
              e.get("targets") == ["sweep-alarm"], str(e.get("targets")))
        check(f"row {run_id} original undiagnosed field is KEPT (append-only, rule 3b)",
              "undiagnosed" in e, "")
    # The exact post-merge gate shape: both sibling issues CLOSED with rows named -> green.
    rc, lines = verdict(committed["failures"],
                        states([(41956933757, 824, "CLOSED"), (43049550731, 829, "CLOSED"),
                                (41788683672, 820, "CLOSED"), (43088760321, 800, "CLOSED")]))
    check("the committed ledger with #824 and #829 CLOSED passes the gate", rc == 0, str(lines))


def test_run_41929086636_is_rediagnosed_onto_the_cancelled_delivery_guard() -> None:
    print("\nrediagnosed row: the cancelled refresh-bot aggregate names the landed guard (issue #823)")
    committed = json.loads(COMMITTED_LEDGER.read_text())
    row = [e for e in committed["failures"] if e["run_id"] == 41929086636]
    check("row 41929086636 exists in the committed ledger", len(row) == 1, str(row))
    if row:
        e = row[0]
        check("row 41929086636 names fix PR #806 (the landed cancelled-delivery alarm fix)",
              e.get("fix_pr") == 806, str(e.get("fix_pr")))
        check("row 41929086636 names a guard test that exists on disk",
              G.guard_test_exists(e.get("guard") or "") and e.get("guard") == "tests/test_sweep_alarm.py",
              str(e.get("guard")))
        check("row 41929086636 diagnosis names the measured cancel line",
              "The operation was canceled" in (e.get("error_excerpt") or ""),
              str(e.get("error_excerpt")))
        check("row 41929086636 diagnosis names the healthy tests verdict it reached",
              "PASSED 124 | FAILED 0" in (e.get("error_excerpt") or ""), "")
        check("row 41929086636 keeps the empty targets the log justified (rule 3b)",
              e.get("targets") == [], str(e.get("targets")))
        check("row 41929086636 original undiagnosed field is KEPT (append-only, rule 3b)",
              "undiagnosed" in e, "")
    # The post-merge gate shape: #823 CLOSED with its row named -> green, beside the siblings.
    rc, lines = verdict(committed["failures"],
                        states([(41929086636, 823, "CLOSED"), (41956933757, 824, "CLOSED"),
                                (43049550731, 829, "CLOSED"), (41788683672, 820, "CLOSED"),
                                (41860616772, 821, "CLOSED"), (41922211098, 822, "CLOSED"),
                                (43088760321, 800, "CLOSED")]))
    check("the committed ledger with #823 CLOSED passes the gate", rc == 0, str(lines))


def test_run_42973469114_is_rediagnosed_onto_the_landed_openspec_binding_fix() -> None:
    print("\n#825: the issue-bot record-pr refusal row names the landed binding fix (rule 6r)")
    committed = json.loads(COMMITTED_LEDGER.read_text())
    row = [e for e in committed["failures"] if e["run_id"] == 42973469114]
    check("row 42973469114 exists in the committed ledger", len(row) == 1, str(row))
    if row:
        e = row[0]
        check("row 42973469114 names fix PR #955 (the landed openspec-binding-check fix)",
              e.get("fix_pr") == 955, str(e.get("fix_pr")))
        check("row 42973469114 names a guard test that exists on disk",
              G.guard_test_exists(e.get("guard") or "")
              and e.get("guard") == "tests/test_openspec_binding.py",
              str(e.get("guard")))
        check("row 42973469114 diagnosis quotes the record-pr refusal the log carries",
              "openspec-record-pr" in (e.get("error_excerpt") or "")
              and "REFUSED" in (e.get("error_excerpt") or ""),
              str(e.get("error_excerpt")))
        check("row 42973469114 diagnosis names the landed gate half of the fix",
              "openspec-binding-check" in (e.get("rediagnosis_note") or "")
              and "#825" in (e.get("rediagnosis_note") or ""),
              str(e.get("rediagnosis_note")))
        check("row 42973469114 targets were GROWN to the target the log names (rule 3b)",
              "openspec-record-pr" in (e.get("targets") or []), str(e.get("targets")))
        check("row 42973469114 original undiagnosed field is KEPT (append-only, rule 3b)",
              "undiagnosed" in e, "")
    # The post-merge gate shape: #825 CLOSED with its row named -> green, beside the siblings.
    rc, lines = verdict(committed["failures"],
                        states([(42973469114, 825, "CLOSED"), (41929086636, 823, "CLOSED"),
                                (41956933757, 824, "CLOSED"), (43049550731, 829, "CLOSED"),
                                (41788683672, 820, "CLOSED"), (41860616772, 821, "CLOSED"),
                                (41922211098, 822, "CLOSED"), (43088760321, 800, "CLOSED")]))
    check("the committed ledger with #825 CLOSED passes the gate", rc == 0, str(lines))


def test_run_43050447566_is_rediagnosed_onto_the_landed_trending_guard() -> None:
    print("\n#830: the issue-bot row that reded the trending-for-your-card guard names the landed fix (rule 6r)")
    committed = json.loads(COMMITTED_LEDGER.read_text())
    row = [e for e in committed["failures"] if e["run_id"] == 43050447566]
    check("row 43050447566 exists in the committed ledger", len(row) == 1, str(row))
    if row:
        e = row[0]
        check("row 43050447566 names fix PR #571 (the landed datacenter-aggregate speed-gate fix)",
              e.get("fix_pr") == 571, str(e.get("fix_pr")))
        check("row 43050447566 names a guard test that exists on disk",
              G.guard_test_exists(e.get("guard") or "")
              and e.get("guard") == "tests/test_trending_for_your_card.py",
              str(e.get("guard")))
        check("row 43050447566 diagnosis quotes the make test red it redded",
              "test_trending_for_your_card" in (e.get("error_excerpt") or "")
              and "28,340" in (e.get("error_excerpt") or ""),
              str(e.get("error_excerpt"))[:200])
        check("row 43050447566 diagnosis names the target the log names",
              "test" in (e.get("targets") or []), str(e.get("targets")))
        check("row 43050447566 original undiagnosed field is KEPT (append-only, rule 3b)",
              "undiagnosed" in e, "")
    # The post-merge gate shape: #830 CLOSED with its row named -> green, beside the siblings.
    rc, lines = verdict(committed["failures"],
                        states([(43050447566, 830, "CLOSED"), (42973469114, 825, "CLOSED"),
                                (41929086636, 823, "CLOSED"), (41956933757, 824, "CLOSED"),
                                (43049550731, 829, "CLOSED"), (41788683672, 820, "CLOSED"),
                                (41860616772, 821, "CLOSED"), (41922211098, 822, "CLOSED"),
                                (43088760321, 800, "CLOSED")]))
    check("the committed ledger with #830 CLOSED passes the gate", rc == 0, str(lines))

def test_run_43108536309_is_rediagnosed_onto_the_landed_openspec_binding_fix() -> None:
    print("\n#831: the issue-bot record-pr refusal row names the landed binding fix (rule 6r)")
    committed = json.loads(COMMITTED_LEDGER.read_text())
    row = [e for e in committed["failures"] if e["run_id"] == 43108536309]
    check("row 43108536309 exists in the committed ledger", len(row) == 1, str(row))
    if row:
        e = row[0]
        check("row 43108536309 names fix PR #955 (the landed openspec-binding-check fix)",
              e.get("fix_pr") == 955, str(e.get("fix_pr")))
        check("row 43108536309 names a guard test that exists on disk",
              G.guard_test_exists(e.get("guard") or "")
              and e.get("guard") == "tests/test_openspec_binding.py",
              str(e.get("guard")))
        check("row 43108536309 diagnosis quotes the record-pr refusal the log carries",
              "openspec-record-pr" in (e.get("error_excerpt") or "")
              and "REFUSED" in (e.get("error_excerpt") or ""),
              str(e.get("error_excerpt")))
        check("row 43108536309 targets name the target the log names (rule 3b)",
              "openspec-record-pr" in str(e.get("targets") or []), str(e.get("targets")))
        check("row 43108536309 original undiagnosed field is KEPT (append-only, rule 3b)",
              "undiagnosed" in e, "")
    # The post-merge gate shape: #831 CLOSED with its row named -> green, beside the siblings.
    rc, lines = verdict(committed["failures"],
                        states([(43108536309, 831, "CLOSED"), (42973469114, 825, "CLOSED"),
                                (41929086636, 823, "CLOSED"), (41956933757, 824, "CLOSED"),
                                (43049550731, 829, "CLOSED"), (41788683672, 820, "CLOSED"),
                                (41860616772, 821, "CLOSED"), (41922211098, 822, "CLOSED"),
                                (43088760321, 800, "CLOSED")]))
    check("the committed ledger with #831 CLOSED passes the gate", rc == 0, str(lines))

def test_run_43109817750_is_rediagnosed_onto_the_landed_sweep_alarm_fix() -> None:
    print("\n#832: the queued-alarm sweep-alarm row names the landed fix PR + guard (rule 6r)")
    committed = json.loads(COMMITTED_LEDGER.read_text())
    row = [e for e in committed["failures"] if e["run_id"] == 43109817750]
    check("row 43109817750 exists in the committed ledger", len(row) == 1, str(row))
    if row:
        e = row[0]
        check("row 43109817750 names fix PR #806 (the #801 in-flight misgrade fix)",
              e.get("fix_pr") == 806, str(e.get("fix_pr")))
        check("row 43109817750 names a guard test that exists on disk",
              G.guard_test_exists(e.get("guard") or "") and e.get("guard") == "tests/test_sweep_alarm.py",
              str(e.get("guard")))
        check("row 43109817750 diagnosis names the measured in-flight verdict line",
              "in_progress" in (e.get("error_excerpt") or ""), str(e.get("error_excerpt"))[:200])
        check("row 43109817750 targets were GROWN to the parseable target (rule 3b)",
              "sweep-alarm" in (e.get("targets") or []), str(e.get("targets")))
        check("row 43109817750 original undiagnosed field is KEPT (append-only, rule 3b)",
              "undiagnosed" in e, "")
    # The exact post-merge gate shape: #832 CLOSED with its row named -> green, beside the siblings.
    rc, lines = verdict(committed["failures"],
                        states([(43109817750, 832, "CLOSED"), (43050447566, 830, "CLOSED"),
                                (42973469114, 825, "CLOSED"), (41929086636, 823, "CLOSED"),
                                (41956933757, 824, "CLOSED"), (43049550731, 829, "CLOSED"),
                                (41788683672, 820, "CLOSED"), (41860616772, 821, "CLOSED"),
                                (41922211098, 822, "CLOSED"), (43088760321, 800, "CLOSED")]))
    check("the committed ledger with #832 CLOSED passes the gate", rc == 0, str(lines))


def test_log_expired_row_is_reported_as_its_own_shape_never_red() -> None:
    print("\nlog_expired (issue #986): a row whose log aged out of retention is its OWN shape, never red")
    expired = {"run_id": 200, "workflow": "qa-validate.yml", "job": "validate",
               "issue_number": 91, "fix_pr": None, "guard": None,
               "undiagnosed": "log fetch failed twice", "rediagnose_attempts": 3,
               "log_expired": "log still unreadable: aged out", "filed_utc": "2026-11-11T21:00:00Z"}
    for issue_state in ("OPEN", "CLOSED"):
        rc, lines = verdict([dict(expired)], states([(200, 91, issue_state)]))
        check(f"log_expired row with {issue_state} issue -> exit 0 (never red)", rc == 0, str(lines))
        check("reported as the log_expired shape, not a generic in-flight line",
              any("log_expired" in line and "TERMINAL" in line for line in lines), str(lines))
        check("a CLOSED log_expired issue is NOT the closed-without-guard refusal",
              not any("closed without a fix PR" in line for line in lines), str(lines))
    # A log_expired row with NO issue number is still reported as its own shape.
    rc2, lines2 = verdict([dict(expired, issue_number=None)], states([]))
    check("log_expired row with no issue -> exit 0, its own shape", rc2 == 0
          and any("log_expired" in line for line in lines2), str(lines2))


def test_fix_in_flight_is_reported_never_red() -> None:
    print("\nin flight: an OPEN issue with no fix PR yet is a report, not a red")
    rc, lines = verdict([entry(104, 55, None, None)], states([(104, 55, "OPEN")]))
    check("open issue -> exit 0", rc == 0, str(lines))
    check("reported as fix in flight", any("fix in flight" in line for line in lines), str(lines))
    # An issue whose state could not be read is indeterminate — never counted as closed.
    rc2, lines2 = verdict([entry(105, 56, None, None)], states([]), repo=None)
    check("unreadable issue state -> exit 0, INDETERMINATE report", rc2 == 0
          and any("INDETERMINATE" in line for line in lines2), str(lines2))
    # An undiagnosed filing (no issue number) is a pending report, not a red.
    rc3, lines3 = verdict([entry(106, None, None, None, undiagnosed=True)], states([]))
    check("undiagnosed pending entry -> exit 0 with a pending report", rc3 == 0
          and any("pending" in line for line in lines3), str(lines3))


def test_closed_marker_issue_the_ledger_never_recorded_is_red() -> None:
    print("\nstale ledger: a CLOSED marker issue with no ledger entry is red (append must land)")
    rc, lines = verdict([entry(107, 57, 903, "tests/test_pipeline_failure_guard.py")],
                        states([(107, 57, "CLOSED"), (999, 77, "CLOSED")]))
    check("closed marker run absent from the ledger -> exit 1", rc == 1, str(lines))
    check("the refusal names the missing ledger append",
          any("CLOSED but the ledger records nothing" in line for line in lines), str(lines))
    # Same marker issue but OPEN: the append is still in flight — reported, not red.
    rc2, lines2 = verdict([entry(108, 58, None, None)], states([(108, 58, "OPEN"),
                                                                (999, 77, "OPEN")]))
    check("OPEN marker run absent from the ledger -> exit 0", rc2 == 0, str(lines2))


def test_guard_test_lookup_is_the_shape_make_test_collects() -> None:
    print("\nguard lookup: only a tests/test_*.py the runner actually collects counts")
    check("this very test file counts as a guard",
          G.guard_test_exists("tests/test_pipeline_failure_guard.py"), "")
    check("a test::name form resolves to its module",
          G.guard_test_exists("tests/test_pipeline_failure_guard.py::test_x"), "")
    check("a path outside tests/ is not a guard", G.guard_test_exists("scripts/validate.py")
          is False, "")
    check("a promised file that does not exist is not a guard",
          G.guard_test_exists("tests/test_promised_but_absent.py") is False, "")
    check("an empty guard is not a guard", G.guard_test_exists("") is False, "")


def test_unreadable_ledger_exits_2_end_to_end() -> None:
    print("\nend to end: a missing or corrupt ledger exits 2 loudly, never a silent clean")
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        proc = subprocess.run([sys.executable, str(GUARD_SCRIPT),
                               "--repo", "octo/repo", "--ledger", str(tmp / "absent.json")],
                              capture_output=True, text=True, timeout=60)
        check("missing ledger -> exit 2 naming the file", proc.returncode == 2
              and "does not exist" in proc.stderr, f"{proc.returncode}\n{proc.stderr}")
        bad = tmp / "bad.json"
        bad.write_text("{ this is not json")
        proc2 = subprocess.run([sys.executable, str(GUARD_SCRIPT),
                                "--repo", "octo/repo", "--ledger", str(bad)],
                               capture_output=True, text=True, timeout=60)
        check("corrupt ledger -> exit 2", proc2.returncode == 2, f"{proc2.returncode}\n{proc2.stderr}")
        shaped = tmp / "notalist.json"
        shaped.write_text(json.dumps({"failures": "not a list"}))
        proc3 = subprocess.run([sys.executable, str(GUARD_SCRIPT),
                                "--repo", "octo/repo", "--ledger", str(shaped)],
                               capture_output=True, text=True, timeout=60)
        check("a ledger of the wrong shape -> exit 2", proc3.returncode == 2,
              f"{proc3.returncode}\n{proc3.stderr}")


def test_gate_is_wired_into_qa_validate_and_the_gate_registry() -> None:
    print("\nwiring: qa-validate runs the gate, the Makefile owns the target, §6q/6r name it")
    check("Makefile defines the gate target", "pipeline-failure-guard-check:" in MAKEFILE.read_text(),
          "")
    check("qa-validate's validate job runs it through the Makefile",
          "make pipeline-failure-guard-check" in QA_WF.read_text(), "")
    import master_alarm
    named = (set(getattr(master_alarm, "GATES", ()))
             | set(getattr(master_alarm, "ALARM_ONLY", ()))
             | set(getattr(master_alarm, "KEEPER", ())))
    check("the gate is named in the master_alarm gate registry (rule 6q/6r)",
          "pipeline-failure-guard-check" in named, str(sorted(named)))


def test_run_43110467252_is_raised_onto_the_landed_implement_guard() -> None:
    print("\nraised row: run 43110467252 (issue #833) names fix PR #1057 beside its guard (keeper raise)")
    committed = json.loads(COMMITTED_LEDGER.read_text())
    row = [e for e in committed["failures"] if e["run_id"] == 43110467252]
    check("the row exists in the committed ledger", len(row) == 1, str(row))
    if not row:
        return
    e = row[0]
    check("the row names fix PR #1057 (the landed #833 implementation)",
          e.get("fix_pr") == 1057, str(e.get("fix_pr")))
    check("the row names a guard test that exists on disk",
          G.guard_test_exists(e.get("guard") or "") and e.get("guard") == "tests/test_implement_stream.py",
          str(e.get("guard")))
    check("the original undiagnosed field is KEPT (append-only, rule 3b)", "undiagnosed" in e, "")
    check("the re-diagnosis fields are KEPT (append-only, rule 3b)",
          "rediagnosed_utc" in e and "rediagnosis_note" in e, "")
    # The exact post-merge gate shape: issue CLOSED, row names fix PR + real guard -> green.
    rc, lines = verdict(committed["failures"],
                        states([(43110467252, 833, "CLOSED"), (43088760321, 800, "CLOSED")]))
    check("the committed ledger with issue #833 CLOSED passes the gate", rc == 0, str(lines))


def test_the_nov15_ledger_rows_are_classified_onto_their_landed_guards() -> None:
    print("\nraised rows: the five Nov-15 red-run rows name their landed fix PR + guard (keeper classification, issues #1039-#1043)")
    committed = json.loads(COMMITTED_LEDGER.read_text())
    index = {e["run_id"]: e for e in committed["failures"]}
    expect = {
        43147240875: (922, "tests/test_owed_rows.py"),
        43716345030: (1082, "tests/test_openspec_index_repair.py"),
        43716362366: (1082, "tests/test_openspec_index_repair.py"),
        43718826142: (1082, "tests/test_openspec_index_repair.py"),
        43725338063: (1082, "tests/test_openspec_index_repair.py"),
    }
    for rid, (pr, guard) in expect.items():
        row = index.get(rid)
        check(f"run {rid} exists in the committed ledger", row is not None, "")
        if row is None:
            continue
        check(f"run {rid} names fix PR #{pr} (merged)", row.get("fix_pr") == pr, str(row.get("fix_pr")))
        check(f"run {rid} names guard {guard} (a module make test collects)",
              row.get("guard") == guard and G.guard_test_exists(guard), str(row.get("guard")))
        check(f"run {rid} keeps the filer's original fields (append-only, rule 3b)",
              "undiagnosed" in row and "targets" in row and "created_utc" in row
              and "issue_number" in row and "filed_utc" in row, "")
    # The post-merge gate shape: every row classified, every issue CLOSED -> green.
    five = [index[rid] for rid in expect]
    closed = states([(rid, index[rid]["issue_number"], "CLOSED") for rid in expect])
    rc, lines = verdict(five, closed)
    check("the five classified rows pass the gate with all five issues CLOSED", rc == 0, str(lines))
    # RED-before-classification: the same rows with the filer's nulls restored go red beside
    # CLOSED issues — the raise is what the #993 close-with-proof verdict reads (rule 6c).
    nullified = []
    for e in five:
        e2 = dict(e)
        e2["fix_pr"] = None
        e2["guard"] = None
        nullified.append(e2)
    rc_old, lines_old = verdict(nullified, closed)
    check("unclassified null rows are RED with CLOSED issues (proven against the pre-raise shape)",
          rc_old == 1 and all("CLOSED without a fix PR" in line for line in lines_old), str(lines_old))


def test_a_closed_row_the_stamp_raised_with_fix_pr_and_guard_clears_the_gate() -> None:
    print("\nstamp lands (#1099): the SAME closed row is red unstamped and green stamped")
    # The state every closed ledger row sat in before the stamp pass existed: the fix merged,
    # the issue closed, and fix_pr/guard still null — permanently red at this gate.
    rc0, lines0 = verdict([entry(450, 931, None, None)], states([(450, 931, "CLOSED")]))
    check("the unraised closed row is RED (the #1099 defect state)",
          rc0 == 1 and any("CLOSED without a fix PR or a guard test" in line for line in lines0),
          str(lines0))
    # The exact row shape `make pipeline-failure-issue`'s stamp pass writes when the merged,
    # guard-carrying PR that closed the issue is observed: fix_pr/guard raised additively.
    raised = entry(450, 931, 940, "tests/test_pipeline_failure_guard.py")
    raised["fix_pr_merged_utc"] = "2026-11-12T09:00:00Z"
    raised["stamp_utc"] = "2026-11-17T06:00:00Z"
    raised["stamp_note"] = ("fix_pr raised by make pipeline-failure-issue's stamp pass "
                            "(issue #1099) from closed issue #931 closed by merged PR #940")
    rc1, lines1 = verdict([raised], states([(450, 931, "CLOSED")]))
    check("the same run's row after the stamp pass raised it is GREEN", rc1 == 0, str(lines1))
    check("the added stamp keys never upset the gate's reader (additive, rule 3b)",
          any("diagnosed" in line for line in lines1) or not lines1, str(lines1))


def test_a_stamped_row_whose_named_guard_no_longer_exists_is_red() -> None:
    print("\nstamp integrity (#1099): a raised guard naming no collected test never clears the gate")
    # The stamp pass raises `guard` from the merged PR's tests/ diff; if that module is later
    # deleted, the row must go RED again — the stamp satisfies the gate only while the named
    # guard is a test the real runner collects.
    raised = entry(452, 933, 942, "tests/test_the_removed_regression_guard.py")
    raised["fix_pr_merged_utc"] = "2026-11-12T09:00:00Z"
    raised["stamp_utc"] = "2026-11-17T06:00:00Z"
    raised["stamp_note"] = "fix_pr raised by make pipeline-failure-issue's stamp pass (issue #1099)"
    rc, lines = verdict([raised], states([(452, 933, "CLOSED")]))
    check("fix_pr raised but the named guard file is absent -> refusal, exit 1",
          rc == 1 and any("guard" in line for line in lines), str(lines))
    check("the refusal names the missing guard module",
          any("test_the_removed_regression_guard" in line for line in lines), str(lines))


def test_a_stamped_row_with_no_error_block_is_its_own_report_never_red() -> None:
    """Issue #1136: attributed-without-a-diagnosis is a DISTINGUISHED report, never silence."""
    print("\nstamp vs diagnosis (#1136): a fix PR + guard with no error block is its own class")
    # A row the stamp pass raised (fix_pr + a collected guard) while carrying NO error block —
    # the exact shape of the five rows issues #1039-#1043 observed.
    stamped = entry(470, 1039, 1044, "tests/test_pipeline_failure_guard.py", excerpt=None)
    stamped["stamp_utc"] = "2026-11-17T06:00:00Z"
    rc, lines = verdict([stamped], states([(470, 1039, "CLOSED")]))
    check("attributed-without-a-diagnosis is NEVER red (its guard did land)", rc == 0, str(lines))
    check("it is reported as its OWN class naming the missing error block",
          any("attributed" in line and "NO error block" in line for line in lines), str(lines))
    check("the report names the seam that recovers the text",
          any("rediagnose_pending" in line for line in lines), str(lines))
    check("the summary counts it as attributed-without-a-diagnosis, not as diagnosed",
          any(line.startswith("0 diagnosed failure")
              and "1 attributed without a diagnosis" in line for line in lines), str(lines))
    # The SAME row once the diagnosis has landed is the diagnosed class — counted, never reported.
    full = entry(470, 1039, 1044, "tests/test_pipeline_failure_guard.py")
    rc2, lines2 = verdict([full], states([(470, 1039, "CLOSED")]))
    check("the diagnosed row is green with no pending-diagnosis report",
          rc2 == 0 and not any("NO error block" in line for line in lines2), str(lines2))
    check("the summary names it as 1 diagnosed failure closed with a fix PR + guard test",
          any(line.startswith("1 diagnosed failure") for line in lines2), str(lines2))
    # A row that claims a fix while its issue is still OPEN is the same class (never red).
    rc3, lines3 = verdict([stamped], states([(470, 1039, "OPEN")]))
    check("open issue + fix PR + no error block -> its own report, exit 0",
          rc3 == 0 and any("NO error block" in line for line in lines3), str(lines3))
    # The class NEVER hides the refusals the gate exists for.
    rc4, lines4 = verdict([stamped, entry(471, 1040, 1045, "tests/test_never_landed.py")],
                          states([(470, 1039, "CLOSED"), (471, 1040, "CLOSED")]))
    check("a real refusal is still red beside the class report",
          rc4 == 1 and any("never_landed" in line for line in lines4), str(lines4))


def test_the_committed_ledger_classifies_its_five_errorless_rows() -> None:
    """Issue #1136 on the shipped ledger: green, with the five rows named as their own class."""
    print("\nstamp vs diagnosis (#1136): the shipped ledger's five rows are named, not silent")
    data = json.loads(COMMITTED_LEDGER.read_text())
    measured = {43147240875, 43716345030, 43716362366, 43718826142, 43725338063}
    # Only the STAMPED rows get a state (the convention the committed-ledger tests already use):
    # a row with no fix claim is a fix in flight — the gate reports it, it cannot be red on a
    # fixture's guess about whether its issue happens to be open today (rule 6m: no live state in
    # a fixture). The five measured rows ARE stamped, so they are exercised as CLOSED here.
    states_map = {str(e["run_id"]): {"number": e.get("issue_number"), "state": "CLOSED"}
                  for e in data["failures"] if e.get("fix_pr") and e.get("issue_number")}
    rc, lines = G.verdict(data, None, states_map)
    check("the shipped ledger clears the gate (rc 0)", rc == 0, "\n".join(lines)[:800])
    named = {line for line in lines if "NO error block" in line}
    check("exactly the five measured runs are named as attributed-without-a-diagnosis",
          len(named) == 5 and all(any(str(rid) in line for line in named) for rid in measured),
          "\n".join(sorted(named))[:800])
    check("the summary counts 12 diagnosed and 5 attributed-without-a-diagnosis",
          any(line.startswith("12 diagnosed failure")
              and "5 attributed without a diagnosis" in line for line in lines),
          "\n".join(lines)[-400:])


def main() -> int:
    print("pipeline failure guard: closing a diagnosed failure without a test is RED (issue #802)")
    test_closed_without_guard_is_red()
    test_closed_with_landed_fix_and_guard_is_green()
    test_a_closed_row_the_stamp_raised_with_fix_pr_and_guard_clears_the_gate()
    test_a_stamped_row_whose_named_guard_no_longer_exists_is_red()
    test_a_stamped_row_with_no_error_block_is_its_own_report_never_red()
    test_the_committed_ledger_classifies_its_five_errorless_rows()
    test_run_41788683672_is_rediagnosed_with_its_landed_guard()
    test_run_41860616772_is_rediagnosed_with_its_landed_guard()
    test_run_41922211098_is_rediagnosed_with_its_landed_guard()


    test_run_41956933757_and_43049550731_are_rediagnosed_onto_the_landed_sweep_alarm_fix()
    test_run_41929086636_is_rediagnosed_onto_the_cancelled_delivery_guard()
    test_run_42973469114_is_rediagnosed_onto_the_landed_openspec_binding_fix()
    test_run_43050447566_is_rediagnosed_onto_the_landed_trending_guard()
    test_run_43108536309_is_rediagnosed_onto_the_landed_openspec_binding_fix()
    test_run_43109817750_is_rediagnosed_onto_the_landed_sweep_alarm_fix()
    test_run_43110467252_is_raised_onto_the_landed_implement_guard()
    test_the_nov15_ledger_rows_are_classified_onto_their_landed_guards()
    test_fix_in_flight_is_reported_never_red()
    test_log_expired_row_is_reported_as_its_own_shape_never_red()
    test_closed_marker_issue_the_ledger_never_recorded_is_red()
    test_guard_test_lookup_is_the_shape_make_test_collects()
    test_unreadable_ledger_exits_2_end_to_end()
    test_gate_is_wired_into_qa_validate_and_the_gate_registry()
    print(f"\nPASSED {_checks_passed} | FAILED {_checks_failed}")
    return 0 if _checks_failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
