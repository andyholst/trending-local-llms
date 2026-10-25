#!/usr/bin/env python3
"""Card-fit view tests (issue #337): "I have N GB of VRAM — what fits?"

The index exists for a card owner, and the low end it prioritises is a GAMING
LAPTOP (8-24 GB). The README used to answer with a per-backend best cell and a
`vram_tier` cell that is a CATEGORY — it disagreed with the model's own
`vram_min` for 20 of 46 models, sat below the smallest card a measurement had run
on for 17, and printed datacenter figures a reader cannot buy (issue #260).

What is locked here:

  1. test_ran_on_is_proved_by_the_run            a 12 GB run proves 12 and 24, never 8
  2. test_a_bigger_card_does_not_qualify_a_small_tier   no guessed fits
  3. test_weights_only_needs_a_known_card        labelled, never sold as a fit
  4. test_a_datacenter_figure_never_places_a_model      the B300 shape, in_scope gate
  5. test_apple_and_cpu_are_not_card_tiers       judged by unified memory / RAM
  6. test_vram_need_prefers_what_the_source_states      least needed, with evidence
  7. test_the_readme_shows_the_card_view         section, anchors, honest empty tier
  8. test_the_validator_catches_a_dropped_row    falsified against a mutated README
  9. test_the_low_end_is_a_gaming_laptop         8-24 GB is the prioritised band

Run:  python3 tests/test_card_fit.py   or   make test
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
    "MLX": {"backend": "Metal", "note": "n", "url": "https://github.com/ml-explore/mlx"},
}


def meas(engine, tps, hw, date="2026-09-30", post="https://lightbrd.com/a/status/1", **kw):
    e = {"engine": engine, "tps": tps, "hardware": hw, "quant": "Q4_K_M", "date": date, "source_post": post}
    e.update(kw)
    return e


def model(mid, name, engines, **kw):
    m = {
        "id": mid, "name": name, "full_name": name, "type": "LLM", "license": "Apache 2.0",
        "params": "8B", "hf": f"org/{mid}", "vram_tier": "8GB", "vram_min": "8GB",
        "backends": ["CUDA"], "supported_engines": sorted({e["engine"] for e in engines}),
        "formats": [{"name": "GGUF", "hf": f"org/{mid}"}], "why": "w", "engines": engines,
        "last_seen": "2026-09-30",
        "engagement": {"likes": 0, "comments": 0, "views": 0, "last_7d_likes": 0, "seen_posts": []},
    }
    m.update(kw)
    return m


def store() -> dict:
    return {
        "generated_utc": "2026-10-01T00:00:00Z", "engines": copy.deepcopy(REGISTRY),
        "models": [
            # ran on a 12 GB card: proves 12 and 24, never 8
            model("twelve", "Twelve", [meas("llama.cpp", "50", "RTX 3060 12GB")], vram_min="8GB"),
            # ran only on a 32 GB card, weights stated at 6 GB -> weights-only at 8
            model("light", "Light", [meas("llama.cpp", "146", "RTX 5090 32GB", weight_gb="5.95GB Q4_K_M")],
                  vram_min="6GB", weight_gb="5.95GB Q4_K_M"),
            # a datacenter figure: never "what fits your card"
            model("cluster", "Cluster", [meas("llama.cpp", "21000", "single NVIDIA B300 GPU (datacenter)")],
                  vram_min="16GB", weight_gb="14.5GB Q4_K_M"),
            # a Mac: judged by unified memory, not by a card tier
            model("mac", "Mac One", [meas("MLX", "237", "16GB Mac (Apple Silicon)")], vram_min="8GB"),
            # only a coarse tier, no vram_min number
            model("coarse", "Coarse", [meas("llama.cpp", "99", "RTX 4090 24GB")], vram_min="", vram_tier="24GB"),
        ],
    }


def rendered(s: dict) -> str:
    return UT.render_readme(json.loads(json.dumps(s)), TODAY)


def test_ran_on_is_proved_by_the_run():
    m = store()["models"][0]
    e = m["engines"][0]
    check("fit: a 12 GB run qualifies 12 GB", UT.fits_tier(m, e, 12) == "ran-on", UT.fits_tier(m, e, 12))
    check("fit: and 24 GB (a bigger card runs it too)", UT.fits_tier(m, e, 24) == "ran-on")
    check("fit: but NOT 8 GB — that was never measured", UT.fits_tier(m, e, 8) is None, UT.fits_tier(m, e, 8))


def test_a_bigger_card_does_not_qualify_a_small_tier():
    """A run on a 32 GB card says nothing about an 8 GB card unless the weight
    footprint is stated — and even then only as 'weights-only'."""
    m = store()["models"][1]
    e = m["engines"][0]
    check("fit: a 32 GB run does not prove 16 GB", UT.fits_tier(m, e, 16) != "ran-on", UT.fits_tier(m, e, 16))
    check("fit: stated 5.95 GB weights make it weights-only at 8", UT.fits_tier(m, e, 8) == "weights-only",
          UT.fits_tier(m, e, 8))
    check("fit: and 32 GB is proved by the run itself", UT.fits_tier(m, e, 32) == "ran-on")


def test_weights_only_needs_a_known_card():
    """A run whose own hardware names no card (a host, a cluster, a bare 'GPU')
    can never claim one of its quants fits a smaller tier."""
    m = model("bare", "Bare", [meas("llama.cpp", "22", "cluster host, experts in system RAM")], weight_gb="9GB Q4")
    e = m["engines"][0]
    check("fit: unknown-card hardware yields no tier placement at all",
          UT.fits_tier(m, e, 24) is None and UT.tier_rows([m], 24, REGISTRY) == [],
          UT.fits_tier(m, e, 24))


def test_a_datacenter_figure_never_places_a_model():
    """The measured LFM2.5 shape: a bare 'B300' was not in the datacenter list, so
    a 21,000 t/s cluster figure passed in_scope() and would have been printed as
    the answer for a gaming laptop (issue #337)."""
    s = store()
    m = next(x for x in s["models"] if x["id"] == "cluster")
    e = m["engines"][0]
    check("scope: a bare 'B300' is recognised as datacenter", UT.in_scope(e) is False, UT.in_scope(e))
    check("scope: a datacenter figure earns no speed bonus",
          UT.speed_bonus(UT._tps_core(e["tps"])) > 0 and UT.best_in_scope(m) is None)
    check("fit: a datacenter measurement places the model in NO card tier",
          UT.tier_rows([m], 24, REGISTRY) == [], UT.tier_rows([m], 24, REGISTRY))
    check("fit: while its 14.5 GB weights alone would have fit 16 GB",
          UT._gb_value(m["weight_gb"]) <= 16)


def test_apple_and_cpu_are_not_card_tiers():
    s = store()
    m = next(x for x in s["models"] if x["id"] == "mac")
    check("fit: a Mac measurement is in no card tier", UT.tier_measurements(m, 24, REGISTRY) == [],
          UT.tier_measurements(m, 24, REGISTRY))
    text = rendered(s)
    check("readme: the Metal table still carries the Mac figure", "16GB Mac (Apple Silicon)" in text)


def test_vram_need_prefers_what_the_source_states():
    s = store()
    twelve = next(x for x in s["models"] if x["id"] == "twelve")
    coarse = next(x for x in s["models"] if x["id"] == "coarse")
    check("need: vram_min is the answer when the source states it", UT.vram_need(twelve) == ("8GB", "declared"),
          UT.vram_need(twelve))
    check("need: the coarse tier is used only as a fallback, and labelled",
          UT.vram_need(coarse) == ("24GB", "tier"), UT.vram_need(coarse))
    # A tier BELOW the stated minimum must never be published as the requirement:
    # the store's Qwen3.5 9B carried vram_tier 16GB / vram_min 32GB.
    lying = model("lying", "Lying", [meas("llama.cpp", "6.73", "32GB laptop, CPU")], vram_min="32GB", vram_tier="16GB")
    check("need: vram_min wins over a smaller vram_tier", UT.vram_need(lying)[0] == "32GB", UT.vram_need(lying))
    check("need: nothing available is reported, never invented",
          UT.vram_need(model("none", "None", [meas("llama.cpp", "5", "cluster")], vram_min="", vram_tier="")) == ("unknown", "unknown"))
    text = rendered(s)
    # …and (issue #349) names the card the headline figure ran on, so a bigger-card
    # number is never read as a fit for the least-VRAM claim beside it.
    check("readme: the most-loved VRAM cell carries the claim's evidence",
          "**8GB**<br><sub>stated by the source" in text)
    check("readme: the most-loved VRAM cell names the measured card",
          re.search(r"\*\*8GB\*\*<br><sub>stated by the source · headline on .+?</sub>", text) is not None)

    # A SPLIT requirement is not one number: publishing its first capacity reads as "fits
    # that card", which an offload requirement does not promise (issue #431).
    split = model("split", "Split", [meas("Strata", "20", "RTX 4090 24GB + 128GB RAM")],
                  vram_min="system RAM holds the expert set (32GB GPU + system RAM)")
    check("need: a GPU+RAM split names both halves",
          UT.vram_need(split) == ("32GB + system RAM", "declared"), UT.vram_need(split))
    ram_only = model("ram", "RAM only", [meas("llama.cpp", "9", "M4 Max")], vram_min="16GB RAM")
    check("need: a plain RAM capacity is not called a split",
          UT.vram_need(ram_only) == ("16GB", "declared"), UT.vram_need(ram_only))
    # …and a NEGATED GPU ("no GPU") is not a GPU half either.
    negated = model("neg", "Negated", [meas("llama.cpp", "9", "Ryzen 9, CPU")],
                    vram_min="8GB RAM (no GPU)")
    check("need: 'no GPU' is a CPU statement, not a split",
          UT.vram_need(negated) == ("8GB", "declared"), UT.vram_need(negated))

    # `vram_min: "CPU"` DECLARES that no VRAM is needed. It used to fall through to the
    # coarse tier (or to "unknown"), so the reader was told the requirement was unstated
    # when the source had stated it plainly (issue #343).
    for marker in ("CPU", "cpu only", "CPU-only"):
        cpu = model("cpu-only", "CPU Only", [meas("llama.cpp", "12", "Ryzen 9 7950X, CPU")],
                    vram_min=marker, vram_tier="16GB")
        check(f"need: vram_min {marker!r} is a declaration, not a gap",
              UT.vram_need(cpu) == ("CPU only", "declared"), UT.vram_need(cpu))
    # …and a sentence that merely MENTIONS system RAM is not that marker: it names a GPU.
    prose = model("moe", "MoE", [meas("Strata", "20", "32GB GPU + system RAM")],
                  vram_min="system RAM holds the expert set (32GB GPU + system RAM)")
    check("need: a prose vram_min is not read as CPU-only",
          UT.vram_need(prose) != ("CPU only", "declared"), UT.vram_need(prose))
    s2 = s
    s2["models"].append(model("cpu-decl", "CPU Decl", [meas("llama.cpp", "9", "Ryzen 9, CPU")],
                              vram_min="CPU", vram_tier="16GB"))
    check("readme: a CPU-only model says so in the VRAM cell, not 'not stated'",
          "**CPU only**" in rendered(s2), "")


def test_the_readme_shows_the_card_view():
    s = store()
    text = rendered(s)
    check("readme: the card section exists", "## 🖥️ Pick your card" in text)
    for t in UT.CARD_TIERS_GB:
        check(f"readme: the anchor index links {t} GB", f"[{t} GB](#{t}-gb)" in text, t)
    check("readme: every tier has a heading", all(f"### {t} GB" in text for t in UT.CARD_TIERS_GB))
    check("readme: a proved fit is laballed 'ran on'", "ran on ≤12 GB" in text)
    check("readme: a weights-only row is labelled, never sold as a fit",
          "weights-only 5.95 GB" in text and "KV cache unknown" in text)
    check("readme: the low end is named as a gaming laptop, 8-24 GB",
          "gaming laptop" in text and "8–24 GB of" in text)
    # The cluster model is in no tier, and every tier it could have polluted lacks it.
    card_only = text.split("## 🖥️")[-1].split("## 🧭")[0]
    for t in UT.CARD_TIERS_GB:
        block = card_only.split(f"### {t} GB")[-1].split("### ")[0]
        check(f"readme: the datacenter model is not in the {t} GB tier", "**Cluster**" not in block, t)
    empty = {"generated_utc": "2026-10-01T00:00:00Z", "engines": copy.deepcopy(REGISTRY), "models": []}
    et = rendered(empty)
    check("readme: an empty tier is reported as a collection gap, not as 'nothing fits'",
          "collection gap" in et)


def test_the_validator_catches_a_dropped_row():
    """The guard must FAIL on a README that silently drops a model from a tier.
    The REAL `check_card_tables` runs against a mutated copy of the rendered
    README (the validator reads `V.README`, so the file is what moves — the logic
    under test is never replaced, rule 6m)."""
    s = store()
    text = rendered(s)
    ok = V._card_section(text)
    check("guard: the section is found in a correct README", ok and "### 12 GB" in ok)
    dropped = text.replace(
        "| [**Twelve**](https://huggingface.co/org/twelve) | 50 | 🟦 CUDA |"
        " [llama.cpp](https://github.com/ggml-org/llama.cpp) **50** · RTX 3060 12GB · Q4_K_M · 2026-09-30"
        " | ran on ≤12 GB |\n", "")
    check("guard: the row was really dropped from the 12 GB block",
          "**Twelve**" not in V._card_section(dropped).split("### 12 GB")[-1].split("### ")[0])
    expected = [row[1]["name"] for row in UT.tier_rows(s["models"], 12, REGISTRY)]
    check("guard: the derivation still expects it", "Twelve" in expected, expected)
    # And the real check rejects the mutated README.
    real_readme = V.README
    with tempfile.TemporaryDirectory() as d:
        p = Path(d) / "README.md"
        p.write_text(dropped)
        V.README = p
        try:
            V.FAILURES.clear()
            V.check_card_tables(s)
            errs = list(V.FAILURES)
        finally:
            V.README = real_readme
    check("guard: check_card_tables FAILS on the mutated README",
          any("12 GB rows differ" in e for e in errs), errs[:2])
    # A README with no section at all is a failure, not a silent pass.
    check("guard: no section is no silent pass", V._card_section("# Trending\n\nno section here\n") == "")
    V.FAILURES.clear()


def test_the_low_end_is_a_gaming_laptop():
    check("band: the low end is 8-24 GB (a gaming laptop)", UT.LOW_END_TIERS_GB == (8, 12, 16, 24),
          UT.LOW_END_TIERS_GB)
    check("band: every low-end tier is offered as a table", set(UT.LOW_END_TIERS_GB) <= set(UT.CARD_TIERS_GB))
    check("band: 32/48 stay available as the workstation step above it",
          (32, 48) == UT.CARD_TIERS_GB[-2:], UT.CARD_TIERS_GB)
    # And the searches must ask for those cards: a tier that is empty because we
    # never looked is the defect this whole change exists to prevent.
    queries = " | ".join(q for qs in UT.SEARCH_GROUPS.values() for q in qs).lower()
    for card in ("3060", "4060", "4070", "8gb vram", "16gb vram", "rx 6600"):
        check(f"queries: the search set names {card}", card in queries)


def test_the_shipped_store_and_readme_answer_the_question():
    """No fixture, no stub: the REAL `data/models.json` and the REAL `README.md`,
    read through the real functions and the real validators (rule 6m). A fixture
    can agree with a broken derivation; the shipped files cannot."""
    store = json.loads((ROOT / "data" / "models.json").read_text())
    models, reg = store["models"], store.get("engines", {})
    text = (ROOT / "README.md").read_text()
    sec = V._card_section(text)
    check("real: the shipped README has the card-fit section", "### 8 GB" in sec and "gaming laptop" in sec,
          sec[:60])
    for t in UT.CARD_TIERS_GB:
        rows = UT.tier_rows(models, t, reg)
        block = sec.split(f"### {t} GB")[-1].split("### ")[0]
        listed = re.findall(r"\[\*\*(.+?)\*\*\]", block)
        check(f"real: the {t} GB tier lists exactly the models the derivation places there",
              listed == [r[1]["name"] for r in rows], (listed[:3], [r[1]["name"] for r in rows][:3]))
    # Every model with card evidence anywhere is in the README, and the
    # most-loved VRAM cell of every model is checked by check_readme_measurements
    # below (46/46), not by a spot-check here.
    # The two real shapes the issue was filed about, locked against live data.
    q = next((m for m in models if m["name"] == "Qwen3.5 9B"), None)
    check("real: Qwen3.5 9B reports the stated minimum, not the smaller tier",
          q is None or UT.vram_need(q) == ("32GB", "declared"), q and UT.vram_need(q))
    lfm = next((m for m in models if m["id"] == "lfm2.5-24b-a2b"), None)
    # A datacenter HEADLINE never places a model: this row's fastest figure is
    # 21,000 t/s on a B300, and that measurement must never be the one a card
    # owner is shown. The refresh also gave it a PROVED RTX 4080 Super 16 GB run,
    # so 16/24 GB are now real evidence (before that run existed the model
    # placed in no tier at all) — and 8 GB still is not.
    rows24 = UT.tier_rows([lfm], 24, reg) if lfm else []
    check("real: a datacenter headline figure never places a card tier",
          lfm is None or all(abs(r[0] - 21000) > 1 and "B300" not in r[2].get("hardware", "")
                             for r in rows24), rows24)
    check("real: the model's proved 16 GB run is what places it",
          lfm is None or (bool(rows24) and rows24[0][3] == "ran-on"
                          and UT.card_memory_gb(rows24[0][2]) == 16), rows24)
    check("real: and its 8 GB tier stays empty (no 8 GB evidence)",
          lfm is None or UT.tier_rows([lfm], 8, reg) == [])
    check("real: and it is still in the README", lfm is None or "LFM2.5-24B-A2B" in text)
    # BOTH evidence branches are exercised by the REAL store, not only by the
    # fixture: a proved run and a stated-weights-only row both exist on disk. If
    # one branch has no real data behind it, that is a collection gap — and the
    # report line above says how much of the store can answer at all.
    check("real: a proved fit exists in the shipped data", "ran on ≤" in sec)
    check("real: a weights-only row exists in the shipped data", "weights-only" in sec)
    # The real validators, on the real tree.
    V.FAILURES.clear()
    V.check_card_tables(store)
    check("real: check_card_tables passes on the shipped tree", V.FAILURES == [], V.FAILURES[:2])
    V.FAILURES.clear()
    V.check_readme_measurements(store)
    check("real: check_readme_measurements passes on the shipped tree", V.FAILURES == [], V.FAILURES[:2])


def test_the_store_holds_what_the_trending_list_needs():
    """The trending list is only real if the STORE carries what it shows: an
    engagement window, a figure per engine with its hardware, and a least-VRAM
    claim. This asserts the shipped store's own coverage, so a silent degrade to
    "not stated" everywhere is visible instead of plausible."""
    store = json.loads((ROOT / "data" / "models.json").read_text())
    models = store["models"]
    check("store: every model has an engagement object with seen_posts",
          all(isinstance(m.get("engagement"), dict) and "seen_posts" in m["engagement"] for m in models))
    check("store: every measurement carries engine + tps + date + source_post",
          all(e.get("engine") and e.get("tps") and e.get("date") and e.get("source_post")
              for m in models for e in m["engines"]))
    check("store: every measurement names the hardware or the quant it ran",
          all((e.get("hardware") or e.get("quant")) for m in models for e in m["engines"]))
    answered = [m for m in models if UT.vram_need(m)[0] != "unknown"]
    check("store: nearly every model states the least VRAM it needs",
          len(answered) >= len(models) - 3, f"{len(answered)}/{len(models)}")
    reg = store.get("engines", {})
    low_end = [(m["name"], t) for m in models for t in UT.LOW_END_TIERS_GB if UT.tier_measurements(m, t, reg)]
    check("store: the gaming-laptop band has real evidence (a tier is not silently empty)",
          len(low_end) > 0, "no low-end evidence at all")


def main() -> int:
    print("card-fit: what fits YOUR card (issue #337)")
    for fn in (
        test_ran_on_is_proved_by_the_run,
        test_a_bigger_card_does_not_qualify_a_small_tier,
        test_weights_only_needs_a_known_card,
        test_a_datacenter_figure_never_places_a_model,
        test_apple_and_cpu_are_not_card_tiers,
        test_vram_need_prefers_what_the_source_states,
        test_the_readme_shows_the_card_view,
        test_the_validator_catches_a_dropped_row,
        test_the_low_end_is_a_gaming_laptop,
        test_the_shipped_store_and_readme_answer_the_question,
        test_the_store_holds_what_the_trending_list_needs,
    ):
        print(f"-- {fn.__name__}")
        fn()
    print(f"\n{_PASS} passed, {_FAIL} failed")
    return 1 if _FAIL else 0


if __name__ == "__main__":
    raise SystemExit(main())
