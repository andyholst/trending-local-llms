#!/usr/bin/env python3
"""tests/test_openspec_merge_tree_check.py — issue #1239.

The index count drifts when two PRs regenerate OPENSPEC.md from different bases:
PR-head-only checks are green on both, and the later merge lands a stale count.
This suite reads the real workflow and fails if the merge-tree check, its
failure path or its restore step is dropped.
"""
from __future__ import annotations

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


def main() -> int:
    print("merge-tree index gate (issue #1239):")
    text = (ROOT / ".github/workflows/qa-validate.yml").read_text(encoding="utf-8")
    step = step_slice(text)
    check("validate carries the merge-tree step", bool(step))
    for name in CLAUSES:
        check(f"step keeps {name}", name not in missing(step), name)
    planted = step.replace("git reset --hard HEAD", "git checkout .")
    check("a planted restore omission is named by the guard",
          "tree is restored" in missing(planted), str(missing(planted)))
    check("this suite is discovered by `make test`", wired(__file__))
    print(f"{'FAILED' if _FAIL else 'PASSED'} {_PASS} | FAILED {_FAIL}")
    return 1 if _FAIL else 0


if __name__ == "__main__":
    raise SystemExit(main())
