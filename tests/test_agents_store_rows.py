#!/usr/bin/env python3
"""`AGENTS.md` carries #1395's declared store-architecture rows (issue #1482).

PR #1479 (`fix/store-architecture-doc-1395`) landed `ARCHITECTURE.md` §2 +
`docs/store.md` and the names-only `scripts/architecture_check.py::
store_file_findings` guard, but the rule-3c-declared `AGENTS.md` edits were
NOT in that tree: the headless leg could not write the protected file. Issue
#1482 owes those three texts, byte-for-byte, as `tll-reviewer` approved them in
`issuecomment-7128719625`:

  1. §7b CHANGE 1 — name the store architecture page's two artifacts
     (`ARCHITECTURE.md` §2 plus `docs/store.md`).
  2. §7b CHANGE 2 — append the rule-3c provenance clause for issue #1395.
  3. §8 — insert the `tests/test_architecture.py` /
     `scripts/architecture_check.py::store_file_findings` regression row.

This guard reads the REAL `AGENTS.md` — no fixture, no stand-in (rule 6m) — and
asserts the three texts are present VERBATIM, so a later edit that re-words or
drops one of them reds here. It is RED on the pre-landing tree by design: the
rows do not exist yet.

Run:  python3 tests/test_agents_store_rows.py   or   make test
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
AGENTS = ROOT / "AGENTS.md"

#: The reviewer-approved §7b first paragraph (CHANGE 1), verbatim.
CHANGE_1 = """The eight `tll-*` lanes are host agents on several machines, started by the owner. The issue
thread is the ONE shared board; a PR is a delivery artifact, never a handover. `tll-docs`
owns the repository's prose — the contract ⇄ docs sync, the store architecture page
(`ARCHITECTURE.md` §2 plus `docs/store.md`) and the doc gaps a delivered PR leaves behind;
it never edits `data/`, a workflow or the generated README."""

#: The reviewer-approved clause appended to the §7b `Rule 3c note` (CHANGE 2).
CHANGE_2 = "The store-architecture page's artifact names were added by issue #1395 and are review-required; the declaration is on that issue."

#: The reviewer-approved §8 regression row, verbatim (978 chars).
ROW_8 = """| `tests/test_architecture.py` — `test_the_dataflow_region_names_every_shipped_store_file`, `test_a_dropped_store_filename_is_red`, `test_the_real_document_passes_the_store_file_scan` + `scripts/architecture_check.py`'s `store_file_findings` (rules 6h/3c, issue #1395) | the architecture description drifting from the shipped #689 store: `ARCHITECTURE.md` §2 drawing one flat `data/models.json` with inline `engines[]` (measured on `d792d29f`: 120 catalog models, **0** carrying inline `engines[]`; the rows live in `data/measurements.json`, 120 models / 611 rows, with engagement published once per `source_post` in `data/posts.json`, 382 posts), so a reader cannot tell where a figure lives. The scan reads the §2 data-flow region bounded by its own anchor and proves the three shipped filenames are NAMED — `data/models.json`, `data/measurements.json`, `data/posts.json` — failing naming any that is dropped; names only, never prose, the same boundary rule 6h already draws |"""

_PASS = 0
_FAIL = 0


def check(name, cond, detail: object = "") -> None:
    global _PASS, _FAIL
    if cond:
        _PASS += 1
        print(f"  ok  {name}")
    else:
        _FAIL += 1
        print(f"  FAIL {name}" + (f"  [{detail}]" if detail else ""))


def section_7b(text: str) -> str:
    """`AGENTS.md` §7b, whole — the fleet lifecycle/delegation section."""
    start = text.index("\n## 7b. TLL fleet")
    return text[start:text.index("\n## 8. ", start)]


def test_section_7b_names_the_two_store_artifacts() -> None:
    """Acceptance 1: §7b's first paragraph names BOTH store-architecture
    artifacts, not just "the store architecture page"."""
    body = section_7b(AGENTS.read_text(encoding="utf-8"))
    para = next(p for p in body.split("\n\n") if p.startswith("The eight `tll-*` lanes"))
    check("agents: §7b first paragraph equals the approved CHANGE 1 text",
          para == CHANGE_1, para[:120])
    check("agents: §7b names `ARCHITECTURE.md` §2", "`ARCHITECTURE.md` §2" in para, para[:120])
    check("agents: §7b names `docs/store.md`", "`docs/store.md`" in para, para[:120])


def test_rule_3c_note_records_the_1395_provenance() -> None:
    """Acceptance 2: the §7b `Rule 3c note` carries the #1395 provenance clause."""
    note = next(ln for ln in section_7b(AGENTS.read_text(encoding="utf-8")).splitlines()
                if ln.startswith("Rule 3c note:"))
    check("agents: §7b rule-3c note ends with the approved CHANGE 2 clause",
          note.endswith(CHANGE_2), note[-160:])
    check("agents: §7b rule-3c note keeps the earlier provenance clauses",
          "issue #1209" in note and "issue #1232" in note and "issue #1258" in note, note[:120])


def test_section_8_carries_the_1395_regression_row() -> None:
    """Acceptance 3: §8 carries the #1395 regression row verbatim, adjacent to
    its `tests/test_architecture.py` sibling."""
    lines = AGENTS.read_text(encoding="utf-8").splitlines()
    hits = [i for i, ln in enumerate(lines) if ln == ROW_8]
    check("agents: §8 carries the approved row exactly once", len(hits) == 1, hits)
    if hits:
        i = hits[0]
        prev_ok = i > 0 and lines[i - 1].startswith("| `tests/test_architecture.py`")
        next_ok = i + 1 < len(lines) and lines[i + 1].startswith("| `tests/test_architecture.py`")
        check("agents: the #1395 row sits between its `test_architecture.py` siblings",
              prev_ok and next_ok, (lines[i - 1][:80] if i else "", lines[i + 1][:80] if i + 1 < len(lines) else ""))
    text = AGENTS.read_text(encoding="utf-8")
    check("agents: §8 row names the `store_file_findings` guard",
          "store_file_findings" in text and ROW_8.count("store_file_findings") == 1, "")


def main() -> int:
    print("rulebook store rows: AGENTS.md carries #1395's declared §7b/§8 texts (#1482)")
    print("-- test_section_7b_names_the_two_store_artifacts")
    test_section_7b_names_the_two_store_artifacts()
    print("-- test_rule_3c_note_records_the_1395_provenance")
    test_rule_3c_note_records_the_1395_provenance()
    print("-- test_section_8_carries_the_1395_regression_row")
    test_section_8_carries_the_1395_regression_row()
    print(f"{_PASS} passed, {_FAIL} failed")
    return 1 if _FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
