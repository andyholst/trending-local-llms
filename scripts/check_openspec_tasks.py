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
  * `- [ ]` / `* [ ]` / `+ [ ]`  -> UNCHECKED (task incomplete — FAILS)
  * `- [x]` / `- [X]`            -> CHECKED (fine)
  * `- [~]`                      -> BLOCKED on a human (issue #409)
  * a bare `-` / `*` bullet that is NOT a checkbox -> ignored (not a task)
  * a checkbox inside a fenced code block          -> ignored (literal sample)
  * a mid-line "[ ]" that is not a list item       -> ignored

The BLOCKED state exists because two of the three states were not enough: work
that is finished as far as an agent may take it and is waiting on a person (an
AGENTS.md row a reviewer must apply, a signature under rule 3c) had only two
exits — tick a box for work that was not done, or leave the CI gate red for a
change whose only remaining work is somebody else's. So:

  * `- [~] <text> — blocked: <who/why>` is ACCEPTED (exit 0) and REPORTED as
    `REVIEW-REQUIRED`, so the change stays visibly incomplete instead of being
    counted as done (an unannotated `- [~]` used to be silently skipped, which
    is why the third state is checked as strictly as the first);
  * a `- [~]` WITHOUT a `blocked:` annotation FAILS: a bare third state is an
    unchecked task wearing a disguise.

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
# Group 1 = the char inside the brackets (space = unchecked, x/X = checked,
# ~ = blocked on a human).
_CHECKBOX = re.compile(r"^\s*[-*+]\s+\[([ xX~])\]\s+")
# A blocked box must say WHO or WHY: the annotation is the difference between a
# third state and a silent skip.
_BLOCKED_REASON = re.compile(r"\bblocked:\s*\S", re.IGNORECASE)


def _in_fence(lines: list[str], i: int) -> bool:
    """True if line *i* is inside a fenced code block (``` or ~~~)."""
    fence_depth = 0
    for j in range(0, i + 1):
        if re.match(r"^\s*(```|~~~)", lines[j]):
            fence_depth += 1
    return fence_depth % 2 == 1


def _boxes(file: Path) -> list[tuple[int, str, str]]:
    """`(1-based line, state char, the line)` for every task box in *file*.

    Lines inside fenced code blocks are ignored. Never raises on a missing or
    unreadable file (returns []); the caller decides how to report absence.
    """
    try:
        lines = file.read_text(encoding="utf-8").splitlines()
    except OSError:
        return []
    out: list[tuple[int, str, str]] = []
    for i, ln in enumerate(lines):
        if _in_fence(lines, i):
            continue
        m = _CHECKBOX.match(ln)
        if m:
            out.append((i + 1, m.group(1), ln))
    return out


def unchecked_tasks(file: Path) -> list[int]:
    """1-based line numbers of `- [ ]` boxes in *file* (the FAILING state)."""
    return [ln for ln, state, _ in _boxes(file) if state == " "]


def blocked_tasks(file: Path) -> list[int]:
    """1-based line numbers of `- [~]` boxes in *file* (blocked on a human)."""
    return [ln for ln, state, _ in _boxes(file) if state == "~"]


def unannotated_blocked_tasks(file: Path) -> list[int]:
    """`- [~]` boxes whose line carries no `blocked:` reason (the FAILING state)."""
    return [
        ln
        for ln, state, text in _boxes(file)
        if state == "~" and not _BLOCKED_REASON.search(text)
    ]


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


def _report_unannotated(name: str, f: Path, bad: list[int]) -> None:
    print(
        f"[openspec-tasks] FAIL {name}: blocked task(s) with no `blocked:` reason "
        f"at lines {bad} — write `- [~] <text> — blocked: <who/why>`"
    )
    lines = f.read_text(encoding="utf-8").splitlines()
    for ln in bad:
        shown = lines[ln - 1].strip() if 1 <= ln <= len(lines) else "(line number beyond file)"
        print(f"    L{ln}: {shown}")


def _report_review(name: str, f: Path, blocked: list[int]) -> None:
    """A blocked task is REPORTED, never silently counted as done (issue #409)."""
    print(
        f"[openspec-tasks] REVIEW-REQUIRED {name}: {len(blocked)} task(s) blocked "
        f"on a human at lines {blocked}"
    )
    lines = f.read_text(encoding="utf-8").splitlines()
    for ln in blocked:
        shown = lines[ln - 1].strip() if 1 <= ln <= len(lines) else "(line number beyond file)"
        print(f"    L{ln}: {shown}")


def _verdict(name: str, f: Path) -> int:
    """Check ONE change's tasks.md: 1 when it fails, 0 otherwise (blocked is 0)."""
    bad = unchecked_tasks(f)
    unannotated = unannotated_blocked_tasks(f)
    blocked = blocked_tasks(f)
    if bad:
        _report(name, f, bad)
    if unannotated:
        _report_unannotated(name, f, unannotated)
    if blocked and not unannotated:
        _report_review(name, f, blocked)
    if bad or unannotated:
        return 1
    if not blocked:
        print(f"[openspec-tasks] OK {name}: all tasks checked")
    return 0


def check_all(
    only: str | None = None, base: Path = CHANGES_DIR, verbose: bool = True
) -> int:
    """Check active changes (all, or just *only*). Returns # of failing changes."""
    if only:
        # An explicitly-requested change must exist and be fully ticked (or
        # explicitly blocked on a human — which is reported, not failed).
        f = tasks_file_for(only, base)
        if f is None:
            print(f"[openspec-tasks] FAIL {only}: no active tasks.md (archived/missing)")
            return 1
        return _verdict(only, f)

    failures = 0
    review: list[str] = []
    for name in active_change_names(base):
        f = tasks_file_for(name, base)
        if f is None:
            print(f"[openspec-tasks] {name}: no active tasks.md (archived/missing) — skip")
            continue
        if _verdict(name, f):
            failures += 1
        elif blocked_tasks(f) and not unannotated_blocked_tasks(f):
            review.append(name)
    if review:
        print(
            f"[openspec-tasks] {len(review)} change(s) need a HUMAN review "
            f"(blocked task(s), not done): {', '.join(review)}"
        )
    return failures


if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else None
    raise SystemExit(1 if check_all(target) > 0 else 0)
