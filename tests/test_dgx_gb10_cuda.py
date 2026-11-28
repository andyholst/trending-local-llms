#!/usr/bin/env python3
"""DGX Spark / GB10 are explicit NVIDIA hardware (issue #1866).

Real-file guard (rule 6m): drives the REAL measurement_backend() over the REAL
shipped store (models.json + measurements.json + posts.json, flattened exactly
as load_store() flattens them) with the store's OWN engines registry. No
stand-ins and no monkeypatch: the guard asserts the vocabulary change itself,
the three rows named in #1866, the full before/after delta recorded in
findings/1866.md, and that Apple/Mac and explicit-CPU-only precedence is kept.

Run:  python3 tests/test_dgx_gb10_cuda.py   or   make test
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


def rows_by_key(s: dict) -> dict:
    return {(m["id"], e.get("engine"), e.get("hardware"), str(e.get("tps"))): e
            for m in s["models"] for e in m.get("engines", [])}


# The three rows named in #1866 (model id, engine, hardware, tps).
NAMED = [
    ("qwen3.8-flash-next-125b", "TensorFold", "DGX Spark", "67"),
    ("qwen3.8-flash-next-125b", "TensorFold",
     "DGX Spark (GB10, 128GB), TP1 (decode tests on two Sparks)", "39.3"),
    ("glm-5.3-flash", "TensorFold", "2x DGX Spark (200 Gb/s link)", "109.1"),
]


def deltas_from_findings():
    """Every enumerated before/after row, with its recorded decision."""
    lines = (ROOT / "findings" / "1866.md").read_text().splitlines()
    out = []
    for line in lines:
        if line.startswith("- DELTA "):
            parts = [p.strip() for p in line[len("- DELTA "):].split("::")]
            if len(parts) != 7:
                raise AssertionError(f"malformed DELTA line: {line!r}")
            mid, eng, hw, tps, before, after, decision = parts
            out.append((mid, eng, hw, tps, before, after, decision))
    return out


def test_vocabulary_is_one_set():
    check("dgx is in the ONE _CUDA_HW token set", "dgx" in UT._CUDA_HW, UT._CUDA_HW)
    check("gb10 is in the ONE _CUDA_HW token set", "gb10" in UT._CUDA_HW, UT._CUDA_HW)
    # The same vocabulary feeds NVIDIA guard, AMD exclusion, CPU check and fallback.
    check("is_nvidia_gpu('DGX Spark') is True", UT.is_nvidia_gpu("DGX Spark"))
    check("is_nvidia_gpu('2x DGX Spark (200 Gb/s link)') is True",
          UT.is_nvidia_gpu("2x DGX Spark (200 Gb/s link)"))
    check("is_nvidia_gpu('GB10') is True", UT.is_nvidia_gpu("GB10"))
    # AMD exclusion still reads the same set: an AMD APU plus an NVIDIA token
    # is NOT AMD hardware (rule 6's 'no NVIDIA token' clause).
    check("is_amd_gpu excludes a Strix Halo + GB10 string",
          not UT.is_amd_gpu("Radeon 8060S / Strix Halo 128GB (ASUS Ascent GX10, GB10)"))


def test_named_rows_are_cuda():
    s = real_store()
    reg = s.get("engines", {})
    rows = rows_by_key(s)
    for mid, eng, hw, tps in NAMED:
        e = rows.get((mid, eng, hw, tps))
        check(f"store row present: {mid} / {hw} / {tps}", e is not None)
        if e is None:
            continue
        got = UT.measurement_backend(e, reg)
        check(f"classify CUDA: {mid} / {eng} / {hw}", got == "CUDA", got)


def test_every_dgx_gb10_row_is_cuda():
    s = real_store()
    reg = s.get("engines", {})
    wrong = []
    total = 0
    for m in s["models"]:
        for e in m.get("engines", []):
            text = ((e.get("hardware") or "") + " " + (e.get("quant") or "")).lower()
            if "dgx" not in text and "gb10" not in text:
                continue
            total += 1
            got = UT.measurement_backend(e, reg)
            if got != "CUDA":
                wrong.append((m["id"], e.get("engine"), e.get("hardware"), got))
    check("real store has DGX/GB10 rows", total >= 1, total)
    check(f"all {total} DGX/GB10 rows classify CUDA (no stand-ins)", not wrong, wrong[:5])


def test_enumerated_delta_matches_its_decision():
    s = real_store()
    reg = s.get("engines", {})
    rows = rows_by_key(s)
    deltas = deltas_from_findings()
    check("findings/1866.md enumerates the six shifted rows", len(deltas) == 6, len(deltas))
    for mid, eng, hw, tps, before, after, decision in deltas:
        e = rows.get((mid, eng, hw, tps))
        check(f"delta row present: {mid} / {hw} / {tps}", e is not None)
        if e is None:
            continue
        got = UT.measurement_backend(e, reg)
        check(f"delta decision ({decision}): {mid} / {eng} / {hw}",
              got == after, f"before={before} documented_after={after} got={got}")
        check(f"delta is a real shift: {mid} / {hw}", before != after)


def test_apple_and_cpu_only_keep_priority():
    s = real_store()
    reg = s.get("engines", {})
    mac = [(m["id"], e) for m in s["models"] for e in m.get("engines", [])
           if e.get("engine") == "TensorFold"
           and any(k in (" " + (e.get("hardware") or "") + " ").lower()
                   for k in ("apple", "mac"))]
    check("real TensorFold-on-Mac rows exist", len(mac) >= 1, len(mac))
    check("real TensorFold-on-Mac rows still classify Metal",
          all(UT.measurement_backend(e, reg) == "Metal" for _, e in mac),
          [(mid, e.get("hardware")) for mid, e in mac
           if UT.measurement_backend(e, reg) != "Metal"][:3])
    check("a TensorFold row on Mac hardware stays Metal",
          UT.measurement_backend({"engine": "TensorFold", "hardware": "M5 Pro Mac mini 64GB"}, reg) == "Metal")
    check("explicit CPU-only wording still wins over a DGX token",
          UT.measurement_backend({"engine": "TensorFold", "hardware": "DGX Spark, CPU only"}, reg) == "CPU")


def main() -> int:
    print("DGX Spark / GB10 classify as explicit NVIDIA hardware (issue #1866)")
    test_vocabulary_is_one_set()
    test_named_rows_are_cuda()
    test_every_dgx_gb10_row_is_cuda()
    test_enumerated_delta_matches_its_decision()
    test_apple_and_cpu_only_keep_priority()
    print(f"\nPASSED {_PASS} | FAILED {_FAIL}")
    return 1 if _FAIL else 0


if __name__ == "__main__":
    raise SystemExit(main())
