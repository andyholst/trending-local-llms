#!/usr/bin/env python3
"""Behavioural tests for scripts/check_openspec_test_lines.py (issue #621).

Rule 6f says a scenario's `- **Test:**` line names the test that LOCKS the
behaviour, but the gate used to prove only that the line was present — so a
change could cite a file and a test that were never written and stay green.
Measured: change `agents-md-footprint-dimensions` cited
`tests/test_agents_rows.py::test_the_footprint_sentence_names_every_dimension`
in all four scenarios with no such file, and `make openspec-check` reported
every change valid. These tests drive the REAL script (its functions, and the
CLI as a subprocess) against fixture change trees and assert the repository's
own tree is fully resolvable, so a spec can never again cite a test that does
not exist while the gate stays green.

Wired into `make test` (rule 6d).
"""
from __future__ import annotations

import contextlib
import importlib.util
import io
import subprocess
import sys
import tempfile
from pathlib import Path

from wiring import wired  # noqa: E402  (issues #176/#192)

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "scripts" / "check_openspec_test_lines.py"

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
    spec = importlib.util.spec_from_file_location("check_openspec_test_lines", SCRIPT)
    assert spec and spec.loader, SCRIPT
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _fixture(base: Path, name: str, spec: str, archived: bool = False) -> Path:
    """An ACTIVE or ARCHIVED change with one spec (specs/cap/spec.md)."""
    d = (base / "archive" / name) if archived else (base / name)
    (d / "specs" / "cap").mkdir(parents=True, exist_ok=True)
    (d / "specs" / "cap" / "spec.md").write_text(spec, encoding="utf-8")
    (d / "proposal.md").write_text(f"# {name}\n\n**Issue:** #1\n", encoding="utf-8")
    return d


def _module_file(root: Path, path: str, body: str = "def test_placeholder():\n    pass\n"):
    """A Python module under *root* that the fixture references (`path` like tests/x.py)."""
    f = root / path
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(body, encoding="utf-8")
    return f


def test_the_shipped_reference_is_red():
    """The measured failure: a spec citing `tests/test_agents_rows.py::test_the_footprint_sentence_names_every_dimension`
    (file exists, wrong body) must be RED, naming the change, the scenario and the symbol."""

    # Given an active change whose spec cites the shipped shape: file exists,
    # but the exact symbol was never written
    mod = _module()
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        base = root / "openspec" / "changes"
        _fixture(
            base,
            "agents-footprint",
            "# agents\n#### Scenario: the rulebook names every dimension\n"
            "- **GIVEN** the rulebook\n- **WHEN** checked\n- **THEN** resolved\n\n"
            "- **Test:** tests/test_agents_rows.py::test_the_footprint_sentence_names_every_dimension\n",
        )
        _module_file(root, "tests/test_agents_rows.py",
                     "def test_the_rows_for_the_two_label_queue_are_written():\n    pass\n")

        # When  the gate runs
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
            rc = mod.check_all(base=base, root=root)

    # Then  it is red and names the change, the scenario line and the missing symbol
    out = buf.getvalue()
    check("shipped: gate exits non-zero", rc == 1, str(rc))
    check("shipped: the change is named", "agents-footprint" in out, out)
    check("shipped: the scenario line is named", "spec.md:" in out, out)
    check("shipped: the missing symbol is named",
          "test_the_footprint_sentence_names_every_dimension" in out and "defines no" in out, out)


def test_a_missing_file_is_red():
    """A `- **Test:** path::test` whose file does not exist is RED, naming the file."""

    # Given an active change citing a file that was never created
    mod = _module()
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        base = root / "openspec" / "changes"
        _fixture(base, "never-written",
                 "# x\n#### Scenario: missing\n- **GIVEN** x\n- **WHEN** y\n- **THEN** z\n\n"
                 "- **Test:** tests/nope.py::test_anything\n")

        # When  the gate runs
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
            rc = mod.check_all(base=base, root=root)

    # Then  it is red and names the missing file
    out = buf.getvalue()
    check("missing-file: gate exits non-zero", rc == 1, str(rc))
    check("missing-file: the missing file is named", "tests/nope.py" in out, out)


def test_a_resolvable_reference_is_green():
    """A `- **Test:** path::test` whose file exists and defines the symbol is GREEN.

    Also covers the `::main` form (a spec may lock a module's `main()`), and a
    reference to a non-Python file whose existence alone is the bound."""

    # Given an active change citing tests that DO exist, in a fixture tree
    mod = _module()
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        base = root / "openspec" / "changes"
        _fixture(base, "solid",
                 "# solid\n#### Scenario: locked\n- **GIVEN** x\n- **WHEN** y\n- **THEN** z\n\n"
                 "- **Test:** tests/ok.py::test_ok\n"
                 "- **Test:** `tests/ok.py::main`\n"
                 "- **Test:** guides/notes.md\n")
        _module_file(root, "tests/ok.py",
                     "def test_ok():\n    pass\n\ndef main():\n    return 0\n")
        doc = root / "guides" / "notes.md"
        doc.parent.mkdir(parents=True, exist_ok=True)
        doc.write_text("locks nothing; file existence is the bound\n", encoding="utf-8")

        # When  the gate runs
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
            rc = mod.check_all(base=base, root=root)
        out = buf.getvalue()

    # Then  it is green and names no failure
    check("resolvable: gate exits 0", rc == 0, str(rc) + " " + out)
    check("resolvable: no FAIL line", "FAIL" not in out, out)


def test_a_prose_test_line_is_reported_not_resolved():
    """A `- **Test:**` line with no `path::symbol` is reported, never treated as resolved."""

    # Given an active change whose spec has prose-style Test lines AND a real one
    mod = _module()
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        base = root / "openspec" / "changes"
        _fixture(base, "prosey",
                 "# prosey\n#### Scenario: locked\n- **GIVEN** x\n- **WHEN** y\n- **THEN** z\n\n"
                 "- **Test:** tests/ok.py::test_ok\n"
                 "- **Test:** tests/ok.py (the §6b list — no symbol)\n"
                 "- **Test:** `scripts/self_test.py`\n")
        _module_file(root, "tests/ok.py", "def test_ok():\n    pass\n")

        # When  the gate runs
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
            rc = mod.check_all(base=base, root=root)
        out = buf.getvalue()

    # Then  it is green but the two non-reference lines are REPORTED, never resolved
    check("prose: gate exits 0", rc == 0, str(rc) + " " + out)
    check("prose: the no-symbol lines are reported", out.count("names no `<path>::<test>`") >= 2, out)
    check("prose: the resolvable line is not reported as prose", "tests/ok.py::test_ok` — " not in out, out)


def test_a_spec_with_no_test_lines_is_reported():
    """A change whose specs carry no `- **Test:**` lines is reported as vacuous, never OK."""

    # Given an active change whose only spec has scenarios but no Test line
    mod = _module()
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        base = root / "openspec" / "changes"
        _fixture(base, "untested",
                 "# untested\n#### Scenario: nothing locks this\n- **GIVEN** x\n- **WHEN** y\n- **THEN** z\n")

        # When  the gate runs
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
            rc = mod.check_all(base=base, root=root)
        out = buf.getvalue()

    # Then  it is green (no unresolvable citation) but the vacuous scan is named
    check("vacuous: gate exits 0", rc == 0, str(rc) + " " + out)
    check("vacuous: the scan reports nothing to resolve",
          "untested" in out and "vacuous" in out, out)


def test_archived_change_is_ignored():
    """An archived change keeps its shape and is not re-checked."""

    # Given an ARCHIVED change whose spec cites a file that does not exist
    mod = _module()
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        base = root / "openspec" / "changes"
        _fixture(base, "old-and-gone",
                 "# old\n#### Scenario: was locked\n- **GIVEN** x\n- **WHEN** y\n- **THEN** z\n\n"
                 "- **Test:** tests/deleted.py::test_gone\n", archived=True)

        # When  the gate runs
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
            rc = mod.check_all(base=base, root=root)
        out = buf.getvalue()

    # Then  it is green and never reports the archived change
    check("archived: gate exits 0", rc == 0, str(rc) + " " + out)
    check("archived: the archived change is not reported", "old-and-gone" not in out, out)


def test_real_repo_references_resolve_and_the_gate_is_wired():
    """This repository's own active changes resolve, and the gate is wired (rule 6d)."""

    # Given this repository's real tree and Makefile
    mod = _module()
    mk = (ROOT / "Makefile").read_text()

    # When  the gate runs over the real tree, and the CLI runs as CI runs it
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc = mod.check_all()
    proc = subprocess.run([sys.executable, str(SCRIPT)], cwd=ROOT, capture_output=True, text=True)

    # Then  it is green both ways
    check("real repo: every active change's references resolve", rc == 0, buf.getvalue())
    check("real repo: the script's exit code is 0", proc.returncode == 0,
          proc.stdout + proc.stderr)

    # And the wiring holds: the target runs the script, `openspec-check` bundles it,
    # and the tests run in the suite
    check("make: openspec-spec-tests-check runs the script",
          "openspec-spec-tests-check:" in mk
          and "python3 scripts/check_openspec_test_lines.py" in mk, "")
    check("make: openspec-check bundles the reference gate",
          "openspec-check: openspec-image openspec-tasks-check openspec-index-check openspec-spec-tests-check" in mk, "")
    check("make: the reference-gate tests run in the suite", wired(__file__), "")


def main() -> int:
    print("OpenSpec test-reference gate (scripts/check_openspec_test_lines.py)")
    test_the_shipped_reference_is_red()
    test_a_missing_file_is_red()
    test_a_resolvable_reference_is_green()
    test_a_prose_test_line_is_reported_not_resolved()
    test_a_spec_with_no_test_lines_is_reported()
    test_archived_change_is_ignored()
    test_real_repo_references_resolve_and_the_gate_is_wired()
    print(f"\nPASSED {_PASS} | FAILED {_FAIL}")
    return 1 if _FAIL else 0


if __name__ == "__main__":
    raise SystemExit(main())
