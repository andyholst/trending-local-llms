#!/usr/bin/env python3
"""Direct unit tests for the README + raw-mapping validators in scripts/validate.py.

Completes validator coverage with pass / edge / failure cases for:
  - check_backend_sort        (README tables sorted by t/s desc)
  - check_readme_has_all_models
  - check_readme_sync         (JSON<->README both change together)
  - check_readme_generated    (README produced by the generator, not hand-edited)
  - check_raw_mapping         (raw search -> models.json position / collision)

The functions read V.README / V.RAW_DIR / V.ROOT module globals, so each test
monkeypatches those to temp files and restores after.

Run:  python3 tests/test_validate_readme.py   or   make test
"""
from __future__ import annotations

import json
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import validate as V  # noqa: E402
import update_trending as UT  # noqa: E402

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


def store() -> dict:
    return {"generated_utc": "2026-09-28T12:00:00Z", "engines": {
        "llama.cpp": {"backend": "CUDA", "note": "x", "url": "https://u"}},
        "models": [{
            "id": "m1", "name": "Model One", "full_name": "Model-One", "type": "LLM",
            "formats": [{"name": "GGUF", "hf": "a/m1"}], "license": "Apache 2.0",
            "params": "13B", "hf": "a/m1", "vram_tier": "12GB", "vram_min": "8GB",
            "backends": ["CUDA"], "supported_engines": ["llama.cpp"],
            "engines": [{"engine": "llama.cpp", "tps": "80", "hardware": "RTX 4070",
                         "date": "2026-09-27", "source_post": "https://lightbrd.com/x"}],
            "why": "w", "engagement": {"likes": 1, "comments": 1, "views": 1, "last_7d_likes": 1},
            "last_seen": "2026-09-27",
        }]}


def _set_readme(text: str) -> Path:
    td = tempfile.mkdtemp()
    p = Path(td) / "README.md"
    p.write_text(text)
    saved = V.README
    V.README = p
    V.__saved_readme = saved
    return p


def _restore_readme():
    if hasattr(V, "__saved_readme"):
        V.README = V.__saved_readme
        delattr(V, "__saved_readme")


def cuda_table(numbers):
    """Build a README with CUDA + Metal + CPU backend tables (the three that
    check_backend_sort requires). Only CUDA carries rows; Metal+CPU are empty
    (empty tables pass the sorted check, so they don't mask the real assertion)."""
    rows = ["# Trending Local LLMs"]
    rows.append("")
    rows.append("# 🟦 CUDA — NVIDIA GPUs")
    rows.append("")
    rows.append("| Model | t/s |")
    rows.append("|---|---|")
    for n in numbers:
        rows.append(f"| **X** | {n} |")
    rows.append("")
    rows.append("# 🟩 Metal — Apple Silicon")
    rows.append("")
    rows.append("| Model | t/s |")
    rows.append("|---|---|")
    rows.append("_No models measured on this backend yet._")
    rows.append("")
    rows.append("# 🟨 CPU — no GPU")
    rows.append("")
    rows.append("| Model | t/s |")
    rows.append("|---|---|")
    rows.append("_No models measured on this backend yet._")
    return "\n".join(rows)


def test_backend_sort_pass():
    reset()
    s = store()
    r = _set_readme(cuda_table([100, 80, 50]))  # descending -> pass
    try:
        V.check_backend_sort(s)
        check("backend-sort: descending passes", len(V.FAILURES) == 0)
    finally:
        _restore_readme()


def test_backend_sort_fail():
    reset()
    s = store()
    r = _set_readme(cuda_table([50, 100, 80]))  # not descending -> fail
    try:
        V.check_backend_sort(s)
        check("backend-sort: catches out-of-order table", len(V.FAILURES) == 1 and "not sorted" in V.FAILURES[0])
    finally:
        _restore_readme()


def test_backend_sort_missing_table():
    reset()
    s = store()
    r = _set_readme("# Just a title\nno tables here\n")
    try:
        V.check_backend_sort(s)
        check("backend-sort: flags missing CUDA table", any("missing CUDA" in f for f in V.FAILURES))
    finally:
        _restore_readme()


def test_readme_has_all_models():
    reset()
    s = store()
    r = _set_readme("# Title\n\n**Model One** here\n")
    try:
        V.check_readme_has_all_models(s)
        check("readme-complete: model present passes", len(V.FAILURES) == 0)
    finally:
        _restore_readme()
    reset()
    s = store()
    r = _set_readme("# Title no model\n")
    try:
        V.check_readme_has_all_models(s)
        check("readme-complete: catches missing model", len(V.FAILURES) == 1)
    finally:
        _restore_readme()


def test_readme_sync_pass():
    reset()
    s = store()
    r = _set_readme("Model One 80 https://lightbrd.com/x\nLast generated: 2026-09-28\n")
    try:
        V.check_readme_sync(s)
        check("sync: JSON+README in step passes", len(V.FAILURES) == 0)
    finally:
        _restore_readme()


def test_readme_sync_missing_model():
    reset()
    s = store()
    r = _set_readme("# no model here\n")
    try:
        V.check_readme_sync(s)
        check("sync: catches model missing from README", any("missing from README" in f for f in V.FAILURES))
    finally:
        _restore_readme()


def test_readme_sync_timestamp_mismatch():
    reset()
    s = store()  # generated_utc 2026-09-28
    r = _set_readme("Model One 80\nLast generated: 2020-01-01\n")  # stale timestamp
    try:
        V.check_readme_sync(s)
        check("sync: catches stale 'Last generated'", any("Last generated" in f or "generated_utc" in f for f in V.FAILURES))
    finally:
        _restore_readme()


def test_readme_generated_pass():
    reset()
    s = store()
    # README exactly equals the generator output -> pass
    expected = UT.render_readme(s, datetime.now(timezone.utc))
    r = _set_readme(expected)
    try:
        V.check_readme_generated(s)
        check("readme-generated: matches generator passes", len(V.FAILURES) == 0)
    finally:
        _restore_readme()


def test_readme_generated_handedited():
    reset()
    s = store()
    expected = UT.render_readme(s, datetime.now(timezone.utc))
    tampered = expected.replace("**Model One**", "**Model One** [HAND EDITED]")
    r = _set_readme(tampered)
    try:
        V.check_readme_generated(s)
        check("readme-generated: catches hand-edited README", any("NOT regenerated" in f or "hand-edited" in f for f in V.FAILURES))
    finally:
        _restore_readme()


def _run_raw_mapping(raw_files, store):
    td = tempfile.mkdtemp()
    rdir = Path(td) / "raw"
    rdir.mkdir()
    for name, content in raw_files.items():
        (rdir / name).write_text(json.dumps(content))
    saved = V.RAW_DIR
    V.RAW_DIR = rdir
    try:
        reset()
        V.check_raw_mapping(store)
        return list(V.FAILURES)
    finally:
        V.RAW_DIR = saved


def test_raw_mapping_maps_existing():
    s = store()
    raw = {"models": [{"id": "m1", "name": "Model One", "hf": "a/m1"}]}  # maps to m1 by id/name
    fails = _run_raw_mapping({"nvidia-1.json": raw}, s)
    check("raw-mapping: known model maps cleanly", len(fails) == 0)


def test_raw_mapping_new_model():
    s = store()
    raw = {"models": [{"id": "kimi-k3", "name": "Kimi K3", "hf": "moonshotai/kimi-k3"}]}  # brand new
    fails = _run_raw_mapping({"general-1.json": raw}, s)
    check("raw-mapping: brand-new model accepted (no collision)", len(fails) == 0)


def test_raw_mapping_id_collision__maps_by_id():
    """A raw model whose id matches an existing model maps BY ID to that
    position (resolve_model_mapping prioritizes id across all models), so it is
    correctly placed — NOT flagged as a collision. This asserts the id-first
    mapping behavior and that the collision guard is not spuriously tripped."""
    s = store()
    # same id 'm1' but different name/hf: exact-id priority wins -> maps to m1
    raw = {"models": [{"id": "m1", "name": "Completely Different", "hf": "other/x"}]}
    fails = _run_raw_mapping({"nvidia-2.json": raw}, s)
    check("raw-mapping: id match maps by id (no spurious collision)", len(fails) == 0)


def test_most_loved_table_clean_shape():
    """REGRESSION: the 'most loved' table must NOT carry a '#' rank column or a
    redundant 'Engines + t/s' column. Rank is implied by row order (first row =
    highest engagement); the CUDA/Metal columns already carry t/s + engine link +
    hardware. A future renderer change that reintroduces either column fails
    here."""
    s = store()
    readme = UT.render_readme(s, datetime(2026, 9, 28, tzinfo=timezone.utc))
    # the most-loved table header (first table after the 'Most loved' heading)
    lines = readme.split("\n")
    start = next(i for i, ln in enumerate(lines) if "Most loved" in ln)
    hdr = next(ln for ln in lines[start:] if ln.startswith("| Model"))
    check("most-loved: no '#' rank column", not hdr.startswith("| #"), hdr)
    check("most-loved: no 'Engines + t/s' column", "Engines + t/s" not in hdr, hdr)
    check("most-loved: has CUDA + Metal t/s columns", "CUDA t/s" in hdr and "Metal t/s" in hdr, hdr)
    # every data row in the most-loved table must have the same column count as
    # the header. Stop at the first non-table line (end of the table block) so
    # we don't bleed into the engine-guide table below.
    hdr_cols = hdr.count("|")
    for ln in lines[start + 1:]:
        if not ln.strip():
            continue
        if not ln.startswith("|"):
            break  # end of the most-loved table block
        if "Model" in ln or "---" in ln:
            continue
        check("most-loved: row column count matches header", ln.count("|") == hdr_cols, ln[:60])


def main() -> int:
    print("validate-readme + raw-mapping: direct unit tests")
    test_backend_sort_pass()
    test_backend_sort_fail()
    test_backend_sort_missing_table()
    test_readme_has_all_models()
    test_readme_sync_pass()
    test_readme_sync_missing_model()
    test_readme_sync_timestamp_mismatch()
    test_readme_generated_pass()
    test_readme_generated_handedited()
    test_raw_mapping_maps_existing()
    test_raw_mapping_new_model()
    test_raw_mapping_id_collision__maps_by_id()
    test_most_loved_table_clean_shape()
    print(f"\nPASSED {_PASS} | FAILED {_FAIL}")
    return 1 if _FAIL else 0


if __name__ == "__main__":
    raise SystemExit(main())
