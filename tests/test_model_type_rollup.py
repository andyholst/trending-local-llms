#!/usr/bin/env python3
"""tests/test_model_type_rollup.py — issue #1246.

The rollup derives `type_group` from the shipped `type` label without editing any
store (rule 3b; #1235 still awaits the owner's persistence ruling). This suite drives
the REAL stores plus a planted unknown label and alias join.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "tests"))
import model_type_rollup as MTR  # noqa: E402
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


def main() -> int:
    print("model-type rollup (issue #1246):")
    check("the two MoE labels map to one group",
          MTR.group_of("LLM (MoE)") == "moe" and MTR.group_of("MoE LLM") == "moe")
    check("GGUF is a format, not an architecture",
          MTR.group_of("GGUF") == "format-only")
    check("an unseen label is UNKNOWN, never bucketed",
          MTR.group_of("Brand New Type") == "unknown")

    models, measurements = MTR.load_stores(ROOT / "data/models.json", ROOT / "data/measurements.json")
    groups = MTR.rollup(models, measurements)
    check("every shipped model lands in a group",
          sum(g["models"] for g in groups.values()) == len(models["models"]),
          str({k: v["models"] for k, v in groups.items()}))
    check("the live store has no unknown labels", "unknown" not in groups,
          str(groups.get("unknown", {}).get("unknown_labels")))
    check("MoE is one bucket of 31 models", groups["moe"]["models"] == 31,
          str(groups["moe"]["models"]))
    check("measurements are joined to the groups",
          sum(g["measurements"] for g in groups.values()) > 100,
          str(sum(g["measurements"] for g in groups.values())))
    check("the report names engines, architectures and median t/s",
          all(x in MTR.render(groups) for x in ("engines", "architectures", "median t/s")))

    planted = {"models": [
        {"id": "x", "type": "Brand New Type", "measurement_model_aliases": ["alias-x"]},
    ]}
    check("shipped string t/s parses (and a range takes its first number)",
          MTR.parse_tps("40") == 40.0 and MTR.parse_tps("40-50") == 40.0)
    planted_measures = {"alias-x": [
        {"engine": "mlx-lm", "hardware": "M3 Max", "tps": "42", "date": "2026-11-22"},
    ]}
    pg = MTR.rollup(planted, planted_measures)
    check("aliased measurements join through the declared alias",
          pg["unknown"]["measurements"] == 1, str(pg["unknown"]))
    check("a planted unknown label is REPORTED",
          "Brand New Type" in MTR.render(pg), MTR.render(pg))
    windowed = MTR.rollup(models, measurements, window_days=7)
    check("a 7-day window drops older measurements",
          0 < sum(g["measurements"] for g in windowed.values()) <
          sum(g["measurements"] for g in groups.values()),
          str((sum(g["measurements"] for g in windowed.values()),
               sum(g["measurements"] for g in groups.values()))))
    check("window cutoff is anchored to the newest stored date",
          MTR.latest_date(measurements) == "2026-11-17", MTR.latest_date(measurements))
    source = (ROOT / "scripts/model_type_rollup.py").read_text(encoding="utf-8")
    check("the rollup never writes a store", ".write_text(" not in source and ".write_bytes(" not in source)
    makefile = (ROOT / "Makefile").read_text(encoding="utf-8")
    check("make model-type-report is bound",
          "model-type-report:" in makefile and "scripts/model_type_rollup.py" in makefile)
    check("this suite is discovered by `make test`", wired(__file__))
    print(f"{'FAILED' if _FAIL else 'PASSED'} {_PASS} | FAILED {_FAIL}")
    return 1 if _FAIL else 0


if __name__ == "__main__":
    raise SystemExit(main())
