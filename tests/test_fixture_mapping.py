#!/usr/bin/env python3
"""Fixture-driven test: raw search JSON -> models.json, verified against the
model contract's mandatory + optional fields.

Loads tests/fixtures/raw_search.json (a raw per-backend search snapshot with
two models — one existing, one brand-new missing several derived fields),
runs the REAL ingest_raw_snapshots + normalize_model path, and asserts:

  1. The resulting store EXACTLY matches tests/fixtures/expected_models.json
     (the golden expected output).
  2. Every MANDATORY field from data/model_contract.json is present and
     non-empty on every model.
  3. Every OPTIONAL field is present (filled by normalization) where the
     contract declares it.
  4. The store validates against data/model_contract.json (JSON Schema).

This is the "expected test data is true" guarantee: the fixture encodes the
raw->models.json mapping contract, so a change to the mapping logic that
breaks a field fill fails here.

Run:  python3 tests/test_fixture_mapping.py   or   make test
"""
from __future__ import annotations

import json
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import update_trending as UT  # noqa: E402

FIXTURES = ROOT / "tests" / "fixtures"
RAW_FIXTURE = FIXTURES / "raw_search.json"
EXPECTED_FIXTURE = FIXTURES / "expected_models.json"
RAW_DUP_FIXTURE = FIXTURES / "raw_duplicates.json"
EXPECTED_DUP_FIXTURE = FIXTURES / "expected_duplicates.json"
CONTRACT = ROOT / "data" / "model_contract.json"

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
    """The pre-ingest store: one existing model (qwen3-14b) fully populated."""
    return {
        "engines": {"llama.cpp": {"backend": "CUDA", "note": "x", "url": "https://github.com/ggml-org/llama.cpp"}},
        "models": [{
            "id": "qwen3-14b", "name": "Qwen3 14B", "full_name": "Qwen3-14B", "type": "LLM",
            "formats": [{"name": "GGUF", "hf": "Qwen/Qwen3-14B"}], "license": "Apache 2.0",
            "params": "14B", "hf": "Qwen/Qwen3-14B", "vram_tier": "9GB", "vram_min": "8GB",
            "backends": ["CUDA"], "supported_engines": ["llama.cpp"],
            "engines": [{"engine": "llama.cpp", "tps": "50", "hardware": "RTX 3060", "quant": "Q4",
                         "date": "2026-09-28", "source_post": "https://lightbrd.com/1"}],
            "why": "w", "engagement": {"likes": 1, "comments": 0, "views": 1, "last_7d_likes": 1},
            "last_seen": "2026-09-28",
        }],
    }


def run_ingest(store: dict) -> dict:
    """Point UT.RAW_DIR at a temp dir holding the raw fixture, ingest, return store."""
    raw = json.loads(RAW_FIXTURE.read_text())
    with tempfile.TemporaryDirectory() as td:
        rdir = Path(td)
        (rdir / "nvidia-1.json").write_text(json.dumps(raw))
        saved = UT.RAW_DIR
        UT.RAW_DIR = rdir
        try:
            UT.ingest_raw_snapshots(store)
        finally:
            UT.RAW_DIR = saved
    UT.sort_models(store["models"], datetime(2026, 9, 29, tzinfo=timezone.utc))
    return store


def test_output_matches_expected_fixture():
    """The real ingest must produce EXACTLY the golden expected_models.json."""
    store = run_ingest(base_store())
    expected = json.loads(EXPECTED_FIXTURE.read_text())
    check("ingest output matches expected_models.json fixture", store == expected,
          "store != expected (see diff below)")


def test_mandatory_fields_present():
    """Every MANDATORY model field from model_contract.json is present and
    non-empty on every model after ingest."""
    contract = json.loads(CONTRACT.read_text())
    required = contract["properties"]["models"]["items"]["required"]
    store = run_ingest(base_store())
    for m in store["models"]:
        for field in required:
            val = m.get(field)
            check(f"{m['id']}: mandatory field '{field}' present+non-empty",
                  val is not None and val != "" and val != [], repr(val))
        # engine mandatory fields
        for e in m.get("engines", []):
            for f in contract["properties"]["models"]["items"]["properties"]["engines"]["items"]["required"]:
                check(f"{m['id']}/{e.get('engine')}: engine mandatory '{f}' present",
                      e.get(f) is not None and e.get(f) != "", repr(e.get(f)))
        # engagement mandatory fields
        for f in contract["properties"]["models"]["items"]["properties"]["engagement"]["required"]:
            check(f"{m['id']}: engagement mandatory '{f}' present",
                  m.get("engagement", {}).get(f) is not None, repr(m.get("engagement", {}).get(f)))


def test_optional_fields_filled():
    """OPTIONAL fields declared by the contract are filled by normalization
    (not left missing) — e.g. hf, engine hardware/quant, seen_posts."""
    contract = json.loads(CONTRACT.read_text())
    items = contract["properties"]["models"]["items"]
    required = items["required"]
    optional = [k for k in items["properties"] if k not in required]
    store = run_ingest(base_store())
    for m in store["models"]:
        for field in optional:
            check(f"{m['id']}: optional field '{field}' present after ingest",
                  field in m, f"missing {field}")
    # engine optional fields
    eng_opt = [k for k in items["properties"]["engines"]["items"]["properties"]
               if k not in items["properties"]["engines"]["items"]["required"]]
    for m in store["models"]:
        for e in m.get("engines", []):
            for f in eng_opt:
                check(f"{m['id']}/{e.get('engine')}: engine optional '{f}' present",
                      f in e, f"missing {f}")


def test_store_validates_against_contract():
    """The ingested store must pass JSON Schema validation against
    model_contract.json (the machine-checkable contract)."""
    import jsonschema
    store = run_ingest(base_store())
    schema = json.loads(CONTRACT.read_text())
    try:
        jsonschema.validate(instance=store, schema=schema)
        valid = True
    except jsonschema.ValidationError as e:
        valid = False
        detail = f"{e.message} at {list(e.absolute_path or [])}"
    check("ingested store validates against model_contract.json", valid, detail if not valid else "")


def test_no_duplicate_engine_rows_from_duplicate_posts():
    """The PR #16 regression: the same model+engine+t/s+GPU size reported by two
    different X posts (with slightly different hardware wording) must collapse
    to ONE engine row. Loads raw_duplicates.json (2 models, each with 2
    duplicate FreeToken rows) and asserts the ingested store EXACTLY matches
    expected_duplicates.json (each model has 1 engine row, no duplicates)."""
    raw = json.loads(RAW_DUP_FIXTURE.read_text())
    store = {
        "engines": {"FreeToken": {"backend": "CUDA", "note": "x", "url": "https://github.com/FlashML-org/FreeToken"}},
        "models": [],
    }
    with tempfile.TemporaryDirectory() as td:
        rdir = Path(td)
        (rdir / "nvidia-1.json").write_text(json.dumps(raw))
        saved = UT.RAW_DIR
        UT.RAW_DIR = rdir
        try:
            UT.ingest_raw_snapshots(store)
        finally:
            UT.RAW_DIR = saved
    UT.sort_models(store["models"], datetime(2026, 9, 29, tzinfo=timezone.utc))
    expected = json.loads(EXPECTED_DUP_FIXTURE.read_text())
    check("no-dup: ingest output matches expected_duplicates.json", store == expected,
          "store != expected (duplicates not collapsed)")
    for m in store["models"]:
        check(f"no-dup: {m['id']} has exactly 1 engine row (no duplicate)",
              len(m["engines"]) == 1, f"got {len(m['engines'])} rows")


def main() -> int:
    print("fixture-driven raw -> models.json mapping (mandatory + optional fields)")
    test_output_matches_expected_fixture()
    test_mandatory_fields_present()
    test_optional_fields_filled()
    test_store_validates_against_contract()
    test_no_duplicate_engine_rows_from_duplicate_posts()
    print(f"\nPASSED {_PASS} | FAILED {_FAIL}")
    return 1 if _FAIL else 0


if __name__ == "__main__":
    raise SystemExit(main())
