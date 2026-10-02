#!/usr/bin/env python3
"""AMD (ROCm) as a first-class backend (issue #76).

Every guard here FAILS on the pre-#76 code (origin/master before this change):

  classifier      AMD hardware -> ROCm, not the CUDA default / CPU ('Ryzen 5 7600 +
                  RX 7800 XT' was CPU, 'RX 7900 XTX' with Strata/vLLM was CUDA);
                  Vulkan on NVIDIA stays CUDA; 'amd'/'hip'/'vulkan' alone are not AMD
  vram            'RX 7900 XTX 24GB' read as 189,600 GB (the 'x' of 'xtx' was a
                  multiplier); AMD cards in the VRAM table; host CPU != RX card
  scope / speed   consumer Radeon + Strix Halo earn speed, Instinct never does
  merge identity  'AMD Radeon RX 7900 XTX' collapsed with an AMD Ryzen CPU row
  render          ROCm table, most-loved ROCm column, matrix legend + cell
  validator       unsorted / missing / misplaced ROCm table, wrong ROCm cell,
                  backends without ROCm
  ingest          AMD leg raw snapshot -> store (backends gain ROCm) -> README
  contracts       ROCm / amd enum values, canonical joined engine backends
  registry        AMD-only engine registers as ROCm, mixed as 'CUDA / ROCm'
  wiring          the amd leg is wired everywhere nvidia/metal/cpu are
                  (Makefile, both workflows, smoke, contract, self-correct)

Run:  python3 tests/test_amd_backend.py   or   make test
"""
from __future__ import annotations

import copy
import glob
import io
import json
import os
import re
import sys
import tempfile
from contextlib import redirect_stdout
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import engine_registry as ER  # noqa: E402
import self_correct_raw as SC  # noqa: E402
import update_trending as UT  # noqa: E402
import validate as V  # noqa: E402

try:
    import yaml
except ImportError:  # pragma: no cover
    yaml = None

TODAY = datetime(2026, 10, 1, tzinfo=timezone.utc)
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
    if os.environ.get("PYTEST_CURRENT_TEST"):  # also a real assertion under pytest
        assert cond, f"{name} {detail}"


# ---------------------------------------------------------------- fixtures --
REGISTRY = {
    "llama.cpp": {"backend": "CUDA / ROCm / CPU / Metal", "note": "n", "url": "https://github.com/ggml-org/llama.cpp"},
    "vLLM": {"backend": "CUDA / ROCm", "note": "n", "url": "https://github.com/vllm-project/vllm"},
    "Strata": {"backend": "CUDA / ROCm", "note": "n", "url": "https://github.com/Niko1221/Strata"},
    "MLX": {"backend": "Metal", "note": "n", "url": "https://github.com/ml-explore/mlx"},
}


def meas(engine, tps, hw, date="2026-09-30", post="https://lightbrd.com/u/status/1", quant="Q4_K_M", **eng):
    e = {"engine": engine, "tps": tps, "hardware": hw, "quant": quant, "date": date, "source_post": post}
    e.update(eng)
    return e


def model(mid, name, engines, backends=("CUDA",), last_seen="2026-09-30"):
    return {
        "id": mid, "name": name, "full_name": name.replace(" ", "-"), "type": "LLM",
        "license": "Apache 2.0", "params": "27B", "hf": f"org/{mid}", "vram_tier": "16GB",
        "vram_min": "16GB", "backends": list(backends), "supported_engines": sorted({e["engine"] for e in engines}),
        "formats": [{"name": name, "hf": f"org/{mid}"}], "why": "w", "engines": engines, "last_seen": last_seen,
        "engagement": {"likes": 0, "comments": 0, "views": 0, "last_7d_likes": 0, "seen_posts": []},
    }


def amd_store() -> dict:
    """Shape every assertion below rides on: one model on NVIDIA + AMD + Apple,
    one AMD-only model (two Radeon figures), one NVIDIA-only model."""
    return {
        "generated_utc": "2026-10-01T00:00:00Z", "engines": copy.deepcopy(REGISTRY),
        "models": [
            model("mixed", "Mixed Q", [
                meas("llama.cpp", "120", "RTX 4090", post="https://lightbrd.com/a/status/1"),
                meas("llama.cpp", "88", "RX 7900 XTX 24GB", quant="Q4_K_M, Vulkan", post="https://lightbrd.com/a/status/2"),
                meas("MLX", "70", "MacBook Pro M4 Max", post="https://lightbrd.com/a/status/3"),
            ], backends=("CUDA", "Metal", "ROCm")),
            model("amdonly", "Radeon Only", [
                meas("Strata", "60", "RX 7900 XTX 24GB", post="https://lightbrd.com/b/status/4", likes=500, comments=41),
                meas("vLLM", "95", "RX 9070 XT 16GB", quant="FP8, ROCm 7.2", post="https://lightbrd.com/b/status/5"),
            ], backends=("ROCm",)),
            model("nvonly", "Green Only", [
                meas("vLLM", "150", "RTX 5090", post="https://lightbrd.com/c/status/6"),
            ]),
        ],
    }


class TempReadme:
    """Point the validator at a temp README (and back)."""

    def __init__(self, text: str):
        self.text = text

    def __enter__(self):
        self.saved = V.README
        self.dir = tempfile.TemporaryDirectory()
        p = Path(self.dir.name) / "README.md"
        p.write_text(self.text)
        V.README = p
        V.FAILURES.clear()
        return p

    def __exit__(self, *exc):
        V.README = self.saved
        self.dir.cleanup()


def run_quiet(fn, *a):
    buf = io.StringIO()
    with redirect_stdout(buf):
        fn(*a)
    return buf.getvalue()


def render(store=None) -> tuple[dict, str]:
    s = store or amd_store()
    s["models"] = UT.sort_models(s["models"], TODAY)
    return s, UT.render_readme(s, TODAY)


def section(md: str, emoji: str) -> str:
    return md.split(f"# {emoji}", 1)[1].split("\n---", 1)[0]


def row(md_section: str, name: str) -> str:
    return next((ln for ln in md_section.splitlines() if ln.startswith(f"| [**{name}**]")), "")


# -------------------------------------------------------------- classifier --
def test_classifier():
    # Given hardware strings as posts write them, When classified (with the
    # store registry, as renderer and validator do), Then AMD GPUs -> ROCm.
    cases = [
        ("RX 7900 XTX 24GB", "llama.cpp", "ROCm"),
        ("Radeon 7800 XT", "llama.cpp", "ROCm"),
        ("AMD Radeon RX 9070 XT", "Ollama", "ROCm"),
        ("rx7600", "llama.cpp", "ROCm"),
        ("ROCm", "llama.cpp", "ROCm"),
        ("llama.cpp (Vulkan) on RX 9070 XT", "llama.cpp", "ROCm"),
        ("Ryzen 5 7600 + RX 7800 XT", "llama.cpp", "ROCm"),          # host CPU named too: was CPU
        ("RX 7900 XTX 24GB", "Strata", "ROCm"),                      # Strata is CUDA in ENGINE_BACKEND: was CUDA
        ("RX 9070 XT 16GB", "vLLM", "ROCm"),                         # vLLM single-backend CUDA map: was CUDA
        ("Radeon 8060S / Strix Halo 128GB", "llama.cpp", "ROCm"),
        ("Ryzen AI Max+ 395 (Strix Halo)", "llama.cpp", "ROCm"),     # 'ryzen' alone was CPU
        ("Radeon AI PRO R9700 32GB", "llama.cpp", "ROCm"),
        ("AMD GPU 8GB", "llama.cpp", "ROCm"),
        ("Instinct MI300X", "vLLM", "ROCm"),
        # not AMD GPU evidence on its own
        ("RTX 4090 Vulkan", "llama.cpp", "CUDA"),                    # Vulkan is cross-vendor
        ("RTX 3090, ROCm-free", "llama.cpp", "CUDA"),
        ("2x RTX 5070 Ti + 2x RX 7900 XTX", "llama.cpp", "CUDA"),    # any NVIDIA token -> CUDA
        ("Ryzen 9 7950X", "llama.cpp", "CPU"),
        ("AMD EPYC 9654", "llama.cpp", "CPU"),
        ("AMD Ryzen 7 7840U", "llama.cpp", "CPU"),
        ("Ryzen AI Max+ 395, CPU only", "llama.cpp", "CPU"),         # explicit CPU-only wins
        ("Raspberry Pi 5 chip, shipped", "llama.cpp", "CPU"),        # 'hip' inside 'chip'/'shipped'
        ("MacBook Pro M4 Max", "MLX", "Metal"),
    ]
    for hw, eng, want in cases:
        got = UT.measurement_backend({"engine": eng, "hardware": hw}, REGISTRY)
        check(f"classify: {hw!r} ({eng}) -> {want}", got == want, got)
    # registry-only AMD engine with blank hardware -> its single registry backend
    reg = dict(REGISTRY, **{"HipServe": {"backend": "ROCm", "note": "n", "url": "https://github.com/x/hipserve"}})
    check("classify: registry-only ROCm engine with blank hardware -> ROCm",
          UT.measurement_backend({"engine": "HipServe", "hardware": ""}, reg) == "ROCm")
    check("classify: ROCm in quant text breaks a tie toward ROCm, CUDA tokens still win",
          UT.measurement_backend({"engine": "Unknown", "hardware": "", "quant": "ROCm 7.2"}) == "ROCm"
          and UT.measurement_backend({"engine": "Unknown", "hardware": "", "quant": "CUDA graphs, ROCm off"}) == "CUDA")


def test_vram_scope_speed():
    vram = {
        "RX 7900 XTX 24GB": 24, "RX 7900 XTX": 24, "RX 7900 XT": 20, "7900 GRE": 16, "RX 7800 XT": 16,
        "RX 7600": 8, "RX 7600 XT": 16, "RX 9070 XT": 16, "RX 9070": 16, "Radeon AI PRO R9700": 32,
        "2x RX 7900 XTX": 48, "rx7600": 8, "2x RTX 3090": 48, "RTX 4090": 24,
    }
    for hw, want in vram.items():
        got = UT.hardware_vram_gb(hw)
        check(f"vram: {hw!r} -> {want} GB", got == want, got)
    check("vram: host CPU 'Ryzen 5 7600' is not an RX 7600", UT.hardware_vram_gb("Ryzen 5 7600") is None)
    check("vram: 'xtx' suffix is not a multiplier (was 7900 x 24 = 189,600 GB)",
          UT.hardware_vram_gb("RX 7900 XTX 24GB") == 24)
    scope = {
        "RX 7900 XTX 24GB": True, "RX 9070 XT": True, "Radeon 8060S / Strix Halo 128GB": True,
        "Ryzen AI Max+ 395 128GB": True, "4x RX 7900 XTX": False, "Instinct MI300X": False,
        "MI355X": False, "AMD MI210 64GB": False,
    }
    for hw, want in scope.items():
        got = UT.in_scope({"engine": "llama.cpp", "hardware": hw})
        check(f"scope: {hw!r} in_scope={want}", got == want, got)
    # Given an AMD-only model trending this week, When scored, Then its Radeon
    # figure earns the speed bonus exactly like a CUDA one; an Instinct one never.
    consumer = model("c", "C", [meas("llama.cpp", "70", "RX 7900 XTX 24GB", date="2026-09-30")])
    dc = model("d", "D", [meas("vLLM", "700", "Instinct MI300X 192GB", date="2026-09-30")])
    UT.sort_models([consumer, dc], TODAY)
    check("speed: consumer Radeon 70 t/s -> +3.0", consumer["engagement"]["speed_bonus"] == 3.0, consumer["engagement"])
    check("speed: Instinct MI300X never earns speed", dc["engagement"]["speed_bonus"] == 0, dc["engagement"])


def test_merge_identity():
    # Given an AMD GPU row and an AMD CPU row with concordant t/s on one engine,
    # When merged, Then both survive (pre-#76 _gpu_size mapped both to 'cpu').
    gpu = meas("llama.cpp", "40", "AMD Radeon RX 7900 XTX", post="https://lightbrd.com/x/status/1")
    cpu = meas("llama.cpp", "41", "AMD Ryzen 9 7950X", post="https://lightbrd.com/x/status/2")
    out = UT.merge_engines([gpu], [cpu])
    check("merge: Radeon GPU and Ryzen CPU rows stay distinct", len(out) == 2, out)
    xt = meas("llama.cpp", "40", "RX 7900 XT", post="https://lightbrd.com/x/status/3")
    check("merge: RX 7900 XTX and RX 7900 XT are different cards",
          len(UT.merge_engines([gpu], [xt])) == 2)
    same = meas("llama.cpp", "41", "Radeon RX 7900 XTX 24GB", post="https://lightbrd.com/x/status/4")
    check("merge: same card reported twice collapses to one row", len(UT.merge_engines([gpu], [same])) == 1)
    check("identity: AMD card ids", (UT._gpu_size("RX 7900 XTX"), UT._gpu_size("7900 xt"), UT._gpu_size("rx-6600"),
                                    UT._gpu_size("Strix Halo"), UT._gpu_size("AMD Ryzen 9 7950X"))
          == ("rx7900xtx", "rx7900xt", "rx6600", "amd-apu", "cpu"))


# ------------------------------------------------------------------ render --
def test_render():
    s, md = render()
    check("render: ROCm table heading", "# 🟪 ROCm — AMD GPUs (8–48 GB)" in md)
    rocm, cuda = section(md, "🟪"), section(md, "🟦")
    check("render: AMD-only model is in the ROCm table", row(rocm, "Radeon Only") != "")
    check("render: AMD-only model is NOT in the CUDA table (Strata/vLLM map to CUDA)", row(cuda, "Radeon Only") == "",
          row(cuda, "Radeon Only")[:120])
    check("render: mixed model's Radeon figure in ROCm, its RTX figure in CUDA",
          "**88**" in row(rocm, "Mixed Q") and "**88**" not in row(cuda, "Mixed Q") and "**120**" in row(cuda, "Mixed Q"))
    peaks = [float(V._split_row(r)[4]) for r in rocm.splitlines() if r.startswith("| [**")]
    check("render: ROCm table sorted by peak t/s desc", peaks == sorted(peaks, reverse=True) and len(peaks) == 2, peaks)
    hdr = next(ln for ln in md.splitlines() if ln.startswith("| Model | Status"))
    cols = [c.strip() for c in V._split_row(hdr)]
    check("render: most-loved has a ROCm column after CUDA/Metal/CPU",
          cols[3:7] == ["CUDA t/s (best)", "Metal t/s (best)", "CPU t/s (best)", "ROCm t/s (best)"], cols)
    loved = next(ln for ln in md.splitlines() if ln.startswith("| [**Radeon Only**]"))
    cells = [c.strip() for c in V._split_row(loved)]
    check("render: most-loved ROCm cell = best Radeon figure (95, vLLM) + '+1 more'",
          cells[6].startswith("**95**") and "+1 more" in cells[6] and cells[3] == "—", cells[3:7])
    check("render: matrix legend lists 🟪 ROCm", "🟪 ROCm" in md.split("## 🧭", 1)[1].split("\n---", 1)[0])
    matrix_row = next(ln for ln in md.split("## 🧭", 1)[1].splitlines() if ln.startswith("| **Mixed Q**"))
    check("render: matrix llama.cpp cell carries CUDA and ROCm bests", "🟦 120" in matrix_row and "🟪 88" in matrix_row,
          matrix_row)
    # Given a store with no AMD figure, Then the ROCm table still renders (empty)
    s2 = amd_store()
    s2["models"] = [m for m in s2["models"] if m["id"] == "nvonly"]
    _, md2 = render(s2)
    check("render: no AMD data -> empty ROCm table, never padded",
          "_No models measured on this backend yet._" in section(md2, "🟪"))


# --------------------------------------------------------------- validator --
def test_validator():
    s, md = render()
    with TempReadme(md):
        run_quiet(V.check_backend_sort, s)
        run_quiet(V.check_readme_measurements, s)
        run_quiet(V.check_readme_tables_wellformed, s)
        run_quiet(V.check_backends_cover_measurements, s)
        check("validator: generated README with ROCm passes sort/measurements/tables/backends",
              not V.FAILURES, V.FAILURES)
    # unsorted ROCm table
    rocm = section(md, "🟪")
    lines = rocm.split("\n")
    data_idx = [i for i, ln in enumerate(lines) if ln.startswith("| [**")]
    swapped = lines[:]
    swapped[data_idx[0]], swapped[data_idx[1]] = lines[data_idx[1]], lines[data_idx[0]]
    with TempReadme(md.replace(rocm, "\n".join(swapped))):
        run_quiet(V.check_backend_sort, s)
        check("validator: unsorted ROCm table -> FAIL", any("ROCm README table not sorted" in f for f in V.FAILURES),
              V.FAILURES)
    # missing ROCm table
    with TempReadme(md.replace("# 🟪 ROCm", "# ROCm (renamed)")):
        run_quiet(V.check_backend_sort, s)
        check("validator: missing ROCm table -> FAIL", "README missing ROCm backend table" in V.FAILURES, V.FAILURES)
    # Radeon figure moved into the CUDA table
    rad = row(rocm, "Radeon Only")
    cuda = section(md, "🟦")
    moved = md.replace(rad + "\n", "").replace(cuda, cuda.rstrip("\n") + "\n" + rad + "\n")
    with TempReadme(moved):
        run_quiet(V.check_readme_measurements, s)
        check("validator: ROCm measurement rendered under CUDA -> FAIL",
              any("Radeon Only has a ROCm measurement but no row in the ROCm table" in f for f in V.FAILURES),
              V.FAILURES)
    # most-loved ROCm cell not the best
    loved = next(ln for ln in md.splitlines() if ln.startswith("| [**Radeon Only**]"))
    with TempReadme(md.replace(loved, loved.replace("**95** t/s", "**60** t/s", 1))):
        run_quiet(V.check_readme_measurements, s)
        check("validator: most-loved ROCm cell not the best -> FAIL",
              any("most-loved ROCm cell for Radeon Only" in f for f in V.FAILURES), V.FAILURES)
    # backends missing ROCm
    s3 = amd_store()
    s3["models"][1]["backends"] = ["CUDA"]
    V.FAILURES.clear()
    run_quiet(V.check_backends_cover_measurements, s3)
    check("validator: AMD figures but backends without ROCm -> FAIL",
          any("amdonly has ROCm measurement(s)" in f for f in V.FAILURES), V.FAILURES)
    V.FAILURES.clear()


# ------------------------------------------------------- ingest + contracts --
def _contract(name):
    return json.loads((ROOT / "data" / name).read_text())


def test_contracts():
    import jsonschema
    mc, sc = _contract("model_contract.json"), _contract("search_contract.json")
    enum = mc["properties"]["engines"]["additionalProperties"]["properties"]["backend"]["enum"]
    from itertools import combinations
    canon = {UT.join_backends(c) for n in range(1, 5) for c in combinations(UT.BACKENDS, n)}
    check("contract: engine backend enum == every canonical join_backends combo", set(enum) == canon,
          sorted(set(enum) ^ canon))
    check("contract: additive — the pre-#76 engine backends are still allowed",
          {"CUDA", "Metal", "CPU", "CUDA / CPU / Metal", "CUDA / Metal"} <= set(enum))
    check("contract: issue values present ('ROCm', 'CUDA / ROCm', 'CUDA / ROCm / Metal')",
          {"ROCm", "CUDA / ROCm", "CUDA / ROCm / Metal"} <= set(enum))
    check("contract: model backends enum == BACKENDS",
          set(mc["properties"]["models"]["items"]["properties"]["backends"]["items"]["enum"]) == set(UT.BACKENDS))
    check("contract: search models[].backends enum == BACKENDS",
          set(sc["properties"]["models"]["items"]["properties"]["backends"]["items"]["enum"]) == set(UT.BACKENDS))
    check("contract: search backend enum == search legs + retired 'general'",
          set(sc["properties"]["backend"]["enum"]) == set(UT.SEARCH_LEGS) | {"general"})
    # every historical raw snapshot still validates against the widened contract
    bad = []
    for f in sorted(glob.glob(str(ROOT / "data" / "raw" / "*.json"))):
        try:
            jsonschema.validate(json.loads(Path(f).read_text()), sc)
        except jsonschema.ValidationError as e:
            bad.append((Path(f).name, e.message))
    check("contract: every data/raw snapshot (old + amd) validates", not bad, bad)


def test_ingest_end_to_end():
    import jsonschema
    # Given the store as it was before the AMD leg (no ROCm anywhere) and an
    # amd-<UTC>.json raw snapshot, When ingested + sorted + rendered,
    # Then the existing model gains ROCm, a new AMD-only model is ROCm-only,
    # the store validates against the contract and the README shows both.
    base = amd_store()
    base["models"] = [m for m in base["models"] if m["id"] == "nvonly"]
    base["models"][0]["backends"] = ["CUDA"]
    raw = {"backend": "amd", "generated_utc": "2026-09-30T10:00:00Z", "models": [
        {"id": "nvonly", "name": "Green Only", "full_name": "Green-Only", "type": "LLM", "license": "Apache 2.0",
         "params": "27B", "hf": "org/nvonly", "vram_tier": "16GB", "vram_min": "16GB", "backends": ["ROCm"],
         "last_seen": "2026-09-30",
         "engines": [meas("vLLM", "90", "RX 9070 XT 16GB", quant="FP8, ROCm", post="https://lightbrd.com/r/status/7")]},
        {"id": "newamd", "name": "New AMD", "full_name": "New-AMD", "type": "LLM", "license": "MIT",
         "params": "8B", "hf": "org/newamd", "vram_tier": "8GB", "vram_min": "8GB", "backends": ["ROCm"],
         "last_seen": "2026-09-30",
         "engines": [meas("llama.cpp", "55", "RX 7600 8GB", quant="Q4_K_M, Vulkan", post="https://lightbrd.com/r/status/8")]},
    ]}
    sc = _contract("search_contract.json")
    try:
        jsonschema.validate(raw, sc)
        ok = True
    except jsonschema.ValidationError as e:
        ok = e.message
    check("ingest: an amd leg snapshot conforms to search_contract.json", ok is True, ok)
    saved = UT.RAW_DIR
    with tempfile.TemporaryDirectory() as td:
        (Path(td) / "amd-20260930-100000.json").write_text(json.dumps(raw))
        UT.RAW_DIR = Path(td)
        try:
            run_quiet(UT.ingest_raw_snapshots, base)
        finally:
            UT.RAW_DIR = saved
    by = {m["id"]: m for m in base["models"]}
    check("ingest: existing model gains 'ROCm' in backends", by["nvonly"]["backends"] == ["CUDA", "ROCm"],
          by["nvonly"]["backends"])
    check("ingest: new AMD-only model is backends=['ROCm'] (not registry CUDA/CPU/Metal)",
          by.get("newamd", {}).get("backends") == ["ROCm"], by.get("newamd", {}).get("backends"))
    base["models"] = UT.sort_models(base["models"], TODAY)
    base["generated_utc"] = "2026-10-01T00:00:00Z"
    try:
        jsonschema.validate(base, _contract("model_contract.json"))
        ok = True
    except jsonschema.ValidationError as e:
        ok = e.message
    check("ingest: resulting store validates against model_contract.json", ok is True, ok)
    md = UT.render_readme(base, TODAY)
    rocm = section(md, "🟪")
    check("ingest: README ROCm table shows both AMD figures",
          row(rocm, "Green Only") != "" and row(rocm, "New AMD") != "", rocm[:300])


def test_registry():
    import jsonschema
    amd = [meas("E", "50", "RX 7900 XTX 24GB")]
    check("registry: AMD-only engine infers 'ROCm' (was CUDA)", ER._infer_backend(amd) == "ROCm", ER._infer_backend(amd))
    check("registry: NVIDIA + AMD engine infers 'CUDA / ROCm'",
          ER._infer_backend(amd + [meas("E", "70", "RTX 4090")]) == "CUDA / ROCm")
    check("registry: CUDA + ROCm + Metal engine infers 'CUDA / ROCm / Metal'",
          ER._infer_backend(amd + [meas("E", "70", "RTX 4090"), meas("E", "40", "Mac Studio M3 Ultra")])
          == "CUDA / ROCm / Metal")
    for desc in ("Fast LLM inference engine for AMD GPUs (ROCm)", "Vulkan backend for GGUF models",
                 "HIP kernels for local LLM serving"):
        kind, _ = ER.classify_repo({"full_name": "o/r", "description": desc, "topics": []}, "r")
        check(f"registry: classify {desc!r} -> engine", kind == "engine", kind)
    kind, _ = ER.classify_repo({"full_name": "o/r", "description": "Chat UI for ROCm users", "topics": []}, "r")
    check("registry: a ROCm chat UI is still not an engine (strong signal wins)", kind == "not-engine", kind)
    # an AMD-only engine auto-registered at ingest validates against the store contract
    s = {"generated_utc": "2026-10-01T00:00:00Z", "engines": copy.deepcopy(REGISTRY), "models": []}
    fake = {"full_name": "amdlab/radeonserve", "description": "LLM inference server for Radeon (ROCm)", "topics": []}
    decisions = ER.register_new_engines(s, [{"id": "m", "engines": [
        meas("RadeonServe", "80", "RX 7900 XTX 24GB", engine_repo="https://github.com/amdlab/radeonserve")]}],
        fetch=lambda url: fake)
    check("registry: AMD-only engine registered with backend 'ROCm'",
          decisions and decisions[0]["decision"] == "registered" and s["engines"]["RadeonServe"]["backend"] == "ROCm",
          (decisions, s["engines"].get("RadeonServe")))
    try:
        jsonschema.validate(s, _contract("model_contract.json"))
        ok = True
    except jsonschema.ValidationError as e:
        ok = e.message
    check("registry: auto-registered ROCm entry validates against model_contract.json", ok is True, ok)


def test_self_correct():
    # Given an amd-<UTC>.json snapshot that dropped 'backend' and a model that
    # dropped 'backends', When self-corrected, Then backend='amd' and ROCm is derived.
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "amd-20261002-101010.json"
        p.write_text(json.dumps({"generated_utc": "2026-10-02T10:10:10Z", "models": [
            {"id": "x", "name": "X", "hf": "org/x", "engines": [meas("Strata", "60", "RX 7900 XTX 24GB")]}]}))
        notes = SC.correct_snapshot(p, {"engines": copy.deepcopy(REGISTRY), "models": []})
        out = json.loads(p.read_text())
    check("self-correct: amd-<UTC>.json backend <- 'amd'", out.get("backend") == "amd", (out.get("backend"), notes))
    check("self-correct: Radeon row derives ROCm in backends", "ROCm" in out["models"][0].get("backends", []),
          out["models"][0].get("backends"))
    check("self-correct: raw backend names == search legs + general",
          set(SC.RAW_BACKENDS) == set(UT.SEARCH_LEGS) | {"general"})


# ------------------------------------------------------------------ wiring --
def test_wiring_parity():
    """The amd leg is wired everywhere the other legs are. One list
    (update_trending.SEARCH_LEGS) - a leg missing anywhere fails here."""
    legs = list(UT.SEARCH_LEGS)
    check("legs: nvidia/metal/cpu/amd", legs == ["nvidia", "metal", "cpu", "amd"], legs)
    check("legs: every leg maps to a README backend, every backend has a leg",
          sorted(UT.SEARCH_LEGS.values()) == sorted(UT.BACKENDS), UT.SEARCH_LEGS)
    check("legs: SEARCH_GROUPS (--fetch path) has one group per backend",
          sorted(UT.SEARCH_GROUPS) == sorted(UT.BACKENDS), list(UT.SEARCH_GROUPS))
    mk = (ROOT / "Makefile").read_text()
    for b in legs:
        check(f"make: _search-{b} recipe", f"\n_search-{b}:\n\thermes -z " in mk)
        check(f"make: public search-{b} docker wrapper", f"\nsearch-{b}:\n\t$(DOCKER_RUN) sh -c \"make _setup && make _search-{b}\"" in mk)
    agg = re.search(r"\n_search:\n.*?make -j4 ([^\n]+)", mk, re.S)
    check("make: _search runs every leg in parallel",
          agg and sorted(agg.group(1).split()) == sorted(f"_search-{b}" for b in legs), agg and agg.group(1))
    test_recipe = re.search(r"\n_test:\n\t([^\n]+)", mk).group(1)
    unwired = sorted(p.name for p in (ROOT / "tests").glob("test_*.py") if f"tests/{p.name}" not in test_recipe)
    check("make: every tests/test_*.py runs in the _test fallback chain (pytest may be absent)", not unwired, unwired)
    ns = {}
    exec(compile((ROOT / "scripts" / "smoke_search.py").read_text(), "smoke_search.py", "exec"), ns)
    check("smoke: one keyword list per leg", sorted(ns["BACKEND_KEYWORDS"]) == sorted(legs))
    prompt = mk[mk.index("_search-amd:\n"):].split("\n", 2)[1]
    for needle, why in (("--write-raw amd <", "writes data/raw/amd-<UTC>.json"),
                        ("record the AMD card exactly as posted in hardware", "the card is what classifies ROCm"),
                        ("put the API (ROCm, HIP, Vulkan) in quant, never in the engine name", "no pseudo-engines"),
                        ("never prompt-processing or prefill t/s", "decode t/s only"),
                        ("skip datacenter Instinct", "8-48 GB scope")):
        check(f"prompt amd: {why}", needle in prompt)
    check("prompt amd: no stray NVIDIA/CPU leg text (copy-paste guard)",
          "--write-raw cpu" not in prompt and "CPU/embedded/edge keywords" not in prompt)
    if yaml is None:
        print("  SKIP workflow parity (PyYAML not installed)")
        return

    def load(name):
        d = yaml.safe_load((ROOT / ".github" / "workflows" / name).read_text())
        return d.get("on") or d.get(True), d["jobs"]
    _, rj = load("refresh-bot.yml")
    check("refresh-bot: search matrix == legs", rj["search"]["strategy"]["matrix"]["backend"] == legs,
          rj["search"]["strategy"]["matrix"])
    _, qj = load("qa-validate.yml")
    live = "\n".join(s.get("run", "") for s in qj["live-smoke"]["steps"])
    check("qa-validate: live smoke per leg", sorted(re.findall(r"BACKEND=(\w+)", live)) == sorted(legs),
          re.findall(r"BACKEND=(\w+)", live))


def test_real_store():
    """Acceptance (#76): the real store/README carry a real AMD measurement."""
    s = json.loads((ROOT / "data" / "models.json").read_text())
    reg = s.get("engines", {})
    rocm = [(m["id"], e) for m in s["models"] for e in m.get("engines", [])
            if UT.measurement_backend(e, reg) == "ROCm"]
    check("store: at least one ROCm measurement", len(rocm) >= 1, len(rocm))
    check("store: every ROCm measurement cites a real …/status/<id> post",
          all(UT._is_post_url(e.get("source_post", "")) for _, e in rocm), [e.get("source_post") for _, e in rocm])
    check("store: every model with a ROCm figure lists ROCm in backends",
          all("ROCm" in next(m for m in s["models"] if m["id"] == mid)["backends"] for mid, _ in rocm))
    readme = (ROOT / "README.md").read_text()
    check("README: ROCm table present with a row", "# 🟪 ROCm" in readme
          and any(r.startswith("| [**") for r in section(readme, "🟪").splitlines()))
    agents = (ROOT / "AGENTS.md").read_text()
    check("AGENTS.md: AMD (ROCm) is a first-class backend", "AMD (ROCm)" in agents and "🟪" in agents)


def main() -> int:
    print("AMD (ROCm) first-class backend (issue #76)")
    test_classifier()
    test_vram_scope_speed()
    test_merge_identity()
    test_render()
    test_validator()
    test_contracts()
    test_ingest_end_to_end()
    test_registry()
    test_self_correct()
    test_wiring_parity()
    test_real_store()
    print(f"\nPASSED {_PASS} | FAILED {_FAIL}")
    return 1 if _FAIL else 0


if __name__ == "__main__":
    raise SystemExit(main())
