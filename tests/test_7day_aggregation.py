#!/usr/bin/env python3
"""Unit tests for the 7-day post-granularity engagement aggregation.

The refresh searches a last-3-day window but ranks models by 7-day engagement.
This test proves the aggregation is correct and never double-counts:

  1. dedupe_posts collapses the same source_post URL seen across overlapping
     3-day search windows into ONE entry (no double-counting).
  2. recompute_7d_engagement sets last_7d_likes = count of DISTINCT posts dated
     within the last 7 days, and keeps last_seen in sync.
  3. prune_posts drops post entries older than 30 days (retention) but never
     removes the model row.
  4. ingest_raw_snapshots seeds engagement.seen_posts from engine source_posts
     and dedupes across multiple raw snapshots.
  5. self_correct_raw fills a missing required top-level 'backend' from the
     snapshot filename (the CPU-search regression).

Run:  python3 tests/test_7day_aggregation.py   or   make test
"""
from __future__ import annotations

import json
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import update_trending as UT  # noqa: E402

_PASS = 0
_FAIL = 0


def check(name, cond, detail=""):
    global _PASS, _FAIL
    if cond:
        _PASS += 1
        print(f"  ok  {name}")
    else:
        _FAIL += 1
        print(f"  FAIL {name}" + (f"  [{detail}]" if detail else ""))


def today() -> datetime:
    return datetime(2026, 9, 29, tzinfo=timezone.utc)


def test_dedupe_posts_collapses_same_url():
    """The same source_post URL re-scanned on 3 overlapping daily windows must
    collapse to ONE entry (keep the latest date). This is the anti-double-count
    guarantee."""
    posts = [
        {"url": "https://lightbrd.com/a", "date": "2026-09-27"},
        {"url": "https://lightbrd.com/a", "date": "2026-09-28"},  # re-seen, fresher
        {"url": "https://lightbrd.com/b", "date": "2026-09-28"},
    ]
    out = UT.dedupe_posts(posts)
    urls = sorted(p["url"] for p in out)
    check("dedupe collapses same URL to one entry", len(out) == 2, json.dumps(urls))
    a = next(p for p in out if p["url"] == "https://lightbrd.com/a")
    check("dedupe keeps the latest date for a re-seen URL", a["date"] == "2026-09-28", a["date"])


def test_recompute_7d_counts_distinct_posts_in_window():
    """last_7d_likes = number of DISTINCT posts dated within the last 7 days.
    A post from 8 days ago is NOT counted; a post from today IS."""
    m = {
        "id": "m1", "name": "M1", "engagement": {"seen_posts": [
            {"url": "https://lightbrd.com/1", "date": "2026-09-29"},  # today
            {"url": "https://lightbrd.com/2", "date": "2026-09-25"},  # 4d ago
            {"url": "https://lightbrd.com/3", "date": "2026-09-20"},  # 9d ago -> out
        ]},
    }
    UT.recompute_7d_engagement(m, today())
    check("last_7d_likes counts only posts within 7 days", m["engagement"]["last_7d_likes"] == 2,
          str(m["engagement"]["last_7d_likes"]))
    check("last_seen syncs to newest post", m["last_seen"] == "2026-09-29", m.get("last_seen"))


def test_recompute_dedupes_before_counting():
    """The same post appearing twice in seen_posts must count ONCE in
    last_7d_likes (dedup happens inside recompute)."""
    m = {
        "id": "m1", "name": "M1", "engagement": {"seen_posts": [
            {"url": "https://lightbrd.com/x", "date": "2026-09-28"},
            {"url": "https://lightbrd.com/x", "date": "2026-09-29"},  # dup, fresher
            {"url": "https://lightbrd.com/y", "date": "2026-09-28"},
        ]},
    }
    UT.recompute_7d_engagement(m, today())
    check("recompute dedupes before counting (2 distinct -> 2)", m["engagement"]["last_7d_likes"] == 2,
          str(m["engagement"]["last_7d_likes"]))


def test_prune_posts_retains_30d_removes_older():
    """Post entries older than 30 days are pruned (retention); the model row is
    untouched. A 31-day-old post is dropped, a 29-day-old one is kept."""
    m = {
        "id": "m1", "name": "M1", "engagement": {"seen_posts": [
            {"url": "https://lightbrd.com/old", "date": "2026-08-29"},  # 31d ago
            {"url": "https://lightbrd.com/keep", "date": "2026-08-31"},  # 29d ago
        ]},
    }
    UT.recompute_7d_engagement(m, today())
    urls = [p["url"] for p in m["engagement"]["seen_posts"]]
    check("prune drops >30d post, keeps <=30d", urls == ["https://lightbrd.com/keep"], json.dumps(urls))
    check("model row never removed by pruning", m["id"] == "m1")


def test_ingest_seeds_and_dedupes_seen_posts():
    """ingest_raw_snapshots seeds engagement.seen_posts from engine source_posts
    and dedupes the same post across two raw snapshots (two overlapping 3-day
    searches)."""
    store = {
        "engines": {"llama.cpp": {"backend": "CUDA", "note": "x", "url": "https://github.com/ggml-org/llama.cpp"}},
        "models": [{
            "id": "qwen3-14b", "name": "Qwen3 14B", "full_name": "Qwen3-14B", "type": "LLM",
            "formats": [{"name": "GGUF", "hf": "Qwen/Qwen3-14B"}], "license": "Apache 2.0",
            "params": "14B", "hf": "Qwen/Qwen3-14B", "vram_tier": "9GB", "vram_min": "8GB",
            "backends": ["CUDA"], "supported_engines": ["llama.cpp"],
            "engines": [{"engine": "llama.cpp", "tps": "50", "date": "2026-09-27",
                         "source_post": "https://lightbrd.com/a"}],
            "why": "w", "engagement": {"likes": 1, "comments": 0, "views": 1, "last_7d_likes": 1},
            "last_seen": "2026-09-27",
        }],
    }
    def raw(post_url, date):
        return {"backend": "nvidia", "generated_utc": "2026-09-28T10:00:00Z", "models": [{
            "id": "qwen3-14b", "name": "Qwen3 14B", "full_name": "Qwen3-14B", "type": "LLM",
            "license": "Apache 2.0", "params": "14B", "hf": "Qwen/Qwen3-14B",
            "vram_tier": "9GB", "vram_min": "8GB", "backends": ["CUDA"],
            "engines": [{"engine": "llama.cpp", "tps": "50", "date": date, "source_post": post_url}],
            "last_seen": date,
        }]}
    with tempfile.TemporaryDirectory() as td:
        rdir = Path(td)
        (rdir / "nvidia-1.json").write_text(json.dumps(raw("https://lightbrd.com/a", "2026-09-27")))
        (rdir / "nvidia-2.json").write_text(json.dumps(raw("https://lightbrd.com/a", "2026-09-28")))  # same post
        (rdir / "nvidia-3.json").write_text(json.dumps(raw("https://lightbrd.com/b", "2026-09-28")))  # new post
        saved = UT.RAW_DIR
        UT.RAW_DIR = rdir
        try:
            UT.ingest_raw_snapshots(store)
        finally:
            UT.RAW_DIR = saved
    m = next(x for x in store["models"] if x["id"] == "qwen3-14b")
    urls = sorted(p["url"] for p in m["engagement"]["seen_posts"])
    check("ingest dedupes same post across snapshots (2 distinct)", len(urls) == 2, json.dumps(urls))
    check("ingest keeps both distinct posts", urls == ["https://lightbrd.com/a", "https://lightbrd.com/b"],
          json.dumps(urls))


def test_correct_raw_fills_missing_backend():
    """Regression: the CPU search wrote a raw snapshot with only models +
    generated_utc (no top-level 'backend'), which failed check_search_contract.
    self_correct_raw must fill backend from the filename prefix."""
    import self_correct_raw as scr
    store = {"engines": {"llama.cpp": {"backend": "CPU"}}}
    schema = json.loads((ROOT / "data" / "search_contract.json").read_text())
    raw = {
        "generated_utc": "2026-09-29T15:48:43Z",
        "models": [{
            "id": "tiny-cpu", "name": "TinyCPU", "full_name": "TinyCPU", "type": "LLM",
            "license": "MIT", "params": "1B", "hf": "org/tiny-cpu",
            "vram_tier": "0GB", "vram_min": "0GB", "backends": ["CPU"],
            "engines": [{"engine": "llama.cpp", "tps": "12", "date": "2026-09-29",
                         "source_post": "https://lightbrd.com/cpu"}],
            "last_seen": "2026-09-29",
        }],
    }
    with tempfile.TemporaryDirectory() as td:
        rdir = Path(td)
        f = rdir / "cpu-20260929-154843.json"  # filename prefix = cpu
        f.write_text(json.dumps(raw))
        saved = scr.RAW_DIR
        scr.RAW_DIR = rdir
        try:
            scr.correct_snapshot(f, store)
        finally:
            scr.RAW_DIR = saved
        out = json.loads(f.read_text())
        check("correct-raw fills missing backend from filename", out.get("backend") == "cpu",
              str(out.get("backend")))
        import jsonschema
        try:
            jsonschema.validate(out, schema)
            valid = True
        except Exception:  # noqa: BLE001
            valid = False
        check("corrected snapshot validates against search_contract.json", valid)


def test_merge_engines_dedup_same_gpu_vram():
    """Same model + same engine + same t/s + same GPU card/VRAM must collapse to
    ONE engine row — the same measurement reported by two different X posts
    (with slightly different hardware wording) is never duplicated. Different
    GPU card or different t/s is a legit distinct measurement and is KEPT."""
    # the PR #16 duplicate: same engine+tps+GPU size, different hardware wording
    current = [{"engine": "FreeToken", "tps": "39.3", "hardware": "RTX 8GB GPU",
                "quant": "4-bit", "date": "2026-09-29", "source_post": "https://lightbrd.com/konig0000/status/1"}]
    incoming_same = [{"engine": "FreeToken", "tps": "39.3", "hardware": "8 GB GPU (MoE, ~3B active/token)",
                      "quant": "4-bit", "date": "2026-09-27", "source_post": "https://lightbrd.com/DailyDoseOfDS_/status/2"}]
    out = UT.merge_engines(current, incoming_same)
    check("merge_engines: same engine+tps+GPU size collapses to one row",
          len(out) == 1, f"len={len(out)}")
    check("merge_engines: keeps the NEWER date's row (2026-09-29)",
          out[0]["date"] == "2026-09-29", out[0]["date"])
    # different GPU card -> legit distinct measurement, KEPT
    incoming_diff_gpu = [{"engine": "FreeToken", "tps": "39.3", "hardware": "RTX 5090",
                          "quant": "4-bit", "date": "2026-09-28", "source_post": "https://lightbrd.com/b"}]
    out2 = UT.merge_engines(out, incoming_diff_gpu)
    check("merge_engines: different GPU card is a distinct row (kept)",
          len(out2) == 2, f"len={len(out2)}")
    # different t/s on the same GPU -> legit distinct measurement, KEPT
    incoming_diff_tps = [{"engine": "FreeToken", "tps": "45", "hardware": "RTX 8GB GPU",
                          "quant": "4-bit", "date": "2026-09-28", "source_post": "https://lightbrd.com/c"}]
    out3 = UT.merge_engines(out2, incoming_diff_tps)
    check("merge_engines: different t/s on same GPU is a distinct row (kept)",
          len(out3) == 3, f"len={len(out3)}")


def test_validate_catches_duplicate_engine_same_gpu_vram():
    """NEGATIVE: the validator must flag a store where the same model has the
    same engine on the same GPU card + VRAM (identical engine/date/hardware/
    tps/quant) twice — the exact 'mentioned twice for a specific GPU + VRAM'
    case the user wants prevented."""
    import validate as V
    V.FAILURES.clear()
    store = {"engines": {"llama.cpp": {"backend": "CUDA", "note": "x", "url": "https://github.com/ggml-org/llama.cpp"}},
             "models": [{
                 "id": "m1", "name": "M1", "full_name": "M1", "type": "LLM",
                 "formats": [{"name": "GGUF", "hf": "org/m1"}], "license": "Apache 2.0",
                 "params": "14B", "hf": "org/m1", "vram_tier": "12GB", "vram_min": "8GB",
                 "backends": ["CUDA"], "supported_engines": ["llama.cpp"],
                 "engines": [
                     {"engine": "llama.cpp", "tps": "50", "hardware": "RTX 4090",
                      "quant": "Q4", "date": "2026-09-28", "source_post": "https://lightbrd.com/a"},
                     {"engine": "llama.cpp", "tps": "50", "hardware": "RTX 4090",
                      "quant": "Q4", "date": "2026-09-28", "source_post": "https://lightbrd.com/b"},
                 ],
                 "why": "w", "engagement": {"likes": 1, "comments": 0, "views": 1, "last_7d_likes": 1},
                 "last_seen": "2026-09-28",
             }]}
    V.check_no_duplicate_engines(store)
    errs = [f for f in V.FAILURES if "duplicate engine row" in f]
    check("validate: catches same model+engine+GPU+VRAM mentioned twice",
          len(errs) == 1, json.dumps(errs))


def test_validate_allows_same_engine_different_gpu():
    """HAPPY: the same model+engine on DIFFERENT GPU cards (or different t/s)
    is a legitimate multi-hardware result and must NOT be flagged as a
    duplicate."""
    import validate as V
    V.FAILURES.clear()
    store = {"engines": {"llama.cpp": {"backend": "CUDA", "note": "x", "url": "https://github.com/ggml-org/llama.cpp"}},
             "models": [{
                 "id": "m1", "name": "M1", "full_name": "M1", "type": "LLM",
                 "formats": [{"name": "GGUF", "hf": "org/m1"}], "license": "Apache 2.0",
                 "params": "14B", "hf": "org/m1", "vram_tier": "12GB", "vram_min": "8GB",
                 "backends": ["CUDA"], "supported_engines": ["llama.cpp"],
                 "engines": [
                     {"engine": "llama.cpp", "tps": "50", "hardware": "RTX 4090",
                      "quant": "Q4", "date": "2026-09-28", "source_post": "https://lightbrd.com/a"},
                     {"engine": "llama.cpp", "tps": "80", "hardware": "RTX 5090",
                      "quant": "Q4", "date": "2026-09-28", "source_post": "https://lightbrd.com/b"},
                 ],
                 "why": "w", "engagement": {"likes": 1, "comments": 0, "views": 1, "last_7d_likes": 1},
                 "last_seen": "2026-09-28",
             }]}
    V.check_no_duplicate_engines(store)
    errs = [f for f in V.FAILURES if "duplicate engine row" in f]
    check("validate: different GPU cards are NOT duplicates (kept)",
          len(errs) == 0, json.dumps(errs))


def test_dedupe_posts_edge_cases():
    """Edge cases for dedupe_posts: empty list, entries missing url, and the
    same url with a missing date must not crash and must not double-count."""
    check("dedupe: empty list -> empty", UT.dedupe_posts([]) == [])
    mixed = [
        {"url": "https://lightbrd.com/a", "date": "2026-09-28"},
        {"url": "", "date": "2026-09-28"},          # no url -> dropped
        {"url": "https://lightbrd.com/a", "date": ""},  # same url, no date
        {"url": "https://lightbrd.com/b", "date": "2026-09-28"},
    ]
    out = UT.dedupe_posts(mixed)
    urls = sorted(p["url"] for p in out)
    check("dedupe: drops url-less entries, dedupes same url", urls == ["https://lightbrd.com/a", "https://lightbrd.com/b"],
          json.dumps(urls))


def test_prune_posts_boundary_30_days():
    """Boundary: a post exactly 30 days old is KEPT (retention), 31 days is
    pruned. Malformed dates are dropped without crashing."""
    m = {"id": "m1", "name": "M1", "engagement": {"seen_posts": [
        {"url": "https://lightbrd.com/30", "date": "2026-08-30"},  # exactly 30d
        {"url": "https://lightbrd.com/31", "date": "2026-08-29"},  # 31d -> prune
        {"url": "https://lightbrd.com/bad", "date": "not-a-date"},  # malformed -> drop
    ]}}
    UT.recompute_7d_engagement(m, today())
    urls = [p["url"] for p in m["engagement"]["seen_posts"]]
    check("prune: exactly-30d kept, 31d pruned, malformed dropped",
          urls == ["https://lightbrd.com/30"], json.dumps(urls))


def test_recompute_7d_boundary():
    """Boundary: a post exactly 7 days old IS counted in last_7d_likes; 8 days
    is not. Empty seen_posts preserves the stored counter (legacy)."""
    m = {"id": "m1", "name": "M1", "engagement": {"seen_posts": [
        {"url": "https://lightbrd.com/7", "date": "2026-09-22"},  # exactly 7d
        {"url": "https://lightbrd.com/8", "date": "2026-09-21"},  # 8d -> out
    ]}}
    UT.recompute_7d_engagement(m, today())
    check("recompute: exactly-7d post counted, 8d not", m["engagement"]["last_7d_likes"] == 1,
          str(m["engagement"]["last_7d_likes"]))
    # legacy: no seen_posts -> reset stale cumulative counter to 0 (a legacy
    # monotonic counter is NOT a 7-day count and must not dominate the rank)
    legacy = {"id": "m2", "name": "M2", "engagement": {"last_7d_likes": 1420}}
    UT.recompute_7d_engagement(legacy, today())
    check("recompute: legacy row resets stale counter to 0 (no rank pollution)",
          legacy["engagement"]["last_7d_likes"] == 0, str(legacy["engagement"]["last_7d_likes"]))


def test_ingest_same_model_engine_gpu_not_duplicated():
    """End-to-end: two raw snapshots carrying the SAME model + engine + t/s +
    GPU card/VRAM (different hardware wording) must produce ONE engine row in
    the store (no duplicate), while a different GPU card adds a second row."""
    store = {
        "engines": {"llama.cpp": {"backend": "CUDA", "note": "x", "url": "https://github.com/ggml-org/llama.cpp"}},
        "models": [{
            "id": "qwen3-14b", "name": "Qwen3 14B", "full_name": "Qwen3-14B", "type": "LLM",
            "formats": [{"name": "GGUF", "hf": "Qwen/Qwen3-14B"}], "license": "Apache 2.0",
            "params": "14B", "hf": "Qwen/Qwen3-14B", "vram_tier": "9GB", "vram_min": "8GB",
            "backends": ["CUDA"], "supported_engines": ["llama.cpp"],
            "engines": [{"engine": "llama.cpp", "tps": "50", "hardware": "RTX 4090",
                         "quant": "Q4", "date": "2026-09-28", "source_post": "https://lightbrd.com/a"}],
            "why": "w", "engagement": {"likes": 1, "comments": 0, "views": 1, "last_7d_likes": 1},
            "last_seen": "2026-09-28",
        }],
    }
    def raw(hw, tps, post, date="2026-09-28"):
        return {"backend": "nvidia", "generated_utc": "2026-09-28T10:00:00Z", "models": [{
            "id": "qwen3-14b", "name": "Qwen3 14B", "full_name": "Qwen3-14B", "type": "LLM",
            "license": "Apache 2.0", "params": "14B", "hf": "Qwen/Qwen3-14B",
            "vram_tier": "9GB", "vram_min": "8GB", "backends": ["CUDA"],
            "engines": [{"engine": "llama.cpp", "tps": tps, "hardware": hw,
                         "quant": "Q4", "date": date, "source_post": post}],
            "last_seen": date,
        }]}
    with tempfile.TemporaryDirectory() as td:
        rdir = Path(td)
        # same model+engine+tps+GPU size, different hardware wording + different post
        (rdir / "nvidia-1.json").write_text(json.dumps(raw("RTX 4090", "50", "https://lightbrd.com/a")))
        (rdir / "nvidia-2.json").write_text(json.dumps(raw("RTX 4090 24GB", "50", "https://lightbrd.com/a2")))
        # different GPU card -> distinct row
        (rdir / "nvidia-3.json").write_text(json.dumps(raw("RTX 5090", "80", "https://lightbrd.com/b")))
        saved = UT.RAW_DIR
        UT.RAW_DIR = rdir
        try:
            UT.ingest_raw_snapshots(store)
        finally:
            UT.RAW_DIR = saved
    m = next(x for x in store["models"] if x["id"] == "qwen3-14b")
    gpu_rows = [(e["hardware"], e["tps"]) for e in m["engines"]]
    check("ingest: same model+engine+tps+GPU size -> ONE row (no duplicate)",
          len(m["engines"]) == 2, json.dumps(gpu_rows))
    check("ingest: same GPU row kept once, diff GPU kept",
          ("RTX 4090 24GB", "50") in gpu_rows and ("RTX 5090", "80") in gpu_rows, json.dumps(gpu_rows))


def test_merge_engines_interaction_weighted():
    """The three engagement rules:
    1. Higher engagement -> that measurement's t/s matters more.
    2. Concordant reports -> engagement-weighted average is set.
    3. Only UPDATE to a higher t/s, never lower the stored value.
    Plus: est-duplicate rows (39.3 vs 39.3 (est)) collapse to one."""
    def eng(tps, likes, hw="RTX 8GB GPU", post="https://lightbrd.com/x", date="2026-09-28"):
        return {"engine": "FreeToken", "tps": tps, "hardware": hw, "date": date,
                "source_post": post, "likes": likes, "comments": 0}

    # rule 3: incoming concordant but LOWER -> keep the stored (higher) value
    cur = [eng("50", 30)]
    inc_lower = [eng("45 (est)", 200)]  # lower core, higher engagement
    out = UT.merge_engines(cur, inc_lower)
    check("interaction: lower re-report keeps the stored higher t/s",
          len(out) == 1 and _core(out[0]["tps"]) == 50.0, json.dumps(out))

    # rule 3b: incoming concordant-but-HIGHER -> update to the higher value
    # (50 -> 55 is within tolerance, so it collapses and the representative is
    # raised toward 55 via the engagement-weighted mean)
    out2 = UT.merge_engines(cur, [eng("55", 200)])
    check("interaction: higher concordant re-report updates the t/s up",
          len(out2) == 1 and _core(out2[0]["tps"]) > 50.0, json.dumps(out2))
    # non-concordant much-higher (50 vs 60, 20% apart) stays distinct — a
    # genuinely different measurement, surfaced by the t/s-descending README.
    out2b = UT.merge_engines(cur, [eng("60", 5)])
    check("interaction: non-concordant higher t/s stays a distinct row",
          len(out2b) == 2, json.dumps(out2b))

    # rules 1+2+3: concordant 39.3(100 likes) + 41(50 likes). Engagement-weighted
    # mean is ~39.87, but 'keep higher' -> final = max(reported, mean) = 41.
    out3 = UT.merge_engines([], [eng("39.3", 100), eng("41", 50)])
    check("interaction: concordant reports collapse, keep-higher wins (41)",
          len(out3) == 1 and _core(out3[0]["tps"]) == 41.0, json.dumps(out3))
    # high-engagement report with a LOWER value pulls the consensus below the
    # higher-engagement low value when it dominates the weight
    out3b = UT.merge_engines([], [eng("39.3", 1000), eng("41", 1)])
    # weighted mean ~39.32 (~39.3), keep-higher still caps at reported 41 -> but
    # the 39.3 report is far higher engagement; final = max(41, ~39.3) = 41.
    check("interaction: keep-higher caps the weighted mean at the reported max",
          len(out3b) == 1 and _core(out3b[0]["tps"]) == 41.0, json.dumps(out3b))

    # est-duplicate collapse: 39.3 vs 39.3 (est) are one row
    out4 = UT.merge_engines([], [eng("39.3", 10), eng("39.3 (est)", 10)])
    check("interaction: est-duplicate collapses to one row",
          len(out4) == 1 and _core(out4[0]["tps"]) == 39.3, json.dumps(out4))

    # non-concordant (45 vs 39.3) stays distinct
    out5 = UT.merge_engines([], [eng("39.3", 10), eng("45", 10)])
    check("interaction: non-concordant different t/s stays distinct",
          len(out5) == 2, json.dumps(out5))


def _core(tps):
    import re
    nums = [float(x) for x in re.findall(r"\d+(?:\.\d+)?", str(tps or ""))]
    return max(nums) if nums else 0.0


def test_merge_engines_edge_cases():
    """Edge cases for the interaction-weighted merge: empty groups, ranges,
    different engines/GPUs, missing engagement, extreme engagement, zero/empty
    tps, and many-concordant collapse."""
    def eng(tps, likes=0, comments=0, hw="RTX 8GB GPU", post="https://lightbrd.com/x",
            date="2026-09-28", engine="FreeToken"):
        return {"engine": engine, "tps": tps, "hardware": hw, "date": date,
                "source_post": post, "likes": likes, "comments": comments}

    # 1. empty inputs
    check("edge: empty current + empty incoming -> []",
          UT.merge_engines([], []) == [], "expected []")
    # 2. single measurement unchanged (core kept, likes defaulted)
    e = UT.merge_engines([], [eng("99.7", likes=5)])[0]
    check("edge: single measurement is kept as-is", _core(e["tps"]) == 99.7 and e.get("likes") == 5, json.dumps(e))
    # 3. no engagement on any -> weight 1 each, collapse to set (max-rep)
    e = UT.merge_engines([], [eng("39.3"), eng("39.3 (est)")])[0]
    check("edge: no-engagement concordant collapse to one", len(UT.merge_engines([], [eng("39.3"), eng("39.3 (est)")])) == 1 and _core(e["tps"]) == 39.3, json.dumps(e))
    # 4. range vs similar single (67-71 core=71 vs 70) concordant
    e = UT.merge_engines([], [eng("67-71", likes=10), eng("70", likes=10)])[0]
    check("edge: range 67-71 and 70 are concordant (collapse, keep-higher=71)",
          _core(e["tps"]) == 71.0, json.dumps(e))
    # 5. far-apart ranges stay distinct
    out = UT.merge_engines([], [eng("67-71", likes=10), eng("120-124", likes=10)])
    check("edge: far-apart ranges 67-71 / 120-124 stay distinct",
          len(out) == 2, json.dumps(out))
    # 6. different engines always distinct
    out = UT.merge_engines([], [eng("50", engine="Ollama"), eng("52", engine="vLLM")])
    check("edge: different engines stay distinct", len(out) == 2, json.dumps(out))
    # 7. different GPU size always distinct
    out = UT.merge_engines([], [eng("50", hw="RTX 8GB GPU"), eng("52", hw="RTX 5090")])
    check("edge: different GPU sizes stay distinct", len(out) == 2, json.dumps(out))
    # 8. zero tps / empty tps -> core 0, no crash, kept
    e = UT.merge_engines([], [eng("", likes=1), eng("", likes=1)])
    check("edge: empty tps does not crash and collapses", len(e) == 1, json.dumps(e))
    # 9. extreme engagement: 40(1 like) + 42(10000 likes) weighted mean ~40.0002
    #    keep-higher caps at 42 -> representative is 42
    e = UT.merge_engines([], [eng("40", likes=1), eng("42", likes=10000)])[0]
    check("edge: extreme-engagement report drives the representative (42)",
          _core(e["tps"]) == 42.0, json.dumps(e))
    # 10. many concordant collapse to ONE row (keep-higher). Values 100..103 span
    #     3%, all within the 12% tolerance, so they form a single group -> 103.
    many = [eng(str(100 + i), likes=1) for i in range(4)]
    e = UT.merge_engines([], many)
    check("edge: many concordant reports collapse to one (keep-higher=103)",
          len(e) == 1 and _core(e[0]["tps"]) == 103.0, json.dumps(e))
    # 10b. a wide spread (30% steps, each pair beyond tolerance) stays distinct
    wide = [eng(str(100 + i * 30), likes=1) for i in range(4)]  # 100,130,160,190
    check("edge: wide-spread reports stay multiple distinct rows",
          len(UT.merge_engines([], wide)) == 4, json.dumps(UT.merge_engines([], wide)))
    # 11. merge never drops an existing row that is far apart (distinct preserved)
    cur = [eng("100", likes=5)]
    inc = [eng("100 (est)", likes=5)]  # concordant -> collapse to 100
    e = UT.merge_engines(cur, inc)
    check("edge: concordant current+incoming collapse, existing not duplicated",
          len(e) == 1 and _core(e[0]["tps"]) == 100.0, json.dumps(e))
    # 12. only likes, comments absent -> still weights by likes
    e = UT.merge_engines([], [{"engine": "F", "tps": "40", "hardware": "8GB", "date": "2026-09-28", "likes": 10},
                              {"engine": "F", "tps": "42", "hardware": "8GB", "date": "2026-09-28", "likes": 100}])[0]
    check("edge: weights by likes even when comments absent (keep-higher=42)",
          _core(e["tps"]) == 42.0, json.dumps(e))


def test_merge_engines_tps_matrix():
    """Data-driven matrix: every (tps_a, tps_b) pair -> expected collapse (1 row)
    or distinct (2 rows) under the concordance rule. Covers identical, est,
    near, decimal-near, range-vs-single, range-vs-range, far, far-range,
    tilde-vs-int, comment-vs-plain, and different-engine/GPU."""
    def eng(tps, hw="RTX 8GB GPU", engine="FreeToken"):
        return {"engine": engine, "tps": tps, "hardware": hw, "date": "2026-09-28",
                "source_post": "https://lightbrd.com/x", "likes": 1, "comments": 0}
    # (a, b, expected_collapse)
    matrix = [
        ("50", "50", True),                       # identical
        ("39.3", "39.3 (est)", True),             # est marker
        ("50", "55", True),                       # near (10%)
        ("39.3", "39.5", True),                   # decimal near
        ("67-71", "70", True),                    # range vs single (71 vs 70)
        ("67-71", "70-72", True),                 # range vs range near
        ("~50", "50", True),                      # tilde vs int
        ("233 (DFlash spec-decode), 74.9 stock", "233", True),  # comment vs plain
        ("39.3", "45", False),                    # far (14.5%)
        ("67-71", "120-124", False),              # far ranges
        ("50", "90", False),                      # far
        ("100", "140", False),                    # far (40%)
    ]
    for a, b, collapse in matrix:
        out = UT.merge_engines([], [eng(a), eng(b)])
        got = len(out) == 1
        check(f"merge-matrix: {a!r} vs {b!r} -> {'collapse' if collapse else 'distinct'}",
              got == collapse, json.dumps(out))
    # different engine / different GPU always distinct
    out = UT.merge_engines([], [eng("50", engine="Ollama"), eng("50", engine="vLLM")])
    check("merge-matrix: same tps different engine -> distinct", len(out) == 2, json.dumps(out))
    out = UT.merge_engines([], [eng("50", hw="RTX 8GB GPU"), eng("50", hw="RTX 5090")])
    check("merge-matrix: same tps different GPU -> distinct", len(out) == 2, json.dumps(out))


def test_eng_weight_composite():
    """_eng_weight uses the composite X signal: likes + 2*comments + 3*reshares
    + log10(views+1), floor 1. Reshares dominate, views are log-scaled, missing
    signals fall back gracefully."""
    def w(**kw):
        m = {"likes": 0, "comments": 0, "reshares": 0, "views": 0}
        m.update(kw)
        return UT._eng_weight(m)
    check("weight: no engagement -> floor 1", w() == 1.0)
    check("weight: likes only", w(likes=10) == 10.0)
    check("weight: comments 2x", w(comments=5) == 10.0)
    check("weight: reshares 3x", w(reshares=5) == 15.0)
    check("weight: reshare-dominant over likes", w(likes=100, reshares=10) == 100 + 30)
    check("weight: views log-scaled (1000 views -> log10(1001)~3.0)", abs(w(views=1000) - 3.0004) < 0.01)
    check("weight: viral views don't dominate (1e6 views -> ~6.0)", abs(w(views=10**6) - 6.0) < 0.01)
    check("weight: combined", w(likes=10, comments=2, reshares=1, views=99) == 10 + 4 + 3 + 2)


def test_ingest_maps_engagement_end_to_end():
    """REAL data-flow test: a raw snapshot whose engine measurements carry
    likes/comments/reshares/views must flow through ingest_raw_snapshots into
    models.json with the engagement preserved AND the t/s engagement-weighted
    (concordant collapse + keep-higher). This proves the search agent's
    per-post engagement is truly mapped, not just unit-tested in isolation."""
    import tempfile as _t
    raw = {
        "backend": "nvidia", "generated_utc": "2026-09-28T10:00:00Z",
        "models": [{
            "id": "qwen3-14b", "name": "Qwen3 14B", "full_name": "Qwen3-14B", "type": "LLM",
            "license": "Apache 2.0", "params": "14B", "hf": "Qwen/Qwen3-14B",
            "vram_tier": "9GB", "vram_min": "8GB", "backends": ["CUDA"],
            "engines": [
                # same engine+GPU, concordant t/s, different engagement
                {"engine": "llama.cpp", "tps": "50", "hardware": "RTX 4090", "date": "2026-09-28",
                 "source_post": "https://lightbrd.com/a", "likes": 30, "comments": 5, "reshares": 2, "views": 1000},
                {"engine": "llama.cpp", "tps": "52 (est)", "hardware": "RTX 4090", "date": "2026-09-28",
                 "source_post": "https://lightbrd.com/b", "likes": 200, "comments": 40, "reshares": 20, "views": 50000},
            ],
            "last_seen": "2026-09-28",
        }],
    }
    store = {"engines": {"llama.cpp": {"backend": "CUDA", "note": "x", "url": "https://github.com/ggml-org/llama.cpp"}}, "models": []}
    with _t.TemporaryDirectory() as td:
        rdir = Path(td); (rdir / "nvidia-1.json").write_text(json.dumps(raw))
        saved = UT.RAW_DIR; UT.RAW_DIR = rdir
        try: UT.ingest_raw_snapshots(store)
        finally: UT.RAW_DIR = saved
    m = store["models"][0]
    # the two concordant measurements collapse to ONE row
    check("e2e: concordant measurements collapse to one engine row",
          len(m["engines"]) == 1, json.dumps(m["engines"]))
    e = m["engines"][0]
    # keep-higher: representative = max(52, weighted mean) -> 52
    check("e2e: keep-higher representative t/s (52)",
          _core(e["tps"]) == 52.0, e["tps"])
    # the representative row carries the HIGHEST-engagement measurement's signals
    check("e2e: representative carries the high-engagement measurement's likes",
          e.get("likes") == 200, json.dumps(e))
    check("e2e: representative carries reshares",
          e.get("reshares") == 20, json.dumps(e))
    check("e2e: representative carries views",
          e.get("views") == 50000, json.dumps(e))
    # the source_post of the high-engagement measurement is kept
    check("e2e: source_post of the high-engagement measurement kept",
          e.get("source_post") == "https://lightbrd.com/b", e.get("source_post"))


def test_ingest_updates_existing_model_to_higher_tps():
    """The user's core rule: a NEW report with HIGHER t/s (and real engagement)
    for an EXISTING model in models.json must UPDATE that model's engine row to
    the higher value — not duplicate it, not keep the stale lower one. And a
    brand-new model is CREATED with the engagement-weighted t/s."""
    import tempfile as _t
    # existing model in the store: llama.cpp at 50
    store = {
        "engines": {"llama.cpp": {"backend": "CUDA", "note": "x", "url": "https://github.com/ggml-org/llama.cpp"}},
        "models": [{
            "id": "qwen3-14b", "name": "Qwen3 14B", "full_name": "Qwen3-14B", "type": "LLM",
            "formats": [{"name": "GGUF", "hf": "Qwen/Qwen3-14B"}], "license": "Apache 2.0",
            "params": "14B", "hf": "Qwen/Qwen3-14B", "vram_tier": "9GB", "vram_min": "8GB",
            "backends": ["CUDA"], "supported_engines": ["llama.cpp"],
            "engines": [{"engine": "llama.cpp", "tps": "50", "hardware": "RTX 4090", "date": "2026-09-20",
                         "source_post": "https://lightbrd.com/old"}],
            "why": "w", "engagement": {"likes": 1, "comments": 0, "views": 1, "last_7d_likes": 1},
            "last_seen": "2026-09-20",
        }],
    }
    # new raw snapshot: same model+engine, HIGHER tps (55) with high engagement
    raw = {
        "backend": "nvidia", "generated_utc": "2026-09-28T10:00:00Z",
        "models": [{
            "id": "qwen3-14b", "name": "Qwen3 14B", "full_name": "Qwen3-14B", "type": "LLM",
            "license": "Apache 2.0", "params": "14B", "hf": "Qwen/Qwen3-14B",
            "vram_tier": "9GB", "vram_min": "8GB", "backends": ["CUDA"],
            "engines": [{"engine": "llama.cpp", "tps": "55", "hardware": "RTX 4090", "date": "2026-09-28",
                         "source_post": "https://lightbrd.com/new", "likes": 500, "comments": 100, "reshares": 50}],
            "last_seen": "2026-09-28",
        }],
    }
    with _t.TemporaryDirectory() as td:
        rdir = Path(td); (rdir / "nvidia-1.json").write_text(json.dumps(raw))
        saved = UT.RAW_DIR; UT.RAW_DIR = rdir
        try: UT.ingest_raw_snapshots(store)
        finally: UT.RAW_DIR = saved
    m = store["models"][0]
    # the existing model is UPDATED, not duplicated: still one llama.cpp row
    check("update: existing model keeps ONE engine row (not duplicated)",
          len(m["engines"]) == 1, json.dumps(m["engines"]))
    e = m["engines"][0]
    # t/s raised to the higher report (55), not the stale 50
    check("update: existing model's t/s raised to the higher report (55)",
          _core(e["tps"]) == 55.0, e["tps"])
    # the new high-engagement measurement's signals are carried
    check("update: representative carries the new report's engagement",
          e.get("likes") == 500 and e.get("reshares") == 50, json.dumps(e))
    check("update: source_post updated to the new report",
          e.get("source_post") == "https://lightbrd.com/new", e.get("source_post"))


def test_merge_engines_engagement_tps_permutations():
    """DATA-DRIVEN permutation matrix of engagement x tps: every combination of
    (low/high engagement) x (lower/same/higher tps) -> expected (rows, core).
    Each row: (tps_a, likes_a, tps_b, likes_b, expected_rows, expected_core or
    None for 'distinct'). keep-higher wins over the weighted mean."""
    def eng(tps, likes, hw="RTX 8GB GPU", post="https://lightbrd.com/x"):
        return {"engine": "FreeToken", "tps": tps, "hardware": hw, "date": "2026-09-28",
                "source_post": post, "likes": likes, "comments": 0}
    # (a_tps, a_likes, b_tps, b_likes, expected_rows, expected_core)
    matrix = [
        # higher vs higher (both high eng) -> collapse, higher tps
        ("50", 1000, "55", 900, 1, 55.0),
        # low vs higher (low-eng lower tps vs high-eng higher) -> higher tps
        ("50", 1, "55", 1000, 1, 55.0),
        # low vs same -> collapse to that tps
        ("50", 1, "50", 1000, 1, 50.0),
        # lower vs low (both low eng) -> keep higher
        ("40", 1, "45", 1, 1, 45.0),
        # high-eng lower vs low-eng higher -> keep-higher caps at 55
        ("50", 10000, "55", 1, 1, 55.0),
        # low-eng lower vs high-eng higher -> higher + higher eng = 55
        ("50", 1, "55", 10000, 1, 55.0),
        # far-apart tps -> distinct regardless of engagement
        ("50", 10000, "90", 1, 2, None),
    ]
    for a_tps, a_l, b_tps, b_l, rows, core in matrix:
        out = UT.merge_engines([], [eng(a_tps, a_l), eng(b_tps, b_l)])
        ok_rows = len(out) == rows
        ok_core = (core is None) or (len(out) == 1 and _core(out[0]["tps"]) == core)
        check(f"perm-matrix: {a_tps}@{a_l} vs {b_tps}@{b_l} -> {rows} row(s) core={core}",
              ok_rows and ok_core, json.dumps(out))


def test_eng_weight_signal_ordering():
    """DATA-DRIVEN: verify the formula weights each signal correctly AND that
    they're ordered against each other — reshares (3x) > comments (2x) > likes
    (1x) > views (log10). Each case asserts an ordering or equivalence."""
    def w(**kw):
        m = {"likes": 0, "comments": 0, "reshares": 0, "views": 0}
        m.update(kw)
        return UT._eng_weight(m)

    checks = [
        ("1 like = 1", w(likes=1) == 1.0),
        ("1 comment = 2x a like", w(comments=1) == 2.0),
        ("1 reshare = 3x a like", w(reshares=1) == 3.0),
        # ordering: reshare > comment > like
        ("reshare outweighs comment", w(reshares=1) > w(comments=1)),
        ("comment outweighs like", w(comments=1) > w(likes=1)),
        # reshare > equal likes
        ("1 reshare (3) > 2 likes (2)", w(reshares=1) > w(likes=2)),
        ("1 comment (2) == 2 likes", w(comments=1) == w(likes=2)),
        ("3 comments (6) > 5 likes (5)", w(comments=3) > w(likes=5)),
        ("2 reshares (6) == 3 comments (6)", w(reshares=2) == w(comments=3)),
        # additive
        ("likes+comments add", w(likes=1, comments=1) == 3.0),
        ("comments+reshares add", w(comments=1, reshares=1) == 5.0),
        # views are LOG-scaled: reach, not endorsement. A million views (6) is
        # still modest — equivalent to ~6 likes, and dwarfed by the same count
        # of true endorsements.
        ("1e6 views ~6 likes (not 1e6)", abs(w(views=10**6) - w(likes=6)) < 0.01),
        ("views grow as log, not linear: 1e9 views << 1e9 likes", w(views=10**9) < w(likes=10**9)),
        ("1e9 views (~9) < 1e4 likes", w(views=10**9) < w(likes=10**4)),
        ("1e6 views contribute ~6, far below 10 likes", w(views=10**6) < w(likes=10)),
    ]
    for name, cond in checks:
        check(f"weight-ordering: {name}", cond, "")



def test_dedupe_posts_tolerates_bare_string_entries():
    """REGRESSION: the CPU search agent wrote engagement.seen_posts as a bare
    URL string (not a {'url','date'} dict), which crashed dedupe_posts with
    'str' object has no attribute 'get' and aborted the whole refresh aggregate.
    dedupe_posts must coerce bare strings to dicts instead of crashing, and
    prune/recompute must not choke on them either."""
    # exact shape from the failing cpu-20261001-170219.json artifact
    posts = ["https://lightbrd.com/ossphere_dev/status/2104934233366241296"]
    out = UT.dedupe_posts(posts)
    check("dedupe: bare-string entry coerced to dict, not crash",
          len(out) == 1 and isinstance(out[0], dict) and out[0]["url"] == posts[0],
          json.dumps(out))
    # mixed: a dict + a bare string for the same URL -> one entry
    mixed = [
        {"url": "https://lightbrd.com/a", "date": "2026-09-28"},
        "https://lightbrd.com/a",
        "https://lightbrd.com/b",
    ]
    out2 = UT.dedupe_posts(mixed)
    urls = sorted(p["url"] for p in out2)
    check("dedupe: dict + bare string for same url collapse to one",
          urls == ["https://lightbrd.com/a", "https://lightbrd.com/b"], json.dumps(urls))
    # prune_posts must not crash on a bare string (no date -> dropped, not crash)
    pruned = UT.prune_posts(["https://lightbrd.com/x"], today())
    check("prune: bare-string entry dropped without crash", pruned == [], json.dumps(pruned))
    # recompute_7d_engagement on a model whose seen_posts is a bare string
    m = {"id": "m1", "name": "M1", "engagement": {"seen_posts": ["https://lightbrd.com/a"]}}
    UT.recompute_7d_engagement(m, today())
    check("recompute: bare-string seen_posts does not crash, resets to 0",
          m["engagement"]["last_7d_likes"] == 0, str(m["engagement"]["last_7d_likes"]))


def test_ingest_normalizes_bare_string_seen_posts():
    """REGRESSION: a raw snapshot whose model carries engagement.seen_posts as a
    bare URL string must be normalized at ingest (merged with engine-derived
    posts, deduped) so the malformed shape never persists into the store."""
    raw = {
        "backend": "cpu", "generated_utc": "2026-09-29T10:00:00Z",
        "models": [{
            "id": "webllm-llama-3.1-8b-inbrowser", "name": "Llama-3.1-8B (WebLLM)",
            "full_name": "Meta-Llama-3.1-8B-Instruct", "type": "LLM (edge)",
            "license": "Llama 3.1", "params": "8B", "hf": "meta-llama/Llama-3.1-8B-Instruct",
            "vram_tier": "8GB", "vram_min": "8GB", "backends": ["CPU"],
            "engines": [{"engine": "WebLLM", "tps": "41.1", "hardware": "M3 Max",
                         "date": "2026-09-29",
                         "source_post": "https://lightbrd.com/ossphere_dev/status/2104934233366241296"}],
            "engagement": {"likes": 0, "comments": 1, "reshares": 5, "views": 223,
                           "last_7d_likes": 0,
                           "seen_posts": ["https://lightbrd.com/ossphere_dev/status/2104934233366241296"]},
            "last_seen": "2026-09-29",
        }],
    }
    with tempfile.TemporaryDirectory() as td:
        rawdir = Path(td) / "raw"; rawdir.mkdir()
        (rawdir / "cpu-20260929-100000.json").write_text(json.dumps(raw))
        store = {"generated_utc": "2026-09-29T10:00:00Z", "engines": {}, "models": []}
        # point UT at the temp dir
        old_raw = UT.RAW_DIR
        UT.RAW_DIR = rawdir
        try:
            added, updated = UT.ingest_raw_snapshots(store)
        finally:
            UT.RAW_DIR = old_raw
        check("ingest: bare-string seen_posts model added", added == 1, str(added))
        m = store["models"][0]
        sp = m["engagement"]["seen_posts"]
        check("ingest: seen_posts normalized to dicts (no bare strings)",
              all(isinstance(p, dict) for p in sp), json.dumps(sp))
        check("ingest: engine-derived post preserved with date",
              any(p.get("url") == "https://lightbrd.com/ossphere_dev/status/2104934233366241296"
                  and p.get("date") == "2026-09-29" for p in sp), json.dumps(sp))


def main() -> int:
    print("7-day post-granularity engagement aggregation")
    test_dedupe_posts_collapses_same_url()
    test_recompute_7d_counts_distinct_posts_in_window()
    test_recompute_dedupes_before_counting()
    test_prune_posts_retains_30d_removes_older()
    test_ingest_seeds_and_dedupes_seen_posts()
    test_correct_raw_fills_missing_backend()
    test_merge_engines_dedup_same_gpu_vram()
    test_validate_catches_duplicate_engine_same_gpu_vram()
    test_validate_allows_same_engine_different_gpu()
    test_merge_engines_interaction_weighted()
    test_merge_engines_edge_cases()
    test_merge_engines_tps_matrix()
    test_eng_weight_composite()
    test_ingest_maps_engagement_end_to_end()
    test_ingest_updates_existing_model_to_higher_tps()
    test_merge_engines_engagement_tps_permutations()
    test_eng_weight_signal_ordering()
    test_dedupe_posts_edge_cases()
    test_dedupe_posts_tolerates_bare_string_entries()
    test_ingest_normalizes_bare_string_seen_posts()
    test_prune_posts_boundary_30_days()
    test_recompute_7d_boundary()
    test_ingest_same_model_engine_gpu_not_duplicated()
    print(f"\nPASSED {_PASS} | FAILED {_FAIL}")
    return 1 if _FAIL else 0


if __name__ == "__main__":
    raise SystemExit(main())
