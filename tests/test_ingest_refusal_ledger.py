#!/usr/bin/env python3
"""Every ingest refusal is TRACEABLE, and the gap analysis reads it (issue #888).

The four refusal seams (#458 fabricated engine, #468 misattribution, #702 cross-model
copy, #615 weight contradiction) refuse loudly but left NO trace: `make data-gaps`
could only ever see a model missing a dimension and report it "not stated by any
captured post" (acquisition gap) — sending a re-search after posts the pipeline
already holds. The seams now record each refusal in an append-only ledger
(`data/refusals.json`: backend, model, engine, reason, source post, stage, utc) and
the analysis reports "REFUSED at ingest" as its own class beside acquisition/ingest.

Driven through the REAL seams and the REAL analysis (rule 6m): the real
`ingest_raw_snapshots` over a real raw fixture under the real `TRENDING_DATA_DIR`
seam, the real `record_ingest_refusals` writer, the real `data_gap_analysis.analyse`
with a real contract file. No stand-ins for the logic under test.

  - test_every_refusal_seam_records_to_the_ledger   all four stages land, fields intact
  - test_the_refused_measurements_never_reach_the_store  the seams still refuse
  - test_the_refusal_stays_visible_in_the_log        bounded per-file + run summaries
  - test_the_ledger_is_append_only                   a second run never rewrites round 1
  - test_an_unreadable_ledger_is_never_rewritten     corrupt file stands; refusal logged
  - test_record_refuses_an_unknown_stage             rule 6d: one stage registry
  - test_the_gap_analysis_distinguishes_refused_from_never_captured  report + render
  - test_refusals_change_the_gap_signature           a new refusal is a new gap state
  - test_every_refusal_call_site_names_a_registered_stage  tree scan (rule 6d)

Run:  python3 tests/test_ingest_refusal_ledger.py   or   make test
"""
from __future__ import annotations

import contextlib
import importlib
import io
import json
import os
import re
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

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


POST1 = "https://lightbrd.com/a/status/9001"
POST2 = "https://lightbrd.com/a/status/9002"
POST3 = "https://lightbrd.com/a/status/9003"
POST4 = "https://lightbrd.com/a/status/9004"
POST5 = "https://lightbrd.com/a/status/9005"

ENGINE_URL = "https://github.com/ggml-org/llama.cpp"


def _store() -> dict:
    """The established store: the cross-model CARRIER, the weight-contradiction owner,
    the family the misattribution seam matches against."""
    return {
        "generated_utc": "2026-11-13T00:00:00Z",
        "note": "fixture",
        "engines": {"llama.cpp": {"backend": "CUDA / CPU / Metal", "note": "n",
                                  "url": ENGINE_URL}},
        "models": [
            {"id": "carrier-model", "name": "Carrier Model 14B",
             "full_name": "Carrier-Model-14B", "type": "LLM", "license": "Apache 2.0",
             "params": "14B", "hf": "a/carrier-model", "vram_tier": "12GB",
             "backends": ["CUDA"], "last_seen": "2026-11-12",
             "engines": [{"engine": "llama.cpp", "tps": "999",
                          "hardware": "RTX 4090 24GB", "quant": "Q4_K_M",
                          "date": "2026-11-12", "source_post": POST2}]},
            {"id": "qwen-3-5-35b", "name": "Qwen 3.5 35B", "full_name": "Qwen-3.5-35B",
             "type": "LLM", "license": "Apache 2.0", "params": "35B",
             "hf": "a/qwen-3-5-35b", "vram_tier": "24GB", "backends": ["CUDA"],
             "last_seen": "2026-11-12", "engines": []},
            {"id": "tiny-model", "name": "Tiny Model 2B", "full_name": "Tiny-Model-2B",
             "type": "LLM", "license": "Apache 2.0", "params": "2B",
             "hf": "a/tiny-model", "vram_tier": "4GB", "weight_gb": "2GB",
             "backends": ["CUDA"], "last_seen": "2026-11-12", "engines": []},
        ],
    }


def _raw_model(mid: str, name: str, full: str, params: str, vram: str,
               engines: list[dict]) -> dict:
    """The shape ONE search leg writes (mirrors tests/test_measurement_footprint.py,
    which the REAL search contract accepts)."""
    return {
        "id": mid, "name": name, "full_name": full, "type": "LLM",
        "license": "Apache 2.0", "params": params, "hf": f"a/{mid}",
        "vram_tier": vram, "backends": ["CUDA"], "why": "test fixture",
        "last_seen": "2026-11-14",
        "engagement": {"likes": 10, "comments": 2, "views": 1000},
        "engines": engines,
    }


def _meas(engine: str, tps: str, hardware: str, post: str, **extra) -> dict:
    m = {"engine": engine, "tps": tps, "hardware": hardware,
         "date": "2026-11-14", "source_post": post}
    m.update(extra)
    return m


def _raw_round1() -> dict:
    return {
        "backend": "nvidia",
        "generated_utc": "2026-11-14T09:00:00Z",
        "models": [
            # (a) fabricated engine: quant token inside the engine name (#458);
            #     the same row ALSO carries a legitimate measurement.
            _raw_model("new-model", "New Model 27B", "New-Model-27B", "27B", "24GB", [
                _meas("llama.cpp Q4_K_M", "70", "RTX 5090 32GB", POST1,
                      quant="Q4_K_M"),
                _meas("llama.cpp", "77", "RTX 4090 24GB", POST1, quant="Q4_K_M"),
            ]),
            # (b) misattribution (#468): the text names Qwen 3.5 35B, not the row.
            _raw_model("qwen-3-6-27b", "Qwen 3.6 27B", "Qwen-3.6-27B", "27B", "24GB", [
                _meas("llama.cpp", "41", "RTX 4090 24GB", POST3,
                      quant="Qwen 3.5 35B served through llama.cpp at 41 tok/s"),
            ]),
            # (c) cross-model copy (#702): the exact carrier tuple.
            _raw_model("copy-model", "Copy Model 14B", "Copy-Model-14B", "14B", "12GB", [
                _meas("llama.cpp", "999", "RTX 4090 24GB", POST2, quant="Q4_K_M"),
            ]),
            # (d) weight contradiction (#615): 493GB cannot belong to a 2 GB model.
            _raw_model("tiny-model", "Tiny Model 2B", "Tiny-Model-2B", "2B", "4GB", [
                _meas("llama.cpp", "300", "4x M5 Ultra", POST4,
                      quant="FP4", weight_gb="~493GB NVFP4"),
            ]),
        ],
    }


def _raw_round2() -> dict:
    return {
        "backend": "nvidia",
        "generated_utc": "2026-11-15T09:00:00Z",
        "models": [
            _raw_model("second-model", "Second Model 8B", "Second-Model-8B", "8B", "12GB", [
                _meas("llama.cpp Q8_0", "88", "RTX 5090 32GB", POST5,
                      quant="Q8_0"),
            ]),
        ],
    }


def _fresh(data_dir: Path):
    """Import update_trending through the real data-dir seam, like the make targets."""
    os.environ["TRENDING_DATA_DIR"] = str(data_dir)
    import update_trending as ut
    importlib.reload(ut)
    return ut


def _run_ingest_round(ut, store: dict, raw: dict, since=None) -> tuple[dict, str]:
    data_dir = Path(os.environ["TRENDING_DATA_DIR"])
    raw_dir = data_dir / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    stamp = raw["generated_utc"].replace("-", "").replace(":", "")
    (raw_dir / f"{raw['backend']}-{stamp}.json").write_text(json.dumps(raw))
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        ut.ingest_raw_snapshots(store, since=since)
    return store, buf.getvalue()


def test_every_refusal_seam_records_to_the_ledger():
    with tempfile.TemporaryDirectory() as tmp:
        ut = _fresh(Path(tmp))
        store, out = _run_ingest_round(ut, _store(), _raw_round1())
        ledger_path = Path(tmp) / "refusals.json"
        check("the ledger file was written", ledger_path.exists(), out)
        if not ledger_path.exists():
            return
        doc = json.loads(ledger_path.read_text())
        rows = doc.get("refusals") or []
        stages = {r.get("stage") for r in rows}
        check("all four seams recorded", stages == set(ut.REFUSAL_STAGES), stages)
        for r in rows:
            ok = all(r.get(k) for k in ("utc", "stage", "backend", "model",
                                        "engine", "reason", "source_post"))
            if not ok:
                check(f"ledger entry carries every field: {r}", False)
                break
        else:
            check("every entry names backend/model/engine/reason/source post", True)
        check("backend is the raw snapshot's own", all(r["backend"] == "nvidia" for r in rows))
        by_model = {r["model"]: r for r in rows}
        check("fabricated engine names the quant token",
              "Q4_K_M" in by_model.get("new-model", {}).get("reason", ""))
        check("misattribution names the other model",
              "35" in by_model.get("qwen-3-6-27b", {}).get("reason", ""))
        check("cross-model copy names the carrier tuple's post",
              by_model.get("copy-model", {}).get("source_post") == POST2)
        check("weight refusal states the ratio",
              "493" in by_model.get("tiny-model", {}).get("reason", ""))


def test_the_refused_measurements_never_reach_the_store():
    with tempfile.TemporaryDirectory() as tmp:
        ut = _fresh(Path(tmp))
        store, out = _run_ingest_round(ut, _store(), _raw_round1())
        models = {m["id"]: m for m in store["models"]}
        new = models.get("new-model") or {}
        tps = {str(e.get("tps")) for e in new.get("engines") or []}
        check("the valid measurement survived", "77" in tps, tps)
        check("the fabricated engine row did not land",
              not any("Q4_K_M" in str(e.get("engine")) for e in new.get("engines") or []))
        all_meas = [e for m in store["models"] for e in m.get("engines") or []]
        check("the misattributed text is nowhere in the store",
              not any("35B served" in str(e.get("quant")) for e in all_meas))
        check("the cross-model copy did not land on copy-model",
              not any(str(e.get("tps")) == "999"
                      and str(e.get("source_post")) == POST2
                      for e in (models.get("copy-model") or {}).get("engines") or []))
        check("the carrier kept its own measurement",
              any(str(e.get("tps")) == "999"
                  for e in models["carrier-model"].get("engines") or []))
        check("the 493GB weight did not land",
              not any("493" in str(e.get("weight_gb")) for e in all_meas))


def test_the_refusal_stays_visible_in_the_log():
    with tempfile.TemporaryDirectory() as tmp:
        ut = _fresh(Path(tmp))
        store, out = _run_ingest_round(ut, _store(), _raw_round1())
        check("fabricated refusal still prints", "REFUSED fabricated engine" in out)
        check("misattribution refusal still prints", "REFUSED misattributed" in out)
        check("cross-model refusal still prints", "REFUSED cross-model duplicate" in out)
        check("weight refusal still prints", "REFUSED weight-gb contradiction" in out)
        check("the per-file summary names the ledger", "recorded in the refusals ledger" in out)
        check("the run summary states the total and the distinction",
              "4 measurement(s) refused at ingest this run" in out
              and "'refused at ingest' from 'never captured'" in out, out[-400:])


def test_the_ledger_is_append_only():
    from datetime import datetime, timezone
    with tempfile.TemporaryDirectory() as tmp:
        ut = _fresh(Path(tmp))
        store, _ = _run_ingest_round(ut, _store(), _raw_round1())
        ledger = Path(tmp) / "refusals.json"
        first = json.loads(ledger.read_text())["refusals"]
        # A real refresh merges only NEWER snapshots (the `since` gate), so round 2
        # re-records ONLY round 2's refusals — the ledger grows, it never rewrites.
        store, _ = _run_ingest_round(
            ut, store, _raw_round2(),
            since=datetime(2026, 11, 14, 23, 59, tzinfo=timezone.utc))
        doc = json.loads(ledger.read_text())
        rows = doc["refusals"]
        check("round 2 appended without dropping round 1",
              rows[:len(first)] == first and len(rows) == len(first) + 1, len(rows))
        check("round 2 refusal recorded", rows[-1]["model"] == "second-model")


def test_an_unreadable_ledger_is_never_rewritten():
    with tempfile.TemporaryDirectory() as tmp:
        ut = _fresh(Path(tmp))
        ledger = Path(tmp) / "refusals.json"
        ledger.write_text("{ this is not json")
        before = ledger.read_text()
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            n = ut.record_ingest_refusals(
                {"id": "m1"}, "refuse_fabricated_engines", [("llama.cpp Q4_K_M", "why", POST1)],
                "nvidia")
        check("a corrupt ledger records nothing (returns 0)", n == 0)
        check("a corrupt ledger is NOT rewritten (rule 3b)", ledger.read_text() == before)
        check("the refusal is still reported loudly", "NOT rewriting it" in buf.getvalue())


def test_record_refuses_an_unknown_stage():
    with tempfile.TemporaryDirectory() as tmp:
        ut = _fresh(Path(tmp))
        try:
            ut.record_ingest_refusals({"id": "m"}, "refuse_something_new",
                                      [("e", "w", POST1)], "cpu")
            check("unknown stage raises", False, "no exception")
        except ValueError as exc:
            check("unknown stage raises loudly (one registry)",
                  "unknown refusal stage" in str(exc))


def test_the_gap_analysis_distinguishes_refused_from_never_captured():
    import data_gap_analysis as dga
    with tempfile.TemporaryDirectory() as tmp:
        ut = _fresh(Path(tmp))
        store, _ = _run_ingest_round(ut, _store(), _raw_round1())
        ledger_rows = json.loads((Path(tmp) / "refusals.json").read_text())["refusals"]
        # tiny-model's only weight figure was the refused 493GB one; its own 2GB
        # footprint proves the contradiction. The ledger must re-label its weight_gb
        # gap as REFUSED, not "never captured".
        contract = dga.contract_keys()
        report = dga.analyse(store, contract,
                             raw_dir=Path(tmp) / "raw", refusals=ledger_rows)
        check("the report carries refused_at_ingest", "refused_at_ingest" in report)
        check("weight refusals map to the weight_gb dimension",
              "tiny-model" in (report.get("refused_dimensions") or {}).get("weight_gb", []),
              report.get("refused_dimensions"))
        kind = dga._gap_kind(report, "weight_gb")
        check("the gap line names the refused class",
              "refused at ingest" in kind and "fix the capture, not the query" in kind, kind)
        text = dga.render(report)
        check("the report renders its own section",
              "## Refused at ingest" in text)
        check("the section names the seam and the post",
              "refuse_weight_gb_contradictions" in text and POST4 in text)
        # 6+ refusals for one model: the render stays bounded, the ledger stays whole.
        fat = [{"utc": "x", "stage": "refuse_fabricated_engines", "backend": "nvidia",
                "model": "m-fat", "engine": f"llama.cpp Q4_K_M{i}", "reason": f"r{i}",
                "source_post": POST1} for i in range(6)]
        r2 = dga.analyse(store, contract, raw_dir=Path(tmp) / "raw", refusals=fat)
        check("a bounded render says where the rest lives",
              "more refusal(s) recorded in data/refusals.json" in dga.render(r2)
              or dga.render(r2).count("m-fat") >= 6, dga.render(r2)[-300:])


def test_refusals_change_the_gap_signature():
    import data_gap_analysis as dga
    with tempfile.TemporaryDirectory() as tmp:
        ut = _fresh(Path(tmp))
        store, _ = _run_ingest_round(ut, _store(), _raw_round1())
        ledger_rows = json.loads((Path(tmp) / "refusals.json").read_text())["refusals"]
        contract = dga.contract_keys()
        a = dga.analyse(store, contract, raw_dir=Path(tmp) / "raw", refusals=[])
        b = dga.analyse(store, contract, raw_dir=Path(tmp) / "raw", refusals=ledger_rows)
        check("a new refusal is a new gap state (baseline can notice it)",
              dga.signature_id(a) != dga.signature_id(b))


def test_every_refusal_call_site_names_a_registered_stage():
    src = (SCRIPTS / "update_trending.py").read_text()
    import update_trending as ut_mod
    stages = set(ut_mod.REFUSAL_STAGES)
    sites = re.findall(r'record_ingest_refusals\(\s*m,\s*"([^"]+)"', src)
    check("all four seams call the recorder exactly once",
          sorted(sites) == sorted(stages), sites)
    check("no seam records an unregistered stage", set(sites) <= stages, sites)


def main() -> int:
    for t in (test_every_refusal_seam_records_to_the_ledger,
              test_the_refused_measurements_never_reach_the_store,
              test_the_refusal_stays_visible_in_the_log,
              test_the_ledger_is_append_only,
              test_an_unreadable_ledger_is_never_rewritten,
              test_record_refuses_an_unknown_stage,
              test_the_gap_analysis_distinguishes_refused_from_never_captured,
              test_refusals_change_the_gap_signature,
              test_every_refusal_call_site_names_a_registered_stage):
        print(f"\n[{t.__name__}]")
        t()
    print(f"\n{ _PASS} passed, {_FAIL} failed")
    return 1 if _FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
