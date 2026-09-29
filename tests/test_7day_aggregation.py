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
    errs = [f for f in V.FAILURES if "duplicate identical engine row" in f]
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
    errs = [f for f in V.FAILURES if "duplicate identical engine row" in f]
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
    test_dedupe_posts_edge_cases()
    test_prune_posts_boundary_30_days()
    test_recompute_7d_boundary()
    test_ingest_same_model_engine_gpu_not_duplicated()
    print(f"\nPASSED {_PASS} | FAILED {_FAIL}")
    return 1 if _FAIL else 0


if __name__ == "__main__":
    raise SystemExit(main())
