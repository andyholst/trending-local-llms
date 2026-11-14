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


def entry(run_id: int, issue, fix_pr, guard, undiagnosed: bool = False) -> dict:
    return {"run_id": run_id, "workflow": "qa-validate.yml", "job": "validate",
            "issue_number": issue, "fix_pr": fix_pr, "guard": guard,
            "undiagnosed": undiagnosed, "filed_utc": "2026-11-11T21:00:00Z"}


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


def main() -> int:
    print("pipeline failure guard: closing a diagnosed failure without a test is RED (issue #802)")
    test_closed_without_guard_is_red()
    test_closed_with_landed_fix_and_guard_is_green()
    test_run_41788683672_is_rediagnosed_with_its_landed_guard()
    test_fix_in_flight_is_reported_never_red()
    test_closed_marker_issue_the_ledger_never_recorded_is_red()
    test_guard_test_lookup_is_the_shape_make_test_collects()
    test_unreadable_ledger_exits_2_end_to_end()
    test_gate_is_wired_into_qa_validate_and_the_gate_registry()
    print(f"\nPASSED {_checks_passed} | FAILED {_checks_failed}")
    return 0 if _checks_failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
