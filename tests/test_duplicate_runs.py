#!/usr/bin/env python3
"""One physical run under two engine names (issue #459).

`merge_engines` keys a measurement on (engine, hardware, quant), so a RENAMED engine — a
fabricated name, a renamed fork, a fixed typo — appends a second row instead of updating the
first: the backend tables, the engine matrix and the card-fit evidence then count one run twice,
and a reader comparing engines is told two engines did what one did.

Measured in the shipped store: `qwen3.8-flash-next-125b` carries the SAME post, date and 191 t/s
under `vLLM` and under `FP4-Local` (a name that is a quant token, refused by ingest since #458).

The scan is REPORT ONLY on purpose: history predates the refusal and cannot be repaired by reding
every PR — but a comparison post legitimately reports one figure for two engines, so the scan names
the pairs instead of judging them.

Run:  python3 tests/test_duplicate_runs.py    or   make test
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import validate as V  # noqa: E402

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


def meas(engine, tps, post="https://lightbrd.com/u/status/1", date="2026-10-20", **kw):
    e = {"engine": engine, "tps": tps, "hardware": "RTX 4090 24GB", "quant": "Q4_K_M",
         "date": date, "source_post": post}
    e.update(kw)
    return e


def model(name, engines):
    return {"id": name.lower(), "name": name, "engines": engines}


def test_one_post_two_engine_names_is_reported():
    models = [model("Qwen3.8-Flash-Next 125B", [
        meas("vLLM", 191, hardware="NVIDIA RTX PRO 6000 (Blackwell)"),
        meas("FP4-Local", 191, hardware="RTX 6000 Pro (Nvidia/Qwen3.8-Flash-Next-FP4-Local)"),
    ])]
    dups = V.duplicate_runs(models)
    check("dup: the same post+date+t/s under two engines is reported", len(dups) == 1, dups)
    check("dup: it names BOTH engines", dups and dups[0][4] == ["FP4-Local", "vLLM"], dups)
    check("dup: it names the model and the post", dups and dups[0][0] == "Qwen3.8-Flash-Next 125B"
          and dups[0][1].endswith("/status/1"), dups)


def test_the_same_engine_twice_is_not_a_duplicate():
    models = [model("A", [meas("llama.cpp", 40, hardware="RTX 4090 24GB"),
                          meas("llama.cpp", 40, hardware="RTX 3090 24GB")])]
    check("dup: one engine on two machines is two measurements, not a duplicate",
          V.duplicate_runs(models) == [], V.duplicate_runs(models))


def test_a_different_date_or_speed_is_not_a_duplicate():
    models = [model("A", [meas("vLLM", 191, date="2026-10-20"),
                          meas("SGLang", 191, date="2026-10-21"),
                          meas("MLX", 100, date="2026-10-20")])]
    check("dup: a different date or a different t/s is a different run",
          V.duplicate_runs(models) == [], V.duplicate_runs(models))


def test_a_placeholder_post_cannot_identify_a_run():
    models = [model("A", [meas("vLLM", 191, post="https://lightbrd.com/"),
                          meas("MLX", 191, post="https://lightbrd.com/")])]
    check("dup: a placeholder post is never treated as evidence of a duplicate",
          V.duplicate_runs(models) == [], V.duplicate_runs(models))


def test_the_scan_is_report_only_and_registered():
    """It must PRINT and never fail: 22 pairs exist in the history today."""
    src = (ROOT / "scripts" / "validate.py").read_text()
    start = src.index("def check_duplicate_runs(")
    body = src[start:src.index("\ndef ", start + 10)]
    check("dup: the check never calls fail()", "fail(" not in body, body[:200])
    check("dup: it is registered in a stage CI runs",
          'add("duplicate-run scan (report only)", "data"' in src, "")
    check("dup: and its stage is selected by a --only list",
          "data,removal" in (ROOT / "Makefile").read_text(), "")


def test_the_shipped_store_reports_the_known_pair():
    store = json.loads((ROOT / "data" / "models.json").read_text())
    dups = V.duplicate_runs(store.get("models", []))
    check("dup: the shipped store reports at least one pair (the scan is not vacuous)",
          len(dups) >= 1, len(dups))
    out = subprocess.run([sys.executable, str(ROOT / "scripts" / "validate.py"), "--only", "data"],
                         capture_output=True, text=True, cwd=ROOT)
    check("dup: `validate --only data` prints the scan", "duplicate-run scan" in out.stdout,
          out.stdout[-300:])
    check("dup: and the run still SUCCEEDS (report only)", out.returncode == 0, out.returncode)


def main() -> int:
    print("duplicate runs: one run under two engine names (issue #459)")
    test_one_post_two_engine_names_is_reported()
    test_the_same_engine_twice_is_not_a_duplicate()
    test_a_different_date_or_speed_is_not_a_duplicate()
    test_a_placeholder_post_cannot_identify_a_run()
    test_the_scan_is_report_only_and_registered()
    test_the_shipped_store_reports_the_known_pair()
    print(f"PASSED {_PASS} | FAILED {_FAIL}")
    return 0 if _FAIL == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
