#!/usr/bin/env python3
"""Explicit NVIDIA hardware wins over a non-CUDA engine registry (issue #1864).

Real-file guard (rule 6m): drives the REAL measurement_backend() over the REAL
shipped store (models.json + measurements.json + posts.json, flattened the same
way load_store() flattens them) with the store's OWN engines registry. No
stand-ins, no monkeypatch: the 13 rows named in #1864 must classify CUDA, and a
genuine TensorFold-on-Mac row must still classify Metal.

Run:  python3 tests/test_nvidia_before_registry.py   or   make test
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import update_trending as UT  # noqa: E402

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


def real_store() -> dict:
    """The shipped store in the flat shape every reader uses (issue #697)."""
    d = ROOT / "data"
    return UT.flatten_store(json.loads((d / "models.json").read_text()),
                            json.loads((d / "measurements.json").read_text()),
                            json.loads((d / "posts.json").read_text()))


# The 13 rows measured in #1864: (model id, engine, hardware, tps).
NAMED = [
    ("qwen3.8-27b", "TensorFold", "2x RTX 5060 Ti 16GB", "108.8"),
    ("qwen3.8-27b", "TensorFold", "RTX 4090 Laptop GPU 16GB", "103.1"),
    ("qwen3.8-27b", "TensorFold", "RTX 5090 32GB (ThinkingCap run 1)", "54"),
    ("qwen3.8-27b", "TensorFold", "NVIDIA DGX Spark (GB10), 64K context", "1045"),
    ("qwen3.8-27b", "TensorFold", "NVIDIA GB10 (DGX Spark)", "200.7"),
    ("qwen3.8-27b", "TensorFold", "NVIDIA DGX Spark (GB10)", "54"),
    ("qwen3.8-27b", "TensorFold", "RTX 4090 24GB", "86"),
    ("qwen3.8-27b", "TensorFold", "RTX 5090 32GB", "352.28"),
    ("qwen3.8-flash-next-125b", "TensorFold", "NVIDIA DGX Spark (GB10, 128GB unified)", "200.7"),
    ("bonsai-2-27b", "MLX", "NVIDIA RTX 5090", "120"),
    ("bonsai-2-27b", "MLX", "single RTX 5090", "143"),
    ("qwen3.8-27b-thinkingcap-tensorfold-1spark", "TensorFold", "NVIDIA DGX Spark (GB10)", "125.2"),
    ("thinkingcap-27b", "TensorFold", "NVIDIA DGX Spark (GB10, 1 Spark)", "54"),
]


def test_named_rows_are_cuda():
    s = real_store()
    reg = s.get("engines", {})
    rows = {(m["id"], e.get("engine"), e.get("hardware"), str(e.get("tps"))): e
            for m in s["models"] for e in m.get("engines", [])}
    for mid, eng, hw, tps in NAMED:
        e = rows.get((mid, eng, hw, tps))
        check(f"store row present: {mid} / {hw} / {tps}", e is not None)
        if e is None:
            continue
        got = UT.measurement_backend(e, reg)
        check(f"classify CUDA over registry: {mid} / {eng} / {hw}", got == "CUDA", got)

    # The visible consequence in #1864: the 1045 t/s DGX Spark figure must not
    # be presented as the Apple-Silicon column's best number.
    e1045 = rows.get(("qwen3.8-27b", "TensorFold", "NVIDIA DGX Spark (GB10), 64K context", "1045"))
    check("1045 t/s DGX Spark figure is CUDA, not Metal",
          e1045 is not None and UT.measurement_backend(e1045, reg) == "CUDA")


def test_every_explicit_nvidia_row_wins_over_registry():
    s = real_store()
    reg = s.get("engines", {})
    wrong = []
    total = 0
    for m in s["models"]:
        for e in m.get("engines", []):
            hw = (" " + (e.get("hardware") or "") + " ").lower()
            if "apple" in hw or "mac" in hw or UT._CPU_ONLY_RE.search(hw):
                continue
            if not any(k in hw for k in UT._CUDA_HW):
                continue
            total += 1
            if UT.measurement_backend(e, reg) != "CUDA":
                wrong.append((m["id"], e.get("engine"), e.get("hardware")))
    check(f"all {total} explicit-NVIDIA rows classify CUDA (no stand-ins)", not wrong, wrong[:3])


def test_apple_and_cpu_only_keep_priority():
    s = real_store()
    reg = s.get("engines", {})
    mac = [(m["id"], e) for m in s["models"] for e in m.get("engines", [])
           if e.get("engine") == "TensorFold"
           and any(k in (" " + (e.get("hardware") or "") + " ").lower() for k in ("apple", "mac"))]
    check("real TensorFold-on-Mac rows exist", len(mac) >= 1, len(mac))
    check("real TensorFold-on-Mac rows still classify Metal",
          all(UT.measurement_backend(e, reg) == "Metal" for _, e in mac),
          [(mid, e.get("hardware")) for mid, e in mac if UT.measurement_backend(e, reg) != "Metal"][:3])
    # Apple wording and explicit CPU-only wording outrank a CUDA token.
    check("a TensorFold row on Mac hardware stays Metal",
          UT.measurement_backend({"engine": "TensorFold", "hardware": "M5 Pro Mac mini 64GB"}, reg) == "Metal")
    check("explicit CPU-only wording still wins over a CUDA token",
          UT.measurement_backend({"engine": "TensorFold", "hardware": "RTX 4090, CPU only"}, reg) == "CPU")


def main() -> int:
    print("NVIDIA hardware beats a non-CUDA engine registry (issue #1864)")
    test_named_rows_are_cuda()
    test_every_explicit_nvidia_row_wins_over_registry()
    test_apple_and_cpu_only_keep_priority()
    print(f"\nPASSED {_PASS} | FAILED {_FAIL}")
    return 1 if _FAIL else 0


if __name__ == "__main__":
    raise SystemExit(main())
