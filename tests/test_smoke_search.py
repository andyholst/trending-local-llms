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
  4. An UPSTREAM error page (Firecrawl reports `success: true` for a page the
     MIRROR served as a 502) is its own `OUTAGE` label: never retried, and not a
     smoke failure — while a 403 bot wall stays OUR failure (issue #291).

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


def test_an_upstream_error_page_is_its_own_outage_label():
    """A DOWN MIRROR must not read as a healthy smoke (issue #291).

    Measured 2026-10-16: lightbrd.com's origin answered 502, Firecrawl answered
    `200 {"success": true, ..., "metadata": {"statusCode": 502}}` and this check
    printed "all backends returned HTTP 200" — a green that said the opposite of
    the truth, while every PR's `live-smoke` was red on the same mirror. The
    upstream status now decides: `>= 500` is its own OUTAGE label (never retried —
    retrying a down mirror is noise — and not a smoke failure), while a 403 bot
    wall stays a FAIL.
    """
    _load_smoke_backends()
    probe = SEARCH_NS["probe"]

    def scripted(status, ok, upstream):
        calls: list[float] = []

        def fn(keyword, key, budget):
            calls.append(budget)
            return {"status": status, "ok": ok, "upstream": upstream, "elapsed": 0.3}
        return fn, calls

    fn, calls = scripted(200, True, 502)
    r = probe("q", "k", 3, retries=1, scrape_fn=fn, sleep_fn=lambda s: None)
    assert r["label"] == "OUTAGE", r
    assert r["upstream"] == 502 and r["status"] == 200, r
    assert len(calls) == 1, f"a down mirror must not be retried: {calls}"

    fn, _ = scripted(200, True, 200)
    assert probe("q", "k", 3, retries=1, scrape_fn=fn, sleep_fn=lambda s: None)["label"] == "OK"

    fn, _ = scripted(200, True, 403)
    assert probe("q", "k", 3, retries=1, scrape_fn=fn, sleep_fn=lambda s: None)["label"] == "FAIL"


def test_one_slow_query_does_not_red_a_leg(S: dict):
    """#258: the verdict is PER LEG, and only a MAJORITY of missed queries may red it.

    Measured: scheduled run 38723723638 — `search (cpu)` answered three of four queries, the
    fourth was slow on BOTH attempts, `aggregate` ran and succeeded, and the run was FAILURE
    anyway — indistinguishable, to whoever reads the notification, from a dead source.

    RED on the pre-change code: there was no decision function at all (the probe counted every
    miss globally and exited 2 on the first one), so these checks could not exist.
    """
    from typing import Callable, cast

    fn = S.get("leg_verdict")
    check("leg: the probe exposes ONE per-leg decision function", callable(fn), str(fn))
    if not callable(fn):
        return
    verdict = cast("Callable[..., tuple[bool, str]]", fn)

    # Given one leg of four queries with ONE slow one
    blocking, note = verdict(total=4, missed=1)

    # Then  it does NOT red the run, and the summary says why
    check("leg: 1 of 4 missed does NOT block the run", blocking is False, f"blocking={blocking}")
    check("leg: the note names the flake and the ratio", "1/4" in note and "sampled" in note, note)

    # And  a MAJORITY missing still fails loudly (an unreachable mirror misses all of them)
    for total, missed in ((4, 4), (4, 3), (3, 2), (5, 3), (1, 1)):
        blocking, note = verdict(total=total, missed=missed)
        check(f"leg: {missed} of {total} missed DOES block", blocking is True, note)

    # And  a clean leg says nothing, and an exact half is not a majority
    check("leg: a clean leg is silent", verdict(4, 0) == (False, ""), str(verdict(4, 0)))
    check("leg: an exact half does not block (not a majority)", verdict(4, 2)[0] is False,
          str(verdict(4, 2)))


def test_the_run_summary_distinguishes_a_flake_from_a_dead_source(S: dict):
    """#258's second acceptance criterion: "the distinction is visible in the run: a leg that only
    *sampled* slower than the budget says so in its summary rather than going red".

    Drives the REAL `main()` through its `probe_fn` seam over one leg (cpu), so the leg verdict,
    the summary lines and the exit code are all production code.
    """
    import contextlib
    import inspect
    import io

    if "probe_fn" not in inspect.signature(S["main"]).parameters:
        check("run: main() exposes the probe seam", False, "no probe_fn parameter on main()")
        return
    check("run: main() exposes the probe seam", True)

    cpu = S["BACKEND_KEYWORDS"]["cpu"]
    good = {"label": "OK", "status": 200, "ok": True, "upstream": 200, "elapsed": 0.3, "attempts": 1}
    slow = {"label": "TIMEOUT", "status": 0, "ok": None, "upstream": None, "elapsed": 3.0, "attempts": 2}

    def run(slow_count: int):
        calls = {"n": 0}

        def probe_fn(*_a, **_kw):
            calls["n"] += 1
            return dict(slow if calls["n"] <= slow_count else good)

        out = io.StringIO()
        argv = sys.argv
        sys.argv = ["smoke_search.py", "--backend", "cpu", "--key", "test"]
        try:
            with contextlib.redirect_stdout(out):
                rc = S["main"](probe_fn=probe_fn)
        finally:
            sys.argv = argv
        return rc, out.getvalue()

    # Given one leg of four queries with ONE slow one
    rc, text = run(slow_count=1)
    # Then  the run stays GREEN and its summary says it only sampled
    check("run: a flaky leg exits 0 (not FAILURE)", rc == 0, f"rc={rc}")
    check("run: the summary says SAMPLED", "SAMPLED" in text, text[-300:])
    check("run: it names the ratio", f"1/{len(cpu)}" in text, text[-300:])
    check("run: it does NOT claim every backend was 200", "all backends returned HTTP 200" not in text,
          text[-200:])

    # And  a MAJORITY slow (an unreachable mirror shape) still FAILS loudly
    rc, text = run(slow_count=len(cpu))
    check("run: a dead source still exits 2", rc == 2, f"rc={rc}")
    check("run: it says the source is unreachable, not a flake",
          "MAJORITY" in text and "not a flake" in text, text[-300:])


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
    test_one_slow_query_does_not_red_a_leg(S)
    test_the_run_summary_distinguishes_a_flake_from_a_dead_source(S)
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
            status, ok, upstream, elapsed = seq.pop(0)
            return {"status": status, "ok": ok, "upstream": upstream, "elapsed": elapsed}
        return fn, calls

    def run(results, retries=1):
        fn, calls = scripted(results)
        return probe("q", "k", 3, retries=retries, scrape_fn=fn, sleep_fn=lambda s: None), calls

    r, calls = run([(0, None, None, 3.0), (200, True, 200, 0.5)])
    check("retry: timeout then 200 -> OK on attempt 2", r["label"] == "OK" and r["attempts"] == 2, str(r))
    check("retry: every attempt keeps the 3s budget", calls == [3, 3], str(calls))

    r, _ = run([(0, None, None, 3.0), (0, None, None, 3.0)])
    check("retry: timeout twice -> TIMEOUT after 2 attempts (no more)",
          r["label"] == "TIMEOUT" and r["attempts"] == 2, str(r))

    r, _ = run([(401, False, None, 0.2)])
    check("retry: 401 is real (bad key) -> FAIL, never retried",
          r["label"] == "FAIL" and r["attempts"] == 1, str(r))

    r, _ = run([(429, False, None, 0.1), (200, True, 200, 0.4)])
    check("retry: 429 rate limit retried once", r["label"] == "OK" and r["attempts"] == 2, str(r))

    r, _ = run([(0, None, None, 3.0)], retries=0)
    check("retry: --retries 0 keeps the old single-attempt behaviour",
          r["label"] == "TIMEOUT" and r["attempts"] == 1, str(r))

    r, calls = run([(200, True, 200, 0.5)])
    check("retry: first-try OK makes exactly one request", r["label"] == "OK" and len(calls) == 1, str(r))

    # The outage: Firecrawl answers 200 + success:true while the MIRROR served a
    # 502 error page. That is the target's failure, so it is its own label, it is
    # never retried (retrying a down mirror is noise) and it does not fail the
    # smoke — the old check called this state "all backends returned HTTP 200",
    # which is how a 502 mirror stayed green here while every PR's live-smoke was
    # red (`make validate-fetch`, measured 2026-10-16).
    r, calls = run([(200, True, 502, 0.7)])
    check("outage: upstream 502 -> OUTAGE label", r["label"] == "OUTAGE", str(r))
    check("outage: the upstream status is carried, not hidden behind Firecrawl's 200",
          r["status"] == 200 and r["upstream"] == 502, str(r))
    check("outage: NOT retried (one request)", len(calls) == 1, str(calls))

    r, _ = run([(200, True, 200, 0.5)])
    check("healthy: upstream absent -> still OK (a real page carries no upstream error)",
          r["label"] == "OK", str(r))

    r, _ = run([(200, True, 403, 0.5)])
    check("bot wall: upstream 403 -> FAIL, not excused as an outage",
          r["label"] == "FAIL", str(r))

    # The same rule as a pytest-collectable test (the spec's `- **Test:**` line
    # names it), so it is not covered only by this script's runner.
    try:
        test_an_upstream_error_page_is_its_own_outage_label()
        check("outage: an upstream error page is its own OUTAGE label, never retried (pytest path)", True)
    except AssertionError as e:
        check("outage: an upstream error page is its own OUTAGE label, never retried (pytest path)",
              False, str(e))

    print(f"\nPASSED {_PASS} | FAILED {_FAIL}")
    return 0 if _FAIL == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
