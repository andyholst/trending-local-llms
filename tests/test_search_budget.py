#!/usr/bin/env python3
"""Search-leg budget guards (issue #64).

The Metal (and earlier CPU) refresh leg died with 'No visible answer was
produced ... reasoning consumed the entire budget'. Root cause: the endpoint
caps deepseek-v4-flash-0731 at 65,536 output tokens (our 384000 was silently
clamped) and effort 'low' still reasons; only reasoning OFF gives 0 reasoning
tokens. Plus the prompt built one giant final payload.

  - test_makefile_budget_settings     searches --reasoning none, fix low, max_tokens <= 65536
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

MODEL = "deepseek/deepseek-v4-flash-0731"
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
    check("make: HERMES_MAX_TOKENS within the 65,536 provider cap", 0 < mt <= 65536, mt)
    check("make: model is the 0731 SKU the cap was measured for", mkvar("HERMES_MODEL") == MODEL, mkvar("HERMES_MODEL"))


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


def _cli(cat, mt, key=None):
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
        json.dump(cat, f)
    args = [sys.executable, str(ROOT / "scripts" / "model_caps_check.py"), "--base", "http://x/v1",
            "--model", MODEL, "--max-tokens", str(mt)]
    if cat is not None:
        args += ["--catalog", f.name]
    env = dict(os.environ)
    env.pop("NOUS_API_KEY", None)
    if key:
        env["NOUS_API_KEY"] = key
    p = subprocess.run(args, capture_output=True, text=True, env=env, timeout=30)
    os.unlink(f.name)
    return p.returncode, p.stdout


def test_model_caps_cli():
    rc, out = _cli(catalog(), 65536)
    check("cli: fits -> exit 0", rc == 0 and "OK" in out, out)
    rc, out = _cli(catalog(), 384000)
    check("cli: overrun -> exit 1", rc == 1 and "FAIL" in out, out)
    rc, out = _cli(None, 1000)
    check("cli: no key, no catalog -> SKIP exit 0", rc == 0 and "SKIP" in out, out)


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


def main() -> int:
    print("search-leg budget guards (issue #64)")
    test_makefile_budget_settings()
    test_prompts_write_per_query()
    test_model_caps_evaluate()
    test_model_caps_cli()
    test_write_raw_never_overwrites()
    print(f"\nPASSED {_PASS} | FAILED {_FAIL}")
    return 1 if _FAIL else 0


if __name__ == "__main__":
    raise SystemExit(main())
