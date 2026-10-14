#!/usr/bin/env python3
"""Tests for scripts/qa_report.sh — the refresh aggregate job's QA pass (#147).

The refresh must tell apart two kinds of non-zero exit:

  * the check RAN and has findings  -> report them, keep going, exit 0 (the data
    still lands as a PR for review);
  * the check COULD NOT RUN         -> fail the job (docker 125 = no image,
    127 = no such command).

Measured before the fix (run 38542951338, job aggregate): every image-dependent
QA target died with "Unable to find image 'trending-local-llms-test:latest'" and
the `|| echo` guards turned that into a green job.

The script runs real `make` targets, so the tests drive it with a real Makefile in
a temp directory — nothing about the script is replaced.
"""
from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "scripts" / "qa_report.sh"

_PASS = 0
_FAIL = 0


def check(name, cond, detail=""):
    global _PASS, _FAIL
    if cond:
        _PASS += 1
        print(f"  ok  {name}")
    else:
        _FAIL += 1
        print(f"  FAIL {name}" + (f"  [{detail}]" if detail else ""))


def _run(targets):
    """Run qa_report.sh against a temp Makefile with real targets."""
    with tempfile.TemporaryDirectory() as td:
        (Path(td) / "Makefile").write_text(
            "ok:\n\t@true\n"
            "findings:\n\t@echo 'FAIL: a data finding'; exit 1\n"
            "no_image:\n\t@echo \"Unable to find image 'x:latest' locally\"; exit 125\n"
            "no_command:\n\t@exit 127\n"
        )
        return subprocess.run(
            ["bash", str(SCRIPT), *targets], cwd=td, capture_output=True, text=True
        )


def test_script_exists_and_is_executable_by_bash():
    check("qa_report.sh: present", SCRIPT.is_file(), str(SCRIPT))
    src = SCRIPT.read_text()
    # `make` collapses a failed recipe to its own exit 2, so the cannot-run state
    # is read from the recipe's status in the output plus docker's own messages.
    check("qa_report.sh: it reads the cannot-run evidence from the output",
          "Unable to find image" in src and "Error (125|127)" in src
          and "could not run" in src, "")
    check("qa_report.sh: a sub-make's `make[1]:` prefix is matched too",
          r"make(\[[0-9]+\])?" in src, "")


def test_findings_are_reported_not_failed():
    """A check that RAN and found a problem is reported; the job stays green so
    the merged data lands for review."""
    # Given a QA target that runs and reports a finding
    r = _run(["ok", "findings"])

    # Then  the script exits 0 and says the finding was reported
    check("findings: exit 0 (data still lands)", r.returncode == 0, r.stdout + r.stderr)
    check("findings: the finding is reported",
          "reported findings" in r.stdout, r.stdout)
    check("findings: both targets ran", r.stdout.count("== qa-report: make") == 2, r.stdout)


def test_cannot_run_fails_the_job():
    """A target that could not run (no image / no command) is a harness failure."""
    # Given a QA target whose docker run fails with 125 (image missing)
    r = _run(["no_image"])

    # Then  the job fails and names the state explicitly
    check("cannot-run 125: exit 1", r.returncode == 1, r.stdout + r.stderr)
    check("cannot-run 125: names the harness failure",
          "could not run" in r.stdout + r.stderr and "::error::" in r.stdout, r.stdout)

    # Given a QA target that is not even a command (127)
    r = _run(["no_command"])

    # Then  it is a harness failure too
    check("cannot-run 127: exit 1", r.returncode == 1, r.stdout + r.stderr)


def test_one_cannot_run_target_fails_after_the_others_report():
    """A run with both kinds is a failure: green must mean every check ran."""
    # Given a pass, a finding and a target that could not run
    r = _run(["ok", "findings", "no_image"])

    # Then  all three are attempted, the finding is reported, and the job fails
    check("mixed: exit 1 (one could not run)", r.returncode == 1, r.stdout + r.stderr)
    check("mixed: the later finding was still reported",
          "reported findings" in r.stdout, r.stdout)
    check("mixed: the report line is replaced by the failure",
          "did NOT run" in r.stdout + r.stderr, r.stdout)


def test_workflow_uses_the_target_and_keeps_no_soft_guard():
    """The refresh aggregate job reports findings THROUGH the script instead of
    `|| echo`-ing every QA target (issue #147)."""
    wf = (ROOT / ".github" / "workflows" / "refresh-bot.yml").read_text()
    check("refresh-bot: the aggregate QA pass runs `make qa-report`",
          "make qa-report" in wf, "")
    check("refresh-bot: no `|| echo` soft-guard around the QA targets",
          "make validate ||" not in wf and "make test ||" not in wf, "")
    mk = (ROOT / "Makefile").read_text()
    check("make: `qa-report` exists and runs the script",
          "qa-report:\n\tbash scripts/qa_report.sh $(QA_REPORT_TARGETS)" in mk, "")
    check("make: it covers the QA targets the aggregate job needs",
          "QA_REPORT_TARGETS := validate validate-search validate-fetch validate-mapped test" in mk, "")


def main() -> int:
    print("refresh aggregate QA pass (findings reported, harness failures fatal)")
    test_script_exists_and_is_executable_by_bash()
    test_findings_are_reported_not_failed()
    test_cannot_run_fails_the_job()
    test_one_cannot_run_target_fails_after_the_others_report()
    test_workflow_uses_the_target_and_keeps_no_soft_guard()
    print(f"\nPASSED {_PASS} | FAILED {_FAIL}")
    return 1 if _FAIL else 0


if __name__ == "__main__":
    raise SystemExit(main())
