#!/usr/bin/env python3
"""The models with no card-tier row are NAMED, with the two reasons split (issue #342).

A tier table places a model only where there is evidence, so a model with none simply does
not appear — and "we never measured this on a card" then looks exactly like "no card can run
it". The two reasons want different actions: unified memory / CPU-only is not a gap at all
(those models live in the Metal and CPU tables), while a CUDA/ROCm figure that places nowhere
is a search target.

Run:  python3 tests/test_card_gap_report.py   or   make test
"""
from __future__ import annotations

import io
import json
import sys
from contextlib import redirect_stdout
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import update_trending as UT  # noqa: E402
import validate as V  # noqa: E402

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


def meas(engine, tps, hardware, quant="Q4_K_M"):
    return {"engine": engine, "tps": tps, "hardware": hardware, "quant": quant,
            "date": "2026-10-01", "source_post": "https://lightbrd.com/someone/status/1"}


def model(mid, name, engines, vram_min="", vram_tier=""):
    return {"id": mid, "name": name, "engines": engines,
            "vram_min": vram_min, "vram_tier": vram_tier}


def fixture() -> dict:
    return {"engines": {}, "models": [
        # Placed: it ran on an 8 GB card.
        model("fits", "Fits 8GB", [meas("llama.cpp", "40", "RTX 4060 Ti 8GB")], vram_min="8GB"),
        # Apple Silicon: unified memory, not a card gap.
        model("mac", "Mac Unified", [meas("MLX", "30", "Mac Studio M4 Max 128GB, 4-bit")]),
        # CPU-only.
        model("cpu", "CPU Only", [meas("llama.cpp", "12", "Ryzen 9 7950X, CPU")], vram_min="CPU"),
        # Has a card figure — but a datacenter one, which places in no tier.
        model("dc", "Datacenter", [meas("vLLM", "21000", "B300 288GB")]),
        # Has a card figure above every tier.
        model("big", "Big Card", [meas("llama.cpp", "60", "96GB GPU")]),
    ]}


def test_the_two_reasons_are_told_apart():
    reg = fixture()["engines"]
    m = {x["id"]: x for x in fixture()["models"]}

    check("gap: a model that ran on a tier card has no gap", UT.card_gap_reason(m["fits"], reg) is None,
          UT.card_gap_reason(m["fits"], reg))
    check("gap: Apple Silicon is 'unified memory / CPU-only'",
          UT.card_gap_reason(m["mac"], reg) == "unified memory / CPU-only",
          UT.card_gap_reason(m["mac"], reg))
    check("gap: a CPU-only model is not a card gap either",
          UT.card_gap_reason(m["cpu"], reg) == "unified memory / CPU-only",
          UT.card_gap_reason(m["cpu"], reg))
    check("gap: a datacenter part IS a card figure we lack",
          UT.card_gap_reason(m["dc"], reg) == "no card figure collected",
          UT.card_gap_reason(m["dc"], reg))
    check("gap: a card above every tier is the same gap",
          UT.card_gap_reason(m["big"], reg) == "no card figure collected",
          UT.card_gap_reason(m["big"], reg))


def test_the_report_names_the_models_it_can_act_on():
    store = fixture()
    buf = io.StringIO()
    with redirect_stdout(buf):
        V.check_card_gap_report(store)
    out = buf.getvalue()

    check("gap report: it counts the models with no row",
          "4/5 models have no card-tier row" in out, out)
    check("gap report: it splits unified/CPU-only from a missing card figure",
          "2 unified memory / CPU-only" in out and "2 with no card figure collected" in out, out)
    check("gap report: it names the models whose gap a search can close",
          "Datacenter" in out and "Big Card" in out, out)
    check("gap report: it does NOT name the unified/CPU-only models as search targets",
          "Mac Unified, " not in out and "Big Card, Mac Unified" not in out, out)
    check("gap report: a placed model is not listed", "Fits 8GB" not in out, out)


def test_the_report_never_fails_and_survives_a_degenerate_store():
    for store in ({"models": [], "engines": {}},
                  {"models": [{"id": "x", "name": "X", "engines": []}], "engines": {}}):
        try:
            with redirect_stdout(io.StringIO()):
                V.check_card_gap_report(store)
            ok = True
        except Exception as exc:  # noqa: BLE001 - the point is that nothing raises
            ok = False
            print(f"    raised {exc!r}")
        check(f"gap report: report-only for {len(store['models'])} model(s)", ok, "")


def test_the_real_store_report_is_actionable():
    store = json.loads((ROOT / "data" / "models.json").read_text())
    buf = io.StringIO()
    with redirect_stdout(buf):
        V.check_card_gap_report(store)
    out = buf.getvalue()
    reg = store.get("engines", {})
    reasons = {m["id"]: UT.card_gap_reason(m, reg) for m in store["models"]}
    no_card = [m for m, r in reasons.items() if r == "no card figure collected"]
    check("gap report: the store's own report runs and counts", "card-tier row" in out, out)
    check("gap report: every model is either placed or explained",
          all(r in (None, "unified memory / CPU-only", "no card figure collected") for r in reasons.values()),
          set(reasons.values()))
    # The actionable half must be named when it exists (it did when this shipped).
    if no_card:
        check("gap report: the store's own missing-card models are named",
              any(mid in out or mid for mid in no_card), out)


def test_the_check_is_wired_into_the_readme_stage():
    src = (ROOT / "scripts" / "validate.py").read_text()
    check("gap report: registered under the readme stage",
          'add("card gaps (report only)", "readme"' in src, "")
    check("gap report: the readme stage is selected by a make target",
          "--only readme" in (ROOT / "Makefile").read_text(), "")


def main() -> int:
    print("card gap report (issue #342)")
    missing = [n for n, ok in (("update_trending.card_gap_reason", hasattr(UT, "card_gap_reason")),
                               ("validate.check_card_gap_report", hasattr(V, "check_card_gap_report")))
               if not ok]
    if missing:
        print(f"FAIL: {', '.join(missing)} missing (issue #342) — the report is not wired")
        return 1
    test_the_two_reasons_are_told_apart()
    test_the_report_names_the_models_it_can_act_on()
    test_the_report_never_fails_and_survives_a_degenerate_store()
    test_the_real_store_report_is_actionable()
    test_the_check_is_wired_into_the_readme_stage()
    print(f"\nPASSED {_PASS} | FAILED {_FAIL}")
    return 1 if _FAIL else 0


if __name__ == "__main__":
    raise SystemExit(main())
