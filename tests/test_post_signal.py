#!/usr/bin/env python3
"""Post-signal + registry-aware backend tests (issue #56).

  - test_registry_backend_parse          'Metal' -> Metal; 'CUDA / CPU / Metal' -> None
  - test_registry_only_engine_classified  new Mac-only engine, blank hardware -> Metal (old: CUDA)
  - test_hardware_still_wins              multi-backend engine on Apple / CPU hardware
  - test_render_and_validator_agree       README puts it in the Metal table; validator passes
  - test_post_signal_coverage             counts real /status/ URLs + engagement
  - test_post_signal_coverage_never_fails coverage is report-only, even at 0%
  - test_placeholder_with_engagement_counts_fails  a count on a placeholder FAILS
  - test_placeholder_without_counts_stays_allowed  a static placeholder row is allowed
  - test_prompts_ask_for_post_url         all 3 search prompts require …/status/<id> + counts

Run:  python3 tests/test_post_signal.py   or   make test
"""
from __future__ import annotations

import copy
import io
import re
import sys
import tempfile
from contextlib import redirect_stdout
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
    "oMLX": {"backend": "Metal", "note": "Mac-only server", "url": "https://github.com/example/omlx"},
    "Strata": {"backend": "CUDA", "note": "n", "url": "https://github.com/Niko1221/Strata"},
}


def store() -> dict:
    def meas(engine, tps, hw, post, **eng):
        return {"engine": engine, "tps": tps, "hardware": hw, "quant": "4-bit", "date": "2026-09-30",
                "source_post": post, **eng}
    return {
        "generated_utc": "2026-10-01T00:00:00Z", "engines": copy.deepcopy(REGISTRY),
        "models": [{
            "id": "m1", "name": "Model One", "full_name": "Model-One", "type": "LLM", "license": "MIT",
            "params": "27B", "hf": "org/m1", "vram_tier": "16GB", "vram_min": "16GB", "backends": ["Metal"],
            "supported_engines": ["oMLX", "llama.cpp"], "formats": [{"name": "m1", "hf": "org/m1"}], "why": "w",
            "last_seen": "2026-09-30",
            "engagement": {"likes": 0, "comments": 0, "views": 0, "last_7d_likes": 0, "seen_posts": []},
            "engines": [
                meas("oMLX", "88", "", "https://lightbrd.com/a/status/1", likes=40, views=900),
                meas("llama.cpp", "61", "RTX 4090", "https://lightbrd.com/"),
                meas("llama.cpp", "22", "Ryzen 9 7950X", "https://lightbrd.com/b"),
            ],
        }],
    }


def test_registry_backend_parse():
    check("registry: single 'Metal' -> Metal", UT.registry_backend("oMLX", REGISTRY) == "Metal")
    check("registry: single 'CUDA' -> CUDA", UT.registry_backend("Strata", REGISTRY) == "CUDA")
    check("registry: multi-backend -> None", UT.registry_backend("llama.cpp", REGISTRY) is None)
    check("registry: unknown engine -> None", UT.registry_backend("nope", REGISTRY) is None)
    check("registry: no registry -> None", UT.registry_backend("oMLX", None) is None)


def test_registry_only_engine_classified():
    e = {"engine": "oMLX", "tps": "88", "hardware": ""}
    check("classify: registry-only Mac engine, blank hardware -> Metal",
          UT.measurement_backend(e, REGISTRY) == "Metal", UT.measurement_backend(e, REGISTRY))
    check("classify: same measurement WITHOUT the registry falls to CUDA (the #56 bug)",
          UT.measurement_backend(e) == "CUDA")


def test_hardware_still_wins():
    check("classify: llama.cpp on Ryzen -> CPU",
          UT.measurement_backend({"engine": "llama.cpp", "hardware": "Ryzen 9 7950X"}, REGISTRY) == "CPU")
    check("classify: llama.cpp on Mac -> Metal",
          UT.measurement_backend({"engine": "llama.cpp", "hardware": "MacBook Pro M4"}, REGISTRY) == "Metal")
    check("classify: llama.cpp on RTX -> CUDA",
          UT.measurement_backend({"engine": "llama.cpp", "hardware": "RTX 4090"}, REGISTRY) == "CUDA")


def test_render_and_validator_agree():
    s = store()
    md = UT.render_readme(copy.deepcopy(s), TODAY)
    metal = md.split("# 🟩", 1)[1].split("\n---", 1)[0]
    cuda = md.split("# 🟦", 1)[1].split("\n---", 1)[0]
    check("render: oMLX figure in the Metal table", "**88**" in metal and "oMLX" in metal, metal[:200])
    check("render: oMLX figure NOT in the CUDA table", "oMLX" not in cuda, cuda[:200])
    td = Path(tempfile.mkdtemp())
    (td / "README.md").write_text(md)
    saved = V.README
    V.README = td / "README.md"
    V.FAILURES.clear()
    try:
        V.check_readme_measurements(s)
        errs = list(V.FAILURES)
    finally:
        V.README = saved
        V.FAILURES.clear()
    check("validator: agrees with the renderer (registry-aware)", not errs, errs[:2])


def test_post_signal_coverage():
    total, real, counted = V.post_signal_coverage(store()["models"])
    check("coverage: 3 measurements", total == 3, total)
    check("coverage: 1 real /status/ URL (placeholder + profile excluded)", real == 1, real)
    check("coverage: 1 with engagement counts", counted == 1, counted)


def test_post_signal_coverage_never_fails():
    """COVERAGE is a warning even at 0% — a low-signal placeholder row is history."""
    s = store()
    for e in s["models"][0]["engines"]:
        e["source_post"] = "https://lightbrd.com/"
        for k in ("likes", "comments", "reshares", "views"):
            e.pop(k, None)
    V.FAILURES.clear()
    saved = V.RAW_DIR
    V.RAW_DIR = Path(tempfile.mkdtemp()) / "none"
    buf = io.StringIO()
    try:
        with redirect_stdout(buf):
            V.check_post_signal(s)
    finally:
        V.RAW_DIR = saved
    out = buf.getvalue()
    check("report: 0% coverage is a WARN line", "WARN: post-signal store: 0/3" in out, out)
    check("report: coverage never adds a failure", not V.FAILURES, V.FAILURES)


def test_placeholder_with_engagement_counts_fails():
    """A count on a placeholder post is FABRICATED attribution (tech-debt #456/#468):
    `check_post_signal` must fail instead of accepting a figure nobody can open."""
    s = store()
    e = s["models"][0]["engines"][1]          # the placeholder row
    e["source_post"] = "https://lightbrd.com/"
    e["likes"] = 2
    V.FAILURES.clear()
    saved = V.RAW_DIR
    V.RAW_DIR = Path(tempfile.mkdtemp()) / "none"
    buf = io.StringIO()
    try:
        with redirect_stdout(buf):
            V.check_post_signal(s)
    finally:
        V.RAW_DIR = saved
    out = buf.getvalue()
    errs = list(V.FAILURES)
    V.FAILURES.clear()
    check("fabricated: a placeholder post with counts FAILS validation",
          "placeholder post" in " ".join(errs) or "placeholder post" in out, (out, errs))
    check("fabricated: the failure names the model and the engine",
          any("Model One" in f and "llama.cpp" in f for f in errs), errs)


def test_placeholder_without_counts_stays_allowed():
    """The issue's carve-out: a low-signal, static placeholder row must NOT fail."""
    s = store()                            # its placeholder row carries no counts
    V.FAILURES.clear()
    saved = V.RAW_DIR
    V.RAW_DIR = Path(tempfile.mkdtemp()) / "none"
    buf = io.StringIO()
    try:
        with redirect_stdout(buf):
            V.check_post_signal(s)
    finally:
        V.RAW_DIR = saved
    check("carve-out: a placeholder with no counts adds no failure", not V.FAILURES, V.FAILURES)


def test_prompts_ask_for_post_url():
    """Issue #638: the search rules live in the skill the legs preload (`data-search`),
    so the post-signal contract is asserted there, at the same strength, and each leg is
    asserted to preload it and to keep no copy in its own recipe."""
    skill = (ROOT / ".hermes" / "skills" / "data-search" / "SKILL.md").read_text()
    flat = " ".join(skill.replace("`", "").split())
    text = (ROOT / "Makefile").read_text()
    check("skill: requires the …/status/<id> post URL", "/status/<id>" in flat, flat[:160])
    check("skill: rejects placeholder/profile URLs",
          "never the bare mirror URL or a profile page" in flat, flat[:200])
    check("skill: per-post counts as integers",
          "likes, comments, reshares and views as integers" in flat, flat[:200])
    for b in UT.SEARCH_LEGS:  # every search leg incl. amd
        recipe = text[text.index(f"_search-{b}:\n"):].split("\n.PHONY", 1)[0]
        check(f"prompt {b}: preloads the skill that carries the post rule",
              "-s data-search,bot-unattended" in recipe, recipe[-160:])
        check(f"prompt {b}: keeps no copy of the post rule",
              "/status/<id>" not in recipe, recipe[-160:])


def main() -> int:
    print("post signal + registry-aware backend (issue #56)")
    test_registry_backend_parse()
    test_registry_only_engine_classified()
    test_hardware_still_wins()
    test_render_and_validator_agree()
    test_post_signal_coverage()
    test_post_signal_coverage_never_fails()
    test_placeholder_with_engagement_counts_fails()
    test_placeholder_without_counts_stays_allowed()
    test_prompts_ask_for_post_url()
    print(f"\nPASSED {_PASS} | FAILED {_FAIL}")
    return 1 if _FAIL else 0


if __name__ == "__main__":
    raise SystemExit(main())
