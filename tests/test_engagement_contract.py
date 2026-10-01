#!/usr/bin/env python3
"""Model-level engagement: raw search snapshot -> ingest -> store contract.

The search contract leaves a model's top-level `engagement` OPEN, but the store
contract (data/model_contract.json) is CLOSED (additionalProperties:false). The
search agent records `reshares` there on every model, so before this fix EVERY
refresh PR went red on:
  schema: Additional properties are not allowed ('reshares' was unexpected)
— a deterministic ingest/contract bug the LLM fix-bot was being asked to repair.

  - test_real_pr50_snapshot_ingests_schema_clean   REAL snapshot from PR #50
  - test_reshares_and_interactions_preserved       declared keys survive ingest
  - test_stray_keys_pruned_and_counters_coerced    undeclared keys dropped
  - test_existing_model_path_also_pruned           update path, not only add
  - test_contract_keys_cover_search_contract       store accepts what search declares

Run:  python3 tests/test_engagement_contract.py   or   make test
"""
from __future__ import annotations

import copy
import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import jsonschema  # noqa: E402
import update_trending as UT  # noqa: E402

FIXTURE = ROOT / "tests" / "fixtures" / "raw_pr50_nvidia_reshares.json"
MODEL_CONTRACT = json.loads((ROOT / "data" / "model_contract.json").read_text())
SEARCH_CONTRACT = json.loads((ROOT / "data" / "search_contract.json").read_text())

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
    """The current store (real engines registry + models), deep-copied."""
    return copy.deepcopy(json.loads((ROOT / "data" / "models.json").read_text()))


def ingest(store: dict, raws: dict[str, dict]) -> dict:
    with tempfile.TemporaryDirectory() as td:
        rdir = Path(td)
        for name, data in raws.items():
            (rdir / name).write_text(json.dumps(data))
        saved = UT.RAW_DIR
        UT.RAW_DIR = rdir
        try:
            UT.ingest_raw_snapshots(store)
        finally:
            UT.RAW_DIR = saved
    return store


def schema_errors(store: dict) -> list[str]:
    v = jsonschema.validators.validator_for(MODEL_CONTRACT)(MODEL_CONTRACT)
    return [f"{list(e.path)}: {e.message}" for e in v.iter_errors(store)]


def raw_model(mid: str, engagement: dict) -> dict:
    return {
        "id": mid, "name": mid, "full_name": mid, "type": "LLM", "license": "MIT",
        "params": "8B", "hf": "org/" + mid, "vram_tier": "8GB", "vram_min": "8GB",
        "backends": ["CUDA"], "last_seen": "2026-10-01",
        "engines": [{"engine": "llama.cpp", "tps": "40", "hardware": "RTX 4090",
                     "date": "2026-10-01", "source_post": "https://lightbrd.com/x/" + mid}],
        "engagement": engagement,
    }


def test_real_pr50_snapshot_ingests_schema_clean():
    raw = json.loads(FIXTURE.read_text())
    has_reshares = [m["id"] for m in raw["models"] if "reshares" in m.get("engagement", {})]
    check("pr50: fixture really carries model-level reshares", len(has_reshares) >= 1, str(has_reshares))
    store = ingest(base_store(), {"nvidia-20261001-223845.json": raw})
    errs = [e for e in schema_errors(store) if "engagement" in e]
    check("pr50: ingested store has no engagement schema errors", not errs, "; ".join(errs[:3]))


def test_reshares_and_interactions_preserved():
    store = ingest(base_store(), {"nvidia-1.json": {
        "backend": "nvidia", "generated_utc": "2026-10-01T00:00:00Z",
        "models": [raw_model("zz-keep", {"likes": 10, "comments": 2, "views": 99,
                                         "reshares": 4, "interactions": 115})]}})
    eng = next(m for m in store["models"] if m["id"] == "zz-keep")["engagement"]
    check("keep: reshares preserved", eng.get("reshares") == 4, json.dumps(eng))
    check("keep: interactions preserved", eng.get("interactions") == 115, json.dumps(eng))
    check("keep: store validates against model_contract", not schema_errors(store),
          "; ".join(schema_errors(store)[:3]))


def test_stray_keys_pruned_and_counters_coerced():
    store = ingest(base_store(), {"nvidia-1.json": {
        "backend": "nvidia", "generated_utc": "2026-10-01T00:00:00Z",
        "models": [raw_model("zz-stray", {"likes": "12", "comments": 1.0, "views": -5,
                                          "quotes": 3, "bookmarks": "n/a"})]}})
    eng = next(m for m in store["models"] if m["id"] == "zz-stray")["engagement"]
    check("prune: undeclared 'quotes' dropped", "quotes" not in eng, json.dumps(eng))
    check("prune: undeclared 'bookmarks' dropped", "bookmarks" not in eng, json.dumps(eng))
    check("coerce: '12' -> 12", eng.get("likes") == 12, json.dumps(eng))
    check("coerce: 1.0 -> 1", eng.get("comments") == 1 and isinstance(eng["comments"], int), json.dumps(eng))
    check("coerce: negative -> 0", eng.get("views") == 0, json.dumps(eng))
    check("prune: store validates against model_contract", not schema_errors(store),
          "; ".join(schema_errors(store)[:3]))


def test_existing_model_path_also_pruned():
    store = base_store()
    target = store["models"][0]
    target["engagement"]["stale_stray"] = 1  # written by older code / a hand edit
    raw = raw_model(target["id"], {"likes": 1})
    raw["name"], raw["hf"] = target["name"], target.get("hf", "")
    ingest(store, {"nvidia-1.json": {"backend": "nvidia",
                                     "generated_utc": "2026-10-01T00:00:00Z", "models": [raw]}})
    eng = next(m for m in store["models"] if m["id"] == target["id"])["engagement"]
    check("update-path: stray key on an existing model pruned", "stale_stray" not in eng, json.dumps(eng)[:200])


def test_contract_keys_cover_search_contract():
    store_keys = set(MODEL_CONTRACT["properties"]["models"]["items"]["properties"]["engagement"]["properties"])
    search_keys = set(SEARCH_CONTRACT["properties"]["models"]["items"]["properties"]["engagement"].get("properties", {}))
    missing = search_keys - store_keys
    check("contracts: every engagement key the search contract declares is storable",
          not missing, str(sorted(missing)))
    check("contracts: ingest reads its allowed keys from model_contract.json",
          UT._engagement_keys() == frozenset(store_keys), str(sorted(UT._engagement_keys())))


def main() -> int:
    print("model-level engagement: raw -> ingest -> store contract")
    test_real_pr50_snapshot_ingests_schema_clean()
    test_reshares_and_interactions_preserved()
    test_stray_keys_pruned_and_counters_coerced()
    test_existing_model_path_also_pruned()
    test_contract_keys_cover_search_contract()
    print(f"\nPASSED {_PASS} | FAILED {_FAIL}")
    return 1 if _FAIL else 0


if __name__ == "__main__":
    raise SystemExit(main())
