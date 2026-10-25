#!/usr/bin/env python3
"""Trending for your card tests (issue #349): "what is TRENDING that fits MY card?"

The headline list ranked every model by ONE global score whose speed term could come
from a card above the reader's — and, measured on the shipped store, from a datacenter
aggregate that named no card at all: Qwen3.8-27B's 28,340 t/s over 512 concurrent
requests on "datacenter GPUs" earned speed +11.5 and headed the list, while the fastest
figure on a card a reader can buy was 500 t/s on an RTX 5090 (issue #349).

What is locked here:

  1. test_a_datacenter_class_never_earns_speed        the 28,340 t/s shape, and a spelled class
  2. test_the_tier_bonus_never_comes_from_a_bigger_card   a tier rewards only its own card
  3. test_a_weights_only_fit_earns_no_bonus           labelled, never a measured fit
  4. test_the_vram_cell_names_the_measured_card       a 5090 number is not a 16 GB laptop's
  5. test_the_section_is_first_and_low_end_first      low end first, above the most-loved list
  6. test_the_validator_catches_a_falsified_tier      the guard, against a mutated README
  7. test_the_shipped_readme_and_store                no fixture-only claim
  8. test_the_check_is_wired_into_the_readme_stage    rule 6d

Run:  python3 tests/test_trending_for_your_card.py   or   make test
"""
from __future__ import annotations

import copy
import json
import re
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
    "SGLang": {"backend": "CUDA", "note": "n", "url": "https://github.com/sgl-project/sglang"},
    "MLX": {"backend": "Metal", "note": "n", "url": "https://github.com/ml-explore/mlx"},
}


def meas(engine, tps, hw, date="2026-09-30", post="https://lightbrd.com/a/status/1", **kw):
    e = {"engine": engine, "tps": tps, "hardware": hw, "quant": "Q4_K_M", "date": date, "source_post": post}
    e.update(kw)
    return e


def seen_posts(mid: str, n: int = 2) -> list[dict]:
    """Real posts IN the 7-day window, so the shipped recompute (which rebuilds
    `buzz_7d` / `posts_7d` from post-granularity data on every sort) yields a score.
    A fixture that hand-sets `buzz_7d` is recomputed to 0, not honoured."""
    return [{"url": f"https://lightbrd.com/{mid}/status/{1000 + i}", "date": "2026-09-29",
             "likes": 10, "comments": 1, "reshares": 0, "views": 1000} for i in range(n)]


def model(mid, name, engines, **kw):
    m = {
        "id": mid, "name": name, "full_name": name, "type": "LLM", "license": "Apache 2.0",
        "params": "8B", "hf": f"org/{mid}", "vram_tier": "8GB", "vram_min": "8GB",
        "backends": ["CUDA"], "supported_engines": sorted({e["engine"] for e in engines}),
        "formats": [{"name": "GGUF", "hf": f"org/{mid}"}], "why": "w", "engines": engines,
        "last_seen": "2026-09-30",
        "engagement": {"likes": 0, "comments": 0, "views": 0, "last_7d_likes": 2,
                       "seen_posts": seen_posts(mid)},
    }
    m.update(kw)
    return m


def store() -> dict:
    return {
        "generated_utc": "2026-10-01T00:00:00Z", "engines": copy.deepcopy(REGISTRY),
        "models": [
            # a 32 GB headline and a 12 GB run: tier-local speed must use its own card
            model("headline", "Headline", [
                meas("llama.cpp", "500", "RTX 5090 32GB", post="https://lightbrd.com/a/status/10"),
                meas("llama.cpp", "50", "RTX 3060 12GB", post="https://lightbrd.com/a/status/11"),
            ]),
            # the measured #349 shape: a datacenter aggregate AND a real consumer run
            model("dc", "Datacenter Aggregate", [
                meas("SGLang", "28340", "datacenter GPUs, 512 concurrent requests",
                     post="https://lightbrd.com/a/status/20"),
                meas("llama.cpp", "90", "RTX 4090 24GB", post="https://lightbrd.com/a/status/21"),
            ], vram_min="16GB"),
            # weights-only at 8 GB: its figure came from a 32 GB card
            model("light", "Light", [
                meas("llama.cpp", "146", "RTX 5090 32GB", weight_gb="5.95GB Q4_K_M",
                     post="https://lightbrd.com/a/status/30"),
            ], vram_min="6GB", weight_gb="5.95GB Q4_K_M"),
            # a Mac is never a card tier
            model("mac", "Mac One", [
                meas("MLX", "237", "16GB Mac (Apple Silicon)", post="https://lightbrd.com/a/status/40"),
            ], vram_min="8GB"),
        ],
    }


def sorted_store() -> dict:
    """The fixture AFTER the real `sort_models()` pass — the shipped recompute rebuilds
    the 7-day score from the posts, so every expectation must read that, not the raw
    dict (a hand-set `buzz_7d` would disagree with the render)."""
    s = store()
    s["models"] = UT.sort_models(s["models"], TODAY)
    return s


def rendered(s: dict) -> str:
    return UT.render_readme(json.loads(json.dumps(s)), TODAY)


def tier_block(text: str, tier: int) -> str:
    sec = V._trending_card_section(text)
    return sec.split(f"### Up to {tier} GB", 1)[-1].split("### ", 1)[0]


# ---- 1. the scope gate ------------------------------------------------------
def test_a_datacenter_class_never_earns_speed():
    """The measured shape: hardware that names a CLASS of machine has no card name and
    no VRAM figure, so `hardware_vram_gb()` returns None and the gate admitted it."""
    s = store()
    m = next(x for x in s["models"] if x["id"] == "dc")
    agg = next(e for e in m["engines"] if e["tps"] == "28340")
    con = next(e for e in m["engines"] if e["tps"] == "90")
    check("scope: the 28,340 t/s aggregate is out of scope", UT.in_scope(agg) is False, UT.in_scope(agg))
    check("scope: the consumer 4090 run stays in scope", UT.in_scope(con) is True)
    check("scope: the best in-scope figure is the 4090 one, never 28,340",
          UT.best_in_scope(m) is not None and UT.best_in_scope(m)["tps"] == "90",
          UT.best_in_scope(m))
    check("scope: speed is computed from the 90 t/s figure",
          UT.speed_bonus(UT._tps_core(UT.best_in_scope(m)["tps"])) == UT.speed_bonus(90))
    for hw in ("Data Center cluster, 8 nodes", "data-centre GPUs", "DATACENTER GPUs, 512 concurrent requests"):
        check(f"scope: {hw!r} is a datacenter class",
              UT.in_scope({"engine": "SGLang", "hardware": hw}) is False, hw)
    # and the board a reader buys is untouched
    check("scope: an RTX 4090 is still in scope",
          UT.in_scope({"engine": "llama.cpp", "hardware": "RTX 4090 24GB"}) is True)
    # the rendered most-loved row must not show the aggregate as its CUDA best
    text = rendered(s)
    loved = text.split("## ❤️ Most loved", 1)[-1]
    row = next(ln for ln in loved.split("\n") if "**Datacenter Aggregate**" in ln)
    check("render: the datacenter aggregate is not the row's best CUDA cell",
          "28340" not in row, row[:200])
    check("render: the consumer figure is", "90" in row)


# ---- 2. the tier-local bonus ------------------------------------------------
def test_the_tier_bonus_never_comes_from_a_bigger_card():
    s = sorted_store()
    models, reg = s["models"], s["engines"]
    m = next(x for x in models if x["id"] == "headline")
    t8, b8, e8 = UT.tier_trend(m, 8, reg)
    t16, b16, e16 = UT.tier_trend(m, 16, reg)
    t32, b32, e32 = UT.tier_trend(m, 32, reg)
    check("tier: no measurement at <= 8 GB means no row at 8 GB",
          UT.tier_trending_rows(models, 8, reg) == [] or
          all(r[1]["id"] != "headline" for r in UT.tier_trending_rows(models, 8, reg)))
    check("tier: 16 GB earns the 12 GB run's bonus", (b16, e16["tps"] if e16 else None) == (UT.speed_bonus(50), "50"),
          (b16, e16))
    check("tier: 32 GB earns the 5090's bonus", (b32, e32["tps"] if e32 else None) == (UT.speed_bonus(500), "500"),
          (b32, e32))
    buzz = m["engagement"]["buzz_7d"]
    check("tier: the buzz is the model's own at every tier", all(
        abs(score - (buzz + bonus)) < 0.05 for score, bonus in ((t8, b8), (t16, b16), (t32, b32))),
        (buzz, t8, b8, t16, b16, t32, b32))
    # the datacenter aggregate never sets a tier's bonus either
    dc = next(x for x in models if x["id"] == "dc")
    _t, b24, e24 = UT.tier_trend(dc, 24, reg)
    check("tier: a datacenter aggregate never sets the tier bonus", e24 is not None and e24["tps"] == "90", e24)


# ---- 3. weights-only is not a measured fit ----------------------------------
def test_a_weights_only_fit_earns_no_bonus():
    s = sorted_store()
    models, reg = s["models"], s["engines"]
    light = next(x for x in models if x["id"] == "light")
    evs = dict((id(e), ev) for e, ev in UT.tier_measurements(light, 8, reg))
    check("weights-only: the 8 GB evidence is weights-only",
          list(evs.values()) == ["weights-only"], evs)
    score, bonus, best = UT.tier_trend(light, 8, reg)
    check("weights-only: it earns no speed bonus", bonus == 0 and best is None, (bonus, best))
    row = next((r for r in UT.tier_trending_rows(models, 8, reg) if r[1]["id"] == "light"), None)
    check("weights-only: it still has a row (labelled, not dropped)", row is not None, row)
    block = tier_block(rendered(s), 8)
    line = next((ln for ln in block.split("\n") if "**Light**" in ln), "")
    check("weights-only: rendered as weights-only, not as a measured fit", "weights-only" in line, line[:200])
    check("weights-only: and it says there is no measured run at this size",
          "no measured run at this size" in line, line[:200])


# ---- 4. the VRAM cell names the card ---------------------------------------
def test_the_vram_cell_names_the_measured_card():
    s = sorted_store()
    text = rendered(s)
    loved = text.split("## ❤️ Most loved", 1)[-1]
    row = next(ln for ln in loved.split("\n") if "**Headline**" in ln)
    vram = V._split_row(row)[-2]
    check("vram: the least VRAM claim stays first", vram.strip().startswith("**8GB**"), vram)
    check("vram: and it names the card the headline figure ran on",
          "headline on RTX 5090 32GB" in vram, vram)


# ---- 5. the section: first, low end first -----------------------------------
def test_the_section_is_first_and_low_end_first():
    s = sorted_store()
    text = rendered(s)
    lines = text.split("\n")
    here = next((i for i, ln in enumerate(lines) if ln.startswith("## 🔥 Trending for your card")), None)
    most = next((i for i, ln in enumerate(lines) if ln.startswith("## ❤️ Most loved")), None)
    check("section: it exists", here is not None)
    check("section: it is ABOVE the most-loved list", here is not None and most is not None and here < most,
          (here, most))
    sec = V._trending_card_section(text)
    heads = [int(x) for x in re.findall(r"^### Up to (\d+) GB", sec, re.M)]
    check("section: one table per tier, low end first", heads == list(UT.CARD_TIERS_GB), heads)
    check("section: the selector links every tier",
          all(f"(#up-to-{t}-gb)" in sec for t in UT.CARD_TIERS_GB))
    check("section: it links the unfiltered view", "(#-most-loved-open-weight-models-on-x" in sec)
    check("section: a Mac is never placed in a card tier",
          all("Mac One" not in tier_block(text, t) for t in UT.CARD_TIERS_GB))


# ---- 6. the validator ------------------------------------------------------
def test_the_validator_catches_a_falsified_tier():
    s = sorted_store()
    text = rendered(s)
    real_readme = V.README

    def run_check(text: str) -> list:
        """Run the REAL check against a README file holding `text` (the validator reads
        `V.README`, so the FILE is what moves — the logic is never replaced, rule 6m)."""
        nonlocal real_readme
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "README.md"
            p.write_text(text)
            V.README = p
            try:
                V.FAILURES.clear()
                V.check_card_trending(s)
                return list(V.FAILURES)
            finally:
                V.README = real_readme

    try:
        check("guard: an untouched README passes the real check", run_check(text) == [],
              run_check(text)[:2])

        # (a) one row dropped from a tier
        block = tier_block(text, 24)
        row = next(ln for ln in block.split("\n") if "**Datacenter Aggregate**" in ln)
        dropped = text.replace(row + "\n", "")
        # (b) a score edited away from the tier-local one
        edited = re.sub(r"(\*\*Headline\*\*[^\n]*?\| )\*\*[\d.]+\*\*", r"\1**99.9**", text, count=1)
        check("guard: the fixtures really mutate", dropped != text and edited != text)

        for label, bad in (("dropped row", dropped), ("edited score", edited)):
            with tempfile.TemporaryDirectory() as d:
                p = Path(d) / "README.md"
                p.write_text(bad)
                V.README = p
                try:
                    V.FAILURES.clear()
                    V.check_card_trending(s)
                    errs = list(V.FAILURES)
                finally:
                    V.README = real_readme
            check(f"guard: check_card_trending FAILS on a {label}", errs != [], errs[:1])
        # a README with no section is a failure, not a silent pass.
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "README.md"
            p.write_text("# Trending\n\nno section here\n")
            V.README = p
            try:
                V.FAILURES.clear()
                V.check_card_trending(s)
                errs = list(V.FAILURES)
            finally:
                V.README = real_readme
        check("guard: no section is no silent pass", any("no '## 🔥 Trending" in e for e in errs), errs[:1])
    finally:
        V.README = real_readme
        V.FAILURES.clear()


# ---- 7. the shipped tree ---------------------------------------------------
def test_the_shipped_readme_and_store():
    """No fixture, no stub: the REAL `data/models.json` and the REAL `README.md`
    through the real functions and the real check (rule 6m)."""
    store = json.loads((ROOT / "data" / "models.json").read_text())
    models, reg = store["models"], store.get("engines", {})
    text = (ROOT / "README.md").read_text()
    sec = V._trending_card_section(text)
    check("real: the shipped README has the trending-for-your-card section", bool(sec))
    for t in UT.CARD_TIERS_GB:
        rows = UT.tier_trending_rows(models, t, reg)
        listed = re.findall(r"\[\*\*(.+?)\*\*\]", tier_block(text, t))
        check(f"real: the {t} GB tier is exactly the tier-local derivation",
              listed == [r[1]["name"] for r in rows], (listed[:3], [r[1]["name"] for r in rows][:3]))
    q = next((m for m in models if m["id"] == "qwen3.8-27b"), None)
    check("real: Qwen3.8-27B's speed bonus is not the 28,340 t/s datacenter aggregate",
          q is None or q["engagement"]["speed_bonus"] == UT.speed_bonus(
              UT._tps_core(UT.best_in_scope(q)["tps"])),
          q and q["engagement"])
    check("real: no best CUDA cell in the most-loved table carries a datacenter figure",
          not any("datacenter" in ln.lower() and "| **" in ln
                  for ln in text.split("## ❤️ Most loved", 1)[-1].split("## ")[0].split("\n")
                  if ln.startswith("| [**")))
    V.FAILURES.clear()
    V.check_card_trending(store)
    check("real: check_card_trending passes on the shipped tree", V.FAILURES == [], list(V.FAILURES)[:2])
    V.FAILURES.clear()


# ---- 8. wiring -------------------------------------------------------------
def test_the_check_is_wired_into_the_readme_stage():
    src = (ROOT / "scripts" / "validate.py").read_text()
    check("wiring: the check is registered under a stage",
          re.search(r'add\("[^"]*trending for your card[^"]*",\s*"readme"', src) is not None)
    mk = (ROOT / "Makefile").read_text()
    check("wiring: a make target selects the readme stage", "--only readme" in mk)


def main() -> int:
    for fn in (
        test_a_datacenter_class_never_earns_speed,
        test_the_tier_bonus_never_comes_from_a_bigger_card,
        test_a_weights_only_fit_earns_no_bonus,
        test_the_vram_cell_names_the_measured_card,
        test_the_section_is_first_and_low_end_first,
        test_the_validator_catches_a_falsified_tier,
        test_the_shipped_readme_and_store,
        test_the_check_is_wired_into_the_readme_stage,
    ):
        print(f"== {fn.__name__} ==")
        fn()
    print(f"\nPASSED {_PASS} | FAILED {_FAIL}")
    return 1 if _FAIL else 0


if __name__ == "__main__":
    raise SystemExit(main())
