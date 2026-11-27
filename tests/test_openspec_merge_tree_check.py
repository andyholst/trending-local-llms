#!/usr/bin/env python3
"""tests/test_openspec_merge_tree_check.py — issues #1239 and #1822.

The index count drifts when two PRs regenerate OPENSPEC.md from different bases:
PR-head-only checks are green on both, and the later merge lands a stale count.
The baseline suite (issue #1239) pins the real workflow's merge-tree step, its
failure path, its restore step and its full-history precondition.

Issue #1822 extends it with the classifier that separates a generated-index
conflict caused by master advancing mid-validate from a genuine source conflict.
The REAL classifier is driven through the real `make merge-tree-index-classify`
target — no business logic is mocked (rule 6m). The two RED-first verdict tests
fail on the pre-#1822 tree because neither the seam nor the retry verdict exists.
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tests"))
from wiring import wired  # noqa: E402

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


def step_slice(text: str) -> str:
    a = text.find("- name: OpenSpec index on the merge tree (issue #1239)")
    if a < 0:
        return ""
    b = text.find("\n      - name:", a + 8)
    return text[a:b if b > a else len(text)]


def workflow_step() -> str:
    return step_slice((ROOT / ".github/workflows/qa-validate.yml").read_text(encoding="utf-8"))


def classify(conflicts: str, base_before: str, master_after: str) -> subprocess.CompletedProcess:
    """Drive the real make target. `IN_CONTAINER=1` uses the documented test
    harness fork (no nested docker); the seam stays byte-identical in CI."""
    env = dict(os.environ, IN_CONTAINER="1")
    return subprocess.run(
        ["make", "-s", "merge-tree-index-classify",
         f"CONFLICTS={conflicts}",
         f"BASE_BEFORE={base_before}",
         f"MASTER_AFTER={master_after}"],
        cwd=str(ROOT), env=env, capture_output=True, text=True,
    )


def verdict(result: subprocess.CompletedProcess) -> str:
    lines = [line.strip() for line in result.stdout.splitlines() if line.strip()]
    return lines[-1] if lines else ""


CLAUSES = {
    "merge-tree step exists": "- name: OpenSpec index on the merge tree (issue #1239)",
    "fetches current master": "git fetch origin master:refs/remotes/origin/master",
    "merges without committing": "git merge --no-commit --no-ff origin/master",
    "runs the same gate": "make openspec-index-check",
    "failure is loud": "[merge-tree-index] FAIL",
    "conflict is loud": "[merge-tree-index] MERGE CONFLICT",
    "tree is restored": "git reset --hard HEAD",
    "PR-head check kept": "make openspec-check",
}


def missing(step: str) -> list[str]:
    return [name for name, needle in CLAUSES.items() if needle not in step]


def test_all_1239_clauses_survive():
    """Every #1239 clause is still byte-present; no skip, no weakening."""
    text = (ROOT / ".github/workflows/qa-validate.yml").read_text(encoding="utf-8")
    step = step_slice(text)
    check("validate carries the merge-tree step", bool(step))
    for name in CLAUSES:
        check(f"step keeps {name}", name not in missing(step), name)
    planted = step.replace("git reset --hard HEAD", "git checkout .")
    check("a planted restore omission is named by the guard",
          "tree is restored" in missing(planted), str(missing(planted)))
    # The two provenance preconditions of the original #1239 fix.
    step_at = text.find("- name: OpenSpec index on the merge tree (issue #1239)")
    checkout_at = text.rfind("- name: Checkout", 0, step_at)
    checkout = text[checkout_at:step_at] if checkout_at >= 0 else ""
    check("validate checkout keeps full history (fetch-depth: 0)",
          "fetch-depth: 0" in checkout, checkout[:120])
    fetch_line = next((ln.strip() for ln in step.splitlines()
                       if "git fetch origin master:" in ln), "")
    check("the merge-tree fetch keeps full history (no --depth)",
          bool(fetch_line) and "--depth" not in fetch_line, fetch_line)


def test_generated_advance_conflict_gets_a_distinct_retryable_verdict():
    """RED on the pre-#1822 tree: no seam, no verdict, no retry line."""
    result = classify("OPENSPEC.md", "aaaaaaa", "bbbbbbb")
    check("the real seam is reachable and exits 0", result.returncode == 0,
          result.stderr[-300:] or result.stdout[-300:])
    check("generated-only conflict + advanced master is GENERATED_ADVANCE",
          verdict(result) == "GENERATED_ADVANCE", result.stdout or result.stderr)
    step = workflow_step()
    check("the step emits a distinct retry verdict",
          "[merge-tree-index] MASTER-ADVANCE-RETRY" in step)
    check("unmerged paths are captured BEFORE the abort",
          step.find("git diff --name-only --diff-filter=U") >= 0
          and step.find("git diff --name-only --diff-filter=U")
          < step.find("git merge --abort"))
    check("the generated index is regenerated by its OWNING command and staged",
          "make openspec-index" in step and "git add OPENSPEC.md" in step)
    check("the retry is bounded to freshly fetched master",
          step.count("git fetch origin master:refs/remotes/origin/master") >= 2)


def test_real_conflict_still_fails():
    """A non-generated path, or no path at all, keeps the original hard fail."""
    for label, conflicts in (("generated plus source", "OPENSPEC.md,scripts/x.py"),
                             ("source only", "README.md"),
                             ("no captured paths", "")):
        result = classify(conflicts, "aaaaaaa", "bbbbbbb")
        check(f"{label} is REAL_CONFLICT",
              result.returncode == 0 and verdict(result) == "REAL_CONFLICT",
              result.stdout or result.stderr)
    step = workflow_step()
    check("REAL_CONFLICT keeps the exact hard-fail line",
          "[merge-tree-index] MERGE CONFLICT: rebase on current master and retry" in step)
    check("REAL_CONFLICT keeps exit 1", "exit 1" in step)


def test_a_generated_conflict_without_a_master_advance_is_not_a_race():
    """RED on the pre-#1822 tree: no seam to reject an unadvanced master."""
    result = classify("OPENSPEC.md", "abc123", "abc123")
    check("a generated-only conflict with no master advance is REAL_CONFLICT",
          result.returncode == 0 and verdict(result) == "REAL_CONFLICT",
          result.stdout or result.stderr)
    check("an empty SHA is not proof of a race either",
          verdict(classify("OPENSPEC.md", "", "abc123")) == "REAL_CONFLICT")


def test_clean_merge_stale_index_still_fails():
    """#1239's clean-merge stale-index detection is unchanged."""
    step = workflow_step()
    check("the clean-merge path still runs the real gate",
          "if ! make openspec-index-check; then" in step)
    check("the clean-merge stale index still hard-fails with FAIL",
          "[merge-tree-index] FAIL" in step and "exit 1" in step)
    check("the retry lives only in the conflict branch",
          step.find("if ! git merge --no-commit --no-ff origin/master >/dev/null 2>&1; then")
          < step.find("MASTER-ADVANCE-RETRY"))


def test_wired():
    """New seam, target, workflow caller and suite discovery are all present."""
    makefile = (ROOT / "Makefile").read_text(encoding="utf-8")
    check("public make target exists", "merge-tree-index-classify:" in makefile)
    check("host `_` recipe exists", "_merge-tree-index-classify:" in makefile)
    check("target routes through the python-env image",
          "merge-tree-index-classify: python-env-image" in makefile)
    check("the workflow calls the make target",
          "make merge-tree-index-classify" in workflow_step())
    check("the seam module exists", (ROOT / "scripts/merge_tree_index.py").is_file())
    check("this suite is discovered by `make test`", wired(__file__))


def main() -> int:
    print("merge-tree index gate (#1239 + #1822):")
    for test in (test_all_1239_clauses_survive,
                 test_generated_advance_conflict_gets_a_distinct_retryable_verdict,
                 test_real_conflict_still_fails,
                 test_a_generated_conflict_without_a_master_advance_is_not_a_race,
                 test_clean_merge_stale_index_still_fails,
                 test_wired):
        test()
    print(f"{'FAILED' if _FAIL else 'PASSED'} {_PASS} | FAILED {_FAIL}")
    return 1 if _FAIL else 0


if __name__ == "__main__":
    raise SystemExit(main())
