#!/usr/bin/env python3
"""A measurement names a different model than the row it is stored on (tech-debt #456/#468).

`data/models.json` -> `qwen-3.6-27b`, measurement `llama.cpp` 140 t/s on `RTX 5090 32GB`:
its `quant` reads "Qwen 3.5 35B served through LM Studio anthropic-compatible endpoint
(v1/messages), 80k context, model fully in VRAM" — the run is Qwen 3.5 35B, not Qwen 3.6
27B. A misplaced measurement inflates the row's t/s and its `posts_7d` signal, and
AGENTS.md §3 requires every figure to trace to a `…/status/<id>` post about THAT model.

The fix has two halves, both asserted here:

  - INGEST refuses a measurement whose captured `quant`/`why` names a different model
    than the row it would merge into (`refuse_misattributed_measurements`), or documents
    the real exception as DATA on the row's `measurement_model_aliases` key (issue #652
    replaced the old code-literal mapping; `check_measurement_alias_map` refuses a
    counterpart that is not a store model id).
  - `make validate` FAILS a measurement that relies on a placeholder `source_post` AND
    claims engagement counts (`check_post_signal`), while a low-signal static placeholder
    row stays allowed. The attribution scan itself is report-only for history.

Run:  python3 tests/test_measurement_attribution.py    or   make test
"""
from __future__ import annotations

import copy
import io
import json
import subprocess
import sys
import tempfile
from contextlib import redirect_stdout
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import update_trending as UT  # noqa: E402
import validate as V  # noqa: E402

_PASS = 0
_FAIL = 0

REAL_POST = "https://lightbrd.com/0xbelorix/status/2075607981027393583"


def check(name, cond, detail: object = ""):
    global _PASS, _FAIL
    if cond:
        _PASS += 1
        print(f"  ok  {name}")
    else:
        _FAIL += 1
        print(f"  FAIL {name}" + (f"  [{detail}]" if detail else ""))


def row(mid, name, full_name="", **kw):
    r = {"id": mid, "name": name, "full_name": full_name or name, "hf": "org/" + mid,
         "why": kw.pop("why", "w"), "engines": kw.pop("engines", [])}
    r.update(kw)
    return r


def meas(quant, why="", post=REAL_POST, **kw):
    e = {"engine": "llama.cpp", "tps": "140", "hardware": "RTX 5090 32GB", "quant": quant,
         "date": "2026-07-10", "source_post": post}
    if why:
        e["why"] = why
    e.update(kw)
    return e


def test_the_reported_measurement_is_refused():
    """The measured defect: a Qwen 3.6 27B row whose quant describes Qwen 3.5 35B."""
    m = row("qwen-3.6-27b", "Qwen 3.6 27B", "Qwen3.6-27B", engines=[
        meas("Qwen 3.5 35B served through LM Studio anthropic-compatible endpoint "
             "(v1/messages), 80k context, model fully in VRAM"),
    ])
    kept, refused = UT.refuse_misattributed_measurements(m, {"models": [m]})
    check("attribution: the Qwen 3.5 35B text on the Qwen 3.6 27B row is REFUSED",
          len(refused) == 1 and not kept, (kept, refused))
    check("attribution: the refusal names both identities",
          refused and "qwen 3.5 35b" in refused[0][1] and "qwen 3.6 27b" in refused[0][1], refused)
    check("attribution: the refusal carries the source post",
          refused and refused[0][2] == REAL_POST, refused)


def test_a_measurement_naming_its_own_row_is_kept():
    m = row("qwen3.8-27b", "Qwen 3.8 27B", "Qwen3.8-27B", engines=[
        meas("Qwen3.8-27B 4-bit, 27B dense, MLX", post="https://lightbrd.com/u/status/2"),
    ])
    kept, refused = UT.refuse_misattributed_measurements(m, {"models": [m]})
    check("attribution: a text naming the row's own model is kept", not refused and kept, refused)


def test_a_multi_model_post_naming_the_row_is_kept():
    """A post that measures THIS row's model and mentions another one is about this row."""
    m = row("qwen-3.6-27b", "Qwen 3.6 27B", "Qwen3.6-27B", engines=[
        meas("Qwen3.6 27B at Q4 via MLX (~32 tok/s with MTP); the same box runs Qwen 3.6 35B",
             post="https://lightbrd.com/u/status/3"),
    ])
    kept, refused = UT.refuse_misattributed_measurements(m, {"models": [m]})
    check("attribution: a multi-model post naming the row's model is kept",
          not refused and kept, refused)


def test_a_comparison_cue_is_kept():
    m = row("qwen-3.6-27b", "Qwen 3.6 27B", "Qwen3.6-27B", engines=[
        meas("Qwen 3.6 27B vs Qwen 3.5 35B on the same card", post="https://lightbrd.com/u/status/4"),
    ])
    kept, refused = UT.refuse_misattributed_measurements(m, {"models": [m]})
    check("attribution: a comparison sentence is kept", not refused and kept, refused)


def test_a_joint_comparison_figure_is_refused():
    """issue #651: ONE t/s figure for a comparison of two models is not attributable."""
    m = row("qwen-3.6-27b", "Qwen 3.6 27B", "Qwen3.6-27B", engines=[
        meas("Qwen 3.6 27B vs Qwen 3.5 35B: 140 t/s", post="https://lightbrd.com/u/status/61"),
    ])
    kept, refused = UT.refuse_misattributed_measurements(m, {"models": [m]})
    check("attribution: a joint single figure on a comparison is REFUSED",
          len(refused) == 1 and not kept, (kept, refused))
    check("attribution: the joint-figure reason names both identities",
          refused and "JOINT" in refused[0][1] and "qwen 3.5 35b" in refused[0][1]
          and "qwen 3.6 27b" in refused[0][1], refused)
    m2 = row("qwen-3.6-27b", "Qwen 3.6 27B", "Qwen3.6-27B", engines=[
        meas("Qwen 3.6 27B vs Qwen 3.5 35B: 60-91 t/s", post="https://lightbrd.com/u/status/62"),
    ])
    kept2, refused2 = UT.refuse_misattributed_measurements(m2, {"models": [m2]})
    check("attribution: a joint RANGE figure is refused too",
          len(refused2) == 1 and not kept2, (kept2, refused2))


def test_one_figure_per_model_is_kept():
    """A bake-off with its own figure per model stays legitimate (unchanged)."""
    m = row("qwen-3.6-27b", "Qwen 3.6 27B", "Qwen3.6-27B", engines=[
        meas("Qwen 3.6 27B 90 t/s vs Qwen 3.5 35B 40 t/s",
             post="https://lightbrd.com/u/status/63"),
    ])
    kept, refused = UT.refuse_misattributed_measurements(m, {"models": [m]})
    check("attribution: one figure per model (two figures) is kept", not refused and kept, refused)


def test_a_cross_family_mention_is_kept():
    """Cross-family mentions are comparison/context, not a same-row mix-up."""
    m = row("qwen-3.6-27b", "Qwen 3.6 27B", "Qwen3.6-27B", engines=[
        meas("Qwen3.6-27B, benchmarked beside Gemma 4 26B", post="https://lightbrd.com/u/status/5"),
    ])
    kept, refused = UT.refuse_misattributed_measurements(m, {"models": [m]})
    check("attribution: a cross-family mention is kept", not refused and kept, refused)


def test_an_unknown_identity_fails_open():
    """A variant name with words between version and size cannot prove a refusal."""
    m = row("qwen3.8-flash-next-125b", "Qwen3.8-Flash-Next 125B",
            "Qwen3.8-Flash-Next 125B", engines=[
                meas("Qwen3.8-27B served beside it", post="https://lightbrd.com/u/status/6"),
            ])
    kept, refused = UT.refuse_misattributed_measurements(m, {"models": [m]})
    check("attribution: an unparseable row identity fails open", not refused and kept, refused)


def test_an_explicit_alias_mapping_documents_an_exception():
    """The exception is DATA on the row (issue #652), never a code literal."""
    base = row("bonsai-2-27b", "Bonsai 2 27B")
    plain = row("bonsai-2-9b", "Bonsai 2 9B", engines=[
        meas("ternary Bonsai 2 27B beside the 9B", post="https://lightbrd.com/u/status/7"),
    ])
    mapped = row("bonsai-2-9b", "Bonsai 2 9B", measurement_model_aliases=["bonsai-2-27b"],
                 engines=[meas("ternary Bonsai 2 27B beside the 9B",
                               post="https://lightbrd.com/u/status/7")])
    store_plain = {"models": [base, plain]}
    kept, refused = UT.refuse_misattributed_measurements(plain, store_plain)
    check("attribution: without the data key the different size is refused",
          bool(refused), refused)
    check("attribution: the refusal names the data key a human can add",
          refused and "measurement_model_aliases" in refused[0][1], refused)
    store_mapped = {"models": [base, mapped]}
    kept, refused = UT.refuse_misattributed_measurements(mapped, store_mapped)
    check("attribution: the row's measurement_model_aliases documents the exception",
          not refused and kept, refused)
    # a NEW raw row inherits the exception already reviewed into the store row
    incoming = {k: v for k, v in mapped.items() if k != "measurement_model_aliases"}
    kept, refused = UT.refuse_misattributed_measurements(incoming, store_mapped)
    check("attribution: the same-id store row's data key carries over to a new row",
          not refused and kept, refused)


def test_attribution_exceptions_live_in_data_not_code():
    src = (ROOT / "scripts" / "update_trending.py").read_text()
    check("code: MEASUREMENT_MODEL_ALIASES is gone from the script",
          "MEASUREMENT_MODEL_ALIASES" not in src)
    check("code: the reader reads the row key",
          'def measurement_model_aliases(' in src
          and '"measurement_model_aliases"' in src)
    contract = json.loads((ROOT / "data" / "model_contract.json").read_text())
    props = contract["properties"]["models"]["items"]["properties"]
    check("contract: measurement_model_aliases is an optional model key",
          "measurement_model_aliases" in props
          and "measurement_model_aliases" not in contract["properties"]["models"]["items"].get("required", []),
          props.get("measurement_model_aliases"))


def test_alias_key_declared_in_both_contracts():
    """The pair (issue #652 + #884): the exception key is declared in BOTH
    contracts — store side and search side — identically and optionally."""
    shapes = []
    for name in ("model_contract.json", "search_contract.json"):
        c = json.loads((ROOT / "data" / name).read_text())
        item = c["properties"]["models"]["items"]
        props = item["properties"]
        check(f"{name}: declares measurement_model_aliases as a model property",
              "measurement_model_aliases" in props, sorted(props))
        check(f"{name}: the alias key is optional (never required)",
              "measurement_model_aliases" not in item.get("required", []), item.get("required"))
        shapes.append(props.get("measurement_model_aliases"))
    check("contracts: both declare the SAME structural shape for the exception key "
          "(array of store-id slugs, unique items)",
          all(s is not None and {k: v for k, v in s.items() if k in ("type", "items", "uniqueItems")}
              == {k: v for k, v in shapes[0].items() if k in ("type", "items", "uniqueItems")}
              for s in shapes)
          and shapes[1].get("minItems", 1) >= 1, shapes)


def test_ingest_calls_the_refusal():
    src = (ROOT / "scripts" / "update_trending.py").read_text()
    start = src.index("def ingest_raw_snapshots(")
    body = src[start:src.index("\ndef ", start + 10)]
    check("ingest: the refusal is called where a raw row merges",
          "refuse_misattributed_measurements(m, store)" in body, body[:200])


def test_ingest_drops_a_new_row_whose_only_measurement_is_refused():
    """A NEW row with nothing left to show is not stored broken (check_model_fields
    would fail it); the rest of the snapshot still merges."""
    raw = {
        "generated_utc": "2026-10-27T00:00:00Z", "backend": "nvidia",
        "models": [{
            "id": "qwen-3.6-27b", "name": "Qwen 3.6 27B", "full_name": "Qwen3.6-27B",
            "hf": "Qwen/Qwen3.6-27B", "license": "Apache 2.0", "params": "27B", "type": "LLM",
            "vram_tier": "18GB", "backends": ["CUDA"],
            "engines": [meas("Qwen 3.5 35B served through LM Studio "
                             "anthropic-compatible endpoint")],
        }],
    }
    store = {"generated_utc": "2026-10-01T00:00:00Z",
             "engines": {"llama.cpp": {"backend": "CUDA / CPU / Metal", "note": "n",
                                       "url": "https://github.com/ggml-org/llama.cpp"}},
             "models": []}
    td = Path(tempfile.mkdtemp())
    (td / "nvidia-test.json").write_text(json.dumps(raw))
    saved = UT.RAW_DIR
    buf = io.StringIO()
    try:
        UT.RAW_DIR = td
        with redirect_stdout(buf):
            added, updated = UT.ingest_raw_snapshots(store, since=None)
    finally:
        UT.RAW_DIR = saved
    out = buf.getvalue()
    check("ingest: a new row whose only measurement is refused is NOT stored",
          added == 0 and updated == 0 and store["models"] == [], (added, updated, store["models"]))
    check("ingest: the refusal is loud and names the model",
          "REFUSED misattributed measurement" in out and "qwen-3.6-27b" in out, out[-400:])


def test_the_shipped_store_reports_the_known_row():
    store = UT.load_store()
    mis = V.misattributed_measurements(store.get("models", []))
    check("scan: the shipped store reports the qwen-3.6-27b row",
          any("qwen-3.6-27b" in m[0] or "Qwen 3.6 27B" in m[0] for m in mis), mis[:2])
    V.FAILURES.clear()
    buf = io.StringIO()
    saved = V.RAW_DIR
    V.RAW_DIR = Path(tempfile.mkdtemp()) / "none"
    try:
        with redirect_stdout(buf):
            V.check_measurement_attribution(store)
    finally:
        V.RAW_DIR = saved
        V.FAILURES.clear()
    out = buf.getvalue()
    check("scan: it prints a WARN naming the misplaced figure",
          "WARN: measurement-attribution scan" in out and "Qwen 3.6 27B" in out, out[-400:])
    check("scan: report only — it adds no failure", not V.FAILURES, V.FAILURES)
    proc = subprocess.run([sys.executable, str(ROOT / "scripts" / "validate.py"), "--only", "data"],
                          capture_output=True, text=True, cwd=ROOT)
    check("scan: `validate --only data` prints it and still SUCCEEDS",
          "measurement-attribution scan" in proc.stdout and proc.returncode == 0,
          (proc.returncode, proc.stdout[-300:]))


# ---- issue #884: the search contract may RECORD the exception, and ingest
# carries a captured one onto the store row additively ----

#: One search-leg snapshot of a bake-off row: its measurement names a DIFFERENT
#: stored model (Gemma 3 27B) — refused without an exception — and the snapshot
#: now records the exception as data on the row, the same key the store contract
#: declares (issue #652) that the search contract previously pruned.
def _bakeoff_raw(alias_value=("gemma-3-27b",), mid="coder-bakeoff-gemma",
                 name="Coder Bakeoff Gemma", post="https://lightbrd.com/bakeoff/status/9001"):
    return {
        "backend": "nvidia",
        "generated_utc": "2026-11-13T09:00:00Z",
        "models": [{
            "id": mid, "name": name, "full_name": "Coder-Bakeoff-Gemma",
            "type": "LLM", "license": "MIT", "params": "27B", "hf": "org/coder-bakeoff-gemma",
            "vram_tier": "24GB", "vram_min": "18GB", "backends": ["CUDA"],
            "why": "bake-off", "last_seen": "2026-11-13",
            "engagement": {"likes": 42, "comments": 3, "views": 5000},
            "engines": [meas("Gemma 3 27B QAT llama.cpp 41 t/s RTX 4090 24GB",
                             post=post, tps="41", hardware="RTX 4090 24GB")],
            "measurement_model_aliases": list(alias_value),
        }],
    }


def _alias_store():
    """A store holding the counterpart model (and, for the union test, a second one)."""
    return {"generated_utc": "2026-11-01T00:00:00Z",
            "engines": {"llama.cpp": {"backend": "CUDA / CPU / Metal", "note": "n",
                                      "url": "https://github.com/ggml-org/llama.cpp"}},
            "models": [
                row("gemma-3-27b", "Gemma 3 27B", full_name="Gemma-3-27B",
                    engines=[meas("QAT 4bit", post="https://lightbrd.com/base/status/8001",
                                  tps="39", hardware="RTX 4080 16GB")]),
                row("mistral-small-3.2", "Mistral Small 3.2", full_name="Mistral-Small-3.2",
                    engines=[meas("instruct 24bit", post="https://lightbrd.com/mistral/status/8002",
                                  tps="55", hardware="RTX 5080 16GB")]),
            ]}


def _write_raw_dir(tmp, raw, fname="nvidia-20261113T090000Z.json"):
    raw_dir = Path(tmp) / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    (raw_dir / fname).write_text(json.dumps(raw))
    return raw_dir


def test_raw_snapshot_carrying_the_exception_conforms():
    """The search stage no longer prunes the exception key: a snapshot carrying a
    resolvable counterpart conforms; a malformed one is REFUSED by the contract."""
    def contract_failures(raw_dir):
        saved = V.RAW_DIR
        V.RAW_DIR = raw_dir
        V.FAILURES.clear()
        try:
            V.check_search_contract()
            failures = list(V.FAILURES)
        finally:
            V.FAILURES.clear()
            V.RAW_DIR = saved
        return failures

    with tempfile.TemporaryDirectory() as tmp:
        failures = contract_failures(_write_raw_dir(tmp, _bakeoff_raw()))
        check("search contract: a snapshot carrying the exception conforms (not pruned)",
              failures == [], failures)
    with tempfile.TemporaryDirectory() as tmp:
        # empty array violates minItems; a non-slug counterpart violates the id pattern
        failures = contract_failures(_write_raw_dir(tmp, _bakeoff_raw(alias_value=())))
        check("search contract: an empty alias array is refused", bool(failures), failures)
    with tempfile.TemporaryDirectory() as tmp:
        failures = contract_failures(_write_raw_dir(tmp, _bakeoff_raw(alias_value=("Bad ID",))))
        check("search contract: a non-slug counterpart is refused", bool(failures), failures)


def test_new_model_keeps_captured_exception():
    """A NEW model captured WITH the exception keeps the key on its store row, and
    its aliased measurement merges instead of being refused (the exclusion is read
    from the row, issue #652)."""
    store = _alias_store()
    with tempfile.TemporaryDirectory() as tmp:
        raw_dir = _write_raw_dir(tmp, _bakeoff_raw())
        saved = UT.RAW_DIR
        try:
            UT.RAW_DIR = raw_dir
            added, updated = UT.ingest_raw_snapshots(store, since=None)
        finally:
            UT.RAW_DIR = saved
    check("ingest: the aliased new model merges (its measurement is NOT refused)",
          added == 1 and updated == 0, (added, updated))
    new = next(m for m in store["models"] if m["id"] == "coder-bakeoff-gemma")
    check("ingest: the new row keeps the captured exception as data",
          new.get("measurement_model_aliases") == ["gemma-3-27b"],
          new.get("measurement_model_aliases"))
    check("ingest: the aliased measurement landed on the row",
          any(e.get("tps") == "41" for e in new["engines"]), new["engines"])


def test_existing_row_gains_aliases_additively():
    """An EXISTING store row gains a newly captured counterpart as a UNION: what
    the row already documented is kept, the new one is added, nothing shrinks
    (rule 3b), and the gain is loud."""
    store = _alias_store()
    store["models"].append(row(
        "coder-bakeoff-gemma", "Coder Bakeoff Gemma", full_name="Coder-Bakeoff-Gemma",
        measurement_model_aliases=["gemma-3-27b"],
        engines=[meas("QAT llama.cpp", post="https://lightbrd.com/bakeoff/status/7001",
                      tps="41", hardware="RTX 4090 24GB")]))
    # the same row captured again, now naming the Mistral counterpart too
    raw = _bakeoff_raw(alias_value=("gemma-3-27b", "mistral-small-3.2"),
                       post="https://lightbrd.com/bakeoff/status/9001")
    raw["models"][0]["engines"] = [meas(
        "Gemma 3 27B and Mistral Small 3.2 both measured, llama.cpp 44 t/s RTX 4090 24GB",
        post="https://lightbrd.com/bakeoff/status/9001", tps="44", hardware="RTX 4090 24GB")]
    with tempfile.TemporaryDirectory() as tmp:
        raw_dir = _write_raw_dir(tmp, raw)
        saved = UT.RAW_DIR
        buf = io.StringIO()
        try:
            UT.RAW_DIR = raw_dir
            with redirect_stdout(buf):
                _added, updated = UT.ingest_raw_snapshots(store, since=None)
        finally:
            UT.RAW_DIR = saved
    existing = next(m for m in store["models"] if m["id"] == "coder-bakeoff-gemma")
    out = buf.getvalue()
    check("ingest: the existing row was updated (not duplicated)", updated == 1, updated)
    check("ingest: aliases are UNIONED — old kept, new added, none removed",
          existing.get("measurement_model_aliases") == ["gemma-3-27b", "mistral-small-3.2"],
          existing.get("measurement_model_aliases"))
    check("ingest: the alias gain is loud",
          "measurement_model_aliases gained" in out and "mistral-small-3.2" in out, out[-300:])
    # a capture WITHOUT the key never clears what the row documents
    store2 = _alias_store()
    store2["models"].append(row("coder-bakeoff-gemma", "Coder Bakeoff Gemma",
                                measurement_model_aliases=["gemma-3-27b"],
                                engines=[meas("plain", post="https://lightbrd.com/bakeoff/status/7002")]))
    raw_noalias = _bakeoff_raw()
    del raw_noalias["models"][0]["measurement_model_aliases"]
    with tempfile.TemporaryDirectory() as tmp:
        raw_dir = _write_raw_dir(tmp, raw_noalias, fname="nvidia-20261113T090001Z.json")
        saved = UT.RAW_DIR
        try:
            UT.RAW_DIR = raw_dir
            UT.ingest_raw_snapshots(store2, since=None)
        finally:
            UT.RAW_DIR = saved
    kept = next(m for m in store2["models"] if m["id"] == "coder-bakeoff-gemma")
    check("ingest: a capture without the key never narrows the row",
          kept.get("measurement_model_aliases") == ["gemma-3-27b"],
          kept.get("measurement_model_aliases"))


def test_the_shipped_joint_figure_is_documented_as_data():
    """Issue #650: the joint figure on the shipped Qwen3.6-35B-A3B row (its
    llama.cpp 33 t/s and vLLM 309 t/s posts compare it against Qwen3.8-27B) is
    exempted by the exception carried on the DATA row, not by a code literal."""
    store = UT.load_store()
    rows = {m.get("id"): m for m in store.get("models", [])}
    aliases = rows.get("qwen3.6-35b-a3b", {}).get("measurement_model_aliases")
    check(isinstance(aliases, list) and "qwen3.8-27b" in aliases,
          "alias: the shipped 35B-A3B row carries the qwen3.8-27b exception", aliases)
    check("qwen3.8-27b" in rows,
          "gate: the exception's counterpart is a model id in the store")
    mis = V.misattributed_measurements(store.get("models", []))
    check(not any("Qwen3.6-35B-A3B" in m[0] or "qwen3.6-35b-a3b" in m[0] for m in mis),
          "scan: the documented joint figure is no longer an attribution WARN",
          [m[0] for m in mis])
    check(any("qwen-3.6-27b" in m[0] or "Qwen 3.6 27B" in m[0] for m in mis),
          "scan: the owner-undecided Qwen 3.6 27B misattribution is still reported "
          "(rule 3b removal awaits the owner ruling on issue #650)")
    out = io.StringIO()
    try:
        with redirect_stdout(out):
            V.check_measurement_alias_map(copy.deepcopy(store))
        alias_ok = "measurement alias map resolves" in out.getvalue()
    except SystemExit:
        alias_ok = False
    check(alias_ok, "gate: the shipped alias passes the counterpart check",
          out.getvalue()[:200])


def main() -> int:
    print("measurement attribution: a measurement naming another model (tech-debt #456/#468)")
    test_the_reported_measurement_is_refused()
    test_a_measurement_naming_its_own_row_is_kept()
    test_a_multi_model_post_naming_the_row_is_kept()
    test_a_comparison_cue_is_kept()
    test_a_joint_comparison_figure_is_refused()
    test_one_figure_per_model_is_kept()
    test_a_cross_family_mention_is_kept()
    test_an_unknown_identity_fails_open()
    test_an_explicit_alias_mapping_documents_an_exception()
    test_attribution_exceptions_live_in_data_not_code()
    test_alias_key_declared_in_both_contracts()
    test_ingest_calls_the_refusal()
    test_ingest_drops_a_new_row_whose_only_measurement_is_refused()
    test_the_shipped_store_reports_the_known_row()
    test_raw_snapshot_carrying_the_exception_conforms()
    test_new_model_keeps_captured_exception()
    test_existing_row_gains_aliases_additively()
    test_the_shipped_joint_figure_is_documented_as_data()
    print(f"\nPASSED {_PASS} | FAILED {_FAIL}")
    return 1 if _FAIL else 0


if __name__ == "__main__":
    raise SystemExit(main())
