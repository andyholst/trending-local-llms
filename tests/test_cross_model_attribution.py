#!/usr/bin/env python3
"""Same-post, cross-model attribution (issue #693).

A reader is told how fast a model runs; the number must belong to the model the
source post measured. Two rows in the shipped store broke that, and this change
removes them:

  * `gemma-3-1b` carried `MLX` 18 t/s on an M5 Pro Mac mini citing pratikg's
    six-model Mac mini test; the measured set named in `data/raw` is Qwen3-30B
    106 / Qwen3-8B 61 / Bonsai-2-27B 26 / Laguna XS 2.1 56 / Qwen3-14B 34 /
    Gemma 3 27B 18 — no 1B ever ran in that test.
  * `gemma-4-26b-a4b` carried `llama.cpp` 50.7 t/s on an RTX 3080 citing the
    PaulGugAI S1 speed test whose own text names LFM's engines (FreeToken/Strata)
    — the number belongs to `lfm2.5-24b-a2b`.

The same-post cross-model scan then reports every identical
`(engine, tps, hardware, source_post)` tuple stored on two model IDs. Remaining
tuples are legitimate (same-family variant IDs, or a post that measured both
models); those are pinned in the allow-list below so a NEW copy fails loudly.

Run:  python3 tests/test_cross_model_attribution.py   or   make test
"""
from __future__ import annotations

import io
import json
import sys
from contextlib import redirect_stdout
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import validate as V  # noqa: E402

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


def _store() -> dict:
    # The normalized store lives as catalog (data/models.json) + split measurement
    # + posts files; load_store() reconstructs the flat view every reader uses
    # (models[i]["engines"] = measurement rows with posts.json counters spliced).
    import update_trending as ut
    return ut.load_store()


def _by_id(store: dict) -> dict:
    return {m.get("id"): m for m in store.get("models", [])}


def _engines(store: dict, mid: str) -> list[dict]:
    m = _by_id(store).get(mid)
    return (m or {}).get("engines", [])


def _seen_posts(store: dict, mid: str) -> list[dict]:
    m = _by_id(store).get(mid)
    return (m or {}).get("engagement", {}).get("seen_posts", [])


# Every remaining same-post cross-model identical tuple, keyed by
# (engine, tps, hardware, source_post) -> [model ids], is one of:
#   * the SAME model under two store ids (qwen3.8-27b / -swift, bonsai = ternary
#     qwen3.8-27b, phone variants, qwen3-30b = its A3B id), or
#   * a post that measured BOTH models (the GuideboardLabs Agon bench reports the
#     same median for LFM2.5 and Qwen3.6-35B-A3B on vLLM; laky_fx's PS5 demo
#     reports each model's own range).
ALLOW_LIST = {
    ("llama.cpp", "80.76", "RTX 4090 24GB",
     "https://lightbrd.com/Oluwaphilemon1/status/2113070110038450648"):
        ["qwen3.8-27b", "qwen3.8-27b-dflash2-teksedge3090"],
    ("llama.cpp", "45", "RX 9070 XT 16GB",
     "https://lightbrd.com/Oluwaphilemon1/status/2107653402540790112"):
        ["qwen3.8-27b", "qwen3.8-27b-swift"],
    ("MLX", "34.5", "Mac Studio M4 Max, 128GB unified memory",
     "https://lightbrd.com/Oluwaphilemon1/status/2100946755487457783"):
        ["bonsai-2-27b-mac-m4-max", "qwen3.8-27b"],
    ("llama.cpp", "69", "2024 MacBook Pro M4 Pro, 48GB unified memory",
     "https://lightbrd.com/Oluwaphilemon1/status/2113439191832916273"):
        ["qwen3.6-35b-a3b", "qwen3.6-35b-a3b-kapitsa-m4-pro-mtp"],
    ("vLLM", "25.4", "Ryzen AI Max+ 395 (Radeon 8060S / Strix Halo)",
     "https://lightbrd.com/GuideboardLabs/status/2110246672166699354"):
        ["lfm2.5-24b-a2b", "qwen3.6-35b-a3b"],
    ("llama.cpp", "190", "RX 7900 XTX 24GB",
     "https://lightbrd.com/Whimsicali/status/2075976039113904260"):
        ["qwen3.6-35b-a3b", "qwopus3.6-35b-a3b-coder-mtp"],
    ("MLX", "9", "M1 Pro MacBook Pro 16GB",
     "https://lightbrd.com/allambition/status/2101077523027435878"):
        ["bonsai-2-27b", "qwen3.8-27b-bonsai-2"],
    ("MLX", "120", "iPhone 18 Pro Max",
     "https://lightbrd.com/eltc9584/status/2111091999638229038"):
        ["bonsai-2-2b", "bonsai-2-2b-phone"],
    ("MLX", "34", "iPhone 18 Pro Max",
     "https://lightbrd.com/eltc9584/status/2111091999638229038"):
        ["bonsai-2-9b", "bonsai-2-9b-phone"],
    ("MLX", "106", "Apple M5 Pro Mac mini, 64GB unified memory",
     "https://lightbrd.com/pratikg/status/2108994425166967019"):
        ["qwen3-30b", "qwen3-30b-a3b"],
    ("llama.cpp (strix-llama.cpp fork)", "21",
     "jailbroken PS5, 12 GiB unified GDDR6, Vulkan on Mihawk-99's RADV port",
     "https://lightbrd.com/laky_fx/status/2111512795803988237"):
        ["qwen3.5-0.8b", "qwen3.8-27b-ps5-llamacpp"],
}

# The copies this change removed: (model id, engine, tps, source_post).
_COPIES = [
    ("gemma-3-1b", "MLX", "18",
     "https://lightbrd.com/pratikg/status/2108994425166967019"),
    ("gemma-4-26b-a4b", "llama.cpp", "50.7",
     "https://lightbrd.com/PaulGugAI/status/2110275665408704970"),
    ("qwen3.6-35b-a3b", "llama.cpp", "51.8",
     "https://lightbrd.com/xfxjapan/status/2096715285923520644"),
]


def test_gemma_3_1b_no_longer_carries_the_27b_figure():
    store = _store()
    for e in _engines(store, "gemma-3-1b"):
        check("gemma-3-1b has no copied MLX 18 pratikg row",
              not (e.get("engine") == "MLX" and e.get("tps") == "18"
                   and "2108994425166967019" in str(e.get("source_post", ""))),
              e)
    check("gemma-3-1b keeps a real measurement",
          len(_engines(store, "gemma-3-1b")) >= 1, _engines(store, "gemma-3-1b"))
    check("gemma-3-1b seen_posts omit the pratikg post",
          all("2108994425166967019" not in str(p.get("url", ""))
              for p in _seen_posts(store, "gemma-3-1b")),
          _seen_posts(store, "gemma-3-1b"))


def test_gemma_4_26b_a4b_no_longer_carries_lfms_figure():
    store = _store()
    for e in _engines(store, "gemma-4-26b-a4b"):
        check("gemma-4-26b-a4b has no copied llama.cpp 50.7 PaulGugAI row",
              not (e.get("engine") == "llama.cpp" and e.get("tps") == "50.7"
                   and "2110275665408704970" in str(e.get("source_post", ""))),
              e)
    check("gemma-4-26b-a4b keeps a real RTX 3080 measurement",
          any(e.get("engine") == "llama.cpp" and e.get("tps") == "22.9"
              and str(e.get("hardware", "")).startswith("NVIDIA RTX 3080")
              for e in _engines(store, "gemma-4-26b-a4b")),
          _engines(store, "gemma-4-26b-a4b"))
    check("gemma-4-26b-a4b seen_posts omit the PaulGugAI speed test",
          all("2110275665408704970" not in str(p.get("url", ""))
              for p in _seen_posts(store, "gemma-4-26b-a4b")),
          _seen_posts(store, "gemma-4-26b-a4b"))


def test_qwen3_6_35b_a3b_no_longer_carries_qwen3_8_27bs_figure():
    store = _store()
    for e in _engines(store, "qwen3.6-35b-a3b"):
        check("qwen3.6-35b-a3b has no copied llama.cpp 51.8 xfxjapan row",
              not (e.get("engine") == "llama.cpp" and e.get("tps") == "51.8"
                   and "2096715285923520644" in str(e.get("source_post", ""))),
              e)
    check("qwen3.6-35b-a3b keeps real measurements",
          len(_engines(store, "qwen3.6-35b-a3b")) >= 1,
          _engines(store, "qwen3.6-35b-a3b"))
    check("qwen3.6-35b-a3b seen_posts omit the xfxjapan post",
          all("2096715285923520644" not in str(p.get("url", ""))
              for p in _seen_posts(store, "qwen3.6-35b-a3b")),
          _seen_posts(store, "qwen3.6-35b-a3b"))


def test_the_readme_renders_no_copied_row():
    sys.path.insert(0, str(ROOT / "scripts"))
    import update_trending as ut  # noqa: E402

    store = _store()
    as_of = ut.parse_utc_stamp(store.get("generated_utc"))
    readme = ut.render_readme(json.loads(json.dumps(store)), as_of)
    on_disk = (ROOT / "README.md").read_text()
    # Drift-clean: re-render is byte-identical to the committed README (the
    # "Last generated" line is a per-run wall clock and is ignored, matching
    # check_readme_generated).
    def _strip_ts(s):
        return "\n".join(ln for ln in s.splitlines() if not ln.startswith("> Last generated:"))
    check("the committed README equals the re-render (drift-clean)",
          _strip_ts(on_disk) == _strip_ts(readme),
          "committed README != render from the corrected store")
    # Gemma 3 1B's own engine rows must not carry the copied figure.
    check("Gemma 3 1B renders no MLX 18 on the M5 Pro Mac mini",
          _copied_row_rendered(readme, "Gemma 3 1B", "MLX", "18", hardware="M5 Pro") is False,
          "Gemma 3 1B renders the 27B's 18")
    check("Gemma 4 26B A4B renders no llama.cpp 50.7 RTX 3080 row",
          _copied_row_rendered(readme, "Gemma 4 26B A4B", "llama.cpp", "50.7",
                               hardware="RTX 3080") is False,
          "Gemma 4 26B A4B renders LFM's 50.7")
    # The owners keep their figures.
    check("README keeps Gemma 3 27B's MLX 18 on the M5 Pro Mac mini",
          _copied_row_rendered(readme, "Gemma 3 27B", "MLX", "18", hardware="M5 Pro") is not False,
          "Gemma 3 27B MLX 18 not rendered")
    check("README keeps LFM2.5-24B-A2B's llama.cpp 50.7 on the RTX 3080",
          _copied_row_rendered(readme, "LFM2.5-24B-A2B", "llama.cpp", "50.7",
                               hardware="RTX 3080") is not False,
          "LFM2.5 llama.cpp 50.7 not rendered")
    check("README keeps qwen3.8-27b's llama.cpp 51.8 on the Radeon R9700",
          _copied_row_rendered(readme, "Qwen3.8-27B", "llama.cpp", "51.8",
                               hardware="Radeon AI PRO R9700") is not False,
          "qwen3.8-27b llama.cpp 51.8 not rendered")


def _copied_row_rendered(readme: str, model_name: str, engine: str, tps: str,
                         hardware: str = "") -> bool:
    """True when a README engine-row renders this model+engine+tps (+hardware).

    The engine rows appear per model; a row is the model's own only when the
    figure and, when given, the hardware sit on the same line as the model.
    Returns False when the row is absent, so callers check `is False` / `is not
    False` to tell "absent" from "present".
    """
    import re
    for line in readme.splitlines():
        if model_name in line and re.search(r"\*\*%s\*\*" % re.escape(tps), line):
            if engine in line and (not hardware or hardware in line):
                return True
    return False


def test_the_same_post_cross_model_scan_is_clean():
    store = _store()
    dups = V.same_post_cross_model_duplicates(store.get("models", []))
    by_post = {post: ids for post, ids in dups}
    # Every reported tuple must be in the documented allow-list, with the SAME
    # model ids the scan found.
    unexpected = []
    for post, ids in dups:
        for key, allowed in ALLOW_LIST.items():
            if key[3] == post and set(ids) == set(allowed):
                break
        else:
            unexpected.append((post, ids))
    check("every same-post cross-model tuple is allow-listed",
          not unexpected, unexpected)
    check("the allow-list tuples are all still present",
          all(any(p == k[3] for p, _ in dups) for k in ALLOW_LIST),
          dups)
    # The three copies are gone: the copied model id no longer shares ANY
    # anonymous (engine, tps, hardware, source_post) tuple with another model.
    # The copied POST may still appear in the scan under a DIFFERENT, legitimate
    # tuple (e.g. pratikg's MLX 106 still pairs qwen3-30b / qwen3-30b-a3b), so we
    # assert on the model id, not on the post URL — a post URL wide assertion
    # fails the moment a same-post legitimate the pair exists for it.
    for mid, engine, tps, post in _COPIES:
        in_any = any(post == p and mid in ids for p, ids in dups)
        check(f"copied model id ({mid} {engine} {tps}) no longer shares a tuple", not in_any, dups)


def test_a_regression_is_reported_never_silent():
    # Re-inject a copy into a synthetic store: the scan must NAME it and the
    # validator must NOT fail (report-only, same pattern as #459).
    store = _store()
    store = json.loads(json.dumps(store))
    for m in store["models"]:
        if m.get("id") == "gemma-3-1b":
            m.setdefault("engines", []).append({
                "engine": "MLX", "tps": "18",
                "hardware": "Apple M5 Pro Mac mini, 64GB unified memory",
                "quant": "MLX build", "date": "2026-10-10",
                "source_post": "https://lightbrd.com/pratikg/status/2108994425166967019",
                "likes": 9, "comments": 6, "reshares": 226, "views": 38759,
            })
    dups = V.same_post_cross_model_duplicates(store["models"])
    check("a re-injected copy is reported",
          any("2108994425166967019" in p for p, _ in dups), dups)
    buf = io.StringIO()
    with redirect_stdout(buf):
        V.check_cross_model_attribution(store)
    out = buf.getvalue()
    check("the validator prints the copy as a WARN and never fails",
          "WARN: same-post cross-model scan" in out, out)


def test_the_check_is_wired_into_the_data_stage():
    src = (ROOT / "scripts" / "validate.py").read_text()
    check("check_cross_model_attribution is registered under the data stage",
          "same-post cross-model scan (report only)" in src
          and "add(\"same-post cross-model scan (report only)\", \"data\"" in src,
          "registration missing")
    check("the data stage is selected by a validate target",
          "--only data,removal" in (ROOT / "Makefile").read_text(),
          "no --only data,removal target")


def main() -> int:
    test_gemma_3_1b_no_longer_carries_the_27b_figure()
    test_gemma_4_26b_a4b_no_longer_carries_lfms_figure()
    test_qwen3_6_35b_a3b_no_longer_carries_qwen3_8_27bs_figure()
    test_the_readme_renders_no_copied_row()
    test_the_same_post_cross_model_scan_is_clean()
    test_a_regression_is_reported_never_silent()
    test_the_check_is_wired_into_the_data_stage()
    print(f"cross-model-attribution: {_PASS} passed, {_FAIL} failed")
    return 1 if _FAIL else 0


if __name__ == "__main__":
    raise SystemExit(main())
