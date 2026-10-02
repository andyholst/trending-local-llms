#!/usr/bin/env python3
"""Engine registration at ingest + engine-kind QA (issue #73).

Refresh PR #72 failed CI on two unregistered engines; fix-bot then registered
'DeepSeekHarness' -> deepseek-ai/deepseek-harness ("Everything is a Plugin",
an agent harness) as a CPU inference engine. These tests pin the earlier,
deterministic path: the search records engine_repo, ingest registers only real
inference engines, and the validator rejects known non-engines. GitHub
metadata is stubbed (hermetic); the real PR #72 raw snapshot is a fixture.

  - test_repo_slug
  - test_classify_table                 engines / harness / agent fw / app / benchmark / unknown
  - test_register_happy_path            quillan.cpp registered, backend inferred, note cites post
  - test_register_refusals              not-engine, unknown, unreachable, non-GitHub, no engine_repo
  - test_already_registered_untouched
  - test_engine_repo_stripped           store contract never sees it
  - test_real_pr72_snapshot             DeepSeekHarness refused, quillan.cpp registered, ingest end-to-end
  - test_check_engine_kind              validator fails a registered harness / uncited auto entry
  - test_check_raw_report               --check-raw CLI reports, never fails
  - test_contracts_and_prompts          engine_repo in search contract; auto in model contract; prompts

Run:  python3 tests/test_engine_registry.py   or   make test
"""
from __future__ import annotations

import copy
import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import engine_registry as ER  # noqa: E402
import update_trending as UT  # noqa: E402
import validate as V  # noqa: E402

FIXTURE = ROOT / "tests" / "fixtures" / "raw_pr72_cpu_new_engines.json"
_PASS = 0
_FAIL = 0

META = {
    "leeex1/quillan.cpp": {"full_name": "leeex1/quillan.cpp", "topics": [],
                           "description": "quillan.cpp is a high-performance, lightweight, standalone C++17 inference "
                                          "engine engineered for the Quillan-Ronin architecture."},
    "deepseek-ai/deepseek-harness": {"full_name": "deepseek-ai/deepseek-harness", "topics": ["agents"],
                                     "description": "DeepSeek Harness: Everything is a Plugin."},
    "acme/fastserve": {"full_name": "acme/fastserve", "topics": ["llm-serving", "cuda"],
                       "description": "High-throughput LLM serving engine with paged attention."},
    "acme/chatbox": {"full_name": "acme/chatbox", "topics": ["chat-ui"],
                     "description": "A desktop app chat UI for local LLMs, supports llama.cpp."},
    "acme/agentkit": {"full_name": "acme/agentkit", "topics": [],
                      "description": "An agent framework for building tool-using assistants on top of vLLM."},
    "acme/llmbench": {"full_name": "acme/llmbench", "topics": [],
                      "description": "Benchmark suite measuring tokens per second across inference engines."},
    "acme/misc": {"full_name": "acme/misc", "topics": [], "description": "My dotfiles."},
}


def check(name, cond, detail: object = ""):
    global _PASS, _FAIL
    if cond:
        _PASS += 1
        print(f"  ok  {name}")
    else:
        _FAIL += 1
        print(f"  FAIL {name}" + (f"  [{detail}]" if detail else ""))


def fake_fetch(url):
    return META.get(ER.repo_slug(url) or "")


def store():
    return {"engines": {"llama.cpp": {"backend": "CUDA / CPU / Metal", "note": "n",
                                      "url": "https://github.com/ggml-org/llama.cpp"}}, "models": []}


def meas(engine, hw="PC (CPU)", repo=None, post="https://lightbrd.com/a/status/1"):
    e = {"engine": engine, "tps": "40", "hardware": hw, "quant": "Q4", "date": "2026-10-01", "source_post": post}
    if repo is not None:
        e["engine_repo"] = repo
    return e


def test_repo_slug():
    check("slug: plain", ER.repo_slug("https://github.com/Leeex1/quillan.cpp") == "leeex1/quillan.cpp")
    check("slug: .git + subpath", ER.repo_slug("https://github.com/a/b.git/tree/main") == "a/b")
    check("slug: not GitHub -> None", ER.repo_slug("https://gitlab.com/a/b") is None)
    check("slug: owner only -> None", ER.repo_slug("https://github.com/a") is None)


def test_classify_table():
    cases = [("leeex1/quillan.cpp", "engine"), ("acme/fastserve", "engine"),
             ("deepseek-ai/deepseek-harness", "not-engine"), ("acme/chatbox", "not-engine"),
             ("acme/agentkit", "not-engine"), ("acme/llmbench", "not-engine"), ("acme/misc", "unknown")]
    for slug, want in cases:
        got, why = ER.classify_repo(META[slug])
        check(f"classify: {slug} -> {want}", got == want, f"{got}: {why}")
    check("classify: no metadata -> unknown", ER.classify_repo(None)[0] == "unknown")
    check("classify: not-engine wins over engine words (chat UI 'supports llama.cpp')",
          ER.classify_repo(META["acme/chatbox"])[0] == "not-engine")
    check("classify: listed name refused even with engine words",
          ER.classify_repo({"full_name": "x/y", "description": "LLM inference engine"}, "DeepSeekHarness")[0]
          == "not-engine")


def test_register_happy_path():
    s = store()
    models = [{"id": "q", "engines": [meas("quillan.cpp", repo="https://github.com/leeex1/quillan.cpp")]}]
    d = ER.register_new_engines(s, models, fetch=fake_fetch)
    reg = s["engines"].get("quillan.cpp", {})
    check("register: decision registered", [x["decision"] for x in d] == ["registered"], d)
    check("register: canonical url", reg.get("url") == "https://github.com/leeex1/quillan.cpp", reg)
    check("register: backend inferred from measurements (CPU)", reg.get("backend") == "CPU", reg)
    check("register: auto flag + note cites the source post",
          reg.get("auto") is True and "Auto-registered from https://lightbrd.com/a/status/1" in reg.get("note", ""), reg)
    s2 = store()
    ER.register_new_engines(s2, [{"id": "f", "engines": [meas("FastServe", hw="RTX 4090",
                                                              repo="https://github.com/acme/fastserve")]}],
                            fetch=fake_fetch)
    check("register: GPU measurement -> CUDA backend", s2["engines"]["FastServe"]["backend"] == "CUDA")


def test_register_refusals():
    cases = [
        ("DeepSeekHarness", "https://github.com/deepseek-ai/deepseek-harness", "not-engine"),
        ("Chatbox", "https://github.com/acme/chatbox", "not-engine"),
        ("AgentKit", "https://github.com/acme/agentkit", "not-engine"),
        ("LLMBench", "https://github.com/acme/llmbench", "not-engine"),
        ("Misc", "https://github.com/acme/misc", "unknown"),
        ("Ghost", "https://github.com/acme/does-not-exist", "unreachable"),
        ("Elsewhere", "https://gitlab.com/acme/engine", "unknown"),
        ("NoRepo", None, "no-repo"),
    ]
    for name, repo, want in cases:
        s = store()
        d = ER.register_new_engines(s, [{"id": "m", "engines": [meas(name, repo=repo)]}], fetch=fake_fetch)
        check(f"refuse: {name} -> {want}, not registered",
              d and d[0]["decision"] == want and name not in s["engines"], d)


def test_already_registered_untouched():
    s = store()
    before = copy.deepcopy(s["engines"])
    d = ER.register_new_engines(s, [{"id": "m", "engines": [meas("llama.cpp", repo="https://github.com/acme/misc")]}],
                                fetch=fake_fetch)
    check("existing: no decision for a registered engine", d == [], d)
    check("existing: registry unchanged", s["engines"] == before)


def test_engine_repo_stripped():
    models = [{"id": "m", "engines": [meas("llama.cpp", repo="https://github.com/ggml-org/llama.cpp"),
                                      meas("quillan.cpp", repo="https://github.com/leeex1/quillan.cpp")]}]
    ER.register_new_engines(store(), models, fetch=fake_fetch)
    check("strip: engine_repo removed from every measurement",
          all("engine_repo" not in e for e in models[0]["engines"]), models)


def _real_store():
    return json.loads((ROOT / "data" / "models.json").read_text())


def test_real_pr72_snapshot():
    raw = json.loads(FIXTURE.read_text())
    eng = {e["engine"] for m in raw["models"] for e in m["engines"]}
    check("pr72: fixture carries both new engines", {"quillan.cpp", "DeepSeekHarness"} <= eng, eng)
    # the search agent, prompted as now, records the repos it saw in the posts
    for m in raw["models"]:
        for e in m["engines"]:
            if e["engine"] == "quillan.cpp":
                e["engine_repo"] = "https://github.com/leeex1/quillan.cpp"
            if e["engine"] == "DeepSeekHarness":
                e["engine_repo"] = "https://github.com/deepseek-ai/deepseek-harness"
    s = _real_store()
    with tempfile.TemporaryDirectory() as td:
        (Path(td) / "cpu-20261002-022138.json").write_text(json.dumps(raw))
        saved_dir, saved_fetch = UT.RAW_DIR, ER.fetch_repo_meta
        UT.RAW_DIR = Path(td)
        ER.fetch_repo_meta = fake_fetch
        orig = ER.register_new_engines
        try:
            ER.register_new_engines = lambda st, models, fetch=fake_fetch: orig(st, models, fetch=fetch)
            UT.ingest_raw_snapshots(s)
        finally:
            UT.RAW_DIR, ER.fetch_repo_meta = saved_dir, saved_fetch
            ER.register_new_engines = orig
    check("pr72: quillan.cpp auto-registered at ingest (no fix-bot)", "quillan.cpp" in s["engines"], list(s["engines"]))
    check("pr72: DeepSeekHarness NOT registered", "DeepSeekHarness" not in s["engines"])
    check("pr72: no engine_repo leaks into the store",
          not any("engine_repo" in e for m in s["models"] for e in m.get("engines", [])))
    V.FAILURES.clear()
    V.check_model_fields(s)
    errs = list(V.FAILURES)
    V.FAILURES.clear()
    check("pr72: validation now flags ONLY DeepSeekHarness (for manual review)",
          errs and all("DeepSeekHarness" in e for e in errs) and not any("quillan" in e for e in errs), errs)


def _kind_errors(s):
    V.FAILURES.clear()
    try:
        V.check_engine_kind(s)
        return list(V.FAILURES)
    finally:
        V.FAILURES.clear()


def test_check_engine_kind():
    s = _real_store()
    check("kind: current registry passes", not _kind_errors(s), _kind_errors(s))
    bad = copy.deepcopy(s)
    bad["engines"]["DeepSeekHarness"] = {"backend": "CPU", "note": "x",
                                         "url": "https://github.com/deepseek-ai/deepseek-harness"}
    check("kind: registered harness (what fix-bot did on PR #72) -> FAIL",
          any("not an inference engine" in e for e in _kind_errors(bad)))
    renamed = copy.deepcopy(s)
    renamed["engines"]["Harness X"] = {"backend": "CPU", "note": "x",
                                       "url": "https://github.com/DeepSeek-AI/DeepSeek-Harness"}
    check("kind: same repo under another name / case -> FAIL", bool(_kind_errors(renamed)))
    uncited = copy.deepcopy(s)
    uncited["engines"]["NewEngine"] = {"backend": "CPU", "note": "fast", "url": "https://github.com/a/b", "auto": True}
    check("kind: auto entry without a cited source -> FAIL",
          any("must cite its source" in e for e in _kind_errors(uncited)))


def test_check_raw_report():
    with tempfile.TemporaryDirectory() as td:
        (Path(td) / "cpu-1.json").write_text(FIXTURE.read_text())
        p = subprocess.run([sys.executable, str(ROOT / "scripts" / "engine_registry.py"), "--check-raw", td],
                           capture_output=True, text=True, timeout=60, cwd=ROOT)
    check("cli: --check-raw exits 0 (report only)", p.returncode == 0, p.stderr[-300:])
    check("cli: reports both unregistered engines as no-repo",
          "'quillan.cpp': no-repo" in p.stdout and "'DeepSeekHarness': no-repo" in p.stdout, p.stdout)


def test_contracts_and_prompts():
    sc = json.loads((ROOT / "data" / "search_contract.json").read_text())
    eprops = sc["properties"]["models"]["items"]["properties"]["engines"]["items"]["properties"]
    check("contract: search measurements accept engine_repo", "engine_repo" in eprops)
    mc = json.loads((ROOT / "data" / "model_contract.json").read_text())
    check("contract: registry entries accept auto", "auto" in mc["properties"]["engines"]["additionalProperties"]["properties"])
    check("contract: store measurements do NOT accept engine_repo (stripped at ingest)",
          "engine_repo" not in mc["properties"]["models"]["items"]["properties"]["engines"]["items"]["properties"])
    mk = (ROOT / "Makefile").read_text()
    for b in ("nvidia", "metal", "cpu"):
        prompt = mk[mk.index(f"_search-{b}:\n"):].split("\n", 2)[1]
        check(f"prompt {b}: defines engine vs harness/app/benchmark", "harnesses, agent frameworks" in prompt)
        check(f"prompt {b}: asks for engine_repo, never invent", "engine_repo" in prompt and "never invent" in prompt)
    fix = mk[mk.index("_fix:\n"):].split("\n", 2)[1]
    check("prompt fix: never register a harness/app/benchmark", "Never register a harness" in fix)
    check("make: engine-check target", "_engine-check:" in mk and "engine_registry.py --check-raw" in mk)


def main() -> int:
    print("engine registration at ingest + engine-kind QA (issue #73)")
    test_repo_slug()
    test_classify_table()
    test_register_happy_path()
    test_register_refusals()
    test_already_registered_untouched()
    test_engine_repo_stripped()
    test_real_pr72_snapshot()
    test_check_engine_kind()
    test_check_raw_report()
    test_contracts_and_prompts()
    print(f"\nPASSED {_PASS} | FAILED {_FAIL}")
    return 1 if _FAIL else 0


if __name__ == "__main__":
    raise SystemExit(main())
