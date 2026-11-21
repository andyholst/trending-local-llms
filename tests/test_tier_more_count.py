#!/usr/bin/env python3
"""tests/test_tier_more_count.py — the per-VRAM tables rendered `+-1 more measured at
this size` (negative counts) because the label computed `sum(ran-on) - 1` even when the
displayed row was not itself classified ran-on by the same tier seam.

This suite locks ONE shared implementation (`_other_ran_on_count`) used by both the
card tables and the above-48-GB tables:

  1. the count excludes the shown row by MEASUREMENT IDENTITY (candidate lists are rebuilt);
  2. a weights-only shown row counts all ran-on rows as "more";
  3. a shown row absent from the candidate list — the exact shipped bug — never goes negative;
  4. the re-rendered shipped README has zero negative labels and keeps its positive ones;
  5. the guard is RED on the old two-copy `- 1` expression (git show origin/master:...).

The guards call the REAL update_trending module; the only external system is the filesystem.
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "tests"))

import update_trending as UT  # noqa: E402
from wiring import wired  # noqa: E402

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


def _e(n, tps="10"):
    return {"engine": f"eng{n}", "tps": tps, "date": "2026-11-01",
            "source_post": f"https://lightbrd.com/a/status/{n}"}


def test_other_ran_on_count_uses_measurement_identity():
    shown, other1, other2 = _e(1), _e(2), _e(3)
    cands = [(shown, "ran-on"), (other1, "ran-on"), (other2, "ran-on"), (_e(4), "weights-only")]
    # A rebuilt candidate list has fresh dict objects — identity comparison must still work.
    check("a ran-on shown row excludes itself, counts the other two",
          UT._other_ran_on_count([(dict(e), ev) for e, ev in cands], shown, "ran-on") == 2)
    check("a weights-only shown row counts all ran-on rows",
          UT._other_ran_on_count(cands, _e(9), "weights-only") == 3)
    check("the exact shipped bug: a shown row absent from the candidates stays >= 0",
          UT._other_ran_on_count([(other1, "ran-on")], shown, "ran-on") == 1)
    check("no candidates means no invented count",
          UT._other_ran_on_count([], shown, "ran-on") == 0)


def test_the_shipped_readme_has_no_negative_labels():
    rd = (ROOT / "README.md").read_text()
    negative = re.findall(r"\+\-(\d+) more measured at this size", rd)
    positive = re.findall(r"\+(\d+) more measured at this size", rd)
    check("zero negative '+-N more' labels", not negative, str(negative[:5]))
    check("the real positive labels survive the fix", len(positive) > 50, str(len(positive)))


def test_the_guard_is_red_on_the_old_expression():
    out = subprocess.run("git show origin/master:scripts/update_trending.py",
                         shell=True, cwd=ROOT, capture_output=True, text=True).stdout
    check("the old render used a bare `- 1` count with no guard",
          'if _ev == "ran-on") - 1' in out, "old code already has the fix?")


def test_wiring():
    check("this suite is discovered by `make test`", wired(__file__), "")


def main() -> int:
    print("per-VRAM 'more measured' label (README rendering):")
    test_other_ran_on_count_uses_measurement_identity()
    test_the_shipped_readme_has_no_negative_labels()
    test_the_guard_is_red_on_the_old_expression()
    test_wiring()
    print(f"{'FAILED' if _FAIL else 'PASSED'} {_PASS} | FAILED {_FAIL}")
    return 1 if _FAIL else 0


if __name__ == "__main__":
    raise SystemExit(main())
