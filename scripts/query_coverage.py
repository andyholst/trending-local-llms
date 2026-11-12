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
                  query (`<id> vram ram context weights offload engine version`),
                  because a post can answer the first without stating any dimension
                  the store ranks as a gap; for the TOP-N trending models AND the
                  QUERY_AGED_N most-aged ones (a row that left the trending window
                  is re-queried too, or its gaps can never close);
  * the default   the coverage report ALSO names every gap dimension the data-gap
                  analysis ranks (`data_gap_analysis.DIMENSIONS`) that NO query asks
                  for — issue #460 measured `storage_offload` (59 models) and
                  `engine_min_version` (35) asked by nothing while every ranked model
                  had a throughput query; such a dimension is a query-set gap and
                  exits 1, never a silent line in the report.
  * the default   the coverage report: which of the TOP-N trending AND
                  QUERY_AGED_N most-aged models the hand-curated queries alone
                  reach, and which of them the full set (curated + derived)
                  names. Exit 1 when the full set misses one, so a gap is LOUD
                  and separable from "the query ran and found nothing" — a stale
                  or broken derivation cannot pass silently.

Exit codes: 0 = every ranked (trending + aged) model is named, 1 = at least one
is not, 2 = the store could not be read.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import update_trending as UT  # noqa: E402


def _load_store() -> dict:
    """The store `update_trending.py` itself reads (same path, same env hook).

    Uses `UT.load_store()` — the FLATTENED store with inline `engines[]` — so
    `newest_measurement_date()` (the aged-sample key) sees each model's
    measurement rows. A bare `json.loads` of the catalog would read no engines
    (the store is split across `data/models.{json,measurements.json,posts.json}`)
    and every aged model would look equally ageless."""
    return UT.load_store()


def report(store: dict, top_n: int, aged_n: int) -> str:
    """What the searches ask for, and what they would miss."""
    models = UT.trending_models(store)[:max(0, top_n)]
    aged = UT.aged_models(store, aged_n)
    curated = [q for group in UT.SEARCH_GROUPS.values() for q in group]
    full = UT.all_search_queries(store, top_n, aged_n)
    full_queries = [q for queries in full.values() for q in queries]

    def rows(models):
        for m in models:
            own = UT.model_query(m)
            foot = UT.footprint_query(m)
            from_curated = sorted({q for q in curated if UT.query_names_model(q, m)})
            named = sorted({q for q in full_queries if UT.query_names_model(q, m)})
            mark = "ok " if named else "MISS"
            yield (f"  {mark} {m.get('id', ''):<32} "
                   f"curated={', '.join(from_curated) or 'none':<46} "
                   f"derived={own} + footprint={foot}")

    lines = [f"top-{len(models)} trending + {len(aged)} most-aged vs the search queries", ""]
    lines += list(rows(models + aged))
    missing = [m for m in models + aged
               if not any(UT.query_names_model(q, m) for q in full_queries)]
    reachable_by_curated = [m for m in models + aged
                            if any(UT.query_names_model(q, m) for q in curated)]
    lines += [
        "",
        f"  queries: {len(curated)} curated across the {len(full)} legs + "
        f"{len(UT.derived_queries(store, top_n))} derived (throughput) + "
        f"{len(UT.footprint_queries(store, top_n))} footprint + "
        f"{len(UT.aged_derived_queries(store, aged_n))} aged (throughput) + "
        f"{len(UT.aged_footprint_queries(store, aged_n))} aged footprint, added to EACH leg "
        f"= {len(full_queries)} sent in total",
        f"  the hand-curated queries alone name {len(reachable_by_curated)}/{len(models + aged)} of "
        f"the {len(models)} trending + {len(aged)} aged",
        f"  the full set names {len(models + aged) - len(missing)}/{len(models + aged)}",
        f"  the aged sample (QUERY_AGED_N={UT.QUERY_AGED_N}) is the {len(aged)} most-aged "
        f"non-trending rows: a model that left the trending window is re-queried so its "
        "gaps can close and its stale figure never sits unrefreshed",
        "  the footprint queries ask the same models for EVERY dimension the data-gap",
        "  analysis ranks (weights / context / ram / offload / engine version): a",
        "  throughput answer can state none of them, which is why those gaps were",
        "  acquisition gaps (issue #460: offload and engine version outran the suffix)",
    ]
    not_asked = UT.dimensions_not_asked()
    if not_asked:
        lines += ["", "  DIMENSION GAP — no query asks for: " + ", ".join(not_asked),
                  "  a ranked gap no search asks for can never be closed by a search "
                  "(issue #460)."]
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
    ap.add_argument("--aged", type=int, default=UT.QUERY_AGED_N,
                    help=f"how many most-aged models must be named (default {UT.QUERY_AGED_N})")
    ap.add_argument("--json", action="store_true", help="machine-readable report")
    args = ap.parse_args(argv)

    # A guard that can be silenced is not a guard: --top 0 would check nothing
    # and exit 0, so a top of at least one trending model is required.
    if args.top < 1 or args.aged < 0:
        print(f"[query-coverage] --top must be >= 1 (got {args.top}) and --aged must be >= 0 "
              f"(got {args.aged}): a run that checks nothing can never report the gap",
              file=sys.stderr, flush=True)
        return 2

    try:
        store = _load_store()
    except Exception as err:  # noqa: BLE001
        print(f"[query-coverage] cannot read the store: {err}", file=sys.stderr, flush=True)
        return 2

    if args.queries:
        print(",".join(UT.derived_queries(store, args.top)
                       + UT.footprint_queries(store, args.top)
                       + UT.aged_derived_queries(store, args.aged)
                       + UT.aged_footprint_queries(store, args.aged)))
        return 0

    missing = UT.uncovered_models(store, args.top, args.aged)
    not_asked = UT.dimensions_not_asked()
    if args.json:
        print(json.dumps({
            "top": args.top,
            "aged": args.aged,
            "trending": [m.get("id") for m in UT.trending_models(store)[:max(0, args.top)]],
            "aged_models": [m.get("id") for m in UT.aged_models(store, args.aged)],
            "derived": UT.derived_queries(store, args.top),
            "footprint": UT.footprint_queries(store, args.top),
            "missing": [m.get("id") for m in missing],
            "dimensions_missing": not_asked,
        }, indent=2))
    else:
        print(report(store, args.top, args.aged), flush=True)
        if missing:
            print(f"[query-coverage] FAIL: {len(missing)} ranked model(s) no query names: "
                  + ", ".join(m.get("id", "?") for m in missing), file=sys.stderr, flush=True)
        if not_asked:
            print("[query-coverage] FAIL: the data-gap analysis ranks dimensions that NO "
                  "query asks for: " + ", ".join(not_asked)
                  + " — add the word to MODEL_FOOTPRINT_SUFFIX or ask the gap on the issue "
                  "(issue #460).", file=sys.stderr, flush=True)
    return 1 if (missing or not_asked) else 0


if __name__ == "__main__":
    raise SystemExit(main())
