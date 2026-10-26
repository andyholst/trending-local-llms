#!/usr/bin/env python3
"""An un-derivable model row is QUARANTINED, never fatal to the whole refresh.

Measured on scheduled refresh-bot run 39159853260 (2026-10-18): all four search
legs went green, then the `aggregate` job died at `make correct-raw` because ONE
model in the captured raw snapshots had no derivable `hf`:

    CANNOT_DERIVE: qwen3.8-flash-next-125b: hf missing (cannot derive); …
    SELF-CORRECT INCOMPLETE: some fields (hf/source_post) cannot be derived — re-search needed.
    make: *** [Makefile:_correct-raw] Error 1

so no PR was opened and four legs of good data were discarded. Proves the two
states are now DISTINCT:

  1. A snapshot that carries an un-derivable model still conforms afterwards: the
     row is excluded, reported by name with its source posts, and the command
     exits 0 — the rest of the capture merges (issue #381).
  2. A model already in the store is REPAIRED from it (`hf <- store`) instead of
     dropped, so a known model's new measurements are never lost.
  3. A measurement with no `source_post` is dropped loudly; a model left with no
     attributed measurement is quarantined too.
  4. Only a capture where NOTHING could be read fails the step (a re-search is
     genuinely needed); one unreadable file beside readable ones is loud, not fatal.
  5. Ingest refuses a NEW model whose `hf` is empty (loudly, naming the snapshot)
     and keeps the rest of the merge, even when the merge runs before
     `correct-raw` — while an EXISTING model still merges and keeps its `hf`.

Run:  python3 tests/test_raw_quarantine.py   or   make test
"""
from __future__ import annotations

import contextlib
import io
import json
import os
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "tests"))

import self_correct_raw as SC  # noqa: E402
import update_trending as UT  # noqa: E402
from wiring import wired  # noqa: E402  (issues #176/#192)

_PASS = 0
_FAIL = 0

POST_A = "https://lightbrd.com/alice/status/1001"
POST_B = "https://lightbrd.com/bob/status/2002"


def check(name, cond, detail=""):
    global _PASS, _FAIL
    if cond:
        _PASS += 1
        print(f"  ok  {name}")
    else:
        _FAIL += 1
        print(f"  FAIL {name}" + (f"  [{detail}]" if detail else ""))


# ------------------------------------------------------------------ fixtures --

_AS_WRITTEN = object()


def raw_model(mid: str, hf=_AS_WRITTEN, post: str = POST_A) -> dict:
    """A contract-conformant raw row. Omitting `hf` means 'as the search wrote
    it'; `hf=None` omits the key entirely (the measured shape); `hf=""` writes blank."""
    m = {
        "id": mid, "name": mid, "full_name": mid, "type": "LLM",
        "license": "Apache 2.0", "params": "8B",
        "vram_tier": "8GB", "vram_min": "8GB", "backends": ["CUDA"],
        "engines": [{"engine": "llama.cpp", "tps": "40", "hardware": "RTX 3060",
                     "quant": "Q4", "date": "2026-10-20", "source_post": post}],
        "last_seen": "2026-10-20",
    }
    if hf is _AS_WRITTEN:
        m["hf"] = "org/" + mid
    elif hf is not None:
        m["hf"] = hf
    return m


def snapshot(models: list[dict], backend: str = "nvidia",
             stamp: str = "2026-10-20T12:00:00Z") -> dict:
    return {"backend": backend, "generated_utc": stamp, "models": models}


def base_store() -> dict:
    """A small but contract-shaped store: one model WITH an hf (the repair path)
    and the engine registry the correction reads backends from."""
    return {
        "generated_utc": "2026-10-19T00:00:00Z",
        "engines": {"llama.cpp": {"backend": "CUDA", "note": "x",
                                  "url": "https://github.com/ggml-org/llama.cpp"}},
        "models": [{
            "id": "qwen3.6-27b", "name": "Qwen3.6 27B", "full_name": "Qwen3.6-27B",
            "type": "LLM", "hf": "Qwen/Qwen3.6-27B",
            "formats": [{"name": "GGUF", "hf": "Qwen/Qwen3.6-27B"}],
            "license": "Apache 2.0", "params": "27B",
            "vram_tier": "16GB", "vram_min": "12GB", "backends": ["CUDA"],
            "supported_engines": ["llama.cpp"],
            "engines": [{"engine": "llama.cpp", "tps": "30", "hardware": "RTX 3060",
                         "quant": "Q4", "date": "2026-10-19", "source_post": POST_A}],
            "why": "w",
            "engagement": {"likes": 1, "comments": 0, "views": 2, "last_7d_likes": 1},
            "last_seen": "2026-10-19",
        }],
    }


def search_contract() -> dict:
    return json.loads((ROOT / "data" / "search_contract.json").read_text())


def conforms(payload: dict) -> tuple[bool, str]:
    import jsonschema
    try:
        jsonschema.validate(payload, search_contract())
        return True, ""
    except Exception as e:  # noqa: BLE001
        return False, str(e)


def run_correct_raw(data_dir: Path) -> subprocess.CompletedProcess:
    """Drive the REAL command the aggregate runs (`make _correct-raw` is a bare
    `python3 scripts/self_correct_raw.py`), against a temp data dir."""
    env = dict(os.environ, TRENDING_DATA_DIR=str(data_dir))
    return subprocess.run([sys.executable, str(ROOT / "scripts" / "self_correct_raw.py")],
                          cwd=str(ROOT), env=env, capture_output=True, text=True,
                          timeout=300)


def utc(s: str) -> datetime:
    return datetime.strptime(s, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)


def ingest(store: dict, raws: dict[str, dict], since=None) -> tuple[int, int, str]:
    """Point UT.RAW_DIR at a temp dir of raw snapshots and run the REAL ingest."""
    with tempfile.TemporaryDirectory() as td:
        rdir = Path(td)
        for name, payload in raws.items():
            (rdir / name).write_text(json.dumps(payload))
        saved = UT.RAW_DIR
        UT.RAW_DIR = rdir
        buf = io.StringIO()
        try:
            with contextlib.redirect_stdout(buf):
                counts = UT.ingest_raw_snapshots(store, since=since)
        finally:
            UT.RAW_DIR = saved
    return counts[0], counts[1], buf.getvalue()


def ids(store: dict) -> set[str]:
    return {m["id"] for m in store["models"]}


# ------------------------------------------------------------ the quarantine --

def test_an_underivable_model_is_quarantined_and_the_rest_merges():
    """The measured failure (run 39159853260): one hf-less model beside a good one
    must not discard the snapshot, and the file must still conform."""
    with tempfile.TemporaryDirectory() as td:
        d = Path(td)
        (d / "raw").mkdir()
        (d / "models.json").write_text(json.dumps(base_store()))
        snap = d / "raw" / "nvidia-20261020-120000.json"
        snap.write_text(json.dumps(snapshot([
            raw_model("good-model", post=POST_A),
            raw_model("sloppy-model", hf=None, post=POST_B),
        ])))

        proc = run_correct_raw(d)
        after = json.loads(snap.read_text())

        check("quarantine: the step SUCCEEDS (exit 0) — it used to exit 1", proc.returncode == 0,
              proc.stdout[-600:] + proc.stderr[-400:])
        check("quarantine: the good model is still captured",
              [m["id"] for m in after["models"]] == ["good-model"],
              [m["id"] for m in after["models"]])
        check("quarantine: the hf-less row is excluded", "sloppy-model" not in
              [m["id"] for m in after["models"]], after["models"])
        reported = [ln for ln in proc.stdout.splitlines() if "QUARANTINED:" in ln]
        check("quarantine: ONE loud line names the model", len(reported) == 1, reported)
        check("quarantine: the report names the model, the reason and its post",
              bool(reported) and "sloppy-model" in reported[0]
              and "hf missing (cannot derive)" in reported[0] and POST_B in reported[0],
              reported)
        check("quarantine: it says the rest of the capture still merges",
              bool(reported) and "still merges" in reported[0], reported)

        ok, why = conforms(after)
        check("quarantine: the remaining snapshot conforms to search_contract.json", ok, why)

        # A second run rewrites nothing and quarantines nothing.
        before = snap.read_text()
        proc2 = run_correct_raw(d)
        check("quarantine: idempotent — a second run is clean and rewrites nothing",
              proc2.returncode == 0 and "QUARANTINED:" not in proc2.stdout
              and snap.read_text() == before,
              proc2.stdout[-400:])


def test_a_known_model_is_repaired_from_the_store():
    """A stored model HAS its hf: take it from there, so a missing field never
    costs the measurements this capture DID attribute."""
    with tempfile.TemporaryDirectory() as td:
        snap = Path(td) / "amd-20261020-120000.json"
        row = raw_model("qwen3.6-27b", hf=None, post=POST_B)
        row["engines"].append({"engine": "vLLM", "tps": "55", "hardware": "RX 7900 XTX",
                               "quant": "FP8", "date": "2026-10-20", "source_post": POST_B})
        snap.write_text(json.dumps(snapshot([row], backend="amd")))

        notes = SC.correct_snapshot(snap, base_store())
        after = json.loads(snap.read_text())
        kept = after["models"][0]

        check("repair: the row is KEPT (a known model is not quarantined)",
              [m["id"] for m in after["models"]] == ["qwen3.6-27b"], after["models"])
        check("repair: hf comes from the store", kept.get("hf") == "Qwen/Qwen3.6-27B",
              kept.get("hf"))
        check("repair: the report says where it came from",
              any("hf <- store 'Qwen/Qwen3.6-27B'" in n for n in notes), notes)
        check("repair: no QUARANTINED line is produced",
              not any(n.startswith("QUARANTINED:") for n in notes), notes)
        check("repair: BOTH measurements survive",
              [e["engine"] for e in kept["engines"]] == ["llama.cpp", "vLLM"],
              kept["engines"])


def test_a_measurement_without_a_post_is_dropped():
    """A t/s with no post cannot be attributed (rule 5b): drop THAT row loudly and
    keep the model; the model goes only when no attributed measurement remains."""
    with tempfile.TemporaryDirectory() as td:
        path = Path(td) / "metal-20261020-120000.json"
        row = raw_model("good-model", post=POST_A)
        row["engines"].append({"engine": "MLX", "tps": "22", "hardware": "Apple M4",
                               "quant": "4bit", "date": "2026-10-20"})  # no source_post
        path.write_text(json.dumps(snapshot([row], backend="metal")))

        notes = SC.correct_snapshot(path, base_store())
        kept = json.loads(path.read_text())["models"][0]
        check("measurement: the model survives with its attributed measurement",
              kept["id"] == "good-model" and [e["engine"] for e in kept["engines"]]
              == ["llama.cpp"], kept["engines"])
        check("measurement: the dropped row is reported by engine name",
              any("dropped measurement 'MLX'" in n for n in notes), notes)
        check("measurement: no quarantine is reported for a rescued model",
              not any(n.startswith("QUARANTINED:") for n in notes), notes)

    # Given a model whose ONLY measurement carries no post
    with tempfile.TemporaryDirectory() as td:
        path = Path(td) / "cpu-20261020-120000.json"
        row = raw_model("orphan-model", post=POST_A)
        row["engines"][0].pop("source_post")
        path.write_text(json.dumps(snapshot([row], backend="cpu")))
        notes = SC.correct_snapshot(path, base_store())
        after = json.loads(path.read_text())
        q = [n for n in notes if n.startswith("QUARANTINED:")]
        check("measurement: a model left with no attributed figure is quarantined",
              after["models"] == [] and len(q) == 1 and "orphan-model" in q[0]
              and "no measurement with a source_post" in q[0], notes)


def test_a_capture_where_no_snapshot_can_be_read_is_the_unusable_state():
    """ONE unreadable file is not the capture; NOTHING readable is (a re-search)."""
    with tempfile.TemporaryDirectory() as td:
        d = Path(td)
        (d / "raw").mkdir()
        (d / "models.json").write_text(json.dumps(base_store()))
        (d / "raw" / "broken.json").write_text("{not json at all")
        (d / "raw" / "nvidia-20261020-120000.json").write_text(json.dumps(snapshot(
            [raw_model("good-model"), raw_model("sloppy-model", hf=None, post=POST_B)])))
        proc = run_correct_raw(d)
        check("unreadable: one corrupt file beside readable ones exits 0",
              proc.returncode == 0, proc.stdout[-500:])
        check("unreadable: the corrupt file is reported loudly, not silently skipped",
              "UNREADABLE broken.json" in proc.stdout, proc.stdout[-500:])
        check("unreadable: the readable snapshot was still corrected (quarantine report)",
              "QUARANTINED: nvidia-20261020-120000.json/sloppy-model" in proc.stdout,
              proc.stdout[-600:])

    with tempfile.TemporaryDirectory() as td:
        d = Path(td)
        (d / "raw").mkdir()
        (d / "models.json").write_text(json.dumps(base_store()))
        (d / "raw" / "a.json").write_text("{broken")
        (d / "raw" / "b.json").write_text("also not json")
        proc = run_correct_raw(d)
        check("unusable: a capture where NOTHING can be read fails (needs a re-search)",
              proc.returncode == 1 and "SELF-CORRECT INCOMPLETE" in proc.stdout,
              proc.stdout[-400:])


# ---------------------------------------------------------------- the ingest --

def test_ingest_refuses_a_new_model_without_an_hf():
    """The merge can run BEFORE correct-raw (the aggregate's order): an hf-less NEW
    row must never reach the store as `hf: ''`, and the rest must still land."""
    store = base_store()
    added, updated, out = ingest(
        store,
        {"nvidia-20261020-120000.json": snapshot([
            raw_model("good-model", post=POST_A),
            raw_model("sloppy-model", hf="", post=POST_B),
        ])},
        since=utc(store["generated_utc"]),
    )
    check("ingest: the good model is added, the hf-less one is refused",
          added == 1 and ids(store) == {"qwen3.6-27b", "good-model"}, sorted(ids(store)))
    check("ingest: the refusal is loud and names the model and the snapshot",
          "REFUSED 'sloppy-model'" in out and "nvidia-20261020-120000.json" in out, out)
    check("ingest: no stored model carries an empty hf",
          all(m.get("hf") for m in store["models"]), [m.get("hf") for m in store["models"]])
    check("ingest: the refusal says the rest of the snapshot still merges",
          "the rest of the snapshot still merges" in out, out)
    check("ingest: the stored model's own hf is untouched",
          next(m for m in store["models"] if m["id"] == "qwen3.6-27b")["hf"]
          == "Qwen/Qwen3.6-27B",
          next(m for m in store["models"] if m["id"] == "qwen3.6-27b")["hf"])

    # An EXISTING model still merges: its stored hf is kept (additive, rule 3b).
    store2 = base_store()
    added2, updated2, out2 = ingest(
        store2,
        {"amd-20261020-130000.json": snapshot([
            dict(raw_model("qwen3.6-27b", hf=None, post=POST_B)),
        ], backend="amd")},
        since=utc(store2["generated_utc"]),
    )
    existing = next(m for m in store2["models"] if m["id"] == "qwen3.6-27b")
    check("ingest: an existing model still merges (no refusal, no deletion)",
          added2 == 0 and updated2 == 1 and "REFUSED" not in out2, (added2, updated2, out2))
    check("ingest: the existing model keeps its stored hf",
          existing["hf"] == "Qwen/Qwen3.6-27B", existing.get("hf"))
    check("ingest: the new measurement landed on it",
          any(e.get("tps") == "40" for e in existing["engines"]), existing["engines"])


def test_the_module_is_wired_into_the_suite():
    check("wiring: the runner discovers this module and `make test` runs the runner",
          wired(__file__), "")


def main() -> int:
    print("Raw-snapshot quarantine: one un-derivable model never discards a refresh")
    test_an_underivable_model_is_quarantined_and_the_rest_merges()
    test_a_known_model_is_repaired_from_the_store()
    test_a_measurement_without_a_post_is_dropped()
    test_a_capture_where_no_snapshot_can_be_read_is_the_unusable_state()
    test_ingest_refuses_a_new_model_without_an_hf()
    test_the_module_is_wired_into_the_suite()
    print(f"\nPASSED {_PASS} | FAILED {_FAIL}")
    return 1 if _FAIL else 0


if __name__ == "__main__":
    raise SystemExit(main())
