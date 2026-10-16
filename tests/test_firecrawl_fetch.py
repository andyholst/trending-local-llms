#!/usr/bin/env python3
"""A refused Firecrawl scrape must be LOUD — never a "quiet search".

Measured on every PR's `live-smoke` job (2026-10-16, runs 38843768204 /
38854399980): `make validate-fetch` printed

    [error] Firecrawl->lightbrd search returned 0 model hits

after SIX seconds, with NO `[warn]` line for any of the four backends' queries.
A real scrape of ~24 queries cannot finish in six seconds, and `gather_x` warns
per query it could not fetch — so the fetches were not failing, they were
"SUCCEEDING": Firecrawl answers a refusal with HTTP 200 and
`{"success": false, "error": …}` (no credits, an invalid key, a banned target),
and the old client returned that JSON *as if it were a page*. Every query then
parsed to zero known models, printed nothing at all, and the check reported a
QUIET SEARCH for what was really a REFUSED FETCH — a diagnosis that points at
the mirror instead of at the credential/quota, on every PR, forever.

This drives the REAL client against a REAL local server (AGENTS.md rule 6m):
the function under test is never stubbed, the request it builds is asserted on,
and so is the loud failure.

Run:  python3 tests/test_firecrawl_fetch.py   or   make test
"""
from __future__ import annotations

import contextlib
import io
import json
import os
import subprocess
import sys
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import update_trending as UT  # noqa: E402

_PASS = 0
_FAIL = 0


def check(name, cond, detail: object = ""):
    global _PASS, _FAIL
    if cond:
        _PASS += 1
        print(f"  ok  {name}")
    else:
        _FAIL += 1
        print(f"  FAIL {name}" + (f"  [{detail}]" if detail else ""))


# ------------------------------------------------------------ the local API ---

class _Firecrawl(BaseHTTPRequestHandler):
    """A local stand-in for Firecrawl's scrape endpoint."""

    status = 200
    body = b"{}"
    seen: list[tuple[str, str, dict]] = []   # (path, Authorization, request JSON)

    def do_POST(self):  # noqa: N802 (BaseHTTPRequestHandler's name)
        n = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(n).decode("utf-8", "replace")
        try:
            sent = json.loads(raw or "{}")
        except json.JSONDecodeError:
            sent = {"__unparsed__": raw}
        type(self).seen.append((self.path, self.headers.get("Authorization", ""), sent))
        self.send_response(type(self).status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(type(self).body)))
        self.end_headers()
        self.wfile.write(type(self).body)

    def log_message(self, *a):  # keep the test output clean
        pass


def _serve(body, status: int = 200):
    _Firecrawl.status = status
    _Firecrawl.seen = []
    _Firecrawl.body = body if isinstance(body, bytes) else json.dumps(body).encode()
    httpd = HTTPServer(("127.0.0.1", 0), _Firecrawl)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    return httpd, f"http://127.0.0.1:{httpd.server_address[1]}/v1/scrape"


@contextlib.contextmanager
def _endpoint(url: str, key: str = "fc-test-key"):
    """Point the REAL client at the local server for the duration of the block.

    `FIRECRAWL_API_KEY` is set as well: `fetch_lightbrd` only takes the Firecrawl
    path when a key is present — without it the test would silently exercise the
    plain-urllib fallback (lightbrd answers 403) and prove nothing about the
    scrape client.
    """
    saved = {name: os.environ.get(name) for name in ("FIRECRAWL_SCRAPE_URL", "FIRECRAWL_API_KEY")}
    os.environ["FIRECRAWL_SCRAPE_URL"] = url
    if key:
        os.environ["FIRECRAWL_API_KEY"] = key
    try:
        yield
    finally:
        for name, value in saved.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value


def _raises(fn, *a, **k) -> str:
    """Run fn and return its error text, or '' when it did NOT raise."""
    try:
        fn(*a, **k)
    except Exception as e:  # noqa: BLE001 — the point of the test
        return f"{type(e).__name__}: {e}"
    return ""


# ------------------------------------------------------------------ the tests -

def test_a_successful_scrape_returns_the_page_and_builds_the_right_request():
    """The happy path, asserted on the request we actually send."""
    httpd, url = _serve({"success": True, "data": {"markdown": "# lightbrd\nQwen3.8 60 t/s\n"}})

    with _endpoint(url):
        page = UT.fetch_via_firecrawl("https://lightbrd.com/search?f=tweets&q=x", "fc-key-123")

    check("scrape ok: the markdown is returned", page.startswith("# lightbrd"), page[:40])
    check("scrape ok: exactly one request", len(_Firecrawl.seen) == 1, len(_Firecrawl.seen))
    path, auth, sent = _Firecrawl.seen[0]
    check("scrape ok: POSTed to the scrape path", path == "/v1/scrape", path)
    check("scrape ok: the key travels in the Authorization header",
          auth == "Bearer fc-key-123", auth)
    check("scrape ok: it asks for markdown (what the parser reads)",
          sent.get("formats") == ["markdown"], sent)
    check("scrape ok: it scrapes the lightbrd URL it was given",
          str(sent.get("url", "")).startswith("https://lightbrd.com/search"), sent.get("url"))
    httpd.shutdown()


def test_a_refused_scrape_raises_and_quotes_firecrawl():
    """HTTP 200 + success:false is a REFUSAL, not an empty page."""
    httpd, url = _serve({"success": False,
                         "error": "Payment Required: no credits remaining"})

    with _endpoint(url):
        err = _raises(UT.fetch_via_firecrawl, "https://lightbrd.com/search?q=x", "fc-key-123")

    check("refusal: it RAISES instead of returning a page", bool(err), err or "(returned)")
    check("refusal: it quotes Firecrawl's own reason",
          "no credits remaining" in err, err)
    check("refusal: the message says it was refused, not that the search was empty",
          "refused" in err.lower(), err)
    httpd.shutdown()


def test_a_200_without_a_page_raises():
    """A 'success' carrying no markdown and no html is still not a page."""
    httpd, url = _serve({"success": True, "data": {}})

    with _endpoint(url):
        err = _raises(UT.fetch_via_firecrawl, "https://lightbrd.com/search?q=x", "k")

    check("no page: it raises", bool(err), err or "(returned)")
    httpd.shutdown()


def test_a_non_json_body_raises():
    """An HTML error page behind a 200 must not be parsed as a scrape result."""
    httpd, url = _serve(b"<html>502 Bad Gateway</html>")

    with _endpoint(url):
        err = _raises(UT.fetch_via_firecrawl, "https://lightbrd.com/search?q=x", "k")

    check("non-json: it raises", bool(err), err or "(returned)")
    check("non-json: it says what came back", "non-JSON" in err, err)
    httpd.shutdown()


def test_a_refused_scrape_warns_per_query_instead_of_reporting_a_quiet_search():
    """The regression, end to end: the OLD client made a refused fetch look like
    a search that ran and found nothing (no warning at all)."""
    httpd, url = _serve({"success": False, "error": "Payment Required: no credits remaining"})
    store = {"models": [{"name": "Qwen3.8-27B"}, {"name": "Bonsai 2 27B"}]}
    captured = io.StringIO()

    with _endpoint(url), contextlib.redirect_stdout(captured):
        per_backend = UT.gather_x(store)

    out = captured.getvalue()
    hits = [t for group in per_backend.values() for t in group]
    check("refused fetch: the Firecrawl path was actually taken (not the urllib fallback)",
          len(_Firecrawl.seen) > 0, len(_Firecrawl.seen))
    check("refused fetch: no model hits were invented", hits == [], hits)
    check("refused fetch: every backend's queries warned LOUDLY", out.count("[warn]") >= len(per_backend),
          out[:200])
    check("refused fetch: the warning carries Firecrawl's reason",
          "no credits remaining" in out, out[:200])
    check("refused fetch: it is not reported as a quiet search",
          "0 model hits" not in out or "[warn]" in out, out[:200])
    httpd.shutdown()


def test_a_mirror_error_page_is_an_upstream_outage_not_a_page():
    """THE MEASURED FAILURE (2026-10-16): lightbrd.com's origin answered 502, so
    Cloudflare served `Error code 502`, and Firecrawl reported `success: true`
    with that page in `data.markdown` plus the real status in
    `data.metadata.statusCode`. Every query then "succeeded" with zero models and
    the live check blamed the query set."""
    httpd, url = _serve({"success": True, "data": {
        "markdown": "# Bad gatewayError code 502\n\nVisit [cloudflare.com](https://www.cloudflare.com/5xx-error-landing?utm_source=errorcode_502) for more information.",
        "metadata": {"statusCode": 502, "title": "lightbrd.com | 502: Bad gateway"},
    }})

    with _endpoint(url):
        err = _raises(UT.fetch_via_firecrawl, "https://lightbrd.com/search?f=tweets&q=x", "k")

    check("outage: it RAISES instead of returning the error page as a page", bool(err), err or "(returned)")
    check("outage: it is classified as an UPSTREAM outage, not a refusal",
          "UpstreamOutage" in err, err)
    check("outage: it names the status the TARGET answered", "502" in err, err)
    httpd.shutdown()


def test_an_error_page_without_a_reported_status_is_still_an_outage():
    """Cloudflare's landing link + "Error code 5NN" is proof enough on its own:
    a response that reports no upstream status must still not be parsed as a
    page of posts."""
    httpd, url = _serve({"success": True, "data": {
        "markdown": "# Bad gatewayError code 504\n",
    }})

    with _endpoint(url):
        err = _raises(UT.fetch_via_firecrawl, "https://lightbrd.com/search?q=x", "k")

    check("outage (no status): it raises", bool(err), err or "(returned)")
    check("outage (no status): classified as an outage", "UpstreamOutage" in err, err)
    httpd.shutdown()


def test_a_bot_wall_is_a_refusal_not_an_outage():
    """A 403 challenge must stay OUR problem (still red): it is the scrape that
    failed, not the mirror that is down."""
    httpd, url = _serve({"success": True, "data": {
        "markdown": "# Just a moment...",
        "metadata": {"statusCode": 403, "title": "Just a moment..."},
    }})

    with _endpoint(url):
        err = _raises(UT.fetch_via_firecrawl, "https://lightbrd.com/search?q=x", "k")

    check("bot wall: it raises", bool(err), err or "(returned)")
    check("bot wall: classified as a REFUSAL, so it keeps failing the check",
          "FirecrawlRefusal" in err, err)
    httpd.shutdown()


def test_a_healthy_page_is_never_read_as_an_outage():
    """The guard must not eat a real page: a post page that happens to be served
    with a 200 and no upstream error is returned as before."""
    page = "# lightbrd\nQwen3.8 60 t/s on an RTX 4090\n"
    httpd, url = _serve({"success": True, "data": {
        "markdown": page, "metadata": {"statusCode": 200, "title": "lightbrd"}}})

    with _endpoint(url):
        out = UT.fetch_via_firecrawl("https://lightbrd.com/search?q=x", "k")

    check("healthy: the page is returned verbatim", out == page, out[:40])
    httpd.shutdown()


def test_the_verdict_tells_an_outage_from_a_refusal_and_a_quiet_search():
    """The three failures that all read as `0 model hits` must be told apart —
    an outage is infrastructure (loud, not blocking), a refusal and a quiet
    search are ours (loud, blocking)."""
    stats: dict = {}
    httpd, url = _serve({"success": True, "data": {
        "markdown": "# Bad gatewayError code 502\n",
        "metadata": {"statusCode": 502}}})
    with _endpoint(url), contextlib.redirect_stdout(io.StringIO()):
        UT.gather_x({"models": [{"name": "Qwen3.8-27B"}]}, stats)
    httpd.shutdown()
    kind, code, lines = UT.zero_hit_verdict(stats)
    check("verdict: a full outage classifies as 'outage'", kind == "outage", stats)
    check("verdict: an outage does NOT block (exit 0)", code == 0, code)
    check("verdict: the outage lines say the mirror is DOWN, loudly",
          all("[outage]" in ln for ln in lines) and "DOWN" in lines[0], lines[0])
    check("verdict: every query is counted as an outage, none as a quiet search",
          stats["outage"] == stats["queries"] and stats["refused"] == 0 == stats["with_hits"],
          stats)

    refused: dict = {}
    httpd, url = _serve({"success": False, "error": "Payment Required: no credits remaining"})
    with _endpoint(url), contextlib.redirect_stdout(io.StringIO()):
        UT.gather_x({"models": [{"name": "Qwen3.8-27B"}]}, refused)
    httpd.shutdown()
    kind, code, lines = UT.zero_hit_verdict(refused)
    check("verdict: a refusal classifies as 'refused'", kind == "refused", refused)
    check("verdict: a refusal BLOCKS (exit 1)", code == 1, code)
    check("verdict: it says the mirror was never reached",
          any("never reached" in ln for ln in lines), lines)

    quiet = {"queries": 4, "with_hits": 0, "outage": 0, "refused": 0, "failed": 0}
    kind, code, lines = UT.zero_hit_verdict(quiet)
    check("verdict: a reachable mirror with no hits is a QUIET SEARCH",
          kind == "quiet" and code == 1, (kind, code))
    check("verdict: the quiet-search line names the query set to look at",
          any("QUIET SEARCH" in ln and "query set" in ln for ln in lines), lines)

    partial = {"queries": 4, "with_hits": 0, "outage": 2, "refused": 0, "failed": 0}
    kind, code, lines = UT.zero_hit_verdict(partial)
    check("verdict: a PARTIAL outage stays blocking (an outage is only excused when every query is one)",
          kind == "quiet" and code == 1, (kind, code))
    check("verdict: the partial-outage line explains the strictness",
          any("EVERY query" in ln for ln in lines), lines)


def test_a_transport_failed_query_does_not_unmask_a_proven_outage():
    """ONE unclassifiable query must not flip a proven mirror outage to `quiet`.

    THE REGRESSION (issue #296), measured on run 38862487215 after #292 landed:
    `queries=24 with-hits=0 outage=23 refused=0 failed=1` — 23 queries proved the
    target's own `502` error page, one hit a connection-level error, and the verdict
    came back `quiet` (exit 1) blaming the query set. `live-smoke` gates
    `auto-merge`, so every open PR was blocked again by a query that proves nothing
    about the mirror either way.
    """

    # Given  the exact outcome of that run: 23 classified outages and 1 transport failure
    real = {"queries": 24, "with_hits": 0, "outage": 23, "refused": 0, "failed": 1,
            "outage_status": ["the target answered HTTP 502 (lightbrd.com | 502: Bad gateway)"],
            "reasons": ["<urlopen error [Errno 111] Connection refused>"]}

    # When   the verdict is taken
    kind, code, lines = UT.zero_hit_verdict(real)

    # Then   it is the mirror's outage, it does NOT block, and it does not blame the query set
    check("verdict(#296): 23 outages + 1 transport failure is an OUTAGE", kind == "outage", (kind, code))
    check("verdict(#296): it does NOT block (exit 0) — a down mirror must not stop every PR",
          code == 0, code)
    check("verdict(#296): the lines name the DOWN mirror and never say QUIET SEARCH",
          "DOWN" in lines[0] and not any("QUIET SEARCH" in ln for ln in lines), lines[0])
    check("verdict(#296): the unclassifiable query is REPORTED, not hidden",
          any("1 further querie" in ln for ln in lines), lines)

    # And    a wholesale transport failure proves no outage, so it is never excused
    none_proven = {"queries": 24, "with_hits": 0, "outage": 0, "refused": 0, "failed": 24}
    kind, code, _ = UT.zero_hit_verdict(none_proven)
    check("verdict(#296): 0 outages PROVEN is never excused as an outage",
          kind == "quiet" and code == 1, (kind, code))

    # And    a mirror that ANSWERED real pages still blocks, even with a failure beside it
    answered = {"queries": 24, "with_hits": 0, "outage": 10, "refused": 0, "failed": 1}
    kind, code, _ = UT.zero_hit_verdict(answered)
    check("verdict(#296): a mirror that answered 13 real pages stays red",
          kind == "quiet" and code == 1, (kind, code))

    # And    a refusal still wins over an outage: that one is OUR configuration
    both = {"queries": 24, "with_hits": 0, "outage": 20, "refused": 1, "failed": 0,
            "reasons": ["Payment Required: no credits remaining"]}
    kind, code, _ = UT.zero_hit_verdict(both)
    check("verdict(#296): a refusal wins over an outage (ours, blocking)",
          kind == "refused" and code == 1, (kind, code))


def test_the_live_check_exits_zero_on_an_outage_and_non_zero_otherwise():
    """THE REGRESSION, at the level it actually hurt: the exit code of
    `make validate-fetch` (`python3 scripts/update_trending.py --fetch
    --require-hits --dry-run`), because that job gates qa-validate's
    `auto-merge` — so a red one stopped EVERY open PR at once (issue #291) while
    a quiet search must still be caught."""
    root = Path(__file__).resolve().parent.parent
    cli = [sys.executable, str(root / "scripts" / "update_trending.py"),
           "--fetch", "--require-hits", "--dry-run"]

    def run_against(payload):
        httpd, url = _serve(payload)
        env = dict(os.environ, FIRECRAWL_SCRAPE_URL=url, FIRECRAWL_API_KEY="fc-test-key")
        try:
            p = subprocess.run(cli, cwd=str(root), env=env, capture_output=True,
                               text=True, timeout=300)
        finally:
            httpd.shutdown()
        return p.returncode, p.stdout + p.stderr

    code, out = run_against({"success": True, "data": {
        "markdown": "# Bad gatewayError code 502\n\nVisit [cloudflare.com](https://www.cloudflare.com/5xx-error-landing?utm_source=errorcode_502)",
        "metadata": {"statusCode": 502, "title": "lightbrd.com | 502: Bad gateway"}}})
    check("live check on a DOWN mirror: exit 0 (not blocking a PR)", code == 0, f"exit={code}\n{out[-800:]}")
    check("live check on a DOWN mirror: it SAYS the mirror is down",
          "[outage]" in out and "DOWN" in out, out[-800:])
    check("live check on a DOWN mirror: it no longer claims a quiet search",
          "returned 0 model hits" not in out, out[-800:])
    check("live check: the outcome counts are printed (issue #293)",
          "fetch outcomes:" in out and "outage=" in out, out[-800:])

    code, out = run_against({"success": False, "error": "Payment Required: no credits remaining"})
    check("live check on a REFUSED scrape: still exit non-zero", code != 0, f"exit={code}\n{out[-500:]}")
    check("live check on a REFUSED scrape: it names the refusal",
          "REFUSED" in out and "no credits remaining" in out, out[-500:])

    code, out = run_against({"success": True, "data": {
        "markdown": "# lightbrd\nnothing to see here\n", "metadata": {"statusCode": 200}}})
    check("live check on a healthy mirror with no hits: still exit non-zero",
          code != 0, f"exit={code}\n{out[-500:]}")
    check("live check on a healthy mirror with no hits: it says QUIET SEARCH",
          "QUIET SEARCH" in out, out[-500:])


def test_the_endpoint_seam_defaults_to_firecrawl():
    """The seam exists for tests only: with no override the client targets the
    real Firecrawl API."""
    saved = os.environ.pop("FIRECRAWL_SCRAPE_URL", None)
    try:
        check("seam: the default is Firecrawl's real v1 scrape endpoint",
              UT.DEFAULT_FIRECRAWL_SCRAPE_URL == "https://api.firecrawl.dev/v1/scrape",
              UT.DEFAULT_FIRECRAWL_SCRAPE_URL)
        check("seam: with no override the client does NOT point somewhere else",
              UT.firecrawl_scrape_url() == UT.DEFAULT_FIRECRAWL_SCRAPE_URL,
              UT.firecrawl_scrape_url())
        check("seam: an empty override does not blank the endpoint",
              _endpoint_defaults_to_firecrawl_with_empty_env())
    finally:
        if saved is not None:
            os.environ["FIRECRAWL_SCRAPE_URL"] = saved


def _endpoint_defaults_to_firecrawl_with_empty_env() -> bool:
    os.environ["FIRECRAWL_SCRAPE_URL"] = "  "
    try:
        return UT.firecrawl_scrape_url() == UT.DEFAULT_FIRECRAWL_SCRAPE_URL
    finally:
        os.environ.pop("FIRECRAWL_SCRAPE_URL", None)


def main() -> int:
    print("firecrawl fetch client: a refusal is loud, never a quiet search")
    test_a_successful_scrape_returns_the_page_and_builds_the_right_request()
    test_a_refused_scrape_raises_and_quotes_firecrawl()
    test_a_200_without_a_page_raises()
    test_a_non_json_body_raises()
    test_a_refused_scrape_warns_per_query_instead_of_reporting_a_quiet_search()
    test_a_mirror_error_page_is_an_upstream_outage_not_a_page()
    test_an_error_page_without_a_reported_status_is_still_an_outage()
    test_a_bot_wall_is_a_refusal_not_an_outage()
    test_a_healthy_page_is_never_read_as_an_outage()
    test_the_verdict_tells_an_outage_from_a_refusal_and_a_quiet_search()
    test_a_transport_failed_query_does_not_unmask_a_proven_outage()
    test_the_live_check_exits_zero_on_an_outage_and_non_zero_otherwise()
    test_the_endpoint_seam_defaults_to_firecrawl()
    print(f"\nPASSED {_PASS} | FAILED {_FAIL}")
    return 1 if _FAIL else 0


if __name__ == "__main__":
    raise SystemExit(main())
