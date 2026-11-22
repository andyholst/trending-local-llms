#!/usr/bin/env python3
"""scripts/vetted_performance.py -- issue #1252.

A READ-ONLY, additive view of the highest measured t/s per VRAM band, with the
evidence attached (engine, hardware/VRAM, quant, dated source post, source count).
It does NOT write either store, reassign a shipped `type`, or change `sort_models`:
rule 3b forbids an agent reassigning values while #1235/#1213 await owner rulings,
and rule 2 forbids inventing a value the sources do not carry.

Deduplication key is (source_post, engine, hardware) so one promotional post cannot
manufacture a leaderboard. Rows with no source post are reported as UNVETTED and
excluded from the vetted top, never silently promoted.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import update_trending as U  # noqa: E402

BANDS = ((0, 8), (8, 16), (16, 24), (24, 32), (32, 4096))


def parse_tps(value) -> float | None:
    """Shipped `tps` is a string; take its first number, never invent one."""
    if isinstance(value, (int, float)):
        return float(value)
    m = re.search(r"\d+(?:\.\d+)?", str(value or ""))
    return float(m.group(0)) if m else None


def band_label(vram: float) -> str:
    for lo, hi in BANDS:
        if lo <= vram < hi:
            return f"{lo}-{hi}GB" if hi < 4096 else f"{lo}GB+"
    return "unknown"


def evidence_rows(models: dict, measurements: dict) -> list[dict]:
    by_id = {str(m.get("id") or ""): m for m in models.get("models", [])}
    seen: set[tuple] = set()
    source_posts: set[tuple[str, str]] = set()
    rows = []
    for key, entries in measurements.items():
        if not isinstance(entries, list):
            continue
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            tps = parse_tps(entry.get("tps"))
            vram = U.hardware_vram_gb(str(entry.get("hardware") or ""))
            source = str(entry.get("source_post") or "").strip()
            engine = str(entry.get("engine") or "").strip()
            hardware = str(entry.get("hardware") or "").strip()
            date = str(entry.get("date") or "")[:10]
            source_posts.add((str(key), source))
            dedup = (source, engine, hardware, str(key))
            if tps is None or vram is None or dedup in seen:
                continue
            seen.add(dedup)
            model = by_id.get(str(key))
            rows.append({
                "model_key": str(key),
                "model": model,
                "tps": tps,
                "vram": vram,
                "band": band_label(vram),
                "engine": engine,
                "hardware": hardware,
                "quant": str(entry.get("quant") or entry.get("quantization") or ""),
                "date": date,
                "source": source,
                "vetted": bool(source),
                "band_rank": U.model_band(model, U.now_utc()) if model else None,
                "posts_7d": ((model or {}).get("engagement") or {}).get("posts_7d", 0),
            })
    for row in rows:
        row["sources"] = sum(1 for key, src in source_posts
                             if key == row["model_key"] and src)
    return rows


def top_by_band(rows: list[dict], top_n: int = 5, vetted_only: bool = True) -> dict[str, list[dict]]:
    groups: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        if vetted_only and not row["vetted"]:
            continue
        groups[row["band"]].append(row)
    for band in groups:
        groups[band].sort(key=lambda r: (-r["tps"], r["date"], r["model_key"]))
        groups[band] = groups[band][:top_n]
    return dict(groups)


def render(groups: dict[str, list[dict]], unvetted: int) -> str:
    lines = [f"# vetted performance view (read-only, issue #1252)",
             f"unvetted rows excluded: {unvetted}",
             "",
             "| VRAM | t/s | model | engine | quant | measured | posts_7d | sources | README band |",
             "|---|---:|---|---|---|---|---:|---|---|"]
    for band in sorted(groups, key=lambda b: int(b.split("-")[0].rstrip("GB+"))):
        for row in groups[band]:
            name = str((row["model"] or {}).get("name") or row["model_key"])
            sources = row["source"].split()[:2]
            source_cell = (f"{', '.join(sources)} (n={row.get('sources', 0)})"
                           if sources else "UNVETTED")
            status = "🔥 eligible" if row["band_rank"] == 0 else f"band {row['band_rank']}"
            lines.append(
                f"| {band} | {row['tps']:.1f} | {name} | {row['engine']} | {row['quant'] or '—'} | "
                f"{row['date']} | {row['posts_7d']} | {source_cell} | {status} |")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--models", type=Path, default=ROOT / "data/models.json")
    ap.add_argument("--measurements", type=Path, default=ROOT / "data/measurements.json")
    ap.add_argument("--top", type=int, default=5)
    ap.add_argument("--include-unvetted", action="store_true")
    ap.add_argument("--vram-band", default="",
                    help="only one band, e.g. 16-24GB or 32GB+ (issue #1252)")
    ap.add_argument("--min-sources", type=int, default=1,
                    help="minimum independent source posts per measurement row (issue #1252)")
    a = ap.parse_args(argv)
    models = json.loads(a.models.read_text(encoding="utf-8"))
    measurements = json.loads(a.measurements.read_text(encoding="utf-8"))
    rows = evidence_rows(models, measurements)
    if a.min_sources > 1:
        rows = [r for r in rows if r["sources"] >= a.min_sources]
    groups = top_by_band(rows, a.top, vetted_only=not a.include_unvetted)
    if a.vram_band:
        wanted = a.vram_band.strip()
        known = ", ".join(sorted(groups))
        groups = {k: v for k, v in groups.items() if k == wanted}
        if not groups:
            print(f"no vetted rows for VRAM band {wanted!r}; known bands: {known or 'none'}")
            return 0
    print(render(groups, sum(1 for r in rows if not r["vetted"])))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
