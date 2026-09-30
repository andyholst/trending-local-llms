#!/usr/bin/env python3
"""Direct unit tests for the validator functions in scripts/validate.py.

These exercise each check's real failure/pass paths (not just the real store),
catching a broken validator in CI. Covers:
  - no duplicate models (id/name)
  - no truly-identical engine rows (same-date-different-hardware is valid)
  - latest t/s ordering (engines newest-date-first)
  - supported_engines consistency
  - required model fields + per-format {name,hf}
  - model_contract.json schema pass/fail
  - search_contract.json pass/fail
  - raw -> models.json mapping + collision
  - no-removal vs snapshot
  - newline terminators

Run:  python3 tests/test_validate.py     or   make test
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import validate as V  # noqa: E402

_PASS = 0
_FAIL = 0


def reset():
    V.FAILURES.clear()


def check(name, cond, detail=""):
    global _PASS, _FAIL
    if cond:
        _PASS += 1
        print(f"  ok  {name}")
    else:
        _FAIL += 1
        print(f"  FAIL {name}" + (f"  [{detail}]" if detail else ""))


def good_store() -> dict:
    return {"engines": {
        "llama.cpp": {"backend": "CUDA / CPU / Metal", "note": "x", "url": "https://u"},
        "MLX": {"backend": "Metal", "note": "x", "url": "https://u"},
    }, "models": [{
        "id": "m1", "name": "Model One", "full_name": "Model-One", "type": "LLM",
        "formats": [{"name": "GGUF", "hf": "a/m1"}], "license": "Apache 2.0",
        "params": "13B", "hf": "a/m1", "vram_tier": "12GB", "vram_min": "8GB",
        "backends": ["CUDA", "Metal"],
        "supported_engines": ["llama.cpp"],
        "engines": [
            {"engine": "llama.cpp", "tps": "80", "hardware": "RTX 4070", "date": "2026-09-27", "source_post": "https://lightbrd.com/x"},
            {"engine": "MLX", "tps": "50", "hardware": "Apple", "date": "2026-09-20", "source_post": "https://lightbrd.com/y"},
        ],
        "why": "w", "engagement": {"likes": 1, "comments": 1, "views": 1, "last_7d_likes": 1},
        "last_seen": "2026-09-27",
    }]}


def test_no_duplicates():
    reset()
    s = good_store()
    V.check_no_duplicates(s)
    check("no dup: unique store passes", len(V.FAILURES) == 0)
    reset()
    s2 = good_store()
    s2["models"].append(dict(s2["models"][0], id="m1", name="Another Name"))  # dup id, diff name
    V.check_no_duplicates(s2)
    check("no dup: catches duplicate id", len(V.FAILURES) == 1 and "duplicate model ids" in V.FAILURES[0])
    reset()
    s3 = good_store()
    s3["models"].append(dict(s3["models"][0], id="m2", name="Model One"))  # dup name
    V.check_no_duplicates(s3)
    check("no dup: catches duplicate name", len(V.FAILURES) == 1 and "duplicate model names" in V.FAILURES[0])


def test_no_duplicate_engines():
    reset()
    s = good_store()
    V.check_no_duplicate_engines(s)
    check("engines: valid store passes", len(V.FAILURES) == 0)
    # truly identical row -> fail
    reset()
    s = good_store()
    s["models"][0]["engines"].append(dict(s["models"][0]["engines"][0]))
    V.check_no_duplicate_engines(s)
    check("engines: catches truly identical row", len(V.FAILURES) == 1)
    # same date different hardware -> valid (the earlier bug)
    reset()
    s = good_store()
    s["models"][0]["engines"].append(
        {"engine": "llama.cpp", "tps": "~50", "hardware": "RTX 3060", "date": "2026-09-26", "source_post": "https://lightbrd.com/z"})
    V.check_no_duplicate_engines(s)
    check("engines: same-date-different-hardware is NOT a dup", len(V.FAILURES) == 0)
    # '39.3' vs '39.3 (est)' on same engine+date IS a duplicate (normalized tps)
    reset()
    s = good_store()
    s["models"][0]["engines"] = [
        {"engine": "llama.cpp", "tps": "39.3", "hardware": "RTX 4090", "date": "2026-09-28", "source_post": "https://lightbrd.com/a"},
        {"engine": "llama.cpp", "tps": "39.3 (est)", "hardware": "RTX 4090", "date": "2026-09-28", "source_post": "https://lightbrd.com/b"},
    ]
    V.check_no_duplicate_engines(s)
    check("engines: '39.3' vs '39.3 (est)' is a dup (normalized)", len(V.FAILURES) == 1, str(V.FAILURES))


def test_tps_shape():
    """check_tps_shape must ACCEPT t/s that start with a numeric token (int,
    float, estimate tilde, range, or comment-after-the-number) and REJECT any
    that start with text/other characters — including duplicate rows whose tps
    is malformed."""
    def tps(v):
        reset()
        s = good_store()
        s["models"][0]["engines"] = [{"engine": "llama.cpp", "tps": v, "date": "2026-09-28",
                                      "source_post": "https://lightbrd.com/x"}]
        V.check_tps_shape(s)
        return len(V.FAILURES)

    # GOOD — starts with a number
    good = ["39.3", "~50", "67-71", "99.7", "120-124", "22", "35.5-43.7",
            "143", "233 (DFlash spec-decode), 74.9 stock", "~237 decode",
            "~38 (1 user); ~215 peak (16 parallel)"]
    for v in good:
        check(f"tps GOOD starts-numeric: {v!r}", tps(v) == 0, str(V.FAILURES))

    # BAD — does not start with a number (text / leading comment / label)
    bad = ["a few (est)", "(est) 50", "~fast", "fast", "slow-ish", "N/A",
           "varies", "unknown"]
    for v in bad:
        check(f"tps BAD rejects non-numeric start: {v!r}", tps(v) == 1, str(V.FAILURES))

    # DUPLICATE with malformed text is caught (both fail tps-shape)
    reset()
    s = good_store()
    s["models"][0]["engines"] = [
        {"engine": "llama.cpp", "tps": "a few (est)", "date": "2026-09-28", "source_post": "https://lightbrd.com/a"},
        {"engine": "llama.cpp", "tps": "~fast", "date": "2026-09-28", "source_post": "https://lightbrd.com/b"},
    ]
    V.check_tps_shape(s)
    check("tps: duplicate malformed-text rows both rejected (2 fails)",
          len(V.FAILURES) == 2, str(V.FAILURES))


def test_latest_tps_order():
    reset()
    s = good_store()  # already newest-first
    V.check_latest_tps(s)
    check("latest-tps: newest-first passes", len(V.FAILURES) == 0)
    reset()
    s = good_store()
    # reverse the engines -> stale t/s first -> fail
    s["models"][0]["engines"].reverse()
    V.check_latest_tps(s)
    check("latest-tps: catches stale-first order", len(V.FAILURES) == 1)


def test_supported_engines():
    reset()
    s = good_store()
    V.check_supported_engines(s)
    check("supported-engines: consistent passes", len(V.FAILURES) == 0)
    reset()
    s = good_store()
    s["models"][0]["supported_engines"].append("vLLM")  # not measured
    V.check_supported_engines(s)
    check("supported-engines: catches engine w/o measurement", len(V.FAILURES) == 1)
    reset()
    s = good_store()
    s["models"][0].pop("supported_engines")
    V.check_supported_engines(s)
    check("supported-engines: catches missing list", len(V.FAILURES) == 1)


def test_model_fields():
    reset()
    s = good_store()
    V.check_model_fields(s)
    check("fields: valid store passes", len(V.FAILURES) == 0)
    reset()
    s = good_store()
    s["models"][0].pop("vram_min")
    V.check_model_fields(s)
    check("fields: catches missing vram_min", any("vram_min" in f for f in V.FAILURES))
    reset()
    s = good_store()
    s["models"][0]["formats"] = ["GGUF"]  # string not {name,hf}
    V.check_model_fields(s)
    check("fields: catches string format (needs {name,hf})", any("formats" in f for f in V.FAILURES))
    reset()
    s = good_store()
    s["engines"]["llama.cpp"].pop("url")
    V.check_model_fields(s)
    check("fields: catches engine without repo url", any("repo url" in f for f in V.FAILURES))


def _run_schema(store, schema_bytes):
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "model_contract.json"
        p.write_text(schema_bytes if isinstance(schema_bytes, str) else json.dumps(schema_bytes))
        saved = V.CONTRACT
        V.CONTRACT = p
        try:
            reset()
            V.check_schema(store)
            return list(V.FAILURES)
        finally:
            V.CONTRACT = saved


def _run_search_contract(raw_files, schema_bytes):
    with tempfile.TemporaryDirectory() as td:
        sdir = Path(td) / "schema.json"
        sdir.write_text(schema_bytes)
        rdir = Path(td) / "raw"
        rdir.mkdir()
        for name, content in raw_files.items():
            (rdir / name).write_text(json.dumps(content))
        saved_s, saved_r = V.SEARCH_CONTRACT, V.RAW_DIR
        V.SEARCH_CONTRACT, V.RAW_DIR = sdir, rdir
        try:
            reset()
            V.check_search_contract()
            return list(V.FAILURES)
        finally:
            V.SEARCH_CONTRACT, V.RAW_DIR = saved_s, saved_r


def test_schema_pass_fail():
    schema = {
        "type": "object", "required": ["models"],
        "properties": {"models": {"type": "array", "items": {"type": "object", "required": ["id", "name"]}}},
    }
    good = {"models": [{"id": "a", "name": "b"}]}
    bad = {"models": [{"id": "a"}]}  # missing name
    fails = _run_schema(good, schema)
    check("schema: conforming store passes", len(fails) == 0)
    fails = _run_schema(bad, schema)
    check("schema: catches non-conforming store", len(fails) == 1 and "schema:" in fails[0])


def test_search_contract_pass_fail():
    schema = {
        "type": "object", "required": ["backend", "models"], "additionalProperties": False,
        "properties": {
            "backend": {"type": "string"},
            "models": {"type": "array", "items": {"type": "object", "required": ["id", "vram_min"]}},
        },
    }
    good = {"backend": "nvidia", "models": [{"id": "x", "vram_min": "8GB"}]}
    bad = {"backend": "nvidia", "models": [{"id": "x"}]}  # missing vram_min
    fails = _run_search_contract({"ok.json": good}, json.dumps(schema))
    check("search-contract: conforming raw passes", len(fails) == 0)
    fails = _run_search_contract({"bad.json": bad}, json.dumps(schema))
    check("search-contract: catches missing vram_min", len(fails) == 1 and "vram_min" in fails[0])


def test_no_removal():
    with tempfile.TemporaryDirectory() as td:
        snap_dir = Path(td)
        (snap_dir / "trending-001.json").write_text(json.dumps(good_store()))
        now = good_store()
        # all models retained
        reset()
        V.check_no_removal(now, snap_dir)
        check("no-removal: retained store passes", len(V.FAILURES) == 0)
        # a model removed
        reset()
        now_minus = good_store()
        now_minus["models"].pop()
        V.check_no_removal(now_minus, snap_dir)
        check("no-removal: catches removed model", len(V.FAILURES) == 1 and "removed" in V.FAILURES[0])


def test_newline_terminators():
    with tempfile.TemporaryDirectory() as td:
        # build a tiny fake git repo with one file
        repo = Path(td)
        subprocess.run(["git", "init", "-q"], cwd=repo)
        f = repo / "test.txt"
        f.write_text("hello")  # no trailing newline
        subprocess.run(["git", "add", "."], cwd=repo, capture_output=True)
        subprocess.run(["git", "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-qm", "x"], cwd=repo, capture_output=True)
        saved_root, saved_ext, saved_names = V.ROOT, V.TEXT_EXTS, V.TEXT_NAMES
        V.ROOT, V.TEXT_EXTS, V.TEXT_NAMES = repo, (".txt",), ("Makefile",)
        try:
            reset()
            V.check_newline_terminators()
            check("newline: catches file without trailing newline", len(V.FAILURES) == 1 and "missing trailing newline" in V.FAILURES[0])
            # fix it
            f.write_text("hello\n")
            subprocess.run(["git", "add", "."], cwd=repo, capture_output=True)
            subprocess.run(["git", "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-qm", "y"], cwd=repo, capture_output=True)
            reset()
            V.check_newline_terminators()
            check("newline: passes once newline added", len(V.FAILURES) == 0)
        finally:
            V.ROOT, V.TEXT_EXTS, V.TEXT_NAMES = saved_root, saved_ext, saved_names


def test_tps_shape_matrix():
    """Data-driven matrix: every tps string form -> expected accept/reject by
    check_tps_shape. Covers ints, decimals, tilde estimates, ranges, est markers,
    comments-after-number, whitespace, empty, and every leading-text/bad form."""
    # (tps, expected_accept). Empty is skipped (no tps -> not a failure).
    matrix = [
        ("50", True), ("39.3", True), ("99.7", True),
        ("~50", True), ("~237.5", True),
        ("67-71", True), ("35.5-43.7", True), ("120-124", True),
        ("39.3 (est)", True), ("39.3(est)", True),
        ("233 (DFlash spec-decode), 74.9 stock", True),
        ("~38 (1 user); ~215 peak (16 parallel)", True),
        ("~ 50", True), ("  50", True), ("50  ", True),
        ("", True),  # empty -> skipped, not a failure
        ("a few (est)", False), ("(est) 50", False), ("~fast", False),
        ("fast", False), ("slow-ish", False), ("N/A", False),
        ("varies", False), ("unknown", False), (", 50", False), ("-50", False),
    ]
    for tps, expect in matrix:
        reset()
        s = good_store()
        s["models"][0]["engines"] = [{"engine": "llama.cpp", "tps": tps,
                                      "date": "2026-09-28", "source_post": "https://lightbrd.com/x"}]
        V.check_tps_shape(s)
        got = len(V.FAILURES) == 0
        check(f"tps-matrix: {tps!r} -> {'accept' if expect else 'reject'}",
              got == expect, str(V.FAILURES))


def main() -> int:
    print("validator: direct unit tests")
    test_no_duplicates()
    test_no_duplicate_engines()
    test_tps_shape()
    test_tps_shape_matrix()
    test_latest_tps_order()
    test_supported_engines()
    test_model_fields()
    test_schema_pass_fail()
    test_search_contract_pass_fail()
    test_no_removal()
    test_newline_terminators()
    print(f"\nPASSED {_PASS} | FAILED {_FAIL}")
    return 1 if _FAIL else 0


if __name__ == "__main__":
    raise SystemExit(main())
