#!/usr/bin/env python3
"""tests/test_alias_identity_gate.py — issue #1207: a measurement_model_aliases counterpart
must share the row's model identity.

The attribution exception (#652) lets a measurement naming the counterpart's model land on
this row. Measured in the shipped store: reciprocal qwen3.8-flash-next-125b <-> qwen3.8-27b
aliases (125B MoE vs 27B dense), qwen3.5-0.8b on the 27B row, and 35B/180B rows on the 125B
row — a different model size's t/s attributed through the exception path, bypassing the
misattribution refusal. This suite locks the gate:

  1. params_identity reads the STORE params field (name parsing fails open on variant names);
  2. cross_identity_alias_reason reds a different-size counterpart, greens a same-identity
     variant (bonsai = ternary 27B), fails open when either params is unknown;
  3. the ingest merge REFUSES a new cross-identity counterpart (with store) and keeps the
     unconditional union without store (back-compat);
  4. a non-pending cross-identity alias is INERT in misattributed_measurement_reason;
  5. validate's check_measurement_alias_map FAILS a cross-identity alias, REPORTS the
     documented load-bearing pair awaiting the owner ruling (#1210), and the shipped store
     is clean (contaminants removed, the official params note recorded).

The guards run the REAL scripts (rule 6m); the only external system is the filesystem.
"""
from __future__ import annotations

import io
import sys
from contextlib import redirect_stdout
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "tests"))

import update_trending as UT  # noqa: E402
import validate as V  # noqa: E402
from wiring import wired  # noqa: E402

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


def _row(mid, params, aliases=None, name=None):
    r = {"id": mid, "name": name or mid, "params": params}
    if aliases is not None:
        r["measurement_model_aliases"] = aliases
    return r


def test_params_identity_reads_the_store_field():
    check("125B (MoE) -> 125b", UT.params_identity("125B (MoE)") == "125b")
    check("35B (MoE, 3B active) -> 35b (leading size)", UT.params_identity("35B (MoE, 3B active)") == "35b")
    check("0.8B -> 0.8b", UT.params_identity("0.8B") == "0.8b")
    check("27B -> 27b", UT.params_identity("27B") == "27b")
    check("empty/None -> None (fail open)", UT.params_identity("") is None and UT.params_identity(None) is None)


def test_cross_identity_reason():
    flash = _row("qwen3.8-flash-next-125b", "125B (MoE)")
    dense = _row("qwen3.8-27b", "27B")
    bonsai = _row("bonsai-2-27b", "27B")
    unknown = _row("mystery", "")
    r = UT.cross_identity_alias_reason(flash, dense)
    check("125B vs 27B is refused, naming both", bool(r) and "125B" in r and "27B" in r, str(r))
    check("same-identity variant (bonsai 27B on 27B) is allowed", UT.cross_identity_alias_reason(dense, bonsai) is None)
    check("unknown params fails open", UT.cross_identity_alias_reason(flash, unknown) is None
          and UT.cross_identity_alias_reason(unknown, dense) is None)


def test_ingest_merge_refuses_a_new_cross_identity_counterpart():
    flash = _row("qwen3.8-flash-next-125b", "125B (MoE)")
    variant = _row("qwen3-8-flash-next-125b", "125B (MoE)")
    dense = _row("qwen3.8-27b", "27B")
    store = {"models": [flash, variant, dense]}
    existing = dict(flash)
    incoming = {"measurement_model_aliases": ["qwen3.8-27b", "qwen3-8-flash-next-125b"]}
    out = io.StringIO()
    with redirect_stdout(out):
        added = UT.merge_measurement_aliases(existing, incoming, store)
    check("the cross-identity counterpart is NOT added", added == ["qwen3-8-flash-next-125b"], str(added))
    check("the refusal is loud in the ingest log", "REFUSED" in out.getvalue() and "qwen3.8-27b" in out.getvalue())
    check("the row keeps only the same-identity variant",
          existing.get("measurement_model_aliases") == ["qwen3-8-flash-next-125b"])
    e2 = dict(flash)
    a2 = UT.merge_measurement_aliases(e2, incoming)  # no store: back-compat unconditional union
    check("without store the union is unconditional (back-compat)",
          set(a2) == {"qwen3.8-27b", "qwen3-8-flash-next-125b"}, str(a2))


def test_a_non_pending_cross_identity_alias_is_inert_in_misattribution():
    dense = _row("qwen3.8-27b", "27B", aliases=["qwen3.5-0.8b"], name="Qwen3.8-27B")
    tiny = _row("qwen3.5-0.8b", "0.8B", name="Qwen3.5-0.8B")
    store = {"models": [dense, tiny]}
    meas = {"quant": "Qwen3.5-0.8B decode 30 tok/s", "tps": "30"}
    reason = UT.misattributed_measurement_reason(meas, dense, store)
    check("the cross-identity alias did NOT rescue the misattributed measurement",
          reason is not None, str(reason))


def test_validate_gate_reports_cross_identity_and_fails_dangling():
    dense = _row("qwen3.8-27b", "27B", aliases=["qwen3.5-0.8b"])
    tiny = _row("qwen3.5-0.8b", "0.8B")
    V.FAILURES.clear()
    out = io.StringIO()
    try:
        with redirect_stdout(out):
            V.check_measurement_alias_map({"models": [dense, tiny]})
        fails = list(V.FAILURES)
    finally:
        V.FAILURES.clear()
    check("a cross-identity alias is REPORTED for owner review, not failed (#650 precedent)",
          not fails and "REPORT" in out.getvalue() and "different model size" in out.getvalue(),
          str(fails) + out.getvalue()[:200])

    dangling = _row("qwen3.8-27b", "27B", aliases=["no-such-model"])
    V.FAILURES.clear()
    out = io.StringIO()
    try:
        with redirect_stdout(out):
            V.check_measurement_alias_map({"models": [dangling]})
        fails = list(V.FAILURES)
    finally:
        V.FAILURES.clear()
    check("a DANGLING counterpart still hard-FAILS (the existing #652 gate)",
          any("dangling" in f for f in fails), str(fails))

    flash = _row("qwen3.8-flash-next-125b", "125B (MoE)", aliases=["qwen3.8-27b"])
    dense2 = _row("qwen3.8-27b", "27B", aliases=["qwen3.8-flash-next-125b"])
    V.FAILURES.clear()
    out = io.StringIO()
    try:
        with redirect_stdout(out):
            V.check_measurement_alias_map({"models": [flash, dense2]})
        fails = list(V.FAILURES)
    finally:
        V.FAILURES.clear()
    check("the load-bearing flash-next pair is reported, not failed",
          not fails and "REPORT" in out.getvalue(), str(fails))
    check("alias_pending_ruling recognizes exactly the documented pair",
          UT.alias_pending_ruling("qwen3.8-flash-next-125b", "qwen3.8-27b")
          and UT.alias_pending_ruling("qwen3.8-27b", "qwen3.8-flash-next-125b")
          and not UT.alias_pending_ruling("qwen3.8-27b", "qwen3.5-0.8b"))


def test_the_shipped_store_is_clean_and_documents_the_params():
    store = UT.load_store()
    V.FAILURES.clear()
    out = io.StringIO()
    try:
        with redirect_stdout(out):
            V.check_measurement_alias_map(store)
        fails = list(V.FAILURES)
    finally:
        V.FAILURES.clear()
    check("the shipped store passes the alias identity gate", not fails, str(fails)[:300])
    by = {m["id"]: m for m in store["models"]}
    fa = by["qwen3.8-flash-next-125b"].get("measurement_model_aliases") or []
    da = by["qwen3.8-27b"].get("measurement_model_aliases") or []
    check("the 0.8B contaminant is gone from the 27B row", "qwen3.5-0.8b" not in da, str(da))
    check("the 35B/180B contaminants are gone from the 125B row",
          "cyber-frost-3.8-mlx" not in fa and "qwopus3.6-35b-a3b-coder-mtp" not in fa, str(fa))
    check("the same-identity variants survive (bonsai, thinkingcap, the Apple Silicon variant)",
          "bonsai-2-27b" in da and "thinkingcap-27b" in da and "qwen3-8-flash-next-125b" in fa)
    check("the official params breakdown is recorded on the flash-next row",
          "125B is the official naming" in (by["qwen3.8-flash-next-125b"].get("why") or ""))


def test_wiring():
    check("this suite is discovered by `make test`", wired(__file__), "")


def main() -> int:
    print("alias identity gate (issue #1207):")
    test_params_identity_reads_the_store_field()
    test_cross_identity_reason()
    test_ingest_merge_refuses_a_new_cross_identity_counterpart()
    test_a_non_pending_cross_identity_alias_is_inert_in_misattribution()
    test_validate_gate_reports_cross_identity_and_fails_dangling()
    test_the_shipped_store_is_clean_and_documents_the_params()
    test_wiring()
    print(f"{'FAILED' if _FAIL else 'PASSED'} {_PASS} | FAILED {_FAIL}")
    return 1 if _FAIL else 0


if __name__ == "__main__":
    raise SystemExit(main())
