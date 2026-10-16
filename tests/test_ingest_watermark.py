#!/usr/bin/env python3
"""Issue #175: a merge folds in only the raw snapshots NEWER than the store.

Proves the boundary the issue asks for:
  1. An OLD raw snapshot (captured at or before the store's own generated_utc)
     cannot change the store.
  2. A FRESH refresh still merges its own legs — a snapshot newer than the
     store's generated_utc is merged.
  3. A snapshot this code cannot date is STILL merged (fail-open: a file we
     cannot place in time is never silently dropped).
  4. The boundary is derived from the store and can be overridden with
     `--since`, end to end through the real CLI.
  5. self_correct_raw refreshes a CORRECTED snapshot's generated_utc so the
     correction is re-merged rather than skipped as "old", and leaves an
     untouched snapshot byte-identical (so the next merge does not re-read it).

Run:  python3 tests/test_ingest_watermark.py   or   make test
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import update_trending as UT  # noqa: E402
import self_correct_raw as SC  # noqa: E402

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


def utc(s: str) -> datetime:
    return datetime.strptime(s, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)


def base_store() -> dict:
    """A minimal but contract-conformant models.json."""
    return {
        "generated_utc": "2026-10-02T00:00:00Z",
        "engines": {
            "llama.cpp": {"backend": "CUDA", "note": "x",
                          "url": "https://github.com/ggml-org/llama.cpp"},
        },
        "models": [{
            "id": "qwen3-14b", "name": "Qwen3 14B", "full_name": "Qwen3-14B", "type": "LLM",
            "formats": [{"name": "GGUF", "hf": "Qwen/Qwen3-14B"}], "license": "Apache 2.0",
            "params": "14B", "hf": "Qwen/Qwen3-14B", "vram_tier": "9GB", "vram_min": "8GB",
            "backends": ["CUDA"], "supported_engines": ["llama.cpp"],
            "engines": [{"engine": "llama.cpp", "tps": "50", "hardware": "RTX 3060",
                         "quant": "Q4", "date": "2026-09-20",
                         "source_post": "https://lightbrd.com/u/status/9000"}],
            "why": "w", "engagement": {"likes": 5, "comments": 1, "views": 10, "last_7d_likes": 2},
            "last_seen": "2026-09-27",
        }],
    }


def raw_model(mid: str) -> dict:
    return {
        "id": mid, "name": mid, "full_name": mid, "type": "LLM", "license": "MIT",
        "params": "8B", "hf": "org/" + mid, "vram_tier": "8GB", "vram_min": "8GB",
        "backends": ["CUDA"], "last_seen": "2026-10-01",
        "engines": [{"engine": "llama.cpp", "tps": "40", "hardware": "RTX 3060",
                     "quant": "Q4", "date": "2026-10-01",
                     "source_post": "https://lightbrd.com/u/status/" + mid}],
    }


def ingest(store: dict, raws: dict[str, dict], since=None) -> tuple[int, int]:
    """Point UT.RAW_DIR at a temp dir of raw snapshots and run the REAL ingest."""
    with tempfile.TemporaryDirectory() as td:
        rdir = Path(td)
        for name, payload in raws.items():
            (rdir / name).write_text(json.dumps(payload))
        saved = UT.RAW_DIR
        UT.RAW_DIR = rdir
        try:
            return UT.ingest_raw_snapshots(store, since=since)
        finally:
            UT.RAW_DIR = saved


def ids(store: dict) -> set[str]:
    return {m["id"] for m in store["models"]}


# ----------------------------------------------------------------- behaviour --

def test_an_old_snapshot_cannot_change_the_store():
    store = base_store()  # generated_utc 2026-10-02
    added, updated = ingest(
        store,
        {"cpu-20261001-120000.json": {"backend": "cpu", "generated_utc": "2026-10-01T12:00:00Z",
                                      "models": [raw_model("oldmodel")]}},
        since=utc(store["generated_utc"]),
    )
    check("old snapshot: it is not merged (0 added, 0 updated)", (added, updated) == (0, 0),
          (added, updated))
    check("old snapshot: the store is untouched", "oldmodel" not in ids(store), sorted(ids(store)))


def test_a_snapshot_newer_than_the_store_is_merged():
    store = base_store()  # generated_utc 2026-10-02
    added, updated = ingest(
        store,
        {"cpu-20261003-120000.json": {"backend": "cpu", "generated_utc": "2026-10-03T12:00:00Z",
                                      "models": [raw_model("freshmodel")]}},
        since=utc(store["generated_utc"]),
    )
    check("fresh snapshot: a fresh refresh still merges its own leg (1 added)", added == 1, added)
    check("fresh snapshot: the new model landed", "freshmodel" in ids(store), sorted(ids(store)))


def test_a_snapshot_with_no_usable_stamp_is_still_merged():
    store = base_store()
    added, _ = ingest(
        store,
        {"snap-0.json": {"backend": "cpu", "models": [raw_model("undated")]}},
        since=utc(store["generated_utc"]),
    )
    check("fail-open: a snapshot with no generated_utc and no name stamp is merged",
          added == 1 and "undated" in ids(store), added)


def test_the_filename_stamp_dates_a_snapshot():
    store = base_store()
    added, _ = ingest(
        store,
        {"cpu-20261001-120000.json": {"backend": "cpu", "models": [raw_model("named-old")]}},
        since=utc(store["generated_utc"]),  # 2026-10-02 > 2026-10-01
    )
    check("name stamp: an old filename stamp is respected (skipped)", added == 0, added)
    store2 = base_store()
    added2, _ = ingest(
        store2,
        {"cpu-20261003-120000.json": {"backend": "cpu", "models": [raw_model("named-new")]}},
        since=utc(store2["generated_utc"]),
    )
    check("name stamp: a new filename stamp is respected (merged)",
          added2 == 1 and "named-new" in ids(store2), added2)


def test_a_snapshot_at_the_boundary_is_already_in_the_store():
    """`since` is the last merge instant, and the rule is STRICTLY newer: a
    snapshot captured at exactly that instant was already folded in."""
    store = base_store()
    added, _ = ingest(
        store,
        {"cpu-20261002-000000.json": {"backend": "cpu", "generated_utc": "2026-10-02T00:00:00Z",
                                      "models": [raw_model("onboundary")]}},
        since=utc(store["generated_utc"]),
    )
    check("boundary: a snapshot captured at the store's own instant is not re-merged",
          added == 0 and "onboundary" not in ids(store), added)


# ---------------------------------------------------------------- the CLI ----

def _run_cli(data_dir: Path):
    env = dict(os.environ, TRENDING_DATA_DIR=str(data_dir),
               TRENDING_README=str(data_dir / "README.md"))
    return subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "update_trending.py")],
        cwd=str(ROOT), env=env, capture_output=True, text=True, timeout=300,
    )


def test_the_cli_derives_the_boundary_from_the_store():
    """End to end: an old raw cannot change the store, a fresh one is merged —
    with no `--since` at all, because main() derives it from the store."""
    with tempfile.TemporaryDirectory() as td:
        d = Path(td)
        (d / "raw").mkdir()
        (d / "models.json").write_text(json.dumps(base_store()))
        (d / "raw" / "cpu-20261001-120000.json").write_text(json.dumps(
            {"backend": "cpu", "generated_utc": "2026-10-01T12:00:00Z",
             "models": [raw_model("stale-leg")]}))
        p = _run_cli(d)
        check("cli: the run succeeded", p.returncode == 0, p.stdout[-500:] + p.stderr[-500:])
        out = json.loads((d / "models.json").read_text())
        check("cli: the OLD raw did not change the store", "stale-leg" not in ids(out),
              sorted(ids(out)))

    with tempfile.TemporaryDirectory() as td:
        d = Path(td)
        (d / "raw").mkdir()
        (d / "models.json").write_text(json.dumps(base_store()))
        (d / "raw" / "cpu-20261003-120000.json").write_text(json.dumps(
            {"backend": "cpu", "generated_utc": "2026-10-03T12:00:00Z",
             "models": [raw_model("fresh-leg")]}))
        p = _run_cli(d)
        check("cli: the run succeeded (fresh leg)", p.returncode == 0, p.stdout[-500:])
        out = json.loads((d / "models.json").read_text())
        check("cli: the FRESH leg was merged", "fresh-leg" in ids(out), sorted(ids(out)))


def test_the_since_flag_overrides_the_derived_boundary():
    with tempfile.TemporaryDirectory() as td:
        d = Path(td)
        (d / "raw").mkdir()
        (d / "models.json").write_text(json.dumps(base_store()))
        (d / "raw" / "cpu-20261001-120000.json").write_text(json.dumps(
            {"backend": "cpu", "generated_utc": "2026-10-01T12:00:00Z",
             "models": [raw_model("forced-leg")]}))
        env = dict(os.environ, TRENDING_DATA_DIR=str(d), TRENDING_README=str(d / "README.md"))
        p = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "update_trending.py"),
             "--since", "2026-09-30T00:00:00Z"],
            cwd=str(ROOT), env=env, capture_output=True, text=True, timeout=300,
        )
        check("--since: the run succeeded", p.returncode == 0, p.stdout[-400:] + p.stderr[-400:])
        out = json.loads((d / "models.json").read_text())
        check("--since: an explicit older boundary re-merges the raw", "forced-leg" in ids(out),
              sorted(ids(out)))

    with tempfile.TemporaryDirectory() as td:
        d = Path(td)
        (d / "raw").mkdir()
        (d / "models.json").write_text(json.dumps(base_store()))
        env = dict(os.environ, TRENDING_DATA_DIR=str(d), TRENDING_README=str(d / "README.md"))
        p = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "update_trending.py"), "--since", "not-a-date"],
            cwd=str(ROOT), env=env, capture_output=True, text=True, timeout=300,
        )
        check("--since: a malformed stamp is refused loudly", p.returncode != 0,
              p.stdout[-300:] + p.stderr[-300:])


# ------------------------------------------------------- corrections (#175) --

def test_self_correct_refreshes_a_corrected_snapshot():
    """A corrected snapshot must be re-merged, not skipped as 'old': self_correct
    refreshes generated_utc when (and only when) it actually changes the file."""
    store = base_store()
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "cpu-20261001-120000.json"
        # missing top-level backend, last_seen and full_name -> correctable
        payload = {"generated_utc": "2026-10-01T12:00:00Z",
                   "models": [{"id": "x", "name": "X", "type": "LLM", "license": "MIT",
                               "params": "8B", "hf": "org/x", "vram_tier": "8GB",
                               "vram_min": "8GB", "backends": ["CUDA"],
                               "engines": [{"engine": "llama.cpp", "tps": "40",
                                            "hardware": "RTX 3060", "quant": "Q4",
                                            "date": "2026-10-01",
                                            "source_post": "https://lightbrd.com/u/status/9"}]}]}
        p.write_text(json.dumps(payload))
        before = p.read_text()
        notes = SC.correct_snapshot(p, store)
        after = json.loads(p.read_text())
        check("self-correct: it corrected the snapshot", bool(notes), notes)
        check("self-correct: the corrected snapshot's generated_utc was refreshed past the store",
              UT.parse_utc_stamp(after["generated_utc"]) > utc(store["generated_utc"]),
              after["generated_utc"])
        check("self-correct: the file changed on disk", p.read_text() != before)

        # a second pass has nothing to do: byte-identical, no stamp bump
        before2 = p.read_text()
        notes2 = SC.correct_snapshot(p, store)
        check("self-correct: an already-conformant snapshot is left byte-identical",
              p.read_text() == before2 and not notes2, (notes2, p.read_text()[:120]))


def main() -> int:
    print("ingest watermark: a merge folds in only the snapshots newer than the store (#175)")
    test_an_old_snapshot_cannot_change_the_store()
    test_a_snapshot_newer_than_the_store_is_merged()
    test_a_snapshot_with_no_usable_stamp_is_still_merged()
    test_the_filename_stamp_dates_a_snapshot()
    test_a_snapshot_at_the_boundary_is_already_in_the_store()
    test_the_cli_derives_the_boundary_from_the_store()
    test_the_since_flag_overrides_the_derived_boundary()
    test_self_correct_refreshes_a_corrected_snapshot()
    print(f"\nPASSED {_PASS} | FAILED {_FAIL}")
    return 1 if _FAIL else 0


if __name__ == "__main__":
    raise SystemExit(main())
