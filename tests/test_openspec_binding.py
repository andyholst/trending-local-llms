#!/usr/bin/env python3
"""Every ACTIVE OpenSpec change binds the Issue its PR closes — BEFORE the
record step can refuse (issue #952).

Drives the REAL `scripts/openspec_binding_check.py` against planted fixture
trees (external system only — a fixture directory, rule 6m) and the REAL
Makefile + qa-validate wiring. The measured failure this suite locks out: the
2026-11-12 weekly sweep (run 43147959554) implemented an issue for ~30
minutes, then died at `make openspec-record-pr` — `REFUSED: no change —
active or archived — references Issue: #624` — because the agent's change was
created with no `Issue:` binding and NOTHING noticed until the last step.
A planted unbound ACTIVE change that passes silently is the defect.

Run:  python3 tests/test_openspec_binding.py   or   make test
"""
from __future__ import annotations

import re
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "scripts" / "openspec_binding_check.py"

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


def plant(changes_dir: Path, name: str, proposal: str | None) -> Path:
    c = changes_dir / name
    c.mkdir(parents=True)
    if proposal is not None:
        (c / "proposal.md").write_text(proposal)
    return c


# --- the planted shapes -----------------------------------------------------

def test_an_unbound_active_change_is_red():
    with tempfile.TemporaryDirectory() as tmp:
        changes = Path(tmp) / "changes"
        plant(changes, "sweep-authored-change",
              "# Proposal\n\n## Why\nThe sweep implemented an issue.\n")
        out = run("--changes-dir", str(changes))
        check("an ACTIVE change with no Issue line goes red (exit 1)",
              out.returncode == 1, out.returncode)
        check("the failure names the change", "sweep-authored-change" in out.stderr,
              out.stderr)
        check("the refusal is at the OPEN of the gate, naming the missing binding",
              "no Issue line" in out.stderr, out.stderr)
        check("the remedy is exact: add the binding or declare the exemption",
              "Issue: #<n>" in out.stderr and "Binding-exempt:" in out.stderr,
              out.stderr)


def test_plain_and_link_issue_spellings_both_bind():
    """The check parses through openspec_index._refs — the ONE Issue parser —
    so `Issue: #650` and `**Issue:** [#715](https://…)` are the same state."""
    with tempfile.TemporaryDirectory() as tmp:
        changes = Path(tmp) / "changes"
        plant(changes, "plain-issue", "Issue: #650 — a tracked gap\n\n## Why\n…\n")
        plant(changes, "link-issue",
              "**Issue:** [#715](https://github.com/o/r/issues/715) · holder **#741**\n\n## Why\n…\n")
        out = run("--changes-dir", str(changes))
        check("both spellings bind (exit 0)", out.returncode == 0, out.stdout + out.stderr)
        check("the count reports both bound", "bound=2" in out.stdout, out.stdout)


def test_an_issue_line_naming_no_issue_is_unbound():
    with tempfile.TemporaryDirectory() as tmp:
        changes = Path(tmp) / "changes"
        plant(changes, "issue-less-issue-line", "Issue: tech-debt — planted fixture\n\n## Why\n…\n")
        out = run("--changes-dir", str(changes))
        check("an Issue line without #<n> is red", out.returncode == 1, out.returncode)
        check("the detail says the line names no issue",
              "names no issue" in out.stderr, out.stderr)


def test_the_declared_keeper_exemption_stays_green_and_is_reported():
    with tempfile.TemporaryDirectory() as tmp:
        changes = Path(tmp) / "changes"
        plant(changes, "keeper-index-regeneration",
              "# Proposal\n\nBinding-exempt: keeper — this change implements no issue (rule 6e)\n\n## Why\n…\n")
        out = run("--changes-dir", str(changes))
        check("a declared exemption is green", out.returncode == 0, out.stdout + out.stderr)
        check("the exemption is REPORTED, never silent",
              "exempt: keeper-index-regeneration" in out.stdout, out.stdout)
        check("the declared reason is quoted", "implements no issue" in out.stdout,
              out.stdout)


def test_silence_is_never_the_default_for_an_unbound_change():
    """An unbound change with prose that merely MENTIONS keeping is still red:
    only the registered `Binding-exempt:` line exempts."""
    with tempfile.TemporaryDirectory() as tmp:
        changes = Path(tmp) / "changes"
        plant(changes, "silent-keeper",
              "# Proposal\n\nThis change is a keeper, we keep things.\n\n## Why\n…\n")
        out = run("--changes-dir", str(changes))
        check("prose about keeping does not exempt", out.returncode == 1, out.returncode)


def test_archive_only_tree_is_green():
    """ARCHIVED changes are out of scope — the historical unbound archives
    (the #952 evidence) must not red the gate retroactively."""
    with tempfile.TemporaryDirectory() as tmp:
        changes = Path(tmp) / "changes"
        arch = changes / "archive"
        (arch / "old-unbound").mkdir(parents=True)
        (arch / "old-unbound" / "proposal.md").write_text("# Proposal\n\n## Why\n…\n")
        out = run("--changes-dir", str(changes))
        check("an unbound ARCHIVED change never reds the gate",
              out.returncode == 0, out.stdout + out.stderr)
        check("zero active is reported as zero", "of 0 active" in out.stdout, out.stdout)


def test_a_change_without_a_proposal_is_red():
    with tempfile.TemporaryDirectory() as tmp:
        changes = Path(tmp) / "changes"
        plant(changes, "proposal-less", None)
        out = run("--changes-dir", str(changes))
        check("no proposal.md at all is red", out.returncode == 1, out.returncode)
        check("the detail says the proposal is missing",
              "no proposal.md" in out.stderr, out.stderr)


def test_a_missing_tree_is_loud():
    with tempfile.TemporaryDirectory() as tmp:
        out = run("--changes-dir", str(Path(tmp) / "no-such-tree"))
        check("a missing changes tree exits 2 (never a vacuous clean)",
              out.returncode == 2, out.returncode)
        check("the refusal names the unreadable tree",
              "no-such-tree" in out.stderr, out.stderr)


# --- the real tree and the real wiring --------------------------------------

def test_the_real_active_changes_are_all_bound():
    """The shipped tree must pass the gate it ships with: every ACTIVE change —
    whatever it counts today — names its issue or declares the exemption."""
    out = run()
    check("the real openspec/changes tree is green", out.returncode == 0,
          out.stdout + out.stderr)
    m = re.search(r"OK: bound=(\d+) exempt=(\d+) of (\d+) active", out.stdout)
    check("the verdict counts every real active change as bound or exempt",
          m is not None and int(m.group(1)) + int(m.group(2)) == int(m.group(3)),
          out.stdout)
    if m:
        real_active = sum(1 for d in (ROOT / "openspec" / "changes").iterdir()
                          if d.is_dir() and d.name != "archive")
        check("the count matches the directories on disk",
              int(m.group(3)) == real_active, f"{m.group(3)} vs {real_active}")


def test_the_binding_check_gates_the_merge_pipeline():
    makefile = (ROOT / "Makefile").read_text(encoding="utf-8")
    m = re.search(r"^openspec-check:\s*(.*)$", makefile, re.MULTILINE)
    check("openspec-binding-check is a prerequisite of openspec-check",
          m is not None and "openspec-binding-check" in m.group(1), m and m.group(1))
    check("the target reaches the product through the Makefile only",
          re.search(r"^openspec-binding-check:.*\n\t.*python3 scripts/openspec_binding_check\.py",
                    makefile, re.MULTILINE) is not None)
    check("the target is .PHONY-registered",
          "openspec-binding-check" in re.search(r"^\.PHONY:.*openspec.*$", makefile,
                                                re.MULTILINE).group(0))
    qa = (ROOT / ".github" / "workflows" / "qa-validate.yml").read_text(encoding="utf-8")
    check("qa-validate's validate job still runs make openspec-check (which now runs this)",
          "make openspec-check" in qa, "no openspec-check call")
    check("the new target has no orphan workflow call",
          "openspec-binding-check" not in qa)


def main() -> int:
    for t in (test_an_unbound_active_change_is_red,
              test_plain_and_link_issue_spellings_both_bind,
              test_an_issue_line_naming_no_issue_is_unbound,
              test_the_declared_keeper_exemption_stays_green_and_is_reported,
              test_silence_is_never_the_default_for_an_unbound_change,
              test_archive_only_tree_is_green,
              test_a_change_without_a_proposal_is_red,
              test_a_missing_tree_is_loud,
              test_the_real_active_changes_are_all_bound,
              test_the_binding_check_gates_the_merge_pipeline):
        print(f"\n[{t.__name__}]")
        t()
    print(f"\n{_PASS} passed, {_FAIL} failed")
    return 1 if _FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
