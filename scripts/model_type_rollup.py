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


def parse_date(value) -> str:
    """ISO dates are lexical; shipped rows use YYYY-MM-DD."""
    return str(value or "")[:10]


def latest_date(measurements: dict) -> str:
    dates = [parse_date(r.get("date")) for rows in measurements.values()
             if isinstance(rows, list) for r in rows if isinstance(r, dict)]
    return max(dates) if dates else ""


def rollup(models: dict, measurements: dict, window_days: int = 0) -> dict[str, dict]:
    by_key: dict[str, list[dict]] = defaultdict(list)
    cutoff = ""
    if window_days > 0:
        newest = latest_date(measurements)
        if newest:
            from datetime import date, timedelta
            cutoff = (date.fromisoformat(newest) - timedelta(days=window_days)).isoformat()
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
                row_date = parse_date(row.get("date"))
                if cutoff and (not row_date or row_date < cutoff):
                    continue
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


def stale_candidates(models: dict, measurements: dict, window_days: int) -> list[tuple[str, str, int, str]]:
    """Models with real measurements but NONE in the trend window — the #1234 shape."""
    if window_days <= 0:
        return []
    newest = latest_date(measurements)
    if not newest:
        return []
    from datetime import date, timedelta
    cutoff = (date.fromisoformat(newest) - timedelta(days=window_days)).isoformat()
    by_key: dict[str, list[dict]] = defaultdict(list)
    for key, rows in measurements.items():
        if isinstance(rows, list):
            by_key[str(key)].extend(r for r in rows if isinstance(r, dict))
    gaps = []
    for model in models.get("models", []):
        rows = [r for key in measurement_keys(model) for r in by_key.get(key, [])]
        if not rows:
            continue
        in_window = [r for r in rows if parse_date(r.get("date")) >= cutoff]
        if not in_window:
            gaps.append((str(model.get("id") or "?"), str(model.get("name") or ""),
                         len(rows), max(parse_date(r.get("date")) for r in rows)))
    return sorted(gaps, key=lambda g: (-g[2], g[0]))


def model_freshness(models: dict, measurements: dict, model_id: str,
                    window_days: int = 7) -> list[str]:
    """Read-only per-model audit (issue #1249): why is a measured model absent from 🔥?"""
    newest = latest_date(measurements)
    cutoff = ""
    if newest and window_days > 0:
        from datetime import date, timedelta
        cutoff = (date.fromisoformat(newest) - timedelta(days=window_days)).isoformat()
    by_key: dict[str, list[dict]] = defaultdict(list)
    for key, rows in measurements.items():
        if isinstance(rows, list):
            by_key[str(key)].extend(r for r in rows if isinstance(r, dict))
    found = [m for m in models.get("models", []) if str(m.get("id") or "") == model_id]
    if not found:
        return [f"MODEL NOT FOUND id={model_id!r}; no store row, no trend verdict."]
    model = found[0]
    rows = [r for key in measurement_keys(model) for r in by_key.get(key, [])]
    if not rows:
        return [f"id={model_id} name={str(model.get('name') or '')!r} has NO measurements "
                f"— absent from 🔥 because there is no measurement row."]
    dates = [parse_date(r.get("date")) for r in rows if parse_date(r.get("date"))]
    latest = max(dates) if dates else "—"
    in_window = [r for r in rows if cutoff and parse_date(r.get("date")) >= cutoff]
    tps = [t for r in rows if (t := parse_tps(r.get("tps"))) is not None]
    engines = sorted({str(r.get("engine")) for r in rows if r.get("engine")})
    archs = sorted({str(r.get("hardware")) for r in rows if r.get("hardware")})
    own_id = str(model.get("id") or "")
    own_in_window = [r for key in measurement_keys(model) if key == own_id
                     for r in by_key.get(key, []) if cutoff and parse_date(r.get("date")) >= cutoff]
    alias_keys = sorted(k for k in measurement_keys(model) if k != own_id)
    if own_in_window:
        reason = "HAS in-window measurements under its OWN id; absence from 🔥 is a RANK/band decision."
    elif in_window:
        reason = (f"NO in-window rows under its own id; {len(in_window)} row(s) came ONLY from "
                  f"declared aliases {alias_keys}. Verify alias identity (#1213) before "
                  f"treating these as this model's posts; the README 🔥 gate counts source posts.")
    else:
        reason = (f"NO measurements in the {window_days}-day window "
                  f"(cutoff {cutoff or 'n/a'}); newest {latest}. Capture fresh posts "
                  f"(#1234), do not edit the store or the ranker.")
    lag = "—"
    if latest != "—" and newest:
        from datetime import date
        lag = str((date.fromisoformat(newest) - date.fromisoformat(latest)).days)
    return [
        f"id={model_id} name={str(model.get('name') or '')!r} group={group_of(str(model.get('type') or ''))}",
        f"newest_measurement={latest} days_behind_newest_store_date={lag} "
        f"(newest store date {newest})",
        f"historical_rows={len(rows)} in_window_rows={len(in_window)} "
        f"window_days={window_days} cutoff={cutoff or 'n/a'}",
        f"median_tps={format(statistics.median(tps), '.1f') if tps else '—'} "
        f"engines={len(engines)} architectures={len(archs)}",
        f"engines: {', '.join(engines[:12])}",
        f"VERDICT: {reason}",
    ]


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
    ap.add_argument("--window-days", type=int, default=0,
                    help="only rows at or after (newest stored date - N days); 0 = all history")
    ap.add_argument("--gaps", action="store_true",
                    help="also list models with measurements but none in the window (#1234 shape)")
    ap.add_argument("--model-id", default="",
                    help="read-only per-model freshness audit instead of the group table (#1249)")
    a = ap.parse_args(argv)
    models, measurements = load_stores(a.models, a.measurements)
    if a.model_id:
        print(f"# per-model freshness audit — {a.model_id} (issue #1249)")
        print("\n".join(model_freshness(models, measurements, a.model_id,
                                        a.window_days or 7)))
        return 0
    groups = rollup(models, measurements, a.window_days)
    cutoff = ""
    if a.window_days > 0 and latest_date(measurements):
        from datetime import date, timedelta
        cutoff = (date.fromisoformat(latest_date(measurements)) - timedelta(days=a.window_days)).isoformat()
    print(f"# model-type trending rollup — window: {a.window_days or 'all'} days "
          f"(rows >= {cutoff or 'all dates'})")
    print(render(groups))
    if a.gaps:
        gaps = stale_candidates(models, measurements, a.window_days or 7)
        print("")
        print(f"## models with measurements but none in the window ({len(gaps)})")
        for mid, name, total, newest in gaps[:25]:
            print(f"GAP id={mid} name={name!r} historical_rows={total} newest={newest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
