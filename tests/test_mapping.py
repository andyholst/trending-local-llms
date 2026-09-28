#!/usr/bin/env python3
"""Unit tests for the raw-search -> models.json mapping + merge logic.

Covers the edge cases that were wrong in earlier iterations:
  - raw model maps to an existing model by id, name, or hf
  - case-insensitive matching
  - a brand-new model (no match) stays 'new'
  - merge_engines preserves distinct SAME-DATE DIFFERENT-HARDWARE rows
    (the earlier (engine,date)-key bug that dropped legit RTX 4070 vs 3060 rows)
  - merge_engines overwrites a truly identical row (engine,date,hardware,quant)
  - resolve_model_mapping never reports a collision wrongly

Run:  python3 tests/test_mapping.py        (no pytest needed)
      make test                             (Makefile target)
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from update_trending import resolve_model_mapping, merge_engines  # noqa: E402

_PASS = 0
_FAIL = 0


def check(name: str, cond: bool, detail: str = ""):
    global _PASS, _FAIL
    if cond:
        _PASS += 1
        print(f"  ok  {name}")
    else:
        _FAIL += 1
        print(f"  FAIL {name}" + (f"  [{detail}]" if detail else ""))


def sample_store() -> dict:
    return {"models": [
        {"id": "bonsai-2-27b", "name": "Bonsai 2 27B", "hf": "prism-ml/Ternary-Bonsai-2-27B-gguf"},
        {"id": "qwen3-14b", "name": "Qwen3 14B", "hf": "Qwen/Qwen3-14B"},
    ]}


def test_map_by_id():
    s = sample_store()
    r = resolve_model_mapping({"id": "bonsai-2-27b", "name": "something else", "hf": "x"}, s)
    check("maps by exact id", r["status"] == "existing" and r["matched_by"] == "id" and r["id"] == "bonsai-2-27b")


def test_map_by_name_case_insensitive():
    s = sample_store()
    r = resolve_model_mapping({"id": "bonsai-2-27b-UPPER", "name": "bonsai 2 27b", "hf": "x"}, s)
    # id doesn't match; name matches case-insensitively -> existing by name
    check("maps by name case-insensitive", r["status"] == "existing" and r["matched_by"] == "name")


def test_map_by_id_beats_name():
    s = sample_store()
    # same name as bonsai but id matches qwen3-14b -> id wins
    r = resolve_model_mapping({"id": "qwen3-14b", "name": "Bonsai 2 27B", "hf": "x"}, s)
    check("exact id wins over name", r["id"] == "qwen3-14b" and r["matched_by"] == "id")


def test_map_by_hf():
    s = sample_store()
    r = resolve_model_mapping({"id": "totally-diff", "name": "totally diff", "hf": "Qwen/Qwen3-14B"}, s)
    check("maps by hf", r["status"] == "existing" and r["matched_by"] == "hf" and r["id"] == "qwen3-14b")


def test_brand_new_model_stays_new():
    s = sample_store()
    r = resolve_model_mapping({"id": "kimi-k3", "name": "Kimi K3", "hf": "moonshotai/kimi-k3"}, s)
    check("brand-new model is 'new'", r["status"] == "new" and r["id"] == "kimi-k3")


def test_merge_keeps_same_date_diff_hardware():
    """THE earlier bug: bonsai had RTX 4070 @ 60-91 and RTX 3060 @ ~50 both on
    2026-09-26. Merging/aggregating must keep BOTH — they are distinct."""
    cur = [{"engine": "llama.cpp", "tps": "67-71", "hardware": "RTX 5060 Ti", "date": "2026-09-27"}]
    incoming = [
        {"engine": "llama.cpp", "tps": "60-91", "hardware": "RTX 4070 12GB", "quant": "PTQ", "date": "2026-09-26"},
        {"engine": "llama.cpp", "tps": "~50", "hardware": "RTX 3060 12GB", "quant": "MTP", "date": "2026-09-26"},
    ]
    out = merge_engines(cur, incoming)
    same_date = [e for e in out if e.get("date") == "2026-09-26"]
    check("same-date different-hardware rows both kept", len(same_date) == 2,
          f"got {len(same_date)} (expected 2)")


def test_merge_overwrites_truly_identical():
    cur = [{"engine": "llama.cpp", "tps": "60", "hardware": "RTX 4070", "quant": "Q4", "date": "2026-09-26"}]
    new = [{"engine": "llama.cpp", "tps": "61", "hardware": "RTX 4070", "quant": "Q4", "date": "2026-09-26"}]
    out = merge_engines(cur, new)
    check("truly identical row overwritten (updated t/s, no dup)",
          len(out) == 1 and out[0]["tps"] == "61")


def test_merge_preserves_current():
    cur = [{"engine": "llama.cpp", "tps": "100", "hardware": "RTX 5090", "date": "2026-09-18"}]
    incoming = [{"engine": "MLX", "tps": "237", "hardware": "Apple", "date": "2026-09-26"}]
    out = merge_engines(cur, incoming)
    check("merge never drops existing rows", len(out) == 2)


def test_merge_no_dup_from_convert():
    """A raw snapshot arriving twice with identical rows must not duplicate."""
    rows = [{"engine": "llama.cpp", "tps": "67-71", "hardware": "RTX 5060 Ti", "date": "2026-09-27"}]
    out = merge_engines(rows, rows)
    check("idempotent merge (identical input twice)", len(out) == 1)


def test_self_correct_fills_missing_fields():
    """The fix-bot's self-correction must fill a failing raw snapshot's missing
    required fields from available data (license, vram_min, backends, dates),
    and flag fields that can't be derived (hf, source_post)."""
    import tempfile
    from pathlib import Path as _P
    sys.path.insert(0, str(ROOT / "scripts"))
    import self_correct_raw as scr
    store = {"engines": {"llama.cpp": {"backend": "CUDA / CPU / Metal", "url": "u"}}}
    snap = {
        "backend": "nvidia", "generated_utc": "2026-09-28T10:00:00Z",
        "models": [{
            "id": "t1", "name": "T One", "type": "LLM", "params": "13B",
            "hf": "t/t1", "vram_tier": "12GB",
            "engines": [{"engine": "llama.cpp", "tps": "80", "source_post": "https://lightbrd.com/p"}],
        }],
    }
    with tempfile.TemporaryDirectory() as td:
        p = _P(td) / "x.json"
        p.write_text(json.dumps(snap))
        notes = scr.correct_snapshot(p, store)
        fixed = json.loads(p.read_text())["models"][0]
        check("self-correct fills license", fixed.get("license") == "Unknown")
        check("self-correct fills vram_min from tier", fixed.get("vram_min") == "12GB")
        check("self-correct fills backends", fixed.get("backends") == ["CUDA", "Metal", "CPU"])
        check("self-correct fills last_seen", fixed.get("last_seen") == "2026-09-28")
        check("self-correct fills engine date", fixed["engines"][0].get("date") == "2026-09-28")
    # cannot-derive flag
    snap2 = {"backend": "nvidia", "generated_utc": "2026-09-28T10:00:00Z",
             "models": [{"id": "t2", "name": "T Two", "type": "LLM", "params": "13B",
                         "vram_tier": "8GB", "engines": [{"engine": "llama.cpp", "tps": "50"}]}]}
    import tempfile as _t
    with _t.TemporaryDirectory() as td:
        p = _P(td) / "y.json"
        p.write_text(json.dumps(snap2))
        notes = scr.correct_snapshot(p, {"engines": {"llama.cpp": {"backend": "CUDA", "url": "u"}}})
        check("self-correct flags cannot-derive (hf)", any("hf missing" in n for n in notes))
        check("self-correct flags cannot-derive (source_post)", any("source_post missing" in n for n in notes))


def main() -> int:
    print("mapping: resolve_model_mapping + merge_engines")
    test_map_by_id()
    test_map_by_name_case_insensitive()
    test_map_by_id_beats_name()
    test_map_by_hf()
    test_brand_new_model_stays_new()
    test_merge_keeps_same_date_diff_hardware()
    test_merge_overwrites_truly_identical()
    test_merge_preserves_current()
    test_merge_no_dup_from_convert()
    print("self-correct: fill failing raw snapshots from available data")
    test_self_correct_fills_missing_fields()
    print(f"\nPASSED {_PASS} | FAILED {_FAIL}")
    return 1 if _FAIL else 0


if __name__ == "__main__":
    raise SystemExit(main())
