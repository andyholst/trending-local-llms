#!/usr/bin/env python3
"""Bounded reachability smoke for the four Hermes search targets.

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
  python3 scripts/smoke_search.py [--budget 90] [--backend nvidia|metal|cpu|amd] [--url-only]
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

import re
import sys as _sys
from pathlib import Path as _Path

# The scripts dir for the vocabulary import below. `__file__` is absent when a
# wiring test execs this file's source in a bare namespace (issue #858,
# tests/test_amd_backend.py::test_wiring_parity), so fall back to the cwd the
# target runs from — the repo root, where `scripts/` is.
_scripts = _Path(globals().get("__file__") or _Path.cwd() / "scripts").resolve().parent
if str(_scripts) not in _sys.path:
    _sys.path.insert(0, str(_scripts))
import query_vocab  # noqa: E402

# ONE vocabulary (issue #858): scripts/query_vocab.py owns the per-leg curated
# queries; the Makefile `_search-*` prompts get the same list through
# `$(<BACKEND>_KEYWORDS) = $(shell python3 scripts/query_vocab.py --print <backend>)`,
# so this probe provably scrapes what the bot actually searches.
BACKEND_KEYWORDS = {leg: query_vocab.curated(leg) for leg in query_vocab.LEGS}

# The yield audit (issue #858): does a query's page even CONTAIN a candidate?
# A post counts when it states a generation rate in a form posts actually use,
# or names a model this store ranks. `OK + zero candidates` is SILENT: the
# mirror answered and the VOCABULARY found nothing — the exact state the 2026-11-11
# refreshes sat in (seven empty cpu-*.json snapshots while nvidia/metal/amd
# captured 9/5/2) while every gate stayed green.
RATE_RE = re.compile(
    r"\b\d[\d,.]{0,6}\s*(?:tok|t|tokens?)/s\b"
    r"|\b\d[\d,.]{0,6}\s+(?:[a-z]+\s+){0,2}(?:tokens?|toks?)\s+per\s+second\b"
    r"|\b\d[\d,.]{0,6}\s*tps\b", re.I)
MODEL_RE = re.compile(
    r"\b(qwen3?\.\d+(?:-[a-z0-9]+)*|qwen\d*\s*\d*b|gemma[- ]\d+[ a-z0-9]*|"
    r"llama\s*\d|llama\.cpp|phi[- ]?\d|deepseek|mistral|strix halo|"
    r"\d+b\b)\b", re.I)


def page_yields(markdown: str) -> tuple[int, int]:
    """(rate-mentioning lines, model-naming lines) of a scraped page."""
    lines = [ln for ln in (markdown or "").splitlines() if ln.strip()]
    return (sum(1 for ln in lines if RATE_RE.search(ln)),
            sum(1 for ln in lines if MODEL_RE.search(ln)))

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

    Returns a dict: `status` (Firecrawl's own HTTP status), `ok` (its `success`
    flag), `upstream` (the status the TARGET answered with — Firecrawl answers
    200 of its own and reports the page's real status in
    `data.metadata.statusCode`) and `elapsed`. The upstream status is what makes
    a DOWN MIRROR visible: without it a 502 lightbrd looks exactly like a
    healthy 200, which is how this check stayed green for hours while every PR's
    `live-smoke` was red (issue #291)."""
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
            ok: object = None
            upstream: object = None
            try:
                payload: object = json.loads(raw)
            except json.JSONDecodeError:
                payload = None
            page = ""
            if isinstance(payload, dict):
                ok = payload.get("success")
                raw_data = payload.get("data")
                data: dict = raw_data if isinstance(raw_data, dict) else {}
                raw_meta = data.get("metadata")
                meta: dict = raw_meta if isinstance(raw_meta, dict) else {}
                for value in (meta.get("statusCode"), data.get("statusCode")):
                    if isinstance(value, (int, str)) and str(value).strip().isdigit():
                        upstream = int(value)
                        break
                page = data.get("markdown") or ""
            rate_hits, model_hits = page_yields(page)
            return {"status": resp.status, "ok": ok, "upstream": upstream,
                    "rate_hits": rate_hits, "model_hits": model_hits,
                    "elapsed": time.time() - t0}
    except _Budget:
        return {"status": 0, "ok": None, "upstream": None, "rate_hits": 0, "model_hits": 0,
                "elapsed": time.time() - t0}
    except urllib.error.HTTPError as e:
        return {"status": e.code, "ok": False, "upstream": None, "rate_hits": 0, "model_hits": 0,
                "elapsed": time.time() - t0}
    except Exception as e:  # noqa: BLE001 -- network/transport errors
        return {"status": 0, "ok": False, "upstream": None, "rate_hits": 0, "model_hits": 0,
                "elapsed": time.time() - t0}
    finally:
        signal.alarm(0)


# Transient outcomes worth ONE more bounded attempt: a client-side timeout
# (status 0 — an uncached Firecrawl scrape keeps running server-side and is
# usually cached a moment later), rate limiting, and 5xx. Auth/4xx failures
# (401/402/403/404) are real and are never retried.
RETRYABLE = {0, 408, 429, 500, 502, 503, 504}


def probe(keyword: str, api_key: str, budget: float, retries: int = 1,
          retry_wait: float = 2.0, scrape_fn=None, sleep_fn=time.sleep):
    """Scrape one query, retrying a transient failure up to `retries` times.
    EVERY attempt is still capped at `budget` seconds.

    Returns a dict: `label` (`OK` / `OUTAGE` / `FAIL` / `TIMEOUT`), `status`,
    `ok`, `upstream`, `elapsed` (of the last attempt) and `attempts`. `OUTAGE`
    is its own label because it is the one outcome that belongs to the TARGET:
    Firecrawl answered 200 + `success: true` for a page the MIRROR served as an
    error, so it is not retried (retrying a down mirror is noise) and it is not a
    smoke failure (issue #291)."""
    scrape_fn = scrape_fn or scrape
    attempts = 0
    while True:
        attempts += 1
        res = dict(scrape_fn(keyword, api_key, budget))
        status, ok = res["status"], res["ok"]
        upstream = res.get("upstream")
        res["attempts"] = attempts
        if status == 200 and ok:
            if isinstance(upstream, int) and upstream >= 500:
                res["label"] = "OUTAGE"
                return res
            if isinstance(upstream, int) and upstream >= 400:
                res["label"] = "FAIL"
                return res
            res["label"] = "OK"
            return res
        if attempts > retries or status not in RETRYABLE:
            res["label"] = "TIMEOUT" if status == 0 else "FAIL"
            return res
        sleep_fn(retry_wait)


def leg_verdict(total: int, missed: int) -> tuple[bool, str]:
    """Does ONE backend's probe result BLOCK the run, and what should the summary say?

    Rule (issue #258): a leg may only fail on a MAJORITY of its queries missing the budget. The
    probe is a pre-flight *reachability* check, not a completeness check — it samples its queries,
    so one slow query out of four means the mirror answered the rest. Reddening a whole scheduled
    run for that is a flake the maintainer learns to ignore, which costs the signal its value; an
    unreachable mirror misses ALL of them and must still fail loudly.

    Measured: scheduled run 38723723638 (`search (cpu)`) — three of four queries answered, the
    fourth was slow on both attempts, `aggregate` ran and succeeded, and the run was FAILURE
    anyway, indistinguishable from a dead source.

    Returns `(blocking, note)`: `blocking` is whether this leg reds the run; `note` explains a
    NON-blocking miss (empty when every query answered, so a clean leg says nothing).
    """
    if total <= 0 or missed == 0:
        return False, ""
    if missed * 2 > total:
        return True, f"{missed}/{total} queries did not answer within the budget"
    return False, (f"{missed}/{total} queries sampled slower than the budget "
                   f"(the rest answered, so the mirror is reachable)")


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--budget", type=int, default=90,
                    help="max seconds per backend query (default 90)")
    ap.add_argument("--backend", choices=list(BACKEND_KEYWORDS), help="test one backend only")
    ap.add_argument("--retries", type=int, default=1,
                    help="extra bounded attempts for a timed-out/429/5xx query (default 1; "
                         "each attempt still capped at --budget)")
    ap.add_argument("--retry-wait", type=float, default=2.0,
                    help="seconds to wait before a retry (default 2)")
    ap.add_argument("--url-only", action="store_true",
                    help="print the exact lightbrd URLs (no network) and exit")
    ap.add_argument("--key", default=os.environ.get("FIRECRAWL_API_KEY", ""),
                    help="Firecrawl API key (default $FIRECRAWL_API_KEY)")
    return ap.parse_args()


def main(probe_fn=None) -> int:
    """`probe_fn` is the probe seam: the ONE implementation is `probe` (the default), and a test
    passes its own to drive a whole leg offline. Nothing else is injected — the leg verdict, the
    summary lines and the exit code under test are the REAL ones."""
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
    probe_fn = probe_fn or probe
    outages = 0
    starved_blocking: list[str] = []
    majority_blocking: list[str] = []
    sampled: list[str] = []
    for b in backends:
        total = missed = 0
        answered = silent = 0
        for k in BACKEND_KEYWORDS[b]:
            total += 1
            res = probe_fn(k, args.key, args.budget, args.retries, args.retry_wait)
            tries = f" (attempt {res['attempts']})" if res["attempts"] > 1 else ""
            rate = int(res.get("rate_hits") or 0)
            model = int(res.get("model_hits") or 0)
            yield_note = ""
            if res["label"] == "OK":
                answered += 1
                if rate or model:
                    yield_note = f" yield: {rate} rate-posts, {model} model-posts"
                else:
                    silent += 1
                    yield_note = " yield: SILENT (no post states a rate or names a model)"
            print(f"[{b}] {res['label']} http={res['status']} success={res['ok']} "
                  f"upstream={res['upstream']} {res['elapsed']:.1f}s{tries}{yield_note}  "
                  f"{lightbrd_url(k)}")
            if res["label"] == "OUTAGE":
                outages += 1
            elif res["label"] != "OK":
                missed += 1
        # The yield gate (issue #858): a leg whose answered pages hold NO
        # candidate at all has a dead VOCABULARY, not a dead mirror — the CPU
        # leg sat starved precisely because every existing check stopped at
        # HTTP status. The gate names the leg and tells the maintainer to fix
        # the WORDS in scripts/query_vocab.py. (Scope: the CPU leg today; the
        # labels are printed for every leg so the next starved one is visible
        # before it needs an issue.)
        if b == "cpu" and answered and silent == answered:
            starved_blocking.append(
                f"{b}: starved curated vocabulary — all {answered} answered pages of "
                f"{len(BACKEND_KEYWORDS[b])} queries state NO generation rate and name "
                f"NO model. The mirror is reachable; the queries capture nothing "
                f"(issue #858). Fix the WORDS in scripts/query_vocab.py.")
        # The verdict is PER LEG (issue #258): a reachability probe samples its queries, so a
        # minority that missed the budget is a note, not a red run — while a majority, and so an
        # unreachable mirror (every query), still fails loudly.
        block, note = leg_verdict(total, missed)
        if block:
            majority_blocking.append(f"{b}: {note}")
        elif note:
            sampled.append(f"{b}: {note}")
    blocking = starved_blocking + majority_blocking
    if blocking:
        # Each rule's sentence is printed only for the rule that actually blocked
        # (issue #858): a dead source is a dead source, a silent leg is a dead
        # VOCABULARY — and neither is excused as a flake.
        rules = []
        if majority_blocking:
            rules.append("a MAJORITY of budget-missed queries is a dead or unreachable "
                         "source, not a flake (issue #258)")
        if starved_blocking:
            rules.append("an answered leg whose pages captured NOTHING is a starved "
                         "curated vocabulary, not a flake (issue #858)")
        print(f"\n[smoke] {len(blocking)} leg(s) failed: {'; '.join(blocking)}. "
              + "; ".join(rules) + ".")
        return 2
    if sampled:
        print(f"\n[smoke] SAMPLED: {'; '.join(sampled)}. Not a failure — a MINORITY of the "
              f"sampled queries was slow, which is a flake (issue #258).")
    if outages:
        # The mirror is down and Firecrawl is faithfully reporting it. That is
        # the TARGET's outage, not our smoke result, and it must be LOUD without
        # blocking every open PR (issue #291) — the old check called this state
        # "all backends returned HTTP 200", which is how a 502 mirror looked
        # green here while every PR's live-smoke was red.
        print(f"[smoke] OUTAGE: {outages} querie(s) came back as the TARGET's own error page "
              f"(upstream >= 500). The lightbrd mirror is DOWN — not a smoke failure, not a "
              f"blocked PR (issue #291). Re-run when it recovers.")
        return 0
    if not sampled:
        print(f"\n[smoke] all backends returned HTTP 200 within {args.budget}s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
