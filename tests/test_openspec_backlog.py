#!/usr/bin/env python3
"""The ACTIVE OpenSpec backlog has a hard 50-change ceiling at the merge gate (issue #938).

Drives the REAL `scripts/openspec_backlog_check.py` against planted fixture trees
(external system only — a fixture directory, rule 6m), and the REAL Makefile +
qa-validate wiring. A planted fixture that passes silently is the defect this
suite exists to prevent.

Run:  python3 tests/test_openspec_backlog.py   or   make test
"""
from __future__ import annotations

import re
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "scripts" / "openspec_backlog_check.py"

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


def run(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(SCRIPT), *args],
                          text=True, capture_output=True, timeout=120)


def plant(changes_dir: Path, n_active: int, n_archived: int = 0) -> None:
    """A fixture openspec/changes tree: n_active active changes (each with a
    proposal.md carrying an Issue line), n_archived under archive/."""
    changes_dir.mkdir(parents=True, exist_ok=True)
    for i in range(n_active):
        c = changes_dir / f"change-{i:03d}"
        c.mkdir()
        (c / "proposal.md").write_text(
            f"# Proposal: change-{i:03d}\n\nIssue: tech-debt — planted fixture #{1000 + i}\n")
    if n_archived:
        arch = changes_dir / "archive"
        arch.mkdir(exist_ok=True)
        for i in range(n_archived):
            a = arch / f"archived-{i:03d}"
            a.mkdir()
            (a / "proposal.md").write_text(f"Issue: #{9000 + i}\n")


def test_exactly_at_the_cap_is_red():
    with tempfile.TemporaryDirectory() as tmp:
        changes = Path(tmp) / "changes"
        plant(changes, 50, n_archived=3)
        out = run("--changes-dir", str(changes))
        check("exactly 50 active goes red (exit 1)", out.returncode == 1, out.stdout)
        body = out.stdout
        check("the failure names the cap and the count", "reached the cap 50" in body, body)
        check("every active change is named", body.count("  - change-") == 50, body)
        check("each entry carries its Issue", "#1000" in body and "#1049" in body)
        check("the remedy is exact per change",
              "make openspec-archive NAME=change-000" in body
              and "openspec-record-pr ISSUE=1000" in body, body)
        check("the merge-gate consequence is stated", "blocks auto-merge" in body)


def test_over_the_cap_is_still_red():
    """The cap is a ceiling, not a one-hit gate: 51 active must stay red too."""
    with tempfile.TemporaryDirectory() as tmp:
        changes = Path(tmp) / "changes"
        plant(changes, 51)
        out = run("--changes-dir", str(changes))
        check("51 active is still red", out.returncode == 1, out.stdout)
        check("the count says 51", "51 ACTIVE OpenSpec change(s)" in out.stdout, out.stdout)


def test_headroom_is_reported():
    with tempfile.TemporaryDirectory() as tmp:
        changes = Path(tmp) / "changes"
        plant(changes, 49)
        out = run("--changes-dir", str(changes))
        check("49 active is green", out.returncode == 0, out.stdout + out.stderr)
        check("headroom is printed, never silent", "active=49/50" in out.stdout, out.stdout)


def test_archived_changes_never_count():
    with tempfile.TemporaryDirectory() as tmp:
        changes = Path(tmp) / "changes"
        plant(changes, 2, n_archived=60)
        out = run("--changes-dir", str(changes))
        check("60 archived + 2 active is green", out.returncode == 0, out.stdout + out.stderr)
        check("the count is the ACTIVE count only", "active=2/50" in out.stdout, out.stdout)


def test_missing_tree_is_loud():
    with tempfile.TemporaryDirectory() as tmp:
        out = run("--changes-dir", str(Path(tmp) / "no-such-tree"))
        check("a missing changes tree exits 2 (never a vacuous clean)",
              out.returncode == 2, out.returncode)
        check("the refusal names the missing tree",
              "no-such-tree" in out.stderr and "refuses" in out.stderr, out.stderr)


def test_the_cap_gates_the_merge_pipeline():
    makefile = (ROOT / "Makefile").read_text()
    m = re.search(r"^openspec-check:\s*([^\n#]*)", makefile, re.M)
    check("openspec-backlog-check is a prerequisite of openspec-check",
          m is not None and "openspec-backlog-check" in m.group(1), m and m.group(1))
    check("the target runs the ONE script through the Makefile (rule 6m)",
          re.search(r"^openspec-backlog-check:.*\n\t.*python3 scripts/openspec_backlog_check\.py",
                    makefile, re.M) is not None)
    check("the target is .PHONY-declared like its siblings",
          "openspec-backlog-check" in re.search(r"\.PHONY:.*openspec", makefile).group(0))
    qa = (ROOT / ".github" / "workflows" / "qa-validate.yml").read_text()
    check("qa-validate gates on make openspec-check (where the cap bites)",
          re.search(r"run:\s*make openspec-check\b", qa) is not None)


def test_the_real_tree_is_under_the_cap():
    """Production check: today's backlog must be green AND report its headroom."""
    out = run()
    check("the real repo backlog passes the cap today", out.returncode == 0,
          out.stdout + out.stderr)
    m = re.search(r"active=(\d+)/50", out.stdout)
    check("the real headroom line is printed", m is not None, out.stdout)


def main() -> int:
    for t in (test_headroom_is_reported,
              test_archived_changes_never_count,
              test_exactly_at_the_cap_is_red,
              test_over_the_cap_is_still_red,
              test_missing_tree_is_loud,
              test_the_cap_gates_the_merge_pipeline,
              test_the_real_tree_is_under_the_cap):
        print(f"\n[{t.__name__}]")
        t()
    print(f"\n{_PASS} passed, {_FAIL} failed")
    return 1 if _FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
