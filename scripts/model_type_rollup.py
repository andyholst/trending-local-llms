#!/usr/bin/env python3
"""scripts/model_type_rollup.py -- issue #1246.

An additive, READ-ONLY rollup: derive a `type_group` from each model's shipped
`type` label and join data/measurements.json by model id (plus the model's declared
measurement aliases). Nothing is written to either store — rule 3b forbids an agent
reassigning shipped values while issue #1235 awaits the owner's persistence ruling.
"""
from __future__ import annotations

import argparse
import json
import statistics
from collections import defaultdict
from pathlib import Path

# The 13 labels measured on master, mapped once (issue #1235). A NEW label is
# reported as `unknown`, never silently bucketed into another group.
TYPE_GROUPS: dict[str, str] = {
    "LLM (MoE)": "moe",
    "MoE LLM": "moe",
    "LLM (MoE, VLM)": "vlm",
    "LLM (ternary, VLM)": "vlm",
    "MoE multimodal LLM": "vlm",
    "VLM": "vlm",
    "LLM (ternary)": "ternary",
    "LLM (adapter over Qwen3.8-27B)": "adapter",
    "Decision LLM (MLX port)": "llm",
    "LLM (4-bit)": "llm",
    "LLM (edge)": "llm",
    "LLM": "llm",
    "GGUF": "format-only",
}


def group_of(label: str) -> str:
    return TYPE_GROUPS.get(label, "unknown")


def parse_tps(value) -> float | None:
    """Shipped `tps` is a STRING ("40", "2.5", sometimes "40-50"); take its first number."""
    import re
    if isinstance(value, (int, float)):
        return float(value)
    m = re.search(r"\d+(?:\.\d+)?", str(value or ""))
    return float(m.group(0)) if m else None


def load_stores(models_path: Path, measurements_path: Path) -> tuple[dict, dict]:
    models = json.loads(models_path.read_text(encoding="utf-8"))
    measurements = json.loads(measurements_path.read_text(encoding="utf-8"))
    return models, measurements


def measurement_keys(model: dict) -> set[str]:
    keys = {str(model.get("id") or "")}
    keys.update(str(x) for x in (model.get("measurement_model_aliases") or []))
    return {k for k in keys if k}


def rollup(models: dict, measurements: dict) -> dict[str, dict]:
    by_key: dict[str, list[dict]] = defaultdict(list)
    for key, rows in measurements.items():
        if isinstance(rows, list):
            by_key[str(key)].extend(r for r in rows if isinstance(r, dict))
    groups: dict[str, dict] = defaultdict(
        lambda: {"models": 0, "measurements": 0, "tps": [], "engines": set(),
                 "hardware": set(), "dates": [], "unknown_labels": set()})
    for model in models.get("models", []):
        label = str(model.get("type") or "")
        g = group_of(label)
        bucket = groups[g]
        bucket["models"] += 1
        if g == "unknown":
            bucket["unknown_labels"].add(label)
        for key in measurement_keys(model):
            for row in by_key.get(key, []):
                bucket["measurements"] += 1
                parsed = parse_tps(row.get("tps"))
                if parsed is not None:
                    bucket["tps"].append(parsed)
                if row.get("engine"):
                    bucket["engines"].add(str(row["engine"]))
                if row.get("hardware"):
                    bucket["hardware"].add(str(row["hardware"]))
                if row.get("date"):
                    bucket["dates"].append(str(row["date"]))
    return dict(groups)


def render(groups: dict[str, dict]) -> str:
    lines = ["| type_group | models | measurements | engines | architectures | newest | median t/s |",
             "|---|---:|---:|---:|---:|---|---:|"]
    for name in sorted(groups):
        b = groups[name]
        median = f"{statistics.median(b['tps']):.1f}" if b["tps"] else "—"
        newest = max(b["dates"]) if b["dates"] else "—"
        lines.append(
            f"| `{name}` | {b['models']} | {b['measurements']} | {len(b['engines'])} | "
            f"{len(b['hardware'])} | {newest} | {median} |")
    unknown = groups.get("unknown", {}).get("unknown_labels")
    if unknown:
        lines.append("")
        lines.append("UNKNOWN labels (report, do not bucket): " + ", ".join(sorted(unknown)))
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--models", type=Path, default=Path("data/models.json"))
    ap.add_argument("--measurements", type=Path, default=Path("data/measurements.json"))
    a = ap.parse_args(argv)
    models, measurements = load_stores(a.models, a.measurements)
    print(render(rollup(models, measurements)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
