#!/usr/bin/env python3
"""A declared Makefile knob with no reader goes RED (issue #630).

`HERMES_LOG_TAIL ?= 60` stayed declared long after the scrub seam went LIVE (`--stream`,
issue #591) and stopped passing `--tail`: an operator setting `HERMES_LOG_TAIL=200` changed
nothing, silently, and the only tree mentions were the definition, two test FIXTURES that
define their own copy, and archived openspec prose — none of which reads the real variable.
These tests run the REAL `scripts/check_makefile_knobs.py` against planted fixture trees —
the planted dead knob MUST go red — and against the real repository, which must pass its own
guard green, with the dead knob provably gone. The wiring is asserted on the real Makefile text.

Run:  python3 tests/test_makefile_knobs.py    or   make test
"""
from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "scripts" / "check_makefile_knobs.py"

_PASS = 0
_FAIL = 0


def check(name, cond, detail=None):
    global _PASS, _FAIL
    if cond:
        _PASS += 1
        print(f"  ok  {name}")
    else:
        _FAIL += 1
        shown = "" if detail is None or detail == "" else f"  [{detail}]"
        print(f"  FAIL {name}{shown}")


def fixture(tmp_path, name, makefile_text, extra=None):
    """A miniature repo: a Makefile plus optional reader files."""
    d = tmp_path / name
    d.mkdir(parents=True, exist_ok=True)
    (d / "Makefile").write_text(makefile_text)
    for rel, body in (extra or {}).items():
        p = d / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(body)
    return d


def run(root: Path):
    return subprocess.run([sys.executable, str(SCRIPT), "--root", str(root)],
                          capture_output=True, text=True)


def test_a_planted_dead_knob_goes_red(tmp_path=None):
    tmp_path = Path(tmp_path) if tmp_path else Path(tempfile.mkdtemp())
    d = fixture(tmp_path, "dead", "DEAD_KNOB ?= 60\nUSED_KNOB ?= x\n\nfoo:\n\t@echo $(USED_KNOB)\n")
    r = run(d)
    check("knobs: a declared-and-unread knob exits 1", r.returncode == 1, r.returncode)
    check("knobs: the refusal names the knob and its Makefile line",
          "DEAD_KNOB" in r.stdout and "Makefile:1" in r.stdout, r.stdout[:200])
    check("knobs: the read knob is not named", "USED_KNOB" not in r.stdout, r.stdout[:200])


def test_a_knob_read_only_by_prose_goes_red(tmp_path=None):
    """The exact cover the old knob had: mentions, not reads."""
    tmp_path = Path(tmp_path) if tmp_path else Path(tempfile.mkdtemp())
    d = fixture(
        tmp_path, "prose",
        "PROSE_KNOB ?= 60\n\nfoo:\n\t@echo hi\n",
        {
            "scripts/a.sh": "# PROSE_KNOB is documented here at length\n# PROSE_KNOB too\n",
            "scripts/b.py": '"""This script mentions PROSE_KNOB in its docstring."""\nprint("hi")\n',
            "tests/test_fake.py": 'FIXTURE = "PROSE_KNOB ?= 60"\n',
            "openspec/changes/archive/old/proposal.md": "It gains `PROSE_KNOB ?= 60` forever.\n",
        },
    )
    r = run(d)
    check("knobs: comments, docstrings, fixtures and archive prose are not readers",
          r.returncode == 1, (r.returncode, r.stdout[:200]))


def test_a_knob_read_by_a_recipe_or_a_script_goes_green(tmp_path=None):
    tmp_path = Path(tmp_path) if tmp_path else Path(tempfile.mkdtemp())
    d = fixture(
        tmp_path, "read",
        "MK_KNOB ?= 60\nSH_KNOB ?= 1\nPY_KNOB ?= 2\nENVY_KNOB ?= 3\nARG_KNOB ?= 4\n\n"
        "foo:\n\t@echo $(MK_KNOB)\n\t${SH_KNOB} sh -c true\n\tpython3 scripts/b.py\n\n"
        "bar:\n\t@make ${PY_KNOB}\n",
        {
            "scripts/b.py": 'import os\nprint(os.environ.get("PY_KNOB"))\nprint(os.environ["ARG_KNOB"])\n',
            "scripts/c.sh": 'if [ -n "${SH_KNOB:-}" ]; then echo set; fi\n',
            ".github/workflows/w.yml": "env:\n  ENVY_KNOB: yes\n",
            "Dockerfile": "ARG ARG_KNOB=4\nRUN echo $ARG_KNOB\n",
        },
    )
    r = run(d)
    check("knobs: make/shell/env-read/yaml-key/ARG readers all count",
          r.returncode == 0, (r.returncode, r.stdout + r.stderr)[:300])


def test_a_missing_makefile_fails_loudly(tmp_path=None):
    tmp_path = Path(tmp_path) if tmp_path else Path(tempfile.mkdtemp())
    d = tmp_path / "empty"
    d.mkdir(parents=True, exist_ok=True)
    r = run(d)
    check("knobs: no Makefile is exit 2, never a silent clean", r.returncode == 2, r.returncode)


def test_the_real_makefile_passes_its_own_guard():
    r = run(ROOT)
    check("knobs: the real Makefile is clean under the new guard", r.returncode == 0,
          (r.stdout + r.stderr)[:400])


def test_the_dead_knob_from_issue_630_is_gone():
    mk = (ROOT / "Makefile").read_text()
    check("make: HERMES_LOG_TAIL is no longer declared (the #630 fix)",
          "HERMES_LOG_TAIL ?=" not in mk, "")
    check("make: the scrub seam comment says why there is no tail knob",
          "NO `HERMES_LOG_TAIL` knob" in mk, mk[mk.find("HERMES_LOG_SCRUBBED"):][:200])


def test_lint_runs_the_guard():
    mk = (ROOT / "Makefile").read_text()
    lint_recipe = mk.split("\nlint: ")[1].split("\n\n")[0]
    check("make: the lint recipe calls check-makefile-knobs",
          "--no-print-directory check-makefile-knobs" in lint_recipe, lint_recipe[:400])
    check("make: _check-makefile-knobs runs the real script",
          "_check-makefile-knobs:\n\tpython3 scripts/check_makefile_knobs.py" in mk, "")
    check("make: the public target check-makefile-knobs exists",
          "check-makefile-knobs: ##" in mk, "")
    listed = subprocess.run(["bash", str(ROOT / "scripts" / "run_tests.sh"), "--list"],
                            capture_output=True, text=True).stdout
    check("wiring: this suite is in `make test`", "test_makefile_knobs.py" in listed, listed[-200:])


def main() -> int:
    tests = [test_a_planted_dead_knob_goes_red,
             test_a_knob_read_only_by_prose_goes_red,
             test_a_knob_read_by_a_recipe_or_a_script_goes_green,
             test_a_missing_makefile_fails_loudly,
             test_the_real_makefile_passes_its_own_guard,
             test_the_dead_knob_from_issue_630_is_gone,
             test_lint_runs_the_guard]
    print("test_makefile_knobs.py")
    for t in tests:
        t()
    print(f"\nPASSED {_PASS} | FAILED {_FAIL}")
    return 1 if _FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
