"""tests/test_model_footprint_copy.py — model-level footprint copies trace to the model's own data (issue #934).

The catalog copy of a footprint (a model-level `weight_gb` / `context_tokens` /
`system_ram_min` / `storage_offload`) was seeded from the search snapshots but never
cross-checked against them: 72 model-level fields matched no measurement row when #934 measured
the gap. This suite locks `scripts/validate.py`'s `data`-stage gate: a HARD model-level copy
must match a value captured FOR that model (its measurement rows, its raw captures row- or
measurement-level, or the structured fields of the posts its rows cite), or carry the canonical
`(est)` marker (rule 2); `engine_min_version` distillations stay report-only (#789 precedent).
Runs as a plain module (no pytest), like every test in this repo.
"""
from __future__ import annotations

import contextlib
import io
import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import validate as V  # noqa: E402

_PASS = 0
_FAIL = 0

SP1 = "https://lightbrd.com/u1/status/1"


def check(name, cond, detail=""):
    global _PASS, _FAIL
    if cond:
        _PASS += 1
        print(f"  ok  {name}")
    else:
        _FAIL += 1
        print(f"  FAIL {name}" + (f"  [{detail}]" if detail else ""))


def model_store(**model_level):
    """A minimal flat store: model `m1` carrying the given MODEL-LEVEL footprint fields."""
    m = {
        "id": "m1", "name": "Model One", "full_name": "Model-One", "type": "LLM",
        "formats": [{"name": "GGUF", "hf": "a/m1"}], "license": "Apache 2.0",
        "params": "13B", "hf": "a/m1", "vram_tier": "12GB", "vram_min": "8GB",
        "backends": ["CUDA"], "supported_engines": ["llama.cpp"],
        "engines": [], "why": "w",
        "engagement": {"likes": 1, "comments": 1, "views": 1, "last_7d_likes": 1},
        "last_seen": "2026-10-05",
    }
    m.update(model_level)
    return {"models": [m]}


def write_snapshot(raw_dir: Path, *, row_level=None, engines=None):
    """One real search snapshot with a `m1` row: row-level footprint and/or measurement rows."""
    row = {"id": "m1", "name": "Model One"}
    row.update(row_level or {})
    row["engines"] = list(engines or [])
    (raw_dir / "nvidia-1.json").write_text(json.dumps(
        {"backend": "nvidia", "generated_utc": "2026-10-05T23:36:47Z", "models": [row]}))


def raw_with(**snapshot_kwargs):
    td = tempfile.TemporaryDirectory()
    raw = Path(td.name) / "raw"
    raw.mkdir()
    write_snapshot(raw, **snapshot_kwargs)
    return td, raw


def flags_of(store, raw):
    return V.model_level_footprint_flags(store, raw)


def gate_failures(store, raw):
    """Run `check_model_footprint_copy` against a swapped RAW_DIR; return (failures, stdout)."""
    saved, V.RAW_DIR = V.RAW_DIR, raw
    V.FAILURES.clear()
    buf = io.StringIO()
    try:
        with contextlib.redirect_stdout(buf):
            V.check_model_footprint_copy(store)
        return list(V.FAILURES), buf.getvalue()
    finally:
        V.RAW_DIR = saved
        V.FAILURES.clear()


def test_row_match_passes():
    """Scenario: model-level value matching a measurement row passes."""
    store = model_store(weight_gb="19GB (MLX 4-bit)")
    store["models"][0]["engines"] = [
        {"engine": "MLX", "tps": "76", "hardware": "M4 Max", "quant": "4-bit",
         "date": "2026-10-05", "source_post": SP1, "weight_gb": "19GB (MLX 4-bit)"}]
    td, raw = raw_with()
    hard, prose = flags_of(store, raw)
    check("a model-level copy identical to its measurement row is supported", not hard, hard)
    problems, _ = gate_failures(store, raw)
    check("and the data-stage gate stays green", not problems, problems)
    td.cleanup()


def test_capture_match_passes():
    """Scenario: model-level value captured in the model's raw snapshots passes — the copy may
    be a fuller distillation of the captured figure (`17.74GB (Q3_K_XL)` ⊃ `17.74GB`)."""
    store = model_store(weight_gb="17.74GB (Q3_K_XL)")
    td, raw = raw_with(engines=[
        {"engine": "llama.cpp", "tps": "40", "hardware": "RTX 4070 Ti Super",
         "quant": "Q3_K_XL", "date": "2026-10-05", "source_post": SP1,
         "weight_gb": "17.74GB"}])
    hard, _ = flags_of(store, raw)
    check("a measurement-level capture of the model supports the catalog copy", not hard, hard)
    # and the row-level capture spelling too
    td2, raw2 = raw_with(row_level={"weight_gb": "17.74GB"})
    hard2, _ = flags_of(store, raw2)
    check("a row-level capture of the model supports it too", not hard2, hard2)
    td.cleanup(); td2.cleanup()


def test_ksuffix_expansion_passes():
    """Scenario: K-suffix notation is the same figure — `200000` matches a captured `200K`
    both ways; a DIFFERENT figure (`300000`) is still flagged."""
    td, raw = raw_with(engines=[
        {"engine": "llama.cpp", "tps": "40", "hardware": "RTX 4060 Ti", "quant": "IQ4_XS",
         "date": "2026-10-05", "source_post": SP1, "context_tokens": "200K"}])
    hard, _ = flags_of(model_store(context_tokens="200000"), raw)
    check("a raw number matches the captured K-notation", not hard, hard)
    hard2, _ = flags_of(model_store(context_tokens="200K"), raw)
    check("and the K-notation copy matches the captured K-notation", not hard2, hard2)
    hard3, _ = flags_of(model_store(context_tokens="300000"), raw)
    check("a different figure is still flagged (expansion does not blur figures)",
          len(hard3) == 1 and hard3[0][1] == "context_tokens", hard3)
    td.cleanup()


def test_untraceable_copy_fails():
    """Scenario: an untraceable unmarked copy fails the gate — exactly one attributed failure."""
    store = model_store(weight_gb="9.99GB")
    store["models"][0]["engines"] = [
        {"engine": "llama.cpp", "tps": "72", "hardware": "RTX 3060", "quant": "Q4_K_M",
         "date": "2026-10-05", "source_post": SP1, "weight_gb": "5GB"}]
    td, raw = raw_with()
    hard, _ = flags_of(store, raw)
    check("a copy matching no row and no capture is a hard flag",
          len(hard) == 1 and hard[0][:2] == ("m1", "weight_gb") and hard[0][2] == "9.99GB", hard)
    problems, _ = gate_failures(store, raw)
    check("the gate fails the data stage naming model, field and value",
          len(problems) == 1 and "m1" in problems[0] and "weight_gb" in problems[0]
          and "9.99GB" in problems[0], problems)
    td.cleanup()


def test_est_marker_passes():
    """Scenario: an (est)-marked copy is attributed, not flagged (rule 2), while the SAME
    unmarked value is still flagged."""
    store = model_store(weight_gb="48GB (80B-A3B file) (est)")
    td, raw = raw_with()
    hard, _ = flags_of(store, raw)
    check("a declared estimate is never a drift flag", not hard, hard)
    check("and it is counted as a declared estimate",
          V.model_level_declared_estimates(store) == 1,
          V.model_level_declared_estimates(store))
    store2 = model_store(weight_gb="48GB (80B-A3B file)")
    hard2, _ = flags_of(store2, raw)
    check("the same unmarked value stays flagged (the marker is the only exemption)",
          len(hard2) == 1, hard2)
    td.cleanup()


def test_prose_field_report_only():
    """Scenario: engine_min_version copies are report-only — an unsupported model-level
    `engine_min_version` adds NO hard flag and NO data-stage failure, only a report line."""
    store = model_store(engine_min_version="llama.cpp with MTP=3")
    td, raw = raw_with()
    hard, prose = flags_of(store, raw)
    check("an unsupported engine_min_version copy is a prose flag, not a hard flag",
          not hard and len(prose) == 1 and prose[0][1] == "engine_min_version",
          (hard, prose))
    problems, out = gate_failures(store, raw)
    check("the gate stays green and reports the prose residue",
          not problems and "report" in out, (problems, out))
    td.cleanup()


def test_shipped_store_has_no_untraceable_hard_copy():
    """Issue #934 Done-when: the shipped store's residue is pinned at ZERO — every model-level
    HARD footprint field matches a row/capture or carries (est). This is the gate that blocks
    the 72-field drift from returning."""
    import copy as _copy
    import update_trending as UT
    store, raw = UT.load_store(), ROOT / "data" / "raw"
    hard, _prose = flags_of(store, raw)
    detail = "\n".join(f"    {mid} {f} {v!r}" for mid, f, v in hard)
    check(f"the shipped store carries 0 untraceable model-level hard copies{chr(10) + detail if detail else ''}",
          hard == [], detail)
    # The gate is LIVE: planting an untraceable copy into a copy of the REAL store flags exactly it.
    mutated = _copy.deepcopy(store)
    mutated["models"][0]["weight_gb"] = "987.6GB"
    hard2, _ = flags_of(mutated, raw)
    check("a planted untraceable copy into the shipped store is flagged exactly once",
          len(hard2) == 1 and hard2[0][0] == str(mutated["models"][0]["id"])
          and hard2[0][1] == "weight_gb" and hard2[0][2] == "987.6GB",
          hard2[:3])





def main() -> int:
    print("== model footprint copy traces to captures (issue #934) ==")
    test_row_match_passes()
    test_capture_match_passes()
    test_ksuffix_expansion_passes()
    test_untraceable_copy_fails()
    test_est_marker_passes()
    test_prose_field_report_only()
    test_shipped_store_has_no_untraceable_hard_copy()
    print(f"== {_PASS} passed, {_FAIL} failed ==")
    return 1 if _FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
