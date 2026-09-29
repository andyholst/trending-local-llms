#!/usr/bin/env python3
"""Regression tests for the two refresh-bot AGGREGATE failures.

The aggregate job ran merge + validate and died on two real bugs:
  1. check_search_contract FAILED because the Hermes search agent writes extra
     top-level keys (note, window, queries_used, engines metadata) that
     search_contract.json forbids (additionalProperties:false). self_correct_raw
     filled missing fields but never PRUNED the extras, so the snapshot still
     violated the contract and the aggregate aborted.
  2. check_backend_sort FAILED on correctly-sorted tables because it parsed the
     WHOLE row for numbers — picking up Params ("125B"->125) and VRAM ("12GB")
     as if they were t/s, so a valid table looked unsorted.

Run:  python3 tests/test_aggregate_recovery.py   or   make test
"""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import validate as V  # noqa: E402

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


def raw_snapshot_with_extras() -> dict:
    """A raw search snapshot carrying the extra top-level keys the Hermes agent
    writes, plus one valid model."""
    return {
        "backend": "nvidia",
        "generated_utc": "2026-09-29T12:00:00Z",
        "note": "Captured from lightbrd.com mirror.",
        "window": "last-3-day",
        "queries_used": ["rtx tokens per second llm"],
        "engines": {"llama.cpp": {"backend": "CUDA"}},
        "models": [{
            "id": "qwen3-14b", "name": "Qwen3 14B", "full_name": "Qwen3-14B", "type": "LLM",
            "license": "Apache 2.0", "params": "14B", "hf": "Qwen/Qwen3-14B",
            "vram_tier": "9GB", "vram_min": "8GB", "backends": ["CUDA"],
            "engines": [{"engine": "llama.cpp", "tps": "50", "date": "2026-09-28",
                         "source_post": "https://lightbrd.com/1"}],
            "last_seen": "2026-09-28",
        }],
    }


def test_self_correct_prunes_extra_top_level_keys():
    """Bug 1: a raw snapshot with extra top-level keys must, after
    self_correct_raw, conform to search_contract.json (additionalProperties:false).
    Import the module fresh with a temp RAW_DIR so we don't touch real data/raw."""
    import self_correct_raw as scr

    store = {"engines": {"llama.cpp": {"backend": "CUDA"}}}
    schema = json.loads((ROOT / "data" / "search_contract.json").read_text())

    with tempfile.TemporaryDirectory() as td:
        rdir = Path(td)
        f = rdir / "nvidia-extras.json"
        f.write_text(json.dumps(raw_snapshot_with_extras()))
        saved = scr.RAW_DIR
        scr.RAW_DIR = rdir
        try:
            scr.correct_snapshot(f, store)
            scr.correct_snapshot(f, store)  # idempotent: second pass must be clean too
        finally:
            scr.RAW_DIR = saved
        out = json.loads(f.read_text())
        extra = sorted(set(out.keys()) - {"backend", "generated_utc", "models"})
        check("self_correct prunes extra top-level keys (note/window/queries_used/engines)",
              extra == [], json.dumps(extra))
        # the surviving snapshot must validate against the real contract
        import jsonschema
        try:
            jsonschema.validate(out, schema)
            valid = True
        except Exception:  # noqa: BLE001
            valid = False
        check("pruned snapshot validates against search_contract.json", valid)


def _backend_table_readme(rows: list) -> Path:
    """Build a README with a CUDA backend table that has a Params column and a
    t/s column. rows = list of (params, tps_str). The t/s column is LAST."""
    lines = ["# Trending Local LLMs", "",
             "# 🟦 CUDA — NVIDIA GPUs", "",
             "| Model | Params | License | HF | VRAM | t/s per engine |", "|---|---|---|---|---|---|"]
    for params, tps in rows:
        lines.append(f"| **M** | {params} | Apache | [l](hf) | 12GB | {tps} |")
    lines += ["", "# 🟩 Metal — Apple Silicon", "", "| Model | t/s |", "|---|---|",
              "_No models measured on this backend yet._", "",
              "# 🟨 CPU — no GPU", "", "| Model | t/s |", "|---|---|",
              "_No models measured on this backend yet._"]
    td = tempfile.mkdtemp()
    p = Path(td) / "README.md"
    p.write_text("\n".join(lines))
    return p


def test_backend_sort_uses_tps_column_not_params():
    """Bug 2: check_backend_sort must rank by the t/s cell, not pick up Params.
    Here Params are deliberately LARGER than t/s (e.g. a 125B model at 43.7 t/s)
    and the t/s column is correctly descending — the old whole-row parse saw
    125 and wrongly flagged it unsorted."""
    V.FAILURES.clear()
    saved = V.README
    try:
        V.README = _backend_table_readme([
            ("125B", "233"),   # biggest param, but should rank by 233
            ("27B", "143"),
            ("30B", "100"),
            ("27B", "99.7"),   # params (27/125) would have broken old logic
        ])
        V.check_backend_sort({"models": []})
    finally:
        V.README = saved
    errs = [m for m in V.FAILURES if "not sorted by t/s" in m]
    check("check_backend_sort passes a param-heavy, t/s-descending table",
          not errs, json.dumps(errs))


def test_backend_sort_still_catches_unsorted_tps():
    """Bug 2 guard: a genuinely unsorted t/s column must still fail."""
    V.FAILURES.clear()
    saved = V.README
    try:
        V.README = _backend_table_readme([("8B", "100"), ("27B", "233")])  # 100 then 233 = wrong
        V.check_backend_sort({"models": []})
    finally:
        V.README = saved
    errs = [m for m in V.FAILURES if "not sorted by t/s" in m]
    check("check_backend_sort still catches a real unsorted table", len(errs) == 1, json.dumps(errs))


def test_correct_raw_fixes_extra_fields_and_missing_last_seen():
    """Reproduce the exact aggregate failure (run #36575326343): a raw snapshot
    with extra top-level keys (method, note, search_group, window) AND a model
    missing last_seen. After `make correct-raw` (self_correct_raw) the snapshot
    must (a) have no extra top-level keys and (b) have last_seen filled — so the
    subsequent _validate passes. This is the ordering fix: correct-raw runs
    BEFORE validate in the aggregate job."""
    import self_correct_raw as scr

    store = {"engines": {"llama.cpp": {"backend": "CUDA"}}}
    schema = json.loads((ROOT / "data" / "search_contract.json").read_text())

    raw = {
            "backend": "metal",
            "generated_utc": "2026-09-29T13:40:22Z",
            "method": "firecrawl-scrape",
            "note": "captured",
            "search_group": "metal",
            "window": "last-3-day",
            "models": [{
                "id": "mimo-v2.6-pro", "name": "Mimo 2.6 Pro", "full_name": "Mimo-2.6-Pro",
                "type": "LLM", "license": "Apache 2.0", "params": "27B", "hf": "org/mimo",
                "vram_tier": "16GB", "vram_min": "12GB", "backends": ["Metal"],
                # NOTE: no last_seen — the exact field the aggregate flagged missing
                "engines": [{"engine": "llama.cpp", "tps": "120", "date": "2026-09-29",
                             "source_post": "https://lightbrd.com/m"}],
            }],
        }
    with tempfile.TemporaryDirectory() as td:
        rdir = Path(td)
        f = rdir / "metal-20260929-134022.json"
        f.write_text(json.dumps(raw))
        saved = scr.RAW_DIR
        scr.RAW_DIR = rdir
        try:
            scr.correct_snapshot(f, store)
        finally:
            scr.RAW_DIR = saved
        out = json.loads(f.read_text())
        extra = sorted(set(out.keys()) - {"backend", "generated_utc", "models"})
        check("correct-raw prunes method/note/search_group/window",
              extra == [], json.dumps(extra))
        m = out["models"][0]
        check("correct-raw fills missing last_seen", bool(m.get("last_seen")), m.get("last_seen"))
        import jsonschema
        try:
            jsonschema.validate(out, schema)
            valid = True
        except Exception:  # noqa: BLE001
            valid = False
        check("corrected snapshot validates against search_contract.json", valid)


def main() -> int:
    print("refresh aggregation recovery (search contract extras + backend sort)")
    test_self_correct_prunes_extra_top_level_keys()
    test_correct_raw_fixes_extra_fields_and_missing_last_seen()
    test_backend_sort_uses_tps_column_not_params()
    test_backend_sort_still_catches_unsorted_tps()
    print(f"\nPASSED {_PASS} | FAILED {_FAIL}")
    return 1 if _FAIL else 0


if __name__ == "__main__":
    raise SystemExit(main())
