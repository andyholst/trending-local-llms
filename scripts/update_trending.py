#!/usr/bin/env python3
"""Update the trending-local-llms data store and regenerate README.md.

Behavior (see AGENTS.md):
  - Fetch X posts mentioning local LLMs via the lightbrd.com mirror.
  - Merge new engagement + per-engine t/s into data/models.json.
  - Sort: trending (last 7 days) -> recent (last 30 days) -> stale (>30 days).
  - Regenerate README.md from the store.
  - If the source is unreachable, preserve last-known data and exit 0 with a
    warning (never blank data). Set STRICT=1 to exit non-zero on fetch failure.

Run:  python3 scripts/update_trending.py [--dry-run] [--no-fetch]
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from hf_id import normalise as normalise_hf  # noqa: E402  (one HF-id definition)
# Allow tests to run the make targets against a small fixture in a temp dir
# instead of the real data/ tree. When set, all data paths resolve under it.
_DATA_DIR = Path(os.environ.get("TRENDING_DATA_DIR", str(ROOT / "data")))
DATA = _DATA_DIR / "models.json"
README = Path(os.environ.get("TRENDING_README", str(ROOT / "README.md")))
SCRAPE_DIR = _DATA_DIR / "scrape"
SNAPSHOT_DIR = _DATA_DIR / "snapshots"
RAW_DIR = _DATA_DIR / "raw"

# Four backend search groups (last-3-day window), refined by live probing (Sep 28
# 2026; AMD Oct 2 2026) for maximum matches per backend. NVIDIA/CUDA and
# Apple/Metal carry most of the signal; CPU is sparse on X (offload-capable
# engines like FreeToken and llama.cpp-cpu surface under the CUDA/engine
# queries); AMD/ROCm posts name the card (RX 7900 XTX, RX 9070 XT, Strix Halo)
# far more often than the API. The General catch-all group was removed; the
# Hermes refresh drives the live search. Keys are BACKENDS names.
SEARCH_GROUPS = {
    "CUDA": [
        "rtx tokens per second llm",
        "rtx 3090 tokens per second qwen",
        "rtx 5090 32gb tokens per second",
        "rtx 4090 tokens per second llm",
        "rtx 3090 vs 5090 27b tokens",
        # Gaming-PC low end (issue #337): the 8/12/16 GB cards a regular person
        # owns. Every card query above named 24/32 GB, so the tier tables would
        # have been honest and empty exactly where the low-end reader looks.
        # These strings are the ones the `_search-nvidia` prompt carries, and
        # `tests/test_smoke_search.py` keeps prompt and smoke list identical.
        "rtx 3060 tokens per second",
        "rtx 4060 tokens per second",
        "rtx 4060 ti 16gb tokens per second",
        "rtx 4070 tokens per second",
        "8gb vram llm tokens per second",
        "16gb vram llm tokens per second",
        "freetoken gpu llm tokens per second",
        "bonsai 2 ternary 27b tokens",
        "qwen3.8-27b dflash speculative tokens",
        "open weight llm benchmark gpu",
    ],
    "Metal": [
        "mlx tokens per second",
        "mlx apple silicon tokens per second model",
        "mac m4 mlx local llm tokens per second",
        "mlxfast bonsai tokens per second",
        "tensorfold dflash mlx qwen tokens per second",
        "mac m series local llm tokens per second",
    ],
    "CPU": [
        "llm tokens per second no gpu cpu",
        "llama.cpp cpu only tokens per second",
        "local llm tokens per second gpu",
    ],
    "ROCm": [
        "rx 7900 xtx tokens per second",
        "rx 9070 xt tokens per second",
        "rocm tokens per second",
        "llama.cpp vulkan amd tokens",
        "strix halo tokens per second",
        "rx 7900 xtx qwen",
        # AMD gaming-PC low end (issue #337): the 8/16 GB Radeon cards a regular
        # person owns. Kept identical to the `_search-amd` prompt list.
        "rx 7600 tokens per second",
        "rx 6600 tokens per second",
        "rx 9060 xt tokens per second",
        "radeon 8gb vram llm tokens per second",
    ],
}

# The Hermes search legs: raw-snapshot backend name (Makefile `_search-<leg>`,
# `--write-raw <leg>`, data/raw/<leg>-<UTC>.json, CI matrix entry, smoke
# BACKEND=<leg>) -> the README backend table its figures mostly land in. ONE
# list: tests/test_amd_backend.py asserts every place that wires a leg (Makefile,
# both workflows, smoke, search contract, self-correct) carries exactly these.
SEARCH_LEGS = {"nvidia": "CUDA", "metal": "Metal", "cpu": "CPU", "amd": "ROCm"}
USER_AGENT = "trending-local-llms-bot/1.0 (research-index)"

# --- query coverage (issue #264) --------------------------------------------
# The searches were a fixed keyword list that named no model: of 24 queries the
# ONE model-specific one named qwen3.8-27b, and none named Strata. So every
# figure for the model topping the trend list arrived incidentally — a generic
# card query happened to surface a post mentioning it — and the pipeline could
# not tell "no such measurement exists" from "we never looked", so a higher one
# upstream could never enter. The trending models are therefore added to the
# query set FROM THE STORE, and `query_names_model()` decides whether any query
# names a model: ONE implementation (rule 6d), read by the search prompts, the
# coverage guard and its tests, so they can never disagree.
QUERY_TOP_N = 10
MODEL_QUERY_SUFFIX = "tokens per second"


def _query_key(text) -> str:
    """Comparison form: lowercased, every run of non-alphanumerics collapsed to
    '-'. So 'Qwen3.8-Flash-Next 125B' and 'qwen3.8-flash-next-125b' compare
    equal, and a SIBLING ('qwen3.8-27b') can never match by accident."""
    return re.sub(r"[^a-z0-9]+", "-", str(text or "").lower()).strip("-")


def model_query(m: dict) -> str:
    """The query that names ONE model, built from the model's own id."""
    return f"{m.get('id', '')} {MODEL_QUERY_SUFFIX}"


def query_names_model(query: str, m: dict) -> bool:
    """True when `query` names THIS model — by its own id, never a sibling's.

    A model with no usable id is named by nothing (an empty key must never
    match every query): that is the case the coverage guard turns red."""
    key = _query_key(m.get("id"))
    return bool(key) and key in _query_key(query)


def trending_models(store: dict, today: datetime | None = None) -> list[dict]:
    """The store's trending band in the store's own rank order, so 'top N'
    means the same thing here as it does in the README."""
    today = today or now_utc()
    band = [m for m in (store.get("models") or []) if model_band(m, today) == 0]
    return sorted(band, key=lambda m: (
        -(m.get("engagement") or {}).get("trend_score", 0),
        -(m.get("engagement") or {}).get("posts_7d", 0),
        -peak_tps(m),
        str(m.get("name", "")).lower(),
    ))


def derived_queries(store: dict, top_n: int = QUERY_TOP_N) -> list[str]:
    """One query naming each of the top-N trending models."""
    return [model_query(m) for m in trending_models(store)[:max(0, int(top_n))]]


def all_search_queries(store: dict, top_n: int = QUERY_TOP_N) -> dict[str, list[str]]:
    """The curated SEARCH_GROUPS with the derived model queries appended to
    EVERY leg — a model's figure can be measured on any backend and the legs run
    in parallel, so each leg asks for the ranked models as well as its hardware
    keywords. The curated base is kept, never replaced."""
    derived = derived_queries(store, top_n)
    return {backend: list(queries) + derived for backend, queries in SEARCH_GROUPS.items()}


def uncovered_models(store: dict, top_n: int = QUERY_TOP_N) -> list[dict]:
    """The top-N trending models that NO query in the set names — the gap the
    coverage guard makes loud, separable from a query that ran and found
    nothing. Empty when the derivation works; non-empty when it does not."""
    queries = [q for queries in all_search_queries(store, top_n).values() for q in queries]
    return [m for m in trending_models(store)[:max(0, int(top_n))]
            if not any(query_names_model(q, m) for q in queries)]

STRICT = os.environ.get("STRICT") == "1"

def now_utc() -> datetime:
    return datetime.now(timezone.utc)

def fetch_lightbrd(query: str) -> str:
    """Fetch one lightbrd search page. Raises on failure; caller decides.

    Uses the Firecrawl scrape API when FIRECRAWL_API_KEY is set (it renders
    through Cloudflare and returns real lightbrd posts). Falls back to plain
    urllib otherwise (which lightbrd usually blocks with HTTP 403)."""
    url = "https://lightbrd.com/search" "?f=tweets&q=" + urllib.parse.quote(query)
    fc_key = os.environ.get("FIRECRAWL_API_KEY", "").strip()
    if fc_key:
        return fetch_via_firecrawl(url, fc_key)
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read().decode("utf-8", "replace")


#: Firecrawl's scrape endpoint. Overridable so a test can point the REAL client
#: at a REAL local server (`ENGINE_REGISTRY_META_FILE` is the same seam), never a
#: stub of this function — the request we build is what the test asserts on.
DEFAULT_FIRECRAWL_SCRAPE_URL = "https://api.firecrawl.dev/v1/scrape"


def firecrawl_scrape_url() -> str:
    return (os.environ.get("FIRECRAWL_SCRAPE_URL", "").strip()
            or DEFAULT_FIRECRAWL_SCRAPE_URL)


class FirecrawlError(RuntimeError):
    """The fetch did not come back with a usable page. Base class, so `gather_x`
    can tell a fetch failure apart from an unrelated bug."""


class FirecrawlRefusal(FirecrawlError):
    """Firecrawl ANSWERED and refused: no credits, a bad key, a banned target, a
    `success: false` payload, a body that is not a scrape result, or a bot wall.
    The mirror was never reached — OUR configuration/quota, so the live check
    must keep failing until it is fixed."""


class UpstreamOutage(FirecrawlError):
    """Firecrawl scraped fine and the page IS an error page FROM THE TARGET
    (`metadata.statusCode >= 500`, Cloudflare's "Error code 502"). The MIRROR is
    down: nothing about our key, our queries or our code is wrong, and the live
    check must say so instead of blocking every open PR (issue #291)."""


#: Cloudflare's own error-page wording and its 5xx landing link, in the markdown
#: Firecrawl hands back. Measured on 2026-10-16, when lightbrd.com was 502:
#: `# Bad gatewayError code 502 … Visit [cloudflare.com](…/5xx-error-landing…)`.
_UPSTREAM_ERROR_PAGE = re.compile(r"Error code 5\d\d|/5xx-error-landing", re.I)


def _upstream_status(data: dict, body: dict) -> int | None:
    """The HTTP status the TARGET answered with, as Firecrawl reports it.

    Firecrawl answers HTTP 200 ITSELF and wraps the fetched page's real status in
    `data.metadata.statusCode` — which is exactly how a 502 mirror looks like a
    successful scrape.
    """
    raw_meta = data.get("metadata")
    meta: dict = raw_meta if isinstance(raw_meta, dict) else {}
    for value in (meta.get("statusCode"), data.get("statusCode"), body.get("statusCode")):
        if isinstance(value, (int, str)) and str(value).strip().isdigit():
            return int(value)
    return None


def fetch_via_firecrawl(url: str, api_key: str) -> str:
    """Fetch a page through Firecrawl's scrape API (renders JS, passes
    Cloudflare, which raw urllib cannot). Raises when the scrape did not
    actually return a page — the caller's `gather_x` turns that into a
    `[warn]` per query.

    Three outcomes, deliberately distinct (they demand OPPOSITE responses):

    * a REFUSAL — HTTP 200 with `{"success": false, "error": …}` (no credits, a
      banned target, an invalid key), no page at all, or a non-JSON body. The
      mirror was never reached: fix the credential/quota (`FirecrawlRefusal`);
    * an UPSTREAM OUTAGE — the scrape succeeded and the page is the TARGET's own
      error page (Cloudflare 502 `Error code 502` / `metadata.statusCode >= 500`).
      The mirror is down; nothing of ours is wrong (`UpstreamOutage`);
    * the page.

    Returning a refusal *as if it were a page* made every query "succeed" with
    zero known models, printed no warning at all, and reported `0 model hits` — a
    quiet-search diagnosis for a refused fetch. Collapsing the outage into the
    same silence did the same on every PR for hours (measured 2026-10-16: the
    whole live check finished in 6 s, no `[warn]`, because Firecrawl answered
    `success: true` with the mirror's 502 error page).
    """
    import urllib.request as _ur

    payload = json.dumps({
        "url": url,
        "formats": ["markdown"],
        "onlyMainContent": False,
    }).encode("utf-8")
    req = _ur.Request(
        firecrawl_scrape_url(),
        data=payload,
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"},
        method="POST",
    )
    with _ur.urlopen(req, timeout=60) as resp:
        raw = resp.read().decode("utf-8", "replace")
    try:
        body = json.loads(raw)
    except json.JSONDecodeError as e:
        raise FirecrawlRefusal(f"Firecrawl returned non-JSON ({raw[:200]!r})") from e
    if not isinstance(body, dict):
        raise FirecrawlRefusal(f"Firecrawl returned {raw[:200]!r}, not a scrape result")
    data = body.get("data")
    if not isinstance(data, dict):
        data = {}
    page = data.get("markdown") or data.get("html")
    if body.get("success") is False or not page:
        raise FirecrawlRefusal(
            "Firecrawl refused the scrape: "
            f"{body.get('error') or body.get('details') or raw[:200]!r}")
    # A page that came back is not automatically a page we can read: the target
    # itself may have answered with an error. Firecrawl reports that in
    # metadata.statusCode while answering 200 of its own.
    status = _upstream_status(data, body)
    if status is not None and status >= 500:
        raw_meta = data.get("metadata")
        title = raw_meta.get("title") if isinstance(raw_meta, dict) else ""
        raise UpstreamOutage(
            f"the target answered HTTP {status} ({title or 'error page'})")
    if _UPSTREAM_ERROR_PAGE.search(page):
        raise UpstreamOutage(
            f"the target answered a Cloudflare error page (HTTP {status or '5xx'})")
    if status is not None and status >= 400:
        raise FirecrawlRefusal(
            f"the target answered HTTP {status} — a bot wall Firecrawl's scrape did not pass")
    return page


def extract_models_seen(html: str) -> list[str]:
    """Very light heuristic: any known model token mentioned in the page."""
    known = re.findall(
        r"\b(Qwen3\.\d+(?:-[A-Za-z0-9]+)*|Qwen\d*\s*\d*B|gemma[- ]\d+[ A-Za-z0-9]*|"
        r"Llama\s*\d|\d+B)", html, re.I
    )
    return [m for m in known if m.strip()]


def gather_x(store: dict, stats: dict | None = None) -> dict:
    """Collect engagement signals per backend group from the lightbrd mirror.
    Returns {backend: [model_tokens_seen]}. Fetches are best-effort; a failed
    query is skipped with a warning and never wipes data.

    `stats`, when passed, is filled with this run's fetch OUTCOMES — how many
    queries there were, how many found a model, and how many failed and WHY
    (`outage` = the target answered an error page, `refused` = Firecrawl did not
    return a page, `failed` = anything else). The caller needs the split: with
    only the hit count, an upstream outage, a broken key and a quiet search are
    the same three words, `0 model hits` (issue #293)."""
    counts = {"queries": 0, "with_hits": 0, "outage": 0, "refused": 0, "failed": 0,
              "outage_status": [], "reasons": []}
    known_names = [m["name"].lower() for m in store["models"]]
    per_backend: dict[str, list[str]] = {}
    for backend, queries in SEARCH_GROUPS.items():
        seen: list[str] = []
        for q in queries:
            counts["queries"] += 1
            try:
                html = fetch_lightbrd(q)
                tokens = extract_models_seen(html)
                # keep only tokens that match a known model (signal, not noise)
                hits = [t for t in tokens if t.lower() in known_names or any(n in t.lower() for n in known_names)]
            except UpstreamOutage as e:
                counts["outage"] += 1
                counts["outage_status"].append(str(e))
                print(f"[warn] {backend} fetch failed for '{q}': {e}")
            except FirecrawlRefusal as e:
                counts["refused"] += 1
                counts["reasons"].append(str(e))
                print(f"[warn] {backend} fetch failed for '{q}': {e}")
            except Exception as e:  # noqa: BLE001
                counts["failed"] += 1
                counts["reasons"].append(str(e))
                print(f"[warn] {backend} fetch failed for '{q}': {e}")
            else:
                if hits:
                    counts["with_hits"] += 1
                seen += hits
        per_backend[backend] = seen
    if stats is not None:
        stats.update(counts)
    return per_backend


def zero_hit_verdict(stats: dict) -> tuple[str, int, list[str]]:
    """Classify a live search that found NO model hits.

    Returns `(kind, exit_code, lines)` where kind is `outage`, `refused` or
    `quiet` — three failures that look identical in a hit count and demand
    OPPOSITE responses:

    * `outage` — EVERY query came back as the target's own error page. The mirror
      is down; nothing of ours is wrong. Loud, and NOT a blocked PR (issue #291:
      `live-smoke` gates `auto-merge`, so an upstream outage used to stop every
      open PR at once).
    * `refused` — Firecrawl did not return a page at all (credits, key, target).
      OUR configuration: still red.
    * `quiet` — the mirror answered and there is no upstream error, yet no model
      was found: the query set (`SEARCH_GROUPS` + the derived model queries) is
      what to look at. Still red, and it says so rather than blaming the mirror.

    A PARTIAL outage stays `quiet` on purpose: an outage is only excused when every
    query that could be CLASSIFIED is one, so a half-answering mirror cannot slip a
    real regression through as infrastructure noise. A query we could not classify
    at all (`failed` — a transport error, e.g. `Connection refused`) is NOT evidence
    the mirror is healthy: with 23 of 24 queries proving the target's own error page,
    one unclassifiable query must not flip the verdict back to `quiet` and re-block
    every open PR (issue #296)."""
    queries = int(stats.get("queries") or 0)
    outage = int(stats.get("outage") or 0)
    refused = int(stats.get("refused") or 0)
    failed = int(stats.get("failed") or 0)
    with_hits = int(stats.get("with_hits") or 0)
    # Queries that returned a REAL page (neither the target's error page, nor a
    # refusal, nor a transport failure). Any of these means the mirror ANSWERED,
    # so an outage can no longer be excused.
    answered = queries - outage - refused - failed
    first_outage = (stats.get("outage_status") or [""])[0]
    first_reason = (stats.get("reasons") or [""])[0]

    # A refusal is OUR configuration (credits/key/target) and always wins.
    if refused:
        return "refused", 1, [
            f"[error] Firecrawl REFUSED the scrape for {refused}/{queries} querie(s): {first_reason}",
            "[error] the mirror was never reached — fix the credential/quota, not the query set",
        ]
    # The outage is excused when the target's own error page is what every query we
    # could CLASSIFY got, nothing was refused, nothing was found, and no query returned
    # a real page. `failed` queries do not disqualify: they prove nothing about the
    # mirror (issue #296), and they are named rather than hidden.
    if queries and outage and not with_hits and not answered:
        return "outage", 0, [
            f"[outage] the lightbrd mirror is DOWN: {outage}/{queries} queries came back as the "
            f"target's own error page ({first_outage})",
            "[outage] 0 model hits is EXPECTED here — this is NOT a quiet search (the mirror "
            "answered, with an error) and NOT a broken key (Firecrawl answered success:true)",
            *([f"[outage] {failed} further querie(s) failed for another reason ({first_reason}) — "
               "not counted against the mirror, but reported"] if failed else []),
            "[outage] NOT blocking: the live check stays green so an upstream outage cannot stop "
            "every open PR (issues #291, #296). Re-run when the mirror recovers.",
        ]
    return "quiet", 1, [
        f"[error] the mirror answered {answered}/{queries} queries with NO upstream error and "
        "0 model hits — a QUIET SEARCH on a reachable mirror: check the query set "
        "(SEARCH_GROUPS and the derived model queries)",
        *([f"[error] {outage + failed} querie(s) did not answer normally; an outage is only "
           "excused when EVERY query that answered is one (issue #291)"] if outage + failed else []),
    ]


# Search window vs trending window. The three Hermes search prompts fetch a
# last-3-day window (fast daily cadence); the TRENDING band aggregates distinct
# posts over the last 7 days so a model stays Trending on a rolling week of
# engagement, not a single day. Post entries older than RETENTION_DAYS are
# pruned from engagement.seen_posts (the model row itself is never removed).
SEARCH_WINDOW_DAYS = 3
TRENDING_WINDOW_DAYS = 7
RETENTION_DAYS = 30

def _as_post(p) -> dict:
    """Coerce a seen_posts entry to a dict. The search agent occasionally writes
    a bare URL string instead of {'url', 'date'}; normalize it so downstream
    code (dedupe/prune/recompute) never crashes on a str. Dicts pass through."""
    if isinstance(p, dict):
        return p
    if isinstance(p, str):
        return {"url": p, "date": ""}
    return {"url": "", "date": ""}


def _post_date(post) -> str:
    return _as_post(post).get("date", "") or ""


_POST_URL = re.compile(r"/status(?:es)?/\d+")

# Per-post engagement fields carried on seen_posts entries (and measurements).
_POST_SIGNALS = ("likes", "comments", "reshares", "views")


def _is_post_url(url: str) -> bool:
    """True for a URL that identifies ONE X post (…/status/<id>). The search
    agent often records a placeholder instead (https://lightbrd.com/ or a
    profile page) — those identify nothing and must not be deduped by URL."""
    return bool(_POST_URL.search(url or ""))


def _post_key(p: dict) -> str:
    """Identity of a seen post. A real post URL is its own identity (the same
    post re-scanned across overlapping windows collapses). A placeholder URL
    is keyed by url+date+engine+hardware+quant so distinct measurements that
    share 'https://lightbrd.com/' are not collapsed into one fake post. NEVER
    key on tps: merge_engines rewrites it ('60-91' -> '91'), which used to mint
    a duplicate 'post' on every re-sort (quant/hardware are never rewritten)."""
    url = p.get("url", "")
    if _is_post_url(url):
        return url
    norm = lambda k: (p.get(k) or "").strip().lower()  # noqa: E731
    return f"{url}#{p.get('date', '')}#{p.get('engine', '')}#{norm('hardware')}#{norm('quant')}"


def post_buzz(p: dict) -> float:
    """Trend contribution of ONE distinct post: breadth first, engagement
    log-dampened.
        1 + 0.5*log2(1 + likes + 2*comments + 3*reshares) + 0.25*log10(1 + views)
    Every post counts at least 1, so breadth dominates: a post with <= 10
    interactions is worth < 4 posts (2 likes + 4 comments + 310 views ~ 2.4),
    while a genuinely viral post still stands out (5,000 likes + 10k views ~
    8.2, i.e. about 8 ordinary posts). Unknown counts read as 0 — the base 1,
    never a penalty."""
    import math

    def n(k):
        try:
            return max(0.0, float(p.get(k) or 0))
        except (TypeError, ValueError):
            return 0.0
    inter = n("likes") + 2 * n("comments") + 3 * n("reshares")
    return 1.0 + 0.5 * math.log2(1.0 + inter) + 0.25 * math.log10(1.0 + n("views"))


def dedupe_posts(posts: list) -> list[dict]:
    """Collapse engagement.seen_posts to one entry per distinct post.

    The same X post is re-scanned across overlapping 3-day search windows, so
    without this a single post would inflate the 7-day score on every run.
    Keep the entry with the latest date per post (a re-seen post may carry a
    fresher date); on a date tie keep the one with more engagement. Tolerates
    bare-string entries (coerced to {'url', 'date'})."""
    by_key: dict[str, dict] = {}
    for p in posts:
        p = _as_post(p)
        if not p.get("url", ""):
            continue
        k = _post_key(p)
        cur = by_key.get(k)
        if (cur is None or _post_date(p) > _post_date(cur)
                or (_post_date(p) == _post_date(cur) and _eng_weight(p) > _eng_weight(cur))):
            by_key[k] = p
    return list(by_key.values())


def prune_posts(posts: list, today: datetime) -> list[dict]:
    """Drop engagement.seen_posts older than RETENTION_DAYS. The model row is
    never removed — only its stale post history is pruned (AGENTS retention)."""
    out = []
    for p in posts:
        p = _as_post(p)
        try:
            d = datetime.strptime(_post_date(p), "%Y-%m-%d").replace(tzinfo=timezone.utc)
        except Exception:  # noqa: BLE001
            continue  # unparseable date -> drop the stale/unknown post entry
        if (today - d).days <= RETENTION_DAYS:
            out.append(p)
    return out

def recompute_7d_engagement(m: dict, today: datetime) -> None:
    """Recompute the 7-day engagement from post-granularity data.

    seen_posts = stored posts UNION the posts behind the model's own engine
    measurements (so rows that existed before post tracking rank too), deduped
    by post identity and pruned to RETENTION_DAYS. Then, over the posts dated
    within TRENDING_WINDOW_DAYS:
      posts_7d      = number of distinct posts
      score_7d      = sum of _eng_weight(post) — likes + 2*comments +
                      3*reshares + log10(views+1), min 1 per post
      last_7d_likes = posts_7d (kept for back-compat)
    A row with no posts gets zeros — a legacy cumulative counter must never
    dominate the trending rank."""
    eng = m.setdefault("engagement", {})
    # Real posts (…/status/<id>) persist in seen_posts. Placeholder posts are
    # DERIVED state: rebuilt from the current measurements on every sort, so a
    # merge that rewrites a measurement can never leave a stale duplicate.
    stored_real = [p for p in (_as_post(x) for x in eng.get("seen_posts", [])) if _is_post_url(p.get("url", ""))]
    posts = dedupe_posts(stored_real + _collect_seen_posts(m))
    posts = prune_posts(posts, today)
    eng["seen_posts"] = posts
    cutoff = (today - timedelta(days=TRENDING_WINDOW_DAYS)).strftime("%Y-%m-%d")
    recent = [p for p in posts if _post_date(p) >= cutoff]
    buzz = round(sum(post_buzz(p) for p in recent), 1)
    best = best_in_scope(m) if recent else None
    speed = speed_bonus(_tps_core(best.get("tps"))) if best else 0.0
    eng["posts_7d"] = len(recent)
    eng["buzz_7d"] = buzz
    eng["score_7d"] = buzz  # back-compat alias of buzz_7d
    eng["speed_bonus"] = speed
    eng["trend_score"] = round(buzz + speed, 1)
    eng["last_7d_likes"] = len(recent)
    # last_seen = the newest DATA date (measurement or post), never the time
    # the merge ran: re-ingesting an old raw snapshot used to stamp today and
    # promote a June measurement to 'trending'.
    dates = [d for d in [_post_date(p) for p in posts] + [e.get("date", "") for e in m.get("engines", [])]
             if re.fullmatch(r"\d{4}-\d{2}-\d{2}", d or "")]
    if dates:
        m["last_seen"] = max(dates)

def merge_engagements(store: dict, seen: list[str]) -> tuple[int, int]:
    """Increment last_7d_likes on matched models; return (matched, unknown)."""
    matched = 0
    tokens = [s.lower() for s in seen]
    today = now_utc()
    for m in store["models"]:
        key = (m["name"] + " " + m.get("full_name", "")).lower()
        if any(t in key for t in tokens):
            m["engagement"]["last_7d_likes"] = m["engagement"].get("last_7d_likes", 0) + 1
            m["last_seen"] = today.strftime("%Y-%m-%d")
            matched += 1
    unknown = sum(1 for s in tokens if s not in set(m["name"].lower() for m in store["models"]))
    return matched, unknown

def apply_engine_aliases(m: dict, engines: list[dict] | None = None) -> list[dict]:
    """Rename engines per the model's `engine_aliases` ({posted name: registry
    name}). Bonsai 2's ternary GGUFs only run on the PrismML llama.cpp fork, so
    a post that says 'llama.cpp' must be stored and linked as
    'llama.cpp (PrismML fork)'. Applied to `engines` (default: the model's own)
    and to supported_engines; idempotent. Returns the (renamed) engine list."""
    aliases = m.get("engine_aliases") or {}
    es = m.get("engines", []) if engines is None else engines
    if not aliases:
        return es
    for e in es:
        if e.get("engine") in aliases:
            e["engine"] = aliases[e["engine"]]
    if engines is None and m.get("supported_engines"):
        seen, out = set(), []
        for name in (aliases.get(x, x) for x in m["supported_engines"]):
            if name not in seen:
                seen.add(name)
                out.append(name)
        m["supported_engines"] = out
    return es


def sort_models(models: list[dict], today: datetime) -> list[dict]:
    """Trending (<=7d) -> recent (<=30d) -> stale (>30d).
    Within a band, sort by last_7d_likes desc, then t/s (numeric) desc.
    Missing dates are treated as trending (conservative, never promoted into stale).
    Also sorts each model's engines newest-date-first so the latest trending
    t/s is always the first/surface figure."""
    for m in models:
        apply_engine_aliases(m)
        m["engines"] = sorted(m.get("engines", []), key=lambda e: e.get("date", ""), reverse=True)
        # recompute the 7-day engagement from distinct posts (dedup + prune)
        recompute_7d_engagement(m, today)

    return sorted(
        models,
        key=lambda m: (
            model_band(m, today),
            -m["engagement"].get("trend_score", 0),
            -m["engagement"].get("posts_7d", 0),
            -peak_tps(m),
            m["name"].lower(),
        ),
    )


BANDS = ("trending", "recent", "stale")


def model_band(m: dict, today: datetime) -> int:
    """0 = trending (last_seen within TRENDING_WINDOW_DAYS), 1 = recent (within
    RETENTION_DAYS), 2 = stale. A missing/unparseable date counts as trending
    (conservative: never demote a row into stale on bad data)."""
    try:
        last = datetime.strptime(m.get("last_seen", ""), "%Y-%m-%d").replace(tzinfo=timezone.utc)
    except Exception:  # noqa: BLE001
        return 0
    delta = (today - last).days
    if delta <= TRENDING_WINDOW_DAYS:
        return 0
    if delta <= RETENTION_DAYS:
        return 1
    return 2


def peak_tps(m: dict) -> float:
    """Highest t/s core across a model's measurements (max of a range)."""
    return max((_tps_core(e.get("tps")) for e in m.get("engines", [])), default=0.0)


# Engine -> backend for single-backend engines. Multi-backend engines (None)
# are decided from the hardware/quant text. ONE classifier for every table.
# AMD is decided by HARDWARE, never by engine name: llama.cpp / Ollama / vLLM /
# SGLang / Strata all run on AMD (ROCm/HIP or Vulkan) as well, and Vulkan also
# runs on NVIDIA and Intel, so 'Vulkan' alone is not AMD evidence.
ENGINE_BACKEND = {
    "Ollama": None, "llama.cpp": None, "vLLM": "CUDA", "SGLang": "CUDA",
    "FreeToken": "CUDA", "TensorRT-LLM": "CUDA", "DFlash2": "CUDA",
    "Strata": "CUDA", "MLX": "Metal", "TensorFold": "Metal",
    "MLX-fast (Bonsai 2)": "Metal", "LiteRT": None, "WebLLM": None,
}
_METAL_HW = ("apple", "mac", "m1 ", "m2 ", "m3 ", "m4 ", "m5 ", "m6 ", "m1)", "m2)", "m3)", "m4)", "m5)", "m6)", "mlx")
_CPU_HW = ("cpu", "intel", "amd ryzen", "ryzen", "epyc", "xeon", "threadripper", "no gpu", "raspberry", "arm64", "snapdragon")
_CUDA_HW = ("rtx", "nvidia", "cuda", "geforce", "tesla", "a100", "h100", "l40", "aic")
# AMD GPU evidence in a hardware string. Word-bounded on purpose: a bare 'amd'
# is also AMD Ryzen/EPYC CPUs, 'hip' is inside 'chip'/'ship', 'rx' inside words,
# and 'vulkan' is cross-vendor - none of those alone means an AMD GPU.
_AMD_GPU_RE = re.compile(
    r"\bradeon\b|\brx\s?-?\d{3,4}\b|\b(?:9070|9060|7900|7800|7700|7600|6950|6900|6800|6750|6700|6650|6600|5700)\s?(?:xtx|xt|gre)\b"
    r"|\brocm\b|\bhip\b|\bstrix[\s-]?halo\b|\bryzen\s+ai\s+max\b|\b(?:8065s|8060s|8050s|890m|880m|780m|760m|680m|660m)\b"
    r"|\bgfx\d{3,4}\b|\binstinct\b|\bmi\d{3}x?\b|\br9700\b|\bw7[89]00\b|\brdna\s?\d|\bnavi\s?\d|\bbc-?250\b"
    r"|\bamd\s+(?:gpu|graphics)\b", re.I)
# Explicit CPU-only wording beats any GPU token ('Ryzen AI Max+ 395, CPU only').
_CPU_ONLY_RE = re.compile(r"\bcpu[\s-]only\b|\bno[\s-]gpu\b|\bwithout (?:a )?gpu\b", re.I)
# AMD unified-memory APUs: judged by platform (like Apple), not by RAM size -
# a 128 GB Strix Halo is a consumer box, not a > 48 GB datacenter GPU.
_AMD_APU_RE = re.compile(r"\bstrix[\s-]?halo\b|\bryzen\s+ai\b|\b(?:8065s|8060s|8050s|890m|880m|780m|760m|680m|660m)\b", re.I)
# README / most-loved column order. ROCm = AMD GPUs (ROCm/HIP or Vulkan).
BACKENDS = ("CUDA", "Metal", "CPU", "ROCm")
# Canonical order when several backends are joined ('CUDA / ROCm / CPU / Metal'):
# keeps the historical 'CUDA / CPU / Metal' and 'CUDA / Metal' values unchanged.
_JOIN_ORDER = ("CUDA", "ROCm", "CPU", "Metal")


def is_amd_gpu(hw: str) -> bool:
    """True when the hardware text names an AMD GPU / APU (and not an NVIDIA one)."""
    h = (hw or "").lower()
    return bool(_AMD_GPU_RE.search(h)) and not any(k in h for k in _CUDA_HW)


def join_backends(backends) -> str:
    """{'ROCm','CUDA'} -> 'CUDA / ROCm' in the canonical order (contract pattern)."""
    seen = {b for b in backends if b in _JOIN_ORDER}
    return " / ".join(b for b in _JOIN_ORDER if b in seen)


def split_backends(raw: str) -> list[str]:
    """'CUDA / ROCm / Metal' -> ['CUDA', 'ROCm', 'Metal'] (known backends only)."""
    return [x.strip() for x in re.split(r"[/,|+]", raw or "") if x.strip() in BACKENDS]


def measured_backends(m: dict, registry: dict | None = None) -> list[str]:
    """The backends a model's measurements actually land in, in BACKENDS order."""
    seen = {measurement_backend(e, registry) for e in m.get("engines", [])}
    return [b for b in BACKENDS if b in seen]


def sync_backends(m: dict, registry: dict | None = None) -> list[str]:
    """Add every backend the model has a measurement on to m['backends'] (never
    removes one: 'backends' also records platforms a model is known to run on
    without a figure yet). Without this an existing model that gains its first
    AMD figure keeps backends without 'ROCm' forever, because ingest only
    derives backends for NEW models."""
    cur = [b for b in (m.get("backends") or []) if b]
    for b in measured_backends(m, registry):
        if b not in cur:
            cur.append(b)
    m["backends"] = cur or ["CUDA"]
    return m["backends"]


def registry_backend(engine: str, registry: dict | None) -> str | None:
    """The single backend the engine registry declares for `engine`
    ('Metal', 'CUDA', 'CPU' or 'ROCm'), or None when it lists several / is unknown."""
    raw = ((registry or {}).get(engine) or {}).get("backend", "")
    parts = [x.strip() for x in re.split(r"[/,|+]", raw) if x.strip()]
    return parts[0] if len(parts) == 1 and parts[0] in BACKENDS else None


def measurement_backend(e: dict, registry: dict | None = None) -> str:
    """Which backend table a measurement belongs to: CUDA, Metal, CPU or ROCm.
    Priority: explicit Apple hardware -> explicit CPU-only wording -> AMD GPU
    hardware (Radeon / RX / Strix Halo / ROCm / HIP ..., no NVIDIA token) ->
    CPU hardware -> the engine registry when it names ONE backend -> the
    built-in single-backend map -> GPU/Apple keywords in hardware+quant -> CUDA
    (default until evidence says otherwise). AMD hardware is checked BEFORE the
    engine lookups because the engines that run on AMD (llama.cpp, vLLM,
    Strata ...) are registered or mapped as CUDA, and before CPU because AMD
    GPU strings often carry the host CPU ('Ryzen 5 7600 + RX 7800 XT'). Pass
    the store's `engines` registry so a new registry-only engine (e.g. a
    Mac-only server) never falls through to the CUDA default."""
    hw = (" " + (e.get("hardware") or "") + " ").lower()
    if "apple" in hw or "mac" in hw:
        return "Metal"
    if _CPU_ONLY_RE.search(hw):
        return "CPU"
    if is_amd_gpu(hw):
        return "ROCm"
    if any(k in hw for k in _CPU_HW) and not any(k in hw for k in _CUDA_HW):
        return "CPU"
    b = registry_backend(e.get("engine", ""), registry) or ENGINE_BACKEND.get(e.get("engine", ""))
    if b:
        return b
    text = hw + " " + (e.get("quant") or "").lower() + " "
    if any(k in text for k in _CUDA_HW):
        return "CUDA"
    if is_amd_gpu(text):
        return "ROCm"
    if any(k in text for k in _METAL_HW):
        return "Metal"
    return "CUDA"


# ---- speed component of the trend score ------------------------------------
# The index is about consumer / workstation hardware (AGENTS rule 6: 8-48 GB
# GPUs, plus Apple and CPU as first-class backends). Only measurements on that
# hardware earn the speed bonus; a datacenter figure never does.
MAX_SCOPE_VRAM_GB = 48
# Datacenter parts never earn the speed bonus (AGENTS.md §5). Every SKU family
# here, bare AND suffixed: 'b300' was missing, so a post reading "single NVIDIA
# B300 GPU (datacenter)" passed hardware_vram_gb() as None and in_scope() as
# True — LFM2.5-24B-A2B earned speed +11 from a 21,000 t/s datacenter figure and
# ranked 3rd (issue #337). Add the family, never one spelling of it.
_DATACENTER_HW = ("h100", "h200", "h800", "a100", "a800", "b100", "b200", "b300", "gb200", "gb300",
                  "mi210", "mi250", "mi300", "mi308", "mi325", "mi355", "tpu", "gaudi",
                  # AMD's datacenter V-series (cloud-gaming / VDI parts). A
                  # 'Radeon Pro V620 32GB x8' homelab cluster is not a card a
                  # reader buys, and its pool size is what the gate must read
                  # (#260). Radeon Pro W-series (W7900/W7800) are workstation
                  # cards and stay in scope.
                  "v620", "v520", "v340")
# A hardware string can name a CLASS of machine instead of a card: the shipped store
# carries 'datacenter GPUs, 512 concurrent requests' for Qwen3.8-27B's 28,340 t/s
# AGGREGATE figure. It has no card name and no VRAM figure, so hardware_vram_gb()
# returned None and the gate ADMITTED it — that number earned speed +11.5, headed the
# most-loved row and was printed as its CUDA best cell, when the fastest figure on a
# card a reader can buy was 500 t/s on an RTX 5090 (issue #349). The SKU list above
# cannot see this shape, so a class phrase is refused on its own.
_DATACENTER_CLASS_RE = re.compile(r"\bdata[\s-]?cent(?:er|re)\b", re.I)
# Known consumer cards -> VRAM (GB). Laptop variants listed first (more specific).
_CARD_VRAM = (
    ("5090 laptop", 24), ("4090 laptop", 16), ("5080 laptop", 16), ("4080 laptop", 12),
    ("5090", 32), ("5080", 16), ("5070 ti", 16), ("5070", 12), ("5060 ti", 16), ("5060", 8),
    ("4090", 24), ("4080", 16), ("4070 ti super", 16), ("4070 ti", 12), ("4070", 12),
    ("4060 ti", 16), ("4060", 8), ("3090", 24), ("3080 ti", 12), ("3080", 10),
    ("3070", 8), ("3060 ti", 8), ("3060", 12), ("a6000", 48), ("l40", 48),
    # AMD Radeon (consumer + workstation). Suffixed names first (7900 xtx before
    # 7900 xt); bare model numbers need the 'rx ' prefix so a host CPU such as
    # 'Ryzen 5 7600' is never read as an RX 7600 (8 GB).
    ("7900 xtx", 24), ("7900 xt", 20), ("7900 gre", 16), ("7800 xt", 16), ("7700 xt", 12),
    ("7600 xt", 16), ("rx 7600", 8), ("9070 xt", 16), ("rx 9070", 16), ("9060 xt", 16),
    ("rx 9060", 8), ("6950 xt", 16), ("6900 xt", 16), ("6800 xt", 16), ("rx 6800", 16),
    ("6750 xt", 12), ("6700 xt", 12), ("6650 xt", 8), ("6600 xt", 8), ("rx 6600", 8),
    ("5700 xt", 8), ("vega 64", 8), ("vega 56", 8), ("r9700", 32), ("w7900", 48), ("w7800", 32),
)


def hardware_vram_gb(hw: str) -> float | None:
    """Total GPU memory the hardware string implies, or None if unknown.
    An explicit 'NN GB' wins; otherwise a known card. 'Nx' multiplies
    ('2x RTX 3090' -> 48)."""
    h = re.sub(r"\brx\s*-?(?=\d)", "rx ", (hw or "").lower())  # 'RX7900' / 'rx-7600' -> 'rx 7900'
    # An explicit pool total wins outright: 'Radeon Pro V620 32GB x8 (256GB
    # total)' states the memory one run had, and reading the per-card 32 would
    # put a 256 GB cluster inside the 8-48 GB band (issue #260).
    total = re.search(r"(\d+(?:\.\d+)?)\s*gb\s*total", h)
    if total:
        return float(total.group(1))
    mult = 1
    # '2x RTX 3090' / '4 x 3090' multiply; a standalone 1-2 digit count only, so
    # the 'x' of an AMD suffix ('7900 xtx', '9070 xt') is never read as one.
    mm = re.search(r"(?<![\w.])(\d{1,2})\s*[x×]\s*(?=[a-z0-9])", h)
    if mm:
        mult = int(mm.group(1))
    m = re.search(r"(\d+(?:\.\d+)?)\s*gb", h)
    if m:
        # '32GB x8' — the multiplier AFTER the size (the mirror image of '2x 32GB').
        after = re.search(r"\d+(?:\.\d+)?\s*gb\s*[x×]\s*(\d{1,2})\b", h)
        return float(m.group(1)) * (int(after.group(1)) if after else mult)
    for card, gb in _CARD_VRAM:
        if card in h:
            return float(gb * mult)
    return None


def in_scope(e: dict) -> bool:
    """True when a measurement ran on consumer/workstation hardware: not a
    datacenter part and not more than MAX_SCOPE_VRAM_GB of GPU memory. Apple
    and CPU measurements are in scope (first-class backends); unified-memory
    Macs and AMD APUs (Strix Halo / Ryzen AI, Radeon 8060S ...) are judged by
    platform, not by their RAM size. Consumer Radeon cards are judged by VRAM
    exactly like NVIDIA; AMD Instinct (MI210/MI250/MI300/MI355) never counts."""
    h = (e.get("hardware") or "").lower()
    if any(k in h for k in _DATACENTER_HW) or re.search(r"\binstinct\b", h):
        return False
    if _DATACENTER_CLASS_RE.search(h):
        return False
    if "apple" in h or "mac" in h or measurement_backend(e) in ("Metal", "CPU"):
        return True
    if _AMD_APU_RE.search(h):
        return True
    vram = hardware_vram_gb(h)
    return vram is None or vram <= MAX_SCOPE_VRAM_GB


def best_in_scope(m: dict) -> dict | None:
    """Fastest measurement on in-scope hardware (the figure the speed bonus uses)."""
    return best_measurement([e for e in m.get("engines", []) if in_scope(e)])


def speed_bonus(tps: float) -> float:
    """log2(1 + tps/10): 10 t/s -> +1, 70 -> +3, 150 -> +4, 630 -> +6. Rewards
    fast models on the hardware that matters, log-scaled so one spec-decode
    outlier can't swamp the engagement signal."""
    import math
    return round(math.log2(1.0 + max(0.0, tps) / 10.0), 1)


def best_measurement(es: list[dict]) -> dict | None:
    """Highest t/s core; newest date breaks a tie."""
    if not es:
        return None
    return max(es, key=lambda e: (_tps_core(e.get("tps")), e.get("date", "")))


# ---- card-fit view (issue #337): "what fits MY card" ------------------------
# The index exists to answer one question for a card owner: with N GB of VRAM,
# which model gives me the most t/s? The README answered it with four per-backend
# cells and a `vram_tier` cell that is a CATEGORY — it disagreed with the model's
# own `vram_min` for 20 of 46 models and sat below the smallest card a measurement
# had ever run on for 17. So the fit is derived here, ONCE (rule 6d), and read by
# the tier tables, the most-loved VRAM cell and the validator, so no two places
# can disagree about what fits.
#
# The evidence ladder, strongest first — and never a guess (rule 2):
#   'ran-on'      a measurement ran on a card of <= N GB, so N GB is PROVEN
#   'weights-only' only the weight footprint fits N GB — KV cache and overhead
#                 are unknown, so it is labelled, never presented as a fit
#   'declared'    the model states the least VRAM it needs (vram_min)
#   'tier'        only the coarse vram_tier string is available
#   'unknown'     nothing supports a claim: reported, never rendered as a number
CARD_TIERS_GB = (8, 12, 16, 24, 32, 48)
# Above the card ladder (issue #572): the memory is UNIFIED (Apple Silicon, a big
# APU), a multi-GPU workstation, or a datacenter part — so the evidence is the
# run's TOTAL memory (unified memory / system RAM / the measured VRAM across every
# GPU), never a card. A model is placed here only when its evidence says it needs
# MORE than `MAX_SCOPE_VRAM_GB` (48): the reader's question is "what runs on the
# machine I have", not "what would also fit a small card", so a 24 GB run does not
# appear in the 64 GB table. The same `ran-on` / `weights-only` labelling applies.
HIGH_TIERS_GB = (64, 128, 256, 512)
#: What a tier of that size usually IS, said in the section's own words.
HIGH_TIER_LABELS = {
    64: "unified memory or a prosumer multi-GPU box",
    128: "unified memory or a prosumer multi-GPU box",
    256: "unified memory or datacenter hardware",
    512: "datacenter hardware",
}
# The low end this index prioritises: a GAMING LAPTOP, 8-24 GB of VRAM. The
# trending list and the tier tables are for that reader first; 32/48 GB is the
# workstation step above it, and everything bigger is unified memory / datacenter
# (AGENTS.md §6 keeps the headline scope at 8-48 GB consumer/workstation).
LOW_END_TIERS_GB = (8, 12, 16, 24)
_GB_TEXT_RE = re.compile(r"(\d+(?:\.\d+)?)\s*gb", re.I)


def _gb_value(value) -> float | None:
    """'5.95GB Q4_K_M' / 12 / '12 GB 8GB' -> the first GB figure, else None."""
    if value is None:
        return None
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return float(value)
    m = _GB_TEXT_RE.search(str(value))
    return float(m.group(1)) if m else None


#: A measurement's `weight_gb` that is this many times the model's OWN stated
#: footprint is not the same model's weights — it is a mis-ingested row (measured:
#: Bonsai 2 9B, a 2 GB ternary model, carried "~493GB NVFP4" on a 4x M5 Ultra run,
#: which the tier ladder happily read as proof it needs a 512 GB machine). The
#: stated value is refused and the model's own footprint is used instead.
WEIGHTS_CONTRADICTION_FACTOR = 10


def weights_gb(m: dict, e: dict) -> tuple[float | None, str]:
    """The weight footprint of the quant THIS measurement ran in, with its
    evidence: the measurement's own `weight_gb` when the post stated it
    ('stated'), else the model's ('model-level'), else (None, 'unknown').

    A 'stated' value that CONTRADICTS the model's own footprint by more than
    `WEIGHTS_CONTRADICTION_FACTOR` is refused in favour of the model-level one:
    a number that cannot belong to this model is not evidence about it.
    """
    stated = _gb_value(e.get("weight_gb"))
    model_level = _gb_value(m.get("weight_gb"))
    if stated is not None and model_level is not None and model_level > 0:
        ratio = max(stated, model_level) / min(stated, model_level)
        if ratio > WEIGHTS_CONTRADICTION_FACTOR:
            return model_level, "model-level"
    if stated is not None:
        return stated, "stated"
    if model_level is not None:
        return model_level, "model-level"
    return None, "unknown"


def card_memory_gb(e: dict) -> float | None:
    """The total memory of the card the measurement ran on (upper bound)."""
    return hardware_vram_gb(e.get("hardware") or "")


def fits_tier(m: dict, e: dict, tier: int) -> str | None:
    """How this measurement qualifies for a `tier`-GB card, or None.

    Only a consumer/workstation measurement can place a model on a card a reader
    owns (`in_scope`): a datacenter figure a reader cannot buy never becomes
    "what fits your card" (issues #260/#337). 'ran-on' is proved by the run;
    'weights-only' needs a KNOWN card — if the run's own hardware names no card
    (a host, a cluster, a bare "GPU"), we cannot claim one of its quants fits a
    smaller tier, because the KV cache and the offload it needed are unknown."""
    if not in_scope(e):
        return None
    c = card_memory_gb(e)
    if c is not None and c <= tier:
        return "ran-on"
    w, _ = weights_gb(m, e)
    if c is not None and c > tier and w is not None and w <= tier:
        return "weights-only"
    return None


def tier_measurements(m: dict, tier: int, registry: dict | None = None) -> list[tuple[dict, str]]:
    """The measurements of `m` with evidence for a `tier`-GB card, as (measurement,
    evidence). Apple Silicon and CPU are judged by unified memory / RAM, not VRAM,
    so they are never placed in a card tier."""
    out = []
    for e in m.get("engines", []):
        if measurement_backend(e, registry) in ("Metal", "CPU"):
            continue
        ev = fits_tier(m, e, tier)
        if ev:
            out.append((e, ev))
    return out


def tier_rows(models: list[dict], tier: int, registry: dict | None = None) -> list[tuple[float, dict, dict, str]]:
    """(best t/s, model, measurement, evidence) for every model with evidence for
    a `tier`-GB card, best first."""
    rows = []
    for m in models:
        cands = tier_measurements(m, tier, registry)
        if not cands:
            continue
        # A proved fit beats a weights-only one, then the fastest figure wins.
        e, ev = max(cands, key=lambda p: (p[1] == "ran-on", _tps_core(p[0].get("tps"))))
        rows.append((_tps_core(e.get("tps")), m, e, ev))
    rows.sort(key=lambda r: (-r[0], r[1]["name"].lower()))
    return rows


# ---- above 48 GB (issue #572): the memory is unified, multi-GPU or datacenter --
def total_memory_gb(e: dict) -> float | None:
    """The TOTAL memory the RUN had, from the hardware it names.

    VRAM first (`hardware_vram_gb`, which multiplies `Nx`), so an `8×H100 80GB`
    run is 640 GB and a `2×RTX 4090 24GB` box is 48; otherwise the largest GB
    figure the hardware states, which is the unified memory of an Apple Silicon
    machine (`M3 Ultra 512GB`) or the system RAM of a CPU run. None when the
    hardware names no size at all — then nothing can be claimed (rule 2).
    """
    hw = e.get("hardware") or ""
    v = hardware_vram_gb(hw)
    if v is not None:
        return v
    gbs = [float(g) for g in _GB_TEXT_RE.findall(hw)]
    return max(gbs) if gbs else None


def high_tier_fit(m: dict, e: dict, tier: int) -> str | None:
    """How this measurement qualifies for an ABOVE-48-GB `tier`, or None.

    The reader of these tiers owns a machine with more memory than any consumer
    card, and asks "what NEEDS this much?". So a model is placed here only with
    evidence that it needs MORE than `MAX_SCOPE_VRAM_GB`:

      'ran-on'       a run whose own total memory was in (48, tier] — it needed
                     more than a card and fit this machine
      'weights-only' only the weight footprint fits the tier and it EXCEEDS 48 GB
                     (KV cache and overhead unknown, so it is labelled)

    A model whose weights fit a consumer card is never placed here — an 8B served
    on a 64 GB Mac mini does not need 64 GB, and listing it would bury the models
    that do. That is the CARD ladder's reader, one section up.
    """
    total = total_memory_gb(e)
    w, _tag = weights_gb(m, e)
    # ONLY the weight footprint can say a model needs more than a consumer card, and
    # an unknown footprint says nothing (rule 2: no figure is invented).
    if w is None or w <= MAX_SCOPE_VRAM_GB or w > tier:
        return None
    if total is not None and MAX_SCOPE_VRAM_GB < total <= tier:
        return "ran-on"
    # The weights fit but the run's own machine does not prove the fit: the KV cache
    # and the overhead it needed are unknown, so it is labelled, never sold as a fit.
    return "weights-only"


def high_tier_measurements(m: dict, tier: int,
                           registry: dict | None = None) -> list[tuple[dict, str]]:
    """The measurements of `m` with evidence for an above-48-GB tier.

    Apple Silicon and CPU are NOT skipped here — unified memory and system RAM are
    exactly what these tiers are — unlike the card tiers, where they never appear.
    """
    return [(e, ev) for e in m.get("engines", [])
            if (ev := high_tier_fit(m, e, tier))]


def high_tier_rows(models: list[dict], tier: int,
                   registry: dict | None = None) -> list[tuple[float, dict, dict, str]]:
    """(best t/s, model, measurement, evidence) for an above-48-GB tier, best first."""
    rows = []
    for m in models:
        cands = high_tier_measurements(m, tier, registry)
        if not cands:
            continue
        e, ev = max(cands, key=lambda p: (p[1] == "ran-on", _tps_core(p[0].get("tps"))))
        rows.append((_tps_core(e.get("tps")), m, e, ev))
    rows.sort(key=lambda r: (-r[0], r[1]["name"].lower()))
    return rows


# ---- trending for your card (issue #349): a tier-local trend ----------------
# The ranking was ONE global list: its speed term could come from any in-scope
# card, so a 32 GB RTX 5090 at 500 t/s and a 16 GB RTX 4060 at 50 t/s competed in
# the same column and the reader with the smaller card had no ranking at all. The
# fix is NOT a per-tier copy of the score — it is the SAME buzz with a speed bonus
# earned only by a measurement that RAN on a card <= the tier, reusing the ONE fit
# rule (`tier_measurements` -> `fits_tier`, rule 6d). A weights-only fit never earns
# it: the figure came from a bigger card and was never measured at this size.


def tier_speed(m: dict, tier: int, registry: dict | None = None) -> dict | None:
    """The measurement that earns a `tier`-GB speed bonus: the fastest one that
    actually RAN on a card <= tier ('ran-on'), never a weights-only fit."""
    ran = [e for e, ev in tier_measurements(m, tier, registry) if ev == "ran-on"]
    return best_measurement(ran)


def tier_trend(m: dict, tier: int, registry: dict | None = None) -> tuple[float, float, dict | None]:
    """(tier-local trend, speed bonus, the measurement behind the bonus).

    The buzz is the model's own 7-day buzz (unchanged: engagement does not depend
    on the reader's card); only the speed term is tier-local. A model with no post
    in the window is not trending at any tier, so its score is 0."""
    eng = m.get("engagement", {}) or {}
    if not int(eng.get("posts_7d", 0) or 0):
        return 0.0, 0.0, None
    best = tier_speed(m, tier, registry)
    bonus = speed_bonus(_tps_core(best.get("tps"))) if best else 0.0
    return round(float(eng.get("buzz_7d", 0) or 0) + bonus, 1), bonus, best


def tier_trending_rows(models: list[dict], tier: int,
                       registry: dict | None = None) -> list[tuple[float, dict, dict | None, str]]:
    """(tier-local trend, model, measurement or None, evidence) for every TRENDING
    model with evidence at <= `tier`, ranked by the tier-local trend, then t/s."""
    rows = []
    for m in models:
        cands = tier_measurements(m, tier, registry)
        if not cands:
            continue
        score, _bonus, best = tier_trend(m, tier, registry)
        if not score:
            continue  # not trending in the window, so it belongs to the card-fit view only
        ev = next((evidence for e, evidence in cands if e is best), cands[0][1])
        rows.append((score, m, best, ev))
    rows.sort(key=lambda r: (-r[0], -(_tps_core(r[2].get("tps")) if r[2] else 0.0),
                             r[1]["name"].lower()))
    return rows


#: A `vram_min` that states a SPLIT requirement: a GPU capacity AND system RAM. Such a
#: value is not one number, and publishing its first number as "the least VRAM needed" reads
#: as "fits that card" — the opposite of what an offload requirement promises (issue #431).
_SPLIT_REQUIREMENT = lambda raw: bool(re.search(r"(?<!\bno )\b(gpu|vram)\b", raw, re.I)) and bool(
    re.search(r"\bram\b", raw, re.I))


#: `vram_min` values that DECLARE "no GPU needed" rather than a capacity. Deliberately
#: strict — a sentence like "system RAM holds the expert set (32GB GPU + system RAM)" is
#: NOT this (it names a GPU too), so only the bare marker forms match (issue #343).
CPU_ONLY_MARKER = re.compile(r"^cpu(?:[- ]?only)?$", re.I)


def card_gap_reason(m: dict, registry: dict | None = None) -> str | None:
    """Why a model has no card-tier row (issue #342), or None when it has one.

    A tier places a model only with EVIDENCE (`fits_tier`), so a model with none is silently
    absent from every table — and "we never measured this on a card" then reads exactly like
    "no card can run it". The two reasons want different actions:

      * ``'unified memory / CPU-only'`` — every measurement is Metal or CPU. There is no
        card figure to collect; the model's home is the Metal/CPU table.
      * ``'no card figure collected'`` — it HAS a CUDA/ROCm figure, but none placed: a
        datacenter part, a card above every tier, or a run whose hardware names no card.
        This is a data gap the searches must close.
    """
    if any(tier_measurements(m, t, registry) for t in CARD_TIERS_GB):
        return None
    backends = {measurement_backend(e, registry) for e in m.get("engines", [])}
    if backends and backends <= {"Metal", "CPU"}:
        return "unified memory / CPU-only"
    return "no card figure collected"


def vram_need(m: dict) -> tuple[str, str]:
    """The LEAST VRAM the model needs to run, with the evidence behind it:
    ('8GB', 'declared') from `vram_min`, ('16GB', 'tier') from the coarse
    `vram_tier`, ('>=12GB', 'measured-on') from the smallest card it ran on, else
    ('unknown', 'unknown'). `vram_tier` alone is never rendered as a requirement —
    it is a category that can sit below what the model actually needs."""
    raw_min = str(m.get("vram_min") or "")
    if CPU_ONLY_MARKER.match(raw_min.strip()):
        # `vram_min: "CPU"` is a DECLARATION — the model needs no VRAM at all — and it used
        # to fall through to the coarse tier or to "unknown", so a reader was told the
        # requirement was unstated when the source had stated it plainly (issue #343).
        return "CPU only", "declared"
    g = _gb_value(raw_min)
    if g is not None:
        # A SPLIT requirement — "32GB GPU + system RAM" — is not one number. Reading it as
        # its first capacity published the GPU half as "the least VRAM needed", which reads
        # as "fits a 32 GB card" and is exactly what a MoE offload does not promise
        # (issue #431). Only a value that names BOTH a GPU capacity and RAM is split:
        # "16GB RAM" (a unified-memory / CPU statement) stays a plain capacity.
        if _SPLIT_REQUIREMENT(raw_min):
            return f"{g:g}GB + system RAM", "declared"
        return f"{g:g}GB", "declared"
    g = _gb_value(m.get("vram_tier"))
    if g is not None:
        return f"{g:g}GB", "tier"
    cards = [c for c in (card_memory_gb(e) for e in m.get("engines", [])) if c is not None]
    if cards:
        return f">={min(cards):g}GB", "measured-on"
    return "unknown", "unknown"


BACKEND_LABEL = {
    "CUDA": ("🟦", "CUDA — NVIDIA GPUs (8–48 GB)"),
    "Metal": ("🟩", "Metal — Apple Silicon (unified memory)"),
    "CPU": ("🟨", "CPU — no GPU"),
    "ROCm": ("🟪", "ROCm — AMD GPUs (8–48 GB)"),
}
BAND_LABEL = ("🔥 trending", "🕑 recent", "💤 stale")


def _fmt_num(x: float) -> str:
    return f"{x:g}"


def _cell(text) -> str:
    """Make free text safe inside a markdown table cell."""
    return str(text or "").replace("|", "\\|").replace("\n", " ").strip()


def trend_cell(m: dict) -> str:
    """Most-loved 'Trend' cell: the score, then how it was built."""
    eng = m.get("engagement", {})
    posts = eng.get("posts_7d", 0)
    if not posts:
        return "**0**<br><sub>no posts in 7 days</sub>"
    sub = f"buzz {_fmt_num(eng.get('buzz_7d', 0))} · {posts} post{'s' if posts != 1 else ''}"
    best = best_in_scope(m)
    if best and eng.get("speed_bonus", 0):
        hw = f", {_cell(best.get('hardware'))}" if best.get("hardware") else ""
        sub += f" · speed +{_fmt_num(eng['speed_bonus'])} ({best['tps']} t/s{hw})"
    return f"**{_fmt_num(eng.get('trend_score', 0))}**<br><sub>{sub}</sub>"


def render_readme(store: dict, today: datetime) -> str:
    """Regenerate README.md from the store + static sections.

    Layout (every section is derived from the same measurement_backend() and
    best_measurement() so the tables can never disagree):
      1. Most loved — one row per model in rank order (band -> 7-day score ->
         posts -> peak t/s): status, 7-day buzz, BEST t/s per backend
         (CUDA / Metal / CPU / ROCm) with engine + hardware + quant, VRAM, why.
      2. Engine matrix — which inference engine runs which model, best t/s per
         backend on that engine. Only engines with a measurement are columns.
      3. Backend tables — numeric Peak t/s column + every measurement
         (engine · t/s · hardware · quant · date), best first.
      4. Engine guide — with the number of models measured on each engine.
    """
    models = sort_models(list(store["models"]), today)
    registry = store.get("engines", {})

    def elink(name: str) -> str:
        url = registry.get(name, {}).get("url")
        return f"[{name}]({url})" if url else name

    def hf_url(m: dict) -> str:
        # The id is an `owner/repo`; a URL-shaped value would otherwise be
        # prefixed again (measured: issue #165), so normalise before building.
        return f"https://huggingface.co/{normalise_hf(m.get('hf', ''))}"

    def detail(e: dict) -> str:
        bits = [_cell(x) for x in (e.get("hardware"), e.get("quant")) if x]
        return " · ".join(bits)

    def by_backend(m: dict) -> dict[str, list[dict]]:
        out: dict[str, list[dict]] = {b: [] for b in BACKENDS}
        for e in m.get("engines", []):
            out[measurement_backend(e, registry)].append(e)
        return out

    # ---- 1. most loved -------------------------------------------------------
    # The figure a CARD OWNER reads must be one they can actually get: the best
    # in-scope measurement (<= 48 GB consumer/workstation, Apple, CPU), the same
    # gate the speed bonus uses — never a datacenter figure a reader cannot buy
    # (issue #260, issue #337). Out-of-scope figures stay in the backend tables.
    def best_cell(es: list[dict]) -> str:
        scoped = [e for e in es if in_scope(e)]
        b = best_measurement(scoped) or best_measurement(es)
        if b is None:
            return "—"
        cell = f"**{b['tps']}** t/s<br>{elink(b['engine'])}"
        if detail(b):
            cell += f" · {detail(b)}"
        if len(es) > 1:
            cell += f"<br><sub>+{len(es) - 1} more</sub>"
        return cell

    def vram_cell(m: dict) -> str:
        need, ev = vram_need(m)
        if need == "unknown":
            return "<sub>not stated</sub>"
        tag = {"declared": "stated by the source", "tier": "category only",
               "measured-on": "smallest card it ran on"}[ev]
        # NAME THE CARD the headline figure ran on: a 500 t/s figure sourced from an
        # RTX 5090 32GB sat in a row whose VRAM cell said "16GB", which reads as "this
        # is what my 16 GB laptop gets" (issue #349). The least-VRAM claim stays first
        # (that is what the column means); the card the number came from follows it.
        best = best_in_scope(m)
        hw = best.get("hardware") if best else None
        if hw:
            tag += f" · headline on {_cell(hw)}"
        return f"**{need}**<br><sub>{tag}</sub>"

    loved = []
    for m in models:
        eng = m.get("engagement", {})
        sub = " · ".join(_cell(x) for x in (m.get("full_name"), m.get("params"), m.get("license")) if x)
        model_cell = f"[**{m['name']}**]({hf_url(m)})" + (f"<br><sub>{sub}</sub>" if sub else "")
        status = BAND_LABEL[model_band(m, today)] + (f"<br><sub>last seen {m['last_seen']}</sub>" if m.get("last_seen") else "")
        buzz = trend_cell(m)
        bb = by_backend(m)
        best_cells = " | ".join(best_cell(bb[b]) for b in BACKENDS)
        loved.append(
            f"| {model_cell} | {status} | {buzz} | {best_cells} "
            f"| {vram_cell(m)} | {_cell(m.get('why')) or '—'} |"
        )
    most_loved = "\n".join(loved)

    # ---- 1a. trending for your card (issue #349) ----------------------------
    # The FIRST section: the reader with 8-24 GB of VRAM picks their card and reads
    # the trend ranked FOR THAT CARD. Ranked by `tier_trending_rows()` — the ONE
    # tier-local derivation the validator also reads (rule 6d) — never by t/s alone
    # and never by the global score, which could inherit a card they do not own.
    def tier_trend_cell(m: dict, score: float, bonus: float, best: dict | None) -> str:
        eng = m.get("engagement", {}) or {}
        posts = int(eng.get("posts_7d", 0) or 0)
        sub = f"buzz {_fmt_num(eng.get('buzz_7d', 0))} · {posts} post{'s' if posts != 1 else ''}"
        if best and bonus:
            hw = f", {_cell(best.get('hardware'))}" if best.get("hardware") else ""
            sub += f" · speed +{_fmt_num(bonus)} ({best['tps']} t/s{hw})"
        else:
            sub += " · speed +0 (no measured fit at this size)"
        return f"**{_fmt_num(score)}**<br><sub>{sub}</sub>"

    def trending_card_section() -> str:
        most_loved_anchor = ("#-most-loved-open-weight-models-on-x-ranked-by-trend-"
                             "7-day-buzz--speed")
        parts = [
            "## 🔥 Trending for your card — low end first",
            "",
            "Jump to your card: " + " · ".join(f"[{t} GB](#up-to-{t}-gb)" for t in CARD_TIERS_GB)
            + f" · [No limit]({most_loved_anchor})",
            "",
            "Ranked by a **tier-local trend**: the model's own 7-day buzz, plus a speed bonus earned only by"
            " a measurement that **actually ran on a card of that size or smaller**. A 32 GB figure can never"
            " top the 8 GB table, and a datacenter measurement never appears at all. The tables are"
            " **cumulative** (`Up to 16 GB` includes every model with evidence at 16 GB or below) and place a"
            " model only with evidence: a proved `ran on` figure, or the labelled `weights-only` fit. A model"
            " with no post in the window is not trending — it keeps its row in"
            " [🖥️ Pick your card](#-pick-your-card--what-fits-your-vram) below.",
            "",
        ]
        for t in CARD_TIERS_GB:
            rows = tier_trending_rows(models, t, registry)
            parts.append(f"### Up to {t} GB")
            parts.append("")
            if not rows:
                parts.append(f"_No trending model has evidence at {t} GB yet. That is a **collection gap, not"
                             f" \u201cnothing fits\u201d**: the search legs must ask for these cards"
                             f" (`skills/gather-data.md`, issue #337)._")
                parts.append("")
                continue
            parts.append("| Model | Trend | Best t/s that fits — engine · hardware · quant · date | VRAM |")
            parts.append("|---|---|---|---|")
            for score, m, e, ev in rows:
                _score, bonus, _best = tier_trend(m, t, registry)
                if e is not None:
                    det = detail(e)
                    date = f" · {e['date']}" if e.get("date") else ""
                    best_cell = f"**{e['tps']}** t/s<br>{elink(e['engine'])}" + (f" · {det}" if det else "") + date
                else:
                    w, tag = weights_gb(m, next((x for x, _ in tier_measurements(m, t, registry)), {}))
                    best_cell = (f"<sub>weights-only {_fmt_num(w)} GB ({tag}) — no measured run at this size</sub>"
                                 if w is not None else "<sub>weights-only — no measured run at this size</sub>")
                parts.append(f"| [**{m['name']}**]({hf_url(m)}) | {tier_trend_cell(m, score, bonus, e)}"
                             f" | {best_cell} | {vram_cell(m)} |")
            parts.append("")
        return "\n".join(parts)

    trending_card = trending_card_section()

    # ---- 1b. pick your card (issue #337) ------------------------------------
    # The card owner's entry point: pick your VRAM, see the fastest model that
    # fits it. Derived from the SAME evidence ladder the most-loved VRAM cell
    # uses (rule 6d), so the two can never disagree; an empty tier is reported as
    # a collection gap instead of reading as "nothing fits your card".
    def card_section() -> str:
        parts = [
            "## 🖥️ Pick your card — what fits your VRAM",
            "",
            "Jump to your card: " + " · ".join(f"[{t} GB](#{t}-gb)" for t in CARD_TIERS_GB)
            + " · **above that:** " + " · ".join(f"[{t} GB](#{t}-gb)" for t in HIGH_TIERS_GB) + ".",
            "",
            "A model is listed in a tier only with **evidence**: *ran on* a card of that size — a real measured"
            " figure — or *weights-only*, where only the weight footprint fits and the KV cache and overhead are"
            " unknown (labelled, never sold as a fit). A measurement on a bigger card does not qualify a smaller"
            " tier, because what it needed there is unknown. Apple Silicon and CPU are judged by unified memory /"
            " RAM: see [🟩 Metal](#-metal--apple-silicon-unified-memory) and [🟨 CPU](#-cpu--no-gpu).",
            "",
            f"The low end this list is for is a **gaming laptop — {LOW_END_TIERS_GB[0]}\u2013{LOW_END_TIERS_GB[-1]} GB of"
            " VRAM**; 32/48 GB is the workstation step above it, and anything bigger is unified memory or datacenter"
            " hardware, never a card tier.",
            "",
        ]
        for t in CARD_TIERS_GB:
            rows = tier_rows(models, t, registry)
            parts.append(f"### {t} GB")
            parts.append("")
            if not rows:
                parts.append(f"_No measurement with evidence at {t} GB yet. That is a **collection gap, not"
                             f" \u201cnothing fits\u201d**: the search legs must ask for these cards"
                             f" (`skills/gather-data.md`, issue #337)._")
                parts.append("")
                continue
            parts.append("| Model | Best t/s that fits | Backend | Engine · hardware · quant · date | Evidence |")
            parts.append("|---|---|---|---|---|")
            for tps, m, e, ev in rows:
                b = measurement_backend(e, registry)
                det = detail(e)
                date = f" · {e['date']}" if e.get("date") else ""
                cell = f"{elink(e['engine'])} **{e['tps']}**" + (f" · {det}" if det else "") + date
                if ev == "ran-on":
                    ev_txt = f"ran on ≤{t} GB"
                else:
                    w, tag = weights_gb(m, e)
                    ev_txt = (f"weights-only {_fmt_num(w)} GB ({tag}), KV cache unknown"
                              if w is not None else "weights-only")
                more = sum(1 for _e, _ev in tier_measurements(m, t, registry) if _ev == "ran-on") - 1
                if more:
                    ev_txt += f"<br><sub>+{more} more measured at this size</sub>"
                parts.append(f"| [**{m['name']}**]({hf_url(m)}) | {_fmt_num(tps)} |"
                             f" {BACKEND_LABEL[b][0]} {b} | {cell} | {ev_txt} |")
            parts.append("")
        # Above 48 GB (issue #572): a card owner stops at 48 GB, so these tiers
        # answer a different question — "what runs on the machine I have" — and a
        # model appears only when its evidence says it needs MORE than 48 GB.
        parts.append("**Above 48 GB** — there is no consumer card up here: the memory is **unified**"
                     " (Apple Silicon, a large APU), a **multi-GPU workstation**, or **datacenter"
                     " hardware**. A model is listed only when its evidence says it needs more than"
                     f" {MAX_SCOPE_VRAM_GB} GB, so a run that fits a card stays in the tiers above.")
        parts.append("")
        for t in HIGH_TIERS_GB:
            rows = high_tier_rows(models, t, registry)
            parts.append(f"### {t} GB")
            parts.append("")
            parts.append(f"_Typically {HIGH_TIER_LABELS[t]}._")
            parts.append("")
            if not rows:
                parts.append(f"_Nothing in the store has evidence of needing more than"
                             f" {MAX_SCOPE_VRAM_GB} GB and fitting {t} GB — a **collection gap, not"
                             f" \u201cnothing runs\u201d**._")
                parts.append("")
                continue
            parts.append("| Model | Best t/s that fits | Backend | Engine · hardware · quant · date | Evidence |")
            parts.append("|---|---|---|---|---|")
            for tps, m, e, ev in rows:
                b = measurement_backend(e, registry)
                det = detail(e)
                date = f" · {e['date']}" if e.get("date") else ""
                cell = f"{elink(e['engine'])} **{e['tps']}**" + (f" · {det}" if det else "") + date
                if ev == "ran-on":
                    total = total_memory_gb(e)
                    ev_txt = f"ran on {_fmt_num(total)} GB total"
                else:
                    w, tag = weights_gb(m, e)
                    ev_txt = (f"weights-only {_fmt_num(w)} GB ({tag}), KV cache unknown"
                              if w is not None else "weights-only")
                more = sum(1 for _e, _ev in high_tier_measurements(m, t, registry)
                           if _ev == "ran-on") - 1
                if more:
                    ev_txt += f"<br><sub>+{more} more measured at this size</sub>"
                parts.append(f"| [**{m['name']}**]({hf_url(m)}) | {_fmt_num(tps)} |"
                             f" {BACKEND_LABEL[b][0]} {b} | {cell} | {ev_txt} |")
            parts.append("")
        return "\n".join(parts)

    card_fit = card_section()

    # ---- 2. engine matrix ----------------------------------------------------
    measured: dict[str, set] = {}
    for m in models:
        for e in m.get("engines", []):
            measured.setdefault(e.get("engine", ""), set()).add(m["id"])
    engines_cols = sorted((k for k in measured if k), key=lambda k: (-len(measured[k]), k.lower()))
    matrix_lines = ["| Model | " + " | ".join(elink(k) for k in engines_cols) + " |",
                    "|---|" + "---|" * len(engines_cols)]
    for m in models:
        cells = []
        for k in engines_cols:
            parts = []
            for b in BACKENDS:
                best = best_measurement([e for e in m.get("engines", [])
                                         if e.get("engine") == k and measurement_backend(e, registry) == b])
                if best:
                    parts.append(f"{BACKEND_LABEL[b][0]} {best['tps']}")
            cells.append("<br>".join(parts) or "—")
        matrix_lines.append(f"| **{m['name']}** | " + " | ".join(cells) + " |")
    engine_matrix = "\n".join(matrix_lines) if engines_cols else "_No engine measurements yet._"

    # ---- 3. backend tables ---------------------------------------------------
    def backend_table(b: str) -> str:
        emoji, title = BACKEND_LABEL[b]
        rows = []
        for m in models:
            es = by_backend(m)[b]
            if not es:
                continue
            es = sorted(es, key=lambda e: (_tps_core(e.get("tps")), e.get("date", "")), reverse=True)
            meas = []
            for e in es:
                t = f"{elink(e['engine'])} **{e['tps']}**"
                if detail(e):
                    t += f" · {detail(e)}"
                if e.get("date"):
                    t += f" · {e['date']}"
                meas.append(t)
            peak = max(_tps_core(e.get("tps")) for e in es)
            rows.append((peak, m, "<br>".join(meas)))
        rows.sort(key=lambda r: -r[0])
        lines = [f"# {emoji} {title}", "",
                 "| Model | Params | License | VRAM | Peak t/s | Measurements (engine · t/s · hardware · quant · date) |",
                 "|---|---|---|---|---|---|"]
        if not rows:
            lines.append("_No models measured on this backend yet._")
        for peak, m, meas in rows:
            lines.append(
                f"| [**{m['name']}**]({hf_url(m)}) | {m.get('params') or '—'} | {m.get('license') or '—'} "
                f"| {m.get('vram_tier') or '—'} | {_fmt_num(peak)} | {meas} |"
            )
        return "\n".join(lines)

    tables = {b: backend_table(b) for b in BACKENDS}
    cuda_md, metal_md, cpu_md, rocm_md = (tables[b] for b in ("CUDA", "Metal", "CPU", "ROCm"))
    loved_hdr = " | ".join(f"{b} t/s (best)" for b in BACKENDS)
    legend = " · ".join(f"{BACKEND_LABEL[b][0]} {b}" for b in BACKENDS)

    # ---- 4. engine guide -----------------------------------------------------
    engine_guide = "\n".join(
        f"| [{k}]({v.get('url', '')}) | {v.get('backend', '—')} | {len(measured.get(k, ()))} | {v.get('note', '—')} |"
        for k, v in registry.items()
    )

    now_s = now_utc().strftime("%Y-%m-%d %H:%M UTC")

    return f"""# Trending Local LLMs

A living, detailed list of **open-weight** LLMs that actually make a difference for local deployment. Every figure is **community-reported on X** (real benchmark posts, not vendor claims), with the hardware and engine it was measured on. This README is **automatically regenerated** from `data/models.json` — see [AGENTS.md](AGENTS.md) and `skills/gather-data.md`.

**How the ranking works.** Models are grouped 🔥 **trending** (seen in the last {TRENDING_WINDOW_DAYS} days) → 🕑 **recent** (last {RETENTION_DAYS} days) → 💤 **stale** (older, kept with their last measurement date). Within a group they rank by **Trend = buzz + speed**:
- **buzz** — for every distinct X post in the last {TRENDING_WINDOW_DAYS} days: 1 + 0.5×log2(1 + likes + 2×comments + 3×reshares) + 0.25×log10(1 + views). Every post counts, so a model many people are posting about beats one post with a few interactions; engagement adds on top with diminishing returns.
- **speed** — log2(1 + t/s ÷ 10) for the model's fastest measurement on consumer hardware (GPUs up to {MAX_SCOPE_VRAM_GB} GB, Apple Silicon, CPU; datacenter parts never count), only while it is trending: 10 t/s → +1, 70 → +3, 150 → +4.

Ties go to more posts, then the highest t/s. t/s is always shown **per engine**, with the hardware and quant it was measured on.

> Last generated: {now_s}. Source: lightbrd.com mirror (X posts).

---

{trending_card}

---

## ❤️ Most loved open-weight models on X (ranked by trend: 7-day buzz + speed)

The **No limit** view: every model in rank order, whatever card it was measured on. Best measured t/s per backend, on consumer/workstation hardware (a datacenter figure is never a "best" cell); the full list of measurements is in the backend tables below. The **VRAM** column is the least amount needed to run the model, with the evidence behind that claim and the card its headline figure came from.

| Model | Status | Trend | {loved_hdr} | VRAM | Why people love it |
|---|---|---|{"---|" * len(BACKENDS)}---|---|
{most_loved}

---

{card_fit}

---

## 🧭 Which inference engine runs what

Best measured t/s per model on each engine ({legend}). Only engines with at least one measurement are shown.

{engine_matrix}

---

{cuda_md}

---

{rocm_md}

> AMD figures land here by **hardware** (Radeon / RX / Strix Halo / ROCm), whichever API ran them: ROCm/HIP (vLLM, SGLang, Ollama, llama.cpp `GGML_HIP`) or Vulkan (llama.cpp `GGML_VULKAN`, often the faster llama.cpp path on consumer Radeon). Vulkan on an NVIDIA card stays in the CUDA table.

---

{cpu_md}

> CPU inference is **memory-bandwidth bound**. Use Q4 quant + a fast CPU build (AVX-512/AMX).

---

{metal_md}

> On Apple Silicon, **MLX** is the fastest engine; **TensorFold** adds speculative decoding (3–6x on memory-bound Macs); **MLX-fast Bonsai 2** (Layr-Labs/mlxfast-bonsai2-27b-engine) pushes Ternary Bonsai 2 27B to ~237 tok/s on a 16 GB Mac.

---

## ⚙️ Inference engine / server guide

| Engine | Backend | Models measured | Best for |
|---|---|---|---|
{engine_guide}

**Quick picks:** Ollama (just works) · llama.cpp (gaming laptop, max speed) · FreeToken (big MoE on small GPU) · MLX + TensorFold + MLX-fast (Mac) · Strata (125B MoE on 12–24 GB) · vLLM + DFlash2 (spec decode) · llama.cpp Vulkan / ROCm (AMD Radeon) · llama.cpp CPU (tiny/edge).

---

## How to contribute

- Update `data/models.json` (add/refresh a model row with real X-sourced engagement and per-engine t/s), then run `python3 scripts/update_trending.py` to regenerate the README.
- Include: full model name, HF link, license, params, type, VRAM tier, a **measured** t/s + **engine + hardware + quant**, and the source X post (a `…/status/<id>` URL, so engagement is counted once per post).
- Prefer numbers from real X benchmark posts over vendor claims. Data is **community-reported on X** — directional, not lab-grade; mark projections `(est)`.
- **Additive only:** never remove or rename a key and never shrink a value — `validate` (`check_no_value_loss`) fails any key, measurement, t/s or engagement counter that was in the previous snapshot and is gone from the store. Add new keys as optional, never as a new `required` entry.
- **Never commit a credential:** run `make secret-scan` before you push — gitleaks scans the working tree and a finding blocks the push. Remove the value and rotate the key; never allowlist a real one.
- **Keys reach Hermes by NAME only (never baked, never a literal):** every credential is injected as `-e <ENV_NAME>` on the `docker run` (see `DOCKER_RUN` / `TEST_RUN` in the Makefile) and read back through the env / Hermes secret scope — never an `ENV` in an image layer, never a value in `config.yaml`, never a literal in a `hermes config set` argument. A plugin's credential follows the same rule under the name **the plugin actually resolves** (verified against its pinned source, never guessed): the nerve plugin baked into the image runs provider `typesafe` (the setting this setup uses, not the plugin's own default) and so reads `TYPESAFE_API_KEY` (`OPENROUTER_API_KEY` / `OPENCODE_API_KEY` are its other providers). `make nerve-check` proves the wiring and that a run without the key fails loudly instead of degrading. The live pre-flight checks follow the same rule: `make hermes-smoke` and `make model-caps` **fail** when `NOUS_API_KEY` is unset rather than reporting a green result that proved nothing — a caller deliberately running without a key sets `LIVE_CHECK_ALLOW_UNCONFIGURED=1`, which no workflow sets.
- **Runner images:** `make image-ensure` prepares what this repo runs — it PULLS the published base + test images when they were built from this revision's `Dockerfile` / `Dockerfile.test` (the CI path, no rebuild) and otherwise builds them here; `make image-ensure-base` when only the base is needed, `make docker-build` / `make docker-test-build` to build unconditionally, and `make image-tags` to print the tags the decision reads. `refresh-bot` publishes both tags (base `:dockerfile-<hash>`, test `:test-<hash>`) weekly, when the hash changed, or on a `force_rebuild` dispatch — the decision itself is data (`make rebuild-decision` → `scripts/ensure_image.py decide`, printed as `built`/`test_built`/`publish_openspec` + reasons), so every branch is covered by tests instead of being observable only by running the pipeline. The base image **is** the agent image, so publishing it on purpose has its own pipeline: `Publish agent image` (dispatch only, owner/collaborator guard first, the default token) runs `make agent-image-push-check` — which proves the credential can write the package in seconds instead of after the build — then `make publish-agent-image`, a no-op when this revision's tag is already published. `make agent-image-ref` prints the refs. The base image **is** the agent image — it bakes the Hermes CLI — so it proves what it carries: the CLI enters through ONE seam (`scripts/install_hermes_ci.sh`, `ARG HERMES_INSTALL_URL` / `ARG HERMES_PACKAGE`, and `make _setup` runs the same file), and the build writes the model alias and then runs `make _hermes-alias-check`, which fails the BUILD on a wrong model, a provider that is not `custom` or a `key_env` that is not `NOUS_API_KEY` (without it a bad pin only surfaced inside a bot run: no alias → `HF_TOKEN` → `HTTP 403`). The OpenSpec CLI runs in its own image too (`make openspec-image`, published as `-openspec:openspec-<hash>` on the same rule), so `make openspec-*` never needs a host `npm install` and CI runs the same CLI you do.
- **Spec-tracked changes (OpenSpec):** every change starts as a tracked change — `make openspec-new NAME=<kebab-name>` creates `openspec/changes/<name>/`, you write `proposal.md` (Why / What Changes / what is **not** covered), a capability spec `specs/<capability>/spec.md` (each Requirement with a Given/When/Then Scenario and a `- **Test:**` line naming the test that locks it) and `tasks.md` (a `- [ ]` checklist, ticked as each step is verified). `make openspec-check` is the gate — every active change validates (`make openspec-validate NAME=…` for one), no box is unticked (`make openspec-tasks-check`) and the index below is current — and CI runs it on every PR. `make openspec-status` shows every change; `make openspec-archive NAME=…` moves a finished one to `openspec/changes/archive/`.
- **The index — `OPENSPEC.md`:** the one file at the repo root that references every change this repo has made (active and archived: issue, PR, capability specs, `ticked/total` tasks). It is **generated**: `make openspec-index` rewrites it, `make openspec-index-check` fails when it is stale or a change on disk has no row, so a change cannot land unlisted.
- **Analysis ships issues, never code:** an implementation run records what it noticed in `findings.md` (one `## <title>` section per finding with `Evidence:` / `Why:` / `Done when:`, or `- none`) — `make findings-check` fails loudly when that analysis is missing, and `make file-findings` files one issue per finding (label `tech-debt`, deduped by an invisible signature, linked to the issue and PR it came from). Findings are never fixed inside the change that found them: they get their own issue, OpenSpec change and review.
- **Two bots, one queue — and a quiet window (issue #179):** `issue-bot` implements ONE open `data-gap-analysis` issue per hour (the oldest with no implementer) and **announces its window** with a start comment before it reads the body. The issue reviewer (`issue-review-bot.yml`, hourly at `41`) reads the SAME queue (`make issue-queue`) and refines the issues nobody has started: it will not touch a body inside `REVIEW_GAP_HOURS` (3 h) around an implementer start — 3 hourly sweeps before it, a run in flight, or a start within the last 3 h. When an implementer HAS started, the body stays off-limits: the reviewer posts ONE bounded reply with the reminders its review found and files what it found as its own `tech-debt` issues (`make findings-check` + `make file-findings`). A **verdict is a hold, not advice**: while the reviewer's own verdict label (`needs-refinement`, or the `obsolete`/`duplicate`/`already-fixed` family) is younger than `VERDICT_TTL_HOURS` (24 h) — measured from the reviewer's newest marker comment, because a label carries no timestamp — the sweep takes another issue and says so ON the held one (`make issue-skip-note`, one comment per review round). It writes no label and edits no body: the answer to a verdict is a comment. Drive it by hand with `make issue-queue` (the shared queue), `make issue-skip-note` (the verdict hold), `make review-issue-pick`, `make review-issue` (refine) / `make review-issue-window` (reply) and `make review-issue-finish`. **The implementer reads the WHOLE thread** (`make issue-thread`: body + every comment with author and timestamp) and decides first: `make issue-verdict` applies its verdict — `refine` posts one restatement and labels the issue `agent:refined`, `close` posts the reason with its cited evidence, closes and labels it `agent:closed` (a close without evidence is refused and the run fails), and only `implement` continues to a PR. A decided issue is skipped by the sweep through the shared queue rule.
- **A stuck `queued` job is loud (issue #252):** a job whose runner label matches nothing does **not** fail — GitHub leaves it `queued` forever, so the run never concludes and every PR's checks sit at "pending" with no signal. `queued-alarm.yml` (twice an hour at `:07`/`:37`, dispatch too) runs `make queued-alarm`: `scripts/queued_run_alarm.py` lists the jobs still `queued` past `MINUTES` (default 30), prints a table naming the runner label and the age, and with `COMMENT=1` leaves ONE marker-deduplicated note on each affected run. It exits 1 when a job is stuck, so the scheduled run goes red. Deterministic, no model; it never edits code, opens a PR or merges.
- **The searches ask for the models we rank (issue #264):** the refresh's queries used to be a fixed keyword list that named no model — of 24 queries the ONE model-specific one named `qwen3.8-27b`, and none named `Strata` — so every figure for the model topping this list arrived incidentally, and a higher one upstream could never enter. Now each of the top `QUERY_TOP_N` (10) trending models gets a query naming it by its own id, derived from the store by ONE implementation (`scripts/update_trending.py`, rule 6d) and appended to every search leg as `$(MODEL_QUERIES)`; the hand-curated queries are kept. `make query-coverage` prints which models the curated set alone reaches vs the full set, and **fails** when a trending model is named by no query, so the gap is loud instead of looking like "the query ran and found nothing". Today the curated set alone names 1 of the top 10; the full set names all 10.
- **A code-review bot reads the tree and the pipelines and files what is wrong (issue #253):** `code-review-bot.yml` (weekly Monday `07:23`, dispatch too) runs `make code-review-scan` then `make code-review-file` (`scripts/code_review.py`). Every check is **deterministic** (no model), so a scan is free and cannot invent a finding: a `run:` that reaches into `scripts/` instead of calling a `make` target, a workflow reading a `secrets.X` the repo does not define, a workflow that has never run, a `workflow_call` file nothing references, two fixed crons in one minute+hour slot. It files ONE issue per new finding, deduped by an invisible `<!-- code-review:<key> -->` marker and capped per run; a re-run on an unchanged tree is silent. Analysis, never implementation: it never edits a file, never opens a PR, never merges, never comments on anyone's PR.
- **The description — `ARCHITECTURE.md`:** how this repo works — the data flow, every `make` target (with the image it runs in), every job of every pipeline and its gates, the three runner images and their content-hash tags, every script, and the life of a change. It is part of the change (AGENTS.md rule 6h): a change that adds, renames or removes a target, a pipeline job, an image or a script MUST update it in the same change, and `make architecture-check` (CI) fails when the file and the repository disagree.
- **Linefeeds:** every tracked text file ends with a newline — `make lint` is the gate (the first step of the PR's `validate` job and the first check in the fix loop) and `make lint-fix` appends what is missing; `.editorconfig` carries the same rule for your editor. A file without a final newline makes git print `\\ No newline at end of file` and turns the next append into a spurious last-line change.
- **QA before a refresh lands:** `make qa-report` runs the aggregate job's QA targets — a *finding* (data quality) is reported, but a target that **could not run** (no image / no such command) fails the run, so a green refresh means the checks actually ran.
- All changes go through a **feature branch + PR**; automation never pushes to `master`. A PR is auto-merged (squash, branch deleted) only when CI (`validate` + `live-smoke`) is green.

## License

Apache License 2.0. See [LICENSE](LICENSE).
"""

def write_snapshot(store: dict) -> Path:
    """Write a timestamped snapshot of the store to data/snapshots/.
    Keeps a full history so the README can be rebuilt from any point and so
    the QA step can prove no model was ever removed."""
    SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
    ts = now_utc().strftime("%Y%m%d-%H%M%S")
    path = SNAPSHOT_DIR / f"trending-{ts}.json"
    path.write_text(json.dumps(store, indent=2, ensure_ascii=False) + "\n")
    return path

_HF_URL_PREFIX = "https://huggingface.co/"


def normalize_hf_ref(value):
    """Collapse a Hugging Face URL written where a bare repo id belongs back to
    the repo id: 'https://huggingface.co/Qwen/Qwen3-14B' -> 'Qwen/Qwen3-14B'.
    A DOUBLED prefix is collapsed too — the search agent pastes the whole URL
    the README builds, and 'https://huggingface.co/https://huggingface.co/X'
    made every raw-hf link 404 (validate builds the URL by prefixing the field
    itself, so the raw snapshot carried the prefix twice). Non-strings and
    already-bare ids pass through unchanged."""
    if not isinstance(value, str):
        return value
    v = value.strip()
    while v.startswith(_HF_URL_PREFIX):
        v = v[len(_HF_URL_PREFIX):]
    return v.strip("/")


def write_raw_snapshot(backend: str, payload: dict) -> Path:
    """Write one backend's raw search findings to data/raw/<backend>-<UTC>.json.
    Each of the four Hermes search prompts (NVIDIA, Metal, CPU, AMD) writes its own
    timestamped file here; never overwrite another backend's file."""
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    ts = now_utc().strftime("%Y%m%d-%H%M%S")
    safe = re.sub(r"[^A-Za-z0-9_-]", "-", backend).lower()
    path = RAW_DIR / f"{safe}-{ts}.json"
    # Searches write once PER QUERY now, so two writes can land in the same
    # second: never overwrite, suffix -2, -3 ... (backend stays the first
    # '-'-separated token of the name, which self_correct_raw relies on).
    n = 2
    while path.exists():
        path = RAW_DIR / f"{safe}-{ts}-{n}.json"
        n += 1
    payload = dict(payload)
    # an `hf` field is a bare repo id (validate/README build the URL by
    # prefixing it) — collapse a full URL / doubled prefix BEFORE it lands in
    # data/raw, so a pasted URL can never 404 the raw-hf link check again.
    for _m in payload.get("models") or []:
        if not isinstance(_m, dict):
            continue
        if _m.get("hf"):
            _m["hf"] = normalize_hf_ref(_m["hf"])
        # The id must satisfy the store contract, or the raw snapshot fails
        # `search_contract` before ingest can even see it (issue #464: a leg wrote
        # `qwen3.8-27b-mlx_srv`).
        _id = str(_m.get("id") or "")
        if _id and not ID_PATTERN.match(_id):
            _fixed = contract_id(_id) or _slug(_m.get("name") or _id)
            print(f"[write-raw] id normalised {_id!r} -> {_fixed!r} (contract pattern)")
            _m["id"] = _fixed
        for _f in _m.get("formats") or []:
            if isinstance(_f, dict) and _f.get("hf"):
                _f["hf"] = normalize_hf_ref(_f["hf"])
    payload.setdefault("generated_utc", now_utc().strftime("%Y-%m-%dT%H:%M:%SZ"))
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n")
    return path

def _collect_seen_posts(m: dict) -> list[dict]:
    """Derive engagement.seen_posts from a model's engine measurements: one
    entry per distinct source_post URL, dated by the measurement date. This is
    the post-granularity signal that powers the 7-day trending aggregation."""
    out = []
    for e in m.get("engines", []):
        url = e.get("source_post", "")
        if not url or not e.get("date"):
            continue
        p = {"url": url, "date": e["date"], "engine": e.get("engine", ""), "tps": str(e.get("tps", "")),
             "hardware": e.get("hardware", "") or "", "quant": e.get("quant", "") or ""}
        for k in _POST_SIGNALS:
            try:
                p[k] = max(0, int(float(e.get(k) or 0)))
            except (TypeError, ValueError):
                p[k] = 0
        out.append(p)
    return dedupe_posts(out)

_RAW_FILENAME_STAMP = re.compile(r"-(\d{8})-(\d{6})(?:-\d+)?\.json$")

def parse_utc_stamp(value) -> datetime | None:
    """Parse a `generated_utc` stamp (`YYYY-MM-DDTHH:MM:SSZ`) into a tz-aware
    datetime. None when it is missing or unparseable, so a caller can treat
    "no usable stamp" as fail-open rather than guess a time."""
    if not isinstance(value, str) or not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    except ValueError:
        return None

def raw_snapshot_stamp(path: Path, data: dict | None = None) -> datetime | None:
    """The instant a raw snapshot was captured: its own `generated_utc` when
    that parses, else the `<YYYYMMDD>-<HHMMSS>` stamp its writer put in the
    filename (`write_raw_snapshot`). None when neither parses — the caller
    then reads the file, so a snapshot this code cannot date is never silently
    dropped. The field is preferred over the name because `self_correct_raw`
    refreshes it when it corrects a snapshot, and a corrected snapshot must be
    re-merged rather than skipped as "old"."""
    if isinstance(data, dict):
        stamp = parse_utc_stamp(data.get("generated_utc"))
        if stamp is not None:
            return stamp
    m = _RAW_FILENAME_STAMP.search(path.name)
    if not m:
        return None
    try:
        return datetime.strptime(m.group(1) + m.group(2), "%Y%m%d%H%M%S").replace(tzinfo=timezone.utc)
    except ValueError:
        return None

HF_MODEL_API = "https://huggingface.co/api/models"


def hf_repo_resolves(repo_id) -> bool | None:
    """True for a Hugging Face repo id that answers, False only when the answer
    is DEFINITIVE (401/404), None when the check could not tell (no id, a
    transport error, 403/429/5xx). A rate-limited or briefly-down API must never
    be reported as a bad link — the whole point is to name a guessed id, not to
    add a flaky failure.

    `HF_MODEL_API` overrides the endpoint (tests point it at a local server)."""
    if not isinstance(repo_id, str) or "/" not in repo_id.strip("/"):
        return None
    base = os.environ.get("HF_MODEL_API", HF_MODEL_API)
    req = urllib.request.Request(f"{base.rstrip('/')}/{repo_id.strip('/')}",
                                 headers={"User-Agent": "trending-local-llms"})
    tok = os.environ.get("HF_TOKEN")
    if tok:
        req.add_header("Authorization", f"Bearer {tok}")
    try:
        with urllib.request.urlopen(req, timeout=10):
            return True
    except urllib.error.HTTPError as e:
        return False if e.code in (401, 404) else None
    except (urllib.error.URLError, TimeoutError, ValueError, OSError):
        return None


def note_unresolved_hf(model: dict) -> None:
    """Name a NEW model's Hugging Face repo that does not resolve, in the run
    that produced it (issue #333).

    `check_links_resolve` already fails the PR on a dead link, but that is the
    first moment anyone sees it, and by then the refresh has opened a PR whose
    only repairer is a bot round. One line here makes a guessed id visible in the
    refresh run itself. Report-only: a guessed id costs a fix round, not a
    blocked refresh."""
    ids = []
    if model.get("hf"):
        ids.append(("hf", model["hf"]))
    for f in model.get("formats") or []:
        if isinstance(f, dict) and f.get("hf") and f["hf"] != model.get("hf"):
            ids.append(("format-hf", f["hf"]))
    for kind, repo in ids:
        if hf_repo_resolves(repo) is False:
            print(f"[ingest] HF {kind} {repo!r} does NOT resolve ({model.get('id')}) "
                  f"— the link check will fail this PR")


#: Shapes that can only be a QUANT or a format, never an inference-engine name.
_QUANT_SHAPE = re.compile(
    # `exl\d+` needs a DIGIT: `ExLlamaV3` is a real registered engine, and a bare `exl`
    # with zero-or-more digits refused it whenever the registry was not consulted.
    r"(?:nv|mx)?fp\d+|bf16|fp16|fp32|int[48]|awq|gptq|gguf|exl\d+|w\d+a\d+|q[2-8](?:_[a-z0-9]+)*", re.I
)
#: Shapes that can only be HARDWARE, never an inference-engine name (issue #458, second
#: measured shape). `Bonsai Oryon` was written for `bonsai-2-9b` on 2026-10-20: Oryon is
#: Qualcomm's CPU core, so the name was manufactured from the model plus the CPU — and it
#: carries no quant token, so `_QUANT_SHAPE` alone could not see it. The boundaries matter
#: in BOTH directions: `strixite` is a real engine and must not match `strix`.
_HW_SHAPE = re.compile(
    r"\b(?:oryon|snapdragon|ryzen|epyc|xeon|radeon|geforce|rtx|gtx|instinct|dgx|"
    r"strix(?![a-z])|halo|apple\s+m\d|m[1-5]\s*(?:max|ultra|pro))\b",
    re.I,
)


def _flat_token(value: object) -> str:
    """Case-folded, punctuation-free form, so `FP4-Local` and `Qwen3.8-Flash-Next-FP4-Local`
    are compared as tokens instead of spellings."""
    return re.sub(r"[^a-z0-9]", "", str(value or "").lower())


def fabricated_engine_reason(engine: object, model: dict, registry: dict) -> str | None:
    """Why `engine` cannot be a real engine name — or None when it could be (issue #458).

    Only a name that is PROVABLY derived from the model or the quant is refused. A genuine
    engine that is simply not registered yet (`SomeRealServe`, engine_repo fetched or not)
    returns None and keeps reding `make validate` for a human — that is the documented
    behaviour and this guard must not swallow it.
    """
    name = str(engine or "").strip()
    if not name or name in (registry or {}):
        return None
    # ONLY a provable shape is refused: a QUANTIZATION token in the engine name. An
    # engine name never contains FP4/NVFP4/Q4_K_M/AWQ/GGUF, so that alone proves the name
    # was manufactured from the quant. A model-name SUBSTRING is NOT proof — measured while
    # building this: `WebLLM` is a real engine that appears inside
    # `Llama-3.1-8B (WebLLM)` and heads `webllm-llama-3.1-8b-inbrowser`, and a substring
    # rule refused a legitimate measurement (tests/test_7day_aggregation.py). A genuinely
    # unknown engine must keep failing validation for a human instead.
    quant = _QUANT_SHAPE.search(name)
    if quant:
        return f"the name carries the quantization token {quant.group(0)!r}"
    hw = _HW_SHAPE.search(name)
    if hw:
        return f"the name carries the hardware token {hw.group(0)!r}"
    return None


def refuse_fabricated_engines(
    model: dict, registry: dict
) -> tuple[list[dict], list[tuple[str, str, str]]]:
    """Split a model's measurements into (kept, [(engine, why, source_post)] refused).

    The post travels with the refusal so the log line names the thing a human can open.
    """
    kept: list[dict] = []
    refused: list[tuple[str, str, str]] = []
    for e in model.get("engines") or []:
        why = fabricated_engine_reason(e.get("engine"), model, registry)
        if why:
            refused.append((str(e.get("engine")), why, str(e.get("source_post") or model.get("source_post") or "unknown")))
        else:
            kept.append(e)
    return kept, refused


def ingest_raw_snapshots(store: dict, since: datetime | None = None,
                         verify_hf: bool = False) -> tuple[int, int]:
    """Merge the data/raw/*.json snapshots NEWER than `since` into the store.
    Each raw file holds one backend's captured findings (models). New models are
    added, existing ones updated, NONE removed. Returns (added, updated).

    `since` is the store's own `generated_utc` — the instant of the last merge —
    which `main()` derives for every run. Only a snapshot STRICTLY NEWER than it
    is merged: one captured at or before that instant was already folded in, so
    re-merging it adds nothing — and doing so anyway made the cost of a refresh
    grow with the whole raw history ("5 added, 210 updated" on a store that
    contained all but 5 of the models, issue #175) while hiding which file
    actually introduced a change. A snapshot this code cannot date is always
    merged (fail-open), never silently dropped."""
    added = updated = 0
    if not RAW_DIR.exists():
        return 0, 0
    by_id = {m["id"]: m for m in store["models"]}
    for path in sorted(RAW_DIR.glob("*.json")):
        try:
            data = json.loads(path.read_text())
        except Exception as e:  # noqa: BLE001
            print(f"[warn] skipping raw {path.name}: {e}")
            continue
        if since is not None:
            stamp = raw_snapshot_stamp(path, data)
            if stamp is not None and stamp <= since:
                continue
        # New engines: auto-register a real inference engine from the
        # measurement's engine_repo (GitHub, classified), never a harness/app;
        # strips engine_repo so the store contract never sees it.
        try:
            sys.path.insert(0, str(ROOT / "scripts"))
            import engine_registry as _er
        finally:
            sys.path.pop(0)
        for d in _er.register_new_engines(store, data.get("models", [])):
            print(f"[ingest] engine {d['engine']!r}: {d['decision']} — {d['reason']}")
        # A FABRICATED engine never becomes data (issue #458). The search legs are told by
        # NAME never to write a model name or a quantization as the engine (Makefile
        # ENGINE_ASK, #378), and the metal leg wrote `FP4-Local` for
        # bdambrosio/status/2111548404866433346 anyway on 2026-10-20 — reding the refresh
        # PR for the second day running. A prompt is necessary and not sufficient, so the
        # refusal happens where the value would enter the store, loudly and by name.
        for m in data.get("models", []):
            kept, refused = refuse_fabricated_engines(m, store.get("engines", {}))
            if refused:
                m["engines"] = kept
                for name, why, post in refused:
                    print(
                        f"[ingest] REFUSED fabricated engine {name!r} on {m.get('id')}: {why}; "
                        f"post {post} — a t/s with no engine named by the post is not a valid "
                        f"entry (rule 5)"
                    )
        for m in data.get("models", []):
            mid = m.get("id")
            if not mid:
                continue
            if mid in by_id:
                # update existing: merge engines (replace t/s on same engine+date), keep rest
                existing = by_id[mid]
                # alias the incoming rows FIRST, so a raw 'llama.cpp' figure merges
                # with the stored fork rows instead of becoming a duplicate
                apply_engine_aliases(existing)
                incoming = apply_engine_aliases(existing, [dict(e) for e in m.get("engines", [])])
                existing["engines"] = merge_engines(existing.get("engines", []), incoming)
                apply_engine_aliases(existing)
                sync_backends(existing, store.get("engines", {}))
                # additive optional metadata (system_ram_min, weight_gb, ...):
                # fill only what is absent, never overwrite — the update path
                # used to drop these entirely, so a gap the contract had just
                # gained room for could never close on an existing model.
                merge_additive_fields(existing, m)
                existing["last_seen"] = now_utc().strftime("%Y-%m-%d")
                # merge post-granularity engagement, deduped by source_post URL
                eng = existing.setdefault("engagement", {})
                eng["seen_posts"] = dedupe_posts(
                    eng.get("seen_posts", []) + _collect_seen_posts(m)
                )
                eng["last_7d_likes"] = max(
                    existing["engagement"].get("last_7d_likes", 0),
                    m.get("engagement", {}).get("last_7d_likes", 0),
                )
                existing["engagement"] = prune_engagement(eng, mid)
                updated += 1
            else:
                model = normalize_model(m, store)
                # A model row carries its HF link (rule 5b, §4): a NEW model the search
                # wrote without an `hf` is REFUSED here, loudly, instead of being stored
                # as `formats[0].hf == ""` — which reds the PR on check_links_present and
                # is the same defect that aborted a whole refresh in self_correct_raw
                # (issue #381). The rest of the capture still merges, and this half holds
                # even when the merge runs BEFORE `correct-raw` (the aggregate's order).
                # Nothing is invented: the row is excluded, never given a guessed repo.
                if not normalise_hf(model.get("hf") or ""):
                    print(f"[ingest] REFUSED {mid!r}: hf missing and not derivable "
                          f"({path.name}) — a model row carries its HF link (rule 5b); "
                          f"the rest of the snapshot still merges")
                    continue
                by_id[mid] = model
                store["models"].append(model)
                added += 1
                if verify_hf:
                    note_unresolved_hf(model)
    return added, updated

def resolve_model_mapping(raw_model: dict, store: dict) -> dict:
    """Resolve a raw search model to the position it maps to in data/models.json.
    Priority across the WHOLE store: exact id first, then exact name, then exact
    hf (each case-insensitive). Returns {'status': 'existing'|'new',
    'id': <resolved or raw id>, 'matched_by': '<id|name|hf>' or ''}.
    This makes the raw->aggregated mapping explicit and verifiable."""
    res = {"status": "new", "id": raw_model.get("id"), "matched_by": ""}
    rid = (raw_model.get("id") or "").lower()
    rname = (raw_model.get("name") or "").lower()
    rhf = (raw_model.get("hf") or "").lower()
    models = store.get("models", [])

    # priority 1: exact id across all models
    for m in models:
        if rid and rid == (m.get("id") or "").lower():
            res = {"status": "existing", "id": m["id"], "matched_by": "id"}
            return res
    # priority 2: exact name across all models
    for m in models:
        if rname and rname == (m.get("name") or "").lower():
            res = {"status": "existing", "id": m["id"], "matched_by": "name"}
            return res
    # priority 3: exact hf across all models
    for m in models:
        if rhf and rhf == (m.get("hf") or "").lower():
            res = {"status": "existing", "id": m["id"], "matched_by": "hf"}
            break
    return res

def _gpu_size(hardware: str) -> str:
    """Normalize a hardware string to a canonical GPU identity so the same
    measurement reported with slightly different wording collapses. Priority:
    (1) a specific NVIDIA card model (RTX 4090, RTX 5090, ...) — the strongest
    signal; (2) a VRAM size ('<N>GB'); (3) a platform (Apple/Mac, CPU). Two rows
    with the same engine + t/s + this identity are the same measurement.
    Returns '' when nothing recognizable (kept as-is, distinct)."""
    hw = (hardware or "").lower()
    if _CPU_ONLY_RE.search(hw):
        return "cpu"
    m = re.search(r"rtx\s*(\d{3,4})\s*(ti)?", hw)
    if m:
        return f"rtx{m.group(1)}{m.group(2) or ''}"
    # AMD card identity (RX 7900 XTX vs RX 7900 XT are different cards); must
    # run before the 'amd' -> cpu rule below, which would otherwise collapse an
    # 'AMD Radeon RX 7900 XTX' figure with a CPU one.
    m = re.search(r"\b(?:rx\s*-?)?(\d{4})\s*(xtx|xt|gre)\b", hw) or re.search(r"\brx\s*-?(\d{3,4})()\b", hw)
    if m:
        return f"rx{m.group(1)}{m.group(2)}"
    if _AMD_APU_RE.search(hw):
        return "amd-apu"
    m = re.search(r"(\d+)\s*gb", hw)
    if m:
        return f"{m.group(1)}gb"
    if any(k in hw for k in ("apple", "mac", "m1", "m2", "m3", "m4", "m5", "m6", "mlx")):
        return "apple"
    if is_amd_gpu(hw):
        return "amd-gpu"
    if any(k in hw for k in ("cpu", "intel", "amd", "no gpu", "raspberry")):
        return "cpu"
    return ""

def _tps_core(tps) -> float:
    """High-end numeric core of a t/s string: the max number it contains. For
    a range ('67-71') this is 71, for an estimate ('~50') 50, for a comment
    ('233 (DFlash spec-decode)') 233."""
    nums = [float(x) for x in re.findall(r"\d+(?:\.\d+)?", str(tps or ""))]
    return max(nums) if nums else 0.0

def _eng_weight(m) -> float:
    """Engagement weight of a measurement — the composite X signal on its source
    post: likes + 2*comments + 3*reshares + log10(views+1). Reshares are the
    strongest (active endorsement + reach), comments next, likes passive, views
    log-scaled so a viral-but-unverified post can't dominate. Floor of 1 (a
    no-engagement post still counts once)."""
    import math
    likes = int(m.get("likes", 0) or 0)
    comments = int(m.get("comments", 0) or 0)
    reshares = int(m.get("reshares", 0) or 0)
    views = int(m.get("views", 0) or 0)
    return max(1.0, likes + 2 * comments + 3 * reshares + math.log10(views + 1))

def _concordant(a: float, b: float, tol: float = 0.12) -> bool:
    """Two t/s cores are the SAME measurement when within `tol` (5%) of the
    larger. 39.3 vs 39.5 -> concordant (averaged); 39.3 vs 45 -> distinct."""
    if b <= 0:
        return a == 0
    return abs(a - b) <= tol * max(a, b)

def _real_post(m: dict) -> str:
    """The model-agnostic identity of a POST: its `/status/<id>` URL, or '' when the row
    carries a placeholder (a bare mirror link, a profile page, nothing at all)."""
    url = str(m.get("source_post") or "")
    return url if re.search(r"/status/\d+", url) else ""


def _collapse_one_post(rows: list[dict]) -> list[dict]:
    """One real post states ONE measurement per (engine, date) — collapse the rest.

    `merge_engines` groups by engine + GPU-size identity + a CONCORDANT t/s, so the same
    post captured twice with different hardware wording (or a different t/s) stayed several
    store rows, carrying contradictory dimension values into the card-fit and traceability
    views: `qwen3.6-35b-a3b` had four Ollama rows dated 2026-10-16 from one post (two
    `context_tokens` 66000 and two 67000), `qwen3.8-27b` two llama.cpp rows from one post
    (8192 and 65536) — issue #389.

    A row whose `source_post` is a REAL post URL collapses with its siblings on
    `(engine, date, source_post)`: the HIGHER t/s is kept (never averaged down, never
    lowered), engagement counters are kept at their max (never shrunk), and `MEASUREMENT_
    DIMENSION_FIELDS` fill only (a stated value is never overwritten, an unstated one never
    invented) — the additive rule (AGENTS.md §2.3b) at measurement level. A placeholder post
    is NOT a key: two rows that both carry '' are not evidence of one measurement.
    """
    out: list[dict] = []
    by_key: dict[tuple, dict] = {}
    for m in rows:
        post = _real_post(m)
        if not post:
            out.append(m)
            continue
        key = (m.get("engine"), str(m.get("date") or ""), post)
        keep = by_key.get(key)
        if keep is None:
            keep = dict(m)
            by_key[key] = keep
            out.append(keep)
            continue
        if _tps_core(m.get("tps")) > _tps_core(keep.get("tps")):
            keep["tps"] = m.get("tps")
        for k in COUNTER_FIELDS:
            keep[k] = max(int(keep.get(k) or 0), int(m.get(k) or 0))
        for k in MEASUREMENT_DIMENSION_FIELDS:
            if keep.get(k) in (None, "", [], {}):
                v = m.get(k)
                # NEVER write an explicit null: the contract types these as strings, and a
                # `weight_gb: null` in the store fails model_contract (measured here).
                if v not in (None, "", [], {}):
                    keep[k] = coerce_additive(v)
    return out


def merge_engines(current: list[dict], incoming: list[dict]) -> list[dict]:
    """Merge incoming engine measurements into current, engagement-weighted.

    Two rows are the SAME measurement (collapse to one) when they share engine +
    GPU size AND a concordant t/s (within 5%). A concordant group's representative
    t/s is the engagement-weighted mean of its cores (likes + comments on each
    source post), taking the HIGHER of (reported, weighted mean) — so a reported
    t/s is only raised, never lowered. The representative row is the group's
    highest-engagement measurement (newest date tie-break). Non-concordant t/s
    (a genuinely different measurement, e.g. a different quant) stays a distinct
    row. Never drops a current entry."""
    # FIRST collapse the rows a single real post produced (issue #389), then group the
    # rest by the existing engine/GPU-size/concordant-t/s identity.
    combined = _collapse_one_post(list(current) + incoming)
    out: list[dict] = []
    used = set()
    for i, m in enumerate(combined):
        if i in used:
            continue
        used.add(i)
        core = _tps_core(m.get("tps"))
        group = [m]
        for j, n in enumerate(combined):
            if j in used or j == i:
                continue
            if (n.get("engine") == m.get("engine")
                    and _gpu_size(n.get("hardware", "")) == _gpu_size(m.get("hardware", ""))
                    and _concordant(_tps_core(n.get("tps")), core)):
                group.append(n)
                used.add(j)
        wsum = sum(_eng_weight(x) for x in group)
        rep_core = sum(_tps_core(x.get("tps")) * _eng_weight(x) for x in group) / wsum if wsum else core
        primary = max(enumerate(group), key=lambda it: (_eng_weight(it[1]), it[1].get("date", ""), it[0]))[1]
        # keep-higher: the representative is the max of (highest reported core in
        # the group, engagement-weighted mean) — a reported t/s is only ever
        # raised, never lowered by a noisy/low-engagement outlier.
        max_core = max(_tps_core(x.get("tps")) for x in group)
        final_core = max(max_core, rep_core)
        row = dict(primary, tps=f"{final_core:g}")
        # The representative is picked by ENGAGEMENT, not by which capture stated
        # the run's footprint: a lower-engagement member can be the only one that
        # states `weight_gb` / `context_tokens` / `system_ram_min` /
        # `storage_offload` / `engine_min_version`. `dict(primary)` used to drop
        # those silently — and, in the other direction, drop a value the STORE row
        # already held when a higher-engagement incoming row won the group. Fill
        # only (a stated value is never overwritten, an unstated one never
        # invented): the additive-only rule (AGENTS.md §2.3b) at measurement level.
        # only when that member captured the SAME post: a dimension states THE RUN's
        # footprint, so a sibling measurement of another post states another run's
        # (measured: qwen3.6-35b-a3b's oMLX row on post …6273 carried `DFlash2 drafter
        # on`, a wording only post …4438's rows state, and the captured-footprint guard
        # in tests/test_data_gap_analysis.py caught the attribution).
        primary_post = _real_post(primary)
        for member in group:
            if not primary_post or _real_post(member) != primary_post:
                continue
            for k in MEASUREMENT_DIMENSION_FIELDS:
                kept = _raised_dimension(row.get(k), member.get(k))
                if kept is not None:          # an unstated dimension is never stored
                    row[k] = kept
        for k in ("likes", "comments", "reshares", "views", "interactions"):
            row.setdefault(k, 0)
        out.append(row)
    return out

_REQ_ENGINE_FIELDS = ("engine", "tps", "date")

# Model-level engagement keys the STORE contract allows. Read from
# data/model_contract.json (single source of truth) so ingest can never drift
# from validation. The search contract leaves model-level engagement OPEN, but
# the store contract is CLOSED (additionalProperties:false) — so any extra key
# the search agent writes there must be pruned at ingest, or every refresh PR
# goes red on a schema error no LLM fixer should have to repair.
_MODEL_CONTRACT = ROOT / "data" / "model_contract.json"
_FALLBACK_ENGAGEMENT_KEYS = frozenset(
    {"likes", "comments", "views", "reshares", "interactions", "last_7d_likes", "posts_7d",
     "score_7d", "buzz_7d", "speed_bonus", "trend_score", "seen_posts"})


def _engagement_props() -> dict:
    try:
        c = json.loads(_MODEL_CONTRACT.read_text())
        return c["properties"]["models"]["items"]["properties"]["engagement"]["properties"]
    except Exception:  # noqa: BLE001 — contract missing/malformed: use the known set
        return {k: {"type": "integer"} for k in _FALLBACK_ENGAGEMENT_KEYS if k != "seen_posts"} | {
            "seen_posts": {"type": "array"}} | {k: {"type": "number"} for k in ("score_7d", "buzz_7d", "speed_bonus", "trend_score")}


def _engagement_keys() -> frozenset:
    return frozenset(_engagement_props())


def prune_engagement(eng: dict, model_id: str = "?") -> dict:
    """Drop model-level engagement keys the store contract does not declare.
    Integer counters are coerced to non-negative ints (an agent writing "12" or
    a float must not fail the schema either). Prints what was pruned."""
    props = _engagement_props()
    out = {}
    for k, v in eng.items():
        if k not in props:
            print(f"[ingest] {model_id}: pruned undeclared engagement key {k!r}")
            continue
        typ = props[k].get("type")
        if typ in ("integer", "number"):
            try:
                f = max(0.0, float(v))
                v = int(f) if typ == "integer" else round(f, 1)
            except (TypeError, ValueError):
                print(f"[ingest] {model_id}: engagement {k}={v!r} not numeric -> 0")
                v = 0
        out[k] = v
    return out

#: The store contract's `id` pattern (`data/model_contract.json`): lowercase, digits, dots and
#: hyphens. A search leg writes ids by hand, so a single `_` (`qwen3.8-27b-mlx_srv`, measured on
#: PR #461) turned a whole refresh PR red — and the id never merged with its own model, because
#: everything matches on it. Normalising where the value is WRITTEN (and again at ingest) keeps
#: the contract true without ever renaming a stored model (rule 3b).
ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9.\-]*$")


def contract_id(value: object) -> str:
    """`value` as a contract-legal model id (`_`→`-`, lowercase, only [a-z0-9.-]).

    Returns "" when nothing usable is left, so a caller can fall back to `_slug(name)` instead
    of writing an empty id.
    """
    s = str(value or "").strip().lower()
    s = s.replace("_", "-").replace(" ", "-")
    s = re.sub(r"[^a-z0-9.\-]+", "-", s)
    s = re.sub(r"-{2,}", "-", s)
    s = re.sub(r"^[^a-z0-9]+", "", s).strip("-")
    return s


def _slug(name: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", (name or "").lower()).strip("-")
    return s or "unknown"


# Model-level OPTIONAL metadata the contracts declare on a model (never in a
# contract's `required`), merged from a raw snapshot onto an EXISTING store row.
# Without this the update path silently drops them: it merged only engines /
# last_seen / engagement, so a dimension the contracts had just gained room for
# (system_ram_min, weight_gb, context_tokens, storage_offload,
# engine_min_version) could only ever land on a brand-new model — the data-gap
# analysis would keep reporting it as missing forever. Declared here (not read
# from the contract) because these are the only fields with this merge order;
# tests/test_data_gap_analysis.py asserts every one is declared in BOTH
# contracts, so the contract can never fall behind this list.
_ADDITIVE_MODEL_FIELDS = (
    "system_ram_min", "weight_gb", "context_tokens", "storage_offload", "engine_min_version")

# The same source-data dimensions ONE LEVEL DOWN: on the measurement that produced
# a t/s figure (issue #337). One model's quants fit different cards, so the card-fit
# view reads the footprint of THE RUN — a measurement on a 32 GB card whose post
# states 5.95 GB weights is what tells an 8 GB owner the model can run for them.
# `engine_min_version` belongs here too: a minimum engine build or a set of required
# flags is a property of the ENGINE THAT RAN THE FIGURE, not of the model — a model
# can be measured on two engines whose required builds differ, so only the
# measurement can carry it (the search agent writes it there; the contract used to
# accept it on the model row alone, so `additionalProperties: false` refused the
# per-measurement one and reddened a whole refresh PR).
# Their absence is MEANINGFUL (the post stated no figure) and is never invented,
# exactly like the model-level ones: `tests/test_fixture_mapping.py` asserts a raw
# snapshot that states none yields none, and `tests/test_measurement_footprint.py`
# drives one that does through the real ingest. ONE definition (rule 6d) — the keys
# are declared in both contracts, which the same test proves.
#: Engagement counters that live on a measurement. Collapsing one post's rows may only
#: RAISE one (AGENTS.md §2.3b): the post's signal is the post's, not one capture's.
COUNTER_FIELDS = ("likes", "comments", "reshares", "views", "interactions")

MEASUREMENT_DIMENSION_FIELDS = (
    "weight_gb", "context_tokens", "system_ram_min", "storage_offload", "engine_min_version")


def _raised_dimension(stored, incoming):
    """The stated footprint to keep: the LARGER figure, never a smaller one (issue #530).

    §2.3b says a value may only be RAISED, never shrunk. The old code filled a dimension
    ONLY when the row had none, which is stricter than the rule and wrong in the other
    direction: it also forbade raising — so the first figure that ever landed for a run was
    pinned for ever. Measured: post `qvac/status/2107139441425014846` states 5.95GB, one leg
    captured 5.93GB first, and every later refresh was red on the guard that exists to catch
    exactly that (`weight_gb` is what the card-fit tables publish as the budget a run needs).

    Two comparables (a GB figure on either side) → the larger wins, so 5.95GB beats 5.93GB and
    950MB never beats 1.2GB. A non-numeric dimension (`engine_min_version`, a prose
    `storage_offload`) is text: an unstated value is filled from any member, a stated one is
    never replaced by a different spelling — "later" is not evidence that a version or a
    medium changed.
    """
    stored_empty = stored in (None, "", [], {})
    incoming_empty = incoming in (None, "", [], {})
    if incoming_empty:
        return stored
    if stored_empty:
        return coerce_additive(incoming)
    a, b = _gb_value(stored), _gb_value(incoming)
    if a is not None and b is not None:
        return coerce_additive(incoming) if b > a else stored
    return stored


def coerce_additive(v):
    """A dimension value is stored as the text the post gave. A bare number the
    search agent wrote (`"context_tokens": 131072`) is kept as its string form
    rather than failing the schema: the contracts declare these keys as strings,
    and a schema rejection is a red refresh PR no value should cost."""
    if isinstance(v, bool):
        return str(v).lower()
    if isinstance(v, (int, float)):
        return f"{v:g}"
    return v


def merge_additive_fields(existing: dict, incoming: dict) -> list[str]:
    """Fill the model-level optional metadata keys an incoming raw model carries
    onto `existing`, WITHOUT overwriting: an absent key is filled, a key that
    already holds a value is kept (additive only — AGENTS.md §2.3b; a value is
    never shrunk, blanked or renamed). Returns the keys that were filled."""
    filled = []
    for k in _ADDITIVE_MODEL_FIELDS:
        v = incoming.get(k)
        if v in (None, "", [], {}):
            continue
        if existing.get(k) in (None, "", [], {}):
            existing[k] = coerce_additive(v)
            filled.append(k)
    return filled

def normalize_model(m: dict, store: dict) -> dict:
    """Fill contract-required fields on a model taken from a raw search snapshot,
    using only data already present (never invents t/s figures). Mirror of
    scripts/self_correct_raw.py but applied AT INGEST so a raw snapshot missing
    derived fields (e.g. full_name, license, vram_min, backends) cannot crash
    render_readme or produce a schema-non-conforming store."""
    m = dict(m)
    # `hf` is a bare repo id everywhere (README/validate prefix it themselves):
    # collapse a pasted URL / doubled prefix so a slug that skipped --write-raw
    # can never land a broken link in the store.
    if m.get("hf"):
        m["hf"] = normalize_hf_ref(m["hf"])
    for _f in m.get("formats") or []:
        if isinstance(_f, dict) and _f.get("hf"):
            _f["hf"] = normalize_hf_ref(_f["hf"])
    m.setdefault("id", _slug(m.get("name", "")))
    # A raw snapshot written before this rule (or by a leg that skipped `--write-raw`) can
    # still carry an id the contract forbids: normalise it HERE too, so the store is never
    # handed one (issue #464). An id that already matches is left byte-identical, and an
    # EXISTING model never reaches this function — ingest matches it by id first (rule 3b).
    if not ID_PATTERN.match(str(m.get("id") or "")):
        _fixed = contract_id(m.get("id")) or _slug(m.get("name") or m.get("id") or "")
        if _fixed != m.get("id"):
            print(f"[ingest] id normalised {m.get('id')!r} -> {_fixed!r} (contract pattern)")
            m["id"] = _fixed
    m.setdefault("full_name", m.get("name", ""))
    m.setdefault("license", "Unknown")
    m.setdefault("params", "unknown")
    m.setdefault("type", m.get("type") or "LLM")
    m.setdefault("vram_tier", m.get("vram_min", ""))
    tiers = [x for x in [m.get("vram_tier"), m.get("vram_min")] if x]
    vm = re.search(r"(\d+)\s*GB", (tiers[0] if tiers else "") or "")
    m.setdefault("vram_min", m["vram_tier"])
    if vm and not m.get("vram_min"):
        m["vram_min"] = f"{vm.group(1)}GB"
    engs = [e for e in m.get("engines", []) if e.get("engine")]
    # default per-measurement engagement (likes/comments) so the interaction-
    # weighted merge has a weight even when the search agent didn't emit it yet
    for e in engs:
        for k in ("likes", "comments", "reshares", "views", "interactions"):
            e.setdefault(k, 0)
        # The source-data dimensions of THIS run, kept as the text the post gave.
        # A bare number the agent wrote (`"context_tokens": 131072`) is coerced
        # instead of failing the schema — the same rule the model-level fields get
        # below.  Absent means "the post stated no figure" and is never invented.
        for k in MEASUREMENT_DIMENSION_FIELDS:
            if e.get(k) not in (None, "", [], {}):
                e[k] = coerce_additive(e[k])
            else:
                e.pop(k, None)
    # dedup the raw model's own engine rows (same engine+tps+GPU size reported
    # by two posts in ONE snapshot) so a brand-new model never carries duplicates
    engs = merge_engines([], engs)
    # backends: what the search wrote, plus every backend its measurements land
    # in (same classifier as the README, so an AMD figure always adds 'ROCm').
    # Fallback for a model with no classifiable rows: the engines' registry
    # backends (legacy behaviour).
    reg = store.get("engines", {})
    backends = [b for b in (m.get("backends") or []) if b in BACKENDS]
    for b in measured_backends({"engines": engs}, reg):
        if b not in backends:
            backends.append(b)
    if not backends:
        for e in engs:
            for cand in split_backends(reg.get(e.get("engine"), {}).get("backend", "")):
                if cand not in backends:
                    backends.append(cand)
    m["backends"] = backends or ["CUDA"]
    m.setdefault("supported_engines", [e.get("engine") for e in engs if e.get("engine")])
    m.setdefault("why", m.get("why") or (m.get("full_name", m.get("name", "")) + " — see source posts."))
    m.setdefault("formats", [{"name": m.get("name", ""), "hf": m.get("hf", "")}])
    eng = m.setdefault("engagement", {})
    for k in ("likes", "comments", "views", "last_7d_likes"):
        eng.setdefault(k, 0)
    # seed post-granularity engagement: merge engine-derived posts (which carry
    # proper dates) with any agent-written seen_posts, normalizing bare URL
    # strings so malformed data never persists into the store
    eng["seen_posts"] = dedupe_posts(_collect_seen_posts(m) + eng.get("seen_posts", []))
    m["engagement"] = prune_engagement(eng, m.get("id", "?"))
    # scrub incomplete engine rows (missing tps or engine identity) so schema passes
    m["engines"] = [e for e in engs if all(e.get(f) is not None for f in _REQ_ENGINE_FIELDS)]
    # source-data dimensions: keep whatever the post stated (never invented),
    # coerced to text so a numeric context_tokens does not fail the schema
    for k in _ADDITIVE_MODEL_FIELDS:
        if m.get(k) not in (None, "", [], {}):
            m[k] = coerce_additive(m[k])
        else:
            m.pop(k, None)
    return m

def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dry-run", action="store_true", help="regenerate + print, do not write")
    ap.add_argument("--render-only", action="store_true",
                    help="regenerate README.md from the store AS OF its own generated_utc — no "
                         "raw ingest, no store write, no snapshot (issue #195: a template change "
                         "must not need a data diff)")
    ap.add_argument("--fetch", action="store_true",
                    help="fetch lightbrd.com search results directly (default: re-sort/re-render "
                         "from the store only; the Hermes CLI does the live fetch via web_extract)")
    ap.add_argument("--require-hits", action="store_true",
                    help="with --fetch, exit non-zero if the search returns 0 model hits — EXCEPT "
                         "when every query came back as the target's own error page (an upstream "
                         "mirror outage, reported loudly and not blocking; issue #291)")
    ap.add_argument("--write-raw", metavar="BACKEND",
                    help="write a per-backend raw snapshot to data/raw/<backend>-<UTC>.json "
                         "(payload read from stdin JSON) and exit")
    ap.add_argument("--since", metavar="UTC",
                    help="merge raw snapshots newer than this YYYY-MM-DDTHH:MM:SSZ stamp "
                         "instead of the store's own generated_utc (issue #175)")
    args = ap.parse_args()

    if args.write_raw:
        import sys as _sys
        payload = json.loads(_sys.stdin.read())
        p = write_raw_snapshot(args.write_raw, payload)
        print("wrote " + p.name)
        return 0

    if not DATA.exists():
        print("[error] missing data/models.json", file=sys.stderr)
        return 1
    store = json.loads(DATA.read_text())

    if args.render_only:
        # Render-only (issue #195). The README is rendered AS OF the store's own
        # `generated_utc` — exactly the as-of `check_readme_generated` re-renders with — so
        # the output is byte-identical to what `make merge` would write, while
        # data/models.json and data/snapshots/ stay untouched. A template/docs change then
        # carries the README and nothing else.
        as_of = parse_utc_stamp(store.get("generated_utc"))
        if as_of is None:
            print("[error] the store has no usable generated_utc — run `make merge`", file=sys.stderr)
            return 1
        readme = render_readme(store, as_of)
        # Keep the "Last generated" line the README already carries: render_readme stamps
        # the WALL CLOCK there, and no data changed — a template change must not move a
        # timestamp (the gate strips that line, and a re-run must be a no-op).
        if README.is_file():
            existing = README.read_text()
            keep = next((ln for ln in existing.splitlines() if ln.startswith("> Last generated:")), "")
            if keep:
                readme = "\n".join(
                    keep if ln.startswith("> Last generated:") else ln
                    for ln in readme.splitlines()) + ("\n" if readme.endswith("\n") else "")
        if args.dry_run:
            print(readme)
            return 0
        README.write_text(readme)
        print(f"[ok] rendered {README.name} from {DATA.name} as of {store['generated_utc']} "
              f"(no store write, no snapshot — issue #195)")
        return 0

    today = now_utc()

    if args.fetch:
        stats: dict = {}
        per_backend = gather_x(store, stats)
        all_seen = [t for grp in per_backend.values() for t in grp]
        print(f"[info] X model-hits this run: {len(all_seen)} across {list(per_backend.keys())}")
        # Name the outcome of every query, not just the hits: the same "0 model
        # hits" is an outage, a bad key or a quiet search (issue #293).
        print(f"[info] fetch outcomes: queries={stats['queries']} with-hits={stats['with_hits']} "
              f"outage={stats['outage']} refused={stats['refused']} failed={stats['failed']}")
        if args.require_hits and not all_seen:
            kind, code, lines = zero_hit_verdict(stats)
            for line in lines:
                print(line, file=sys.stdout if kind == "outage" else sys.stderr)
            # An upstream outage is not ours to fix and must not block every
            # open PR (its `live-smoke` job gates `auto-merge`, issue #291).
            return code
        if all_seen:
            matched, unknown = merge_engagements(store, all_seen)
            print(f"[info] matched {matched} known models, {unknown} unknown tokens (ignored unless curated)")
        if args.dry_run:
            return 0

    # Merge any per-backend raw snapshots left by the Hermes search prompts —
    # only the ones NEWER than the store we just loaded, i.e. the snapshots no
    # earlier merge has already folded in (issue #175). `--since` overrides the
    # derived boundary; a store with no usable `generated_utc` reads everything.
    since = parse_utc_stamp(store.get("generated_utc"))
    if args.since is not None:
        since = parse_utc_stamp(args.since)
        if since is None:
            print(f"[error] --since {args.since!r} is not a YYYY-MM-DDTHH:MM:SSZ stamp", file=sys.stderr)
            return 1
    added, updated = ingest_raw_snapshots(store, since=since, verify_hf=True)
    if added or updated:
        print(f"[info] ingested raw snapshots: {added} added, {updated} updated")

    # One instant for sorting, the stored timestamp and the render, so the
    # validator can re-render the README "as of generated_utc" byte-for-byte.
    today = today.replace(microsecond=0)
    store["generated_utc"] = today.strftime("%Y-%m-%dT%H:%M:%SZ")
    store["models"] = sort_models(store["models"], today)
    readme = render_readme(store, today)

    if args.dry_run:
        print(readme)
        return 0

    DATA.write_text(json.dumps(store, indent=2, ensure_ascii=False) + "\n")
    README.write_text(readme)
    snap = write_snapshot(store)
    print("[ok] wrote data/models.json, README.md, snapshot " + snap.name)
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
