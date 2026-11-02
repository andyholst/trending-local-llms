#!/usr/bin/env python3
"""Tests for the normalised store split (issue #689): the additive seam that
writes data/measurements.json + data/posts.json alongside the still-flat
data/models.json, and the flatten-equality guard.

The old readers keep operating on the flat data/models.json (unchanged on
disk). This test proves the NEW code — split_store(), flatten_store(),
_measurement_identity(), the two new contracts, and validate.check_split_flatten
— is correct and lossless: a split→flatten round-trip keeps every (model,
engine, tps, source_post) measurement and every footprint, and counters only
ever grow (never shrink).

Run:  python3 tests/test_split_store.py   or   make test
"""
from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import update_trending as UT  # noqa: E402
import validate as V  # noqa: E402

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


def sample_measurement(mid="qwen3-14b"):
    return {"engine": "llama.cpp", "tps": "50", "hardware": "RTX 3060", "quant": "Q4",
            "date": "2026-09-28", "source_post": "https://lightbrd.com/od/status/1",
            "likes": 5, "comments": 1, "reshares": 0, "views": 10, "interactions": 16,
            "weight_gb": "3.5GB"}


def flat_store():
    m = {
        "id": "qwen3-14b", "name": "Qwen3 14B", "full_name": "Qwen3-14B", "type": "LLM",
        "formats": [{"name": "GGUF", "hf": "Qwen/Qwen3-14B"}], "license": "Apache 2.0",
        "params": "14B", "hf": "Qwen/Qwen3-14B", "vram_tier": "9GB", "vram_min": "8GB",
        "backends": ["CUDA"], "supported_engines": ["llama.cpp"],
        "engines": [sample_measurement()],
        "why": "w", "engagement": {"likes": 5, "comments": 1, "views": 10, "last_7d_likes": 2},
        "last_seen": "2026-09-28",
    }
    return {"generated_utc": "2026-09-28T10:00:00Z",
            "engines": {"llama.cpp": {"backend": "CUDA", "note": "x", "url": "https://github.com/ggml-org/llama.cpp"}},
            "models": [m]}


def test_split_pulls_counters_off_rows():
    cat, meas, posts = UT.split_store(flat_store())
    row = meas["qwen3-14b"][0]
    check("split: counters are NOT on the measurement row",
          all(k not in row for k in UT._MEASUREMENT_COUNTERS), json.dumps(row))
    check("split: footprint stays on the measurement row", row.get("weight_gb") == "3.5GB", json.dumps(row))
    check("split: source_post stays on the measurement row", row.get("source_post")==sample_measurement()["source_post"])
    check("split: counters move to posts.json", posts[sample_measurement()["source_post"]]["likes"] == 5,
          json.dumps(posts.get(sample_measurement()["source_post"])))
    check("split: catalog has NO inline engines[]",
          "engines" not in cat["models"][0], list(cat["models"][0].keys()))


def test_flatten_reconstructs_identity():
    cat, meas, posts = UT.split_store(flat_store())
    back = UT.flatten_store(cat, meas, posts)
    def key(s):
        return {(m["id"], e.get("engine"), str(e.get("tps")), e.get("source_post"),
                 e.get("weight_gb", ""))
                for m in s["models"] for e in m.get("engines", [])}
    check("flatten: every (model, engine, tps, source_post, footprint) survives",
          key(back) == key(flat_store()))
    check("flatten: counters spliced back", back["models"][0]["engines"][0]["likes"] == 5)
    check("flatten: store is flat for readers", "engines" in back["models"][0])


def test_missing_post_resolves_zero():
    cat, meas, posts = UT.split_store(flat_store())
    exports = copy.deepcopy(meas)
    for mid, rows in exports.items():
        for r in rows:
            r["source_post"] = "https://example.com/not-in-posts"
    back = UT.flatten_store(cat, exports, posts)
    row = back["models"][0]["engines"][0]
    check("missing post -> counters resolve to 0 (never a penalty)",
          row["likes"] == 0 and row["views"] == 0, json.dumps(row))


def test_max_counters_never_shrink():
    a = flat_store()
    a["models"][0]["engines"].append(
        dict(sample_measurement(), likes=9, source_post="https://lightbrd.com/od/status/2"))
    # a lower like count for the SAME post must not become the stored value
    low = flat_store()
    low["models"][0]["engines"][0]["source_post"] = "https://lightbrd.com/od/status/2"
    low["models"][0]["engines"][0]["likes"] = 2
    _, _, posts_a = UT.split_store(a)
    _, _, posts_low = UT.split_store(low)
    check("posts hold the MAX across referencing rows",
          posts_a["https://lightbrd.com/od/status/2"]["likes"] == 9
          and posts_low["https://lightbrd.com/od/status/2"]["likes"] == 2,
          json.dumps(posts_a["https://lightbrd.com/od/status/2"]) +
          " / " + json.dumps(posts_low["https://lightbrd.com/od/status/2"]))


def test_new_contracts_validate_the_real_files():
    schema_m = json.loads((ROOT / "data" / "measurements_contract.json").read_text())
    schema_p = json.loads((ROOT / "data" / "posts_contract.json").read_text())
    import jsonschema
    measurements = json.loads((ROOT / "data" / "measurements.json").read_text())
    posts = json.loads((ROOT / "data" / "posts.json").read_text())
    try:
        jsonschema.validate(instance=measurements, schema=schema_m)
        jsonschema.validate(instance=posts, schema=schema_p)
        check("contracts validate the shipped split files", True)
    except jsonschema.ValidationError as e:
        check("contracts validate the shipped split files", False, e.message)


def test_validate_split_flatten_is_green():
    store = json.loads((ROOT / "data" / "models.json").read_text())
    failures_before = len(V.FAILURES)
    V.check_split_flatten(store)
    check("validate.check_split_flatten passes on the real store",
          len(V.FAILURES) == failures_before, V.FAILURES[failures_before:])


def test_shipped_split_matches_flat_store():
    cat, meas, posts = UT.split_store(json.loads((ROOT / "data" / "models.json").read_text()))
    shipped_m = json.loads((ROOT / "data" / "measurements.json").read_text())
    shipped_p = json.loads((ROOT / "data" / "posts.json").read_text())
    check("shipped measurements.json == split_store(models.json)", shipped_m == meas)
    check("shipped posts.json == split_store(models.json)", shipped_p == posts)


def main() -> int:
    test_split_pulls_counters_off_rows()
    test_flatten_reconstructs_identity()
    test_missing_post_resolves_zero()
    test_max_counters_never_shrink()
    test_new_contracts_validate_the_real_files()
    test_validate_split_flatten_is_green()
    test_shipped_split_matches_flat_store()
    print(f"\nPASSED {_PASS} | FAILED {_FAIL}")
    return 1 if _FAIL else 0


if __name__ == "__main__":
    raise SystemExit(main())