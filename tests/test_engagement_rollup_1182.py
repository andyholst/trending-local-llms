#!/usr/bin/env python3
"""tests/test_engagement_rollup_1182.py — issue #1182: a model-level counter that may only
grow must not sit at 0 while its own source posts carry values.

Measured in the shipped store (2026-11-21): 56/120 rows had engagement.likes == 0 while
their `seen_posts` summed real likes; the flagship qwen3.8-flash-next-125b row had 47 posts
summing 19,516 likes / 319 comments / 210 reshares / 117,971 views with every aggregate at 0.

This suite locks the repair in the ONE rollup seam (`recompute_7d_engagement`):

  1. cumulative counters are raised to at least the sum of their source posts;
  2. MAX, never assignment — a higher ingest-provided value is never lowered (rule 3b);
  3. the rank semantics are UNCHANGED: last_7d_likes stays posts_7d, and trend_score is
     computed from 7-day post buzz only — these legacy counters never dominate the tables
     (the correction posted on #1182);
  4. the shipped store carries the repaired counters, and the stored values equal the
     render seam's output (the store/render invariant);
  5. an optional counter absent from a row is NOT invented as an empty key — the exact-match
     golden ingest fixtures broke on `reshares: 0` in CI (rule 2, no invented data);
  6. the guard is RED on an authentic pre-change seam blob pinned in this file, never an
    empty `git show origin/master:…` that passes vacuously in a shallow CI checkout.

The guards call the REAL update_trending module; the only external system is the filesystem.
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# The genuine pre-#1182 rollup body, pinned verbatim from `git show
# e2bad5f6^:scripts/update_trending.py`. An in-memory fixture (issue #1292)
# cannot go empty in a shallow CI checkout, so the guard below is RED for the
# same reason on every clone instead of passing on empty `git show` output.
PRECHANGE_RECOMPUTE = r'''def recompute_7d_engagement(m: dict, today: datetime) -> None:
    eng = m.setdefault("engagement", {})
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
    eng["score_7d"] = buzz
    eng["speed_bonus"] = speed
    eng["trend_score"] = round(buzz + speed, 1)
    eng["last_7d_likes"] = len(recent)
    dates = [d for d in [_post_date(p) for p in posts] + [e.get("date", "") for e in m.get("engines", [])]
             if re.fullmatch(r"\d{4}-\d{2}-\d{2}", d or "")]
    if dates:
        m["last_seen"] = max(dates)
'''
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "tests"))

import update_trending as UT  # noqa: E402
from wiring import wired  # noqa: E402

_PASS = 0
_FAIL = 0
TODAY = datetime(2026, 11, 21, tzinfo=timezone.utc)


def check(name, cond, detail=""):
    global _PASS, _FAIL
    if cond:
        _PASS += 1
        print(f"  ok  {name}")
    else:
        _FAIL += 1
        print(f"  FAIL {name}" + (f"  [{detail}]" if detail else ""))


def _row(likes=0):
    return {
        "id": "flash", "name": "Flash 125B", "params": "125B (MoE)",
        "engagement": {
            "likes": likes, "comments": 0, "reshares": 0, "views": 0,
            "seen_posts": [
                {"url": "https://lightbrd.com/a/status/1", "date": "2026-11-20",
                 "likes": 120, "comments": 3, "reshares": 2, "views": 900},
                {"url": "https://lightbrd.com/a/status/2", "date": "2026-11-19",
                 "likes": 77, "comments": 1, "reshares": 0, "views": 100},
            ],
        },
    }


def test_counters_are_raised_from_the_posts_they_store():
    m = _row()
    UT.recompute_7d_engagement(m, TODAY)
    e = m["engagement"]
    check("likes becomes the source sum", e["likes"] == 197, str(e["likes"]))
    check("comments / reshares / views become their source sums",
          (e["comments"], e["reshares"], e["views"]) == (4, 2, 1000), str(e))
    check("last_7d_likes stays posts_7d (locked rank semantics)",
          e["last_7d_likes"] == e["posts_7d"] == 2, str(e))
    check("trend_score comes from buzz, not the cumulative counters",
          e["trend_score"] == round(e["buzz_7d"] + e["speed_bonus"], 1), str(e))


def test_an_existing_higher_value_is_never_lowered():
    m = _row(likes=5000)
    UT.recompute_7d_engagement(m, TODAY)
    check("MAX keeps the higher ingest-provided value (rule 3b)",
          m["engagement"]["likes"] == 5000, str(m["engagement"]["likes"]))


def test_a_row_with_no_posts_keeps_zeros():
    m = _row()
    m["engagement"]["seen_posts"] = []
    UT.recompute_7d_engagement(m, TODAY)
    check("no source posts means no invented value (rule 2)",
          m["engagement"]["likes"] == 0 and m["engagement"]["last_7d_likes"] == 0,
          str(m["engagement"]))


def test_the_shipped_store_carries_the_repair():
    store = json.loads((ROOT / "data" / "models.json").read_text())
    flash = next(m for m in store["models"] if m["id"] == "qwen3.8-flash-next-125b")
    e = flash["engagement"]
    check("flash-next's 19,516 likes are now stored", e["likes"] == 19516, str(e["likes"]))
    check("and its comments / reshares / views", (e["comments"], e["reshares"], e["views"])
          == (319, 210, 117971), str(e))
    zero_with_posts = 0
    for m in store["models"]:
        eng = m.get("engagement") or {}
        posts = eng.get("seen_posts") or []
        sourced = sum(int(p.get("likes") or 0) for p in posts)
        if sourced > 0 and not (eng.get("likes") or 0):
            zero_with_posts += 1
    check("no row still has a zero aggregate while its posts carry likes",
          zero_with_posts == 0, str(zero_with_posts))


def test_stored_counters_equal_the_rollup_output():
    """The store and the render seam must agree — otherwise the README shows counters
    that data/models.json does not hold, and the next refresh silently rewrites them."""
    store = UT.load_store()
    gen = json.loads((ROOT / "data" / "models.json").read_text()).get("generated_utc")
    as_of = UT.parse_utc_stamp(gen)
    disagree = []
    for m in store["models"]:
        eng = m.get("engagement") or {}
        before = {k: int(eng.get(k) or 0) for k in ("likes", "comments", "reshares", "views")}
        UT.recompute_7d_engagement(m, as_of)
        after = {k: int(m["engagement"].get(k) or 0)
                 for k in ("likes", "comments", "reshares", "views")}
        if before != after:
            disagree.append((m["id"], before, after))
    check("every stored counter equals what the render seam computes",
          not disagree, str(disagree[:3]))


def test_an_absent_optional_counter_is_not_invented():
    """Golden fixtures omit `reshares` on rows with no reshare data — the rollup
    must not introduce an empty key (rule 2; the CI failure this fixed)."""
    m = _row()
    m["engagement"].pop("reshares", None)
    for p in m["engagement"]["seen_posts"]:
        p.pop("reshares", None)
    UT.recompute_7d_engagement(m, TODAY)
    check("an absent optional counter stays absent when no post carries it",
          "reshares" not in m["engagement"], str(m["engagement"]))
    check("the other counters still roll up",
          m["engagement"]["likes"] == 197, str(m["engagement"]["likes"]))


def test_the_pre_change_fixture_is_authentic():
    # Loud refusal if the pinned blob is empty/garbled — the failure mode the
    # old `git show origin/master:` probe hid behind a vacuous pass.
    check("the pre-change blob is a non-empty rollup body",
          "def recompute_7d_engagement(" in PRECHANGE_RECOMPUTE
          and "eng[\"last_7d_likes\"]" in PRECHANGE_RECOMPUTE
          and len(PRECHANGE_RECOMPUTE) > 200,
          repr(PRECHANGE_RECOMPUTE[:80]))


def test_the_guard_is_red_on_the_pre_change_seam():
    old = PRECHANGE_RECOMPUTE
    check("the fixture resolved to the real pre-change rollup",
          "def recompute_7d_engagement(" in old, repr(old[:80]))
    check("the pre-change rollup never reads post counters into the aggregates",
          "for counter in" not in old and "19,516" not in old, old[-200:])


def test_wiring():
    check("this suite is discovered by `make test`", wired(__file__), "")


def main() -> int:
    print("engagement rollup (issue #1182):")
    test_counters_are_raised_from_the_posts_they_store()
    test_an_existing_higher_value_is_never_lowered()
    test_a_row_with_no_posts_keeps_zeros()
    test_the_shipped_store_carries_the_repair()
    test_stored_counters_equal_the_rollup_output()
    test_an_absent_optional_counter_is_not_invented()
    test_the_pre_change_fixture_is_authentic()
    test_the_guard_is_red_on_the_pre_change_seam()
    test_wiring()
    print(f"{'FAILED' if _FAIL else 'PASSED'} {_PASS} | FAILED {_FAIL}")
    return 1 if _FAIL else 0


if __name__ == "__main__":
    raise SystemExit(main())
