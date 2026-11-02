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
import update_trending as ut  # noqa: E402  (single source of CROSS_MODEL_ALLOW_LIST)

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
# The allow-list lives in ONE place — `update_trending.CROSS_MODEL_ALLOW_LIST` —
# and the ingest-time refusal (issue #702) and this post-merge gate read the SAME
# constant, so the two gates never disagree.
ALLOW_LIST = ut.CROSS_MODEL_ALLOW_LIST

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


def test_cross_model_carriers_are_the_store_already_merged():
    # The carriers map (issue #702) is built from the ALREADY-merged store ONLY,
    # so only a copy ARRIVING at ingest is ever refused, never the established owner.
    store = _store()
    carriers = ut.cross_model_carriers(store)
    check("carriers is non-empty for the real store",
          len(carriers) >= 11, len(carriers))
    # The two qwen3.8-27b / -swift variants that legitimately share a 45 t/s post.
    check("carriers keys use the (engine, tps, hardware, source_post) identity",
          ("llama.cpp", "45", "RX 9070 XT 16GB",
           "https://lightbrd.com/Oluwaphilemon1/status/2107653402540790112")
          in carriers, sorted(carriers)[:3])

    # An established owner's own tuple must not be refused:
    model = {"id": "qwen3.8-27b", "engines": [{
        "engine": "llama.cpp", "tps": "45", "hardware": "RX 9070 XT 16GB",
        "quant": "IQ4_XS", "date": "2026-10-11",
        "source_post": "https://lightbrd.com/Oluwaphilemon1/status/2107653402540790112",
    }]}
    kept, refused = ut.refuse_cross_model_duplicate_measurements(model, carriers)
    check("an established owner's tuple is kept, not refused",
          len(kept) == 1 and not refused, (kept, refused))


def test_a_copy_onto_a_model_the_post_never_measured_is_refused():
    # Re-inject the #693 gemma-3-1b copy (MLX 18 from pratikg's post, whose tuple
    # is ALREADY carried by Gemma 3 27B) as a NEW raw row: it must be REFUSED at
    # ingest with the owning model id — the write-time refusal #702 adds.
    store = _store()
    store = json.loads(json.dumps(store))
    # Find the true owner id of the (MLX, 18, ..., pratikg) tuple.
    carriers = ut.cross_model_carriers(store)
    owner_ident = ("MLX", "18", "Apple M5 Pro Mac mini, 64GB unified memory",
                   "https://lightbrd.com/pratikg/status/2108994425166967019")
    owners = carriers.get(owner_ident, set())
    check("the gemma-3-1b copied tuple's owner is in the store",
          bool(owners), owners)
    copies = {"gemma-3-1b", "gemma-4-26b-a4b", "qwen3.6-35b-a3b"}
    check("the #693 copied model ids are NOT among the owners",
          not owners.intersection(copies), owners)

    model = {"id": "gemma-3-1b", "engines": [{
        "engine": "MLX", "tps": "18", "hardware": "Apple M5 Pro Mac mini, 64GB unified memory",
        "quant": "MLX build", "date": "2026-10-10",
        "source_post": "https://lightbrd.com/pratikg/status/2108994425166967019",
    }]}
    kept, refused = ut.refuse_cross_model_duplicate_measurements(model, carriers)
    check("the copied measurement is refused at ingest",
          len(refused) == 1 and not kept, (kept, refused))
    check("the refusal lands by ownership, never by name",
          "already carried by" in refused[0][1] and owner_ident[3].split("/status/")[-1]
          in refused[0][2], refused)


def test_a_documented_allow_listed_pair_is_kept_at_ingest():
    # A NEW raw row for qwen3.8-27b-swift carrying the SAME tuple as qwen3.8-27b
    # (a documented same-family variant pair) must be KEPT — the allow-list says
    # this post measured both variants.
    store = _store()
    carriers = ut.cross_model_carriers(store)
    ident = ("llama.cpp", "45", "RX 9070 XT 16GB",
             "https://lightbrd.com/Oluwaphilemon1/status/2107653402540790112")
    check("the variant pair is allow-listed",
          ident in ut.CROSS_MODEL_ALLOW_LIST
          and "qwen3.8-27b-swift" in ut.CROSS_MODEL_ALLOW_LIST[ident],
          ut.CROSS_MODEL_ALLOW_LIST.get(ident))
    model = {"id": "qwen3.8-27b-swift", "engines": [{
        "engine": "llama.cpp", "tps": "45", "hardware": "RX 9070 XT 16GB",
        "quant": "IQ4_XS", "date": "2026-10-11",
        "source_post": "https://lightbrd.com/Oluwaphilemon1/status/2107653402540790112",
    }]}
    kept, refused = ut.refuse_cross_model_duplicate_measurements(model, carriers)
    check("an allow-listed variant measurement is kept, not refused",
          len(kept) == 1 and not refused, (kept, refused))


def test_cross_model_refusal_is_wired_into_ingest():
    # The seam runs in ingest_raw_snapshots() at the exact spot a raw row would
    # enter the store, alongside the two existing refusal seams.
    src = (ROOT / "scripts" / "update_trending.py").read_text()
    check("the cross-model seam is registered in ingest_raw_snapshots",
          "refuse_cross_model_duplicate_measurements(m, _carriers)" in src,
          "refusal not wired into ingest")
    check("carriers are built from the store once, before the per-row loop",
          "_carriers = cross_model_carriers(store)" in src,
          "carriers not built once")
    check("all three refusal seams sit in the same ingest function",
          "refuse_fabricated_engines" in src
          and "refuse_misattributed_measurements" in src
          and "REFUSED cross-model duplicate measurement" in src,
          "seams missing")


def test_ingest_refuses_a_re_capture_before_it_merges():
    # E2E through the REAL ingest pipeline (`ingest_raw_snapshots`, input-to-result,
    # no mock): a temp data dir carries a copy of the committed store, and a crafted
    # raw snapshot RE-CAPTURES the #693 gemma-3-1b copy (MLX 18 from pratikg's post,
    # whose tuple is already carried by gemma-3-27b). The copy must be refused at
    # ingest and never land on the model — while a legitimate fresh measurement on
    # that same raw row still merges (the rest of the snapshot survives).
    import subprocess
    import textwrap
    script = textwrap.dedent("""
        import json, os, shutil, sys, tempfile
        from pathlib import Path
        ROOT = Path(sys.argv[1])
        tmp = Path(sys.argv[2])
        for name in ("models.json", "measurements.json", "posts.json"):
            shutil.copy(ROOT / "data" / name, tmp / name)
        (tmp / "raw").mkdir(parents=True, exist_ok=True)
        post_hw = "Apple M5 Pro Mac mini, 64GB unified memory"
        post = "https://lightbrd.com/pratikg/status/2108994425166967019"
        (tmp / "raw" / "re-capture.json").write_text(json.dumps({
            "generated_utc": "2026-11-02T23:00:00Z",  # strictly newer than the store
            "models": [{
                "id": "gemma-3-1b", "name": "Gemma 3 1B Instruct",
                "hf": "google/gemma-3-1b-it", "formats": [{"format": "MLX"}],
                "engines": [
                    {  # the COPY: tuple already carried by gemma-3-27b
                        "engine": "MLX", "tps": "18", "hardware": post_hw,
                        "quant": "MLX build", "date": "2026-10-10",
                        "source_post": post, "likes": 9, "comments": 6,
                        "reshares": 226, "views": 38759,
                    },
                    {  # a LEGIT fresh measurement of gemma-3-1b (not a copy)
                        "engine": "MLX", "tps": "31", "hardware": "iPhone 18 Pro Max",
                        "quant": "MLX build", "date": "2026-11-01",
                        "source_post": "https://lightbrd.com/eltc9584/status/2111091999638229038",
                    },
                ],
            }],
        }))
        os.environ["TRENDING_DATA_DIR"] = str(tmp)
        sys.path.insert(0, str(ROOT / "scripts"))
        import update_trending as ut
        store = ut.load_store()
        added, updated = ut.ingest_raw_snapshots(store, since=None)
        out_models = {m["id"]: m for m in store["models"]}
        g1b = out_models["gemma-3-1b"]
        copied_present = any(
            e.get("engine") == "MLX" and e.get("tps") == "18" and post_hw in str(e.get("hardware", ""))
            for e in g1b.get("engines", [])
        )
        legit_merged = any(
            e.get("engine") == "MLX" and e.get("tps") == "31"
            for e in g1b.get("engines", [])
        )
        print(f"ADDED={added} UPDATED={updated}")
        print(f"COPIED_PRESENT={copied_present}")
        print(f"LEGIT_MERGED={legit_merged}")
    """)
    tmp = ROOT / "tmp-ig702-e2e"
    shutil_rmtree = __import__("shutil").rmtree
    shutil_rmtree(tmp, ignore_errors=True)
    tmp.mkdir(parents=True, exist_ok=True)
    import io as _io
    buf = _io.StringIO()
    with redirect_stdout(buf):
        r = subprocess.run([sys.executable, "-c", script, str(ROOT), str(tmp)],
                           capture_output=True, text=True, timeout=180)
    out = buf.getvalue() + r.stdout
    check("the E2E ingest subprocess runs clean",
          r.returncode == 0, (r.returncode, r.stderr[-400:]))
    check("the copied row is REFUSED at ingest (never merges)",
          "COPIED_PRESENT=False" in out, r.stdout)
    check("a legitimate measurement on the same raw row still merges",
          "LEGIT_MERGED=True" in out, r.stdout)
    check("the refusal is loud in the ingest log",
          "REFUSED cross-model duplicate measurement" in out, r.stderr)
    shutil_rmtree(tmp, ignore_errors=True)


def main() -> int:
    test_gemma_3_1b_no_longer_carries_the_27b_figure()
    test_gemma_4_26b_a4b_no_longer_carries_lfms_figure()
    test_qwen3_6_35b_a3b_no_longer_carries_qwen3_8_27bs_figure()
    test_the_readme_renders_no_copied_row()
    test_the_same_post_cross_model_scan_is_clean()
    test_a_regression_is_reported_never_silent()
    test_the_check_is_wired_into_the_data_stage()
    test_cross_model_carriers_are_the_store_already_merged()
    test_a_copy_onto_a_model_the_post_never_measured_is_refused()
    test_a_documented_allow_listed_pair_is_kept_at_ingest()
    test_cross_model_refusal_is_wired_into_ingest()
    test_ingest_refuses_a_re_capture_before_it_merges()
    print(f"cross-model-attribution: {_PASS} passed, {_FAIL} failed")
    return 1 if _FAIL else 0


if __name__ == "__main__":
    raise SystemExit(main())
