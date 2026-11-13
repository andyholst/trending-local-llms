#!/usr/bin/env python3
"""ONE home for the curated per-leg search vocabulary (issue #858).

Before this file, the same keyword lists were hand-written in THREE places —
the four Makefile `_search-<backend>` prompts, `scripts/smoke_search.py`'s
probe list, and (near-duplicated) `update_trending.SEARCH_GROUPS` — and the
CPU leg's copy captured nothing for eight straight refreshes while every gate
stayed green, because no gate ever read the WORDS, only their HTTP status.

This module owns the prompt vocabulary only:
  * the Makefile's `_search-<backend>` prompts receive it through
    `$(<BACKEND>_KEYWORDS)` — `python3 scripts/query_vocab.py --print <backend>`;
  * `scripts/smoke_search.py` probes the exact same list (the live-smoke yield
    audit therefore probes what the bot actually searches).
`update_trending.SEARCH_GROUPS` stays the deliberately SMALL fetch sampling
(`make validate-fetch`'s budget) — its CPU entry is kept in sync here because
a sampled leg must sample what the leg really searches.

Changing a leg's vocabulary is editing ONE dict in the tree, reviewed like
code, verified by `make search-smoke`'s per-query CAPTURED/SILENT labels.
"""
from __future__ import annotations

LEGS = ("nvidia", "metal", "cpu", "amd")

# The bot's real vocabulary per leg. Every entry was proven against the
# lightbrd mirror the crawler reads (issue #858 audit); a query that surfaces
# no post stating a generation rate is a defect, not a keyword preference.
CURATED: dict[str, list[str]] = {
    "nvidia": [
        "rtx tokens per second llm",
        "rtx 3090/4090/5090 tokens per second",
        "rtx 3060 tokens per second",
        "rtx 4060 tokens per second",
        "rtx 4060 ti 16gb tokens per second",
        "rtx 4070 tokens per second",
        "8gb vram llm tokens per second",
        "16gb vram llm tokens per second",
        "bonsai 2 ternary",
        "freetoken gpu",
        "dflash speculative",
    ],
    "metal": [
        "mlx tokens per second",
        "mlx apple silicon",
        "mac m4 mlx local llm",
        "mlxfast bonsai",
        "tensorfold dflash mlx",
    ],
    # Rewritten by the issue #858 audit: the old set ANDed 5-6 words
    # ("llm tokens per second no gpu cpu"), named a GPU on a CPU query
    # ("local llm tokens per second gpu"), and the refresh store proved the
    # CPU leg captured zero models across its whole history. The new set is
    # short ANDs whose terms co-occur in real CPU-inference posts; the
    # leg's agent still filters non-CPU figures out (data-search skill).
    "cpu": [
        "cpu tokens per second",
        "no gpu tokens per second",
        "llama.cpp cpu tokens per second",
        "raspberry pi tokens per second",
    ],
    "amd": [
        "rx 7900 xtx tokens per second",
        "rx 9070 xt tokens per second",
        "rx 7600 tokens per second",
        "rx 6600 tokens per second",
        "rx 9060 xt tokens per second",
        "radeon 8gb vram llm tokens per second",
        "rocm tokens per second",
        "llama.cpp vulkan amd tokens",
        "strix halo tokens per second",
    ],
}


def curated(backend: str) -> list[str]:
    if backend not in CURATED:
        raise KeyError(f"unknown search leg {backend!r}; legs are {', '.join(LEGS)}")
    return list(CURATED[backend])


def prompt_string(backend: str) -> str:
    """The exact `keywords=(...)` payload for the `_search-<backend>` prompt."""
    return ", ".join(curated(backend))


def main(argv: list[str] | None = None) -> int:
    import argparse
    ap = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    ap.add_argument("--print", dest="leg", choices=LEGS, metavar="BACKEND",
                    help="print the leg's curated queries, comma-separated")
    ap.add_argument("--json", action="store_true", help="print the whole vocabulary as JSON")
    args = ap.parse_args(argv)
    if args.json:
        import json
        print(json.dumps(CURATED))
        return 0
    if args.leg:
        print(prompt_string(args.leg))
        return 0
    ap.error("pass --print <backend> or --json")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
