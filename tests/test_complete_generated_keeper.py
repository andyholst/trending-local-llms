#!/usr/bin/env python3
"""tests/test_complete_generated_keeper.py — the sibling-gate class (issue #1339).

A post-merge repair keeper that regenerates only ONE generated artifact fails the
sibling generated gate and can never auto-merge (measured 2026-11-22: PR #1331 red
at openspec-index-check, PR #1332 red at architecture-check, both generated
artifacts stale on master 48184330). These guards pin the fix in the REAL workflow:
each repair job regenerates BOTH artifacts and lands a keeper naming both files.
"""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WF = (ROOT / ".github" / "workflows" / "qa-validate.yml").read_text(encoding="utf-8")


def _job_block(job_name: str) -> str:
    """Return the YAML text of one job by its `name:` display value."""
    m = re.search(rf"^  [a-z0-9-]+:\n    name: {re.escape(job_name)}\n", WF, re.M)
    assert m, f"job named {job_name!r} not found in qa-validate.yml"
    start = m.start()
    nxt = re.search(r"^  [a-z0-9-]+:\n", WF[start + 1:], re.M)
    end = start + 1 + nxt.start() if nxt else len(WF)
    return WF[start:end]


def test_index_repair_lands_both_generated_files():
    job = _job_block("index-repair (keeper PR for a stale generated index)")
    assert "make architecture-refresh" in job, (
        "index-repair must regenerate the sibling ARCHITECTURE.md block, "
        "else its keeper fails architecture-check (#1339)"
    )
    m = re.search(r'make keeper-pr FILE=([^\s]+(?:\s+[^\s]+)?)', job)
    assert m, "index-repair has no keeper-pr FILE= argument"
    files = m.group(1).strip('"').split()
    assert "OPENSPEC.md" in files and "ARCHITECTURE.md" in files, (
        f"index-repair keeper must own BOTH generated files, got {files} (#1339)"
    )


def test_architecture_repair_lands_both_generated_files():
    job = _job_block("architecture-repair (keeper PR for a stale generated inventory block)")
    assert "make openspec-index" in job, (
        "architecture-repair must regenerate the sibling OPENSPEC.md index, "
        "else its keeper fails openspec-index-check (#1339)"
    )
    m = re.search(r'make keeper-pr FILE=([^\s]+(?:\s+[^\s]+)?)', job)
    assert m, "architecture-repair has no keeper-pr FILE= argument"
    files = m.group(1).strip('"').split()
    assert "OPENSPEC.md" in files and "ARCHITECTURE.md" in files, (
        f"architecture-repair keeper must own BOTH generated files, got {files} (#1339)"
    )


def test_second_keeper_is_noop_when_both_current():
    """keeper_pr.py's real FILE seam supports a space-separated list, so the
    sibling job (landed second) sees no owned file changed and lands no PR."""
    src = (ROOT / "scripts" / "keeper_pr.py").read_text(encoding="utf-8")
    assert "--file" in src and ".split()" in src, (
        "keeper_pr.py must split its --file list so both artifacts are one owned set"
    )
    # The workflow's no-change suppression path is the same one both jobs use.
    assert "make keeper-pr" in WF


def main() -> int:
    """Hand-rolled runner — the workflow-coverage guard requires every test
    module to carry one and to call each of its test_* cases here (rule 6c)."""
    failures = []
    for case in (
        test_index_repair_lands_both_generated_files,
        test_architecture_repair_lands_both_generated_files,
        test_second_keeper_is_noop_when_both_current,
    ):
        try:
            case()
            print(f"  ok  {case.__name__}")
        except AssertionError as exc:
            failures.append(f"{case.__name__}: {exc}")
            print(f"  FAIL {case.__name__}: {exc}")
    if failures:
        print(f"\n{len(failures)} FAILURE(S)")
        return 1
    print("\ncomplete_generated_keeper: all checks pass")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
