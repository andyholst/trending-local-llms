#!/usr/bin/env python3
"""Run the actual make targets against a SMALL fixture in a temp dir.

The real pipeline needs live Firecrawl/Hermes searches (~12 min each). This
test instead points the make targets at a tiny fixture via TRENDING_DATA_DIR /
TRENDING_README, so the deterministic make commands (merge, validate,
validate-search, validate-mapped, test) can be exercised end-to-end fast.

Run:  python3 tests/test_make_commands.py   or   make test
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

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


def make(target, env):
    """Run a make target on the host (the _-prefixed recipes are host commands)."""
    return subprocess.run(
        ["make", target],
        cwd=str(ROOT),
        env={**os.environ, **env},
        capture_output=True,
        text=True,
    )


def build_fixture(tmp: Path) -> dict:
    """A tiny but contract-conformant data/ tree + README in a temp dir."""
    data = tmp / "data"
    (data / "raw").mkdir(parents=True)
    (data / "snapshots").mkdir(parents=True)

    engines = {
        "llama.cpp": {"backend": "CUDA", "note": "x", "url": "https://github.com/ggml-org/llama.cpp"},
        "MLX": {"backend": "Metal", "note": "x", "url": "https://github.com/ml-explore/mlx"},
    }
    model = {
        "id": "qwen3-14b", "name": "Qwen3 14B", "full_name": "Qwen3-14B", "type": "LLM",
        "formats": [{"name": "GGUF", "hf": "Qwen/Qwen3-14B"}], "license": "Apache 2.0",
        "params": "14B", "hf": "Qwen/Qwen3-14B", "vram_tier": "9GB", "vram_min": "8GB",
        "backends": ["CUDA"], "supported_engines": ["llama.cpp"],
        "engines": [{"engine": "llama.cpp", "tps": "50", "hardware": "RTX 3060",
                     "quant": "Q4", "date": "2026-09-28", "source_post": "https://lightbrd.com/1"}],
        "why": "w", "engagement": {"likes": 5, "comments": 1, "views": 10, "last_7d_likes": 2},
        "last_seen": "2026-09-28",
    }
    store = {"generated_utc": "2026-09-28T10:00:00Z", "engines": engines, "models": [model]}
    (data / "models.json").write_text(json.dumps(store, indent=2) + "\n")

    # copy the real contracts so schema checks pass
    shutil.copy(ROOT / "data" / "model_contract.json", data / "model_contract.json")
    shutil.copy(ROOT / "data" / "search_contract.json", data / "search_contract.json")

    # one raw snapshot per backend (small)
    for backend, eng, tps in [("nvidia", "llama.cpp", "50"), ("metal", "MLX", "85")]:
        raw = {
            "backend": backend, "generated_utc": "2026-09-28T10:00:00Z",
            "models": [{
                "id": "qwen3-14b", "name": "Qwen3 14B", "full_name": "Qwen3-14B", "type": "LLM",
                "license": "Apache 2.0", "params": "14B", "hf": "Qwen/Qwen3-14B",
                "vram_tier": "9GB", "vram_min": "8GB", "backends": ["CUDA" if backend == "nvidia" else "Metal"],
                "engines": [{"engine": eng, "tps": tps, "hardware": "RTX 3060" if backend == "nvidia" else "M4 Max",
                             "date": "2026-09-28", "source_post": f"https://lightbrd.com/{backend}"}],
                "last_seen": "2026-09-28",
            }],
        }
        (data / "raw" / f"{backend}-20260928-100000.json").write_text(json.dumps(raw, indent=2) + "\n")

    readme = tmp / "README.md"
    readme.write_text("# placeholder\n")
    return {"TRENDING_DATA_DIR": str(data), "TRENDING_README": str(readme)}


def test_make_merge():
    with tempfile.TemporaryDirectory() as td:
        env = build_fixture(Path(td))
        r = make("_merge", env)
        check("make _merge exits 0", r.returncode == 0, r.stderr[-300:])
        store = json.loads((Path(env["TRENDING_DATA_DIR"]) / "models.json").read_text())
        check("make _merge wrote models.json", "models" in store)
        check("make _merge regenerated README", "Trending Local LLMs" in Path(env["TRENDING_README"]).read_text())


def test_make_validate():
    with tempfile.TemporaryDirectory() as td:
        env = build_fixture(Path(td))
        make("_merge", env)
        r = make("_validate", env)
        check("make _validate exits 0", r.returncode == 0, r.stdout[-300:] + r.stderr[-300:])
        check("make _validate reports QA PASSED", "QA PASSED" in r.stdout)


def test_make_validate_search():
    with tempfile.TemporaryDirectory() as td:
        env = build_fixture(Path(td))
        make("_merge", env)
        r = make("_validate-search", env)
        check("make _validate-search exits 0", r.returncode == 0, r.stdout[-300:] + r.stderr[-300:])


def test_make_validate_mapped():
    with tempfile.TemporaryDirectory() as td:
        env = build_fixture(Path(td))
        make("_merge", env)
        r = make("_validate-mapped", env)
        check("make _validate-mapped exits 0", r.returncode == 0, r.stdout[-300:] + r.stderr[-300:])


def test_make_test():
    """Run the individual test files directly (NOT `make _test`, which would
    recurse into this file). Verifies the test suite passes against the fixture."""
    with tempfile.TemporaryDirectory() as td:
        env = build_fixture(Path(td))
        make("_merge", env)
        for tf in ["test_mapping.py", "test_validate.py", "test_validate_readme.py", "test_ingest_render.py"]:
            r = subprocess.run(
                [sys.executable, str(ROOT / "tests" / tf)],
                cwd=str(ROOT), env={**os.environ, **env},
                capture_output=True, text=True,
            )
            check(f"{tf} exits 0", r.returncode == 0, r.stdout[-200:] + r.stderr[-200:])


def main() -> int:
    print("make commands against small fixture")
    test_make_merge()
    test_make_validate()
    test_make_validate_search()
    test_make_validate_mapped()
    test_make_test()
    print(f"\nPASSED {_PASS} | FAILED {_FAIL}")
    return 1 if _FAIL else 0


if __name__ == "__main__":
    raise SystemExit(main())
