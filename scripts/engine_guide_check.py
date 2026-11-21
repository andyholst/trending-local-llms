#!/usr/bin/env python3
"""Check that the README's inference engine / server guide stays in step with the
store registry and the engines actually measured (issue #1220).

`render_readme` builds BOTH the trending tables and the engine guide from
data/models.json in one pass. Nothing verified that a refresh which updated the
trending lists also re-rendered the guide, so a PR could leave the reader-facing
server list behind the data with every gate green. This is a READ-ONLY check:
it never writes a file, never mutates the store (rule 3b), and names every
offending engine so a red gate is actionable.

Usage:
    python3 scripts/engine_guide_check.py          # data/models.json + README.md
    python3 scripts/engine_guide_check.py --data DIR --readme FILE
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

GUIDE_HEADING = "## ⚙️ Inference engine / server guide"
ROW = re.compile(r"^\|\s*\[([^\]]+)\]\(([^)]*)\)\s*\|", re.MULTILINE)


def guide_engines(readme: str) -> list[str]:
    """Engine names in the reader-facing guide table (one `[name](url)` per row)."""
    i = readme.find(GUIDE_HEADING)
    if i < 0:
        return []
    j = readme.find("\n## ", i + len(GUIDE_HEADING))
    section = readme[i:j if j > 0 else len(readme)]
    return [m.group(1).strip() for m in ROW.finditer(section)]


def measured_engines(measurements: dict) -> set[str]:
    """Engines that actually carry a t/s figure: {model_id: [measurement, ...]}."""
    used = set()
    for rows in (measurements or {}).values():
        for row in rows if isinstance(rows, list) else []:
            if isinstance(row, dict) and row.get("engine"):
                used.add(str(row["engine"]))
    return used


def problems(guide: list[str], registry: dict, measured: set[str]) -> list[str]:
    """Named, actionable drift findings. Empty means the guide is current."""
    out = []
    reg = set(registry or {})
    listed = set(guide)
    if not guide:
        out.append("the README has no engine guide table (render it with --render-only)")
    for name in sorted(reg - listed):
        out.append(f"engine {name!r} is in the store registry but MISSING from the README guide")
    for name in sorted(listed - reg):
        out.append(f"engine {name!r} is in the README guide but NOT in the store registry (stale row)")
    for name in sorted(measured - reg):
        out.append(f"engine {name!r} has measurements but is NOT registered in the store")
    for name in sorted(measured - listed):
        out.append(f"engine {name!r} is measured but MISSING from the README guide")
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--data", default=str(ROOT / "data"), help="store data directory")
    ap.add_argument("--readme", default=str(ROOT / "README.md"), help="README to check")
    a = ap.parse_args(argv)
    data = Path(a.data)
    readme = Path(a.readme)
    store = json.loads((data / "models.json").read_text())
    guide = guide_engines(readme.read_text())
    measurements = json.loads((data / "measurements.json").read_text()) \
        if (data / "measurements.json").exists() else {}
    found = problems(guide, store.get("engines") or {}, measured_engines(measurements))
    if found:
        print(f"[engine-guide-check] FAIL {len(found)} drift finding(s):")
        for line in found:
            print(f"  - {line}")
        print("  Fix: python3 scripts/update_trending.py --render-only (then commit README.md)")
        return 1
    print(f"[engine-guide-check] OK: {len(guide)} guide row(s) match "
          f"{len(store.get('engines') or {})} registry engine(s) and "
          f"{len(measured_engines(measurements))} measured engine(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())