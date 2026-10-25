#!/usr/bin/env python3
"""Fail when a tracked file carries a merge-conflict block (issue #588).

`#583` removed the one PRODUCER of markers it knew about: a conflicted `branch-adopt`
re-apply, which used to leave `<<<<<<<` in the tree and let `git add -A` commit it. Measured on
run 40202490846 the markers landed in the **Makefile**, the commit succeeded, and the next
target died with `Makefile:588: *** missing separator` — after which nothing in the run could be
repaired, because every `make` had to parse the broken file first.

That fix is producer-side. This is the last line of defence: any OTHER source of a marker — a
botched manual merge, a salvaged detached run, a `git stash pop` an operator ran, a future tool
— is refused before it becomes a commit, naming the paths.

A conflict block is a line that starts a marker (7 `<`, `=`, `|`, or `>` characters, optionally
followed by a branch name), which is git's own format. The check reads `git ls-files`, so an
IGNORED or generated file never fails it, and it skips binary files (a NUL byte in the first
8000 bytes) so a marker-shaped byte sequence inside an image is not a finding.

Usage:
    python3 scripts/check_conflict_markers.py [--root DIR] [PATHS…]

Exit: 0 = clean (or nothing to scan), 1 = markers found (paths are named), 2 = not a git tree.
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

#: Git's conflict markers, at the start of a line. `|||||||` is the diff3 base marker.
MARKER = re.compile(r"^(?:<{7}|={7}|\|{7}|>{7})(?:[ \t].*)?$")
BINARY_PROBE = 8000


def tracked(root: Path) -> list[str]:
    out = subprocess.run(["git", "ls-files", "-z"], cwd=str(root), capture_output=True)
    if out.returncode != 0:
        print(f"[conflict-markers] FAIL: {root} is not a git checkout: "
              f"{out.stderr.decode(errors='replace').strip()}", file=sys.stderr)
        raise SystemExit(2)
    return [p for p in out.stdout.decode("utf-8", "replace").split("\0") if p]


def scan(path: Path) -> list[int]:
    """The 1-based line numbers of conflict markers in `path` (empty for binary files)."""
    try:
        blob = path.read_bytes()
    except OSError:
        return []
    if b"\0" in blob[:BINARY_PROBE]:
        return []
    text = blob.decode("utf-8", "replace")
    return [i for i, line in enumerate(text.splitlines(), 1) if MARKER.match(line)]


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Fail when a tracked file has a merge-conflict block")
    ap.add_argument("--root", default=".", help="repository root (default: .)")
    ap.add_argument("paths", nargs="*", help="limit the scan to these paths (default: every tracked file)")
    args = ap.parse_args(argv)
    root = Path(args.root).resolve()
    candidates = args.paths or tracked(root)
    findings: list[tuple[str, list[int]]] = []
    for rel in candidates:
        lines = scan(root / rel)
        if lines:
            findings.append((rel, lines))
    if not findings:
        print(f"[conflict-markers] OK: no conflict marker in {len(candidates)} tracked file(s)")
        return 0
    for rel, lines in findings:
        print(f"[conflict-markers] FAIL: {rel} carries a conflict block at line(s) "
              f"{', '.join(str(n) for n in lines[:5])}", file=sys.stderr)
    print(f"[conflict-markers] {len(findings)} file(s) with a conflict marker — resolve them "
          f"before committing: a marker in a parsed file (Makefile, a workflow, a module) makes "
          f"every later `make` fail (#588).", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
