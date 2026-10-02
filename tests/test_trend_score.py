#!/usr/bin/env python3
"""Trend score tests (issue #59): breadth-first buzz + speed on consumer hardware.

  - test_real_store_bonsai_beats_single_post   REAL data from refresh #58 (fixture)
  - test_breadth_beats_light_single_post       1 post (<=10 interactions) < 5 posts
  - test_viral_post_still_wins                 5,000 likes beats 3 silent posts
  - test_post_buzz_values                      formula values + unknown counts = base 1
  - test_speed_breaks_equal_buzz               same buzz -> faster consumer t/s first
  - test_speed_only_while_trending             recent/stale rows get no speed bonus
  - test_datacenter_never_earns_speed          H100 / 80 GB / 4x4090 excluded; Mac + CPU count
  - test_vram_parsing                          explicit GB, known cards, laptop, Nx
  - test_no_duplicate_posts_after_tps_rewrite  merge rewrites tps -> posts_7d unchanged
  - test_real_posts_persist_placeholders_derived
  - test_readme_trend_cell                     score + breakdown shown
  - test_validator_ranking_accepts_and_rejects reorder / wrong score -> FAIL

Run:  python3 tests/test_trend_score.py   or   make test
"""
from __future__ import annotations

import copy
import json
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import update_trending as UT  # noqa: E402
import validate as V  # noqa: E402

FIXTURE = ROOT / "tests" / "fixtures" / "store_pr58_trend.json"
TODAY = datetime(2026, 10, 1, tzinfo=timezone.utc)
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


def meas(engine, tps, hw, date, post, **eng):
    return {"engine": engine, "tps": tps, "hardware": hw, "quant": "Q4", "date": date,
            "source_post": post, **eng}


def model(mid, engines, last_seen="2026-09-30"):
    return {"id": mid, "name": mid, "engines": engines, "last_seen": last_seen,
            "engagement": {"seen_posts": []}}


def eng(ms, mid):
    return next(m for m in ms if m["id"] == mid)["engagement"]


def order(ms, today=TODAY):
    return [m["id"] for m in UT.sort_models(ms, today)]


def test_real_store_bonsai_beats_single_post():
    s = json.loads(FIXTURE.read_text())
    today = V._as_of(s)
    o = order(s["models"], today)
    check("real: Bonsai 2 27B (5 posts, 237 t/s on a 16 GB Mac) ranks first", o[0] == "bonsai-2-27b", o)
    check("real: ...above Qwen3.8-27B (1 post, 2 likes + 4 comments)",
          o.index("bonsai-2-27b") < o.index("qwen3.8-27b"), o)
    b = eng(s["models"], "bonsai-2-27b")
    check("real: Bonsai posts_7d counts real posts once (5, not the 9 duplicates)", b["posts_7d"] == 5, b["posts_7d"])
    check("real: trend = buzz + speed", abs(b["trend_score"] - (b["buzz_7d"] + b["speed_bonus"])) <= 0.1, b)


def test_breadth_beats_light_single_post():
    ms = [
        model("one", [meas("llama.cpp", "40", "RTX 4090", "2026-09-30", "https://lightbrd.com/a/status/1",
                           likes=5, comments=2, reshares=0, views=20000)]),
        model("five", [meas("llama.cpp", "40", "RTX 4090", "2026-09-30", f"https://lightbrd.com/b/status/{i}")
                       for i in range(5)]),
    ]
    check("breadth: 5 silent posts outrank 1 post with 9 interactions + 20k views",
          order(ms)[0] == "five", [(m["id"], m["engagement"]["trend_score"]) for m in ms])


def test_viral_post_still_wins():
    ms = [
        model("viral", [meas("llama.cpp", "40", "RTX 4090", "2026-09-30", "https://lightbrd.com/a/status/1",
                             likes=5000, views=10000)]),
        model("three", [meas("llama.cpp", "40", "RTX 4090", "2026-09-30", f"https://lightbrd.com/b/status/{i}")
                        for i in range(3)]),
    ]
    check("viral: a 5,000-like post still outranks 3 silent posts", order(ms)[0] == "viral",
          [(m["id"], m["engagement"]["trend_score"]) for m in ms])


def test_post_buzz_values():
    check("buzz: silent / unknown counts = 1 (base, never a penalty)", UT.post_buzz({}) == 1.0)
    light = UT.post_buzz({"likes": 2, "comments": 4, "views": 310})
    check("buzz: 2 likes + 4 comments + 310 views ~ 3.35", abs(light - 3.35) < 0.01, light)
    viral = UT.post_buzz({"likes": 5000, "views": 10000})
    check("buzz: 5,000 likes + 10k views ~ 8.1 (diminishing returns)", 8.0 < viral < 8.3, viral)
    check("buzz: garbage counts read as 0", UT.post_buzz({"likes": "n/a", "views": None}) == 1.0)


def test_speed_breaks_equal_buzz():
    ms = [
        model("slow", [meas("llama.cpp", "20", "RTX 3060", "2026-09-30", "https://lightbrd.com/a/status/1")]),
        model("fast", [meas("llama.cpp", "150", "RTX 4090", "2026-09-30", "https://lightbrd.com/b/status/2")]),
    ]
    o = order(ms)
    check("speed: equal buzz -> faster consumer t/s ranks first", o[0] == "fast", o)
    check("speed: 150 t/s -> +4.0", eng(ms, "fast")["speed_bonus"] == 4.0, eng(ms, "fast"))
    check("speed: bonus values 10/70/630 -> 1/3/6",
          (UT.speed_bonus(10), UT.speed_bonus(70), UT.speed_bonus(630)) == (1.0, 3.0, 6.0))


def test_speed_only_while_trending():
    ms = [model("old", [meas("llama.cpp", "500", "RTX 4090", "2026-09-15", "https://lightbrd.com/a/status/1")],
                last_seen="2026-09-15")]
    UT.sort_models(ms, TODAY)
    e = eng(ms, "old")
    check("speed: no posts in 7 days -> speed_bonus 0, trend 0",
          e["speed_bonus"] == 0 and e["trend_score"] == 0, e)


def test_datacenter_never_earns_speed():
    cases = [
        ("H100 80GB", False), ("A100", False), ("RTX PRO 6000 96GB", False), ("4x RTX 4090", False),
        ("RTX 5090", True), ("2x RTX 3090", True), ("RTX A6000 48GB", True),
        ("MacBook Pro M4 Max 128GB", True), ("Ryzen 9 7950X", True), ("", True),
    ]
    for hw, want in cases:
        got = UT.in_scope({"engine": "vLLM", "hardware": hw})
        check(f"scope: '{hw or '(blank)'}' in scope = {want}", got == want, got)
    ms = [model("dc", [meas("vLLM", "1200", "H100 80GB", "2026-09-30", "https://lightbrd.com/a/status/1"),
                       meas("llama.cpp", "30", "RTX 4090", "2026-09-30", "https://lightbrd.com/a/status/2")])]
    UT.sort_models(ms, TODAY)
    check("scope: speed uses the consumer 30 t/s, not the H100 1200",
          eng(ms, "dc")["speed_bonus"] == UT.speed_bonus(30), eng(ms, "dc"))


def test_vram_parsing():
    cases = [("RTX 5060 Ti 16GB", 16), ("RTX 4090", 24), ("RTX 4090 Laptop", 16), ("RTX 5090", 32),
             ("2x RTX 3090", 48), ("4x RTX 4090", 96), ("RTX 3060 12 GB", 12), ("unknown box", None)]
    for hw, want in cases:
        got = UT.hardware_vram_gb(hw)
        check(f"vram: '{hw}' -> {want}", got == (float(want) if want is not None else None), got)


def test_no_duplicate_posts_after_tps_rewrite():
    m = model("dup", [meas("llama.cpp", "60-91", "RTX 4070 12GB", "2026-09-30", "https://lightbrd.com/someone")])
    UT.sort_models([m], TODAY)
    first = m["engagement"]["posts_7d"]
    m["engines"][0]["tps"] = "91"  # what merge_engines does (keep-higher reformat)
    UT.sort_models([m], TODAY)
    UT.sort_models([m], TODAY)
    check("dupes: tps rewrite + re-sorts keep posts_7d at 1", first == 1 and m["engagement"]["posts_7d"] == 1,
          m["engagement"]["seen_posts"])


def test_real_posts_persist_placeholders_derived():
    m = model("persist", [meas("llama.cpp", "50", "RTX 4090", "2026-09-30", "https://lightbrd.com/")])
    m["engagement"]["seen_posts"] = [
        {"url": "https://lightbrd.com/x/status/77", "date": "2026-09-29", "likes": 3},  # real, no measurement now
        {"url": "https://lightbrd.com/", "date": "2026-09-29", "engine": "llama.cpp", "tps": "1"},  # stale placeholder
    ]
    UT.sort_models([m], TODAY)
    urls = [p["url"] for p in m["engagement"]["seen_posts"]]
    check("persist: stored real post kept", "https://lightbrd.com/x/status/77" in urls, urls)
    check("persist: stale placeholder dropped, current one derived", m["engagement"]["posts_7d"] == 2, urls)


def test_last_seen_from_data_not_merge_time():
    """REGRESSION: re-running the merge over a committed raw snapshot stamped
    last_seen = today, so DeepSeek R1 1.5B (only measurement 2026-06-25) showed
    as 'trending' with no posts in 7 days. last_seen must come from the data."""
    m = model("old", [meas("Ollama", "4", "Raspberry Pi 4B", "2026-06-25", "https://lightbrd.com/")],
              last_seen="2026-10-01")  # what ingest stamped
    UT.sort_models([m], TODAY)
    check("last_seen: derived from the newest measurement date", m["last_seen"] == "2026-06-25", m["last_seen"])
    check("last_seen: so the row is stale, not trending", UT.model_band(m, TODAY) == 2)
    with tempfile.TemporaryDirectory() as td:
        raw = {"backend": "cpu", "generated_utc": "2026-10-01T00:00:00Z", "models": [{
            "id": "old", "name": "old", "engines": [meas("Ollama", "4", "Raspberry Pi 4B", "2026-06-25",
                                                         "https://lightbrd.com/")]}]}
        (Path(td) / "cpu-1.json").write_text(json.dumps(raw))
        store = {"engines": {}, "models": [m]}
        saved = UT.RAW_DIR
        UT.RAW_DIR = Path(td)
        try:
            UT.ingest_raw_snapshots(store)
        finally:
            UT.RAW_DIR = saved
    UT.sort_models(store["models"], TODAY)
    check("last_seen: re-ingesting an old raw snapshot does not make it trending",
          store["models"][0]["last_seen"] == "2026-06-25", store["models"][0]["last_seen"])


def _readme_for(s):
    md = UT.render_readme(copy.deepcopy(s), V._as_of(s))
    td = Path(tempfile.mkdtemp())
    (td / "README.md").write_text(md)
    return md, td / "README.md"


def test_readme_trend_cell():
    s = json.loads(FIXTURE.read_text())
    md, _ = _readme_for(s)
    hdr = next(ln for ln in md.split("\n") if ln.startswith("| Model | Status"))
    check("readme: 'Trend' column", "| Trend |" in hdr, hdr)
    row = next(ln for ln in md.split("\n") if ln.startswith("| [**Bonsai 2 27B**]"))
    cell = V._split_row(row)[2]
    check("readme: trend cell shows buzz, posts and speed source",
          "buzz " in cell and "5 posts" in cell and "speed +" in cell and "t/s" in cell, cell)
    check("readme: formula explained", "Trend = buzz + speed" in md and "48 GB" in md)


def _ranking_errors(s, path):
    saved = V.README
    V.README = path
    V.FAILURES.clear()
    try:
        V.check_readme_ranking(s)
        return list(V.FAILURES)
    finally:
        V.README = saved
        V.FAILURES.clear()


def test_validator_ranking_accepts_and_rejects():
    s = json.loads(FIXTURE.read_text())
    md, path = _readme_for(s)
    check("validator: generated README passes the ranking check", not _ranking_errors(s, path),
          _ranking_errors(s, path)[:2])
    lines = md.split("\n")
    i = next(k for k, ln in enumerate(lines) if ln.startswith("| [**Bonsai 2 27B**]"))
    lines[i], lines[i + 1] = lines[i + 1], lines[i]
    path.write_text("\n".join(lines))
    check("validator: swapped rows -> FAIL", any("order" in e for e in _ranking_errors(s, path)))
    b = UT.sort_models(copy.deepcopy(s["models"]), V._as_of(s))[0]["engagement"]["trend_score"]
    path.write_text(md.replace(f"**{UT._fmt_num(b)}**<br><sub>buzz", "**99.9**<br><sub>buzz", 1))
    check("validator: wrong displayed trend score -> FAIL",
          any("Trend cell" in e for e in _ranking_errors(s, path)))


def main() -> int:
    print("trend score: breadth-first buzz + consumer speed (issue #59)")
    test_real_store_bonsai_beats_single_post()
    test_breadth_beats_light_single_post()
    test_viral_post_still_wins()
    test_post_buzz_values()
    test_speed_breaks_equal_buzz()
    test_speed_only_while_trending()
    test_datacenter_never_earns_speed()
    test_vram_parsing()
    test_no_duplicate_posts_after_tps_rewrite()
    test_real_posts_persist_placeholders_derived()
    test_last_seen_from_data_not_merge_time()
    test_readme_trend_cell()
    test_validator_ranking_accepts_and_rejects()
    print(f"\nPASSED {_PASS} | FAILED {_FAIL}")
    return 1 if _FAIL else 0


if __name__ == "__main__":
    raise SystemExit(main())
