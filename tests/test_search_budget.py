#!/usr/bin/env python3
"""Search-leg budget guards (issue #64).

The Metal (and earlier CPU) refresh leg died with 'No visible answer was
produced ... reasoning consumed the entire budget'. Root cause: the endpoint
capped the then-current SKU at 65,536 output tokens (our 384000 was silently
clamped) and effort 'low' still reasons; only reasoning OFF gives 0 reasoning
tokens. Plus the prompt built one giant final payload. The pin has since moved
to the dated deepseek/deepseek-v4.1-flash-1017, which declares NO
max_completion_tokens — so
HERMES_MAX_TOKENS keeps the conservative 65,536 until a live measurement.

  - test_makefile_budget_settings     searches --reasoning none, fix low, max_tokens <= 65536
  - test_no_stale_model_pin           no retired SKU string left in the pipeline files
  - test_prompts_write_per_query      all 3 search prompts write after EACH query
  - test_model_caps_evaluate          offline catalog: ok / cap overrun / missing / no reasoning
  - test_model_caps_cli               --catalog file exit codes; SKIP without key
  - test_write_raw_never_overwrites   same-second writes -> -2, -3; backend prefix intact

Run:  python3 tests/test_search_budget.py   or   make test
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import model_caps_check as MC  # noqa: E402
import update_trending as UT  # noqa: E402

MODEL = "deepseek/deepseek-v4.1-flash-1017"
# The UNDATED family alias the endpoint ALSO serves. Pinning it lets the provider
# repoint the model under a published image whose tag, budget and measured caps
# all stay put — the install-URL defect (#218) one layer down — so the pin must
# be the dated snapshot.
FLOATING = "deepseek/deepseek-v4.1-flash"
# The retired pin, split so THIS guard file never matches its own scan.
OLD_MODEL = "deepseek/deepseek-v4-flash" + "-0731"
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


def catalog(cap=65536, params=("max_tokens", "reasoning", "tools"), model=MODEL):
    return {"data": [{"id": model, "top_provider": {"context_length": 1048576, "max_completion_tokens": cap},
                      "supported_parameters": list(params)}]}


def mkvar(name):
    m = re.search(rf"^{name}\s*:=\s*(\S+)", (ROOT / "Makefile").read_text(), re.M)
    return m.group(1) if m else None


def test_makefile_budget_settings():
    check("make: searches run with reasoning OFF (none)", mkvar("HERMES_REASONING") == "none", mkvar("HERMES_REASONING"))
    check("make: fix-bot reasoning low (not medium/high)", mkvar("HERMES_FIX_REASONING") == "low",
          mkvar("HERMES_FIX_REASONING"))
    fix_recipe = next((l for l in (ROOT / "Makefile").read_text().splitlines()
                       if "make _fix" in l and "DOCKER_RUN" in l), "")
    check("make: the docker 'fix' wrapper forwards HERMES_FIX_REASONING into the container "
          "(fix_loop.sh retries with none when 'low' burns the budget)",
          "make _fix HERMES_FIX_REASONING=$(HERMES_FIX_REASONING)" in fix_recipe, fix_recipe)
    mt = int(mkvar("HERMES_MAX_TOKENS") or 0)
    check("make: HERMES_MAX_TOKENS within the 65,536 conservative bound", 0 < mt <= 65536, mt)
    check("make: model is the pinned SKU (cap kept conservative until re-measured)",
          mkvar("HERMES_MODEL") == MODEL, mkvar("HERMES_MODEL"))


def test_no_stale_model_pin():
    """Every pipeline file names the current pin, never the retired SKU.

    The model pin lives in one Makefile variable, but its NAME is repeated in
    the prompts, the skill, the workflows and the comments. A bump that updates
    the variable and leaves a stale SKU behind (issue #109 acceptance: no
    stale SKU reference left in Makefile / tests / skills / AGENTS.md /
    workflows / scripts) misleads the next reader
    and lets a live check quote a model the pipeline no longer runs.

    The scan is by DIRECTORY + suffix, never a hand-kept file list, so a new
    workflow, script, skill or test is covered the moment it lands. `data/`
    (the store, where the model itself is tracked as data) and
    `tests/fixtures/` (fixture model ids) are excluded on purpose; the guard
    constant is split in two so THIS file never matches its own scan.
    """
    targets = ["Makefile", "AGENTS.md", "README.md"]
    for d in (".github/workflows", "scripts", "skills", "tests"):
        targets += [str(p.relative_to(ROOT)) for p in sorted((ROOT / d).rglob("*"))
                    if p.is_file() and p.suffix in {".md", ".yml", ".yaml", ".sh", ".py"}
                    and "__pycache__" not in p.parts]
    stale = [rel for rel in targets
             if (ROOT / rel).exists() and OLD_MODEL in (ROOT / rel).read_text(errors="ignore")]
    check("pin: no retired SKU left in the pipeline files", not stale, stale)
    check("pin: the current SKU is named in the Makefile", MODEL in (ROOT / "Makefile").read_text())
    # The pin is the DATED snapshot, never the floating family alias: an alias can
    # be repointed while every artifact that records the pin still says the same
    # thing, so a bump back to it must go red here rather than silently at run time.
    pin = mkvar("HERMES_MODEL")
    check("pin: the pin is the dated snapshot, not the floating alias",
          pin == MODEL and pin != FLOATING, pin)


def test_prompts_write_per_query():
    text = (ROOT / "Makefile").read_text()
    for b in UT.SEARCH_LEGS:  # every search leg incl. amd
        prompt = text[text.index(f"_search-{b}:\n"):].split("\n", 2)[1]
        check(f"prompt {b}: write after EACH query", "After EACH query, immediately write only that query" in prompt)
        check(f"prompt {b}: never one big payload", "never collect all queries into one big payload" in prompt)
        check(f"prompt {b}: still uses --write-raw {b}", f"--write-raw {b} <" in prompt)


def test_model_caps_evaluate():
    check("caps: within cap + reasoning -> ok", MC.evaluate(catalog(), MODEL, 65536) == [])
    p = MC.evaluate(catalog(), MODEL, 384000)
    check("caps: 384000 > 65536 -> problem (the silent clamp)", len(p) == 1 and "65536" in p[0], p)
    check("caps: model not served -> problem", MC.evaluate(catalog(model="x/y"), MODEL, 1000) != [])
    p = MC.evaluate(catalog(params=("max_tokens", "tools")), MODEL, 1000)
    check("caps: no 'reasoning' param -> problem", len(p) == 1 and "reasoning" in p[0], p)
    check("caps: unknown cap -> no false alarm",
          MC.evaluate({"data": [{"id": MODEL, "top_provider": {}, "supported_parameters": ["reasoning"]}]},
                      MODEL, 10**6) == [])


def _cli(cat, mt, key=None, allow_unconfigured=None):
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
        json.dump(cat, f)
    args = [sys.executable, str(ROOT / "scripts" / "model_caps_check.py"), "--base", "http://x/v1",
            "--model", MODEL, "--max-tokens", str(mt)]
    if cat is not None:
        args += ["--catalog", f.name]
    env = dict(os.environ)
    env.pop("NOUS_API_KEY", None)
    env.pop("LIVE_CHECK_ALLOW_UNCONFIGURED", None)
    if key:
        env["NOUS_API_KEY"] = key
    if allow_unconfigured is not None:
        env["LIVE_CHECK_ALLOW_UNCONFIGURED"] = allow_unconfigured
    p = subprocess.run(args, capture_output=True, text=True, env=env, timeout=30)
    os.unlink(f.name)
    return p.returncode, p.stdout


def test_model_caps_cli():
    rc, out = _cli(catalog(), 65536)
    check("cli: fits -> exit 0", rc == 0 and "OK" in out, out)
    rc, out = _cli(catalog(), 384000)
    check("cli: overrun -> exit 1", rc == 1 and "FAIL" in out, out)
    # Issue #209: the live pre-flight must not go green having checked nothing.
    # Given no key and no catalog
    rc, out = _cli(None, 1000)

    # When  the caps check runs
    # Then  it FAILS, naming the variable and what stayed unverified — not a SKIP
    check("cli: no key, no catalog -> non-zero", rc != 0, out)
    check("cli: no key -> it names the missing variable", "NOUS_API_KEY is not set" in out, out)
    check("cli: no key -> it says what could not be checked",
          "cannot be read" in out and "unverified" in out, out)
    check("cli: no key -> it is not a SKIP", "SKIP" not in out, out)

    # Given the same, with the explicit opt-out
    rc, out = _cli(None, 1000, allow_unconfigured="1")

    # Then  it reports NOT CONFIGURED and exits 0
    check("cli: opt-out -> exit 0", rc == 0 and "NOT CONFIGURED" in out, out)


def test_write_raw_never_overwrites():
    with tempfile.TemporaryDirectory() as td:
        saved_dir, saved_now = UT.RAW_DIR, UT.now_utc
        UT.RAW_DIR = Path(td)
        from datetime import datetime, timezone
        UT.now_utc = lambda: datetime(2026, 10, 2, 1, 2, 3, tzinfo=timezone.utc)
        try:
            paths = [UT.write_raw_snapshot("metal", {"backend": "metal", "models": [{"id": f"m{i}"}]})
                     for i in range(3)]
        finally:
            UT.RAW_DIR, UT.now_utc = saved_dir, saved_now
        names = [p.name for p in paths]
        check("raw: three same-second writes -> three files", len(set(names)) == 3, names)
        check("raw: suffixes -2, -3", names == ["metal-20261002-010203.json", "metal-20261002-010203-2.json",
                                                "metal-20261002-010203-3.json"], names)
        check("raw: every file keeps its own models", [json.loads(p.read_text())["models"][0]["id"] for p in paths]
              == ["m0", "m1", "m2"])
        check("raw: backend is still the first '-' token", all(n.split("-")[0] == "metal" for n in names))


def test_the_model_id_matches_the_contract():
    """Issue #464: a search leg wrote `qwen3.8-27b-mlx_srv`, whose `_` violates the store
    contract's `^[a-z0-9][a-z0-9.\\-]*$`. It reached `data/models.json` AND the raw snapshot,
    so the refresh PR went red twice, and the id could never merge with its own model —
    every lookup is by id. The id is now normalised where it is WRITTEN (`--write-raw`) and
    again at ingest, and an id that already matches is never touched (rule 3b)."""
    check("id: the measured 'mlx_srv' becomes a legal id",
          UT.contract_id("qwen3.8-27b-mlx_srv") == "qwen3.8-27b-mlx-srv")
    check("id: uppercase, spaces and repeats are folded",
          UT.contract_id("Qwen3.8-27B_MLX srv") == "qwen3.8-27b-mlx-srv")
    check("id: a legal id is unchanged", UT.contract_id("good.id-2") == "good.id-2")
    check("id: a value with nothing legal left yields empty (caller falls back)",
          UT.contract_id("___") == "")
    for v in ("qwen3.8-27b-mlx_srv", "Qwen3.8-27B_MLX srv", "___", "ÄÖ x"):
        check(f"id: {v!r} normalises INTO the contract pattern",
              bool(UT.ID_PATTERN.match(UT.contract_id(v) or "unknown")))

    # And  ingest applies the same rule to a raw row that predates it
    m = UT.normalize_model({"id": "qwen3.8-27b-mlx_srv", "name": "Qwen3.8 27B mlx_srv",
                            "engines": [{"engine": "mlx-serve", "tps": "20", "hardware": "M5",
                                         "quant": "Q4", "date": "2026-10-20",
                                         "source_post": "https://lightbrd.com/u/status/1"}]},
                           {"models": [], "engines": {}})
    check("id: ingest normalises the id it stores", m["id"] == "qwen3.8-27b-mlx-srv", m["id"])
    # …and an existing model's id is never rewritten (ingest matches it by id first)
    good = UT.normalize_model({"id": "qwen3.8-27b", "name": "Qwen3.8 27B", "engines": [
        {"engine": "vLLM", "tps": "40", "hardware": "RTX 4090", "quant": "NVFP4",
         "date": "2026-10-20", "source_post": "https://lightbrd.com/u/status/2"}]},
        {"models": [], "engines": {}})
    check("id: a legal id is left byte-identical", good["id"] == "qwen3.8-27b", good["id"])

    with tempfile.TemporaryDirectory() as td:
        saved_dir, saved_now = UT.RAW_DIR, UT.now_utc
        UT.RAW_DIR = Path(td)
        try:
            path = UT.write_raw_snapshot("metal", {"models": [
                {"id": "qwen3.8-27b-mlx_srv", "name": "Qwen3.8 27B mlx_srv"}]})
            written = json.loads(Path(path).read_text())["models"][0]["id"]
        finally:
            UT.RAW_DIR, UT.now_utc = saved_dir, saved_now
    check("id: the RAW SNAPSHOT itself is written legal", written == "qwen3.8-27b-mlx-srv", written)


def test_write_raw_normalizes_hf_ref():
    """An `hf` field is a bare repo id: validate/README build the URL by
    prefixing it themselves, so a full URL (or the doubled prefix the search
    agent produced, 'https://huggingface.co/https://huggingface.co/X') written
    into data/raw 404s every raw-hf link check. --write-raw, the single funnel
    every search prompt writes through, must collapse it."""
    check("hf: bare id unchanged", UT.normalize_hf_ref("Qwen/Qwen3-14B") == "Qwen/Qwen3-14B")
    check("hf: full URL -> repo id",
          UT.normalize_hf_ref("https://huggingface.co/Qwen/Qwen3-14B") == "Qwen/Qwen3-14B")
    check("hf: doubled prefix -> repo id",
          UT.normalize_hf_ref("https://huggingface.co/https://huggingface.co/Qwen/Qwen3.8-Flash-Next-125B")
          == "Qwen/Qwen3.8-Flash-Next-125B")
    check("hf: trailing slash / padding stripped",
          UT.normalize_hf_ref("  https://huggingface.co/Qwen/Qwen3-14B/  ") == "Qwen/Qwen3-14B")
    check("hf: non-string passes through", UT.normalize_hf_ref(None) is None)

    with tempfile.TemporaryDirectory() as td:
        saved_dir, saved_now = UT.RAW_DIR, UT.now_utc
        UT.RAW_DIR = Path(td)
        from datetime import datetime, timezone
        UT.now_utc = lambda: datetime(2026, 10, 14, 11, 10, 33, tzinfo=timezone.utc)
        try:
            p = UT.write_raw_snapshot("amd", {
                "backend": "amd",
                "models": [{
                    "id": "qwen3-14b",
                    "hf": "https://huggingface.co/https://huggingface.co/Qwen/Qwen3-14B",
                    "formats": [{"name": "GGUF", "hf": "https://huggingface.co/Qwen/Qwen3-14B"}],
                }],
            })
            m = json.loads(p.read_text())["models"][0]
        finally:
            UT.RAW_DIR, UT.now_utc = saved_dir, saved_now
        check("raw: model hf collapsed on write", m["hf"] == "Qwen/Qwen3-14B", m["hf"])
        check("raw: format hf collapsed on write", m["formats"][0]["hf"] == "Qwen/Qwen3-14B", m["formats"])


def test_normalize_model_collapses_hf():
    """Defense in depth: a raw model ingested through normalize_model (a slug
    that did not go through --write-raw) must not land a URL in the store."""
    store = {"models": [], "engines": {"llama.cpp": {"url": "https://github.com/ggml-org/llama.cpp",
                                                     "backend": "CUDA"}}}
    m = UT.normalize_model({
        "id": "qwen3-14b", "name": "Qwen3-14B",
        "hf": "https://huggingface.co/https://huggingface.co/Qwen/Qwen3-14B",
        "formats": [{"name": "GGUF", "hf": "https://huggingface.co/Qwen/Qwen3-14B"}],
        "engines": [{"engine": "llama.cpp", "tps": "40", "date": "2026-10-14",
                     "source_post": "https://lightbrd.com/u/status/1"}],
    }, store)
    check("normalize_model: model hf collapsed", m["hf"] == "Qwen/Qwen3-14B", m["hf"])
    check("normalize_model: format hf collapsed", m["formats"][0]["hf"] == "Qwen/Qwen3-14B", m["formats"])


def main() -> int:
    print("search-leg budget guards (issue #64)")
    test_makefile_budget_settings()
    test_no_stale_model_pin()
    test_prompts_write_per_query()
    test_model_caps_evaluate()
    test_model_caps_cli()
    test_write_raw_never_overwrites()
    test_the_model_id_matches_the_contract()
    test_write_raw_normalizes_hf_ref()
    test_normalize_model_collapses_hf()
    print(f"\nPASSED {_PASS} | FAILED {_FAIL}")
    return 1 if _FAIL else 0


if __name__ == "__main__":
    raise SystemExit(main())
