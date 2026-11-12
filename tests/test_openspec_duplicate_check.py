#!/usr/bin/env python3
"""Behavioural tests for scripts/openspec_duplicate_check.py (issue #622).

`openspec validate` checks a change's STRUCTURE, `check_openspec_tasks.py` its
checklist, and `openspec_index.py` that it is indexed — none notice a SECOND
change proposing the same rule. Measured: `agents-md-footprint-dimensions`
(#375) and `the-owed-section-4-sentence` (#371, CLOSED) each declared an ADDED
Requirement for the SAME `AGENTS.md` §4 sentence, so a run could have landed it
twice or neither. This script is that gate; these tests drive the REAL script
against fixture change trees and assert the repository's own tree is clean.

Wired into `make test` (rule 6d).
"""
from __future__ import annotations

import importlib.util
import io
import os
import subprocess
import sys
import tempfile
from pathlib import Path

from wiring import wired  # noqa: E402  (issues #176/#192)

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "scripts" / "openspec_duplicate_check.py"

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


def _module():
    """The REAL script, imported by path (no copy of its logic in the test)."""
    spec = importlib.util.spec_from_file_location("openspec_duplicate_check", SCRIPT)
    assert spec and spec.loader, SCRIPT
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _spec(base, change, kind, *headings):
    """Write one capability spec declaring *headings* under *kind*.

    Openspec requires a capability directory (weDo not need `.openspec.yaml`
    for the duplicate gate — it reads only the specs/ tree).
    """
    d = base / change / "specs" / "the-capability"
    d.mkdir(parents=True, exist_ok=True)
    lines = [f"# the-capability", "", f"## {kind} Requirements", ""]
    for h in headings:
        lines += [f"### Requirement: {h}", "", "body text", ""]
    (d / "spec.md").write_text("\n".join(lines), encoding="utf-8")


def test_duplicate_added_heading_fails_naming_both():
    """Two changes both ADDing the same rule heading fail, naming both."""

    # Given the #375/#371 pair: two ACTIVE changes each ADD the same §4 heading
    mod = _module()
    with tempfile.TemporaryDirectory() as td:
        base = Path(td) / "changes"
        _spec(base, "agents-md-footprint-dimensions", "ADDED",
              "§4 names every optional per-measurement footprint dimension")
        _spec(base, "the-owed-section-4-sentence", "ADDED",
              "§4 names every optional per-measurement footprint dimension")

        # When  the duplicate gate runs over the active changes
        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = mod.check_all(base=base)
        out = buf.getvalue()

    # Then  it fails and names BOTH changes and the shared heading
    check("pair: gate exits non-zero", rc == 1, str(rc))
    check("pair: the first change is named", "agents-md-footprint-dimensions" in out, out)
    check("pair: the second change is named", "the-owed-section-4-sentence" in out, out)
    check("pair: the shared heading is named",
          "footprint dimension" in out, out)
    check("pair: it says both propose it",
          "both declare the requirement" in out, out)


def test_add_then_modify_is_a_chain_not_a_duplicate():
    """ADDED in one change + MODIFIED in another is a chain, never a duplicate."""

    # Given the firecrawl/outage shape: BUILD adds a heading, REFINE modifies it
    mod = _module()
    with tempfile.TemporaryDirectory() as td:
        base = Path(td) / "changes"
        _spec(base, "build", "ADDED",
              "the live check's verdict names the failure, and only an outage is non-blocking")
        _spec(base, "refine", "MODIFIED",
              "the live check's verdict names the failure, and only an outage is non-blocking")

        # When  the gate runs
        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = mod.check_all(base=base)
        out = buf.getvalue()

    # Then  it is green and never reports the chain
    check("chain: gate exits 0", rc == 0, str(rc) + " " + out)
    check("chain: neither change is reported", "build" not in out and "refine" not in out, out)


def test_duplicate_modified_heading_fails_naming_both():
    """Two changes both MODIFYing the same rule heading fail, naming both."""

    # Given two ACTIVE changes both rewriting one existing rule
    mod = _module()
    with tempfile.TemporaryDirectory() as td:
        base = Path(td) / "changes"
        _spec(base, "rewrite-a", "MODIFIED", "the §4 sentence is the one rule")
        _spec(base, "rewrite-b", "MODIFIED", "the §4 sentence is the one rule")

        # When  the gate runs
        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = mod.check_all(base=base)
        out = buf.getvalue()

    # Then  it fails and names both
    check("modified pair: gate exits non-zero", rc == 1, str(rc))
    check("modified pair: rewrite-a is named", "rewrite-a" in out, out)
    check("modified pair: rewrite-b is named", "rewrite-b" in out, out)


def test_distinct_headings_pass():
    """Unrelated changes with distinct requirements pass."""

    # Given several ACTIVE changes each proposing their own distinct rule
    mod = _module()
    with tempfile.TemporaryDirectory() as td:
        base = Path(td) / "changes"
        _spec(base, "pipeline-a", "ADDED", "every scheduled pipeline runs weekly")
        _spec(base, "pipeline-b", "ADDED", "a red cron pipeline is loud")
        _spec(base, "pipeline-c", "ADDED", "the queue reads both labels oldest-first")
        _spec(base, "chain", "MODIFIED", "a failed query does not unmask an outage")

        # When  the gate runs
        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = mod.check_all(base=base)
        out = buf.getvalue()

    # Then  it is green
    check("distinct: gate exits 0", rc == 0, str(rc) + " " + out)


def test_case_and_whitespace_insensitive():
    """The same rule written with different case/whitespace is still a duplicate."""

    mod = _module()
    with tempfile.TemporaryDirectory() as td:
        base = Path(td) / "changes"
        _spec(base, "a", "ADDED", "§4  names every  optional dimension.")
        _spec(base, "b", "ADDED", "§4 NAMES EVERY OPTIONAL DIMENSION")

        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = mod.check_all(base=base)
        out = buf.getvalue()

    check("case-insensitive: gate exits non-zero", rc == 1, str(rc))
    check("case-insensitive: both named", "a" in out and "b" in out, out)


def test_real_repo_has_no_same_kind_heading_duplicate():
    """The repository's own tree is clean: no two active changes share a same-kind heading."""

    # Given this repository's real openspec/changes tree
    mod = _module()

    # When  the gate runs over it (and the CLI runs as CI runs it)
    buf = io.StringIO()
    with redirect_stdout(buf):
        rc = mod.check_all()
    proc = subprocess.run([sys.executable, str(SCRIPT)], cwd=ROOT,
                          capture_output=True, text=True)

    # Then  it is green both ways
    check("real repo: no same-kind heading duplicate", rc == 0, buf.getvalue())
    check("real repo: the script's exit code is 0",
          proc.returncode == 0, proc.stdout + proc.stderr)


def test_wired_into_make_openspec_check():
    """The gate is reachable from a make target CI runs (rule 6d)."""

    # Given the Makefile
    mk = (ROOT / "Makefile").read_text()

    # When  the openspec targets are read
    # Then  the duplicate gate is wired, `openspec-check` includes it and the tests run in the suite
    check("make: openspec-duplicate-check runs the script",
          "openspec-duplicate-check:" in mk
          and "python3 scripts/openspec_duplicate_check.py" in mk, "")
    check("make: openspec-check runs the duplicate gate",
          "openspec-check:" in mk and "openspec-duplicate-check" in mk, "")
    check("make: the duplicate-gate tests run in the suite", wired(__file__), "")


def redirect_stdout(stream):
    import contextlib
    return contextlib.redirect_stdout(stream)


def main() -> int:
    print("OpenSpec duplicate-change gate (scripts/openspec_duplicate_check.py)")
    test_duplicate_added_heading_fails_naming_both()
    test_add_then_modify_is_a_chain_not_a_duplicate()
    test_duplicate_modified_heading_fails_naming_both()
    test_distinct_headings_pass()
    test_case_and_whitespace_insensitive()
    test_real_repo_has_no_same_kind_heading_duplicate()
    test_wired_into_make_openspec_check()
    print(f"\nPASSED {_PASS} | FAILED {_FAIL}")
    return 1 if _FAIL else 0


if __name__ == "__main__":
    raise SystemExit(main())
