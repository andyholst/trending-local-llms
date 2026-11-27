#!/usr/bin/env python3
"""tests/test_rollup_history_counter_1847.py — issue #1847.

A rule-3b history post kept in `seen_posts` by the #1827 `keep_urls` exemption is
still the evidence of a stored measurement. The #1182 counter rollup used only the
retention-only re-prune (`prune_posts(posts, today)`), so a row whose ONLY liked
posts are those history posts was written back with engagement.likes == 0 while
its own `seen_posts` carried real likes (43 rows in refresh run 46061634103).

These guards call the REAL recompute_7d_engagement / prune_posts on real in-memory
rows and on the shipped store. No business logic is mocked; no external system is
touched beyond reading data/models.json.

Run:  python3 tests/test_rollup_history_counter_1847.py   or   make test
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "tests"))

import update_trending as UT  # noqa: E402
from wiring import wired  # noqa: E402

_PASS = 0
_FAIL = 0
TODAY = datetime(2026, 11, 27, tzinfo=timezone.utc)
OLD = "2026-09-01"   # 87 days before TODAY — outside RETENTION_DAYS (30)
NEW = "2026-11-26"   # inside the trending window


def check(name, cond, detail=""):
    global _PASS, _FAIL
    if cond:
        _PASS += 1
        print(f"  ok  {name}")
    else:
        _FAIL += 1
        print(f"  FAIL {name}" + (f"  [{detail}]" if detail else ""))


def _post(url, date, likes, comments=0, reshares=0, views=0):
    p = {"url": url, "date": date, "likes": likes,
         "comments": comments, "views": views}
    if reshares is not None:
        p["reshares"] = reshares
    return p


def _history_row():
    """Row whose only counter-bearing posts are rule-3b history posts."""
    url = "https://lightbrd.com/h/status/9001"
    return {
        "id": "history-model",
        "name": "History Model",
        "params": "9B",
        "engines": [{"name": "MLX", "tps": 10, "date": OLD, "source_post": url}],
        "engagement": {
            "likes": 0, "comments": 0, "reshares": 0, "views": 0,
            "seen_posts": [_post(url, OLD, 500, 20, 5, 3000)],
        },
    }


def test_history_only_counter_is_sourced_and_post_retained():
    """RED on base: the counter stayed 0 although the retained history post carries 500."""
    m = _history_row()
    retained = m["engagement"]["seen_posts"][0]["url"]
    UT.recompute_7d_engagement(m, TODAY)
    e = m["engagement"]
    check("a history-only row sources its likes from seen_posts",
          e["likes"] == 500, str(e["likes"]))
    check("comments / reshares / views are sourced from the same post",
          (e["comments"], e["reshares"], e["views"]) == (20, 5, 3000), str(e))
    check("the rule-3b history post is still retained in seen_posts (#1827 intact)",
          any(p.get("url") == retained for p in e["seen_posts"]), str(e["seen_posts"]))
    check("that post really is outside the retention window",
          UT.prune_posts(e["seen_posts"], TODAY) == [], "post was not old")


def test_retention_view_stays_primary():
    """A fresh post wins over an old history post — `counted = posts` would over-count."""
    m = _history_row()
    m["engagement"]["seen_posts"].append(
        _post("https://lightbrd.com/h/status/9002", NEW, 120, 3, 1, 900))
    m["engines"].append({"name": "MLX", "tps": 11, "date": NEW,
                         "source_post": "https://lightbrd.com/h/status/9002"})
    UT.recompute_7d_engagement(m, TODAY)
    e = m["engagement"]
    check("the retention-only sum is primary, not the whole seen_posts sum",
          e["likes"] == 120, str(e["likes"]))
    check("rank inputs are untouched",
          e["last_7d_likes"] == e["posts_7d"] == 1, str(e))


def test_max_is_never_lowered_on_the_fallback_path():
    m = _history_row()
    m["engagement"]["likes"] = 5000
    UT.recompute_7d_engagement(m, TODAY)
    check("a higher stored counter is never lowered by the fallback",
          m["engagement"]["likes"] == 5000, str(m["engagement"]["likes"]))


def test_fallback_does_not_invent_an_absent_key():
    m = _history_row()
    m["engagement"].pop("reshares")
    m["engagement"]["seen_posts"][0].pop("reshares")
    UT.recompute_7d_engagement(m, TODAY)
    check("an absent optional counter stays absent when no post carries it",
          "reshares" not in m["engagement"], str(m["engagement"]))
    check("the other counters still roll up from history",
          m["engagement"]["likes"] == 500, str(m["engagement"]["likes"]))


def test_shipped_store_has_no_zero_with_liked_posts():
    store = json.loads((ROOT / "data" / "models.json").read_text())
    zero_with_posts = 0
    for row in store["models"]:
        eng = row.get("engagement") or {}
        sourced = sum(int(p.get("likes") or 0) for p in (eng.get("seen_posts") or []))
        if sourced > 0 and not (eng.get("likes") or 0):
            zero_with_posts += 1
    check("no shipped row has a zero aggregate while its posts carry likes",
          zero_with_posts == 0, str(zero_with_posts))


def test_flash_next_pinned_counter_is_preserved():
    store = json.loads((ROOT / "data" / "models.json").read_text())
    flash = next(r for r in store["models"] if r["id"] == "qwen3.8-flash-next-125b")
    check("flash-next stays at the pinned 19,516 likes (#1182)",
          flash["engagement"]["likes"] == 19516, str(flash["engagement"]["likes"]))


def test_wiring():
    check("this suite is discovered by `make test`", wired(__file__), "")


def main() -> int:
    print("rollup history counter (issue #1847):")
    test_history_only_counter_is_sourced_and_post_retained()
    test_retention_view_stays_primary()
    test_max_is_never_lowered_on_the_fallback_path()
    test_fallback_does_not_invent_an_absent_key()
    test_shipped_store_has_no_zero_with_liked_posts()
    test_flash_next_pinned_counter_is_preserved()
    test_wiring()
    print(f"{'FAILED' if _FAIL else 'PASSED'} {_PASS} | FAILED {_FAIL}")
    return 1 if _FAIL else 0


if __name__ == "__main__":
    raise SystemExit(main())
