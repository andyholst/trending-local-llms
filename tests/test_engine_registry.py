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
    for b in UT.SEARCH_LEGS:  # every search leg incl. amd
        prompt = mk[mk.index(f"_search-{b}:\n"):].split("\n", 2)[1]
        check(f"prompt {b}: defines engine vs harness/app/benchmark", "harnesses, agent frameworks" in prompt)
        check(f"prompt {b}: asks for engine_repo, never invent", "engine_repo" in prompt and "never invent" in prompt)
    fix = mk[mk.index("_fix:\n"):].split("\n", 2)[1]
    check("prompt fix: never register a harness/app/benchmark", "Never register a harness" in fix)
    check("make: engine-check target", "_engine-check:" in mk and "engine_registry.py --check-raw" in mk)


# --------------------------------------------------------------------------
# Gap tests (classifier against reality, edge cases, contract, network, CLI)
# --------------------------------------------------------------------------
META_FIXTURE = ROOT / "tests" / "fixtures" / "github_meta.json"


def real_meta() -> dict:
    return {k.lower(): v for k, v in json.loads(META_FIXTURE.read_text())["repos"].items()}


def test_registered_engines_never_refused():
    """REAL GitHub metadata (captured fixture) for every engine in the registry:
    the classifier must never call a registered engine 'not-engine'. It caught
    MLX-fast (Bonsai 2) — 'MLX inference speedup benchmark engine' — being
    refused because a bare 'benchmark' always won."""
    meta = real_meta()
    reg = _real_store()["engines"]
    for name, v in reg.items():
        slug = ER.repo_slug(v["url"])
        check(f"reality: metadata captured for {name}", slug in meta, slug)
        kind, why = ER.classify_repo(meta.get(slug), name)
        check(f"reality: registered '{name}' is never classified not-engine", kind != "not-engine", f"{kind}: {why}")
    check("reality: NON_ENGINE lists share nothing with the registry",
          not ({ER.repo_slug(v["url"]) for v in reg.values()} & ER.NON_ENGINE_REPOS))
    check("reality: quillan.cpp (real) -> engine", ER.classify_repo(meta["leeex1/quillan.cpp"])[0] == "engine")
    check("reality: open-webui (real) -> not-engine", ER.classify_repo(meta["open-webui/open-webui"])[0] == "not-engine")


def test_app_bundled_inference_server():
    """PR #80: mlx-serve ('Native LLM inference server for Apple Silicon ...
    Zig backend, Swift frontend macOS app') was refused on 'frontend', so it
    never registered and validation failed on every Metal refresh."""
    meta = real_meta()
    check("app+server: mlx-serve (real) -> engine", ER.classify_repo(meta["ddalcu/mlx-serve"])[0] == "engine",
          ER.classify_repo(meta["ddalcu/mlx-serve"]))
    check("app+server: oMLX (real, menu-bar app) -> engine", ER.classify_repo(meta["jundot/omlx"])[0] == "engine")
    check("app+server: a chat UI that only SUPPORTS llama.cpp is still not-engine",
          ER.classify_repo(META["acme/chatbox"])[0] == "not-engine")
    check("app+server: open-webui (real) still not-engine",
          ER.classify_repo(meta["open-webui/open-webui"])[0] == "not-engine")
    c = lambda d, t=(): ER.classify_repo({"full_name": "x/y", "description": d, "topics": list(t)})[0]  # noqa: E731
    check("app+server: hard signal wins over a self-declared server (harness with inference server)",
          c("Agent framework with a built-in inference server") == "not-engine")
    check("app+server: 'inference server' only in topics does not rescue an app",
          c("Desktop app chat UI", ["inference-server"]) == "not-engine")


def test_search_prompts_look_up_missing_repos():
    """mlx-serve's post linked no repo, so engine_repo was empty and ingest
    could not register it. The prompts must ask for ONE verified lookup."""
    mk = (ROOT / "Makefile").read_text()
    lines = [l for l in mk.splitlines() if "hermes -z" in l and "--write-raw" in l]
    check("prompts: every search prompt asks for a verified repo lookup when the post links none",
          lines and all("links no repo" in l and "page resolves" in l for l in lines), len(lines))


def test_classifier_signals():
    def c(desc, topics=(), full="x/y", name=""):
        return ER.classify_repo({"full_name": full, "description": desc, "topics": list(topics)}, name)[0]
    harness = real_meta()["deepseek-ai/deepseek-harness"]
    check("signal: harness caught by DESCRIPTION alone (renamed repo, not in list)",
          c(harness["description"], harness["topics"], full="someone/renamed") == "not-engine")
    check("signal: strong 'benchmark suite' beats engine words",
          c("Benchmark suite for LLM inference engines") == "not-engine")
    check("signal: weak 'benchmark' + engine signal -> engine",
          c("MLX inference speedup benchmark engine") == "engine")
    check("signal: weak 'benchmark' alone -> not-engine", c("Collected LLM benchmark results") == "not-engine")
    check("signal: hyphenated topic 'llm-serving' -> engine", c("Fast.", topics=["llm-serving"]) == "engine")
    check("signal: 'plugins' plural is strong", c("vLLM plugins collection") == "not-engine")
    check("signal: empty description + no topics -> unknown", c("") == "unknown")
    check("signal: None description handled", ER.classify_repo({"full_name": "a/b", "description": None})[0] == "unknown")
    check("signal: word boundary — 'mlxfast' alone is not 'mlx'", c("mlxfast tools") == "unknown")


def test_repo_slug_edges():
    cases = {"https://github.com/a/b?tab=readme-ov-file": "a/b", "https://github.com/a/b#readme": "a/b",
             "https://github.com/a/b/": "a/b", "http://www.github.com/A/B.git": "a/b",
             "https://github.com/a/b.c.d": "a/b.c.d", "github.com/a/b": None, "": None, None: None}
    for url, want in cases.items():
        check(f"slug: {url!r} -> {want}", ER.repo_slug(url) == want, ER.repo_slug(url))


def test_invalid_name_never_registered():
    s = store()
    d = ER.register_new_engines(s, [{"id": "m", "engines": [meas("Foo+Bar", repo="https://github.com/leeex1/quillan.cpp")]}],
                                fetch=fake_fetch)
    check("name: 'Foo+Bar' -> invalid-name, not registered (store schema would break)",
          d[0]["decision"] == "invalid-name" and "Foo+Bar" not in s["engines"], d)


def test_conflicting_repos():
    s = store()
    models = [{"id": "a", "engines": [meas("X", repo="https://github.com/leeex1/quillan.cpp")]},
              {"id": "b", "engines": [meas("X", repo="https://github.com/acme/fastserve")]}]
    d = ER.register_new_engines(s, models, fetch=fake_fetch)
    check("conflict: two different repos for one new engine -> conflict, not registered",
          d[0]["decision"] == "conflict" and "X" not in s["engines"], d)
    s = store()
    models = [{"id": "a", "engines": [meas("Q", repo="https://github.com/leeex1/quillan.cpp")]},
              {"id": "b", "engines": [meas("Q", repo="https://github.com/Leeex1/quillan.cpp.git")]},
              {"id": "c", "engines": [meas("Q", repo="https://github.com/leeex1/quillan.cpp/")]}]
    d = ER.register_new_engines(s, models, fetch=fake_fetch)
    check("conflict: same repo in 3 URL spellings across 3 models -> registered ONCE",
          [x["decision"] for x in d] == ["registered"] and "Q" in s["engines"], d)


def test_renamed_repo_uses_canonical_url():
    s = store()
    moved = {"full_name": "NewOwner/quillan.cpp", "description": "standalone C++17 inference engine", "topics": []}
    ER.register_new_engines(s, [{"id": "m", "engines": [meas("Q", repo="https://github.com/oldowner/quillan.cpp")]}],
                            fetch=lambda u: moved)
    check("rename: registry url is GitHub's canonical full_name",
          s["engines"]["Q"]["url"] == "https://github.com/NewOwner/quillan.cpp", s["engines"]["Q"])


def test_backend_inference_matches_contract_enum():
    enum = json.loads((ROOT / "data" / "model_contract.json").read_text())[
        "properties"]["engines"]["additionalProperties"]["properties"]["backend"]["enum"]
    hw = {"CUDA": "RTX 4090", "Metal": "MacBook Pro M4", "CPU": "Ryzen 9 7950X", "ROCm": "RX 7900 XTX 24GB"}
    # The registry records exactly the backends measured, joined in the
    # canonical order (CUDA, ROCm, CPU, Metal). Before the AMD backend any mix
    # with CPU collapsed to 'CUDA / CPU / Metal' (claiming CUDA for a Metal+CPU
    # engine); an AMD-only engine must register as 'ROCm', not 'CUDA'.
    combos = {("CUDA",): "CUDA", ("Metal",): "Metal", ("CPU",): "CPU", ("ROCm",): "ROCm",
              ("CUDA", "Metal"): "CUDA / Metal", ("CUDA", "CPU"): "CUDA / CPU", ("Metal", "CPU"): "CPU / Metal",
              ("CUDA", "Metal", "CPU"): "CUDA / CPU / Metal", ("CUDA", "ROCm"): "CUDA / ROCm",
              ("ROCm", "CUDA"): "CUDA / ROCm", ("CUDA", "ROCm", "Metal"): "CUDA / ROCm / Metal",
              ("Metal", "CPU", "ROCm", "CUDA"): "CUDA / ROCm / CPU / Metal"}
    for combo, want in combos.items():
        got = ER._infer_backend([meas("E", hw=hw[b]) for b in combo])
        check(f"backend: {'+'.join(combo)} -> {want} (in contract enum)", got == want and got in enum, got)


def test_auto_entry_validates_against_contract():
    import jsonschema
    s = _real_store()
    ER.register_new_engines(s, [{"id": "q", "engines": [meas("quillan.cpp", repo="https://github.com/leeex1/quillan.cpp")]}],
                            fetch=fake_fetch)
    schema = json.loads((ROOT / "data" / "model_contract.json").read_text())
    errs = [e.message for e in jsonschema.validators.validator_for(schema)(schema).iter_errors(s)]
    check("contract: store with an auto-registered engine validates", not errs, errs[:2])


def test_search_contract_engine_repo_pattern():
    import jsonschema
    sc = json.loads((ROOT / "data" / "search_contract.json").read_text())
    sub = sc["properties"]["models"]["items"]["properties"]["engines"]["items"]["properties"]["engine_repo"]
    v = jsonschema.validators.validator_for(sc)(sub)
    for url, ok in [("https://github.com/leeex1/quillan.cpp", True), ("https://github.com/a/b/", True),
                    ("https://gitlab.com/a/b", False), ("https://github.com/a", False),
                    ("https://github.com/a/b/tree/main", False), ("github.com/a/b", False), ("TBD", False)]:
        check(f"contract: engine_repo {url!r} valid={ok}", v.is_valid(url) == ok)


def test_fetch_repo_meta_network_paths():
    import io
    import os
    import urllib.error
    import urllib.request
    seen = {}

    def fake_urlopen(req, timeout=0):
        seen["url"], seen["auth"] = req.full_url, req.get_header("Authorization")
        if "missing" in req.full_url:
            raise urllib.error.HTTPError(req.full_url, 404, "Not Found", {}, None)
        if "down" in req.full_url:
            raise urllib.error.URLError("network down")

        class R(io.BytesIO):
            def __enter__(self): return self
            def __exit__(self, *a): return False
        return R(json.dumps({"full_name": "a/b", "description": "LLM inference engine"}).encode())

    saved_open, saved_env = urllib.request.urlopen, dict(os.environ)
    urllib.request.urlopen = fake_urlopen
    os.environ.pop("ENGINE_REGISTRY_META_FILE", None)
    try:
        os.environ["GH_TOKEN"] = "tok123"
        m = ER.fetch_repo_meta("https://github.com/a/b")
        check("fetch: hits the GitHub repos API for the slug", seen.get("url") == "https://api.github.com/repos/a/b")
        check("fetch: sends the token when GH_TOKEN is set", seen.get("auth") == "Bearer tok123", seen.get("auth"))
        check("fetch: returns the repo JSON", m and m["full_name"] == "a/b", m)
        check("fetch: 404 -> None", ER.fetch_repo_meta("https://github.com/a/missing") is None)
        check("fetch: network error -> None", ER.fetch_repo_meta("https://github.com/a/down") is None)
        seen.clear()
        check("fetch: non-GitHub url -> None without any request",
              ER.fetch_repo_meta("https://gitlab.com/a/b") is None and not seen)
        os.environ.pop("GH_TOKEN", None)
        os.environ.pop("GITHUB_TOKEN", None)
        ER.fetch_repo_meta("https://github.com/a/b")
        check("fetch: no token -> no Authorization header", seen.get("auth") is None)
    finally:
        urllib.request.urlopen = saved_open
        os.environ.clear()
        os.environ.update(saved_env)


def test_offline_cache():
    import os
    saved = os.environ.get("ENGINE_REGISTRY_META_FILE")
    os.environ["ENGINE_REGISTRY_META_FILE"] = str(META_FIXTURE)
    try:
        m = ER.fetch_repo_meta("https://github.com/Leeex1/Quillan.cpp")
        check("cache: case-insensitive hit", m and m["full_name"].lower() == "leeex1/quillan.cpp", m)
        check("cache: miss -> None (unreachable)", ER.fetch_repo_meta("https://github.com/nobody/nothing") is None)
    finally:
        if saved is None:
            os.environ.pop("ENGINE_REGISTRY_META_FILE", None)
        else:
            os.environ["ENGINE_REGISTRY_META_FILE"] = saved


def test_engine_check_cli_every_branch():
    import os
    raw = {"backend": "cpu", "generated_utc": "2026-10-02T00:00:00Z", "models": [{"id": "m", "engines": [
        meas("quillan.cpp", repo="https://github.com/leeex1/quillan.cpp"),
        meas("DeepSeekHarness", repo="https://github.com/deepseek-ai/deepseek-harness"),
        meas("Ghost", repo="https://github.com/nobody/nothing"),
        meas("NoRepo"),
        meas("llama.cpp")]}]}
    with tempfile.TemporaryDirectory() as td:
        (Path(td) / "cpu-1.json").write_text(json.dumps(raw))
        env = dict(os.environ, ENGINE_REGISTRY_META_FILE=str(META_FIXTURE))
        p = subprocess.run([sys.executable, str(ROOT / "scripts" / "engine_registry.py"), "--check-raw", td],
                           capture_output=True, text=True, timeout=60, cwd=ROOT, env=env)
        after = json.loads((Path(td) / "cpu-1.json").read_text())
    out = p.stdout
    check("cli: exit 0 even with refusals (report only)", p.returncode == 0, p.stderr[-200:])
    check("cli: quillan.cpp -> registered (OK)", "OK   'quillan.cpp': registered" in out, out)
    check("cli: DeepSeekHarness -> not-engine (WARN)", "WARN 'DeepSeekHarness': not-engine" in out, out)
    check("cli: missing repo -> unreachable (WARN)", "WARN 'Ghost': unreachable" in out, out)
    check("cli: no engine_repo -> no-repo (WARN)", "WARN 'NoRepo': no-repo" in out, out)
    check("cli: registered engine not reported", "'llama.cpp'" not in out, out)
    check("cli: summary counts the 3 that will fail validation", "3 engine(s) will FAIL validation" in out, out)
    check("cli: report never modifies the raw snapshot", after == raw)
    check("cli: report never modifies models.json",
          json.loads((ROOT / "data" / "models.json").read_text())["engines"].get("quillan.cpp") is None)


def test_ingest_idempotent_and_model_backends():
    import os
    raw = json.loads(FIXTURE.read_text())
    for m in raw["models"]:
        for e in m["engines"]:
            if e["engine"] == "quillan.cpp":
                e["engine_repo"] = "https://github.com/leeex1/quillan.cpp"
    s = _real_store()
    saved_env = os.environ.get("ENGINE_REGISTRY_META_FILE")
    os.environ["ENGINE_REGISTRY_META_FILE"] = str(META_FIXTURE)
    try:
        with tempfile.TemporaryDirectory() as td:
            (Path(td) / "cpu-1.json").write_text(json.dumps(raw))
            saved = UT.RAW_DIR
            UT.RAW_DIR = Path(td)
            try:
                UT.ingest_raw_snapshots(s)
                first = copy.deepcopy(s["engines"]["quillan.cpp"])
                UT.ingest_raw_snapshots(s)
            finally:
                UT.RAW_DIR = saved
    finally:
        if saved_env is None:
            os.environ.pop("ENGINE_REGISTRY_META_FILE", None)
        else:
            os.environ["ENGINE_REGISTRY_META_FILE"] = saved_env
    check("ingest: re-ingest keeps the same registry entry (idempotent)", s["engines"]["quillan.cpp"] == first)
    check("ingest: exactly one quillan.cpp entry", sum(k == "quillan.cpp" for k in s["engines"]) == 1)
    q = next(m for m in s["models"] if m["id"] == "quillan-ronin")
    check("ingest: new model's backends include the auto-registered engine's backend (CPU)",
          "CPU" in q.get("backends", []), q.get("backends"))


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
    test_registered_engines_never_refused()
    test_classifier_signals()
    test_app_bundled_inference_server()
    test_search_prompts_look_up_missing_repos()
    test_repo_slug_edges()
    test_invalid_name_never_registered()
    test_conflicting_repos()
    test_renamed_repo_uses_canonical_url()
    test_backend_inference_matches_contract_enum()
    test_auto_entry_validates_against_contract()
    test_search_contract_engine_repo_pattern()
    test_fetch_repo_meta_network_paths()
    test_offline_cache()
    test_engine_check_cli_every_branch()
    test_ingest_idempotent_and_model_backends()
    print(f"\nPASSED {_PASS} | FAILED {_FAIL}")
    return 1 if _FAIL else 0


if __name__ == "__main__":
    raise SystemExit(main())
