#!/usr/bin/env python3
"""`make test` must never report a verdict it cannot show (issue #911).

Measured on a branch whose host `make test` wrote a captured log containing the
recipe echo and the platform warning and NOTHING from inside the container —
yet the wrapper exited 0. The old runner discarded a passing module's output
(mktemp then rm), so a green suite was one fragile line, and the TEST_RUN
container ran without the PYTHONUNBUFFERED=1 the DOCKER_RUN lesson (issue #591)
already taught. An empty capture and a clean run were indistinguishable.

This suite locks the three repairs END TO END (rule 6m — the real script and
the real recipe run; only the external container is a stub on PATH):
  1. scripts/run_tests.sh prints `[test] ok <module>` for every passing module.
  2. TEST_RUN forwards -e PYTHONUNBUFFERED=1 explicitly.
  3. the `test:` target tees its capture and refuses a verdict over an empty
     capture — while still propagating the suite's real exit code.
"""
from __future__ import annotations

import os
import re
import stat
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RUNNER = ROOT / "scripts" / "run_tests.sh"
MAKEFILE = ROOT / "Makefile"

_PASS = 0
_FAIL = 0


def check(name, cond, detail=""):
    global _PASS, _FAIL
    if cond:
        _PASS += 1
        print(f"  ok  {name}")
    else:
        _FAIL += 1
        print(f"  FAIL {name}" + (f"  [{detail[:300]}]" if detail else ""))


def _run_script(path: Path, *args, env=None):
    return subprocess.run(
        ["bash", str(path), *args],
        capture_output=True,
        text=True,
        timeout=120,
        env=env,
    )


# ---------------------------------------------------------------- runner ----

def _fixture_tests(tmp: Path) -> Path:
    d = tmp / "tests"
    d.mkdir(parents=True, exist_ok=True)
    (d / "test_dummy_a.py").write_text(
        "import sys\nprint('module A did work')\nsys.exit(0)\n", encoding="utf-8"
    )
    (d / "test_dummy_b.py").write_text(
        "import sys\nprint('module B did work')\nsys.exit(0)\n", encoding="utf-8"
    )
    return d


def test_a_passing_module_leaves_a_trace_in_the_stream():
    with tempfile.TemporaryDirectory() as tmp:
        d = _fixture_tests(Path(tmp))
        r = _run_script(RUNNER, str(d))
        out = r.stdout
        check("runner exits 0 on an all-green fixture", r.returncode == 0, r.stderr)
        check("runner prints '[test] ok' for the first passing module",
              "[test] ok test_dummy_a.py" in out, out)
        check("runner prints '[test] ok' for the second passing module",
              "[test] ok test_dummy_b.py" in out, out)
        check("runner still prints the final verdict line",
              "[test] 2 module(s) passed" in out, out)
        check("a passing module's own chatter is NOT dumped into the stream",
              "module A did work" not in out, out)


def test_the_first_red_stops_the_run_and_its_output_is_shown():
    with tempfile.TemporaryDirectory() as tmp:
        d = _fixture_tests(Path(tmp))
        (d / "test_dummy_c.py").write_text(
            "import sys\nprint('the red evidence')\nsys.exit(1)\n", encoding="utf-8"
        )
        r = _run_script(RUNNER, str(d))
        check("runner exits non-zero when a module fails", r.returncode != 0, "")
        check("green modules BEFORE the red one are still traced",
              "[test] ok test_dummy_a.py" in r.stdout and "[test] ok test_dummy_b.py" in r.stdout,
              r.stdout)
        check("the failing module's full output is shown", "the red evidence" in r.stdout,
              r.stdout)
        check("the run stops at the first red", "test_dummy_c.py FAILED" in r.stdout,
              r.stdout)


# ------------------------------------------------------------- Makefile -----

def _test_run_body(mk: str) -> str:
    start = mk.find("TEST_RUN :=")
    return mk[start : mk.find("\n\n", start)]


def _test_recipe(mk: str) -> str:
    lines = mk.splitlines()
    out = []
    for i, line in enumerate(lines):
        if line == "test:":
            for nxt in lines[i + 1 :]:
                if not nxt.startswith("\t"):
                    break
                out.append(nxt)
            break
    return "\n".join(out)


def test_test_run_forwards_the_unbuffered_lesson():
    mk = MAKEFILE.read_text(encoding="utf-8")
    body = _test_run_body(mk)
    check("TEST_RUN sets -e PYTHONUNBUFFERED=1 explicitly (issue #591 lesson applied to the test container)",
          "-e PYTHONUNBUFFERED=1" in body, body[:200])


def test_the_test_target_tees_and_verifies_its_capture():
    recipe = _test_recipe(MAKEFILE.read_text(encoding="utf-8"))
    check("test: captures the suite stream through tee", "tee" in recipe, recipe)
    check("test: refuses a capture with no '[test]' line",
          "grep -q '^\\[test\\] '" in recipe and "UNVERIFIABLE" in recipe, recipe[:300])
    check("test: propagates the suite's real exit code", "exit $$rc" in recipe, recipe)
    check("test: counts the per-module traces it captured",
          "grep -c '^\\[test\\] ok '" in recipe, recipe)


# -------------------------------------- end-to-end via the real recipe ------

def _stub(bin_dir: Path, name: str, stdout_lines, rc: int) -> Path:
    script = bin_dir / name
    body = "#!/bin/sh\n"
    for line in stdout_lines:
        body += f"printf '%s\\n' \"{line}\"\n"
    body += f"exit {rc}\n"
    script.write_text(body, encoding="utf-8")
    script.chmod(script.stat().st_mode | stat.S_IEXEC)
    return script


def _fixture_make(tmp: Path, stub: Path) -> Path:
    recipe = _test_recipe(MAKEFILE.read_text(encoding="utf-8"))
    mk = tmp / "Makefile"
    mk.write_text(
        "SHELL := /bin/bash\n"
        f"TEST_RUN := bash {stub}\n"
        ".PHONY: test\ntest:\n" + recipe + "\n",
        encoding="utf-8",
    )
    return mk


def _run_make(mk: Path):
    return subprocess.run(
        ["make", "-f", str(mk), "test"],
        capture_output=True,
        text=True,
        timeout=120,
    )


def test_an_empty_capture_is_refused_loudly():
    with tempfile.TemporaryDirectory() as tmp:
        tmp_p = Path(tmp)
        # the measured failure: the container answers 0 and streams NOTHING.
        stub = _stub(tmp_p, "stub_run.sh", [], 0)
        mk = _fixture_make(tmp_p, stub)
        r = _run_make(mk)
        check("an empty capture makes `make test` FAIL (rc 0 over silence is unverifiable)",
              r.returncode != 0, f"rc={r.returncode}")
        check("the refusal names the empty capture",
              "captured NO" in r.stderr and "UNVERIFIABLE" in r.stderr, r.stderr[:300])


def test_a_green_capture_passes_and_counts_its_traces():
    with tempfile.TemporaryDirectory() as tmp:
        tmp_p = Path(tmp)
        stub = _stub(tmp_p, "stub_run.sh",
                     ["[test] ok test_a.py", "[test] ok test_b.py", "[test] 2 module(s) passed"], 0)
        mk = _fixture_make(tmp_p, stub)
        r = _run_make(mk)
        check("a capture WITH verdict lines lets a green rc through",
              r.returncode == 0, f"rc={r.returncode} stderr={r.stderr[:200]}")
        check("the harness reports the per-module traces it counted",
              "captured 2 per-module trace(s)" in r.stderr, r.stderr[:300])
        check("the suite's own stream stays visible on stdout",
              "[test] 2 module(s) passed" in r.stdout, r.stdout[:200])


def test_the_suite_exit_code_is_propagated():
    with tempfile.TemporaryDirectory() as tmp:
        tmp_p = Path(tmp)
        stub = _stub(tmp_p, "stub_run.sh",
                     ["[test] ok test_a.py", "[test] 1 module(s) passed, test_b FAILED"], 7)
        mk = _fixture_make(tmp_p, stub)
        r = _run_make(mk)
        check("a red suite makes `make test` fail (make reports the recipe error)",
              r.returncode != 0, f"rc={r.returncode}")
        check("the guard ANNOUNCES the suite's own exit code it propagated",
              "suite rc=7" in r.stderr, r.stderr[:300])


def main():
    for fn in [
        test_a_passing_module_leaves_a_trace_in_the_stream,
        test_the_first_red_stops_the_run_and_its_output_is_shown,
        test_test_run_forwards_the_unbuffered_lesson,
        test_the_test_target_tees_and_verifies_its_capture,
        test_an_empty_capture_is_refused_loudly,
        test_a_green_capture_passes_and_counts_its_traces,
        test_the_suite_exit_code_is_propagated,
    ]:
        fn()
    print(f"\n{_PASS} passed, {_FAIL} failed")
    return 0 if _FAIL == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
