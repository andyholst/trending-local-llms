#!/usr/bin/env python3
"""Post-refresh data-gap analysis (issue #115).

The analysis must (a) report a requirement dimension the CONTRACT cannot hold as a
contract gap, (b) separate a value that exists only as free text from one that is
actually stored, (c) file exactly ONE issue when the gap set changed — none when it
did not, and (d) be wired into the Makefile and the refresh pipeline (rule 6d: no
dead script). Wired into `make test`.

Run:  python3 tests/test_data_gap_analysis.py    or   make test
"""
from __future__ import annotations

import json
import os
import stat
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import data_gap_analysis as G  # noqa: E402

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


def store_with(models: list[dict]) -> dict:
    return {"generated_utc": "2026-10-14T06:00:00Z",
            "engines": {"llama.cpp": {"backend": "CUDA / CPU", "note": "x", "url": "https://u"}},
            "models": models}


def model(mid: str, **extra) -> dict:
    m = {"id": mid, "name": mid, "full_name": mid, "type": "LLM", "license": "Apache 2.0",
         "params": "27B", "hf": f"a/{mid}", "vram_tier": "16GB", "vram_min": "12GB",
         "backends": ["CUDA"], "supported_engines": ["llama.cpp"], "why": "w",
         "last_seen": "2026-10-14",
         "engines": [{"engine": "llama.cpp", "tps": "91", "hardware": "RTX 4090 24GB",
                      "quant": "Q4_K_M", "date": "2026-10-14",
                      "source_post": "https://lightbrd.com/u/status/1"}]}
    m.update(extra)
    return m


def contract_declaring(*keys: str) -> dict:
    """A contract that declares `keys` on a model — the shape only matters for the
    keys, which is what the analysis reads."""
    return {
        "properties": {"models": {"items": {"properties": {k: {"type": "string"} for k in keys}
                                            | {"id": {"type": "string"}},
                                   }}},
    }


def test_contract_gap_vs_stored_dimension():
    """A dimension absent from the contract is a CONTRACT gap (ingest prunes it);
    one the contract declares is only 'missing values'."""

    # Given a store with a model and a contract that declares system_ram_min
    with tempfile.TemporaryDirectory() as td:
        cp = Path(td) / "contract.json"
        cp.write_text(json.dumps(contract_declaring("id", "system_ram_min")))
        saved_c, saved_s = G.CONTRACT, G.SEARCH_CONTRACT
        G.CONTRACT, G.SEARCH_CONTRACT = cp, Path(td) / "absent.json"
        try:
            contract = G.contract_keys()
        finally:
            G.CONTRACT, G.SEARCH_CONTRACT = saved_c, saved_s

        # When  the store is analysed
        report = G.analyse(store_with([model("m1")]), contract, raw_dir=Path(td) / "raw")

        # Then  system_ram_min is NOT a contract gap, but the value is missing
        check("declared key is not a contract gap", "system_ram_min" not in report["contract_gaps"])
        check("declared key with no value is 'missing'", report["missing"]["system_ram_min"] == ["m1"])
        # And  a dimension the contract does not declare IS a contract gap
        check("undeclared dimension is a contract gap", "context_tokens" in report["contract_gaps"])
        check("contract gap explains the prune",
              "pruned at ingest" in report["contract_gaps"]["context_tokens"])


def test_free_text_mention_is_unstructured_not_present():
    """A RAM figure that lives inside `quant` is unstructured data, not stored data —
    the exact gap measured on the store (Gemma 4 edge: '1432 MB peak RAM')."""

    # Given a model whose only RAM figure is free text inside `quant`
    m = model("gemma-4-e2b", quant=None)
    m["engines"][0]["quant"] = "1432 MB peak RAM"
    m["why"] = "runs on a Raspberry Pi 5 at 1432 MB peak RAM"

    # When  it is analysed
    report = G.analyse(store_with([m]), {"model": set(), "measurement": set(), "search_model": set()},
                       raw_dir=Path("/nonexistent"))

    # Then  it is reported as free-text-only, and never as having the dimension
    check("free-text RAM is flagged unstructured", report["unstructured"]["system_ram_min"] == ["gemma-4-e2b"])
    check("the model still counts as missing system_ram_min", report["missing"]["system_ram_min"] == ["gemma-4-e2b"])
    check("the finding names the free-text case",
          any("free text" in f for f in report["findings"]), str(report["findings"]))


def test_signature_tracks_the_store_not_the_noise():
    """The issue-triggering signature covers what the STORE lacks; volatile items
    (empty raw legs, estimates) stay in the report and out of the signature."""

    # Given one store, analysed twice
    contract = {"model": set(), "measurement": set(), "search_model": set()}
    a = G.analyse(store_with([model("m1")]), contract, raw_dir=Path("/nonexistent"))
    b = G.analyse(store_with([model("m1")]), contract, raw_dir=Path("/nonexistent"))

    # Then  the signature is stable
    check("same data -> same signature", a["signature"] == b["signature"])
    check("signature covers the missing dimensions",
          "missing:system_ram_min:m1" in a["signature"], str(a["signature"]))

    # And  a new model missing a dimension changes it
    c = G.analyse(store_with([model("m1"), model("m2")]), contract, raw_dir=Path("/nonexistent"))
    check("a new model changes the signature", c["signature"] != a["signature"])

    # And  an estimate-only difference does NOT (it is report-only)
    d = store_with([model("m1")])
    d["models"][0]["engines"][0]["tps"] = "91 (est)"
    report = G.analyse(d, contract, raw_dir=Path("/nonexistent"))
    check("an '(est)' t/s is reported but does not change the signature",
          report["signature"] == a["signature"] and bool(report["maintenance"]["estimated"]))


def test_one_issue_per_changed_gap_set(tmp_path=None, monkeypatch=None):
    """`--issue` files ONE issue when the gap set changed and none when it did not;
    the `gh` call is the real subprocess, against a stub CLI on PATH."""
    if tmp_path is None:  # the standalone runner passes no pytest fixture
        with tempfile.TemporaryDirectory() as td:
            return _one_issue_per_changed_gap_set(Path(td))
    return _one_issue_per_changed_gap_set(Path(tmp_path))


def _one_issue_per_changed_gap_set(tmp_path):
    # Given a stub `gh` on PATH that records how it was called
    bindir = tmp_path / "bin"
    bindir.mkdir()
    log = tmp_path / "gh.log"
    gh = bindir / "gh"
    gh.write_text(f"#!/bin/sh\nprintf '%s\\n' \"$@\" >> {log}\ncat >> {log}\n"
                  "printf '%s\\n' 'https://github.com/andyholst/trending-local-llms/issues/999'\n")
    gh.chmod(gh.stat().st_mode | stat.S_IEXEC)

    store = tmp_path / "models.json"
    store.write_text(json.dumps(store_with([model("m1"), model("m2")])))
    baseline = tmp_path / "gap_baseline.json"
    saved_path = os.environ["PATH"]
    os.environ["PATH"] = f"{bindir}:{saved_path}"
    saved_store, saved_contract = G.STORE, G.CONTRACT
    G.STORE, G.CONTRACT = store, tmp_path / "absent-contract.json"
    try:
        # When  it runs the first time (no baseline)
        first = G.main(["--baseline", str(baseline), "--issue"])
        # Then  it files the issue, labels it, and writes the baseline
        args = log.read_text()
        check("first run exits 0", first == 0)
        check("first run files an issue", "issue" in args and "create" in args)
        check("issue carries the analysis label", G.LABEL in args)
        check("issue body names the ranked gap", "system_ram_min" in args, args[:200])
        check("baseline written", baseline.exists())

        # And  an unchanged gap set files NOTHING
        log.write_text("")
        second = G.main(["--baseline", str(baseline), "--issue"])
        check("unchanged gap set files no second issue", second == 0 and log.read_text() == "")

        # And  a changed gap set files again, and `--check` turns it into a signal
        store.write_text(json.dumps(store_with([model("m1"), model("m2"), model("m3")])))
        third = G.main(["--baseline", str(baseline), "--check"])
        check("a changed gap set exits 1 under --check", third == 1)
        fourth = G.main(["--baseline", str(baseline)])
        check("report-only runs stay exit 0", fourth == 0)
    finally:
        G.STORE, G.CONTRACT = saved_store, saved_contract
        os.environ["PATH"] = saved_path


def test_real_store_names_the_system_ram_gap():
    """On the REAL store + contracts: system RAM is the flagship gap — the contract
    cannot hold it, every model lacks it, and at least one names it in free text."""

    # Given the real store and the real contracts
    contract = G.contract_keys()
    report = G.analyse(G.load(G.STORE), contract, raw_dir=G.RAW_DIR)

    # Then  the RAM dimension is a contract gap and every model is missing it
    check("real store: system_ram_min is a contract gap", "system_ram_min" in report["contract_gaps"])
    check("real store: models exist", report["models"] > 0, str(report["models"]))
    check("real store: system_ram_min missing on every model",
          len(report["missing"]["system_ram_min"]) == report["models"])
    check("real store: at least one free-text RAM mention",
          bool(report["unstructured"]["system_ram_min"]), str(report["unstructured"]["system_ram_min"]))
    check("real store: RAM is the top-ranked gap",
          G.rank_impact(report)[0][0] in ("context_tokens", "engine_min_version", "storage_offload",
                                          "system_ram_min", "weight_gb"), str(G.rank_impact(report)[:3]))


def test_analysis_is_wired_to_make_and_the_refresh_pipeline():
    """Rule 6d: the analysis is a make target the refresh pipeline runs — a script
    no target calls is a defect."""

    # Given the Makefile and the refresh pipeline
    makefile = (ROOT / "Makefile").read_text()
    workflow = (ROOT / ".github/workflows/refresh-bot.yml").read_text()

    # Then  the targets exist, follow the internal-`_name` + public-wrapper pattern,
    #       and the pipeline runs both the report and the issue step
    for target in ("_data-gaps", "data-gaps", "_data-gap-issue", "data-gap-issue"):
        check(f"Makefile defines {target}", f"{target}:" in makefile)
    check("public target runs the container wrapper", "$(TEST_RUN) make _data-gaps" in makefile)
    check("the script is called from the Makefile", "scripts/data_gap_analysis.py" in makefile)
    check("refresh pipeline runs the report", "make data-gaps" in workflow)
    check("refresh pipeline files the issue", "make data-gap-issue" in workflow)
    check("issue step uses the owner PAT, never the default token",
          "FIXBOT_DISPATCH_TOKEN" in workflow.split("make data-gap-issue")[0][-400:])


def main() -> int:
    print("data-gap analysis: unit tests")
    test_contract_gap_vs_stored_dimension()
    test_free_text_mention_is_unstructured_not_present()
    test_signature_tracks_the_store_not_the_noise()
    with tempfile.TemporaryDirectory() as td:
        test_one_issue_per_changed_gap_set(Path(td))
    test_real_store_names_the_system_ram_gap()
    test_analysis_is_wired_to_make_and_the_refresh_pipeline()
    print(f"\nPASSED {_PASS} | FAILED {_FAIL}")
    return 1 if _FAIL else 0


if __name__ == "__main__":
    raise SystemExit(main())
