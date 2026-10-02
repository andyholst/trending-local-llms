#!/usr/bin/env python3
"""Hermetic checks for scripts/smoke_search.py — the bounded reachability smoke
that replays the exact Firecrawl search the Makefile `make search-<backend>`
commands issue.

Rules these enforce (all offline):
  1. Every keyword list in smoke_search.py matches, verbatim, the keyword list
     written inside the matching Makefile `_search-<backend>` prompt. This is
     how we guarantee the smoke is "tested with the same search parameters".
  2. Every keyword is URL-encoded into a lightbrd search URL so the exact
     request the Hermes search agent would build is reproduced.
  3. There is exactly one keyword list per search leg (nvidia/metal/cpu/amd =
     update_trending.SEARCH_LEGS) — the removed `general` group must not come back.

Run standalone: python3 tests/test_smoke_search.py
"""
import math
import re
import sys
import urllib.parse
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MAKEFILE = ROOT / "Makefile"
sys.path.insert(0, str(ROOT / "scripts"))
from update_trending import SEARCH_LEGS  # noqa: E402

LEGS = tuple(SEARCH_LEGS)  # ('nvidia', 'metal', 'cpu', 'amd')
SMOKE = ROOT / "scripts" / "smoke_search.py"
SEARCH_NS = {}

_PASS = 0
_FAIL = 0


def check(name: str, cond: bool, detail: str = ""):
    global _PASS, _FAIL
    if cond:
        _PASS += 1
        print(f"  ok  {name}")
    else:
        _FAIL += 1
        print(f"  FAIL {name} {detail}")


def _load_smoke_backends() -> dict:
    # import smoke_search safely (it must not hit the network at import time)
    src = SMOKE.read_text()
    SEARCH_NS["BACKEND_KEYWORDS"] = None
    exec(compile(src, str(SMOKE), "exec"), SEARCH_NS)
    kw = SEARCH_NS["BACKEND_KEYWORDS"]
    assert isinstance(kw, dict), "BACKEND_KEYWORDS must be a dict"
    return kw


def _makefile_keywords(backend: str) -> list:
    """Extract the keyword list the Makefile `_search-<backend>` prompt embeds:
    'Search with <X> keywords ONLY (<k1>, <k2>, ...), one query at a time'."""
    text = MAKEFILE.read_text()
    target = "_search-" + backend + ":\n"
    body = text[text.index(target):]
    # prompt value is the quoted hermes -z "..." string
    m = re.search(r'keywords ONLY \((.*?)\), one query at a time', body)
    if not m:
        return []
    return [k.strip() for k in m.group(1).split(",")]


def main() -> int:
    print("smoke_search: Makefile keywords match the bounded smoke (same params)")
    smoke = _load_smoke_backends()

    for backend in LEGS:
        mk_kw = _makefile_keywords(backend)
        smoke_kw = smoke.get(backend, [])
        check(f"backend {backend}: smoke defines {len(smoke[backend])} keywords",
              backend in smoke and len(smoke[backend]) > 0)
        check(f"backend {backend}: smoke keywords match Makefile verbatim",
              sorted(smoke_kw) == sorted(mk_kw),
              f"drift: smoke={smoke_kw} makefile={mk_kw}")

    check("no 'general' backend resurrected", "general" not in smoke,
          f"got: {list(smoke)}")
    check("exactly the four search legs (nvidia/metal/cpu/amd)", sorted(smoke) == sorted(LEGS), f"got: {sorted(smoke)}")

    # URL building: each keyword -> exact lightbrd search URL (urlencoded q=)
    print("smoke_search: every keyword builds a lightbrd search URL")
    S = SEARCH_NS
    for backend, kws in smoke.items():
        for k in kws:
            url = S["lightbrd_url"](k)
            expect = "https://lightbrd.com/search?f=tweets&q=" + urllib.parse.quote(k)
            check(f"url: {backend}/{k!r} encodes to exact lightbrd URL",
                  url == expect, f"got {url}")

    # Retry policy (offline, scripted scrape results). The 3s cap per attempt
    # stays; a cache-miss timeout gets ONE more bounded attempt. Live CI flaked
    # on exactly this: a different uncached query timed out on each run while
    # the re-run of the same query answered in ~0.5s.
    print("smoke_search: bounded retry policy")
    probe = S["probe"]

    def scripted(results):
        seq = list(results)
        calls = []
        def fn(keyword, key, budget):
            calls.append(budget)
            return seq.pop(0)
        return fn, calls

    fn, calls = scripted([(0, None, 3.0), (200, True, 0.5)])
    r = probe("q", "k", 3, retries=1, scrape_fn=fn, sleep_fn=lambda s: None)
    check("retry: timeout then 200 -> OK on attempt 2", r[0] == "OK" and r[4] == 2, str(r))
    check("retry: every attempt keeps the 3s budget", calls == [3, 3], str(calls))

    fn, calls = scripted([(0, None, 3.0), (0, None, 3.0)])
    r = probe("q", "k", 3, retries=1, scrape_fn=fn, sleep_fn=lambda s: None)
    check("retry: timeout twice -> TIMEOUT after 2 attempts (no more)", r[0] == "TIMEOUT" and r[4] == 2, str(r))

    fn, calls = scripted([(401, False, 0.2)])
    r = probe("q", "k", 3, retries=1, scrape_fn=fn, sleep_fn=lambda s: None)
    check("retry: 401 is real (bad key) -> FAIL, never retried", r[0] == "FAIL" and r[4] == 1, str(r))

    fn, calls = scripted([(429, False, 0.1), (200, True, 0.4)])
    r = probe("q", "k", 3, retries=1, scrape_fn=fn, sleep_fn=lambda s: None)
    check("retry: 429 rate limit retried once", r[0] == "OK" and r[4] == 2, str(r))

    fn, calls = scripted([(0, None, 3.0)])
    r = probe("q", "k", 3, retries=0, scrape_fn=fn, sleep_fn=lambda s: None)
    check("retry: --retries 0 keeps the old single-attempt behaviour", r[0] == "TIMEOUT" and r[4] == 1, str(r))

    fn, calls = scripted([(200, True, 0.5)])
    r = probe("q", "k", 3, retries=1, scrape_fn=fn, sleep_fn=lambda s: None)
    check("retry: first-try OK makes exactly one request", r[0] == "OK" and len(calls) == 1, str(r))

    print(f"\nPASSED {_PASS} | FAILED {_FAIL}")
    return 0 if _FAIL == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
