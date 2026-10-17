#!/usr/bin/env python3
"""A t/s figure can state the footprint of ITS OWN run (issue #337).

One model's quants fit different cards, so the card-fit view needs the footprint
on the MEASUREMENT that produced a t/s figure — not only on the model row. The
contracts now declare optional `weight_gb` / `context_tokens` / `system_ram_min` /
`storage_offload` on a measurement item.

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
        "supported_engines": ["llama.cpp"], "why": "ternary", "last_seen": "2026-10-17",
        "formats": [{"name": "GGUF", "hf": "prism-ml/Ternary-Bonsai-2-27B-gguf"}],
        "engagement": {"likes": 10, "comments": 2, "views": 1000},
        "engines": [{
            "engine": "llama.cpp", "tps": "146", "hardware": "RTX 5090 32GB",
            "quant": "PTQ1_0 ternary", "date": "2026-10-17",
            "source_post": "https://lightbrd.com/a/status/1",
            "weight_gb": "5.95GB PTQ1_0", "context_tokens": "262144",
            "system_ram_min": "16GB", "storage_offload": "640GB NVMe",
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


def run_ingest(tmp: str):
    """Real ingest of a real raw file under a temp data tree; returns (store, model, measurement)."""
    os.environ["TRENDING_DATA_DIR"] = tmp
    (Path(tmp) / "raw").mkdir(parents=True, exist_ok=True)
    (Path(tmp) / "raw" / "nvidia-20261017T090000Z.json").write_text(json.dumps(RAW))
    import update_trending as ut  # imported AFTER the env seam, like the make targets
    store = json.loads(json.dumps(STORE))
    ut.ingest_raw_snapshots(store, since=None)
    m = store["models"][0]
    return ut, store, m, m["engines"][0]


def main() -> int:
    print("measurement footprint: a figure can state its own run (issue #337)")
    with tempfile.TemporaryDirectory() as tmp:
        ut, store, m, e = run_ingest(tmp)
        print("-- test_a_measurement_footprint_survives_ingest")
        for k, want in (("weight_gb", "5.95GB PTQ1_0"), ("context_tokens", "262144"),
                        ("system_ram_min", "16GB"), ("storage_offload", "640GB NVMe")):
            check(f"ingest: the measurement keeps its own {k}", e.get(k) == want, e.get(k))
        check("ingest: the t/s figure itself is unchanged", e.get("tps") == "146", e.get("tps"))
        check("ingest: nothing was pruned from the measurement",
              set(e) >= {"engine", "tps", "hardware", "quant", "date", "source_post",
                         "weight_gb", "context_tokens", "system_ram_min", "storage_offload"}, sorted(e))

        print("-- test_the_store_still_conforms_to_the_contract")
        V.FAILURES.clear()
        V.check_schema(store)
        check("contract: the real check_schema accepts a store carrying the new keys",
              V.FAILURES == [], V.FAILURES[:2])
        V.FAILURES.clear()

        print("-- test_the_footprint_drives_the_card_fit")
        check("fit: the run proves the 32 GB card it ran on", ut.fits_tier(m, e, 32) == "ran-on")
        check("fit: and its stated 5.95 GB weights make 8 GB 'weights-only', not 'ran-on'",
              ut.fits_tier(m, e, 8) == "weights-only", ut.fits_tier(m, e, 8))
        check("fit: a measured footprint beats the model-level field",
              ut.weights_gb(m, e) == (5.95, "stated"), ut.weights_gb(m, e))

    print("-- test_the_contract_declares_them_optional")
    for name in ("model_contract.json", "search_contract.json"):
        c = json.loads((ROOT / "data" / name).read_text())
        item = c["properties"]["models"]["items"]["properties"]["engines"]["items"]
        for k in ("weight_gb", "context_tokens", "system_ram_min", "storage_offload"):
            check(f"{name}: measurement declares optional {k}", k in item["properties"], sorted(item["properties"]))
            check(f"{name}: {k} is NOT required (additive, rule 3b)", k not in item.get("required", []),
                  item.get("required"))
    print(f"\n{_PASS} passed, {_FAIL} failed")
    return 1 if _FAIL else 0


if __name__ == "__main__":
    raise SystemExit(main())
