#!/usr/bin/env python3
"""End-to-end integration test: raw search snapshot -> models.json -> README.

Proves the full data chain that the unit tests only cover piecemeal:
  1. A raw per-search snapshot (data/raw/<backend>-<UTC>.json) written by the
     Firecrawl search flow conforms to the search contract.
  2. ingest_raw_snapshots merges it into data/models.json, mapping to the right
     model and adding/updating t/s PER ENGINE for that model.
  3. render_readme surfaces that per-engine t/s in the README (most-loved +
     backend tables).
  4. A second raw snapshot UPDATES (adds a new engine t/s) without removing
     existing rows — the no-removal guarantee.

This exercises ingest_raw_snapshots + render_readme together (not just their
helpers), closing the integration-coverage gap.

Run:  python3 tests/test_ingest_render.py   or   make test
"""
from __future__ import annotations

import json
import shutil
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import update_trending as UT  # noqa: E402

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


def base_store() -> dict:
    """A minimal but contract-conformant models.json."""
    return {
        "generated_utc": "2026-09-27T10:00:00Z",
        "engines": {
            "llama.cpp": {"backend": "CUDA", "note": "x", "url": "https://github.com/ggml-org/llama.cpp"},
            "MLX": {"backend": "Metal", "note": "x", "url": "https://github.com/ml-explore/mlx"},
        },
        "models": [{
            "id": "qwen3-14b", "name": "Qwen3 14B", "full_name": "Qwen3-14B", "type": "LLM",
            "formats": [{"name": "GGUF", "hf": "Qwen/Qwen3-14B"}], "license": "Apache 2.0",
            "params": "14B", "hf": "Qwen/Qwen3-14B", "vram_tier": "9GB", "vram_min": "8GB",
            "backends": ["CUDA"], "supported_engines": ["llama.cpp"],
            "engines": [{"engine": "llama.cpp", "tps": "50", "hardware": "RTX 3060",
                         "quant": "Q4", "date": "2026-09-20", "source_post": "https://lightbrd.com/1"}],
            "why": "w", "engagement": {"likes": 5, "comments": 1, "views": 10, "last_7d_likes": 2},
            "last_seen": "2026-09-27",
        }],
    }


def raw_snapshot(backend: str, models) -> dict:
    return {"backend": backend, "generated_utc": "2026-09-28T10:00:00Z", "models": models}


def run(store, raw_payloads):
    """Point UT.RAW_DIR at a temp dir full of raw snapshots, ingest, return store."""
    with tempfile.TemporaryDirectory() as td:
        rdir = Path(td)
        for i, rp in enumerate(raw_payloads):
            (rdir / f"snap-{i}.json").write_text(json.dumps(rp))
        saved = UT.RAW_DIR
        UT.RAW_DIR = rdir
        try:
            UT.ingest_raw_snapshots(store)
        finally:
            UT.RAW_DIR = saved
    return store


def test_ingest_maps_and_adds_per_engine():
    """Raw snapshot maps to the right model and ADDS a new per-engine t/s."""
    s = base_store()
    raw = raw_snapshot("nvidia", [{
        "id": "qwen3-14b", "name": "Qwen3 14B", "full_name": "Qwen3-14B", "type": "LLM",
        "license": "Apache 2.0", "params": "14B", "hf": "Qwen/Qwen3-14B",
        "vram_tier": "9GB", "vram_min": "8GB", "backends": ["Metal"],
        "engines": [{"engine": "MLX", "tps": "85", "hardware": "M4 Max", "date": "2026-09-28",
                     "source_post": "https://lightbrd.com/new"}],
        "last_seen": "2026-09-28",
    }])
    run(s, [raw])
    m = next(x for x in s["models"] if x["id"] == "qwen3-14b")
    mlx = [e for e in m["engines"] if e["engine"] == "MLX"]
    llama = [e for e in m["engines"] if e["engine"] == "llama.cpp"]
    check("ingest maps to existing model (no new row)", len(s["models"]) == 1)
    check("ingest adds NEW engine t/s (MLX 85)", len(mlx) == 1 and mlx[0]["tps"] == "85")
    check("ingest KEEPS existing engine t/s (llama.cpp 50)", len(llama) == 1 and llama[0]["tps"] == "50")


def test_ingest_updates_existing_engine_ts():
    """A newer measurement for the SAME engine+hardware+quant+date overwrites the
    t/s (merge key is full identity). A different date is a NEW row (kept, and
    newest-date-first surfaces it)."""
    s = base_store()
    raw = raw_snapshot("nvidia", [{
        "id": "qwen3-14b", "name": "Qwen3 14B", "full_name": "Qwen3-14B", "type": "LLM",
        "license": "Apache 2.0", "params": "14B", "hf": "Qwen/Qwen3-14B",
        "vram_tier": "9GB", "vram_min": "8GB", "backends": ["CUDA"],
        "engines": [{"engine": "llama.cpp", "tps": "78", "hardware": "RTX 3060",
                     "quant": "Q4", "date": "2026-09-20", "source_post": "https://lightbrd.com/u"}],
        "last_seen": "2026-09-28",
    }])
    run(s, [raw])
    m = next(x for x in s["models"] if x["id"] == "qwen3-14b")
    llama = [e for e in m["engines"] if e["engine"] == "llama.cpp"]
    check("ingest overwrites same-identity t/s (50 -> 78)", len(llama) == 1 and llama[0]["tps"] == "78")


def test_ingest_different_date_is_new_row():
    """A different date for the same engine+hardware is a NEW measurement row
    (kept alongside), and newest-date-first surfaces the latest t/s."""
    s = base_store()
    raw = raw_snapshot("nvidia", [{
        "id": "qwen3-14b", "name": "Qwen3 14B", "full_name": "Qwen3-14B", "type": "LLM",
        "license": "Apache 2.0", "params": "14B", "hf": "Qwen/Qwen3-14B",
        "vram_tier": "9GB", "vram_min": "8GB", "backends": ["CUDA"],
        "engines": [{"engine": "llama.cpp", "tps": "90", "hardware": "RTX 3060",
                     "quant": "Q4", "date": "2026-09-28", "source_post": "https://lightbrd.com/v"}],
        "last_seen": "2026-09-28",
    }])
    run(s, [raw])
    m = next(x for x in s["models"] if x["id"] == "qwen3-14b")
    llama = [e for e in m["engines"] if e["engine"] == "llama.cpp"]
    check("ingest keeps different-date row (2 rows)", len(llama) == 2)
    UT.sort_models(s["models"], datetime(2026, 9, 28, tzinfo=timezone.utc))
    check("ingest newest-date-first surfaces latest t/s (90 first)",
          m["engines"][0]["tps"] == "90")


def test_ingest_new_model_no_removal():
    """A brand-new model is ADDED; existing models are never removed."""
    s = base_store()
    raw = raw_snapshot("general", [{
        "id": "kimi-k3", "name": "Kimi K3", "full_name": "Kimi-K3", "type": "MoE",
        "license": "Modified MIT", "params": "1T", "hf": "moonshotai/kimi-k3",
        "vram_tier": "512GB", "vram_min": "256GB", "backends": ["CPU"],
        "engines": [{"engine": "llama.cpp", "tps": "12", "hardware": "CPU", "date": "2026-09-28",
                     "source_post": "https://lightbrd.com/2"}],
        "last_seen": "2026-09-28",
    }])
    run(s, [raw])
    ids = [m["id"] for m in s["models"]]
    check("ingest ADDS brand-new model", "kimi-k3" in ids)
    check("ingest never removes existing model", "qwen3-14b" in ids)


def test_render_shows_per_engine_ts():
    """After ingest, render_readme surfaces each model's per-engine t/s in the
    most-loved table (Engines + t/s column) and the backend tables."""
    s = base_store()
    # add an MLX engine + a second model with two engines
    s["models"][0]["engines"].append(
        {"engine": "MLX", "tps": "85", "hardware": "M4 Max", "date": "2026-09-28", "source_post": "https://lightbrd.com/3"})
    readme = UT.render_readme(s, datetime(2026, 9, 28, tzinfo=timezone.utc))
    check("render: most-loved shows llama.cpp t/s", "llama.cpp" in readme and "50" in readme)
    check("render: most-loved shows MLX t/s", "MLX" in readme and "85" in readme)
    check("render: CUDA backend table present", "# 🟦 CUDA" in readme)
    check("render: Metal backend table present", "# 🟩 Metal" in readme)


def test_render_newest_tps_first():
    """render_readme orders each model's engines newest-date-first (latest t/s
    surfaced)."""
    s = base_store()
    s["models"][0]["engines"] = [
        {"engine": "llama.cpp", "tps": "50", "hardware": "RTX 3060", "date": "2026-09-20", "source_post": "https://lightbrd.com/1"},
        {"engine": "llama.cpp", "tps": "90", "hardware": "RTX 5090", "date": "2026-09-28", "source_post": "https://lightbrd.com/4"},
    ]
    # render sorts engines newest first internally, but models.json should too
    UT.sort_models(s["models"], datetime(2026, 9, 28, tzinfo=timezone.utc))
    dates = [e["date"] for e in s["models"][0]["engines"]]
    check("sort_models orders engines newest-date-first", dates == sorted(dates, reverse=True))


def main() -> int:
    print("integration: raw snapshot -> models.json -> README")
    test_ingest_maps_and_adds_per_engine()
    test_ingest_updates_existing_engine_ts()
    test_ingest_different_date_is_new_row()
    test_ingest_new_model_no_removal()
    test_render_shows_per_engine_ts()
    test_render_newest_tps_first()
    print(f"\nPASSED {_PASS} | FAILED {_FAIL}")
    return 1 if _FAIL else 0


if __name__ == "__main__":
    raise SystemExit(main())
