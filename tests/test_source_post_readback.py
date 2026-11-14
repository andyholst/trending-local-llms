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
                 "context_tokens": row.get("context_tokens", ""),
                 "engine_min_version": row.get("engine_min_version", "")}]})
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


def _ship_store_and_raw():
    """The REAL shipped store + the REAL raw snapshot dir (no fixtures, rule 6m).

    `load_store()` is the same seam the pipeline and `make validate` use: it flattens
    `data/models.json` (catalog) + `data/measurements.json` + `data/posts.json` into the
    inline shape every validator — and `source_post_figure_flags` — reads.
    """
    import update_trending as UT
    return UT.load_store(), ROOT / "data" / "raw"


def test_the_shipped_store_flags_no_unsupported_footprint_values():
    """Issue #788 Done-when: the shipped store's readback residue is pinned at ZERO.

    #531's scan flagged 23 values; the reconciling merges landed and the count is now 0.
    This test is the gate that blocks the drift from returning: it runs the REAL scan over
    the REAL `data/models.json` + `data/raw/` and names every flagged value if any appears.
    """
    store, raw = _ship_store_and_raw()
    flags = V.source_post_figure_flags(store, raw)
    detail = "\n".join(f"    {m} {eng} {tps} {field}={value!r} cites {sp}"
                       for m, eng, tps, field, value, sp in flags)
    check(f"shipped store flags {len(flags)} unsupported footprint value(s) — "
          f"residue must be 0{chr(10) + detail if detail else ''}",
          flags == [], detail)


def test_the_store_gate_fires_on_a_planted_drift():
    """The shipped-store gate is LIVE: planting the #531 drift (a `weight_gb` the cited post
    nowhere states, the `5.93GB` vs `5.95GB` class) into a copy of the REAL store must make
    the SAME scan return exactly that flag, attributed to model, field, value and post."""
    import copy
    store, raw = _ship_store_and_raw()
    target = None
    for m in store.get("models", []):
        for e in m.get("engines", []):
            if e.get("weight_gb"):
                target = (m, e)
                break
        if target:
            break
    if target is None:
        check("the shipped store carries a weight_gb footprint to plant against", False,
              "no footprint row found")
        return
    m, e = target
    planted = "7.41GB"
    mutated = copy.deepcopy(store)
    for mm in mutated["models"]:
        if mm.get("id") == m.get("id"):
            for ee in mm.get("engines", []):
                if ee.get("engine") == e.get("engine") and ee.get("tps") == e.get("tps"):
                    ee["weight_gb"] = planted
    base = V.source_post_figure_flags(mutated, raw)
    hit = [f for f in base if f[0] == str(m.get("id")) and f[3] == "weight_gb"
           and f[4] == planted]
    check("the planted drift is flagged with full attribution",
          len(hit) == 1 and hit[0][5] == str(e.get("source_post")),
          "; ".join(f"{f[0]}/{f[3]}={f[4]}" for f in hit[:2]))
    check("and it is the ONLY new flag (the scan stays precise on the shipped store)",
          len(base) == 1,
          "; ".join(f"{f[0]}/{f[3]}={f[4]}" for f in base[:4]))


def _raw_with(captures):
    td = tempfile.TemporaryDirectory()
    raw = Path(td.name) / "raw"
    raw.mkdir()
    write_raw(raw, captures)
    return td, raw


def test_a_declared_estimate_is_attributable_not_a_contradiction():
    """Issue #788: a value carrying the canonical `(est)` marker (rule 2) is a DECLARED
    estimate — attributable on its row — so the scan never flags it as a contradiction, and
    `source_post_declared_estimates` counts it toward the visible residue."""
    store = store_with([{"engine": "llama.cpp", "tps": "72", "hardware": "M5 Max",
                         "quant": "8-bit MLX build", "date": "2026-10-05",
                         "source_post": SP1, "weight_gb": "~29.5GB (est; 8-bit MLX)"}])
    td, raw = _raw_with({"nvidia-1.json": {SP1: {"quant": "8-bit MLX build"}}})
    flags = V.source_post_figure_flags(store, raw)
    check("an (est)-marked value is never a contradiction flag", not flags, flags)
    check("and it is counted as a declared estimate",
          V.source_post_declared_estimates(store) == 1,
          V.source_post_declared_estimates(store))
    td.cleanup()
    # Precision opposite: the SAME value WITHOUT the marker is still flagged.
    store2 = store_with([{"engine": "llama.cpp", "tps": "72", "hardware": "M5 Max",
                          "quant": "8-bit MLX build", "date": "2026-10-05",
                          "source_post": SP1, "weight_gb": "~29.5GB (8-bit MLX)"}])
    td2, raw2 = _raw_with({"nvidia-1.json": {SP1: {"quant": "8-bit MLX build"}}})
    flags2 = V.source_post_figure_flags(store2, raw2)
    check("the same unmarked value stays flagged (the marker is the only exemption)",
          len(flags2) == 1 and flags2[0][3] == "weight_gb", flags2)
    td2.cleanup()


def test_the_captures_own_structured_value_supports_a_fuller_distillation():
    """Issue #788 precision: the capture's structured `engine_min_version` "MTP=2" supports
    the store's fuller distillation "llama.cpp with MTP=2" of the SAME claim (the shipped
    `qwen3.8-27b llama.cpp 51.8` row was flagged only because containment ran one way).
    Free text stays one-way — a capture's prose never confirms a longer stored guess."""
    store = store_with([{"engine": "llama.cpp", "tps": "51.8", "hardware": "RTX 5090",
                         "quant": "Q4_K_M", "date": "2026-10-05", "source_post": SP1,
                         "engine_min_version": "llama.cpp with MTP=2"}])
    td, raw = _raw_with({"nvidia-1.json": {SP1: {"quant": "Q4_K_M",
                                                  "engine_min_version": "MTP=2"}}})
    flags = V.source_post_figure_flags(store, raw)
    check("the capture's own structured field confirms the store's distillation",
          not flags, flags)
    td.cleanup()
    # Precision: a structured value under ANOTHER field does not leak support.
    td2, raw2 = _raw_with({"nvidia-1.json": {SP1: {"quant": "Q4_K_M",
                                                    "context_tokens": "MTP=2"}}})
    flags2 = V.source_post_figure_flags(store, raw2)
    check("a structured value of a different field confirms nothing",
          len(flags2) == 1 and flags2[0][3] == "engine_min_version", flags2)
    td2.cleanup()
    # Precision: free text stays one-way (stored value must appear IN the text).
    store3 = store_with([{"engine": "llama.cpp", "tps": "51.8", "hardware": "RTX 5090",
                          "quant": "llama.cpp with MTP=2 draft head", "date": "2026-10-05",
                          "source_post": SP1,
                          "engine_min_version": "llama.cpp with MTP=2 plus parser tail prose"}])
    td3, raw3 = _raw_with({"nvidia-1.json": {SP1: {"quant": "llama.cpp with MTP=2 draft head"}}})
    flags3 = V.source_post_figure_flags(store3, raw3)
    check("a stored distillation longer than the post prose is still flagged",
          len(flags3) == 1, flags3)
    td3.cleanup()


def test_annotation_brackets_do_not_break_confirmation():
    """Issue #788: `official checkpoints (no extreme quantization)` (stored) confirms against
    the post's own `official checkpoints, no extreme quantization` — annotation brackets are
    presentation, not a different figure (the shipped qwen3.6-35b-a3b row was flagged only on
    the parenthesis)."""
    store = store_with([{"engine": "llama.cpp", "tps": "39.3", "hardware": "RTX 3090",
                         "quant": "official checkpoints, no extreme quantization",
                         "date": "2026-10-05", "source_post": SP1,
                         "weight_gb": "official checkpoints (no extreme quantization)"}])
    td, raw = _raw_with({"nvidia-1.json": {SP1: {
        "quant": "official checkpoints, no extreme quantization"}}})
    flags = V.source_post_figure_flags(store, raw)
    check("bracketed annotation matches the post phrase", not flags, flags)
    td.cleanup()


def main() -> int:
    print("the source-post readback scan (issue #531)")
    test_a_stored_value_the_capture_states_is_kept()
    test_a_contradicted_stored_value_is_flagged()
    test_a_value_in_the_capture_structured_field_is_kept()
    test_a_cards_vram_never_confirms_a_weight_footprint()
    test_an_uncaptured_post_is_skipped()
    test_the_scan_is_report_only_it_never_fails()
    test_the_shipped_store_flags_no_unsupported_footprint_values()
    test_the_store_gate_fires_on_a_planted_drift()
    test_a_declared_estimate_is_attributable_not_a_contradiction()
    test_the_captures_own_structured_value_supports_a_fuller_distillation()
    test_annotation_brackets_do_not_break_confirmation()
    print(f"\nPASSED {_PASS} | FAILED {_FAIL}")
    return 1 if _FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
