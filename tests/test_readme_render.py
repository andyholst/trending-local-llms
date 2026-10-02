#!/usr/bin/env python3
"""Ranking + README layout tests (issue #52).

  - test_rank_follows_engagement_not_post_count   one viral post beats 3 silent ones
  - test_existing_rows_rank_from_own_measurements legacy rows (empty seen_posts) still score
  - test_placeholder_urls_do_not_collapse         'https://lightbrd.com/' x2 = 2 posts
  - test_real_post_url_dedupes_across_windows     same /status/<id> twice = 1 post
  - test_bands_and_stale_marking                  trending -> recent -> stale + labels
  - test_peak_uses_max_of_range                   '35.5-43.7' ranks as 43.7
  - test_classifier                                CPU / Metal / CUDA by hardware + engine
  - test_most_loved_best_per_backend              best figure, CPU column, '+N more'
  - test_engine_matrix                             only measured engines; best per backend
  - test_backend_tables                            Peak column sorted; every measurement w/ hardware
  - test_validator_accepts_generated_readme        check_readme_measurements / backend_sort / tables
  - test_validator_catches_misplaced_measurement   CPU figure rendered under CUDA -> FAIL
  - test_readme_generated_is_date_stable          re-render 'as of generated_utc', days later
  - test_score_7d_stays_float_through_ingest       contract type-aware coercion

Run:  python3 tests/test_readme_render.py   or   make test
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


REGISTRY = {
    "llama.cpp": {"backend": "CUDA / CPU / Metal", "note": "n", "url": "https://github.com/ggml-org/llama.cpp"},
    "Ollama": {"backend": "CUDA / CPU / Metal", "note": "n", "url": "https://github.com/ollama/ollama"},
    "MLX": {"backend": "Metal", "note": "n", "url": "https://github.com/ml-explore/mlx"},
    "vLLM": {"backend": "CUDA", "note": "n", "url": "https://github.com/vllm-project/vllm"},
    "SGLang": {"backend": "CUDA", "note": "never measured", "url": "https://github.com/sgl-project/sglang"},
}


def meas(engine, tps, hw, date, post, quant="Q4_K_M", **eng):
    e = {"engine": engine, "tps": tps, "hardware": hw, "quant": quant, "date": date, "source_post": post}
    e.update(eng)
    return e


def model(mid, name, engines, last_seen="2026-09-30", **kw):
    m = {
        "id": mid, "name": name, "full_name": name.replace(" ", "-"), "type": "LLM",
        "license": "Apache 2.0", "params": "8B", "hf": f"org/{mid}", "vram_tier": "8GB",
        "vram_min": "8GB", "backends": ["CUDA"], "supported_engines": sorted({e["engine"] for e in engines}),
        "formats": [{"name": name, "hf": f"org/{mid}"}], "why": "w | with a pipe",
        "engines": engines, "last_seen": last_seen,
        "engagement": {"likes": 0, "comments": 0, "views": 0, "last_7d_likes": 0, "seen_posts": []},
    }
    m.update(kw)
    return m


def store() -> dict:
    return {
        "generated_utc": "2026-10-01T00:00:00Z", "engines": copy.deepcopy(REGISTRY),
        "models": [
            # 3 posts, no engagement -> score 3
            model("quiet", "Quiet Three", [
                meas("llama.cpp", "300", "RTX 5090", "2026-09-30", "https://lightbrd.com/a/status/1"),
                meas("llama.cpp", "280", "RTX 4090", "2026-09-29", "https://lightbrd.com/a/status/2"),
                meas("Ollama", "250", "RTX 3090", "2026-09-28", "https://lightbrd.com/a/status/3"),
            ]),
            # 1 viral post -> score 500 + 2*40 + 3*30 + log10(10001) = 674
            model("viral", "Viral One", [
                meas("llama.cpp", "40", "Ryzen 9 7950X", "2026-09-30", "https://lightbrd.com/b/status/9",
                     quant="Q4_0", likes=500, comments=40, reshares=30, views=10000),
                meas("MLX", "35.5-43.7", "MacBook Pro M4 Max", "2026-09-30", "https://lightbrd.com/b/status/9",
                     quant="4-bit", likes=500, comments=40, reshares=30, views=10000),
                meas("llama.cpp", "120", "RTX 4090", "2026-09-29", "https://lightbrd.com/b/status/10"),
                meas("vLLM", "150", "RTX 4090", "2026-09-29", "https://lightbrd.com/b/status/11"),
            ]),
            # recent band (12 days)
            model("recent", "Recent Mid", [
                meas("Ollama", "60", "RTX 3060", "2026-09-19", "https://lightbrd.com/")], last_seen="2026-09-19"),
            # stale band (60 days)
            model("stale", "Stale Old", [
                meas("llama.cpp", "999", "RTX 5090", "2026-08-01", "https://lightbrd.com/")], last_seen="2026-08-01"),
        ],
    }


def sorted_ids(s):
    return [m["id"] for m in UT.sort_models(s["models"], TODAY)]


def test_rank_follows_engagement_not_post_count():
    s = store()
    order = sorted_ids(s)
    check("rank: viral (1 big post) above quiet (3 silent posts)", order.index("viral") < order.index("quiet"), order)
    v = next(m for m in s["models"] if m["id"] == "viral")["engagement"]
    q = next(m for m in s["models"] if m["id"] == "quiet")["engagement"]
    check("rank: quiet score = 3 (1 per post)", q["score_7d"] == 3.0 and q["posts_7d"] == 3, q)
    check("rank: viral buzz adds engagement on top of its 3 posts, log-dampened",
          v["posts_7d"] < v["buzz_7d"] < v["posts_7d"] + 10, v)
    check("rank: viral's two measurements from ONE post count once (+2 others)", v["posts_7d"] == 3, v)
    check("rank: last_7d_likes == posts_7d (back-compat)", v["last_7d_likes"] == v["posts_7d"], v)


def test_existing_rows_rank_from_own_measurements():
    s = store()
    m = next(m for m in s["models"] if m["id"] == "quiet")
    check("legacy: seen_posts starts empty", m["engagement"]["seen_posts"] == [])
    UT.sort_models(s["models"], TODAY)
    check("legacy: seen_posts rebuilt from the row's own measurements", len(m["engagement"]["seen_posts"]) == 3,
          m["engagement"]["seen_posts"])


def test_placeholder_urls_do_not_collapse():
    s = store()
    s["models"][2]["engines"].append(meas("Ollama", "45", "RTX 3060", "2026-09-19", "https://lightbrd.com/", quant="Q8"))
    UT.sort_models(s["models"], TODAY)
    posts = s["models"][2]["engagement"]["seen_posts"]
    check("placeholder: two measurements behind 'https://lightbrd.com/' stay 2 posts", len(posts) == 2, posts)
    check("placeholder: _is_post_url rejects the bare mirror URL",
          not UT._is_post_url("https://lightbrd.com/") and UT._is_post_url("https://lightbrd.com/u/status/12"))


def test_real_post_url_dedupes_across_windows():
    posts = [{"url": "https://lightbrd.com/u/status/7", "date": "2026-09-28", "likes": 1},
             {"url": "https://lightbrd.com/u/status/7", "date": "2026-09-30", "likes": 5},
             {"url": "https://lightbrd.com/u/status/8", "date": "2026-09-30"}]
    out = UT.dedupe_posts(posts)
    check("dedupe: same /status/<id> across windows -> 1 entry", len(out) == 2, out)
    keep = next(p for p in out if p["url"].endswith("/7"))
    check("dedupe: keeps the newest sighting", keep["date"] == "2026-09-30" and keep["likes"] == 5, keep)


def test_bands_and_stale_marking():
    s = store()
    order = sorted_ids(s)
    check("bands: stale (999 t/s) still sorts last", order[-1] == "stale", order)
    check("bands: recent below trending", order.index("recent") > order.index("quiet"), order)
    md = UT.render_readme(s, TODAY)
    check("bands: stale row labeled with its last-seen date", "💤 stale<br><sub>last seen 2026-08-01</sub>" in md)
    check("bands: trending label present", "🔥 trending" in md)
    check("bands: recent label present", "🕑 recent" in md)


def test_peak_uses_max_of_range():
    check("peak: '35.5-43.7' -> 43.7", UT.peak_tps({"engines": [{"tps": "35.5-43.7"}]}) == 43.7)
    check("peak: '~50' -> 50", UT.peak_tps({"engines": [{"tps": "~50"}]}) == 50.0)
    check("peak: no engines -> 0", UT.peak_tps({"engines": []}) == 0.0)


def test_classifier():
    cases = [
        (meas("llama.cpp", "1", "Ryzen 9 7950X", "d", "u"), "CPU"),
        (meas("llama.cpp", "1", "Raspberry Pi 5", "d", "u"), "CPU"),
        (meas("llama.cpp", "1", "RTX 4090 + CPU offload", "d", "u"), "CUDA"),
        (meas("llama.cpp", "1", "M5 Max (Apple Silicon)", "d", "u"), "Metal"),
        (meas("llama.cpp", "1", "MacBook Pro M4", "d", "u"), "Metal"),
        (meas("MLX", "1", "", "d", "u"), "Metal"),
        (meas("vLLM", "1", "", "d", "u"), "CUDA"),
        (meas("Ollama", "1", "unknown box", "d", "u"), "CUDA"),
    ]
    for e, want in cases:
        got = UT.measurement_backend(e)
        check(f"classify: {e['engine']} on '{e['hardware']}' -> {want}", got == want, got)


def _row(md: str, section_start: str, name: str) -> list[str]:
    lines = md.split("\n")
    i = next(k for k, ln in enumerate(lines) if ln.startswith(section_start))
    for ln in lines[i:]:
        if ln.startswith("|") and f"**{name}**" in V._split_row(ln)[0]:
            return [c.strip() for c in V._split_row(ln)]
    return []


def test_most_loved_best_per_backend():
    s = store()
    md = UT.render_readme(s, TODAY)
    hdr = next(ln for ln in md.split("\n") if ln.startswith("| Model | Status"))
    check("loved: CPU column present (backends are equal)", "CPU t/s (best)" in hdr, hdr)
    check("loved: no '#' rank column (rank = row order)", not hdr.startswith("| #"), hdr)
    v = _row(md, "## ❤️", "Viral One")
    check("loved: CUDA best is vLLM 150 (not the newer 120)", v[3].startswith("**150**") and "vLLM" in v[3], v[3])
    check("loved: CUDA cell notes the other measurement", "+1 more" in v[3], v[3])
    check("loved: Metal best shows range verbatim", v[4].startswith("**35.5-43.7**") and "MLX" in v[4], v[4])
    check("loved: CPU best is the Ryzen measurement", v[5].startswith("**40**") and "Ryzen" in v[5], v[5])
    check("loved: hardware + quant shown with the engine", "RTX 4090 · Q4_K_M" in v[3], v[3])
    q = _row(md, "## ❤️", "Quiet Three")
    check("loved: no Metal/CPU measurement -> '—'", q[4] == "—" and q[5] == "—", q[4:6])
    check("loved: model cell links to HF", "(https://huggingface.co/org/viral)" in v[0], v[0])
    check("loved: pipe in free text escaped", "w \\| with a pipe" in md)


def test_engine_matrix():
    s = store()
    md = UT.render_readme(s, TODAY)
    lines = md.split("\n")
    i = next(k for k, ln in enumerate(lines) if ln.startswith("## 🧭"))
    hdr = next(ln for ln in lines[i:] if ln.startswith("| Model"))
    check("matrix: measured engines are columns", all(e in hdr for e in ("llama.cpp", "Ollama", "MLX", "vLLM")), hdr)
    check("matrix: never-measured engine is not a column", "SGLang" not in hdr, hdr)
    check("matrix: most-measured engine first", V._split_row(hdr)[1].strip().startswith("[llama.cpp]"), hdr)
    v = _row(md, "## 🧭", "Viral One")
    cols = [c.strip() for c in V._split_row(hdr)]
    llama = v[cols.index(next(c for c in cols if c.startswith("[llama.cpp]")))]
    check("matrix: llama.cpp cell has CUDA and CPU best", "🟦 120" in llama and "🟨 40" in llama, llama)


def test_backend_tables():
    s = store()
    md = UT.render_readme(s, TODAY)
    lines = md.split("\n")
    i = next(k for k, ln in enumerate(lines) if ln.startswith("# 🟦"))
    hdr = next(ln for ln in lines[i:] if ln.startswith("| Model"))
    check("backend: numeric Peak t/s column", "Peak t/s" in hdr, hdr)
    q = _row(md, "# 🟦", "Quiet Three")
    check("backend: measurements best-first with hardware + date",
          q[5].startswith("[llama.cpp](https://github.com/ggml-org/llama.cpp) **300** · RTX 5090 · Q4_K_M · 2026-09-30"), q[5])
    cpu = _row(md, "# 🟨", "Viral One")
    check("backend: CPU table holds the CPU measurement", cpu and "**40**" in cpu[5], cpu)
    cuda_v = _row(md, "# 🟦", "Viral One")
    check("backend: CPU figure NOT in the CUDA row", "**40**" not in cuda_v[5], cuda_v[5])


def _validate_rendered(md: str, s: dict) -> list[str]:
    td = Path(tempfile.mkdtemp())
    (td / "README.md").write_text(md)
    saved = V.README
    V.README = td / "README.md"
    V.FAILURES.clear()
    try:
        V.check_readme_measurements(s)
        V.check_backend_sort(s)
        V.check_readme_tables_wellformed(s)
        V.check_readme_has_all_models(s)
        return list(V.FAILURES)
    finally:
        V.README = saved
        V.FAILURES.clear()


def test_validator_accepts_generated_readme():
    s = store()
    md = UT.render_readme(s, TODAY)
    errs = _validate_rendered(md, s)
    check("validator: generated README passes measurement/sort/table/completeness checks", not errs, errs[:3])


def test_validator_catches_misplaced_measurement():
    s = store()
    md = UT.render_readme(s, TODAY)
    # move the Ryzen (CPU) figure into the CUDA table row
    bad = md.replace("| 120 | [vLLM]", "| 150 | [llama.cpp](https://github.com/ggml-org/llama.cpp) **40** · Ryzen<br>[vLLM]")
    lines = bad.split("\n")
    # drop the CPU table row for Viral One
    lines = [ln for ln in lines if not (ln.startswith("| [**Viral One**]") and "Ryzen" in ln and "| 40 |" in ln)]
    errs = _validate_rendered("\n".join(lines), s)
    check("validator: CPU measurement missing from its CPU row -> FAIL",
          any("no row in the CPU table" in e or "missing from its CPU row" in e for e in errs), errs[:3])
    wrong_best = md.replace("**150** t/s<br>[vLLM]", "**120** t/s<br>[vLLM]", 1)
    errs = _validate_rendered(wrong_best, s)
    check("validator: most-loved cell not showing the true best -> FAIL",
          any("should start with '**150**'" in e for e in errs), errs[:3])


def test_readme_generated_is_date_stable():
    s = store()
    UT.sort_models(s["models"], TODAY)
    md = UT.render_readme(copy.deepcopy(s), TODAY)
    td = Path(tempfile.mkdtemp())
    (td / "README.md").write_text(md)
    saved = V.README
    V.README = td / "README.md"
    V.FAILURES.clear()
    try:
        V.check_readme_generated(s)  # wall clock is 'later' than generated_utc
        errs = list(V.FAILURES)
    finally:
        V.README = saved
        V.FAILURES.clear()
    check("generated: re-render as of generated_utc is byte-stable on later days", not errs, errs[:2])


def test_score_7d_stays_float_through_ingest():
    eng = UT.prune_engagement({"likes": "3", "score_7d": 674.4, "posts_7d": 2.0, "bogus": 1}, "t")
    check("coerce: score_7d keeps its decimal", eng.get("score_7d") == 674.4, eng)
    check("coerce: posts_7d int", eng.get("posts_7d") == 2 and isinstance(eng["posts_7d"], int), eng)
    check("coerce: undeclared key pruned", "bogus" not in eng, eng)


def main() -> int:
    print("ranking + README layout (issue #52)")
    test_rank_follows_engagement_not_post_count()
    test_existing_rows_rank_from_own_measurements()
    test_placeholder_urls_do_not_collapse()
    test_real_post_url_dedupes_across_windows()
    test_bands_and_stale_marking()
    test_peak_uses_max_of_range()
    test_classifier()
    test_most_loved_best_per_backend()
    test_engine_matrix()
    test_backend_tables()
    test_validator_accepts_generated_readme()
    test_validator_catches_misplaced_measurement()
    test_readme_generated_is_date_stable()
    test_score_7d_stays_float_through_ingest()
    print(f"\nPASSED {_PASS} | FAILED {_FAIL}")
    return 1 if _FAIL else 0


if __name__ == "__main__":
    raise SystemExit(main())
