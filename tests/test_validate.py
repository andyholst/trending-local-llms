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
  - additive-only (no key/value loss vs snapshot)
  - every check wired to a stage + a Makefile `--only` target (no dead validator function)
  - newline terminators

Run:  python3 tests/test_validate.py     or   make test
"""
from __future__ import annotations

import ast
import contextlib
import io
import json
import os
import re
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
            "143", "39.3 (est)", "~237", "52", "~ 50"]
    for v in good:
        check(f"tps GOOD starts-numeric: {v!r}", tps(v) == 0, str(V.FAILURES))

    # BAD — does not start with a number (text / leading comment / label)
    bad = ["a few (est)", "(est) 50", "~fast", "fast", "slow-ish", "N/A",
           "varies", "unknown", "233 (DFlash spec-decode), 74.9 stock",
           "~237 decode", "~38 (1 user); ~215 peak (16 parallel)",
           "44 (spec-decode 3.6x; 12 stock)", "52-60 output / 1250 prompt"]
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


def _snap_with_posts(store: dict) -> dict:
    """Snapshot fixture carrying the optional engagement keys (`seen_posts`, the
    computed trend fields) and per-measurement counters, so the additive-only
    check has something to lose."""
    s = json.loads(json.dumps(store))
    m = s["models"][0]
    m["engagement"].update({"seen_posts": [
        {"url": "https://lightbrd.com/x/status/1", "date": "2026-09-27", "engine": "llama.cpp",
         "tps": "80", "likes": 3, "views": 10},
    ], "posts_7d": 1, "buzz_7d": 1.5, "score_7d": 1.5, "speed_bonus": 2.0, "trend_score": 3.5})
    m["engines"][0].update({"likes": 10, "comments": 4, "views": 100})
    m["formats"].append({"name": "MLX", "hf": "a/m1-mlx"})
    return s


def _run_value_loss(snapshot: dict, current: dict):
    with tempfile.TemporaryDirectory() as td:
        snap_dir = Path(td)
        (snap_dir / "trending-001.json").write_text(json.dumps(snapshot))
        reset()
        V.check_no_value_loss(current, snap_dir)
        return list(V.FAILURES)


def test_no_value_loss():
    """The additive-only guarantee: nothing that existed in the newest snapshot
    may lose a key, a measurement, a t/s or a counter — while adding is fine."""
    snap = _snap_with_posts(good_store())

    # unchanged store -> nothing lost
    fails = _run_value_loss(snap, json.loads(json.dumps(snap)))
    check("value-loss: unchanged store passes", len(fails) == 0, str(fails))

    # ADDITIVE changes must never be reported (a new key, a new measurement, a
    # new backend, a raised counter, a grown supported_engines list)
    grown = json.loads(json.dumps(snap))
    m = grown["models"][0]
    m["system_ram_min"] = "16GB"                       # new optional key
    m["backends"].append("CPU")
    m["supported_engines"].append("MLX")
    m["engines"].append({"engine": "vLLM", "tps": "120", "hardware": "RTX 4070",
                         "date": "2026-09-28", "source_post": "https://lightbrd.com/n"})
    m["engines"][0]["likes"] = 99                      # counter rose
    fails = _run_value_loss(snap, grown)
    check("value-loss: additive-only changes pass", len(fails) == 0, str(fails))

    # an OPTIONAL engagement key removed -> caught (the schema cannot see it)
    lost_key = json.loads(json.dumps(snap))
    lost_key["models"][0]["engagement"].pop("seen_posts")
    fails = _run_value_loss(snap, lost_key)
    check("value-loss: catches removed optional key",
          len(fails) == 1 and "engagement.seen_posts" in fails[0], str(fails))

    # a required key removed -> caught too
    lost_req = json.loads(json.dumps(snap))
    lost_req["models"][0]["engagement"].pop("views")
    fails = _run_value_loss(snap, lost_req)
    check("value-loss: catches removed engagement key",
          len(fails) == 1 and "engagement.views" in fails[0], str(fails))

    # a whole (engine, GPU size) measurement group gone -> caught
    lost_meas = json.loads(json.dumps(snap))
    lost_meas["models"][0]["engines"] = [
        e for e in lost_meas["models"][0]["engines"] if e["engine"] != "llama.cpp"]
    fails = _run_value_loss(snap, lost_meas)
    # the dropped row also carried the per-measurement counters, so the loss is
    # reported both as a missing measurement group and as lost keys
    check("value-loss: catches a lost measurement group",
          any("measurement llama.cpp" in f for f in fails)
          and any("engines.likes" in f for f in fails), str(fails))

    # a t/s figure can only be raised, never lowered
    lowered = json.loads(json.dumps(snap))
    lowered["models"][0]["engines"][0]["tps"] = "20"
    fails = _run_value_loss(snap, lowered)
    check("value-loss: catches a lowered t/s",
          len(fails) == 1 and "t/s lowered" in fails[0], str(fails))

    # engagement counters may only grow
    counter = json.loads(json.dumps(snap))
    counter["models"][0]["engines"][0]["likes"] = 1
    fails = _run_value_loss(snap, counter)
    check("value-loss: catches a lowered counter",
          len(fails) == 1 and "likes lowered" in fails[0], str(fails))

    # a scalar list that lost a member -> caught
    lost_backend = json.loads(json.dumps(snap))
    lost_backend["models"][0]["backends"] = ["CUDA"]
    fails = _run_value_loss(snap, lost_backend)
    check("value-loss: catches a backend dropped from backends",
          len(fails) == 1 and "backends lost" in fails[0], str(fails))

    # a removed MODEL is check_no_removal's failure, not double-reported here
    fails = _run_value_loss(snap, {"models": []})
    check("value-loss: a removed model is not reported twice", len(fails) == 0, str(fails))

    # no snapshot -> nothing to compare, and it SAYS so (never a silent pass)
    with tempfile.TemporaryDirectory() as td:
        out = io.StringIO()
        reset()
        with contextlib.redirect_stdout(out):
            V.check_no_value_loss(good_store(), Path(td))
        check("value-loss: no snapshot passes as 'nothing to compare'",
              len(V.FAILURES) == 0 and "nothing to compare" in out.getvalue(),
              out.getvalue())


def _validator_ast() -> "ast.Module":
    return ast.parse((ROOT / "scripts" / "validate.py").read_text())


def test_every_check_is_wired_to_a_stage_and_a_makefile_target():
    """No dead validator function: every `check_*` in scripts/validate.py must be
    registered in main() under a STAGE, every stage must be selected by an explicit
    `--only` list in the Makefile, and `--only <stage>` must really execute it."""
    tree = _validator_ast()

    # Given every check function defined in the validator
    defined = {n.name for n in tree.body if isinstance(n, ast.FunctionDef) and n.name.startswith("check_")}
    check("wiring: the validator defines check_* functions", len(defined) > 5, str(len(defined)))

    # When  main()'s registrations are read
    main_fn = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "main")
    registered: dict[str, str] = {}
    for node in ast.walk(main_fn):
        if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "add"):
            continue
        if not (isinstance(node.args[0], ast.Constant) and isinstance(node.args[1], ast.Constant)):
            continue
        stage = str(node.args[1].value)
        registered[stage] = registered.get(stage, "") + " " + ast.unparse(node.args[2])

    # Then  every check is registered by name (a check nobody calls is a defect)
    for name in sorted(defined):
        check(f"wiring: {name} is registered in main()", name in " ".join(registered.values()),
              "not referenced by any add(...)")

    # And  every stage is explicitly selected by a Makefile target — read through the
    # ONE implementation of that contract (`architecture_check.stage_lists`, issue #514).
    # This test used to re-parse the Makefile with its own regex, so a `--only` shape it
    # accepted and the guard refused (or the reverse) could make one of them lie.
    from architecture_check import stage_lists, validate_stages
    selected = {s for _target, stages in stage_lists(ROOT / "Makefile") for s in stages}
    check("wiring: the one reader actually found the Makefile's --only lists",
          len(stage_lists(ROOT / "Makefile")) >= 5 and len(selected) >= 5,
          (len(stage_lists(ROOT / "Makefile")), sorted(selected)))
    check("wiring: the two readers agree on which stages the validator registers",
          registered.keys() == validate_stages(ROOT / "scripts" / "validate.py"),
          (sorted(registered), sorted(validate_stages(ROOT / "scripts" / "validate.py"))))
    for stage in sorted(registered):
        check(f"wiring: stage '{stage}' is selected by a Makefile --only list",
              stage in selected, f"--only stages: {sorted(selected)}")

    # And  `--only removal` really runs the additive-only check (the actual call path)
    out = subprocess.run([sys.executable, str(ROOT / "scripts" / "validate.py"), "--only", "removal"],
                         capture_output=True, text=True, cwd=ROOT)
    check("wiring: --only removal executes the additive-only check",
          "additive-only (no key/value loss)" in out.stdout, out.stdout[-200:])
    check("wiring: the full `make validate` path runs every stage without --only",
          re.search(r"^_validate:\n\tpython3 scripts/validate\.py\s*$",
                    (ROOT / "Makefile").read_text(), re.M) is not None)


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
        ("39.3 (est)", True), ("39.3(est)", True),
        ("~ 50", True), ("  50", True), ("50  ", True),
        ("", True),  # empty -> skipped, not a failure
        ("a few (est)", False), ("(est) 50", False), ("~fast", False),
        ("fast", False), ("slow-ish", False), ("N/A", False),
        ("varies", False), ("unknown", False), (", 50", False), ("-50", False),
        ("233 (DFlash spec-decode), 74.9 stock", False),
        ("~38 (1 user); ~215 peak (16 parallel)", False),
        ("~237 decode", False), ("44 (spec-decode 3.6x; 12 stock)", False),
        ("52-60 output / 1250 prompt", False),
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


def test_tps_embedded_text_permutations():
    """DATA-DRIVEN: every way a t/s string can embed text must be REJECTED by
    check_tps_shape. Covers number+text, tilde+text, range+text, leading text,
    leading comment, prose-after-number, multi-token prose, parentheses prose."""
    reject = [
        # number then text/comment
        "50 xyz", "50 fast", "50 (note)", "50 runs", "50 per second",
        # tilde + text
        "~fast", "~50 decode", "~ slow", "~aprox", "~ 237 decode",
        # range + text
        "50-60 combined", "67-71 tokens", "35.5-43.7 per sec",
        # leading text / leading comment
        "a few (est)", "~(est) 50", "(est) 50", "fast 50", "about 50",
        # prose after / multi-token prose
        "233 (DFlash spec-decode), 74.9 stock", "~38 (1 user); ~215 peak (16 parallel)",
        "44 (spec-decode 3.6x; 12 stock)", "52-60 output / 1250 prompt",
        "~237 decode", "50 tokens per second (est)",
    ]
    # acceptable (clean numeric, no embedded text)
    accept = ["50", "39.3", "~50", "~ 50", "67-71", "35.5-43.7", "99.7",
              "120-124", "39.3 (est)", "39.3(est)", "~237", "52", "143"]
    def run(v):
        reset()
        s = good_store()
        s["models"][0]["engines"] = [{"engine": "llama.cpp", "tps": v,
                                      "date": "2026-09-28", "source_post": "https://lightbrd.com/x"}]
        V.check_tps_shape(s)
        return len(V.FAILURES) == 0
    for v in reject:
        check(f"tps-embed: REJECT {v!r}", run(v) is False, str(V.FAILURES))
    for v in accept:
        check(f"tps-embed: ACCEPT {v!r}", run(v) is True, str(V.FAILURES))


def main() -> int:
    print("validator: direct unit tests")
    test_no_duplicates()
    test_no_duplicate_engines()
    test_tps_shape()
    test_tps_shape_matrix()
    test_tps_embedded_text_permutations()
    test_latest_tps_order()
    test_supported_engines()
    test_model_fields()
    test_schema_pass_fail()
    test_search_contract_pass_fail()
    test_no_removal()
    test_no_value_loss()
    test_every_check_is_wired_to_a_stage_and_a_makefile_target()
    test_newline_terminators()
    print(f"\nPASSED {_PASS} | FAILED {_FAIL}")
    return 1 if _FAIL else 0


if __name__ == "__main__":
    raise SystemExit(main())
