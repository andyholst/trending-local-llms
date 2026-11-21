#!/usr/bin/env python3
"""tests/test_engine_guide_check.py — issue #1220: the README's inference-server guide
must stay in step with the store registry and the engines actually measured when the
trending lists refresh.

The check is READ-ONLY (rule 3b) and runs in CI (`_validate-search`), so a refresh that
updates the data but forgets to re-render the guide goes RED with the exact engine names
instead of silently shipping a stale server list.

The guards call the REAL checker; the only external system is the filesystem.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "tests"))

import engine_guide_check as GC  # noqa: E402
from wiring import wired  # noqa: E402

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


def test_guide_parsing_and_shipped_store():
    readme = (ROOT / "README.md").read_text()
    guide = GC.guide_engines(readme)
    store = json.loads((ROOT / "data" / "models.json").read_text())
    reg = store.get("engines") or {}
    meas = json.loads((ROOT / "data" / "measurements.json").read_text())
    matrix = GC.matrix_engines(readme)
    used = GC.measured_engines(meas)
    check("the shipped guide table is parsed", len(guide) >= 40, str(len(guide)))
    check("the shipped engine matrix columns are parsed", len(matrix) >= 40, str(len(matrix)))
    check("the shipped guide and matrix match the registry and measurements",
          not GC.problems(guide, reg, used, matrix),
          str(GC.problems(guide, reg, used, matrix)[:3]))
    check("a missing matrix is a finding, not a silent pass",
          any("no engine matrix" in p for p in GC.problems(guide, reg, used, [])))
    check("a missing heading is a finding, not a silent pass",
          any("no engine guide table" in p for p in GC.problems([], reg, set())))


def test_planted_drift_is_named():
    reg = {"llama.cpp": {}, "vLLM": {}, "MLX": {}}
    guide = ["llama.cpp", "vLLM", "MLX"]
    check("a clean planted set passes", not GC.problems(guide, reg, {"llama.cpp"}))
    missing = GC.problems(["llama.cpp", "MLX"], reg, set())
    check("a registry engine dropped from the guide is named",
          any("vLLM" in p and "MISSING" in p for p in missing), str(missing))
    stale = GC.problems(guide + ["GhostEngine"], reg, set())
    check("a stale guide row is named",
          any("GhostEngine" in p and "stale" in p for p in stale), str(stale))
    unregistered = GC.problems(guide, reg, {"Strata"})
    check("a measured but unregistered engine is named",
          any("Strata" in p and "NOT registered" in p for p in unregistered), str(unregistered))
    stale_matrix = GC.problems(guide, reg, {"llama.cpp", "vLLM"}, ["llama.cpp", "GhostEngine"])
    check("a stale engine-matrix column is named",
          any("GhostEngine" in p and "engine matrix" in p for p in stale_matrix), str(stale_matrix))
    missing_matrix = GC.problems(guide, reg, {"MLX"}, ["llama.cpp"])
    check("a measured engine missing from the matrix is named",
          any("MLX" in p and "engine matrix" in p for p in missing_matrix), str(missing_matrix))


def test_the_check_runs_in_ci():
    mk = (ROOT / "Makefile").read_text()
    check("_validate-search invokes the check (CI validate job)",
          "python3 scripts/engine_guide_check.py" in mk)
    check("there is a standalone make target", "engine-guide-check:" in mk)


def test_wiring():
    check("this suite is discovered by `make test`", wired(__file__), "")


def main() -> int:
    print("engine guide / registry sync (issue #1220):")
    test_guide_parsing_and_shipped_store()
    test_planted_drift_is_named()
    test_the_check_runs_in_ci()
    test_wiring()
    print(f"{'FAILED' if _FAIL else 'PASSED'} {_PASS} | FAILED {_FAIL}")
    return 1 if _FAIL else 0


if __name__ == "__main__":
    raise SystemExit(main())
