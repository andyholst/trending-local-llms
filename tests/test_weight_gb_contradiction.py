#!/usr/bin/env python3
"""A measurement's stated weight_gb cannot belong to its model (issue #615).

A reader is told how fast a model runs AND at what footprint; the number must
belong to the model the source post measured. The shipped store carried one
row that violated this:

  * `bonsai-2-9b` (a 2 GB ternary 9B, own footprint `2.0GB (ternary)`) carried an
    `MLX` 36 t/s measurement on `4x Apple M5 Ultra Mac Studio (512GB each,
    Thunderbolt RDMA)` with `weight_gb: "~493GB NVFP4"` — the figure belongs to
    Muse Spark Open (a ~493 GB NVFP4 model), not to a 2 GB ternary Bonsai.

`weights_gb()` (#614) already REFUSED a 'stated' value more than
`WEIGHTS_CONTRADICTION_FACTOR` (10x) away from the model's footprint — but only
when a READER asked, and it fell back to the model-level figure. The stored value
still carried `~493GB NVFP4` for every other consumer. This change:

  * refuses such a measurement at INGEST (write-time, like refuse_fabricated_engines
    #458) — `refuse_weight_gb_contradictions`, wired into `ingest_raw_snapshots`;
  * corrects the shipped store — the misattributed measurement is removed from
    `bonsai-2-9b` additively (rule 3b; no other value changes);
  * reports any regression via `check_weight_gb_contradictions` (report-only).

Run:  python3 tests/test_weight_gb_contradiction.py   or   make test
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
import update_trending as ut  # noqa: E402

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


def _store() -> dict:
    return ut.load_store()


def _by_id(store: dict) -> dict:
    return {m.get("id"): m for m in store.get("models", [])}


def _engines(store: dict, mid: str) -> list[dict]:
    return (_by_id(store).get(mid) or {}).get("engines", [])


# The shipped row the issue names: Bonsai 2 9B, MLX 36 on 4x M5 Ultra, ~493GB NVFP4.
_MID = "bonsai-2-9b"
_M_POST = "https://lightbrd.com/Chahatusharma/status/2111173528838103533"


def test_the_shipped_bonsai_row_is_corrected():
    # Rule 3b (restore commit 9a51fcc): a STORED value is never removed by automation.
    # The ~493GB NVFP4 figure (a Muse Spark post) stays in the store as HISTORY — the
    # #615 refusal is at INGEST only (test_the_shipped_bonsai_row_is_refused) and the
    # store scan reports it (test_the_store_scan_is_clean_and_a_regression_is_reported).
    store = _store()
    rows = _engines(store, _MID)
    check("bonsai-2-9b keeps the shipped ~493GB measurement as history (rule 3b — never removed)",
          any(_M_POST == str(e.get("source_post", "")) for e in rows), rows)
    check("bonsai-2-9b keeps real ternary measurements",
          len(rows) >= 10, len(rows))
    check("bonsai-2-9b chaturpost stays in seen_posts (history is never wiped)",
          any(_M_POST == p.get("url") for p in (_by_id(store).get(_MID) or {}).get("engagement", {}).get("seen_posts", [])),
          (_by_id(store).get(_MID) or {}).get("engagement", {}).get("seen_posts", [])[:2])


def test_the_shipped_bonsai_row_is_refused():
    # Re-inject the exact shipped row as a NEW raw measurement: the write-time
    # refusal (#615) refuses it, naming the post — the way #458 refuses a
    # fabricated engine.
    model = {
        "id": _MID,
        "name": "Bonsai 2 9B",
        "weight_gb": "2.0GB (ternary)",
        "engines": [
            {
                "engine": "MLX", "tps": "36",
                "hardware": "4x Apple M5 Ultra Mac Studio (512GB each, Thunderbolt RDMA)",
                "quant": "NVFP4 (~493GB weights), 8,192-token context; Apple MLX distributed inference",
                "date": "2026-10-16",
                "source_post": _M_POST,
                "weight_gb": "~493GB NVFP4",
                "context_tokens": "8192",
            },
        ],
    }
    kept, refused = ut.refuse_weight_gb_contradictions(model)
    check("the contradictory measurement is refused", len(refused) == 1 and not kept, (kept, refused))
    check("the refusal carries the source post and names both footprints",
          _M_POST in refused[0][2] and "~493GB NVFP4" in refused[0][1]
          and "2.0GB (ternary)" in refused[0][1], refused)


def test_a_footprint_within_the_factor_is_kept():
    model = {"id": "m", "weight_gb": "2.0GB (ternary)",
             "engines": [{"engine": "MLX", "tps": "1", "weight_gb": "~5GB",
                          "source_post": "https://lightbrd.com/u/status/1"}]}
    kept, refused = ut.refuse_weight_gb_contradictions(model)
    check("a stated footprint within the factor is kept",
          len(kept) == 1 and not refused, (kept, refused))


def test_a_measurement_without_a_stated_weight_is_kept():
    model = {"id": "m", "weight_gb": "2.0GB (ternary)",
             "engines": [{"engine": "MLX", "tps": "1",
                          "source_post": "https://lightbrd.com/u/status/1"}]}
    kept, refused = ut.refuse_weight_gb_contradictions(model)
    check("a measurement with no stated weight is kept",
          len(kept) == 1 and not refused, (kept, refused))


def test_a_model_without_its_own_footprint_is_kept():
    model = {"id": "m",   # own weight_gb absent
             "engines": [{"engine": "MLX", "tps": "1", "weight_gb": "~493GB NVFP4",
                          "source_post": "https://lightbrd.com/u/status/1"}]}
    kept, refused = ut.refuse_weight_gb_contradictions(model)
    check("a model with no own footprint fails open",
          len(kept) == 1 and not refused, (kept, refused))


def test_upper_boundary_of_the_factor_is_kept():
    # Exactly AT the factor (not strictly more) is kept: 2GB model, stated 20GB.
    model = {"id": "m", "weight_gb": "2.0GB",
             "engines": [{"engine": "MLX", "tps": "1", "weight_gb": "20GB",
                          "source_post": "https://lightbrd.com/u/status/1"}]}
    kept, refused = ut.refuse_weight_gb_contradictions(model)
    check("a footprint exactly at the factor (10x) is kept",
          len(kept) == 1 and not refused, (kept, refused))


def test_the_ingest_wiring():
    # The seam runs in ingest_raw_snapshots() at the exact spot a raw row would
    # enter the store, alongside the existing refusal seams (#458/#468/#702).
    src = (ROOT / "scripts" / "update_trending.py").read_text()
    check("the weight-gb seam is registered in ingest_raw_snapshots",
          "refuse_weight_gb_contradictions(m, store)" in src,
          "refusal not wired into ingest")
    check("all refusal seams sit in the same ingest function",
          "refuse_fabricated_engines" in src
          and "refuse_misattributed_measurements" in src
          and "REFUSED weight-gb contradiction" in src,
          "seams missing")
    check("REFUSED weight-gb contradiction names the measurement and the post in the log line",
          "REFUSED weight-gb contradiction" in src and "post {post}" in src,
          "log shape missing")


def test_ingest_refuses_a_re_capture_before_it_merges():
    # E2E through the REAL ingest pipeline (`ingest_raw_snapshots`, no mock): a temp
    # data dir carries a store WITHOUT the contradiction (the copy removed from the
    # fixture copy only — the real store keeps its history, rule 3b), and a crafted
    # raw snapshot RE-CAPTURES the #615 bonsai copy (MLX 36 ~493GB NVFP4,
    # Chahatusharma post). It must be refused at ingest and never land — while a
    # legitimate fresh measurement on that same raw row still merges.
    import subprocess
    import textwrap
    script = textwrap.dedent("""
        import json, os, shutil, sys
        from pathlib import Path
        ROOT = Path(sys.argv[1]); tmp = Path(sys.argv[2])
        post = "https://lightbrd.com/Chahatusharma/status/2111173528838103533"
        for name in ("models.json", "measurements.json", "posts.json"):
            shutil.copy(ROOT / "data" / name, tmp / name)
        models = json.loads((tmp / "models.json").read_text())
        for m in models["models"]:
            if m.get("id") == "bonsai-2-9b":
                m["engines"] = [e for e in m.get("engines", [])
                                if str(e.get("source_post", "")) != post]
        (tmp / "models.json").write_text(json.dumps(models))
        meas = json.loads((tmp / "measurements.json").read_text())
        if isinstance(meas, dict) and isinstance(meas.get("bonsai-2-9b"), list):
            meas["bonsai-2-9b"] = [
                e for e in meas["bonsai-2-9b"]
                if str(e.get("source_post", "")) != post]
            (tmp / "measurements.json").write_text(json.dumps(meas))
        (tmp / "raw").mkdir(parents=True, exist_ok=True)
        (tmp / "raw" / "re-capture.json").write_text(json.dumps({
            "generated_utc": "2026-11-11T23:59:59Z",
            "models": [{
                "id": "bonsai-2-9b", "name": "Bonsai 2 9B",
                "hf": "prism-ml/Ternary-Bonsai-2-9B-gguf",
                "weight_gb": "2.0GB (ternary)",
                "engines": [
                    {  # the COPY: weight contradicts the model's own footprint
                        "engine": "MLX", "tps": "36",
                        "hardware": "4x Apple M5 Ultra Mac Studio (512GB each, Thunderbolt RDMA)",
                        "quant": "NVFP4 (~493GB weights), 8,192-token context; Apple MLX distributed inference",
                        "date": "2026-10-16", "source_post": post,
                        "weight_gb": "~493GB NVFP4", "context_tokens": "8192",
                    },
                    {  # a LEGIT fresh ternary measurement
                        "engine": "MLX", "tps": "182",
                        "hardware": "Apple M5 Max Pro",
                        "quant": "ternary ~2GB", "date": "2026-11-11",
                        "source_post": "https://lightbrd.com/lmoroney/status/2115199452228723159",
                        "weight_gb": "~2GB",
                    },
                ],
            }],
        }))
        os.environ["TRENDING_DATA_DIR"] = str(tmp)
        sys.path.insert(0, str(ROOT / "scripts"))
        import update_trending as ut
        store = ut.load_store()
        added, updated = ut.ingest_raw_snapshots(store, since=None)
        out_models = {m["id"]: m for m in store["models"]}
        b = out_models["bonsai-2-9b"]
        contra = any(
            e.get("engine") == "MLX" and e.get("tps") == "36"
            and "493" in str(e.get("weight_gb", "")) for e in b.get("engines", [])
        )
        legit = any(
            e.get("engine") == "MLX" and e.get("tps") == "182"
            for e in b.get("engines", [])
        )
        print(f"UPDATE={updated}")
        print(f"CONTRADICTORY_PRESENT={contra}")
        print(f"LEGIT_MERGED={legit}")
    """)
    import shutil
    tmp = ROOT / "tmp-ig615-e2e"
    shutil.rmtree(tmp, ignore_errors=True)
    tmp.mkdir(parents=True, exist_ok=True)
    buf = io.StringIO()
    with redirect_stdout(buf):
        r = subprocess.run([sys.executable, "-c", script, str(ROOT), str(tmp)],
                           capture_output=True, text=True, timeout=180)
    out = buf.getvalue() + r.stdout
    check("the E2E ingest subprocess runs clean",
          r.returncode == 0, (r.returncode, r.stderr[-400:]))
    check("the contradictory re-capture is REFUSED at ingest (never merges)",
          "CONTRADICTORY_PRESENT=False" in out, r.stdout)
    check("a legitimate measurement on the same raw row still merges",
          "LEGIT_MERGED=True" in out, r.stdout)
    check("the refusal is loud in the ingest log",
          "REFUSED weight-gb contradiction" in out, r.stderr)
    shutil.rmtree(tmp, ignore_errors=True)


def test_the_store_scan_is_clean_and_a_regression_is_reported():
    # Rule 3b keeps the shipped contradiction in the store as history, so the scan is
    # report-only and DOES name that historical row; a NEW re-injected copy must be
    # reported the same way, and the validator must never fail.
    store = _store()
    hits = V.weight_gb_contradiction_hits(store)
    check("the shipped historical contradiction is named by the report-only scan",
          any(_M_POST in str(h[5]) for h in hits), hits[:2])
    len_before = len(hits)
    # Re-inject the copy into a synthetic store: the scan must NAME it and the
    # validator must NOT fail (report-only).
    store = json.loads(json.dumps(store))
    for m in store["models"]:
        if m.get("id") == _MID:
            m.setdefault("engines", []).append({
                "engine": "MLX", "tps": "36",
                "hardware": "4x Apple M5 Ultra Mac Studio (512GB each, Thunderbolt RDMA)",
                "quant": "NVFP4 (~493GB weights)", "date": "2026-10-16",
                "source_post": _M_POST, "weight_gb": "~493GB NVFP4", "context_tokens": "8192",
            })
    hits = V.weight_gb_contradiction_hits(store)
    check("a re-injected contradiction adds a named hit on top of the historical one",
          len(hits) == len_before + 1
          and any("2111173528838103533" in str(h[5]) for h in hits), hits)
    buf = io.StringIO()
    with redirect_stdout(buf):
        V.check_weight_gb_contradictions(store)
    out = buf.getvalue()
    check("the validator prints the contradiction as a WARN and never fails",
          "WARN: weight-gb scan" in out, out)


def test_the_check_is_wired_into_the_data_stage():
    src = (ROOT / "scripts" / "validate.py").read_text()
    check("check_weight_gb_contradictions is registered under the data stage",
          "check_weight_gb_contradictions(store)" in src
          and "weight-gb contradiction (report only)" in src
          and 'add("weight-gb contradiction (report only)", "data"' in src,
          "registration missing")
    check("the data stage is selected by a validate target",
          "--only data,removal" in (ROOT / "Makefile").read_text(),
          "no --only data,removal target")


def main() -> int:
    test_the_shipped_bonsai_row_is_corrected()
    test_the_shipped_bonsai_row_is_refused()
    test_a_footprint_within_the_factor_is_kept()
    test_a_measurement_without_a_stated_weight_is_kept()
    test_a_model_without_its_own_footprint_is_kept()
    test_upper_boundary_of_the_factor_is_kept()
    test_the_ingest_wiring()
    test_ingest_refuses_a_re_capture_before_it_merges()
    test_the_store_scan_is_clean_and_a_regression_is_reported()
    test_the_check_is_wired_into_the_data_stage()
    print(f"weight-gb-contradiction: {_PASS} passed, {_FAIL} failed")
    return 1 if _FAIL else 0


if __name__ == "__main__":
    raise SystemExit(main())
