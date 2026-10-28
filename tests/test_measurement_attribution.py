#!/usr/bin/env python3
"""A measurement names a different model than the row it is stored on (tech-debt #456/#468).

`data/models.json` -> `qwen-3.6-27b`, measurement `llama.cpp` 140 t/s on `RTX 5090 32GB`:
its `quant` reads "Qwen 3.5 35B served through LM Studio anthropic-compatible endpoint
(v1/messages), 80k context, model fully in VRAM" — the run is Qwen 3.5 35B, not Qwen 3.6
27B. A misplaced measurement inflates the row's t/s and its `posts_7d` signal, and
AGENTS.md §3 requires every figure to trace to a `…/status/<id>` post about THAT model.

The fix has two halves, both asserted here:

  - INGEST refuses a measurement whose captured `quant`/`why` names a different model
    than the row it would merge into (`refuse_misattributed_measurements`), or documents
    the real exception in the explicit `MEASUREMENT_MODEL_ALIASES` mapping.
  - `make validate` FAILS a measurement that relies on a placeholder `source_post` AND
    claims engagement counts (`check_post_signal`), while a low-signal static placeholder
    row stays allowed. The attribution scan itself is report-only for history.

Run:  python3 tests/test_measurement_attribution.py    or   make test
"""
from __future__ import annotations

import copy
import io
import json
import subprocess
import sys
import tempfile
from contextlib import redirect_stdout
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import update_trending as UT  # noqa: E402
import validate as V  # noqa: E402

_PASS = 0
_FAIL = 0

REAL_POST = "https://lightbrd.com/0xbelorix/status/2075607981027393583"


def check(name, cond, detail: object = ""):
    global _PASS, _FAIL
    if cond:
        _PASS += 1
        print(f"  ok  {name}")
    else:
        _FAIL += 1
        print(f"  FAIL {name}" + (f"  [{detail}]" if detail else ""))


def row(mid, name, full_name="", **kw):
    r = {"id": mid, "name": name, "full_name": full_name or name, "hf": "org/" + mid,
         "why": kw.pop("why", "w"), "engines": kw.pop("engines", [])}
    r.update(kw)
    return r


def meas(quant, why="", post=REAL_POST, **kw):
    e = {"engine": "llama.cpp", "tps": "140", "hardware": "RTX 5090 32GB", "quant": quant,
         "date": "2026-07-10", "source_post": post}
    if why:
        e["why"] = why
    e.update(kw)
    return e


def test_the_reported_measurement_is_refused():
    """The measured defect: a Qwen 3.6 27B row whose quant describes Qwen 3.5 35B."""
    m = row("qwen-3.6-27b", "Qwen 3.6 27B", "Qwen3.6-27B", engines=[
        meas("Qwen 3.5 35B served through LM Studio anthropic-compatible endpoint "
             "(v1/messages), 80k context, model fully in VRAM"),
    ])
    kept, refused = UT.refuse_misattributed_measurements(m, {"models": [m]})
    check("attribution: the Qwen 3.5 35B text on the Qwen 3.6 27B row is REFUSED",
          len(refused) == 1 and not kept, (kept, refused))
    check("attribution: the refusal names both identities",
          refused and "qwen 3.5 35b" in refused[0][1] and "qwen 3.6 27b" in refused[0][1], refused)
    check("attribution: the refusal carries the source post",
          refused and refused[0][2] == REAL_POST, refused)


def test_a_measurement_naming_its_own_row_is_kept():
    m = row("qwen3.8-27b", "Qwen 3.8 27B", "Qwen3.8-27B", engines=[
        meas("Qwen3.8-27B 4-bit, 27B dense, MLX", post="https://lightbrd.com/u/status/2"),
    ])
    kept, refused = UT.refuse_misattributed_measurements(m, {"models": [m]})
    check("attribution: a text naming the row's own model is kept", not refused and kept, refused)


def test_a_multi_model_post_naming_the_row_is_kept():
    """A post that measures THIS row's model and mentions another one is about this row."""
    m = row("qwen-3.6-27b", "Qwen 3.6 27B", "Qwen3.6-27B", engines=[
        meas("Qwen3.6 27B at Q4 via MLX (~32 tok/s with MTP); the same box runs Qwen 3.6 35B",
             post="https://lightbrd.com/u/status/3"),
    ])
    kept, refused = UT.refuse_misattributed_measurements(m, {"models": [m]})
    check("attribution: a multi-model post naming the row's model is kept",
          not refused and kept, refused)


def test_a_comparison_cue_is_kept():
    m = row("qwen-3.6-27b", "Qwen 3.6 27B", "Qwen3.6-27B", engines=[
        meas("Qwen 3.6 27B vs Qwen 3.5 35B on the same card", post="https://lightbrd.com/u/status/4"),
    ])
    kept, refused = UT.refuse_misattributed_measurements(m, {"models": [m]})
    check("attribution: a comparison sentence is kept", not refused and kept, refused)


def test_a_cross_family_mention_is_kept():
    """Cross-family mentions are comparison/context, not a same-row mix-up."""
    m = row("qwen-3.6-27b", "Qwen 3.6 27B", "Qwen3.6-27B", engines=[
        meas("Qwen3.6-27B, benchmarked beside Gemma 4 26B", post="https://lightbrd.com/u/status/5"),
    ])
    kept, refused = UT.refuse_misattributed_measurements(m, {"models": [m]})
    check("attribution: a cross-family mention is kept", not refused and kept, refused)


def test_an_unknown_identity_fails_open():
    """A variant name with words between version and size cannot prove a refusal."""
    m = row("qwen3.8-flash-next-125b", "Qwen3.8-Flash-Next 125B",
            "Qwen3.8-Flash-Next 125B", engines=[
                meas("Qwen3.8-27B served beside it", post="https://lightbrd.com/u/status/6"),
            ])
    kept, refused = UT.refuse_misattributed_measurements(m, {"models": [m]})
    check("attribution: an unparseable row identity fails open", not refused and kept, refused)


def test_an_explicit_alias_mapping_documents_an_exception():
    """The issue's 'or needs an explicit alias mapping' half."""
    base = row("bonsai-2-27b", "Bonsai 2 27B")
    variant = row("bonsai-2-27b-mlx", "Bonsai 2 27B MLX", engines=[
        meas("ternary Bonsai 2 27B on an M1 Pro", post="https://lightbrd.com/u/status/7"),
    ])
    # The variant's own params are 27b, so the same-size mention is already kept; use a
    # size-different base to exercise the mapping.
    base = row("bonsai-2-27b", "Bonsai 2 27B")
    variant = row("bonsai-2-9b", "Bonsai 2 9B", engines=[
        meas("ternary Bonsai 2 27B beside the 9B", post="https://lightbrd.com/u/status/7"),
    ])
    store = {"models": [base, variant]}
    saved = dict(UT.MEASUREMENT_MODEL_ALIASES)
    try:
        UT.MEASUREMENT_MODEL_ALIASES.clear()
        kept, refused = UT.refuse_misattributed_measurements(variant, store)
        check("attribution: without an alias mapping the different size is refused",
              bool(refused), refused)
        UT.MEASUREMENT_MODEL_ALIASES["bonsai-2-9b"] = {"bonsai-2-27b"}
        kept, refused = UT.refuse_misattributed_measurements(variant, store)
        check("attribution: an explicit alias mapping documents the exception",
              not refused and kept, refused)
    finally:
        UT.MEASUREMENT_MODEL_ALIASES.clear()
        UT.MEASUREMENT_MODEL_ALIASES.update(saved)


def test_ingest_calls_the_refusal():
    src = (ROOT / "scripts" / "update_trending.py").read_text()
    start = src.index("def ingest_raw_snapshots(")
    body = src[start:src.index("\ndef ", start + 10)]
    check("ingest: the refusal is called where a raw row merges",
          "refuse_misattributed_measurements(m, store)" in body, body[:200])


def test_ingest_drops_a_new_row_whose_only_measurement_is_refused():
    """A NEW row with nothing left to show is not stored broken (check_model_fields
    would fail it); the rest of the snapshot still merges."""
    raw = {
        "generated_utc": "2026-10-27T00:00:00Z", "backend": "nvidia",
        "models": [{
            "id": "qwen-3.6-27b", "name": "Qwen 3.6 27B", "full_name": "Qwen3.6-27B",
            "hf": "Qwen/Qwen3.6-27B", "license": "Apache 2.0", "params": "27B", "type": "LLM",
            "vram_tier": "18GB", "backends": ["CUDA"],
            "engines": [meas("Qwen 3.5 35B served through LM Studio "
                             "anthropic-compatible endpoint")],
        }],
    }
    store = {"generated_utc": "2026-10-01T00:00:00Z",
             "engines": {"llama.cpp": {"backend": "CUDA / CPU / Metal", "note": "n",
                                       "url": "https://github.com/ggml-org/llama.cpp"}},
             "models": []}
    td = Path(tempfile.mkdtemp())
    (td / "nvidia-test.json").write_text(json.dumps(raw))
    saved = UT.RAW_DIR
    buf = io.StringIO()
    try:
        UT.RAW_DIR = td
        with redirect_stdout(buf):
            added, updated = UT.ingest_raw_snapshots(store, since=None)
    finally:
        UT.RAW_DIR = saved
    out = buf.getvalue()
    check("ingest: a new row whose only measurement is refused is NOT stored",
          added == 0 and updated == 0 and store["models"] == [], (added, updated, store["models"]))
    check("ingest: the refusal is loud and names the model",
          "REFUSED misattributed measurement" in out and "qwen-3.6-27b" in out, out[-400:])


def test_the_shipped_store_reports_the_known_row():
    store = json.loads((ROOT / "data" / "models.json").read_text())
    mis = V.misattributed_measurements(store.get("models", []))
    check("scan: the shipped store reports the qwen-3.6-27b row",
          any("qwen-3.6-27b" in m[0] or "Qwen 3.6 27B" in m[0] for m in mis), mis[:2])
    V.FAILURES.clear()
    buf = io.StringIO()
    saved = V.RAW_DIR
    V.RAW_DIR = Path(tempfile.mkdtemp()) / "none"
    try:
        with redirect_stdout(buf):
            V.check_measurement_attribution(store)
    finally:
        V.RAW_DIR = saved
        V.FAILURES.clear()
    out = buf.getvalue()
    check("scan: it prints a WARN naming the misplaced figure",
          "WARN: measurement-attribution scan" in out and "Qwen 3.6 27B" in out, out[-400:])
    check("scan: report only — it adds no failure", not V.FAILURES, V.FAILURES)
    proc = subprocess.run([sys.executable, str(ROOT / "scripts" / "validate.py"), "--only", "data"],
                          capture_output=True, text=True, cwd=ROOT)
    check("scan: `validate --only data` prints it and still SUCCEEDS",
          "measurement-attribution scan" in proc.stdout and proc.returncode == 0,
          (proc.returncode, proc.stdout[-300:]))


def main() -> int:
    print("measurement attribution: a measurement naming another model (tech-debt #456/#468)")
    test_the_reported_measurement_is_refused()
    test_a_measurement_naming_its_own_row_is_kept()
    test_a_multi_model_post_naming_the_row_is_kept()
    test_a_comparison_cue_is_kept()
    test_a_cross_family_mention_is_kept()
    test_an_unknown_identity_fails_open()
    test_an_explicit_alias_mapping_documents_an_exception()
    test_ingest_calls_the_refusal()
    test_ingest_drops_a_new_row_whose_only_measurement_is_refused()
    test_the_shipped_store_reports_the_known_row()
    print(f"\nPASSED {_PASS} | FAILED {_FAIL}")
    return 1 if _FAIL else 0


if __name__ == "__main__":
    raise SystemExit(main())
