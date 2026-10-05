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


def empty_backend_tables(header: str = "| Model | t/s |", sep: str = "|---|---|") -> list[str]:
    """Empty Metal + CPU + ROCm tables: every backend check_backend_sort requires
    besides CUDA (update_trending.BACKENDS). The ONE place a new backend table is
    added to these README fixtures."""
    rows = []
    for title in ("# 🟩 Metal — Apple Silicon", "# 🟨 CPU — no GPU", "# 🟪 ROCm — AMD GPUs"):
        rows += ["", title, "", header, sep, "_No models measured on this backend yet._"]
    return rows


def cuda_table(numbers):
    """Build a README with CUDA + Metal + CPU + ROCm backend tables (the four
    that check_backend_sort requires). Only CUDA carries rows; the others are
    empty (empty tables pass the sorted check, so they don't mask the real
    assertion)."""
    rows = ["# Trending Local LLMs"]
    rows.append("")
    rows.append("# 🟦 CUDA — NVIDIA GPUs")
    rows.append("")
    rows.append("| Model | t/s |")
    rows.append("|---|---|")
    for n in numbers:
        rows.append(f"| **X** | {n} |")
    rows += empty_backend_tables()
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
    # README exactly equals the generator output -> pass. Render as of the
    # store's generated_utc, exactly like check_readme_generated does: status
    # bands + the 7-day score are date-relative, so a wall-clock render drifts
    # out of sync with the validator once the fixture date ages past a band.
    expected = UT.render_readme(s, _store_as_of(s))
    r = _set_readme(expected)
    try:
        V.check_readme_generated(s)
        check("readme-generated: matches generator passes", len(V.FAILURES) == 0)
    finally:
        _restore_readme()


def test_readme_generated_handedited():
    reset()
    s = store()
    expected = UT.render_readme(s, _store_as_of(s))
    tampered = expected.replace("**Model One**", "**Model One** [HAND EDITED]")
    r = _set_readme(tampered)
    try:
        V.check_readme_generated(s)
        check("readme-generated: catches hand-edited README", any("NOT regenerated" in f or "hand-edited" in f for f in V.FAILURES))
    finally:
        _restore_readme()


def _store_as_of(s: dict) -> datetime:
    return datetime.strptime(s["generated_utc"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)


def test_readme_generated_tests_are_clock_independent():
    """Regression: test_readme_generated_pass rendered the expected README with
    datetime.now() while the validator renders as of store.generated_utc, so the
    test went red on master once the fixture (2026-09-28) aged past the 7-day
    trending band (run 37247105182). No test may render a README from the wall
    clock; it must use a fixed as-of date."""
    import ast
    offenders = []
    for f in sorted((ROOT / "tests").glob("test_*.py")):
        tree = ast.parse(f.read_text())
        for node in ast.walk(tree):
            if not (isinstance(node, ast.Call) and getattr(node.func, "attr", getattr(node.func, "id", "")) == "render_readme"):
                continue
            for arg in node.args[1:] + [k.value for k in node.keywords]:
                for sub in ast.walk(arg):
                    if isinstance(sub, ast.Attribute) and sub.attr in ("now", "utcnow", "today"):
                        offenders.append(f"{f.name}:{node.lineno}")
    check("readme-generated: no test renders README from the wall clock", not offenders, ", ".join(offenders))


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


def test_engine_guide_engine_name_is_link():
    """REGRESSION: the inference engine guide must link the ENGINE NAME to its
    repo/main site — not a separate 'Repo' column. A future renderer change that
    reintroduces a bare engine name or a 'Repo' column fails here."""
    s = store()
    readme = UT.render_readme(s, datetime(2026, 9, 28, tzinfo=timezone.utc))
    lines = readme.split("\n")
    start = next(i for i, ln in enumerate(lines) if "Inference engine" in ln)
    hdr = next(ln for ln in lines[start:] if ln.startswith("| Engine"))
    check("engine-guide: no separate 'Repo' column", "Repo" not in hdr, hdr)
    # every engine row must have the engine name as a markdown link
    for ln in lines[start:]:
        if not ln.strip():
            continue
        if not ln.startswith("|"):
            break
        if "Engine" in ln or "---" in ln:
            continue
        cells = [c.strip() for c in ln.strip().strip("|").split("|")]
        check("engine-guide: engine name is a link", cells[0].startswith("["), cells[0])


def test_readme_tables_wellformed():
    """HAPPY: a well-formed README (as generated) PASSES the markdown-it table
    validator. NEGATIVE: a broken separator column count FAILS it."""
    import tempfile
    s = store()
    readme = UT.render_readme(s, datetime(2026, 9, 28, tzinfo=timezone.utc))
    tmp = tempfile.mkdtemp()

    # happy: render -> every table well-formed
    happy = Path(tmp) / "README.md"
    happy.write_text(readme)
    saved = V.README
    V.README = happy
    try:
        reset()
        V.check_readme_tables_wellformed(s)
        errs = [m for m in V.FAILURES if "readme-tables" in m]
        check("readme-tables: generated README is well-formed",
              len(errs) == 0, json.dumps(errs))
    finally:
        V.README = saved

    # negative: drop one dash-group from the most-loved separator
    broken = readme.replace(
        "|---|---|---|---|---|---|---|",
        "|---|---|---|---|---|---|",
        1)
    bp = Path(tmp) / "README-broken.md"
    bp.write_text(broken)
    saved2 = V.README
    V.README = bp
    try:
        reset()
        V.check_readme_tables_wellformed(s)
        errs = [m for m in V.FAILURES if "readme-tables" in m]
        check("readme-tables: broken separator column count is CATCHED",
              any("separator has" in e for e in errs), json.dumps(errs))
    finally:
        V.README = saved2


def _cuda_table_with_dates(cells):
    """Build a CUDA table whose t/s cells carry the real format:
    'engine tps (YYYY-MM-DD); engine tps (date)'. Metal+CPU+ROCm are empty."""
    rows = ["# Trending Local LLMs", "", "# 🟦 CUDA — NVIDIA GPUs", "",
            "| Model | t/s |", "|---|---|"]
    for c in cells:
        rows.append(f"| **X** | {c} |")
    rows += empty_backend_tables()
    return "\n".join(rows)


def test_backend_sort_counts_1000plus_and_strips_dates():
    """REGRESSION: a t/s >= 1000 (e.g. spec-decode 1250) must be counted (was
    dropped by a '<1000' filter), and the embedded '(YYYY-MM-DD)' date must not
    let the YEAR (2026) be read as t/s. 1250-first, 380-second must PASS as
    sorted. This guards the CUDA-table 'unsorted' false positive that blocked
    refresh PRs."""
    reset()
    s = store()
    r = _set_readme(_cuda_table_with_dates([
        "DFlash2 1250 (2026-09-28)",
        "llama.cpp 380 (2026-09-27)",
    ]))
    try:
        V.check_backend_sort(s)
        check("backend-sort: 1250 counted + dates stripped -> sorted passes",
              len(V.FAILURES) == 0, json.dumps(V.FAILURES))
    finally:
        _restore_readme()


def test_backend_sort_dates_not_counted_as_tps():
    """REGRESSION: the YEAR in an embedded date must not be read as t/s. Table
    is in TRUE descending tps order (60, then 50) but with the years INVERTED
    (2025 on the high-tps row, 2026 on the low-tps row). If the year leaked, the
    parse would read [2025, 2026] (unsorted) and the correctly-sorted table
    would FALSE-fail. With date-stripping it reads [60, 50] and passes."""
    reset()
    s = store()
    r = _set_readme(_cuda_table_with_dates([
        "llama.cpp 60 (2025-12-01)",
        "llama.cpp 50 (2026-09-28)",
    ]))
    try:
        V.check_backend_sort(s)
        check("backend-sort: date year inverted does NOT leak as t/s -> passes",
              len(V.FAILURES) == 0, json.dumps(V.FAILURES))
    finally:
        _restore_readme()


def test_backend_sort_ignores_digits_in_link_urls():
    """REGRESSION (PR #53): the Strata repo URL github.com/Niko1221/Strata put
    '1221' into the legacy t/s cell, so a correctly-sorted CUDA table (99.7 then
    93) was flagged unsorted and fix-bot was dispatched to 'repair' valid data."""
    reset()
    s = store()
    r = _set_readme(_cuda_table_with_dates([
        "[llama.cpp](https://github.com/ggml-org/llama.cpp) 99.7 (2026-09-19)",
        "[Strata](https://github.com/Niko1221/Strata) 93 (2026-10-01)",
    ]))
    try:
        V.check_backend_sort(s)
        check("backend-sort: digits inside link URLs are not t/s -> sorted passes",
              len(V.FAILURES) == 0, json.dumps(V.FAILURES))
    finally:
        _restore_readme()


def test_backend_sort_reads_peak_column_by_header():
    """Current layout: the sort key is the numeric 'Peak t/s' column, read by
    header name — hardware text ('RTX 5090') in the measurements cell must not
    count. Correct order passes; a swapped order fails."""
    def table(rows):
        out = ["# 🟦 CUDA — NVIDIA GPUs", "",
               "| Model | Params | License | VRAM | Peak t/s | Measurements (engine · t/s · hardware · quant · date) |",
               "|---|---|---|---|---|---|"]
        out += [f"| **{n}** | 27B | MIT | 16GB | {p} | [Strata](https://github.com/Niko1221/Strata) **{p}** · RTX 5090 · Q4 · 2026-10-01 |"
                for n, p in rows]
        out += empty_backend_tables("| Model | Peak t/s |")
        return "\n".join(out)
    reset()
    s = store()
    _set_readme(table([("A", 120), ("B", 93)]))
    try:
        V.check_backend_sort(s)
        check("backend-sort: Peak column sorted -> passes (RTX 5090 / 1221 ignored)",
              len(V.FAILURES) == 0, json.dumps(V.FAILURES))
    finally:
        _restore_readme()
    reset()
    _set_readme(table([("A", 93), ("B", 120)]))
    try:
        V.check_backend_sort(s)
        check("backend-sort: Peak column out of order -> FAIL", len(V.FAILURES) == 1, json.dumps(V.FAILURES))
    finally:
        _restore_readme()


def main() -> int:
    print("validate-readme + raw-mapping: direct unit tests")
    test_backend_sort_pass()
    test_backend_sort_fail()
    test_backend_sort_missing_table()

    test_backend_sort_counts_1000plus_and_strips_dates()
    test_backend_sort_dates_not_counted_as_tps()
    test_backend_sort_ignores_digits_in_link_urls()
    test_backend_sort_reads_peak_column_by_header()
    test_readme_has_all_models()
    test_readme_sync_pass()
    test_readme_sync_missing_model()
    test_readme_sync_timestamp_mismatch()
    test_readme_generated_pass()
    test_readme_generated_handedited()
    test_readme_generated_tests_are_clock_independent()
    test_raw_mapping_maps_existing()
    test_raw_mapping_new_model()
    test_raw_mapping_id_collision__maps_by_id()
    test_most_loved_table_clean_shape()
    test_engine_guide_engine_name_is_link()
    test_readme_tables_wellformed()
    print(f"\nPASSED {_PASS} | FAILED {_FAIL}")
    return 1 if _FAIL else 0


if __name__ == "__main__":
    raise SystemExit(main())
