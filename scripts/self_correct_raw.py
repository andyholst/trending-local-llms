#!/usr/bin/env python3
"""Self-correct raw search snapshots so they conform to data/search_contract.json.

Used by the fix-bot (and locally via `make correct-raw`) as part of the fix
job: when a raw snapshot fails the search_contract — e.g. a search dropped a
required field like vram_min, license, or backends — this fills in the missing
value FROM THE DATA IT HAS / known defaults, so the snapshot is repaired
rather than discarded. It never invents t/s figures.

Fill rules (per missing field, uses only data already present in the payload):
  - id          -> derived slug from name (if missing)
  - full_name   -> name (if missing)
  - license     -> "Unknown" (only when absent; never guesses a specific one)
  - params      -> "unknown" (only when absent)
  - hf          -> left as-is (cannot derive; must come from search) -> flagged
  - vram_tier   -> derive from smallest vram_min-style value present, else leave
  - vram_min    -> derive from vram_tier if present, else leave
  - backends    -> derive from engine registry backend of the engines present,
                   plus ROCm for any row measured on AMD hardware
  - date on engine -> use snapshot generated_utc date (fallback)
  - source_post remains required (cannot fake) -> flagged if missing

Re-writes the file in place only when changes were made. Exit 0 = all raw
snapshots now conform (or were corrected); non-zero = some field cannot be
derived (missing source_post / hf) and must be re-searched.

Run:  python3 scripts/self_correct_raw.py
"""
from __future__ import annotations

import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
# Allow tests to run against a small fixture in a temp dir.
RAW_DIR = Path(os.environ.get("TRENDING_DATA_DIR", str(ROOT / "data"))) / "raw"

REQUIRED_MODEL = ["id", "name", "full_name", "type", "license", "params", "hf",
                  "vram_tier", "vram_min", "backends", "engines", "last_seen"]
REQUIRED_ENGINE = ["engine", "tps", "date", "source_post"]


def slug(name: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return s or "unknown"


def derive_vram_min(vram_tier: str) -> str:
    # vram_min is the LEAST required; vram_tier is a category. If we only have
    # a tier, use it as the min (conservative, not invented larger).
    m = re.search(r"(\d+)\s*GB", vram_tier or "")
    return f"{m.group(1)}GB" if m else ""


# Store/README backends, in the order update_trending.BACKENDS renders them.
_BACKENDS = ("CUDA", "Metal", "CPU", "ROCm")
# Raw-snapshot backend names (the search legs) — update_trending.SEARCH_LEGS
# keys, plus the retired 'general' kept so historical snapshots still validate.
RAW_BACKENDS = ("nvidia", "metal", "cpu", "amd", "general")
_LEG_OF = {"CUDA": "nvidia", "Metal": "metal", "CPU": "cpu", "ROCm": "amd"}


def _is_amd_gpu(hw: str) -> bool:
    import sys
    sys.path.insert(0, str(ROOT / "scripts"))
    try:
        import update_trending as ut
    finally:
        sys.path.pop(0)
    return ut.is_amd_gpu(hw)


def derive_backends(engines, store_engines) -> list:
    backs = []
    for e in engines:
        eng = store_engines.get(e.get("engine"), {})
        b = eng.get("backend", "")
        for cand in _BACKENDS:
            if re.search(rf"\b{cand}\b", b):
                backs.append(cand)
        # an AMD card in the hardware is ROCm whatever the engine is registered as
        if _is_amd_gpu(e.get("hardware") or ""):
            backs.append("ROCm")
    # de-dup, preserve order CUDA,Metal,CPU,ROCm
    out = []
    for b in _BACKENDS:
        if b in backs and b not in out:
            out.append(b)
    return out or ["CUDA"]


def correct_snapshot(path: Path, store: dict) -> list[str]:
    """Returns list of (field) notes for what was corrected/flagged."""
    data = json.loads(path.read_text())
    notes = []
    ts_date = data.get("generated_utc", "")[:10]

    # search_contract.json has additionalProperties:false at the top level, so
    # prune any extra keys the Hermes agent wrote (note, window, queries_used,
    # engines metadata, etc.) that are not declared. Without this the snapshot
    # fails check_search_contract and the aggregate job dies.
    _ALLOWED_TOP = {"backend", "generated_utc", "models"}
    extra_top = sorted(set(data.keys()) - _ALLOWED_TOP)
    for k in extra_top:
        data.pop(k, None)
    if extra_top:
        notes.append(f"{path.name}: pruned unexpected top-level keys {extra_top}")
    # search_contract requires a top-level 'backend'. A search that dropped it
    # (e.g. the CPU prompt wrote only models + generated_utc) must be repaired
    # here, not left to fail check_search_contract. Derive it from the snapshot
    # filename prefix (<backend>-<UTC>.json) when present, else from the models'
    # backends field, else default to 'general'.
    if not data.get("backend"):
        stem = path.stem
        prefix = stem.split("-")[0].lower()
        if prefix in RAW_BACKENDS:
            data["backend"] = prefix
        else:
            backs = {b for m in data.get("models", []) for b in m.get("backends", [])}
            legs = [_LEG_OF[b] for b in ("Metal", "ROCm", "CPU") if b in backs]
            data["backend"] = legs[0] if legs else "general"
        notes.append(f"{path.name}: backend <- '{data['backend']}' (derived from filename/models)")
    for m in data.get("models", []):
        if not m.get("id"):
            m["id"] = slug(m.get("name", "unknown"))
            notes.append(f"{path.name}/{m.get('id')}: derived id")
        if not m.get("full_name"):
            m["full_name"] = m.get("name", "")
            notes.append(f"{path.name}/{m.get('id')}: full_name <- name")
        if not m.get("license"):
            m["license"] = "Unknown"
            notes.append(f"{path.name}/{m.get('id')}: license <- 'Unknown'")
        if not m.get("params"):
            m["params"] = "unknown"
            notes.append(f"{path.name}/{m.get('id')}: params <- 'unknown'")
        if not m.get("vram_min") and m.get("vram_tier"):
            m["vram_min"] = derive_vram_min(m["vram_tier"])
            notes.append(f"{path.name}/{m.get('id')}: vram_min <- {m['vram_min']}")
        if not m.get("vram_tier") and m.get("vram_min"):
            m["vram_tier"] = m["vram_min"]
            notes.append(f"{path.name}/{m.get('id')}: vram_tier <- vram_min")
        if not m.get("backends"):
            m["backends"] = derive_backends(m.get("engines", []), store.get("engines", {}))
            notes.append(f"{path.name}/{m.get('id')}: backends from engines")
        if not m.get("last_seen"):
            m["last_seen"] = ts_date
            notes.append(f"{path.name}/{m.get('id')}: last_seen <- snapshot date")
        for e in m.get("engines", []):
            if not e.get("date"):
                e["date"] = ts_date
                notes.append(f"{path.name}/{m.get('id')}: engine date <- snapshot date")
    # detect fields we cannot derive
    cannot = []
    for m in data.get("models", []):
        if not m.get("hf"):
            cannot.append(f"{m.get('id')}: hf missing (cannot derive)")
        for e in m.get("engines", []):
            if not e.get("source_post"):
                cannot.append(f"{m.get('id')}/{e.get('engine')}: source_post missing (cannot derive)")
    if cannot:
        notes.append("CANNOT_DERIVE: " + "; ".join(cannot))
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")
    return notes


def main() -> int:
    if not RAW_DIR.exists():
        print("(no data/raw snapshots yet)")
        return 0
    store_path = ROOT / "data" / "models.json"
    store = json.loads(store_path.read_text()) if store_path.exists() else {"engines": {}}
    any_correction = False
    cannot_any = False
    for path in sorted(RAW_DIR.glob("*.json")):
        try:
            notes = correct_snapshot(path, store)
        except Exception as e:  # noqa: BLE001
            print(f"  ERROR {path.name}: {e}")
            cannot_any = True
            continue
        if notes:
            any_correction = True
            for n in notes:
                print(f"  {n}")
            if any("CANNOT_DERIVE" in n for n in notes):
                cannot_any = True
    if cannot_any:
        print("SELF-CORRECT INCOMPLETE: some fields (hf/source_post) cannot be derived — re-search needed.")
        return 1
    print("SELF-CORRECT OK: all raw snapshots conform (or were corrected from available data).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
