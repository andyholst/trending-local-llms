#!/usr/bin/env python3
"""Model-specific engine forks (issue #62).

Ternary Bonsai 2's PTQ1_0 / PQ2_0 GGUFs only run on the PrismML llama.cpp fork
(prism branch); stock ggml-org/llama.cpp rejects them. Posts still say
'llama.cpp', so a model-level `engine_aliases` maps the posted name to the
registered fork on ingest and on every sort.

  - test_real_store_bonsai_links_the_fork       README: no Bonsai figure links stock llama.cpp
  - test_alias_applied_on_sort_idempotent       engines + supported_engines renamed once
  - test_raw_llama_cpp_merges_into_fork_rows    ingest aliases BEFORE merge (no duplicate rows)
  - test_other_models_keep_stock_llama_cpp      aliases are per model
  - test_validator_engine_aliases               unaliased leftover / unregistered target / wrong url -> FAIL
  - test_fork_registered_and_known              registry + KNOWN_ENGINE_URLS agree
  - test_prompts_mention_forks                  all 3 search prompts

Run:  python3 tests/test_engine_aliases.py   or   make test
"""
from __future__ import annotations

import copy
import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import update_trending as UT  # noqa: E402
import validate as V  # noqa: E402

FORK = "llama.cpp (PrismML fork)"
FORK_URL = "https://github.com/PrismML-Eng/llama.cpp"
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


def real_store() -> dict:
    return json.loads((ROOT / "data" / "models.json").read_text())


def bonsai(s):
    return next(m for m in s["models"] if m["id"] == "bonsai-2-27b")


def test_real_store_bonsai_links_the_fork():
    s = real_store()
    check("store: Bonsai 2 27B declares the fork alias", bonsai(s).get("engine_aliases") == {"llama.cpp": FORK})
    md = UT.render_readme(copy.deepcopy(s), V._as_of(s))
    rows = [ln for ln in md.split("\n") if "Bonsai 2 27B" in ln and ln.startswith("|")]
    check("readme: Bonsai rows exist", len(rows) >= 3, len(rows))
    check("readme: no Bonsai row links stock ggml-org/llama.cpp",
          not any("ggml-org/llama.cpp" in r for r in rows), [r[:80] for r in rows if "ggml-org" in r])
    check("readme: Bonsai CUDA figures link the PrismML fork", any(f"]({FORK_URL})" in r for r in rows))
    guide = md.split("## ⚙️", 1)[1]
    check("readme: engine guide lists the fork with models measured = 1",
          f"| [{FORK}]({FORK_URL}) | CUDA / CPU / Metal | 1 |" in guide)


def _model():
    return {"id": "b", "name": "B", "engine_aliases": {"llama.cpp": FORK},
            "supported_engines": ["llama.cpp", FORK, "MLX"], "last_seen": "2026-09-30",
            "engagement": {"seen_posts": []},
            "engines": [{"engine": "llama.cpp", "tps": "71", "hardware": "RTX 5060 Ti 16GB", "quant": "PTQ1_0",
                         "date": "2026-09-30", "source_post": "https://lightbrd.com/a/status/1"}]}


def test_alias_applied_on_sort_idempotent():
    from datetime import datetime, timezone
    m = _model()
    UT.sort_models([m], datetime(2026, 10, 1, tzinfo=timezone.utc))
    UT.sort_models([m], datetime(2026, 10, 1, tzinfo=timezone.utc))
    check("sort: measurement renamed to the fork", [e["engine"] for e in m["engines"]] == [FORK], m["engines"])
    check("sort: supported_engines renamed + deduped, order kept", m["supported_engines"] == [FORK, "MLX"],
          m["supported_engines"])


def test_raw_llama_cpp_merges_into_fork_rows():
    s = real_store()
    before = len(bonsai(s)["engines"])
    existing = next(e for e in bonsai(s)["engines"] if e["engine"] == FORK)
    raw = {"backend": "nvidia", "generated_utc": "2026-10-01T00:00:00Z", "models": [{
        "id": "bonsai-2-27b", "name": "Bonsai 2 27B",
        "engines": [dict(existing, engine="llama.cpp")]}]}  # the same figure, posted as plain llama.cpp
    with tempfile.TemporaryDirectory() as td:
        (Path(td) / "nvidia-1.json").write_text(json.dumps(raw))
        saved = UT.RAW_DIR
        UT.RAW_DIR = Path(td)
        try:
            UT.ingest_raw_snapshots(s)
        finally:
            UT.RAW_DIR = saved
    engs = bonsai(s)["engines"]
    check("ingest: raw 'llama.cpp' stored as the fork", all(e["engine"] != "llama.cpp" for e in engs),
          [e["engine"] for e in engs])
    check("ingest: merged into the existing fork row (no duplicate)", len(engs) == before, (before, len(engs)))


def test_unaliased_store_plus_raw_no_duplicates():
    """REGRESSION: the alias is declared but the STORED rows still say
    'llama.cpp' (the state right after the alias is added). Ingesting a raw
    snapshot with the same figures must alias BOTH sides before merging —
    aliasing only the incoming rows left them unmatched and duplicated
    54.1 / 67-71 on the first regeneration."""
    s = real_store()
    b = bonsai(s)
    for e in b["engines"]:
        if e["engine"] == FORK:
            e["engine"] = "llama.cpp"
    before = len(b["engines"])
    raw = {"backend": "nvidia", "generated_utc": "2026-10-01T00:00:00Z", "models": [{
        "id": "bonsai-2-27b", "name": "Bonsai 2 27B",
        "engines": [dict(e) for e in b["engines"] if e["engine"] == "llama.cpp"]}]}
    with tempfile.TemporaryDirectory() as td:
        (Path(td) / "nvidia-1.json").write_text(json.dumps(raw))
        saved = UT.RAW_DIR
        UT.RAW_DIR = Path(td)
        try:
            UT.ingest_raw_snapshots(s)
        finally:
            UT.RAW_DIR = saved
    engs = bonsai(s)["engines"]
    check("ingest: unaliased store + same raw figures -> no duplicate rows", len(engs) == before, (before, len(engs)))
    check("ingest: every llama.cpp row now the fork", all(e["engine"] != "llama.cpp" for e in engs))


def test_other_models_keep_stock_llama_cpp():
    s = real_store()
    other = [m for m in s["models"] if m["id"] != "bonsai-2-27b" and any(e["engine"] == "llama.cpp" for e in m["engines"])]
    check("scope: other models still use stock llama.cpp", len(other) >= 1, [m["id"] for m in other])


def _alias_errors(s):
    V.FAILURES.clear()
    try:
        V.check_engine_aliases(s)
        return list(V.FAILURES)
    finally:
        V.FAILURES.clear()


def test_validator_engine_aliases():
    s = real_store()
    check("validator: real store passes", not _alias_errors(s), _alias_errors(s))
    left = copy.deepcopy(s)
    bonsai(left)["engines"][0]["engine"] = "llama.cpp"
    check("validator: a measurement still on 'llama.cpp' -> FAIL",
          any("should be" in e for e in _alias_errors(left)))
    missing = copy.deepcopy(s)
    del missing["engines"][FORK]
    check("validator: alias target not in registry -> FAIL",
          any("not a registered engine" in e for e in _alias_errors(missing)))
    wrong = copy.deepcopy(s)
    wrong["engines"][FORK]["url"] = "https://github.com/ggml-org/llama.cpp"
    check("validator: alias target with the wrong repo url -> FAIL",
          any("known-good" in e for e in _alias_errors(wrong)))


def test_fork_registered_and_known():
    s = real_store()
    check("registry: fork url", s["engines"].get(FORK, {}).get("url") == FORK_URL)
    check("validate: fork in KNOWN_ENGINE_URLS", V.KNOWN_ENGINE_URLS.get(FORK) == FORK_URL)


def test_prompts_mention_forks():
    text = (ROOT / "Makefile").read_text()
    for b in ("nvidia", "metal", "cpu"):
        body = text[text.index(f"_search-{b}:\n"):].split("\n", 2)[1]
        check(f"prompt {b}: record forks by their registry name",
              "fork or custom build" in body and "engines registry" in body)


def main() -> int:
    print("model-specific engine forks (issue #62)")
    test_real_store_bonsai_links_the_fork()
    test_alias_applied_on_sort_idempotent()
    test_raw_llama_cpp_merges_into_fork_rows()
    test_unaliased_store_plus_raw_no_duplicates()
    test_other_models_keep_stock_llama_cpp()
    test_validator_engine_aliases()
    test_fork_registered_and_known()
    test_prompts_mention_forks()
    print(f"\nPASSED {_PASS} | FAILED {_FAIL}")
    return 1 if _FAIL else 0


if __name__ == "__main__":
    raise SystemExit(main())
