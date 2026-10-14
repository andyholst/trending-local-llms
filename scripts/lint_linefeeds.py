#!/usr/bin/env python3
"""Every tracked text file ends with a newline (issue #186).

A file without a final newline is a real diff defect: git prints ``\\ No newline
at end of file``, the next append to that file shows a spurious last-line change,
and a naive line-based tool can drop the line. This repo had **no** check for it
(no `.editorconfig` either), and five tracked files already violated it when this
landed.

    make lint        # fail closed: list every tracked text file without a final newline
    make lint-fix    # append exactly one newline to each and re-report

The file set is what git tracks (`git ls-files`), so an ignored or generated file
can never fail the lint, and a new file is covered the moment it is added. A file
is treated as text unless its first 8000 bytes contain a NUL byte; an empty file
has no missing newline to report. The check is pure stdlib, so the same command
runs on the host and inside the test image with the same answer.

Wired into `make lint` (a `qa-validate` step), into `scripts/fix_loop.sh`'s check
list (so the fix loop repairs a missing newline like any other red check) and into
`make test` through `tests/test_lint_linefeeds.py` (rule 6d).

Usage:
    python3 scripts/lint_linefeeds.py            # check the repository (exit 1 on a finding)
    python3 scripts/lint_linefeeds.py --fix      # repair, then report what changed
    python3 scripts/lint_linefeeds.py --root DIR # check a fixture tree
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

SNIFF = 8000


def tracked_files(root: Path) -> list[str]:
    """The tracked files of *root* (via git), sorted; [] when git cannot answer.

    `-c safe.directory=*` because the test suite runs this inside a container as
    root over host-owned files: without it git refuses to answer ("detected
    dubious ownership") and a false red would be reported for a correct tree.
    """
    out = subprocess.run(
        ["git", "-c", "safe.directory=*", "-C", str(root), "ls-files"],
        capture_output=True, text=True,
    )
    if out.returncode != 0:
        return []
    return sorted(line for line in out.stdout.splitlines() if line.strip())


def is_binary(path: Path) -> bool:
    try:
        return b"\0" in path.read_bytes()[:SNIFF]
    except OSError:
        return True


def missing_newline(path: Path) -> bool:
    """True when the file is non-empty, non-binary and does not end with a newline."""
    try:
        data = path.read_bytes()
    except OSError:
        return False
    if not data or is_binary(path):
        return False
    return not data.endswith(b"\n")


def offenders(root: Path) -> list[str]:
    """Every tracked text file without a final newline, sorted."""
    return [f for f in tracked_files(root) if missing_newline(root / f)]


def fix(root: Path) -> list[str]:
    """Append one newline to each offender; return what was repaired."""
    repaired = []
    for name in offenders(root):
        path = root / name
        with path.open("ab") as fh:
            fh.write(b"\n")
        repaired.append(name)
    return repaired


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Every tracked text file ends with a newline")
    ap.add_argument("--fix", action="store_true", help="append the missing newline to each file")
    ap.add_argument("--root", default=str(Path(__file__).resolve().parents[1]))
    a = ap.parse_args(argv)

    root = Path(a.root)
    files = tracked_files(root)
    if not files:
        print(f"[lint] no tracked files under {root} (not a git checkout?)", file=sys.stderr)
        return 1

    if a.fix:
        repaired = fix(root)
        for name in repaired:
            print(f"[lint] fixed {name}: appended the missing final newline")
        left = offenders(root)
        if left:  # cannot happen without a concurrent writer, but never report a false green
            print(f"[lint] FAIL still missing a final newline: {left}", file=sys.stderr)
            return 1
        print(f"[lint] OK every one of {len(files)} tracked files ends with a newline "
              f"({len(repaired)} repaired)")
        return 0

    bad = offenders(root)
    if bad:
        print(f"[lint] FAIL {len(bad)} tracked file(s) do not end with a newline:", file=sys.stderr)
        for name in bad:
            print(f"[lint]   - {name}", file=sys.stderr)
        print("[lint] run `make lint-fix` to append it (and keep the diff honest)", file=sys.stderr)
        return 1

    print(f"[lint] OK every one of {len(files)} tracked files ends with a newline")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
