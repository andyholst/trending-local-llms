#!/usr/bin/env python3
"""The source-post readback scan (issue #531): a stored figure its captured post nowhere states.

`data/models.json` carries a measurement's `source_post`, and `data/raw/*.json` holds the
captured text of those posts. Nothing compared the two, so a stored figure could contradict
the post it cites while every gate stayed green — measured: `bonsai-2-27b` carried
`weight_gb: "5.93GB"` for a post all three captures state as `5.95GB`.

These tests run the REAL `source_post_figure_flags` against a REAL temp raw-snapshot tree —
no mock of the business logic (rule 6m). They lock the readback: a stored value the capture
states is kept, one the capture nowhere states is flagged, a captured structured field
confirms a value the free text lacks, a card's VRAM never confirms a weight footprint, an
uncaptured post is skipped, and the scan is report-only.

Run:  python3 tests/test_source_post_readback.py   or   make test
"""
from __future__ import annotations

import contextlib
import io
import json
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import validate as V  # noqa: E402

_PASS = 0
_FAIL = 0

SP1 = "https://lightbrd.com/u1/status/1"
SP2 = "https://lightbrd.com/u2/status/2"
SP3 = "https://lightbrd.com/u3/status/3"
SP5 = "https://lightbrd.com/u5/status/5"
SP404 = "https://lightbrd.com/u404/status/404"


def check(name, cond, detail=""):
    global _PASS, _FAIL
    if cond:
        _PASS += 1
        print(f"  ok  {name}")
    else:
        _FAIL += 1
        print(f"  FAIL {name}" + (f"  [{detail}]" if detail else ""))


def store_with(engine_rows):
    """A minimal flat store whose model `m1` carries the given engine/measurement rows."""
    return {"models": [{
        "id": "m1", "name": "Model One", "full_name": "Model-One", "type": "LLM",
        "formats": [{"name": "GGUF", "hf": "a/m1"}], "license": "Apache 2.0",
        "params": "13B", "hf": "a/m1", "vram_tier": "12GB", "vram_min": "8GB",
        "backends": ["CUDA"], "supported_engines": ["llama.cpp"],
        "engines": engine_rows, "why": "w",
        "engagement": {"likes": 1, "comments": 1, "views": 1, "last_7d_likes": 1},
        "last_seen": "2026-10-05",
    }]}


def write_raw(raw_dir: Path, captures):
    """Write each `{filename: {source_post: row}}` map as a real search snapshot."""
    for fname, snap in captures.items():
        models = []
        for sp, row in snap.items():
            models.append({"id": "m1", "name": "Model One", "engines": [
                {"engine": "llama.cpp", "tps": "100", "quant": row.get("quant", ""),
                 "hardware": row.get("hardware", ""), "date": "2026-10-05",
                 "source_post": sp, "weight_gb": row.get("weight_gb", ""),
                 "context_tokens": row.get("context_tokens", "")}]})
        (raw_dir / fname).write_text(json.dumps(
            {"backend": "nvidia", "generated_utc": "2026-10-05T23:36:47Z", "models": models}))


def test_a_stored_value_the_capture_states_is_kept():
    store = store_with([{"engine": "llama.cpp", "tps": "146", "hardware": "RTX 5090",
                         "quant": "5.95GB ternary", "date": "2026-10-05",
                         "source_post": SP1, "weight_gb": "5.95GB"}])
    with tempfile.TemporaryDirectory() as td:
        raw = Path(td) / "raw"; raw.mkdir()
        write_raw(raw, {"nvidia-1.json": {SP1: {"quant": "PTQ1_0 ternary (5.95 GB weights), thinking mode"}}})
        flags = V.source_post_figure_flags(store, raw)
    check("stated value is kept (spacing-insensitive match)", not flags, flags)


def test_a_contradicted_stored_value_is_flagged():
    store = store_with([{"engine": "llama.cpp", "tps": "146", "hardware": "RTX 5090",
                         "quant": "5.95GB ternary", "date": "2026-10-05",
                         "source_post": SP2, "weight_gb": "5.93GB"}])
    with tempfile.TemporaryDirectory() as td:
        raw = Path(td) / "raw"; raw.mkdir()
        write_raw(raw, {"nvidia-1.json": {SP2: {"quant": "5.95GB ternary (PTQ1_0), SDK runtime"}}})
        flags = V.source_post_figure_flags(store, raw)
    check("contradicted value is flagged", len(flags) == 1, flags)
    if flags:
        check("flag names field, value and post",
              flags[0][3] == "weight_gb" and flags[0][4] == "5.93GB" and flags[0][5] == SP2, flags[0])


def test_a_value_in_the_capture_structured_field_is_kept():
    store = store_with([{"engine": "llama.cpp", "tps": "146", "hardware": "RTX 5090",
                         "quant": "5.95GB ternary", "date": "2026-10-05",
                         "source_post": SP3, "context_tokens": "262144"}])
    with tempfile.TemporaryDirectory() as td:
        raw = Path(td) / "raw"; raw.mkdir()
        # The capture's STRUCTURED context_tokens states it; its free text states no window.
        write_raw(raw, {"nvidia-1.json": {SP3: {"quant": "5.95GB ternary",
                                                "context_tokens": "262144"}}})
        flags = V.source_post_figure_flags(store, raw)
    check("a captured structured field confirms the value", not flags, flags)


def test_a_cards_vram_never_confirms_a_weight_footprint():
    store = store_with([{"engine": "llama.cpp", "tps": "100", "hardware": "RTX 5090",
                         "quant": "PTQ1_0 ternary", "date": "2026-10-05",
                         "source_post": SP5, "weight_gb": "16GB"}])
    with tempfile.TemporaryDirectory() as td:
        raw = Path(td) / "raw"; raw.mkdir()
        # The 16GB lives ONLY in the hardware field (a card's VRAM) — never a weights figure.
        write_raw(raw, {"nvidia-1.json": {SP5: {"quant": "PTQ1_0 ternary", "hardware": "16GB 16GB GPU"}}})
        flags = V.source_post_figure_flags(store, raw)
    check("hardware VRAM does not certify a weight footprint", len(flags) == 1, flags)


def test_an_uncaptured_post_is_skipped():
    store = store_with([{"engine": "llama.cpp", "tps": "146", "hardware": "RTX 5090",
                         "quant": "5.95GB ternary", "date": "2026-10-05",
                         "source_post": SP404, "weight_gb": "5.93GB"}])
    with tempfile.TemporaryDirectory() as td:
        raw = Path(td) / "raw"; raw.mkdir()
        write_raw(raw, {"nvidia-1.json": {SP1: {"quant": "5.95GB ternary"}}})
        flags = V.source_post_figure_flags(store, raw)
    check("a post no snapshot captured is not checked", not flags, flags)


def test_the_scan_is_report_only_it_never_fails():
    store = store_with([{"engine": "llama.cpp", "tps": "146", "hardware": "RTX 5090",
                         "quant": "5.95GB ternary", "date": "2026-10-05",
                         "source_post": SP2, "weight_gb": "5.93GB"}])
    with tempfile.TemporaryDirectory() as td:
        raw = Path(td) / "raw"; raw.mkdir()
        write_raw(raw, {"nvidia-1.json": {SP2: {"quant": "5.95GB ternary"}}})
        saved, V.RAW_DIR = V.RAW_DIR, raw
        V.FAILURES.clear()
        buf = io.StringIO()
        try:
            with contextlib.redirect_stdout(buf):
                V.check_source_post_readback(store)
        finally:
            V.RAW_DIR = saved
    check("the scan reports but adds NO failure", len(V.FAILURES) == 0, V.FAILURES)
    check("… and prints the contradiction, not a silent pass",
          "NEITHER the capture's fields NOR the post text" in buf.getvalue(), buf.getvalue()[:200])


def main() -> int:
    print("the source-post readback scan (issue #531)")
    test_a_stored_value_the_capture_states_is_kept()
    test_a_contradicted_stored_value_is_flagged()
    test_a_value_in_the_capture_structured_field_is_kept()
    test_a_cards_vram_never_confirms_a_weight_footprint()
    test_an_uncaptured_post_is_skipped()
    test_the_scan_is_report_only_it_never_fails()
    print(f"\nPASSED {_PASS} | FAILED {_FAIL}")
    return 1 if _FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
