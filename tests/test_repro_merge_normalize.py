#!/usr/bin/env python3
"""Repro test: ingest a raw snapshot missing derived fields must not crash and
must produce a store that conforms to model_contract.json (esp. full_name)."""
import json
import sys
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

spec = importlib.util.spec_from_file_location("ut", ROOT / "scripts" / "update_trending.py")
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

# Simulate a store + a raw snapshot whose new model is missing derived fields
store = {
    "models": [{
        "id": "existing", "name": "Exist", "full_name": "Exist Model",
        "hf": "x/y", "license": "MIT", "params": "1B", "type": "LLM",
        "vram_tier": "12GB", "engagement": {"last_7d_likes": 1}, "engines": [],
    }],
    "engines": {},
}
raw_dir = ROOT / "data" / "raw"
raw_dir.mkdir(exist_ok=True)
raw_dir.joinpath("test-repro.json").write_text(json.dumps({"models": [{"id": "newm", "name": "BrandNew", "hf": "a/b"}]}))

try:
    added, updated = mod.ingest_raw_snapshots(store)
    assert added == 1, f"expected 1 added, got {added}"
    # must have been normalized
    nm = store["models"][1]
    assert nm.get("full_name") == "BrandNew", f"full_name not normalized: {nm!r}"
    assert nm.get("license") == "Unknown", "license not defaulted"
    assert nm.get("params") == "unknown", "params not defaulted"
    assert nm.get("backends"), "backends not derived"
    assert nm.get("engagement", {}).get("likes") == 0, "engagement not defaulted"
    # render must not crash on missing full_name
    mod.render_readme(store, mod.now_utc())
    print("REPRO PASS: new model normalized, render OK")
except Exception as e:  # noqa: BLE001
    print(f"REPRO FAIL: {type(e).__name__}: {e}")
    sys.exit(1)
finally:
    raw_dir.joinpath("test-repro.json").unlink(missing_ok=True)
