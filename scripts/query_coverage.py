#!/usr/bin/env python3
"""Do the searches ask for the models we rank? (issue #264)

The refresh's queries were a fixed keyword list that named no model: of the 24
queries in `SEARCH_GROUPS`, the ONE model-specific one named `qwen3.8-27b`, and
none named `Strata`. So every figure for the model topping the trend list arrived
incidentally, and the pipeline could not tell "no such measurement exists" from
"we never looked" — a higher figure upstream could never enter.

This is the CLI over the rule, whose ONE implementation lives in
`update_trending.py` (rule 6d) and is shared with the search prompts:

  * `--queries`   the derived model queries, comma-separated — exactly what the
                  `_search-<backend>` prompts append, so the searches ask for the
                  ranked models and not only the hardware keywords. Two per model:
                  the throughput query (`<id> tokens per second`) and the FOOTPRINT
                  query (`<id> vram ram context weights`), because a post can answer
                  the first without stating any dimension the store ranks as a gap;
  * the default   the coverage report: which of the top-N trending models the
                  hand-curated queries alone reach, and which of them the full
                  set (curated + derived) names. Exit 1 when the full set misses
                  one, so a gap is LOUD and separable from "the query ran and
                  found nothing" — a stale or broken derivation cannot pass
                  silently.

Exit codes: 0 = every top-N trending model is named, 1 = at least one is not,
2 = the store could not be read.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import update_trending as UT  # noqa: E402


def _load_store() -> dict:
    """The store `update_trending.py` itself reads (same path, same env hook)."""
    return json.loads(UT.DATA.read_text())


def report(store: dict, top_n: int) -> str:
    """What the searches ask for, and what they would miss."""
    models = UT.trending_models(store)[:max(0, top_n)]
    curated = [q for group in UT.SEARCH_GROUPS.values() for q in group]
    full = UT.all_search_queries(store, top_n)
    full_queries = [q for queries in full.values() for q in queries]

    lines = [f"top-{len(models)} trending models vs the search queries", ""]
    for m in models:
        own = UT.model_query(m)
        foot = UT.footprint_query(m)
        from_curated = sorted({q for q in curated if UT.query_names_model(q, m)})
        named = sorted({q for q in full_queries if UT.query_names_model(q, m)})
        mark = "ok " if named else "MISS"
        lines.append(f"  {mark} {m.get('id', ''):<32} "
                     f"curated={', '.join(from_curated) or 'none':<46} "
                     f"derived={own} + footprint={foot}")
    missing = [m for m in models if not any(UT.query_names_model(q, m) for q in full_queries)]
    reachable_by_curated = [m for m in models
                            if any(UT.query_names_model(q, m) for q in curated)]
    lines += [
        "",
        f"  queries: {len(curated)} curated across the {len(full)} legs + "
        f"{len(UT.derived_queries(store, top_n))} derived (throughput) + "
        f"{len(UT.footprint_queries(store, top_n))} footprint, added to EACH leg "
        f"= {len(full_queries)} sent in total",
        f"  the hand-curated queries alone name {len(reachable_by_curated)}/{len(models)} of "
        f"the top {len(models)}",
        f"  the full set names {len(models) - len(missing)}/{len(models)}",
        "  the footprint queries ask the same models for the dimensions the data-gap",
        "  analysis ranks (vram / ram / context / weights): a throughput answer can state",
        "  none of them, which is why those gaps were acquisition gaps",
    ]
    if missing:
        lines += ["", "  MISSED — no query names: " + ", ".join(m.get("id", "?") for m in missing),
                  "  a model the searches never ask for can never surface a higher figure "
                  "(issue #264)."]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    ap.add_argument("--queries", action="store_true",
                    help="print the derived model queries, comma-separated (what the prompts append)")
    ap.add_argument("--top", type=int, default=UT.QUERY_TOP_N,
                    help=f"how many trending models must be named (default {UT.QUERY_TOP_N})")
    ap.add_argument("--json", action="store_true", help="machine-readable report")
    args = ap.parse_args(argv)

    # A guard that can be silenced is not a guard: --top 0 would check nothing
    # and exit 0, so a top of at least one trending model is required.
    if args.top < 1:
        print(f"[query-coverage] --top must be >= 1 (got {args.top}): a run that checks "
              "nothing can never report the gap", file=sys.stderr, flush=True)
        return 2

    try:
        store = _load_store()
    except Exception as err:  # noqa: BLE001
        print(f"[query-coverage] cannot read the store: {err}", file=sys.stderr, flush=True)
        return 2

    if args.queries:
        print(",".join(UT.derived_queries(store, args.top)
                       + UT.footprint_queries(store, args.top)))
        return 0

    missing = UT.uncovered_models(store, args.top)
    if args.json:
        print(json.dumps({
            "top": args.top,
            "trending": [m.get("id") for m in UT.trending_models(store)[:max(0, args.top)]],
            "derived": UT.derived_queries(store, args.top),
            "footprint": UT.footprint_queries(store, args.top),
            "missing": [m.get("id") for m in missing],
        }, indent=2))
    else:
        print(report(store, args.top), flush=True)
        if missing:
            print(f"[query-coverage] FAIL: {len(missing)} trending model(s) no query names: "
                  + ", ".join(m.get("id", "?") for m in missing), file=sys.stderr, flush=True)
    return 1 if missing else 0


if __name__ == "__main__":
    raise SystemExit(main())
