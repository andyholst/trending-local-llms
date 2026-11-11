#!/usr/bin/env python3
"""The standalone-script convention gets a mechanical guard (issue #768).

Every tests/test_*.py is a SCRIPT run standalone by scripts/run_tests.sh and the TEST image has
no pytest, yet a module imported it anyway and the violation surfaced only inside the TEST image
after a full ~15-minute red validate job (qa-validate run 42800200326, PR #764 head 0db0462),
while every host gate stayed green. These tests run the REAL scripts/check_pytest_imports.py
against planted fixtures — the planted violation MUST go red — and against the real tests/, which
MUST pass the guard it guards. The wiring is asserted on the real Makefile text.

Run:  python3 tests/test_pytest_import_guard.py    or   make test
"""
from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "scripts" / "check_pytest_imports.py"

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


def fixture_dir(tmp_path, name, body):
    d = tmp_path / name
    d.mkdir(parents=True, exist_ok=True)
    (d / "test_planted.py").write_text(body)
    return d


def run(dirpath: Path):
    return subprocess.run([sys.executable, str(SCRIPT), "--tests-dir", str(dirpath)],
                          capture_output=True, text=True)


def test_a_planted_import_pytest_goes_red(tmp_path=None):
    tmp_path = tmp_path or Path(tempfile.mkdtemp())
    d = fixture_dir(tmp_path, "planted", (
        "#!/usr/bin/env python3\n"
        "import pytest\n\n\n"
        "def test_x(tmp_path=None):\n"
        "    assert True\n"
    ))
    r = run(d)
    check("planted: a top-level import is refused (exit 1)", r.returncode == 1, f"rc={r.returncode}")
    check("planted: the file is named", "test_planted.py" in r.stderr, r.stderr[:120])
    check("planted: the line is named", "line(s) 2" in r.stderr, r.stderr[:120])
    check("planted: the house pattern is stated", "scripts/run_tests.sh" in r.stderr
          and "tmp_path=None" in r.stderr, r.stderr[:200])


def test_the_other_pytest_spellings_go_red(tmp_path=None):
    tmp_path = tmp_path or Path(tempfile.mkdtemp())
    cases = {
        "from_import": "from py""test import mark\n",
        "member_use": "def test_x(tmp_path=None):\n    return py""test.mark.parametrize('a', [1])\n",
        "dotted_import": "import py""test.fixture\n",
        "aliased_import": "import py""test as pt\n",
    }
    for name, body in cases.items():
        d = fixture_dir(tmp_path, name, body)
        r = run(d)
        check(f"spelling {name}: refused", r.returncode == 1, f"rc={r.returncode}")
        check(f"spelling {name}: names the file", "test_planted.py" in r.stderr, r.stderr[:120])


def test_a_clean_module_and_a_comment_line_pass(tmp_path=None):
    tmp_path = tmp_path or Path(tempfile.mkdtemp())
    d = fixture_dir(tmp_path, "clean", (
        "#!/usr/bin/env python3\n"
        "# a comment may name it: import py" + "test is forbidden, py" + "test.raises is too\n"
        "import subprocess\n\n\n"
        "def test_ok(tmp_path=None):\n"
        "    return 0\n\n\n"
        "def main() -> int:\n"
        "    return 0\n\n\n"
        'if __name__ == "__main__":\n    sys.exit(main())\n'
    ))
    r = run(d)
    check("clean: stdlib-only module passes", r.returncode == 0, r.stderr[:120])
    check("clean: a whole-line comment is not code", "test_planted.py" not in r.stderr, r.stderr[:120])


def test_a_missing_tests_dir_is_a_loud_two(tmp_path=None):
    tmp_path = tmp_path or Path(tempfile.mkdtemp())
    r = run(tmp_path / "nope")
    check("missing dir: exit 2, named loudly", r.returncode == 2 and "not a directory" in r.stderr,
          f"rc={r.returncode}")


def test_the_real_tests_pass_the_guard():
    r = subprocess.run([sys.executable, str(SCRIPT)], capture_output=True, text=True)
    check("real suite: tests/ passes its own guard", r.returncode == 0, r.stderr[:200])
    check("real suite: the modules were actually scanned", "test module(s)" in r.stdout, r.stdout[:120])


def test_lint_runs_the_guard():
    makefile = (ROOT / "Makefile").read_text()
    check("makefile: `lint` runs the guard", "check-pytest-imports" in makefile.split("lint:")[1][:800], "")
    check("makefile: the public target exists", "\ncheck-pytest-imports:" in makefile, "")
    check("makefile: the public target delegates to the internal recipe",
          "_check-pytest-imports" in makefile.split("\ncheck-pytest-imports:")[1][:300], "")
    check("makefile: the internal recipe calls the script",
          "check_pytest_imports.py" in makefile.split("\n_check-pytest-imports:")[1][:300], "")


def main(tmp_path=None) -> int:
    print("pytest-import guard: unit tests")
    test_a_planted_import_pytest_goes_red(tmp_path)
    test_the_other_pytest_spellings_go_red(tmp_path)
    test_a_clean_module_and_a_comment_line_pass(tmp_path)
    test_a_missing_tests_dir_is_a_loud_two(tmp_path)
    test_the_real_tests_pass_the_guard()
    test_lint_runs_the_guard()
    print(f"\nPASSED {_PASS} | FAILED {_FAIL}")
    return 1 if _FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
