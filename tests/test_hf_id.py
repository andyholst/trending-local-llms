#!/usr/bin/env python3
"""One HF identifier definition, and the raw-snapshot correction that uses it.

Measured (issue #165, refresh PR #160): a raw snapshot carried a full URL in `hf`

    "hf": "https://huggingface.co/Qwen/Qwen3.6-35B-A3B"

and every consumer that builds a link from that field prefixed it again —
`https://huggingface.co/https://huggingface.co/Qwen/Qwen3.6-35B-A3B` — turning a
good repo into a failing link and the refresh PR red.

The entity under test is the product code: `scripts/hf_id.normalise` and
`scripts/self_correct_raw.correct_snapshot` (driven on a real snapshot file in a
temp data dir).
"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import hf_id  # noqa: E402
import self_correct_raw as SCR  # noqa: E402

from wiring import wired  # noqa: E402  (issues #176/#192)

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


def test_normalise_accepts_every_shape_the_search_emits():
    """A bare id, a full link, a link into a file/branch, and the noisy tails all
    reduce to `owner/repo` — the form the store and the link builders require."""
    cases = [
        # Given/When: the value the search emitted -> Then: the id
        ("Qwen/Qwen3-14B", "Qwen/Qwen3-14B"),
        ("  Qwen/Qwen3-14B  ", "Qwen/Qwen3-14B"),
        ("https://huggingface.co/Qwen/Qwen3.6-35B-A3B", "Qwen/Qwen3.6-35B-A3B"),
        ("http://huggingface.co/Qwen/Qwen3-14B", "Qwen/Qwen3-14B"),
        ("https://www.huggingface.co/Qwen/Qwen3-14B", "Qwen/Qwen3-14B"),
        ("https://hf.co/Qwen/Qwen3-14B", "Qwen/Qwen3-14B"),
        ("huggingface.co/Qwen/Qwen3-14B", "Qwen/Qwen3-14B"),
        ("https://huggingface.co/Qwen/Qwen3-14B/", "Qwen/Qwen3-14B"),
        ("https://huggingface.co/Qwen/Qwen3-14B.git", "Qwen/Qwen3-14B"),
        ("https://huggingface.co/Qwen/Qwen3-14B/tree/main", "Qwen/Qwen3-14B"),
        ("https://huggingface.co/Qwen/Qwen3-14B/blob/main/model.gguf", "Qwen/Qwen3-14B"),
        ("https://huggingface.co/Qwen/Qwen3-14B?tab=files", "Qwen/Qwen3-14B"),
        ("https://huggingface.co/Qwen/Qwen3-14B#usage", "Qwen/Qwen3-14B"),
        ("https://huggingface.co/datasets/org/data", "datasets/org"),
    ]
    for raw, want in cases:
        check(f"normalise({raw!r}) -> {want!r}", hf_id.normalise(raw) == want,
              hf_id.normalise(raw))

    # A URL that cannot become owner/repo is MISSING, never a value to build on;
    # a bare non-URL token is passed through for validate to judge.
    for raw in ("https://huggingface.co/", "https://huggingface.co/onlyone", ""):
        check(f"normalise({raw!r}) -> '' (missing)", hf_id.normalise(raw) == "",
              hf_id.normalise(raw))
    check("normalise('not-an-id') passes through (validate decides)",
          hf_id.normalise("not-an-id") == "not-an-id", hf_id.normalise("not-an-id"))


def _snapshot(hf_value, format_hf=None):
    return {
        "backend": "amd", "generated_utc": "2026-10-14T11:10:33Z",
        "models": [{
            "id": "qwen3.6-35b-a3b", "name": "Qwen3.6 35B A3B",
            "full_name": "Qwen3.6-35B-A3B", "type": "LLM", "license": "Apache 2.0",
            "params": "35B", "hf": hf_value,
            "formats": ([{"name": "GGUF", "hf": format_hf}] if format_hf else []),
            "vram_tier": "24GB", "vram_min": "20GB", "backends": ["ROCm"],
            "engines": [{"engine": "llama.cpp", "tps": "40", "date": "2026-10-14",
                         "source_post": "https://x.com/i/status/1"}],
            "last_seen": "2026-10-14",
        }],
    }


def test_correct_raw_reduces_a_url_shaped_hf():
    """The correction step fixes the SHAPE it receives (issue #165): the measured
    URL becomes an id, so no link can ever be prefixed twice."""
    with tempfile.TemporaryDirectory() as td:
        data = Path(td)
        raw = data / "raw"
        raw.mkdir()
        (data / "models.json").write_text(json.dumps({"engines": {}, "models": []}))
        snap = raw / "amd-20261014-111033.json"
        url = "https://huggingface.co/Qwen/Qwen3.6-35B-A3B"
        snap.write_text(json.dumps(_snapshot(url, format_hf=url)))

        # When  the correction step runs against that snapshot
        env = {**__import__("os").environ, "TRENDING_DATA_DIR": str(data)}
        proc = subprocess.run([sys.executable, "scripts/self_correct_raw.py"],
                              cwd=ROOT, capture_output=True, text=True, env=env)
        fixed = json.loads(snap.read_text())
        got = fixed["models"][0]["hf"]
        got_format = fixed["models"][0]["formats"][0]["hf"]

        # Then  the id is an owner/repo and the correction is reported
        check("correct-raw: the URL-shaped hf becomes an id",
              got == "Qwen/Qwen3.6-35B-A3B", got)
        check("correct-raw: a format's hf is corrected too",
              got_format == "Qwen/Qwen3.6-35B-A3B", got_format)
        check("correct-raw: the correction is reported",
              "hf <- Qwen/Qwen3.6-35B-A3B" in proc.stdout, proc.stdout[-300:])
        check("correct-raw: no doubled URL is left in the file",
              "huggingface.co/https" not in snap.read_text(), snap.read_text()[:200])

        # Given a URL that cannot become an id
        snap.write_text(json.dumps(_snapshot("https://huggingface.co/onlyone")))
        proc = subprocess.run([sys.executable, "scripts/self_correct_raw.py"],
                              cwd=ROOT, capture_output=True, text=True, env=env)
        after = json.loads(snap.read_text())

        # Then  it counts as MISSING — never a value to build a link on. The row is
        # known to the store, so its hf is repaired from there (it is not thrown
        # away), and the step SUCCEEDS: one bad value must never abort a refresh
        # (issue #381).
        kept = after["models"][0] if after["models"] else {}
        check("correct-raw: an irreducible URL counts as missing (reported)",
              "hf <- MISSING" in proc.stdout, proc.stdout[-400:])
        check("correct-raw: a known model is repaired from the store, not dropped",
              kept.get("id") == "qwen3.6-35b-a3b"
              and kept.get("hf") == "Qwen/Qwen3.6-35B-A3B",
              kept.get("hf"))
        check("correct-raw: it is not a failed step (exit 0)",
              proc.returncode == 0, proc.returncode)


def test_the_link_checker_builds_links_with_the_same_definition():
    """`_extract_links` is where the doubled link SURFACED (issue #165): it built
    the URL with a bare prefix, so a URL-shaped `hf` produced
    `https://huggingface.co/https://…`. It must use the one definition too."""
    sys.path.insert(0, str(ROOT / "scripts"))
    import validate as V  # noqa: E402

    # Given a store and a raw snapshot whose `hf` is a full URL (the measured shape)
    url = "https://huggingface.co/Qwen/Qwen3.6-35B-A3B"
    store = {"engines": {}, "models": [{
        "id": "qwen3.6-35b-a3b", "hf": url,
        "formats": [{"name": "GGUF", "hf": url}], "engines": [],
    }]}
    with tempfile.TemporaryDirectory() as td:
        raw = Path(td) / "raw"
        raw.mkdir()
        (raw / "amd-1.json").write_text(json.dumps(
            {"backend": "amd", "generated_utc": "2026-10-14T11:10:33Z",
             "models": [{"id": "qwen3.6-35b-a3b", "hf": url, "engines": []}]}))
        saved = V.RAW_DIR
        V.RAW_DIR = raw
        try:
            links = V._extract_links(store)
        finally:
            V.RAW_DIR = saved

    # Then  every HF link is built ONCE, from the id
    hf_links = [(kind, u) for kind, _, u in links if kind.endswith("hf")]
    check("extract_links: HF links exist", bool(hf_links), str(links))
    check("extract_links: no doubled URL is produced",
          all("huggingface.co/https" not in u for _, u in hf_links), str(hf_links))
    check("extract_links: every HF link is the canonical one",
          all(u == url for _, u in hf_links), str(hf_links))

    # Then  the checker itself uses the one definition
    src = (ROOT / "scripts" / "validate.py").read_text()
    check("validate: builds HF links through the normaliser",
          src.count("normalise_hf(") >= 5, str(src.count("normalise_hf(")))


def test_the_link_builders_use_the_same_definition():
    """One definition: the README builder and the corrector must import it, so a
    URL-shaped value cannot be prefixed twice anywhere (issue #165)."""
    ut = (ROOT / "scripts" / "update_trending.py").read_text()
    check("update_trending: builds the HF link through the normaliser",
          "normalise_hf(m.get('hf', ''))" in ut, "")
    scr = (ROOT / "scripts" / "self_correct_raw.py").read_text()
    check("self_correct_raw: imports the same definition",
          "from hf_id import normalise as normalise_hf" in scr, "")
    mk = (ROOT / "Makefile").read_text()
    check("make: the tests are wired into the suite",
          wired(__file__), "")


def main() -> int:
    print("HF identifier (one definition) + raw-snapshot correction")
    test_normalise_accepts_every_shape_the_search_emits()
    test_correct_raw_reduces_a_url_shaped_hf()
    test_the_link_checker_builds_links_with_the_same_definition()
    test_the_link_builders_use_the_same_definition()
    print(f"\nPASSED {_PASS} | FAILED {_FAIL}")
    return 1 if _FAIL else 0


if __name__ == "__main__":
    raise SystemExit(main())
