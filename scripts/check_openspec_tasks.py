#!/usr/bin/env python3
"""Ensure active OpenSpec changes have ALL task checkboxes completed.

`openspec validate` checks a change's STRUCTURE (proposal / specs / tasks all
present and well-formed) but does NOT fail on `- [ ]` unchecked task boxes — an
implementer can leave tasks unticked and CI stays green. This script is the
completion half of the gate: it fails (exit non-zero) when any ACTIVE change's
`tasks.md` still has an unchecked box.

Scope: only ACTIVE (non-archived) changes under `openspec/changes/*`. Archived
changes (`openspec/changes/archive/<name>`, written by `openspec archive`)
legitimately keep their original tasks and are excluded.

Wired into `make openspec-tasks-check`, which `make openspec-check` runs and
`qa-validate` calls on every PR (rule 6d: reachable from a make target CI runs).

Checkbox recognition (GFM markdown):
  * `- [ ]` / `* [ ]` / `+ [ ]`  -> UNCHECKED (task incomplete)
  * `- [x]` / `- [X]`            -> CHECKED (fine)
  * a bare `-` / `*` bullet that is NOT a checkbox -> ignored (not a task)
  * a checkbox inside a fenced code block          -> ignored (literal sample)
  * a mid-line "[ ]" that is not a list item       -> ignored

Usage:
    python3 scripts/check_openspec_tasks.py            # all active changes
    python3 scripts/check_openspec_tasks.py <name>     # just <name>
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
CHANGES_DIR = REPO_ROOT / "openspec" / "changes"

# A line whose FIRST non-whitespace run is a list marker then a bracket.
# Group 1 = the char inside the brackets (space = unchecked, x/X = checked).
_CHECKBOX = re.compile(r"^\s*[-*+]\s+\[([ xX])\]\s+")


def _in_fence(lines: list[str], i: int) -> bool:
    """True if line *i* is inside a fenced code block (``` or ~~~)."""
    fence_depth = 0
    for j in range(0, i + 1):
        if re.match(r"^\s*(```|~~~)", lines[j]):
            fence_depth += 1
    return fence_depth % 2 == 1


def unchecked_tasks(file: Path) -> list[int]:
    """1-based line numbers of unchecked `- [ ]` boxes in *file*.

    Lines inside fenced code blocks are ignored. Never raises on a missing or
    unreadable file (returns []); the caller decides how to report absence.
    """
    try:
        lines = file.read_text(encoding="utf-8").splitlines()
    except OSError:
        return []
    bad: list[int] = []
    for i, ln in enumerate(lines):
        if _in_fence(lines, i):
            continue
        m = _CHECKBOX.match(ln)
        if m and m.group(1) == " ":
            bad.append(i + 1)
    return bad


def active_change_names(base: Path = CHANGES_DIR) -> list[str]:
    """All ACTIVE (non-archived) change names that have a tasks.md."""
    if not base.is_dir():
        return []
    out = []
    for p in sorted(base.iterdir()):
        if not p.is_dir() or p.name == "archive":
            continue
        if (p / "tasks.md").is_file():
            out.append(p.name)
    return out


def tasks_file_for(change: str, base: Path = CHANGES_DIR) -> Path | None:
    """tasks.md for an ACTIVE change; None if archived or missing."""
    if (base / "archive" / change).exists():
        return None
    p = base / change / "tasks.md"
    return p if p.is_file() else None


def _report(name: str, f: Path, bad: list[int]) -> None:
    print(f"[openspec-tasks] FAIL {name}: unchecked task checkbox(es) at lines {bad}")
    lines = f.read_text(encoding="utf-8").splitlines()
    for ln in bad:
        shown = lines[ln - 1].strip() if 1 <= ln <= len(lines) else "(line number beyond file)"
        print(f"    L{ln}: {shown}")


def check_all(
    only: str | None = None, base: Path = CHANGES_DIR, verbose: bool = True
) -> int:
    """Check active changes (all, or just *only*). Returns # of failing changes."""
    if only:
        # An explicitly-requested change must exist and be fully ticked.
        f = tasks_file_for(only, base)
        if f is None:
            print(f"[openspec-tasks] FAIL {only}: no active tasks.md (archived/missing)")
            return 1
        bad = unchecked_tasks(f)
        if bad:
            _report(only, f, bad)
            return 1
        print(f"[openspec-tasks] OK {only}: all tasks checked")
        return 0

    failures = 0
    for name in active_change_names(base):
        f = tasks_file_for(name, base)
        if f is None:
            print(f"[openspec-tasks] {name}: no active tasks.md (archived/missing) — skip")
            continue
        bad = unchecked_tasks(f)
        if bad:
            failures += 1
            _report(name, f, bad)
        else:
            print(f"[openspec-tasks] OK {name}: all tasks checked")
    return failures


if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else None
    raise SystemExit(1 if check_all(target) > 0 else 0)
