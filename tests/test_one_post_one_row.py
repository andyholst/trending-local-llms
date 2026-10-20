#!/usr/bin/env python3
"""One real post is ONE measurement per (engine, date) — issues #389/#387.

`merge_engines` grouped by engine + GPU-size identity + a concordant t/s, so the same post
captured twice — different hardware wording, a different t/s, a re-scan — became several
store rows carrying CONTRADICTORY dimension values into the card-fit and traceability views.
Measured on the store: `qwen3.6-35b-a3b` had four Ollama rows dated 2026-10-16 from one post
(two `context_tokens` 66000, two 67000); `qwen3.8-27b` two llama.cpp rows from one post
(8192 and 65536).

Run:  python3 tests/test_one_post_one_row.py   or   make test
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import update_trending as UT  # noqa: E402

_PASS = 0
_FAIL = 0

POST = "https://lightbrd.com/niklaslenz_ai/status/2111204284453044383"


def check(name, cond, detail: object = ""):
    global _PASS, _FAIL
    if cond:
        _PASS += 1
        print(f"  ok  {name}")
    else:
        _FAIL += 1
        print(f"  FAIL {name}" + (f"  [{detail}]" if detail else ""))


def meas(tps, hardware, context_tokens=None, likes=0, post=POST, engine="Ollama",
         date="2026-10-16", **extra):
    e = {"engine": engine, "tps": tps, "hardware": hardware, "quant": "Q4_K_M",
         "date": date, "source_post": post, "likes": likes}
    if context_tokens is not None:
        e["context_tokens"] = context_tokens
    e.update(extra)
    return e


def test_the_measured_case_collapses_to_one_row():
    # Given the four rows one post produced on the store (hardware wording and t/s differ)
    rows = [meas("41", "RTX 4090 24GB", "66000", likes=10),
            meas("41.5", "RTX 4090", "66000", likes=12),
            meas("43", "RTX 4090 24GB", "67000", likes=25),
            meas("42", "RTX 4090 24GB, Q4", "67000", likes=8)]

    # When  they are collapsed
    out = UT._collapse_one_post(rows)

    # Then  they are ONE row…
    check("collapse: one post -> one row", len(out) == 1, [r["tps"] for r in out])
    # …carrying the HIGHEST t/s, never an average or a lower figure
    check("collapse: the highest t/s is kept", out[0]["tps"] == "43", out[0]["tps"])
    # …with ONE dimension value (the first stated; never contradictory duplicates)
    check("collapse: context_tokens is a single stated value",
          out[0]["context_tokens"] == "66000", out[0].get("context_tokens"))
    # …and counters kept at their max, never shrunk
    check("collapse: counters are raised to the max, never shrunk", out[0]["likes"] == 25,
          out[0].get("likes"))


def test_different_posts_stay_distinct():
    out = UT._collapse_one_post([meas("41", "RTX 4090 24GB", "66000"),
                                 meas("43", "RTX 4090 24GB", "66000",
                                      post="https://lightbrd.com/other/status/99")])
    check("collapse: two posts stay two rows", len(out) == 2, [r["source_post"] for r in out])


def test_different_engines_on_one_post_stay_distinct():
    out = UT._collapse_one_post([meas("41", "RTX 4090 24GB", "66000"),
                                 meas("20", "RTX 4090 24GB", "66000", engine="llama.cpp")])
    check("collapse: one post, two engines -> two measurements", len(out) == 2,
          [r["engine"] for r in out])


def test_a_placeholder_post_is_never_a_key():
    # Two rows that both carry a bare mirror link are NOT evidence of one measurement: keying
    # on "" would collapse every uncited row in the store into one.
    bare = [meas("41", "RTX 4090", post="https://lightbrd.com/"),
            meas("9", "M1 Max", post=""),
            meas("8", "M2 Max", post=None)]
    out = UT._collapse_one_post(bare)
    check("collapse: placeholder posts never group", len(out) == 3, len(out))


def test_a_stated_value_is_never_overwritten():
    cur = [meas("41", "RTX 4090 24GB", "66000", weight_gb="19.5")]
    inc = [meas("43", "RTX 4090 24GB", "67000", weight_gb="21.0", storage_offload="SSD")]
    out = UT._collapse_one_post(cur + inc)
    check("collapse: a stored dimension value is not overwritten",
          out[0]["weight_gb"] == "19.5", out[0].get("weight_gb"))
    check("collapse: an unstated dimension is filled from a sibling",
          out[0].get("storage_offload") == "SSD", out[0].get("storage_offload"))


def test_ingest_path_passes_through_the_collapse():
    # merge_engines is the ingest seam: the collapse must run there, not only when called
    # directly — otherwise the duplicate rows still reach the store.
    merged = UT.merge_engines([], [meas("41", "RTX 4090 24GB", "66000", likes=10),
                                   meas("43", "RTX 4090", "67000", likes=25)])
    check("merge_engines: one post -> one stored measurement", len(merged) == 1,
          [r["tps"] for r in merged])
    check("merge_engines: the kept row is the highest t/s", merged[0]["tps"] in ("43", "43"),
          merged[0]["tps"])


def test_the_store_duplicates_this_targets_would_collapse():
    # Evidence, not a contract: the rows the issue measured are the shape this handles.
    store = json.loads((ROOT / "data" / "models.json").read_text())
    for mid in ("qwen3.6-35b-a3b", "qwen3.8-27b"):
        model = next((m for m in store["models"] if m.get("id") == mid), None)
        if model is None:
            continue
        before = model.get("engines") or []
        after = UT._collapse_one_post(before)
        keys = {}
        for e in before:
            post = UT._real_post(e)
            if post:
                keys.setdefault((e.get("engine"), str(e.get("date")), post), 0)
                keys[(e.get("engine"), str(e.get("date")), post)] += 1
        dupes = {k: n for k, n in keys.items() if n > 1}
        check(f"store: {mid} has no contradictory duplicate left after a collapse",
              len(after) == len(before) - sum(n - 1 for n in dupes.values()),
              (len(before), len(after), dupes))


def main() -> int:
    print("one post, one row (issues #389/#387)")
    missing = [n for n in ("_collapse_one_post", "_real_post") if not hasattr(UT, n)]
    if missing:
        print(f"FAIL: {', '.join(missing)} missing (issue #389) — the collapse is not wired")
        return 1
    test_the_measured_case_collapses_to_one_row()
    test_different_posts_stay_distinct()
    test_different_engines_on_one_post_stay_distinct()
    test_a_placeholder_post_is_never_a_key()
    test_a_stated_value_is_never_overwritten()
    test_ingest_path_passes_through_the_collapse()
    test_the_store_duplicates_this_targets_would_collapse()
    print(f"\nPASSED {_PASS} | FAILED {_FAIL}")
    return 1 if _FAIL else 0


if __name__ == "__main__":
    raise SystemExit(main())
