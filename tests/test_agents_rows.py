#!/usr/bin/env python3
"""The §8 rows a change owed are WRITTEN, not promised (issues #310/#391/#400).

Rule 6c requires a change's guard row in the §8 table in the same change. Three changes could
not write theirs: AGENTS.md writes were gated behind an approval prompt in a headless bot run
("Silence is not consent", #310), so the guards shipped registered in `make test` and
undiscoverable from the rulebook. These tests pin the rows that were owed, so the gap cannot
reopen quietly.

Run:  python3 tests/test_agents_rows.py   or   make test
"""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
AGENTS = ROOT / "AGENTS.md"

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


def section8() -> str:
    text = AGENTS.read_text(encoding="utf-8")
    return text[text.index("## 8. Regression guards"):]


def test_the_owed_rows_are_present():
    sec = section8()
    # #400: the CI entry point that never ran.
    check("rows: §8 names tests/test_ci_wiring.py", "`tests/test_ci_wiring.py`" in sec)
    check("rows: … and the dead pytest branch it catches",
          "2>/dev/null" in sec and "pytest is absent" in sec)
    # #310: the code-review secret contract.
    check("rows: §8 names tests/test_code_review.py", "`tests/test_code_review.py`" in sec)
    check("rows: … and the four checks it catches",
          "GITHUB_TOKEN" in sec and "COMMENTED reference" in sec)
    # #391: the loop's scratch file.
    check("rows: §8 names the scratch-notes guard",
          "test_scratch_notes_stay_out_of_the_tree" in sec)
    check("rows: … and the measured 0-byte file it catches",
          "qa-report.txt.notes" in sec and "PR #387" in sec)


def test_the_rows_name_modules_that_exist():
    sec = section8()
    for mod in ("tests/test_ci_wiring.py", "tests/test_code_review.py", "tests/test_fix_loop.py"):
        check(f"rows: {mod} is a real module", (ROOT / mod).is_file(), mod)
    check("rows: the guards the rows name live in those modules",
          "test_scratch_notes_stay_out_of_the_tree" in
          (ROOT / "tests" / "test_fix_loop.py").read_text())


def test_the_section_still_parses_as_a_table():
    sec = section8()
    rows = [l for l in sec.splitlines() if l.startswith("|")]
    check("rows: the section is a table with a header", rows and rows[0].startswith("| Guard"), rows[:1])
    bad = [r for r in rows if r.count("|") < 3]
    check("rows: every row has at least a guard and a description", not bad, bad[:2])


def main() -> int:
    print("the owed §8 rows (issues #310/#391/#400)")
    test_the_owed_rows_are_present()
    test_the_rows_name_modules_that_exist()
    test_the_section_still_parses_as_a_table()
    print(f"\nPASSED {_PASS} | FAILED {_FAIL}")
    return 1 if _FAIL else 0


if __name__ == "__main__":
    raise SystemExit(main())
