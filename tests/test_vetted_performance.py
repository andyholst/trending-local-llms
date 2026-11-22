#!/usr/bin/env python3
"""Read-only vetted-performance view (issue #1252) regression suite."""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "tests"))
import vetted_performance as VP  # noqa: E402
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
        print(f"  FAIL {name}  [{detail}]")


def main() -> int:
    print("vetted performance view (issue #1252):")
    models = {"models": [
        {"id": "m-fast", "name": "Fast Model", "engagement": {"posts_7d": 0}},
        {"id": "m-slow", "name": "Slow Model", "engagement": {"posts_7d": 9}},
    ]}
    measures = {
        "m-fast": [
            {"tps": "700", "hardware": "RTX 3060 12GB", "engine": "MLX",
             "date": "2026-10-16", "quant": "Q4", "source_post": "u/a/1"},
            # duplicate source+engine+hardware — must not double-count
            {"tps": "700", "hardware": "RTX 3060 12GB", "engine": "MLX",
             "date": "2026-10-16", "source_post": "u/a/1"},
        ],
        "m-slow": [
            {"tps": "20", "hardware": "RTX 4090 24GB", "engine": "llama.cpp",
             "date": "2026-11-17", "source_post": "u/b/2"},
            # no source post: UNVETTED, must not enter the vetted top
            {"tps": "9999", "hardware": "RTX 5090 32GB", "engine": "vLLM",
             "date": "2026-11-17"},
        ],
    }
    rows = VP.evidence_rows(models, measures)
    check("vetted rows are joined with VRAM and parsed t/s", len(rows) == 3 and sum(1 for r in rows if r["vetted"]) == 2, str(rows))
    check("duplicate source+engine+hardware is dropped",
          len([r for r in rows if r["model_key"] == "m-fast"]) == 1)
    check("a row with no source post is still reported as unvetted",
          any(not r["vetted"] for r in rows))
    groups = VP.top_by_band(rows)
    rendered = VP.render(groups, sum(1 for r in rows if not r["vetted"]))
    check("top t/s is rendered per VRAM band", "700.0" in rendered and "8-16GB" in rendered)
    check("the source post is rendered so vetted is auditable",
          "u/a/1" in rendered and "UNVETTED" not in rendered)
    check("the unvetted 9999 t/s row is NOT in the vetted table", "9999.0" not in rendered)
    check("the view never writes a store", ".write_text(" not in
          (ROOT / "scripts/vetted_performance.py").read_text(encoding="utf-8"))
    makefile = (ROOT / "Makefile").read_text(encoding="utf-8")
    check("make vetted-performance is bound", "vetted-performance:" in makefile and
          "scripts/vetted_performance.py" in makefile)
    check("this suite is discovered by `make test`", wired(__file__))
    print(f"PASSED {_PASS} | FAILED {_FAIL}")
    return 1 if _FAIL else 0


if __name__ == "__main__":
    raise SystemExit(main())
