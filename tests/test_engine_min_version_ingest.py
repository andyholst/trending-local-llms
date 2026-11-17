#!/usr/bin/env python3
"""Engine-build fill at ingest (issue #877).

#876 widened the `engine_min_version` detector so `make data-gaps` can SEE the
build sentences posts actually use and names that class (`captured:engine_min_version`)
an INGEST job. This test locks the half that CLOSES it: `fill_engine_min_version`
computes the structured key from the raw measurement's OWN captured text during
`ingest_raw_snapshots`, and the merge carries it onto the store row. Every value
must be the matched phrase VERBATIM, cited by the measurement's own `source_post`
(rule 3, nothing invented); the fill is additive (rule 3b: a missing key only);
the precision class stays exact (no phrase, no field); `why` prose never fills
anything (#470); and the detector has exactly ONE implementation (rule 6d).

Run:  python3 tests/test_engine_min_version_ingest.py    or   make test
"""
from __future__ import annotations

import copy
import json
import re
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import data_gap_analysis as G  # noqa: E402
import update_trending as UT  # noqa: E402

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


def store_with(models: list[dict]) -> dict:
    return {"generated_utc": "2026-11-13T06:00:00Z",
            "engines": {"llama.cpp": {"backend": "CUDA / CPU", "note": "x",
                                      "url": "https://github.com/ggml-org/llama.cpp"},
                        "MLX": {"backend": "Metal", "note": "x",
                                "url": "https://github.com/ml-explore/mlx"}},
            "models": models}


def model(mid: str, **extra) -> dict:
    m = {"id": mid, "name": mid, "full_name": mid, "type": "LLM", "license": "Apache 2.0",
         "params": "27B", "hf": f"a/{mid}", "vram_tier": "16GB", "vram_min": "12GB",
         "backends": ["CUDA"], "supported_engines": ["llama.cpp"], "why": "w",
         "last_seen": "2026-11-01", "engagement": {},
         "engines": [{"engine": "llama.cpp", "tps": "91", "hardware": "RTX 4090 24GB",
                      "quant": "Q4_K_M", "date": "2026-11-01", "likes": 1,
                      "source_post": "https://lightbrd.com/u/status/111"}]}
    m.update(extra)
    return m


def write_raw(raw_dir: Path, models: list[dict], stamp: str = "20261113-120000") -> Path:
    p = raw_dir / f"cpu-{stamp}.json"
    p.write_text(json.dumps({"generated_utc": "2026-11-13T12:00:00Z",
                             "backend": "cpu", "models": models}))
    return p


def ingest_fixture(store: dict, raw_dir: Path) -> tuple[int, int]:
    """Run the REAL ingest over the fixture directory (since=None merges every
    snapshot; the product seam, no stand-ins)."""
    return UT.ingest_raw_snapshots(store, since=None, verify_hf=False, raw_dir=raw_dir)


def find_store_model(store: dict, mid: str) -> dict:
    return next(m for m in store["models"] if m.get("id") == mid)


POST_BUILT = "https://lightbrd.com/u/status/2141"
PHRASE = "BigMoeOnEdge on stock llama.cpp (untouched upstream, submodule)"


def test_a_build_phrase_in_the_captured_text_fills_the_field():
    """The gap #877 exists to close: the post's OWN measurement text states the
    build, and after ingest the store measurement carries it verbatim."""
    with tempfile.TemporaryDirectory() as td:
        raw = Path(td) / "raw"
        raw.mkdir()
        store = store_with([model("built-model")])
        write_raw(raw, [model("built-model", engines=[{
            "engine": "llama.cpp", "tps": "42", "hardware": "Radeon R9700 32GB",
            "quant": PHRASE, "date": "2026-11-13", "likes": 40,
            "source_post": POST_BUILT}])])
        added, updated = ingest_fixture(store, raw)
        row = find_store_model(store, "built-model")
        filled = [e for e in row["engines"] if e.get("engine_min_version")]
        check("a build phrase in the captured text fills the field",
              len(filled) == 1
              and filled[0]["engine_min_version"] == G._ENGINE_MIN_TEXT.search(PHRASE).group(0)
              and filled[0]["source_post"] == POST_BUILT
              and updated == 1,
              str(row["engines"]))


def test_no_build_phrase_fills_nothing():
    """#213/#458's precision class stays exact: capacity + speed beside a quant is
    NOT a build claim, and no other field of the measurement changes."""
    with tempfile.TemporaryDirectory() as td:
        raw = Path(td) / "raw"
        raw.mkdir()
        store = store_with([model("plain-model")])
        incoming = {"engine": "llama.cpp", "tps": "150",
                    "hardware": "RTX 4090 24GB", "quant": "Q4_K_M (~14.6GB)",
                    "date": "2026-11-13", "likes": 5,
                    "source_post": "https://lightbrd.com/u/status/222"}
        write_raw(raw, [model("plain-model", engines=[dict(incoming)])])
        ingest_fixture(store, raw)
        row = find_store_model(store, "plain-model")
        check("no build phrase fills nothing",
              all("engine_min_version" not in e for e in row["engines"]),
              str(row["engines"]))
        check("no other field changed",
              all(e.get("tps") == incoming["tps"] and e.get("quant") == incoming["quant"]
                  for e in row["engines"] if e.get("source_post") == incoming["source_post"]))


def test_an_existing_value_is_never_overwritten():
    """Additive-only (rule 3b): a stated `engine_min_version` survives
    byte-identical even when the text would match a different phrase."""
    kept_value = "llama.cpp b1000"
    m = model("kept-model", engines=[{
        "engine": "llama.cpp", "tps": "14", "hardware": "Radeon R9700 32GB",
        "quant": PHRASE, "engine_min_version": kept_value, "date": "2026-11-13",
        "source_post": POST_BUILT}])
    before = copy.deepcopy(m)
    filled = UT.fill_engine_min_version([m])
    check("an existing value is never overwritten",
          filled == 0 and m["engines"][0]["engine_min_version"] == kept_value
          and m == before,
          f"filled={filled} value={m['engines'][0].get('engine_min_version')}")


def test_the_build_detector_has_one_implementation():
    """Rule 6d: the fill reads the ONE claim reader `data_gap_analysis` exports —
    `engine_min_claim`, which wraps the ONE compiled `_ENGINE_MIN_TEXT` detector
    (#1025); `update_trending` defines no own build-phrase regex or vocabulary."""
    detector = UT._engine_min_detector()
    check("the fill uses the ONE claim reader from data_gap_analysis",
          detector is G.engine_min_claim)
    check("the claim reader is built on the ONE detector object",
          G.engine_min_claim.__globals__["_ENGINE_MIN_TEXT"] is G._ENGINE_MIN_TEXT)
    src = (ROOT / "scripts" / "update_trending.py").read_text()
    own_copy = any(tok in src for tok in
                   ("untouched upstream", "stock llama.cpp", "nightly build",
                    "bleeding edge", "n-gpu-layers"))
    check("update_trending carries no second copy of the detector vocabulary",
          not own_copy, "a build-phrase literal was written into update_trending")


def test_a_model_version_collision_never_fills():
    """Issue #1025: three live candidates where the match names the MODEL's version,
    not an engine build. The claim reader refuses them, so no ingest job may structure
    them (rule 2 fabrication). The exact sentences are the ones `data_gap_analysis.py`
    lists under `unstructured:engine_min_version`."""
    fixtures = [
        ("glm-5.3-flash", "RED-SNOW-5.3-FLASH-MLX-4bit"),
        ("qwen3.8-27b-ps5lm-native", "2-bit Qwen 3.8 27B (PS5LM, llama.cpp port)"),
        ("bonsai-2-27b-mac-m4-max", "MLX weights (~7GB), 1.72 bits/weight"),
    ]
    for mid, phrase in fixtures:
        filled = UT.fill_engine_min_version([model(mid, engines=[{
            "engine": "llama.cpp", "tps": "10", "hardware": "RTX 4090 24GB",
            "quant": phrase, "date": "2026-11-14", "likes": 1,
            "source_post": "https://lightbrd.com/u/status/901"}])])
        check(f"#1025: {mid} — {phrase!r} fills NOTHING",
              filled == 0, f"filled={filled}")
    # A genuine build phrase in the SAME text still claims after the collision (#1006's
    # class): the reader skips the colliding match, it does not blind the field.
    filled = UT.fill_engine_min_version([model("glm-5.3-flash", engines=[{
        "engine": "llama.cpp", "tps": "10", "hardware": "RTX 4090 24GB",
        "quant": "RED-SNOW-5.3-FLASH-MLX-4bit; mlx 0.25.1 required",
        "date": "2026-11-14", "likes": 1,
        "source_post": "https://lightbrd.com/u/status/902"}])])
    check("#1025: a real build phrase after the collision still fills",
          filled == 1, f"filled={filled}")


def test_bits_per_weight_is_not_a_build():
    """Issue #1025's quant shape: `1.72 bits/weight` beside an engine word is a
    BIT-WIDTH, the sibling of #998's throughput lookahead — refused at the token."""
    check("1.72 bits/weight is not a build version",
          re.search(G._BUILD_VERSION, "7GB, 1.72 bits/weight on 4-bit") is None)
    check("306.9 tokens/s stays refused (#998 regression)",
          re.search(G._BUILD_VERSION, "306.9 tokens/s") is None)
    check("a real build version is untouched",
          re.search(G._BUILD_VERSION, "mlx 0.25.1") is not None)


def test_bare_engine_names_beside_throughput_figures_never_claim():
    """Issue #1020: the seven engine_min_version ingest candidates were engine NAMES
    beside throughput figures (`llama.cpp 306.9 tokens/s`, `llama.cpp 21.11 t/s`), a
    comparison sentence where the rate sits on the engine side (`345.9 vs llama.cpp's
    306.9 tokens/s`), a toolchain compound (`0.0.3 (C++/CUDA`) and quant/model-name
    descriptions (`ternary MLX weights`, `PS5LM, llama.cpp port`, `TensorFold vs vLLM`,
    `ExLlamaV3 + Hermes Agent`). None of them is a build claim; structuring one stores
    a speed or a name as an engine build (rule 2 fabrication). Every shape is planted
    on the row it was observed on and must fill NOTHING through the real fill seam."""
    fixtures = [
        ("qwen2.5-0.5b", "Q4_K_M GGUF, median of three runs; same post: llama.cpp "
                         "306.9 tokens/s on the identical GGUF"),
        ("gemma-4-e4b", "Q3_K_M GGUF, median of three runs; same post: llama.cpp "
                        "44.8 tokens/s on the identical GGUF (SonicBoom ~20% faster)"),
        ("qwen2.5-0.5b", "Tiny Qwen2.5 model used as the SonicBoom benchmark baseline: "
                         "345.9 vs llama.cpp's 306.9 tokens/s on an RTX 3050 8GB."),
        ("gemma-4-e4b", "SonicBoom 0.0.3 (C++/CUDA, MLIR compiler, zero Python) beats "
                        "llama.cpp on a consumer RTX 3050 8GB: 53.6 vs 44.8 tokens/s."),
        ("minicpm-v-4.7", "ExLlamaV3 + Hermes Agent"),
        ("qwen3.8-27b-ps5lm-native", "PS5LM, llama.cpp port"),
        ("bonsai-2-27b-mac-m4-max", "ternary MLX weights"),
        ("glm-5.3-flash", "TensorFold vs vLLM"),
        ("qwen2.5-0.5b", "llama.cpp 21.11 t/s at 32K context on the same card"),
        ("gemma-4-e4b", "llama.cpp 44.8 tokens per second on the identical GGUF"),
        ("gemma-4-e4b", "llama.cpp 44.8 t/s on the identical GGUF"),
    ]
    for mid, phrase in fixtures:
        filled = UT.fill_engine_min_version([model(mid, engines=[{
            "engine": "llama.cpp", "tps": "44", "hardware": "RTX 3050 8GB",
            "quant": phrase, "date": "2026-11-16", "likes": 1,
            "source_post": "https://lightbrd.com/u/status/1020"}])])
        check(f"#1020: {mid} — {phrase[:44]!r} fills NOTHING",
              filled == 0, f"filled={filled}")
    # The rate-on-the-engine-side refusal is a READER refusal, checked directly: the
    # possessive comparison and the bare `t/s` spelling never claim, while the engine
    # name followed by a build word still does.
    check("#1020: the possessive comparison sentence claims nothing",
          G.engine_min_claim(model("qwen2.5-0.5b"),
                             "345.9 vs llama.cpp's 306.9 tokens/s") is None)
    check("#1020: bare t/s beside an engine name claims nothing",
          G.engine_min_claim(model("qwen2.5-0.5b"), "llama.cpp 21.11 t/s") is None)
    check("#1020: an engine name followed by a build word still claims",
          G.engine_min_claim(model("qwen2.5-0.5b"), "llama.cpp build 2.1") is not None)


def test_explicit_build_phrases_still_claim():
    """The #1020 tightening refuses throughput adjacency, never an explicit build
    phrase: the one genuine build sentence of the seven-candidate set (the PrismML
    fork that rejected the stock llama.cpp format) and versioned provenance phrasings
    still claim through the ONE reader and fill through the real seam (rule 6d)."""
    claims = [
        "stock llama.cpp rejects the format so the PrismML fork ran it",
        "llama.cpp b5310 or newer is required for PTQ1_0 weights",
        "llama.cpp build 2.1, measured 306.9 tokens/s",
        "CUDA 12.4 is the minimum build",
    ]
    for phrase in claims:
        hit = G.engine_min_claim(model("qwen3.8-27b-bonsai-2"), phrase)
        check(f"#1020: {phrase[:44]!r} still claims", hit is not None, phrase)
    filled = UT.fill_engine_min_version([model("qwen3.8-27b-bonsai-2", engines=[{
        "engine": "llama.cpp (PrismML fork)", "tps": "34", "hardware": "M4 Max 128GB",
        "quant": claims[0], "date": "2026-11-16", "likes": 9,
        "source_post": "https://lightbrd.com/u/status/1021"}])])
    check("the genuine PrismML sentence fills through the real seam",
          filled == 1, f"filled={filled}")


def test_the_captured_class_closes_after_the_fill():
    """The report's own Done-when: a model the analysis named
    `captured:engine_min_version` (the post states it, the store does not — the
    INGEST class) leaves that list after the seam ingests the snapshot, and its
    measurement holds the structured value."""
    with tempfile.TemporaryDirectory() as td:
        raw = Path(td) / "raw"
        raw.mkdir()
        store = store_with([model("swift-model", backends=["Metal"],
                                  supported_engines=["MLX"],
                                  engines=[{"engine": "MLX", "tps": "31",
                                            "hardware": "M4 Max 128GB",
                                            "quant": "4-bit", "date": "2026-11-01",
                                            "likes": 1,
                                            "source_post": "https://lightbrd.com/u/status/333"}])])
        write_raw(raw, [model("swift-model", backends=["Metal"],
                              supported_engines=["MLX"], engines=[{
                                  "engine": "MLX", "tps": "12", "hardware": "M4 Max 128GB",
                                  "quant": "MLX 4-bit Swift 1.5 adapter (token-count cut)",
                                  "date": "2026-11-13", "likes": 20,
                                  "source_post": "https://lightbrd.com/u/status/444"}])])
        before = G.analyse(copy.deepcopy(store), G.contract_keys(), raw_dir=raw)
        check("the fixture starts in the captured (INGEST) class",
              "swift-model" in before["captured_prose"]["engine_min_version"],
              str(before["captured_prose"]["engine_min_version"]))
        ingest_fixture(store, raw)
        after = G.analyse(store, G.contract_keys(), raw_dir=raw)
        row = find_store_model(store, "swift-model")
        check("the captured class closes after the fill",
              "swift-model" not in after["captured_prose"]["engine_min_version"]
              and any(e.get("engine_min_version") == "MLX 4-bit Swift 1.5"
                      for e in row["engines"]),
              str(row["engines"]))


def test_model_why_prose_never_fills_a_value():
    """#470: a model's `why` is agent prose, not the post's record. A build claim
    living only in `why` fills NOTHING anywhere."""
    with tempfile.TemporaryDirectory() as td:
        raw = Path(td) / "raw"
        raw.mkdir()
        store = store_with([model("why-model")])
        write_raw(raw, [model("why-model", why="0.0.3 (C++/CUDA build)", engines=[{
            "engine": "llama.cpp", "tps": "18", "hardware": "M4 Pro 24GB",
            "quant": "4-bit", "date": "2026-11-13", "likes": 3,
            "source_post": "https://lightbrd.com/u/status/555"}])])
        ingest_fixture(store, raw)
        row = find_store_model(store, "why-model")
        check("`why` prose never fills a value",
              all("engine_min_version" not in e for e in row["engines"])
              and "engine_min_version" not in row,
              str(row.get("engines")))


def main() -> int:
    test_a_build_phrase_in_the_captured_text_fills_the_field()
    test_no_build_phrase_fills_nothing()
    test_an_existing_value_is_never_overwritten()
    test_the_build_detector_has_one_implementation()
    test_a_model_version_collision_never_fills()
    test_bits_per_weight_is_not_a_build()
    test_bare_engine_names_beside_throughput_figures_never_claim()
    test_explicit_build_phrases_still_claim()
    test_the_captured_class_closes_after_the_fill()
    test_model_why_prose_never_fills_a_value()
    print(f"\nPASSED {_PASS} | FAILED {_FAIL}")
    return 1 if _FAIL else 0


if __name__ == "__main__":
    raise SystemExit(main())
