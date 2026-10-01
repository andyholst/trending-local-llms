#!/usr/bin/env python3
"""Bounded reachability smoke for the three Hermes search targets.

Replays the EXACT same Firecrawl scrape call that the Makefile ``_search-{backend}``
prompts issue -- POST https://api.firecrawl.dev/v1/scrape with
{"url": "https://lightbrd.com/search?f=tweets&q=<urlencoded>", "formats": ["markdown"]}
against the lightbrd.com mirror -- capped at ``--budget`` seconds per backend query.

Exits 0 only if EVERY backend got a successful scrape (HTTP 200 + Firecrawl
success:true) within budget. A query that exceeds ``--budget`` is reported as
TIMEOUT and makes the run FAIL (exit 2) -- the scrape genuinely takes tens of
seconds, so a 1-3s budget is expected to time out before any 200.

The per-backend keyword lists below must stay identical to the Makefile
``_search-{backend}`` prompts; the hermetic test ``_make_search_keywords_match``
(scripts/smoke_search.py) cross-checks them so one side cannot drift.

Usage:
  python3 scripts/smoke_search.py [--budget 90] [--backend nvidia|metal|cpu] [--url-only]
"""
import argparse
import json
import os
import signal
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

# Keep in sync with the Makefile _search-* prompts (verified by test_search_keywords_match).
BACKEND_KEYWORDS = {
    "nvidia": [
        "rtx tokens per second llm",
        "rtx 3090/4090/5090 tokens per second",
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
    "cpu": [
        "llm tokens per second no gpu cpu",
        "llama.cpp cpu only",
        "raspberry pi llm tokens per second",
        "local llm cpu",
    ],
}

SCRAPE_URL = "https://api.firecrawl.dev/v1/scrape"


def lightbrd_url(keyword: str) -> str:
    return "https://lightbrd.com/search?f=tweets&q=" + urllib.parse.quote(keyword)


class _Budget(Exception):
    pass


def _arm_budget(seconds: float) -> None:
    def _raise(_sig, _frm):  # noqa: ARG001
        raise _Budget()
    signal.signal(signal.SIGALRM, _raise)
    signal.alarm(max(1, int(seconds)))


def scrape(keyword: str, api_key: str, budget: float):
    """One Firecrawl scrape of the Makefile-exact lightbrd URL, bounded by budget.
    Returns (http_status, firecrawl_success, elapsed)."""
    body = json.dumps({
        "url": lightbrd_url(keyword),
        "formats": ["markdown"],
        "onlyMainContent": False,
    }).encode("utf-8")
    req = urllib.request.Request(
        SCRAPE_URL,
        data=body,
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"},
        method="POST",
    )
    t0 = time.time()
    _arm_budget(budget)
    try:
        with urllib.request.urlopen(req, timeout=max(budget, 120)) as resp:
            raw = resp.read().decode("utf-8", "replace")
            ok = None
            try:
                ok = json.loads(raw).get("success")
            except json.JSONDecodeError:
                pass
            return resp.status, ok, time.time() - t0
    except _Budget:
        return 0, None, time.time() - t0  # signal = timed out, no HTTP status
    except urllib.error.HTTPError as e:
        return e.code, False, time.time() - t0
    except Exception as e:  # noqa: BLE001 -- network/transport errors
        return 0, False, time.time() - t0
    finally:
        signal.alarm(0)


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--budget", type=int, default=90,
                    help="max seconds per backend query (default 90)")
    ap.add_argument("--backend", choices=list(BACKEND_KEYWORDS), help="test one backend only")
    ap.add_argument("--url-only", action="store_true",
                    help="print the exact lightbrd URLs (no network) and exit")
    ap.add_argument("--key", default=os.environ.get("FIRECRAWL_API_KEY", ""),
                    help="Firecrawl API key (default $FIRECRAWL_API_KEY)")
    return ap.parse_args()


def main() -> int:
    args = parse_args()
    if args.url_only:
        for b, kw in BACKEND_KEYWORDS.items():
            print(f"[{b}]")
            for k in kw:
                print("  " + lightbrd_url(k))
        return 0
    if not args.key:
        print("[error] FIRECRAWL_API_KEY not set", file=sys.stderr)
        return 1

    backends = [args.backend] if args.backend else list(BACKEND_KEYWORDS)
    fails = 0
    for b in backends:
        for k in BACKEND_KEYWORDS[b]:
            status, ok, elapsed = scrape(k, args.key, args.budget)
            label = "OK" if (status == 200 and ok) else ("TIMEOUT" if status == 0 else "FAIL")
            print(f"[{b}] {label} http={status} success={ok} {elapsed:.1f}s  {lightbrd_url(k)}")
            if label != "OK":
                fails += 1
    if fails:
        print(f"\n[smoke] {fails} request(s) did NOT return HTTP 200. "
              f"Budget {args.budget}s may be too low (Firecrawl scrape needs ~10-60s).")
        return 2
    print(f"\n[smoke] all backends returned HTTP 200 within {args.budget}s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
