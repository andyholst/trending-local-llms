#!/usr/bin/env python3
"""Post-refresh data-gap analysis (issue #115).

The analysis must (a) report a requirement dimension the CONTRACT cannot hold as a
contract gap, (b) separate a value that exists only as free text from one that is
actually stored, (c) file exactly ONE issue when the gap set changed — none when it
did not, and (d) be wired into the Makefile and the refresh pipeline (rule 6d: no
dead script). Every dimension it reports must also be CAPTURABLE end to end: its
key declared OPTIONAL in BOTH contracts and merged at ingest onto an existing
model — a dimension the store can hold but never receives is still a gap — and
every value a model CARRIES must trace to a real `…/status/<id>` post: closing a
gap by inventing a figure (or by reading one the post never gave) is the one
failure this stage must never make. Wired into `make test`.

Run:  python3 tests/test_data_gap_analysis.py    or   make test
"""
from __future__ import annotations

import json
import os
import re
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


def test_a_measurement_level_value_is_captured():
    """#337/#376 put a run's footprint ON the measurement, and both contracts declare every
    dimension optional there. A value that lives only on a measurement is CAPTURED — counting
    it as missing re-filed the same gap issue on every refresh (#364 then #376 both topped out
    at `storage_offload` while the store held it; issues #368/#388)."""

    # Given a model whose ONLY storage_offload lives on one of its measurements
    with_meas = model("m-measured")
    with_meas["engines"][0]["storage_offload"] = "12 of 48 layers streamed from SSD"
    # …and a model that states it nowhere
    without = model("m-silent")

    # When  the store is analysed
    report = G.analyse(store_with([with_meas, without]),
                       {"model": set(), "measurement": set(), "search_model": set()},
                       raw_dir=Path("/nonexistent"))

    # Then  the measurement-level value counts as captured…
    check("a measurement-level value is NOT missing",
          report["missing"]["storage_offload"] == ["m-silent"], report["missing"]["storage_offload"])
    check("…and is not reported as free-text-only either",
          "m-measured" not in report["unstructured"]["storage_offload"],
          report["unstructured"]["storage_offload"])
    # …while a model that states it nowhere is still the gap it always was
    check("a model with the value nowhere is still missing",
          "m-silent" in report["missing"]["storage_offload"], report["missing"]["storage_offload"])
    check("the signature follows: the captured model is not a gap",
          not any("storage_offload:m-measured" in g for g in report["signature"]),
          str(report["signature"]))


def test_a_storage_offload_needs_a_medium_and_an_offload(  ):
    """Issues #413/#367: the detector matched `ssd|disk|offload` anywhere, so a RAM offload
    ("offloaded to the CPU"), a file size ("2.1GB on disk") and a machine's own SSD were all
    reported as a storage requirement the model has — five models re-filed for ever."""

    def unstructured(quant_text: str) -> list:
        m = model("m")
        m["engines"][0]["quant"] = quant_text
        return G.analyse(store_with([m]), {"model": set(), "measurement": set(), "search_model": set()},
                         raw_dir=Path("/nonexistent"))["unstructured"]["storage_offload"]

    # Then  a memory offload is NOT a storage offload
    check("storage_offload: 'offloaded to the CPU' is a RAM story",
          unstructured("Q4_K_M with 26 MoE layers offloaded to the CPU") == [], "flagged")
    check("storage_offload: 'experts in system RAM' is a RAM story",
          unstructured("Q4_K_M, experts in system RAM") == [], "flagged")
    check("storage_offload: a file size on disk is not an offload requirement",
          unstructured("4-bit MLX, 2.1GB on disk") == [], "flagged")
    check("storage_offload: a machine's own SSD is not the model's requirement",
          unstructured("M2 Ultra, 2TB SSD, 192GB unified memory") == [], "flagged")
    # …while a GENUINE storage-streaming requirement still counts
    check("storage_offload: experts streamed from NVMe SSD IS flagged",
          unstructured("experts streamed from NVMe SSD") == ["m"],
          unstructured("experts streamed from NVMe SSD"))
    check("storage_offload: 'offload to SSD' IS flagged",
          unstructured("MoE expert offload to SSD") == ["m"],
          unstructured("MoE expert offload to SSD"))
def test_a_capacity_mention_is_not_an_unstructured_weights_figure():
    """A card's VRAM, a Mac's unified memory and a context size are NOT weight footprints.
    Counting them as `unstructured:weight_gb` reported 18 claims that do not exist and sent a
    backfill hunting for weights in text that never stated one (issue #213)."""

    # Given a model whose HARDWARE names a card, and another whose quant states a footprint
    card = model("card")
    card["engines"][0].update({"hardware": "RX 9070 XT 16GB", "quant": "Q4_K_M, Vulkan (RADV)"})
    stated = model("stated")
    stated["engines"][0].update({"hardware": "RTX 4090 24GB", "quant": "Q4_K_M, 19GB weights"})
    mac = model("mac")
    mac["engines"][0].update({"hardware": "M3 Ultra 256GB", "quant": "oQ4e DWQ"})

    # When  the store is analysed
    report = G.analyse(store_with([card, stated, mac]),
                       {"model": set(), "measurement": set(), "search_model": set()},
                       raw_dir=Path("/nonexistent"))
    unstructured = report["unstructured"]["weight_gb"]

    # Then  only the model that STATES a footprint is prose-only
    check("weight_gb: a card's VRAM is not an unstructured weights figure",
          "card" not in unstructured, unstructured)
    check("weight_gb: a Mac's unified memory is not one either", "mac" not in unstructured,
          unstructured)
    check("weight_gb: a stated footprint IS reported as prose-only", "stated" in unstructured,
          unstructured)
    # …and all three still count as missing the STRUCTURED value (that is the real gap).
    check("weight_gb: all three are still missing the structured value",
          set(report["missing"]["weight_gb"]) == {"card", "stated", "mac"},
          report["missing"]["weight_gb"])


def test_an_engine_note_is_not_per_model_prose_evidence():
    """An engine's registry note describes the ENGINE, and every model that names it
    shares it — so it can never be evidence about ONE model's footprint.

    Measured on the store (issue #456): the `DFlash2` note reads "Speculative decoding
    + context-lookup … up to ~381 tok/s context-lookup on 24 GB RTX 3090", and every
    model naming DFlash2 was reported as stating a context window in prose — three
    entries in `unstructured:context_tokens` and three `…:context_tokens:<model>`
    signature lines, from one sentence about an engine."""

    # Given a store whose engine note mentions a context window…
    store = store_with([model("silent", supported_engines=["DFlash2"])])
    store["engines"]["DFlash2"] = {
        "backend": "CUDA", "url": "https://github.com/x/dflash2",
        "note": "Speculative decoding + context-lookup; up to ~381 tok/s context-lookup on 24 GB RTX 3090 (128K context)"}
    # …and a model whose OWN quant states one
    speaking = model("speaking", supported_engines=["DFlash2"])
    speaking["engines"][0]["quant"] = "Q4_K_M, 128K context"
    store["models"].append(speaking)

    # When  the store is analysed
    report = G.analyse(store, {"model": set(), "measurement": set(), "search_model": set()},
                       raw_dir=Path("/nonexistent"))
    unstructured = report["unstructured"]["context_tokens"]

    # Then  the engine's sentence is NOT read as the silent model's prose…
    check("context_tokens: an engine note is not per-model prose evidence",
          "silent" not in unstructured, str(unstructured))
    # …the silent model is still a real COVERAGE gap…
    check("context_tokens: a model with no figure is still 'missing'",
          "silent" in report["missing"]["context_tokens"], str(report["missing"]["context_tokens"]))
    check("context_tokens: the engine note adds no UNSTRUCTURED signature entry for the model",
          not any(s.startswith("unstructured:") and s.endswith(":silent")
                  for s in report["signature"]), str(report["signature"]))
    # …and the guard is not vacuous: the model that states one IS reported.
    check("context_tokens: a model's own stated window is still reported as prose",
          "speaking" in unstructured, str(unstructured))


def test_a_context_window_needs_a_figure():
    """`context` is a TOPIC, not a figure. Issue #456: the detector matched any
    `context` / `kv-cache` word or a bare `NN k`, so a KV-cache QUANT
    (`"kv-cache q4_0"`), a feature name (`"DFlash2 context lookup"`) and a
    document-size test (`"25K-token document reproduction"`) were reported as
    context windows the store had left unstructured."""

    def unstructured(field_text: str) -> list:
        m = model("m")
        m["engines"][0]["quant"] = field_text
        return G.analyse(store_with([m]), {"model": set(), "measurement": set(), "search_model": set()},
                         raw_dir=Path("/nonexistent"))["unstructured"]["context_tokens"]

    # Then  a topic word with no figure is NOT a context window
    check("context_tokens: 'kv-cache q4_0' is a cache QUANT, not a window",
          unstructured("Q4_K_M, + flash-attention + kv-cache q4_0; 30 tok/s at 70B Q4") == [], "flagged")
    check("context_tokens: 'context lookup' is a feature, not a window",
          unstructured("DFlash2 context lookup, 25K-token document reproduction") == [], "flagged")
    check("context_tokens: 'NX-token document' is not a model's context window",
          unstructured("prefix caching, 25K-token document reproduction") == [], "flagged")
    check("context_tokens: a capacity near the word 'context' is not a window",
          unstructured("a long context on 24 GB, RTX 3090") == [], "flagged")
    # …while a stated window IS one, in every wording the posts use
    for text in ("80k context, model fully in VRAM", "Multimodal + audio, 256K ctx.",
                 "llama-server, 262,144-token context", "context window 131072",
                 "ctx 32K", "64K kv cache"):
        check(f"context_tokens: {text!r} IS a stated window", unstructured(text) == ["m"],
              f"{text!r} -> {unstructured(text)}")


def test_flash_attention_is_not_a_storage_medium():
    """`flash` in the medium list made an attention KERNEL answer for an SSD.

    Measured on the store (issue #456): `bonsai-2-9b` was reported as
    `unstructured:storage_offload` for "llama-server with GPU offload, Flash
    Attention, 262,144-token context" — no storage medium is named at all."""

    def unstructured(field_text: str) -> list:
        m = model("m")
        m["engines"][0]["quant"] = field_text
        return G.analyse(store_with([m]), {"model": set(), "measurement": set(), "search_model": set()},
                         raw_dir=Path("/nonexistent"))["unstructured"]["storage_offload"]

    # Then  Flash Attention is not a storage offload
    check("storage_offload: 'Flash Attention' is an attention kernel, not an SSD",
          unstructured("llama-server with GPU offload, Flash Attention, 262,144-token context") == [],
          "flagged")
    # …while flash STORAGE still is
    check("storage_offload: 'flash storage' is still a medium",
          unstructured("experts streamed from flash storage") == ["m"],
          str(unstructured("experts streamed from flash storage")))
    check("storage_offload: 'NVMe flash drive' is still a medium",
          unstructured("MoE expert offload to an NVMe flash drive") == ["m"],
          str(unstructured("MoE expert offload to an NVMe flash drive")))


def test_a_vram_capacity_is_not_a_weights_figure_even_beside_gguf():
    """A capacity qualified as MEMORY is the machine, not the weights — even when a
    weights word sits close enough to satisfy the proximity rule.

    Measured on the store (issue #456): `deepseek-v4.1-flash` was reported for
    "MXFP4-engram GGUF, 32K context at fp16, 16GB on VRAM + 60GB RAM" — `GGUF` is 24
    characters from `16GB`, but that 16GB is the card's VRAM (#213's class, surviving
    through a nearby format word)."""

    def unstructured(field_text: str) -> list:
        m = model("m")
        m["engines"][0]["quant"] = field_text
        return G.analyse(store_with([m]), {"model": set(), "measurement": set(), "search_model": set()},
                         raw_dir=Path("/nonexistent"))["unstructured"]["weight_gb"]

    # Then  a VRAM / RAM / unified-memory capacity is not a weight footprint
    check("weight_gb: '16GB on VRAM' beside GGUF is not a weights figure",
          unstructured("MXFP4-engram GGUF, 32K context at fp16, 16GB on VRAM + 60GB RAM") == [],
          "flagged")
    check("weight_gb: '60GB RAM' beside a quant word is not a weights figure",
          unstructured("Q4_K_M GGUF, 60GB RAM for the KV cache") == [], "flagged")
    check("weight_gb: '256GB unified memory' is not a weights figure",
          unstructured("GGUF, 256GB unified memory") == [], "flagged")
    # …while a stated footprint still IS one
    check("weight_gb: 'Q4_K_M (16.8GB weights)' IS a stated footprint",
          unstructured("Q4_K_M (16.8GB weights), + flash-attention") == ["m"], "not flagged")
    check("weight_gb: '<20GB weights' IS a stated footprint",
          unstructured("Fits 24/32 GB at 4-bit (<20GB weights + KV)") == ["m"], "not flagged")


def test_the_real_store_reports_only_figures_it_can_point_at():
    """On the store this change ships against, every `unstructured` claim is a figure
    in that model's OWN text, and the coverage counts are untouched.

    Measured before/after (issue #456): `unstructured:context_tokens` 6 -> 2,
    `unstructured:weight_gb` 3 -> 2, `unstructured:storage_offload` 1 -> 0, while
    `missing` stayed 30 / 36 / 44 / 58 / 35 — those are real acquisition gaps."""

    # Given the real store and contracts
    store = G.load(G.STORE)
    report = G.analyse(store, G.contract_keys(), raw_dir=G.RAW_DIR)
    by_id = {m.get("id"): m for m in store["models"]}

    def own_text(m: dict) -> list:
        fields = ("quant", "hardware", "why")
        return [str(m.get(f, "")) for f in fields] + [
            str(e.get(f, "")) for e in (m.get("engines") or []) for f in fields]

    # Then  every claim can be pointed at a figure in the model's own text …
    unpinned = [f"{k}:{mid}" for k, ids in report["unstructured"].items() for mid in ids
                if not any(next(d for d in G.DIMENSIONS if d["key"] == k)["text"].search(t)
                           for t in own_text(by_id[mid]))]
    check("real store: every 'unstructured' claim is a figure in the model's own text",
          unpinned == [], str(unpinned))

    # … the set is no larger than the measured, figure-bearing set …
    check("real store: context_tokens prose claims are the 2 stated windows",
          set(report["unstructured"]["context_tokens"]) <= {"qwen-3.6-27b", "gemma-4-12b"},
          str(report["unstructured"]["context_tokens"]))
    check("real store: weight_gb prose claims are the 2 stated footprints",
          set(report["unstructured"]["weight_gb"]) <= {"qwen3.6-27b", "muse-glimmer-30b"},
          str(report["unstructured"]["weight_gb"]))
    check("real store: no storage offload is claimed from 'Flash Attention'",
          report["unstructured"]["storage_offload"] == [],
          str(report["unstructured"]["storage_offload"]))

    # … and the COVERAGE gaps are still reported in full (the report did not go quiet).
    for key, count in (("system_ram_min", 30), ("weight_gb", 36), ("context_tokens", 44),
                       ("storage_offload", 58), ("engine_min_version", 35)):
        check(f"real store: {key} still reports its missing coverage",
              len(report["missing"][key]) == count, str(len(report["missing"][key])))


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
    # `issue view` answers the label verification (issue #161): the filer now
    # checks that the issue it filed carries the label the bots trigger on.
    gh.write_text(f"#!/bin/sh\nprintf '%s\\n' \"$@\" >> {log}\n"
                  "case \"$1 $2\" in\n"
                  "  'issue view') printf '%s\\n' '{\"labels\":[{\"name\":\"data-gap-analysis\"}]}' ;;\n"
                  "  'label list') printf '%s\\n' '[{\"name\":\"data-gap-analysis\"}]' ;;\n"
                  f"  *) cat >> {log}\n"
                  "     printf '%s\\n' 'https://github.com/andyholst/trending-local-llms/issues/999' ;;\n"
                  "esac\n")
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


def test_write_baseline_records_the_signature_without_filing(tmp_path=None):
    """Issue #174: `--write-baseline` records the CURRENT gap signature as the
    baseline and files NOTHING — the repair for a baseline write lost to a rebase
    or a refresh PR closed before it merged. The file it writes is the contract
    `changed()` reads on the next run, so it must equal `analyse(store)`'s
    signature exactly, and a run against it must then see "unchanged"."""
    if tmp_path is None:
        with tempfile.TemporaryDirectory() as td:
            return _write_baseline_records_the_signature_without_filing(Path(td))
    return _write_baseline_records_the_signature_without_filing(Path(tmp_path))


def _write_baseline_records_the_signature_without_filing(tmp_path):
    # Given a store and an ABSENT baseline
    store = tmp_path / "models.json"
    store.write_text(json.dumps(store_with([model("m1"), model("m2")])))
    baseline = tmp_path / "gap_baseline.json"
    saved_store, saved_contract = G.STORE, G.CONTRACT
    G.STORE, G.CONTRACT = store, tmp_path / "absent-contract.json"
    try:
        # When  `--write-baseline` runs — with NO `gh` on PATH, so a run that
        # tried to file would have raised instead of returning 0
        first = G.main(["--baseline", str(baseline), "--write-baseline",
                        "--out", str(tmp_path / "report.md")])

        # Then  it exits 0 and writes the baseline …
        check("--write-baseline exits 0", first == 0, str(first))
        check("--write-baseline writes the baseline file", baseline.exists())

        # … the written signature IS `analyse(store)` — the contract `changed()` reads …
        expected = G.analyse(G.load(store), G.contract_keys())["signature"]
        written = json.loads(baseline.read_text())["signature"]
        check("the written signature equals analyse(store)", written == expected,
              f"{written[:3]} != {expected[:3]}")

        # … and the next run sees NO change: `--check` is a green no-op against it
        check("a run against the fresh baseline sees no change",
              G.main(["--baseline", str(baseline), "--check",
                      "--out", str(tmp_path / "report2.md")]) == 0)

        # And  it filed nothing: the second run's baseline is still the one it wrote
        check("nothing re-filed or re-written by the check run",
              json.loads(baseline.read_text())["signature"] == written)
    finally:
        G.STORE, G.CONTRACT = saved_store, saved_contract


def test_real_store_dimensions_are_capturable_and_partly_filled():
    """On the REAL store + contracts: every reported dimension is CAPTURABLE end
    to end (declared OPTIONAL, so ingest keeps it instead of pruning it) and the
    backfill that closes the filed gaps is REAL data — at least one model now
    carries a structured value, a free-text mention is still never counted as a
    stored one, and a gap dimension is still ranked.

    The store used to have NO value for any of the five dimensions; asserting
    that emptiness is what this test must not do — it would fail the moment the
    gap actually closes (the point of the analysis)."""

    # Given the real store and the real contracts
    contract = G.contract_keys()
    store = G.load(G.STORE)
    report = G.analyse(store, contract, raw_dir=G.RAW_DIR)
    dims = [d["key"] for d in G.DIMENSIONS]

    # Then  each dimension is CAPTURABLE …
    check("real store: models exist", report["models"] > 0, str(report["models"]))
    for key in dims:
        check(f"real store: {key} is capturable (never a contract gap)",
              key not in report["contract_gaps"], str(report["contract_gaps"]))

    # … the backfill that closes the filed gaps has landed on at least one model …
    filled = [m.get("id") for m in store["models"] if any(m.get(k) for k in dims)]
    check("real store: at least one model carries a structured requirement dimension",
          bool(filled), "no model has any of " + str(dims))

    # … a figure that lives only in free text is still 'missing', never 'stored' …
    check("real store: free text is never counted as a stored value",
          all(set(report["unstructured"][k]) <= set(report["missing"][k]) for k in dims),
          str({k: report["unstructured"][k] for k in dims}))

    # … and the remaining gaps are still ranked and reported
    check("real store: a gap dimension is still ranked",
          bool(G.rank_impact(report)), str(G.rank_impact(report)[:3]))


def test_structured_dimensions_trace_to_a_real_post():
    """Every source-data dimension in the store must trace to a REAL X post.

    A model that carries one of the requirement dimensions must have at least
    one measurement whose `source_post` is a `…/status/<id>` URL: a figure
    without a post behind it is a fabrication, and the backfill measured on the
    store hit exactly this case (two models whose only 'source' was a placeholder
    URL or a profile page — their values were left unset, not invented)."""

    import update_trending as UT  # noqa: E402

    store = G.load(G.STORE)
    dims = [d["key"] for d in G.DIMENSIONS]
    untraceable = [
        f"{m.get('id')}:{k}"
        for m in store["models"] if any(m.get(k) for k in dims)
        for k in dims if m.get(k)
        and not any(UT._is_post_url(str(e.get("source_post", ""))) for e in (m.get("engines") or []))
    ]
    check("every structured dimension traces to a real …/status/<id> post",
          not untraceable, str(untraceable))
    check("and at least one dimension is actually filled (the guard is not vacuous)",
          any(m.get(k) for m in store["models"] for k in dims), "no dimension carries a value")


def test_every_dimension_is_a_declared_optional_key():
    """Every dimension the analysis reports must be CAPTURABLE, or the gap can
    never close: its key is declared in BOTH contracts (the search snapshot and
    the store), OPTIONAL in both (never added to `required` — AGENTS.md §2.3b),
    visible to the analysis, and merged at ingest onto an existing model."""

    # Given both real contracts and the ingest merge list
    mc = json.loads((ROOT / "data" / "model_contract.json").read_text())
    sc = json.loads((ROOT / "data" / "search_contract.json").read_text())
    m_items = mc["properties"]["models"]["items"]
    s_items = sc["properties"]["models"]["items"]
    import update_trending as UT  # noqa: E402  (sys.path already carries scripts/)

    # Then  every reported dimension is representable end to end
    declared = G.contract_keys()
    for dim in G.DIMENSIONS:
        key = dim["key"]
        check(f"{key}: declared in model_contract.json", key in m_items["properties"], str(key))
        check(f"{key}: declared in search_contract.json", key in s_items["properties"], str(key))
        check(f"{key}: OPTIONAL in both contracts (never in required)",
              key not in m_items.get("required", []) and key not in s_items.get("required", []))
        check(f"{key}: the analysis sees it as declared",
              key in declared["model"] or key in declared["measurement"] or key in declared["search_model"])
        check(f"{key}: merged at ingest for an EXISTING model",
              key in UT._ADDITIVE_MODEL_FIELDS, str(UT._ADDITIVE_MODEL_FIELDS))


def test_ingest_merge_list_covers_every_declared_dimension():
    """The ingest merge list and the reported dimensions are one set — a new
    dimension cannot be added to the analysis without ingest support (and a
    declared dimension cannot be reported as unfixable)."""

    import update_trending as UT  # noqa: E402
    check("ingest merge list == reported dimensions",
          set(UT._ADDITIVE_MODEL_FIELDS) == {d["key"] for d in G.DIMENSIONS},
          str(sorted(set(UT._ADDITIVE_MODEL_FIELDS) ^ {d["key"] for d in G.DIMENSIONS})))


def test_analysis_is_wired_to_make_and_the_refresh_pipeline():
    """Rule 6d: the analysis is a make target the refresh pipeline runs — a script
    no target calls is a defect."""

    # Given the Makefile and the refresh pipeline
    makefile = (ROOT / "Makefile").read_text()
    workflow = (ROOT / ".github/workflows/refresh-bot.yml").read_text()

    # Then  the report follows the internal-`_name` + public-wrapper pattern and
    #       runs in the image (it needs no `gh`) …
    for target in ("_data-gaps", "data-gaps", "data-gap-issue", "data-gap-baseline"):
        check(f"Makefile defines {target}", f"{target}:" in makefile)
    check("public target runs the container wrapper", "$(TEST_RUN) make _data-gaps" in makefile)
    check("the script is called from the Makefile", "scripts/data_gap_analysis.py" in makefile)

    # … and the filer's REPAIR half is reachable too (issue #174): `--write-baseline`
    # ran nowhere — no target, no workflow — so the "re-record the baseline without
    # filing" path was dead code (rule 6d) and could not be exercised or tested.
    baseline_t = (makefile.split("data-gap-baseline:", 1)[1].split("\n\n", 1)[0]
                  if "data-gap-baseline:" in makefile else "")
    check("data-gap-baseline records the baseline without filing",
          "python3 scripts/data_gap_analysis.py --write-baseline" in baseline_t, baseline_t)
    check("data-gap-baseline is HOST-side (writes the file as the caller, not as root)",
          "$(TEST_RUN)" not in baseline_t, baseline_t)
    check("no dead internal wrapper target is left behind (rule 6d)",
          "_data-gap-baseline:" not in makefile, "")

    # … and the FILER runs on the HOST, because the test image has no `gh`
    # (measured: the step died with FileNotFoundError: 'gh', issue #150).
    filer = makefile.split("data-gap-issue:", 1)[1].split("\n\n", 1)[0]
    check("filer target does NOT run in the image (no `gh` there)",
          "$(TEST_RUN)" not in filer and "python3 scripts/data_gap_analysis.py --issue" in filer,
          filer)
    check("no dead internal wrapper target is left behind (rule 6d)",
          "_data-gap-issue:" not in makefile, "")
    check("refresh pipeline runs the report", "make data-gaps" in workflow)
    check("refresh pipeline files the issue", "make data-gap-issue" in workflow)
    # The step's own comment promises the filer never blocks the data PR; that
    # promise is only kept with continue-on-error (measured: the job went red and
    # the PR step was skipped, run 38549751388).
    step = workflow.split("- name: File a data-gap issue", 1)[1].split("\n      - name:", 1)[0]
    # The token, corrected by the measurement in #277: the owner PAT declares no
    # Issues scope, so the filing it created carried NO label (the label is what
    # both bots' queues are keyed on) and the step failed silently. Issue writes
    # use the DEFAULT token with `issues: write` — the rule AGENTS.md §6b states.
    check("filer step uses the DEFAULT token (it must be able to write issues)",
          "github.token" in step and "FIXBOT_DISPATCH_TOKEN" not in step, step)
    check("the aggregate job requests `issues: write` for it",
          "issues: write" in workflow.split("- name: File a data-gap issue", 1)[0]
          .rsplit("aggregate:", 1)[-1], step)
    check("the filer step is report-only, as documented",
          "continue-on-error: true" in step, step)

    # Given the baseline the filer writes, derived from the script (not restated)
    baseline_rel = str(G.DEFAULT_BASELINE.relative_to(ROOT))
    check("the filer's baseline path is derived from the script",
          baseline_rel == "data/gap_baseline.json", baseline_rel)

    # When  the commit step that runs right AFTER the filer decides and stages
    commit = workflow.split("- name: Commit + open PR if changed", 1)[1]
    commit_head = commit.split("\n      - name:", 1)[0]

    # Then  its change test AND its git add include the baseline, or the new
    # baseline is discarded and the same gap issue is filed on every run (#152)
    diff_line = [l for l in commit_head.splitlines() if "git diff --quiet" in l]
    add_line = [l for l in commit_head.splitlines() if l.strip().startswith("git add ")]
    check("commit step: the change test includes the baseline",
          bool(diff_line) and baseline_rel in diff_line[0], str(diff_line))
    check("commit step: the baseline is staged",
          bool(add_line) and baseline_rel in add_line[0], str(add_line))

    # Then  the filer runs BEFORE that commit step: the file must exist when the
    # commit decides, and a baseline-only change must not print "No data changes"
    i_filer = workflow.index("run: make data-gap-issue")
    i_commit = workflow.index("- name: Commit + open PR if changed")
    check("ordering: the filer runs before the commit step", i_filer < i_commit,
          f"{i_filer} < {i_commit}")


# A fake `gh` on PATH: `issue list` answers from a store file, `issue create`
# records the signature marker from the body it receives on stdin and appends it
# to that store. The product code (the filer) runs for real; only the CLI is faked.
_GH_STUB = """#!/bin/sh
echo "$@" >> "$FAKE_GH_LOG"
case "$1 $2" in
  "issue list")
    sig=""
    for a in "$@"; do case "$a" in *" in:body") sig="${a% in:body}";; esac; done
    line=$(grep "^${sig}|" "$FAKE_GH_STORE" 2>/dev/null | head -1)
    if [ -n "$line" ]; then
      n=$(printf '%s' "$line" | cut -d'|' -f2)
      st=$(printf '%s' "$line" | cut -d'|' -f3)
      printf '[{"number":%s,"state":"%s","url":"https://example.test/issues/%s"}]\\n' "$n" "$st" "$n"
    else
      printf '[]\\n'
    fi ;;
  "issue create")
    body=$(cat)
    sig=$(printf '%s' "$body" | sed -n 's/.*data-gap-signature: \\([0-9a-f]*\\).*/\\1/p' | head -1)
    n=$(grep -c . "$FAKE_GH_STORE" 2>/dev/null || true)
    n=$(( ${n:-0} + 1 ))
    printf '%s|%s|OPEN\n' "$sig" "$n" >> "$FAKE_GH_STORE"
    printf 'https://example.test/issues/%s\n' "$n" ;;
  "issue view")
    printf '{"labels":[{"name":"data-gap-analysis"}]}\n' ;;
  "label list")
    # The repo already carries the label (issue #277: the filer checks before it
    # relies on it, and creates it when it is missing).
    printf '[{"name":"data-gap-analysis"}]\n' ;;
esac
exit 0
"""


def _run_filer(baseline_text, td):
    """Run `--issue` once with a stale baseline (a fresh checkout of master)."""
    baseline = td / "baseline.json"
    baseline.write_text(baseline_text)
    env = {**os.environ, "PATH": f"{td}{os.pathsep}{os.environ['PATH']}",
           "FAKE_GH_LOG": str(td / "gh.log"), "FAKE_GH_STORE": str(td / "issues.txt")}
    return subprocess.run(
        [sys.executable, "scripts/data_gap_analysis.py", "--issue", "--baseline", str(baseline)],
        cwd=ROOT, capture_output=True, text=True, env=env)


def test_a_gap_set_is_filed_once():
    """Issue #157: the baseline reaches master only through the refresh PR, so two
    runs before that merge see the same change. The second must file nothing."""
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        stub = td / "gh"
        stub.write_text(_GH_STUB)
        stub.chmod(0o755)
        (td / "gh.log").write_text("")
        (td / "issues.txt").write_text("")
        # A baseline whose signature differs from the store's = the stale master
        # state while the previous run's PR is still open.
        stale = json.dumps({"as_of": "2026-01-01T00:00:00Z", "signature": ["stale"]})

        # Given a refresh run that sees a changed gap set
        first = _run_filer(stale, td)

        # Then  it files exactly one issue, carrying the signature marker
        creates = [l for l in (td / "gh.log").read_text().splitlines() if l.startswith("issue create")]
        check("first run: files one issue", len(creates) == 1, str(creates))
        filed_sig = (td / "issues.txt").read_text().strip().split("|")[0]
        check("first run: the body carries the signature marker",
              len(filed_sig) == 12 and all(c in "0123456789abcdef" for c in filed_sig),
              (td / "issues.txt").read_text()[:80])
        # …and the baseline FILE is updated to this run's signature (the message
        # for that is only printed for the explicit `--write-baseline` flag)
        baseline_sig = json.loads((td / "baseline.json").read_text())["signature"]
        check("first run: the baseline is written",
              baseline_sig != ["stale"] and len(baseline_sig) > 1, str(baseline_sig)[:80])

        # When  the next run starts from master again (the baseline in the repo is
        # still the old one, because the first run's PR is not merged yet)
        second = _run_filer(stale, td)

        # Then  it recognises the gap set and files NO duplicate
        creates = [l for l in (td / "gh.log").read_text().splitlines() if l.startswith("issue create")]
        check("second run: no duplicate issue", len(creates) == 1, str(creates))
        check("second run: it says the gap set is already filed",
              "already filed" in second.stderr, second.stderr)

        # Given the previous issue was CLOSED (the work was done or dropped)
        store = (td / "issues.txt").read_text().replace("|OPEN", "|CLOSED")
        (td / "issues.txt").write_text(store)

        # When  the gap set is seen again
        third = _run_filer(stale, td)

        # Then  a closed issue does not block the new work
        creates = [l for l in (td / "gh.log").read_text().splitlines() if l.startswith("issue create")]
        check("third run: a CLOSED issue does not suppress a new one", len(creates) == 2, str(creates))
        check("third run: it files again", "filed https://example.test" in third.stderr, third.stderr)


# The same fake `gh`, extended for issue #161: `issue create` can silently DROP
# the label (measured in CI), `issue view` reports what the store holds, and
# `issue edit --add-label` can be made to fail as well.
_GH_STUB_LABELS = """#!/bin/sh
echo "$@" >> "$FAKE_GH_LOG"
case "$1 $2" in
  "issue list")
    sig=""
    for a in "$@"; do case "$a" in *" in:body") sig="${a% in:body}";; esac; done
    line=$(grep "^${sig}|" "$FAKE_GH_STORE" 2>/dev/null | head -1)
    if [ -n "$line" ]; then
      n=$(printf '%s' "$line" | cut -d'|' -f2)
      st=$(printf '%s' "$line" | cut -d'|' -f3)
      printf '[{"number":%s,"state":"%s","url":"https://example.test/issues/%s"}]\\n' "$n" "$st" "$n"
    else
      printf '[]\\n'
    fi ;;
  "issue create")
    body=$(cat)
    sig=$(printf '%s' "$body" | sed -n 's/.*data-gap-signature: \\([0-9a-f]*\\).*/\\1/p' | head -1)
    n=$(grep -c . "$FAKE_GH_STORE" 2>/dev/null || true)
    n=$(( ${n:-0} + 1 ))
    labels=""
    [ "${FAKE_GH_DROP_LABEL:-0}" = "1" ] || labels="data-gap-analysis"
    printf '%s|%s|OPEN|%s\\n' "$sig" "$n" "$labels" >> "$FAKE_GH_STORE"
    printf 'https://example.test/issues/%s\\n' "$n" ;;
  "issue view")
    line=$(cut -d'|' -f2,4 "$FAKE_GH_STORE" | grep "^${3}|" | head -1)
    labels=$(printf '%s' "$line" | cut -d'|' -f2)
    if [ -n "$labels" ]; then
      printf '{"labels":[{"name":"%s"}]}\\n' "$labels"
    else
      printf '{"labels":[]}\\n'
    fi ;;
  "issue edit")
    if [ "${FAKE_GH_EDIT_LABEL_FAILS:-0}" = "1" ]; then
      echo "could not add label: 'data-gap-analysis' not found" >&2
      exit 1
    fi
    n=""
    for a in "$@"; do case "$a" in [0-9]*) [ -z "$n" ] && n="$a";; esac; done
    awk -F'|' -v n="$n" 'BEGIN{OFS="|"} $2==n {$4="data-gap-analysis"} 1' \\
      "$FAKE_GH_STORE" > "$FAKE_GH_STORE.tmp" && mv "$FAKE_GH_STORE.tmp" "$FAKE_GH_STORE" ;;
  "label list")
    # The repo's label set is a FILE the test creates (or does not): a missing
    # label is exactly what GitHub silently ignores on `issue create`.
    if [ -f "$FAKE_GH_LABEL_FLAG" ]; then
      printf '[{"name":"data-gap-analysis"}]\\n'
    else
      printf '[]\\n'
    fi ;;
  "label create")
    # The repo gains the label — unless creating it is refused too.
    if [ "${FAKE_GH_LABEL_CREATE_FAILS:-0}" = "1" ]; then
      echo "HTTP 403: Resource not accessible by personal access token" >&2
      exit 1
    fi
    : > "$FAKE_GH_LABEL_FLAG" ;;
esac
exit 0
"""


def _run_filer_env(baseline_text, td, extra_env=None, label_exists=True):
    baseline = td / "baseline.json"
    baseline.write_text(baseline_text)
    label_flag = td / "label-exists"
    # Default: the repo already carries the label. With `label_exists=False` the
    # run starts WITHOUT it, and the stub writes the flag when it is asked to
    # create one — so a missing label is a case the test can set up, not an
    # accident of the environment.
    label_flag.unlink(missing_ok=True)
    if label_exists:
        label_flag.touch()
    env = {**os.environ, "PATH": f"{td}{os.pathsep}{os.environ['PATH']}",
           "FAKE_GH_LOG": str(td / "gh.log"), "FAKE_GH_STORE": str(td / "issues.txt"),
           "FAKE_GH_LABEL_FLAG": str(label_flag), **(extra_env or {})}
    return subprocess.run(
        [sys.executable, "scripts/data_gap_analysis.py", "--issue", "--baseline", str(baseline)],
        cwd=ROOT, capture_output=True, text=True, env=env)


def test_a_filed_issue_carries_the_label_the_bots_trigger_on():
    """Issue #161: the CLI created the issue with NO label while returning 0, and
    the label is exactly what issue-bot / its sweep key on — an unlabelled filing
    is invisible to both. The filer must verify, repair, or fail."""
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        stub = td / "gh"
        stub.write_text(_GH_STUB_LABELS)
        stub.chmod(0o755)
        (td / "gh.log").write_text("")
        (td / "issues.txt").write_text("")
        stale = json.dumps({"as_of": "2026-01-01T00:00:00Z", "signature": ["stale"]})

        # Given a create that returns 0 but applies no label
        dropped = _run_filer_env(stale, td, {"FAKE_GH_DROP_LABEL": "1"})

        # Then  the filed issue carries the label (re-applied), and it is a success
        check("label dropped: the run still exits 0", dropped.returncode == 0, dropped.stderr)
        check("label dropped: the issue ends up labelled",
              "data-gap-analysis" in (td / "issues.txt").read_text().splitlines()[0],
              (td / "issues.txt").read_text()[:80])
        check("label dropped: it re-applied the label with gh issue edit",
              any(l.startswith("issue edit") for l in (td / "gh.log").read_text().splitlines()),
              (td / "gh.log").read_text())

        # Given a create that drops the label AND an edit that cannot apply it
        (td / "issues.txt").write_text("")
        (td / "gh.log").write_text("")
        broken = _run_filer_env(stale, td, {"FAKE_GH_DROP_LABEL": "1",
                                            "FAKE_GH_EDIT_LABEL_FAILS": "1"})

        # Then  the filer FAILS LOUDLY instead of reporting an invisible filing
        check("label unappliable: the run fails", broken.returncode != 0, broken.stderr)
        check("label unappliable: it names the label and why it matters",
              "does not carry" in broken.stderr and "data-gap-analysis" in broken.stderr,
              broken.stderr)
        # …and it carries `gh`'s OWN words: the conclusion alone ("the label did
        # not stick") named no cause and no fix, which is what made the measured
        # failure (#277) unactionable.
        check("label unappliable: gh's own message reaches the operator",
              "not found" in broken.stderr, broken.stderr)


def test_the_filer_creates_the_label_the_bots_trigger_on():
    """Issue #277: GitHub IGNORES a label the repo does not have, so a filing made
    before `data-gap-analysis` exists lands UNLABELLED while `gh issue create`
    returns 0 — and `gh issue edit --add-label` then refuses it. The measured
    consequence on master: `make issue-queue` -> `candidates=0` and
    `make review-issue-pick` -> `action=none`, so the implementer's and the
    reviewer's jobs were SKIPPED every run while the pipeline stayed green. The
    filer must create the label rather than file into the void."""
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        stub = td / "gh"
        stub.write_text(_GH_STUB_LABELS)
        stub.chmod(0o755)
        (td / "gh.log").write_text("")
        (td / "issues.txt").write_text("")
        stale = json.dumps({"as_of": "2026-01-01T00:00:00Z", "signature": ["stale"]})

        # Given a repo that does NOT carry the label, and a create that drops it
        created = _run_filer_env(stale, td, {"FAKE_GH_DROP_LABEL": "1"}, label_exists=False)

        # Then  the label is created first, and the issue ends up carrying it
        calls = (td / "gh.log").read_text()
        check("label missing: the filer creates it", "label create" in calls, calls)
        check("label missing: the label now exists in the repo", (td / "label-exists").exists(), "")
        check("label missing: the run exits 0", created.returncode == 0, created.stderr)
        check("label missing: the filing is visible to both bots",
              "data-gap-analysis" in (td / "issues.txt").read_text().splitlines()[0],
              (td / "issues.txt").read_text()[:80])

        # Given the label cannot be created either
        (td / "issues.txt").write_text("")
        (td / "gh.log").write_text("")
        refused = _run_filer_env(stale, td, {"FAKE_GH_DROP_LABEL": "1",
                                             "FAKE_GH_LABEL_CREATE_FAILS": "1"},
                                 label_exists=False)

        # Then  the run fails loudly, naming gh's own refusal
        check("label uncreatable: the run fails", refused.returncode != 0, refused.stderr)
        check("label uncreatable: gh's refusal is quoted",
              "Resource not accessible" in refused.stderr, refused.stderr)


# ---- the backfill that closes the filed `engine_min_version` gap (issue #163) --
#
# A structured requirement dimension is only ever the SOURCE POST's own
# statement. The post is captured in data/raw/*.json, so the evidence for a
# value is the model's captured text there: a value whose version-like tokens
# (and at least one distinctive token) do not appear in it has no post behind it
# and is a fabrication — the one failure this stage must never make.

def _captured_text(store_models: set[str] | None = None) -> dict[str, str]:
    """Per model id, the free text the search captured in data/raw/*.json (the
    record of the real `…/status/<id>` post): the model's own prose plus every
    measurement's `quant` / `hardware`."""
    out: dict[str, list[str]] = {}
    for f in sorted(G.RAW_DIR.glob("*.json")):
        d = G.load(f, {}) or {}
        for m in d.get("models", []):
            mid = m.get("id")
            if not mid or (store_models is not None and mid not in store_models):
                continue
            parts = [m[k] for k in ("quant", "hardware", "why") if isinstance(m.get(k), str)]
            for e in m.get("engines", []) or []:
                parts += [e[k] for k in ("quant", "hardware") if isinstance(e.get(k), str)]
            out.setdefault(mid, []).append(" ".join(parts))
    return {k: " ".join(v) for k, v in out.items()}


def _engine_min_version_is_evidenced(value: str, captured: str) -> bool:
    """True when the captured source text supports the value: every version-like
    token of it appears in the text, and at least one distinctive token does."""
    hay = captured.lower()
    tokens = [t for t in re.split(r"[^A-Za-z0-9.]+", value or "") if len(t) >= 4]
    if not tokens or not any(t.lower() in hay for t in tokens):
        return False
    versioned = [t for t in tokens if re.search(r"\d+\.\d+", t) or re.fullmatch(r"b\d{3,}", t)]
    return all(t.lower() in hay for t in versioned)


def test_engine_min_version_backfill_traces_to_the_captured_source_text():
    """Issue #163's top-ranked gap closes with REAL data only: every structured
    `engine_min_version` in the store must be the source post's own statement of
    the build / required flags, i.e. its wording is present in the text the
    search captured for that model (`data/raw/*.json`) — and the post it came
    from is a real `…/status/<id>` URL."""

    import update_trending as UT  # noqa: E402

    store = G.load(G.STORE)
    captured = _captured_text()
    carried = [m for m in store["models"] if m.get("engine_min_version")]

    # Then  the guard is not vacuous …
    check("engine_min_version: at least one model carries a structured value",
          bool(carried), "no model carries engine_min_version")

    # … every value is evidenced by the captured text of a real post …
    unevidenced = [m.get("id") for m in carried
                   if not _engine_min_version_is_evidenced(m["engine_min_version"],
                                                           captured.get(m.get("id"), ""))]
    check("engine_min_version: every value is present in the model's captured source text",
          not unevidenced, str(unevidenced))

    # … and each such model has a real `…/status/<id>` post behind it
    untraceable = [m.get("id") for m in carried
                   if not any(UT._is_post_url(str(e.get("source_post", "")))
                              for e in (m.get("engines") or []))]
    check("engine_min_version: every value traces to a real …/status/<id> post",
          not untraceable, str(untraceable))

    # And  an invented value — one no captured snapshot mentions — is refused
    check("engine_min_version: an unsupported value fails the evidence rule",
          not _engine_min_version_is_evidenced("llama.cpp b999999, --invented-flag 7.7.7",
                                               captured.get(carried[0].get("id"), "")))


def test_engine_min_version_coverage_can_never_shrink():
    """The closed gap must not silently reopen. The dimension is carried by a
    floor of models, and the analysis reports fewer models missing it than the
    29/30 the filed issue (#163) recorded."""

    store = G.load(G.STORE)
    report = G.analyse(store, G.contract_keys(), raw_dir=G.RAW_DIR)
    n = sum(1 for m in store["models"] if m.get("engine_min_version"))
    missing = len(report["missing"]["engine_min_version"])
    # The filed 29/30 is a count over THAT model set. A refresh adds models, and
    # a brand-new model legitimately has no value yet, so the allowance is the
    # filed count plus every model added since: new models may be missing it,
    # models that already had it may never lose it (AGENTS.md rule 6b).
    allowance = 29 + max(0, len(store["models"]) - 30)

    check("engine_min_version: coverage floor holds (>= 25 models)",
          n >= 25, f"{n} models carry it")
    check("engine_min_version: no model that predates the refresh lost it "
          "(filed 29/30 + models added since)",
          missing <= allowance, f"{missing} missing (allowance {allowance})")


# A storage-offload value names a storage MEDIUM and (usually) a size. The value
# is only real when the model's captured source text says both.
_STORAGE_MEDIA = ("ssd", "nvme", "flash", "disk", "hdd")
_STORAGE_SIZE_RX = re.compile(r"\d+(?:\.\d+)?\s*(?:gb|mb|tb)", re.I)


def _storage_offload_is_evidenced(value: str, captured: str) -> bool:
    """True when the captured source text supports a `storage_offload` value:
    the value names a storage medium, the captured text names one too, every size
    token of the value appears in the text, and at least one distinctive token
    does. An invented offload ('8TB tape library') has no medium and is refused."""
    hay = (captured or "").lower()
    low = (value or "").lower()
    if not (any(med in low for med in _STORAGE_MEDIA) and any(med in hay for med in _STORAGE_MEDIA)):
        return False
    if any(s.lower() not in hay for s in _STORAGE_SIZE_RX.findall(low)):
        return False
    tokens = [t for t in re.split(r"[^A-Za-z0-9]+", low) if len(t) >= 4]
    return bool(tokens) and any(t in hay for t in tokens)


def test_storage_offload_backfill_traces_to_the_captured_source_text():
    """Issue #364's top-ranked gap closes with REAL data only: every structured
    `storage_offload` in the store must be the source post's own statement of the
    offload, i.e. its storage medium and every size token are present in the text
    the search captured for that model (`data/raw/*.json`) — and the post it came
    from is a real `…/status/<id>` URL."""

    import update_trending as UT  # noqa: E402

    store = G.load(G.STORE)
    captured = _captured_text()
    carried = [m for m in store["models"] if m.get("storage_offload")]

    # Then  the guard is not vacuous …
    check("storage_offload: at least one model carries a structured value",
          bool(carried), "no model carries storage_offload")

    # … every value is evidenced by the captured text of a real post …
    unevidenced = [m.get("id") for m in carried
                   if not _storage_offload_is_evidenced(m["storage_offload"],
                                                        captured.get(m.get("id"), ""))]
    check("storage_offload: every value is present in the model's captured source text",
          not unevidenced, str(unevidenced))

    # … and each such model has a real `…/status/<id>` post behind it
    untraceable = [m.get("id") for m in carried
                   if not any(UT._is_post_url(str(e.get("source_post", "")))
                              for e in (m.get("engines") or []))]
    check("storage_offload: every value traces to a real …/status/<id> post",
          not untraceable, str(untraceable))

    # And  an invented value — one no captured snapshot mentions — is refused
    check("storage_offload: an unsupported value fails the evidence rule",
          not _storage_offload_is_evidenced("8TB tape library, experts streamed",
                                            captured.get(carried[0].get("id"), "")),
          "a value naming no captured storage medium was accepted")


def test_storage_offload_coverage_can_never_shrink():
    """The closed gap must not silently reopen. The dimension is carried by a
    floor of models, and the analysis reports fewer models missing it than the
    41/49 the filed issue (#364) recorded."""

    store = G.load(G.STORE)
    report = G.analyse(store, G.contract_keys(), raw_dir=G.RAW_DIR)
    n = sum(1 for m in store["models"] if m.get("storage_offload"))
    missing = len(report["missing"]["storage_offload"])
    # Same allowance as engine_min_version: the filed 41/49 is a count over the
    # model set of that day, so models added since may lack the value while the
    # older ones may never lose it.
    allowance = 41 + max(0, len(store["models"]) - 49)

    check("storage_offload: coverage floor holds (>= 9 models)",
          n >= 9, f"{n} models carry it")
    check("storage_offload: no model that predates the refresh lost it "
          "(filed 41/49 + models added since)",
          missing <= allowance, f"{missing} missing (allowance {allowance})")


MEASUREMENT_DIMENSIONS = ("weight_gb", "context_tokens", "system_ram_min",
                          "storage_offload", "engine_min_version")


def _captured_raw_text() -> dict[str, str]:
    """Every text field of every captured raw model, per model id — the record of the
    real `…/status/<id>` posts the search acquired."""
    text: dict[str, list[str]] = {}
    for path in sorted((ROOT / "data" / "raw").glob("*.json")):
        data = json.loads(path.read_text())
        for m in data.get("models", []):
            mid = m.get("id")
            if not mid:
                continue
            parts = text.setdefault(mid, [])
            parts += [str(m.get(k, "")) for k in ("why", "quant", "hardware")]
            for e in m.get("engines", []):
                parts += [str(e.get(k, "")) for k in
                          ("quant", "hardware", *MEASUREMENT_DIMENSIONS)]
    return {mid: " ".join(p) for mid, p in text.items()}


def test_measurement_dimensions_trace_to_the_captured_snapshot():
    """Every per-measurement dimension value in the store is the captured post's own
    wording — a value no raw snapshot states is a fabrication."""
    store = json.loads((ROOT / "data" / "models.json").read_text())
    text = _captured_raw_text()
    invented = []
    for m in store["models"]:
        hay = text.get(m["id"], "")
        for e in m.get("engines", []):
            for k in MEASUREMENT_DIMENSIONS:
                v = e.get(k)
                if v and str(v) not in hay:
                    invented.append(f"{m['id']}/{e.get('engine')}:{k}={v!r}")
    check("traceability: every measurement dimension value appears in the captured text",
          invented == [], invented[:5])


def test_measurement_dimension_coverage_can_never_shrink():
    """A floor on measurements carrying a structured dimension, so a regeneration
    that drops the backfill cannot pass silently."""
    store = json.loads((ROOT / "data" / "models.json").read_text())
    carrying = sum(1 for m in store["models"] for e in m.get("engines", [])
                   if any(e.get(k) for k in MEASUREMENT_DIMENSIONS))
    check("coverage: at least 46 measurements carry a structured dimension "
          "(the merge/backfill cannot silently regress)", carrying >= 46, carrying)
    # PER DIMENSION, the same floor: a single dimension's backfill must not be
    # droppable while the total still passes on the other four.
    floors = {"weight_gb": 26, "context_tokens": 18, "system_ram_min": 24,
              "storage_offload": 2, "engine_min_version": 14}
    for k, floor in floors.items():
        n = sum(1 for m in store["models"] for e in m.get("engines", []) if e.get(k))
        check(f"coverage: at least {floor} measurements carry {k}", n >= floor, str(n))


def _captured_measurement_values() -> dict[tuple[str, str, str], dict[str, set[str]]]:
    """Per (model id, source_post, engine), the dimension values the captured
    snapshots (`data/raw/*.json`) state for that run — the record of the real
    `…/status/<id>` post the search acquired.

    Keyed by the MODEL the snapshot recorded it for, not by the post alone: one
    post is sometimes captured under two models (measured: a Bonsai 2 27B run's
    `4221` context sits under `qwen3.8-27b` in one leg), and copying a value
    across models is exactly the fabrication this stage must never make. Several
    legs may capture the same run, so a value is a set: they do not always agree
    on the wording."""
    out: dict[tuple[str, str, str], dict[str, set[str]]] = {}
    for path in sorted((ROOT / "data" / "raw").glob("*.json")):
        for m in json.loads(path.read_text()).get("models", []):
            mid = m.get("id")
            if not mid:
                continue
            for e in m.get("engines", []) or []:
                post, engine = str(e.get("source_post", "")), e.get("engine")
                if not post or not engine:
                    continue
                for k in MEASUREMENT_DIMENSIONS:
                    if e.get(k):
                        out.setdefault((mid, post, engine), {}).setdefault(k, set()).add(str(e[k]))
    return out


def _restates_a_captured_wording(stored: object, values: set[str]) -> bool:
    """True when a stored dimension value restates one of the wordings the
    captured legs give for the same run.

    The legs do not always phrase one figure identically — the same R9700 run is
    `llama.cpp with MTP=2` in one snapshot and `MTP=2` in the next, and
    `llama.cpp PR #27342 (DFlash 2 speculative decoding, …)` beside
    `DFlash 2 speculative decoding, PR #27342`. Exact wording is the common
    case; a stored value carrying EVERY token of a captured wording just keeps
    more of the post (the engine name, the caveat), which is not a loss. A store
    that dropped or replaced the value still fails, because its tokens are gone.
    """
    s = str(stored or "").lower()
    if not s:
        return False
    for v in values:
        vv = str(v).lower()
        if vv == s:
            return True
        tokens = [t for t in re.split(r"[^a-z0-9]+", vv) if len(t) >= 2]
        if tokens and all(t in s for t in tokens):
            return True
    return False


def _lost_captured_footprints(models: list[dict],
                              stated: dict[tuple[str, str, str], dict[str, set[str]]]
                              ) -> tuple[int, list[str]]:
    """The captured dimension values NO matching store measurement carries.

    A captured value the store dropped is a silent LOSS of real data
    (AGENTS.md §2.3b: loss is a defect, not a simplification) — and it is the
    gap the filed issue reports ("real data the search sees and the store does
    not capture"). A value the legs disagree on is satisfied by ANY of the
    wordings the captured post states."""
    rows: dict[tuple[str, str, str], list[dict]] = {}
    for m in models:
        for e in m.get("engines", []) or []:
            rows.setdefault((str(m.get("id", "")), str(e.get("source_post", "")),
                             e.get("engine")), []).append(e)
    checked = 0
    lost: list[str] = []
    for (mid, post, engine), dims in stated.items():
        stored = rows.get((mid, post, engine))
        if not stored:
            continue
        for k, values in dims.items():
            checked += 1
            if not any(_restates_a_captured_wording(r.get(k), values) for r in stored):
                lost.append(f"{mid}/{engine}/{k} on {post.rsplit('/', 1)[-1]} "
                            f"(captured {sorted(values)})")
    return checked, lost


def test_a_captured_measurement_footprint_is_never_lost_from_the_store():
    """The store carries every per-run dimension value the search captured.

    Issue #395's own words: the gap is "real data the search sees and the store
    does not capture". Measured on the store BEFORE this change: three captured
    cells belonged to a run whose store measurement carried nothing at all — the
    oMLX and mlx-serve runs' `engine_min_version` on `qwen3.8-27b` and
    `bonsai-2-2b`'s `0.43GB ternary` weight footprint."""

    store = json.loads((ROOT / "data" / "models.json").read_text())
    stated = _captured_measurement_values()
    checked, lost = _lost_captured_footprints(store["models"], stated)

    # Then  the guard is not vacuous …
    check("captured footprints: the guard compares real captured cells", checked > 0, str(checked))

    # … the store carries every one of them …
    check("captured footprints: no captured dimension value is missing from the store",
          lost == [], str(lost[:5]))

    # … and the rule BITES: a store stripped of a captured value is reported
    stripped = json.loads(json.dumps(store["models"]))
    rows = {(str(m.get("id", "")), str(e.get("source_post", "")), e.get("engine"))
            for m in stripped for e in m.get("engines", []) or []}
    candidates = [(key, dims) for key, dims in sorted(stated.items()) if key in rows and dims]
    check("captured footprints: the evidence-keyed pairs exist in the store",
          bool(candidates), "no (model, post, engine) pair matched")
    (mid, post, engine), dims = candidates[0]
    key = sorted(dims)[0]
    for m in stripped:
        for e in m.get("engines", []) or []:
            if (str(m.get("id", "")), str(e.get("source_post", "")), e.get("engine")) == (mid, post, engine):
                e.pop(key, None)
    _, caught = _lost_captured_footprints(stripped, stated)
    check("captured footprints: a store that dropped the value fails the guard",
          any(f"{mid}/{engine}/{key}" in c for c in caught), str(caught[:3]))


def main() -> int:
    print("data-gap analysis: unit tests")
    test_contract_gap_vs_stored_dimension()
    test_free_text_mention_is_unstructured_not_present()
    test_a_measurement_level_value_is_captured()
    test_a_storage_offload_needs_a_medium_and_an_offload()
    test_a_capacity_mention_is_not_an_unstructured_weights_figure()
    test_an_engine_note_is_not_per_model_prose_evidence()
    test_a_context_window_needs_a_figure()
    test_flash_attention_is_not_a_storage_medium()
    test_a_vram_capacity_is_not_a_weights_figure_even_beside_gguf()
    test_the_real_store_reports_only_figures_it_can_point_at()
    test_signature_tracks_the_store_not_the_noise()
    with tempfile.TemporaryDirectory() as td:
        test_one_issue_per_changed_gap_set(Path(td))
    with tempfile.TemporaryDirectory() as td:
        test_write_baseline_records_the_signature_without_filing(Path(td))
    test_real_store_dimensions_are_capturable_and_partly_filled()
    test_structured_dimensions_trace_to_a_real_post()
    test_every_dimension_is_a_declared_optional_key()
    test_ingest_merge_list_covers_every_declared_dimension()
    test_analysis_is_wired_to_make_and_the_refresh_pipeline()
    test_a_gap_set_is_filed_once()
    test_a_filed_issue_carries_the_label_the_bots_trigger_on()
    test_the_filer_creates_the_label_the_bots_trigger_on()
    test_engine_min_version_backfill_traces_to_the_captured_source_text()
    test_engine_min_version_coverage_can_never_shrink()
    test_storage_offload_backfill_traces_to_the_captured_source_text()
    test_storage_offload_coverage_can_never_shrink()
    test_measurement_dimensions_trace_to_the_captured_snapshot()
    test_measurement_dimension_coverage_can_never_shrink()
    test_a_captured_measurement_footprint_is_never_lost_from_the_store()
    print(f"\nPASSED {_PASS} | FAILED {_FAIL}")
    return 1 if _FAIL else 0


if __name__ == "__main__":
    raise SystemExit(main())
