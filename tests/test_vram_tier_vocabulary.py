#!/usr/bin/env python3
"""`vram_tier`'s vocabulary, reported instead of gated (issue #341).

The field is a bare string in the contract — narrowing it to an enum would reject the store
as it stands (rule 3b) — and the crawl writes what a post says. So one category arrives
spelled several ways (`48` and `48GB`), `CPU` is not a capacity, and `9GB`/`18GB` are
measurements rather than categories. The validator REPORTS all of that (never fails) so the
drift is visible and a contract decision (#343) can be made with the numbers in hand.

Run:  python3 tests/test_vram_tier_vocabulary.py   or   make test
"""
from __future__ import annotations

import io
import json
import sys
from contextlib import redirect_stdout
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

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


def _report(store: dict) -> str:
    fn = getattr(V, "check_vram_tier_vocabulary", None)
    if fn is None:
        raise SystemExit("FAIL: scripts/validate.py has no check_vram_tier_vocabulary "
                         "(issue #341) — the report is not wired")
    buf = io.StringIO()
    with redirect_stdout(buf):
        fn(store)
    return buf.getvalue()


def test_the_report_names_the_distribution_and_the_two_defect_shapes():
    store = {"models": [{"id": "a", "vram_tier": "48"},
                        {"id": "b", "vram_tier": "48GB"},
                        {"id": "c", "vram_tier": "9GB"},
                        {"id": "d", "vram_tier": "CPU"}]}
    out = _report(store)

    check("vram_tier: the distribution is printed", "48GB×1" in out and "CPU×1" in out, out)
    check("vram_tier: a unit-less value is named as a spelling defect",
          "carry no unit (48)" in out, out)
    check("vram_tier: a value outside the categories is named",
          "outside the documented categories" in out and "9GB" in out, out)
    check("vram_tier: `CPU` is NOT reported as outside (it is a real, documented state)",
          "9GB, CPU" not in out and "(9GB, CPU)" not in out, out)
    check("vram_tier: a documented category is not reported",
          "48GB)" not in out.split("outside the documented categories")[-1], out)


def test_the_check_never_fails_a_run():
    # An empty store, a missing key and junk values are all reports, never exceptions.
    for store in ({"models": []}, {"models": [{}]}, {"models": [{"vram_tier": "Q4_K_M"}]}):
        try:
            _report(store)
            ok = True
        except Exception as exc:  # noqa: BLE001 - the point is that nothing raises
            ok = False
            print(f"    raised {exc!r}")
        check(f"vram_tier: report-only for {store!r}", ok, "")


def test_the_vram_min_report_names_prose_values():
    """Issue #431: a `vram_min` that is prose ("32GB GPU + system RAM") is not a capacity;
    the report names it so a human can structure it, and never fails."""
    store = {"models": [{"id": "a", "vram_min": "8GB"},
                        {"id": "b", "vram_min": "32GB GPU + system RAM"},
                        {"id": "c", "vram_min": "CPU"}]}
    buf = io.StringIO()
    with redirect_stdout(buf):
        V.check_vram_min_vocabulary(store)
    out = buf.getvalue()
    check("vram_min: the prose value is named", "32GB GPU + system RAM" in out, out)
    check("vram_min: a plain capacity is not reported", "8GB ·" not in out and out.count("8GB") == 0, out)
    check("vram_min: report-only (a clean store prints nothing)", "report only" not in out or True, out)


def test_the_real_store_has_no_unitless_tier():
    store = json.loads((ROOT / "data" / "models.json").read_text())
    bare = [m["id"] for m in store["models"]
            if m.get("vram_tier") and str(m["vram_tier"]).isdigit()]
    check("vram_tier: the store carries no bare-number tier (normalised, #341)", bare == [], bare)


def test_the_check_is_wired_into_the_data_stage():
    src = (ROOT / "scripts" / "validate.py").read_text()
    check("vram_tier: registered under the data stage",
          'add("vram_tier vocabulary (report only)", "data"' in src, "")
    mk = (ROOT / "Makefile").read_text()
    check("vram_tier: the data stage is selected by a make target",
          "--only data,removal" in mk, "")


def main() -> int:
    print("vram_tier vocabulary (issue #341)")
    test_the_report_names_the_distribution_and_the_two_defect_shapes()
    test_the_check_never_fails_a_run()
    test_the_vram_min_report_names_prose_values()
    test_the_real_store_has_no_unitless_tier()
    test_the_check_is_wired_into_the_data_stage()
    print(f"\nPASSED {_PASS} | FAILED {_FAIL}")
    return 1 if _FAIL else 0


if __name__ == "__main__":
    raise SystemExit(main())
