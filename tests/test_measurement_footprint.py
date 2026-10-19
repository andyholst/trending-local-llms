#!/usr/bin/env python3
"""A t/s figure can state the footprint of ITS OWN run (issue #337).

One model's quants fit different cards, so the card-fit view needs the footprint
on the MEASUREMENT that produced a t/s figure — not only on the model row. The
contracts now declare optional `weight_gb` / `context_tokens` / `system_ram_min` /
`storage_offload` / `engine_min_version` on a measurement item.

`engine_min_version` is a requirement dimension too, and the only one whose home
is the MEASUREMENT: a minimum engine build (or the flags a run needed) is a
property of the engine that produced the figure, so a raw snapshot that records
it per measurement is right — the store contract used to accept it on the model
row alone and `additionalProperties: false` then refused the per-measurement one,
reddening a whole refresh PR (run 39124432576).

The contract files being right is not enough: the measurement item is
`additionalProperties: false`, so a key the ingest path does not carry through is
pruned SILENTLY and the figure never reaches the store (rule 3b). This test drives
the REAL path against a real temp data tree (`TRENDING_DATA_DIR`, the seam the make
targets use), through the REAL contract — no stub of the logic under test (rule 6m).

  - test_a_measurement_footprint_survives_ingest   raw -> store, keys intact
  - test_the_store_still_conforms_to_the_contract  the real check_schema passes
  - test_the_footprint_drives_the_card_fit         the real fit reads it
  - test_the_contract_declares_them_optional       additive, never required

Run:  python3 tests/test_measurement_footprint.py   or   make test
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

# Imported BEFORE the data-dir seam is switched below: the validator's own paths
# (its contract files) must stay the real ones, only the INGEST seam moves.
import validate as V  # noqa: E402

_PASS = 0
_FAIL = 0


def check(name, cond, detail: object = ""):
    global _PASS, _FAIL
    if cond:
        _PASS += 1
        print(f"  ok  {name}")
    else:
        _FAIL += 1
        print(f"  FAIL {name}" + (f"  [{detail}]" if detail else ""))


# The shape a search leg writes: one raw snapshot for one backend, with the
# footprint of the run that produced each figure recorded ON the measurement.
RAW = {
    "backend": "nvidia",
    "generated_utc": "2026-10-17T09:00:00Z",
    "models": [{
        "id": "bonsai-2-27b", "name": "Bonsai 2 27B", "full_name": "Ternary-Bonsai-2-27B",
        "type": "LLM", "license": "Apache 2.0", "params": "27B", "hf": "prism-ml/Ternary-Bonsai-2-27B-gguf",
        "vram_tier": "12GB", "vram_min": "6GB", "backends": ["CUDA"],
        "why": "ternary", "last_seen": "2026-10-17",
        "formats": [{"name": "GGUF", "hf": "prism-ml/Ternary-Bonsai-2-27B-gguf"}],
        "engagement": {"likes": 10, "comments": 2, "views": 1000},
        "engines": [{
            "engine": "llama.cpp", "tps": "146", "hardware": "RTX 5090 32GB",
            "quant": "PTQ1_0 ternary", "date": "2026-10-17",
            "source_post": "https://lightbrd.com/a/status/1",
            "weight_gb": "5.95GB PTQ1_0", "context_tokens": "262144",
            "system_ram_min": "16GB", "storage_offload": "640GB NVMe",
            "engine_min_version": "b6xxx, --n-gpu-layers 99",
        }],
    }],
}

STORE = {
    "generated_utc": "2026-10-16T00:00:00Z",
    "note": "fixture",
    "engines": {"llama.cpp": {"backend": "CUDA / CPU / Metal", "note": "n",
                              "url": "https://github.com/ggml-org/llama.cpp"}},
    "models": [],
}


def _write_raw(tmp: str) -> Path:
    """Write the shape ONE search leg produces into `tmp/raw` and return the dir."""
    raw_dir = Path(tmp) / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    (raw_dir / "nvidia-20261017T090000Z.json").write_text(json.dumps(RAW))
    return raw_dir


def search_contract_failures(raw_dir: Path) -> list:
    """Run the REAL `check_search_contract` against the REAL search contract over
    `raw_dir` and return what it reported — the check the refresh PR failed on, not
    a stub of it (rule 6m)."""
    V.RAW_DIR = raw_dir
    V.FAILURES.clear()
    V.check_search_contract()
    failures = list(V.FAILURES)
    V.FAILURES.clear()
    return failures


def run_ingest(tmp: str):
    """Real ingest of a real raw file under a temp data tree; returns (store, model, measurement)."""
    os.environ["TRENDING_DATA_DIR"] = tmp
    _write_raw(tmp)
    import update_trending as ut  # imported AFTER the env seam, like the make targets
    store = json.loads(json.dumps(STORE))
    ut.ingest_raw_snapshots(store, since=None)
    m = store["models"][0]
    return ut, store, m, m["engines"][0]


# The merge must not lose a dimension a lower-engagement capture stated, and must
# not drop one the store already held when a higher-engagement capture wins the
# group as representative. Both are real `…/status/<id>` posts: the values are
# copied from data/raw/nvidia-20261019-003834.json (qwen3.8-27b's llama.cpp run
# states 14.6GB IQ4_XS / 64000 context / 16GB RAM that the store measurement lost).
MERGE_STORE = {
    "generated_utc": "2026-10-15T00:00:00Z",
    "note": "fixture",
    "engines": {"llama.cpp": {"backend": "CUDA / CPU / Metal", "note": "n",
                              "url": "https://github.com/ggml-org/llama.cpp"}},
    "models": [
        {"id": "store-wins", "name": "Store Wins", "full_name": "Store Wins", "type": "LLM",
         "license": "Apache 2.0", "params": "27B", "hf": "a/store-wins",
         "vram_tier": "8GB", "vram_min": "8GB", "backends": ["CUDA"],
         "supported_engines": ["llama.cpp"], "why": "w", "last_seen": "2026-10-15",
         "formats": [{"name": "GGUF", "hf": "a/store-wins"}],
         "engagement": {"likes": 0, "comments": 0, "views": 0, "last_7d_likes": 0},
         "engines": [{"engine": "llama.cpp", "tps": "5", "hardware": "RTX 4060 8GB laptop",
                      "quant": "UD-Q3_K_XL", "date": "2026-09-16",
                      "source_post": "https://lightbrd.com/a/status/1",
                      "likes": 131, "comments": 10, "reshares": 15, "views": 15067}]},
        {"id": "incoming-wins", "name": "Incoming Wins", "full_name": "Incoming Wins",
         "type": "LLM", "license": "Apache 2.0", "params": "27B", "hf": "a/incoming-wins",
         "vram_tier": "24GB", "vram_min": "24GB", "backends": ["CUDA"],
         "supported_engines": ["llama.cpp"], "why": "w", "last_seen": "2026-10-15",
         "formats": [{"name": "GGUF", "hf": "a/incoming-wins"}],
         "engagement": {"likes": 0, "comments": 0, "views": 0, "last_7d_likes": 0},
         "engines": [{"engine": "llama.cpp", "tps": "45", "hardware": "RTX 5090 32GB",
                      "quant": "Q4_K_M", "date": "2026-10-01",
                      "source_post": "https://lightbrd.com/a/status/2",
                      "likes": 1, "comments": 0, "storage_offload": "640GB NVMe"}]},
    ],
}
MERGE_RAW = {
    "backend": "nvidia", "generated_utc": "2026-10-17T09:00:00Z",
    "models": [
        {"id": "store-wins", "name": "Store Wins", "engines": [
            {"engine": "llama.cpp", "tps": "5", "hardware": "RTX 4060 8GB laptop",
             "quant": "Unsloth IQ4_XS 14.6GB, 64K context", "date": "2026-09-16",
             "source_post": "https://lightbrd.com/a/status/1",
             "likes": 10, "comments": 0, "weight_gb": "14.6GB IQ4_XS",
             "context_tokens": "64000", "system_ram_min": "16GB"}]},
        {"id": "incoming-wins", "name": "Incoming Wins", "engines": [
            {"engine": "llama.cpp", "tps": "45", "hardware": "RTX 5090 32GB",
             "quant": "Q4_K_M", "date": "2026-10-01",
             "source_post": "https://lightbrd.com/a/status/2",
             "likes": 500, "comments": 10}]},
    ],
}


def merge_ingest(tmp: str):
    """Drive the REAL ingest of MERGE_RAW into a store that already holds both
    measurements. A fresh module import per test, because the data-dir seam is
    bound at import time (the same seam the make targets use)."""
    import importlib
    os.environ["TRENDING_DATA_DIR"] = tmp
    raw_dir = Path(tmp) / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    (raw_dir / "nvidia-20261017T090000Z.json").write_text(json.dumps(MERGE_RAW))
    import update_trending as ut
    ut = importlib.reload(ut)
    store = json.loads(json.dumps(MERGE_STORE))
    ut.ingest_raw_snapshots(store, since=None)
    return {m["id"]: m for m in store["models"]}


def test_a_dimension_survives_the_merge_onto_an_existing_measurement():
    """The store row wins the group as representative; the incoming row is the only
    one stating the run's footprint — the merge must carry it across."""
    with tempfile.TemporaryDirectory() as tmp:
        models = merge_ingest(tmp)
        e = models["store-wins"]["engines"][0]
        check("merge: the representative keeps the stated weight_gb", e.get("weight_gb") == "14.6GB IQ4_XS", e.get("weight_gb"))
        check("merge: the representative keeps the stated context_tokens", e.get("context_tokens") == "64000", e.get("context_tokens"))
        check("merge: the representative keeps the stated system_ram_min", e.get("system_ram_min") == "16GB", e.get("system_ram_min"))
        check("merge: the t/s figure is not altered by the fill", e.get("tps") == "5", e.get("tps"))


def test_the_merge_never_drops_a_stored_dimension():
    """The incoming row wins the group as representative and states no offload; the
    stored value must survive (additive only, AGENTS.md rule 3b)."""
    with tempfile.TemporaryDirectory() as tmp:
        models = merge_ingest(tmp)
        e = models["incoming-wins"]["engines"][0]
        check("merge: a higher-engagement incoming row does not drop the stored storage_offload",
              e.get("storage_offload") == "640GB NVMe", e.get("storage_offload"))
        check("merge: the representative is the incoming row (t/s unchanged)",
              e.get("tps") == "45", e.get("tps"))


def main() -> int:
    print("measurement footprint: a figure can state its own run (issue #337)")
    with tempfile.TemporaryDirectory() as tmp:
        ut, store, m, e = run_ingest(tmp)
        print("-- test_a_measurement_footprint_survives_ingest")
        for k, want in (("weight_gb", "5.95GB PTQ1_0"), ("context_tokens", "262144"),
                        ("system_ram_min", "16GB"), ("storage_offload", "640GB NVMe"),
                        ("engine_min_version", "b6xxx, --n-gpu-layers 99")):
            check(f"ingest: the measurement keeps its own {k}", e.get(k) == want, e.get(k))
        check("ingest: the t/s figure itself is unchanged", e.get("tps") == "146", e.get("tps"))
        check("ingest: nothing was pruned from the measurement",
              set(e) >= {"engine", "tps", "hardware", "quant", "date", "source_post",
                         "weight_gb", "context_tokens", "system_ram_min", "storage_offload",
                         "engine_min_version"}, sorted(e))

        print("-- test_the_store_still_conforms_to_the_contract")
        V.FAILURES.clear()
        V.check_schema(store)
        check("contract: the real check_schema accepts a store carrying the new keys",
              V.FAILURES == [], V.FAILURES[:2])
        V.FAILURES.clear()

        print("-- test_the_search_contract_accepts_a_per_measurement_engine_min_version")
        # The regression this fix exists for: a search leg wrote the minimum engine
        # build ON THE MEASUREMENT and the search contract refused it
        # (`Additional properties are not allowed ('engine_min_version' was
        # unexpected) (at ['models', 0, 'engines', 1])`), so a whole refresh PR went
        # red and the loop burned its budget repairing nothing (run 39124432576).
        # The REAL check, against the REAL contract.
        failures = search_contract_failures(Path(tmp) / "raw")
        check("search contract: a per-measurement engine_min_version is accepted",
              failures == [], failures[:2])

        print("-- test_the_footprint_drives_the_card_fit")
        check("fit: the run proves the 32 GB card it ran on", ut.fits_tier(m, e, 32) == "ran-on")
        check("fit: and its stated 5.95 GB weights make 8 GB 'weights-only', not 'ran-on'",
              ut.fits_tier(m, e, 8) == "weights-only", ut.fits_tier(m, e, 8))
        check("fit: a measured footprint beats the model-level field",
              ut.weights_gb(m, e) == (5.95, "stated"), ut.weights_gb(m, e))

    test_a_dimension_survives_the_merge_onto_an_existing_measurement()
    test_the_merge_never_drops_a_stored_dimension()

    print("-- test_the_contract_declares_them_optional")
    for name in ("model_contract.json", "search_contract.json"):
        c = json.loads((ROOT / "data" / name).read_text())
        item = c["properties"]["models"]["items"]["properties"]["engines"]["items"]
        for k in ("weight_gb", "context_tokens", "system_ram_min", "storage_offload",
                  "engine_min_version"):
            check(f"{name}: measurement declares optional {k}", k in item["properties"], sorted(item["properties"]))
            check(f"{name}: {k} is NOT required (additive, rule 3b)", k not in item.get("required", []),
                  item.get("required"))
    print(f"\n{_PASS} passed, {_FAIL} failed")
    return 1 if _FAIL else 0


if __name__ == "__main__":
    raise SystemExit(main())
