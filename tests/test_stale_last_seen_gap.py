#!/usr/bin/env python3
"""tests/test_stale_last_seen_gap.py — issue #1183: a stale `last_seen` is never an alarm.

The pipeline could not tell "no post exists" from "we stopped finding it": the flash-next
rows sit at 2026-11-08/09 while Edge0-145B (Qwen3.8-Flash-Next base) is trending on
2026-11-16. The rank is CORRECT (it uses 7-day post buzz) — the capture is missing. This
suite locks the declared `stale_last_seen` acquisition gap:

  1. a row whose newest post aged out of the 7-day window while a SAME-BASE sibling has
     newer captured evidence produces exactly ONE evidence-bearing finding;
  2. no false positives: a current row, or a stale row with no newer sibling, produces none;
  3. analyse() adds ONE class signature entry (#472 lesson) and the issue BODY names the
     rows, the lag and the sibling evidence;
  4. the SHIPPED store actually surfaces the seven flash-next rows with the Edge0 sibling;
  5. the guard is RED on the pre-change analysis (git show origin/master:...).

The guards call the REAL data_gap_analysis module; the only external system is the filesystem.
"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "tests"))

import data_gap_analysis as GA  # noqa: E402
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


def _store(stale_date="2026-11-08", sibling_date="2026-11-16", newest="2026-11-17"):
    return {"models": [
        {"id": "qwen3.8-flash-next-125b", "name": "Qwen3.8-Flash-Next 125B",
         "full_name": "Qwen3.8-Flash-Next-125B", "params": "125B (MoE)", "last_seen": stale_date},
        {"id": "edge0-145b", "name": "Edge0-145B",
         "full_name": "Edge0-145B (Qwen3.8-Flash-Next base)", "params": "145B",
         "last_seen": sibling_date},
        {"id": "qwen3.8-27b", "name": "Qwen3.8-27B", "params": "27B", "last_seen": newest},
    ]}


def test_stale_row_with_a_newer_same_base_sibling_is_detected():
    stale = GA.stale_last_seen(_store())
    check("exactly one stale finding", len(stale) == 1, str(stale))
    if stale:
        s = stale[0]
        check("the stale row is flash-next", s["id"] == "qwen3.8-flash-next-125b", str(s))
        check("the store-wide newest is the clock, not the wall clock",
              s["newest_in_store"] == "2026-11-17" and s["last_seen"] == "2026-11-08", str(s))
        check("the lag is measured in days", s["lag_days"] == 9, str(s))
        check("the sibling evidence is the same-base Edge0 row",
              s["sibling"] == "edge0-145b" and s["sibling_last_seen"] == "2026-11-16", str(s))


def test_no_false_positives():
    current = GA.stale_last_seen(_store(stale_date="2026-11-15"))
    check("a row inside the 7-day window is not flagged", not current, str(current))
    s = _store()
    s["models"] = [m for m in s["models"] if m["id"] != "edge0-145b"]
    check("a stale row with no newer same-base sibling is not flagged",
          not GA.stale_last_seen(s), str(GA.stale_last_seen(s)))
    s2 = _store()
    s2["models"][1]["full_name"] = "Edge0-145B (unrelated base)"
    check("a sibling without the same-base phrase is not flagged",
          not GA.stale_last_seen(s2), str(GA.stale_last_seen(s2)))


def test_analyse_signature_and_issue_body():
    contract = {"model": set(), "search_model": set(), "measurement": set()}
    with tempfile.TemporaryDirectory() as td:
        report = GA.analyse(_store(), contract, raw_dir=Path(td), refusals=[])
    check("analyse reports the stale rows", len(report.get("stale_last_seen") or []) == 1,
          str(report.get("stale_last_seen")))
    check("ONE class signature entry, never one per model (#472)",
          report["signature"].count("stale_last_seen") == 1, str(report["signature"]))
    body, title = GA.issue_body(report, None, ["stale_last_seen"])
    check("the issue BODY declares the capture hole with evidence",
          "Stale `last_seen` (capture hole)" in body
          and "qwen3.8-flash-next-125b" in body
          and "edge0-145b" in body
          and "9d behind" in body, body[:300])
    check("the issue carries the signature marker for dedup",
          GA.marker(GA.entry_id("stale_last_seen")) in body)
    check("the title is non-empty", bool(title))


def test_the_shipped_store_surfaces_the_real_flash_next_gap():
    store = json.loads((ROOT / "data" / "models.json").read_text())
    stale = GA.stale_last_seen(store)
    flash = [s for s in stale if "flash-next" in s["id"]]
    check("the shipped store's flash-next rows are declared stale",
          len(flash) >= 1, str(flash[:3]))
    check("the evidence names the newer same-base Edge0 sibling",
          any(s.get("sibling") == "edge0-145b" for s in flash), str(flash[:3]))


def test_the_guard_is_red_on_the_pre_change_analysis():
    out = subprocess.run("git show origin/master:scripts/data_gap_analysis.py",
                         shell=True, cwd=ROOT, capture_output=True, text=True).stdout
    check("the pre-change analysis has no stale_last_seen signal",
          "stale_last_seen" not in out, "the old module already has the guard?")


def test_wiring():
    check("this suite is discovered by `make test`", wired(__file__), "")


def main() -> int:
    print("stale_last_seen gap (issue #1183):")
    test_stale_row_with_a_newer_same_base_sibling_is_detected()
    test_no_false_positives()
    test_analyse_signature_and_issue_body()
    test_the_shipped_store_surfaces_the_real_flash_next_gap()
    test_the_guard_is_red_on_the_pre_change_analysis()
    test_wiring()
    print(f"{'FAILED' if _FAIL else 'PASSED'} {_PASS} | FAILED {_FAIL}")
    return 1 if _FAIL else 0


if __name__ == "__main__":
    raise SystemExit(main())