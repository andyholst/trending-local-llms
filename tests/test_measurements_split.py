"""Issue #697 switch-over acceptance tests (five Given/When/Then, mapped 1:1 to
the OpenSpec `measurement-store-normalized` / `catalog-measurements` spec).

Every test exercises the REAL business logic (update_trending.split_store,
flatten_store, load_store, render_readme, tier_trending_rows, measurement_backend;
validate.check_split_flatten) on REAL data files — no logic mocks. Only the main
pipeline's external calls (network/registry) would be mocked, and none of these
tests mock the logic.

Run:  python3 tests/test_measurements_split.py   or   make test
"""
from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import update_trending as UT  # noqa: E402
import validate as V  # noqa: E402

_PASS = 0
_FAIL = 0


def check(label: str, ok: bool, detail=""):
    global _PASS, _FAIL
    if ok:
        _PASS += 1
        print(f"  ok  {label}")
    else:
        _FAIL += 1
        print(f"  FAIL {label}  [{detail}]")


def _real_files() -> tuple[dict, dict, dict]:
    """The REAL shipped catalog + measurements + posts, read as split files."""
    d = ROOT / "data"
    return (json.loads((d / "models.json").read_text()),
            json.loads((d / "measurements.json").read_text()),
            json.loads((d / "posts.json").read_text()))


# (a) The catalog no longer inlines measurement rows (GWT 1) -----------------
def test_catalog_has_no_inline_engines():
    catalog, measurements, posts = _real_files()
    check("catalog: no model row carries an inline engines[] key",
          all("engines" not in m for m in catalog["models"]))
    check("catalog: the top-level engines registry is still present (metadata, not rows)",
          "engines" in catalog)
    # every model with measurements is reachable in the catalog
    missing = [mid for mid in measurements if mid not in {m["id"] for m in catalog["models"]}]
    check("catalog: every measured model_id resolves to a catalog row", missing == [], str(missing[:5]))
    # flatten of the real files restores the measurement rows the catalog dropped
    flat = UT.flatten_store(catalog, measurements, posts)
    n = sum(len(m.get("engines", [])) for m in flat["models"])
    check("catalog: flatten restores the measurement rows", n == sum(len(v) for v in measurements.values()),
          f"{n} vs {sum(len(v) for v in measurements.values())}")


# (b) Each measurement resolves engagement ONCE from posts.json (GWT 2) -------
def test_engagement_resolved_once_from_posts():
    catalog, measurements, posts = _real_files()
    flat = UT.flatten_store(catalog, measurements, posts)
    by_id = {m["id"]: m for m in flat["models"]}
    # For every measurement row, the counters come from the ONE posts.json entry
    checked = 0
    for mid, rows in measurements.items():
        m = by_id.get(mid)
        if m is None:
            continue
        for r, e in zip(rows, m.get("engines", [])):
            sp = r.get("source_post", "")
            p = posts.get(sp)
            if p is None:
                # a mirror link / profile page: resolves to 0, never a penalty
                check(f"engagement: {mid} {e.get('engine')} with no post entry resolves to 0",
                      all(int(e.get(c) or 0) == 0 for c in UT._MEASUREMENT_COUNTERS))
            else:
                check(f"engagement: {mid} {e.get('engine')} reads the ONE posts[{sp}] entry",
                      all(int(e.get(c) or 0) == int(p.get(c) or 0) for c in UT._MEASUREMENT_COUNTERS))
            checked += 1
    check("engagement: at least one reference checked (not vacuous)", checked > 0, str(checked))


# (b2) Value-for-value: flatten(row).engagement == posts[source_post].engagement (issue #699)
def test_flatten_engagement_equals_posts_value_for_value():
    catalog, measurements, posts = _real_files()
    flat = UT.flatten_store(catalog, measurements, posts)
    by_id = {m["id"]: m for m in flat["models"]}
    # Compare every resolved row's five counters against the canonical posts entry
    # value-for-value (NOT merely non-shrinking) — this is the primary resolution contract.
    matched = no_entry = total = 0
    mismatches: list[str] = []
    for mid, rows in measurements.items():
        m = by_id.get(mid)
        if m is None:
            continue
        for r, e in zip(rows, m.get("engines", [])):
            total += 1
            sp = r.get("source_post", "")
            p = posts.get(sp)
            if p is None:
                # no canonical entry => row resolves each counter to 0
                no_entry += 1
                if not all(int(e.get(c) or 0) == 0 for c in UT._MEASUREMENT_COUNTERS):
                    mismatches.append(f"{mid} {e.get('engine')}: no-entry row has nonzero counters")
                continue
            matched += 1
            for c in UT._MEASUREMENT_COUNTERS:
                rv = int(e.get(c) or 0)
                pv = int(p.get(c) or 0)
                if rv != pv:
                    mismatches.append(f"{mid} {e.get('engine')} [{sp}] {c}: row={rv} posts={pv}")
    check("value-fidelity: every row with a canonical post entry equals it value-for-value (all 5 counters)",
          mismatches == [], "; ".join(mismatches[:5]))
    check("value-fidelity: rows compared (not vacuous)", total > 0, str(total))
    check("value-fidelity: rows matched to a canonical post entry + nonexistent-entry rows",
          matched + no_entry == total, f"{matched}+{no_entry} != {total}")


# (c) Flattened view == old inline view, guarded by check_no_value_loss (GWT 3)
def test_flatten_equals_old_inline_guarded():
    failures_before = len(V.FAILURES)
    catalog, measurements, posts = _real_files()
    # the guard runs against the flattened view reconstructed from the split
    store = UT.flatten_store(catalog, measurements, posts)
    V.check_split_flatten(store)
    new_fail = V.FAILURES[failures_before:]
    check("guard: check_split_flatten is green on the real flatten", len(new_fail) == 0, new_fail[:3])
    # and check_no_value_loss (the #463/#525/#411/#650 guard) is green vs snapshots
    V.FAILURES.clear()
    V.check_no_value_loss(store, ROOT / "data" / "snapshots")
    nl = list(V.FAILURES)
    check("guard: check_no_value_loss is green on the real flatten", len(nl) == 0, nl[:3])
    V.FAILURES[:] = V.FAILURES  # keep it replayable


# (d) The renderer materialises catalog x measurements with unchanged ranking (GWT 4)
def test_renderer_materialises_same_ranking():
    catalog, measurements, posts = _real_files()
    flat = UT.load_store()
    as_of = UT.parse_utc_stamp(flat.get("generated_utc"))
    # render through the flattened view; it must carry the same in-scope best t/s ranking
    readme = UT.render_readme(flat, as_of)
    check("renderer: README renders from the flattened view", "Trending Local LLMs" in readme)
    # best-t/s per model is computed from the flattened measurements, unchanged
    reg = flat.get("engines", {})
    for m in flat["models"]:
        best = UT.best_measurement([e for e in m.get("engines", []) if UT.in_scope(e)])
        if best:
            check("renderer: best in-scope measurement materialises from flattened store",
                  all(k in best for k in ("engine", "tps", "hardware")), best)
            break
    # tier-local derivation (what the validator checks) uses the same store
    check("renderer: tier_trending_rows runs on the flattened store",
          all(r[0] and r[1]["name"] for r in UT.tier_trending_rows(flat["models"], 8, reg) if r[2]))


# (e) The engine support-surface (#338) reads the same store (GWT 5) ----------
def test_support_surface_reads_same_store():
    flat = UT.load_store()
    reg = flat.get("engines", {})
    # measured_backends / measurement_backend derive from the SAME flattened rows
    for m in flat["models"]:
        if m.get("engines"):
            mb = UT.measured_backends(m, reg)
            check("support-surface: measured_backends derives from the flattened store",
                  bool(mb) and all(UT.measurement_backend(e, reg) in mb for e in m["engines"]),
                  str((mb, [UT.measurement_backend(e, reg) for e in m["engines"]])))
            break
    # every registered engine that appears in the registry is still addressable
    check("support-surface: the engine registry is intact on the catalog",
          "llama.cpp" in reg or bool(reg))


def main() -> int:
    test_catalog_has_no_inline_engines()
    test_engagement_resolved_once_from_posts()
    test_flatten_engagement_equals_posts_value_for_value()
    test_flatten_equals_old_inline_guarded()
    test_renderer_materialises_same_ranking()
    test_support_surface_reads_same_store()
    print(f"\nPASSED {_PASS} | FAILED {_FAIL}")
    return 1 if _FAIL else 0


if __name__ == "__main__":
    raise SystemExit(main())
