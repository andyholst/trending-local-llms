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
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
# Allow tests to run the make targets against a small fixture in a temp dir
# instead of the real data/ tree. When set, all data paths resolve under it.
_DATA_DIR = Path(os.environ.get("TRENDING_DATA_DIR", str(ROOT / "data")))
DATA = _DATA_DIR / "models.json"
README = Path(os.environ.get("TRENDING_README", str(ROOT / "README.md")))
SCRAPE_DIR = _DATA_DIR / "scrape"
SNAPSHOT_DIR = _DATA_DIR / "snapshots"
RAW_DIR = _DATA_DIR / "raw"

# Three backend search groups (last-3-day window), refined by live probing (Sep 28
# 2026) for maximum matches per backend. NVIDIA/CUDA and Apple/Metal carry most
# of the signal; CPU is sparse on X (offload-capable engines like FreeToken and
# llama.cpp-cpu surface under the CUDA/engine queries). The General catch-all
# group was removed; the Hermes refresh drives the live search.
SEARCH_GROUPS = {
    "CUDA": [
        "rtx tokens per second llm",
        "rtx 3090 tokens per second qwen",
        "rtx 5090 32gb tokens per second",
        "rtx 4090 tokens per second llm",
        "rtx 3090 vs 5090 27b tokens",
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
}
USER_AGENT = "trending-local-llms-bot/1.0 (research-index)"
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


def fetch_via_firecrawl(url: str, api_key: str) -> str:
    """Fetch a page through Firecrawl's scrape API (renders JS, passes
    Cloudflare, which raw urllib cannot)."""
    import urllib.request as _ur

    payload = json.dumps({
        "url": url,
        "formats": ["markdown"],
        "onlyMainContent": False,
    }).encode("utf-8")
    req = _ur.Request(
        "https://api.firecrawl.dev/v1/scrape",
        data=payload,
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"},
        method="POST",
    )
    with _ur.urlopen(req, timeout=60) as resp:
        body = json.loads(resp.read().decode("utf-8", "replace"))
    # Firecrawl returns {success, data:{markdown}} — fall back to raw html if present
    return body.get("data", {}).get("markdown") or json.dumps(body)


def extract_models_seen(html: str) -> list[str]:
    """Very light heuristic: any known model token mentioned in the page."""
    known = re.findall(
        r"\b(Qwen3\.\d+(?:-[A-Za-z0-9]+)*|Qwen\d*\s*\d*B|gemma[- ]\d+[ A-Za-z0-9]*|"
        r"Llama\s*\d|\d+B)", html, re.I
    )
    return [m for m in known if m.strip()]


def gather_x(store: dict) -> dict:
    """Collect engagement signals per backend group from the lightbrd mirror.
    Returns {backend: [model_tokens_seen]}. Fetches are best-effort; a failed
    query is skipped with a warning and never wipes data."""
    known_names = [m["name"].lower() for m in store["models"]]
    per_backend: dict[str, list[str]] = {}
    for backend, queries in SEARCH_GROUPS.items():
        seen: list[str] = []
        for q in queries:
            try:
                html = fetch_lightbrd(q)
                tokens = extract_models_seen(html)
                # keep only tokens that match a known model (signal, not noise)
                seen += [t for t in tokens if t.lower() in known_names or any(n in t.lower() for n in known_names)]
            except Exception as e:  # noqa: BLE001
                print(f"[warn] {backend} fetch failed for '{q}': {e}")
        per_backend[backend] = seen
    return per_backend


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


def dedupe_posts(posts: list) -> list[dict]:
    """Collapse engagement.seen_posts to one entry per source_post URL.

    The same X post is re-scanned across overlapping 3-day search windows, so
    without this a single post would inflate last_7d_likes on every run. Keep
    the entry with the latest date for each URL (a re-seen post may carry a
    fresher date). Tolerates bare-string entries (coerced to {'url', 'date'})."""
    by_url: dict[str, dict] = {}
    for p in posts:
        p = _as_post(p)
        url = p.get("url", "")
        if not url:
            continue
        cur = by_url.get(url)
        if cur is None or _post_date(p) > _post_date(cur):
            by_url[url] = p
    return list(by_url.values())


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
    """Recompute last_7d_likes from engagement.seen_posts: the count of DISTINCT
    posts dated within the last TRENDING_WINDOW_DAYS. This makes 'ranked by
    7-day engagement' literally true and prevents double-counting the same post
    across overlapping search windows. Falls back to the stored counter when a
    model has no seen_posts (legacy rows)."""
    eng = m.setdefault("engagement", {})
    posts = dedupe_posts(eng.get("seen_posts", []))
    posts = prune_posts(posts, today)
    eng["seen_posts"] = posts
    cutoff = (today - timedelta(days=TRENDING_WINDOW_DAYS)).strftime("%Y-%m-%d")
    if posts:
        # post-granularity signal present -> last_7d_likes is the distinct-post count
        eng["last_7d_likes"] = sum(1 for p in posts if _post_date(p) >= cutoff)
    else:
        # No post-granularity signal (legacy row or no recent posts) -> the
        # stored counter is a stale cumulative number, not a 7-day count. Reset
        # to 0 so the trending rank reflects REAL recent engagement, never a
        # legacy monotonic counter that would dominate the list forever.
        eng["last_7d_likes"] = 0
    # keep last_seen in sync with the newest post (or today if none)
    dates = [d for d in (_post_date(p) for p in posts) if d]
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

def sort_models(models: list[dict], today: datetime) -> list[dict]:
    """Trending (<=7d) -> recent (<=30d) -> stale (>30d).
    Within a band, sort by last_7d_likes desc, then t/s (numeric) desc.
    Missing dates are treated as trending (conservative, never promoted into stale).
    Also sorts each model's engines newest-date-first so the latest trending
    t/s is always the first/surface figure."""
    for m in models:
        m["engines"] = sorted(m.get("engines", []), key=lambda e: e.get("date", ""), reverse=True)
        # recompute the 7-day engagement from distinct posts (dedup + prune)
        recompute_7d_engagement(m, today)

    def parse(d):
        try:
            return datetime.strptime(d, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        except Exception:
            return today

    def band(m):
        last = parse(m.get("last_seen", ""))
        delta = (today - last).days if last else 0
        if delta <= 7:
            return 0
        if delta <= 30:
            return 1
        return 2

    def peak_tps(m):
        vals = []
        for e in m.get("engines", []):
            mnum = re.search(r"(\d+\.?\d*)", str(e.get("tps", "")))
            if mnum:
                vals.append(float(mnum.group(1)))
        return max(vals) if vals else 0.0

    return sorted(
        models,
        key=lambda m: (
            band(m),
            -m["engagement"].get("last_7d_likes", 0),
            -peak_tps(m),
            m["name"].lower(),
        ),
    )

def render_readme(store: dict, today: datetime) -> str:
    """Regenerate README.md from the store + static sections."""
    models = sort_models(list(store["models"]), today)
    today_s = today.strftime("%Y-%m-%d")

    def elink(e):
        url = store["engines"].get(e["engine"], {}).get("url")
        return f"[{e['engine']}]({url})" if url else e["engine"]

    def eng_cells(m):
        if not m.get("engines"):
            return "—", "—"
        # newest first
        es = sorted(m["engines"], key=lambda e: e.get("date", ""), reverse=True)
        cuda = []
        metal = []
        for e in es:
            cell = f"{e['tps']} ({elink(e)}"
            if e.get("hardware"):
                cell += f", {e['hardware']}"
            if e.get("quant"):
                cell += f", {e['quant']}"
            cell += ")"
            if e["engine"] in ("MLX", "TensorFold", "MLX-fast (Bonsai 2)") or "Apple" in e.get("hardware", "") or "Mac" in e.get("hardware", ""):
                metal.append(cell)
            else:
                cuda.append(cell)
        return "<br>".join(cuda) or "—", "<br>".join(metal) or "—"

    rows = []
    for m in models:
        cu, me = eng_cells(m)
        rows.append(
            f"| **{m['name']}** | {m.get('full_name', m.get('name',''))} | [link](https://huggingface.co/{m['hf']}) "
            f"| {m.get('why','')} | {cu} | {me} | {m.get('vram_tier','—')} |"
        )
    most_loved = "\n".join(rows)

    # Which backend a given engine measurement belongs to (equal first-class
    # categories: NVIDIA/CUDA, Apple/Metal, CPU). Override on hardware/engine name.
    ENGINE_BACKEND = {
        "Ollama": None, "llama.cpp": None, "vLLM": "CUDA", "SGLang": "CUDA",
        "FreeToken": "CUDA", "TensorRT-LLM": "CUDA", "DFlash2": "CUDA",
        "Strata": "CUDA", "MLX": "Metal", "TensorFold": "Metal",
        "MLX-fast (Bonsai 2)": "Metal", "LiteRT": None, "WebLLM": None,
    }
    def eng_backend(m, e):
        if any(k in e.get("hardware", "").lower() for k in ("apple", "mac")):
            return "Metal"
        if any(k in e.get("hardware", "").lower() for k in ("cpu", "intel", "amd ryzen", "no gpu")):
            return "CPU"
        b = ENGINE_BACKEND.get(e["engine"])
        if b:
            return b
        # Ollama/llama.cpp/LiteRT are multi-backend: decide from hardware text
        hw = (e.get("hardware", "") + " " + e.get("quant", "")).lower()
        if any(k in hw for k in ("rtx", "nvidia", "cuda", "geforce", "tesla", "aic")):
            return "CUDA"
        if any(k in hw for k in ("apple", "mac", "m1", "m2", "m3", "m4", "m5", "m6", "mlx")):
            return "Metal"
        return "CUDA"  # default NVIDIA until evidence says otherwise

# Group every model's measurements by backend for the equal backend tables.
    backend_rows = {"CUDA": [], "Metal": [], "CPU": []}
    for m in models:
        seen_backends = set()
        for e in m.get("engines", []):
            be = eng_backend(m, e)
            seen_backends.add(be)
        for be in seen_backends:
            es = [e for e in m["engines"] if eng_backend(m, e) == be]
            es_sorted = sorted(es, key=lambda e: e.get("date", ""), reverse=True)
            parts = []
            peak = 0.0
            for e in es_sorted:
                s = f"{elink(e)} {e['tps']}"
                if e.get("date"):
                    s += f" ({e.get('date')})"
                parts.append(s)
                nums = [float(x) for x in re.findall(r"(\d+\.?\d*)", str(e.get("tps", "")))]
                if nums:
                    peak = max(peak, max(nums))
            desc = "; ".join(parts)
            backend_rows[be].append((m, desc, peak))

    def backend_table(title, emoji, rows_):
        rows_ = sorted(rows_, key=lambda r: -r[2])
        lines = [f"# {emoji} {title}", "", "| Model | Params | License | HF | VRAM | t/s per engine |",
                 "|---|---|---|---|---|---|"]
        if not rows_:
            lines.append("_No models measured on this backend yet._")
        for m, desc, _peak in rows_:
            lines.append(
                f"| **{m['name']}** | {m.get('params','—')} | {m.get('license','—')} "
                f"| [link](https://huggingface.co/{m['hf']}) | {m.get('vram_tier','—')} | {desc} |"
            )
        return "\n".join(lines)

    cuda_md = backend_table("CUDA — NVIDIA GPUs (8–48 GB)", "🟦", backend_rows["CUDA"])
    metal_md = backend_table("Metal — Apple Silicon (unified memory)", "🟩", backend_rows["Metal"])
    cpu_md = backend_table("CPU — no GPU", "🟨", backend_rows["CPU"])

    engine_guide = "\n".join(
        f"| [{k}]({v.get('url','')}) | {v['backend']} | {v['note']} |"
        for k, v in store["engines"].items()
    )

    now_s = now_utc().strftime("%Y-%m-%d %H:%M UTC")

    return f"""# Trending Local LLMs

A living, detailed list of **open-weight** LLMs that actually make a difference for local deployment. Every figure is **community-reported on X** (real benchmark posts, not vendor claims), with the hardware and engine it was measured on. This README is **automatically regenerated** from `data/models.json` — see [AGENTS.md](AGENTS.md) and `skills/gather-data.md`.

**Ranked by 7-day X engagement** (likes/comments/views), retained through a 30-day window. Within a rank, models sort by **highest t/s** with the **one engine** that produced it. t/s is always shown **per engine**.

> Last generated: {now_s}. Source: lightbrd.com mirror (X posts).

---

## ❤️ Most loved open-weight models on X (ranked by 7-day engagement)

| Model | Full name | HF link | Why people love it | CUDA t/s (engine) | Metal t/s (engine) | VRAM |
|---|---|---|---|---|---|---|
{most_loved}

---

{cuda_md}

---

{cpu_md}

> CPU inference is **memory-bandwidth bound**. Use Q4 quant + a fast CPU build (AVX-512/AMX).

---

{metal_md}

> On Apple Silicon, **MLX** is the fastest engine; **TensorFold** adds speculative decoding (3–6x on memory-bound Macs); **MLX-fast Bonsai 2** (Layr-Labs/mlxfast-bonsai2-27b-engine) pushes Ternary Bonsai 2 27B to ~237 tok/s on a 16 GB Mac.

---

## ⚙️ Inference engine / server guide

| Engine | Backend | Best for |
|---|---|---|
{engine_guide}

**Quick picks:** Ollama (just works) · llama.cpp (gaming laptop, max speed) · FreeToken (big MoE on small GPU) · MLX + TensorFold + MLX-fast (Mac) · Strata (125B MoE on 12–24 GB) · vLLM + DFlash2 (spec decode) · llama.cpp CPU (tiny/edge).

---

## How to contribute

- Update `data/models.json` (add/refresh a model row with real X-sourced engagement and per-engine t/s), then run `python3 scripts/update_trending.py` to regenerate the README.
- Include: full model name, HF link, license, params, type, VRAM tier, a **measured** t/s + **engine + hardware + quant**, and the source X post.
- Prefer numbers from real X benchmark posts over vendor claims. Data is **community-reported on X** — directional, not lab-grade; mark projections `(est)`.
- All changes go through a **feature branch + PR**; automation never pushes to/merges `master` directly.

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

def write_raw_snapshot(backend: str, payload: dict) -> Path:
    """Write one backend's raw search findings to data/raw/<backend>-<UTC>.json.
    Each of the three Hermes search prompts (NVIDIA, Metal, CPU) writes its own
    timestamped file here; never overwrite another backend's file."""
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    ts = now_utc().strftime("%Y%m%d-%H%M%S")
    safe = re.sub(r"[^A-Za-z0-9_-]", "-", backend).lower()
    path = RAW_DIR / f"{safe}-{ts}.json"
    payload = dict(payload)
    payload.setdefault("generated_utc", now_utc().strftime("%Y-%m-%dT%H:%M:%SZ"))
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n")
    return path

def _collect_seen_posts(m: dict) -> list[dict]:
    """Derive engagement.seen_posts from a model's engine measurements: one
    entry per distinct source_post URL, dated by the measurement date. This is
    the post-granularity signal that powers the 7-day trending aggregation."""
    posts: dict[str, dict] = {}
    for e in m.get("engines", []):
        url = e.get("source_post", "")
        if not url:
            continue
        cur = posts.get(url)
        date = e.get("date", "")
        if cur is None or date > cur.get("date", ""):
            posts[url] = {"url": url, "date": date}
    return list(posts.values())

def ingest_raw_snapshots(store: dict) -> tuple[int, int]:
    """Merge all data/raw/*.json into the store. Each raw file holds one
    backend's captured findings (models). New models are added, existing ones
    updated, NONE removed. Returns (added, updated)."""
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
        for m in data.get("models", []):
            mid = m.get("id")
            if not mid:
                continue
            if mid in by_id:
                # update existing: merge engines (replace t/s on same engine+date), keep rest
                existing = by_id[mid]
                existing["engines"] = merge_engines(existing.get("engines", []), m.get("engines", []))
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
                by_id[mid] = normalize_model(m, store)
                store["models"].append(by_id[mid])
                added += 1
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
    m = re.search(r"rtx\s*(\d{3,4})\s*(ti)?", hw)
    if m:
        return f"rtx{m.group(1)}{m.group(2) or ''}"
    m = re.search(r"(\d+)\s*gb", hw)
    if m:
        return f"{m.group(1)}gb"
    if any(k in hw for k in ("apple", "mac", "m1", "m2", "m3", "m4", "m5", "m6", "mlx")):
        return "apple"
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
    combined = list(current) + incoming
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
    {"likes", "comments", "views", "reshares", "interactions", "last_7d_likes", "seen_posts"})


def _engagement_keys() -> frozenset:
    try:
        c = json.loads(_MODEL_CONTRACT.read_text())
        props = c["properties"]["models"]["items"]["properties"]["engagement"]["properties"]
        return frozenset(props)
    except Exception:  # noqa: BLE001 — contract missing/malformed: use the known set
        return _FALLBACK_ENGAGEMENT_KEYS


def prune_engagement(eng: dict, model_id: str = "?") -> dict:
    """Drop model-level engagement keys the store contract does not declare.
    Integer counters are coerced to non-negative ints (an agent writing "12" or
    a float must not fail the schema either). Prints what was pruned."""
    allowed = _engagement_keys()
    out = {}
    for k, v in eng.items():
        if k not in allowed:
            print(f"[ingest] {model_id}: pruned undeclared engagement key {k!r}")
            continue
        if k != "seen_posts":
            try:
                v = max(0, int(float(v)))
            except (TypeError, ValueError):
                print(f"[ingest] {model_id}: engagement {k}={v!r} not numeric -> 0")
                v = 0
        out[k] = v
    return out

def _slug(name: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", (name or "").lower()).strip("-")
    return s or "unknown"

def normalize_model(m: dict, store: dict) -> dict:
    """Fill contract-required fields on a model taken from a raw search snapshot,
    using only data already present (never invents t/s figures). Mirror of
    scripts/self_correct_raw.py but applied AT INGEST so a raw snapshot missing
    derived fields (e.g. full_name, license, vram_min, backends) cannot crash
    render_readme or produce a schema-non-conforming store."""
    m = dict(m)
    m.setdefault("id", _slug(m.get("name", "")))
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
    # dedup the raw model's own engine rows (same engine+tps+GPU size reported
    # by two posts in ONE snapshot) so a brand-new model never carries duplicates
    engs = merge_engines([], engs)
    backends = []
    for e in engs:
        b = store.get("engines", {}).get(e.get("engine"), {}).get("backend", "")
        for cand in ("CUDA", "Metal", "CPU"):
            if cand in b and cand not in backends:
                backends.append(cand)
    m.setdefault("backends", backends or ["CUDA"])
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
    return m

def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dry-run", action="store_true", help="regenerate + print, do not write")
    ap.add_argument("--fetch", action="store_true",
                    help="fetch lightbrd.com search results directly (default: re-sort/re-render "
                         "from the store only; the Hermes CLI does the live fetch via web_extract)")
    ap.add_argument("--require-hits", action="store_true",
                    help="with --fetch, exit non-zero if the search returns 0 model hits")
    ap.add_argument("--write-raw", metavar="BACKEND",
                    help="write a per-backend raw snapshot to data/raw/<backend>-<UTC>.json "
                         "(payload read from stdin JSON) and exit")
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
    today = now_utc()

    if args.fetch:
        per_backend = gather_x(store)
        all_seen = [t for grp in per_backend.values() for t in grp]
        print(f"[info] X model-hits this run: {len(all_seen)} across {list(per_backend.keys())}")
        if args.require_hits and not all_seen:
            print("[error] Firecrawl->lightbrd search returned 0 model hits", file=sys.stderr)
            return 1
        if all_seen:
            matched, unknown = merge_engagements(store, all_seen)
            print(f"[info] matched {matched} known models, {unknown} unknown tokens (ignored unless curated)")
        if args.dry_run:
            return 0

    # Merge any per-backend raw snapshots left by the Hermes search prompts.
    added, updated = ingest_raw_snapshots(store)
    if added or updated:
        print(f"[info] ingested raw snapshots: {added} added, {updated} updated")

    store["models"] = sort_models(store["models"], today)
    store["generated_utc"] = now_utc().strftime("%Y-%m-%dT%H:%M:%SZ")
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
