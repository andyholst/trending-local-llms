#!/usr/bin/env python3
"""Unstage the bot's working files, from ONE list (issue #543).

A bot run writes its inputs and logs at the repository root (`issue.md`, `pr-body.md`,
`findings.md`, `implement.log`, …). They are gitignored, but both bots unstage them explicitly
before `git add -A`, because a name written before the `.gitignore` entry lands — or created in
another checkout — can be staged anyway, and a commit carrying a reviewer's `findings.md`
publishes scratch inside the repository (issue #390 measured the sibling case: a 0-byte
`qa-report.txt.notes` reached PR #387).

That unstage used to be one long `git reset -q -- …` line, copied verbatim into two steps of
`issue-bot.yml` and a third time into `fix-bot.yml`, with `.gitignore` as the fourth copy. This
module is the implementation those steps call: the list is
`scripts/issue_bot_working_files.txt`, and `make check-working-files` proves every name on it is
also gitignored.

Usage:
    python3 scripts/reset_working_files.py [--root DIR] [--list FILE] [--check]

Exit codes: 0 = done (or every name is ignored, with --check); 1 = a name is not ignored
(--check), the list is missing/empty, or git could not read the tree.
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

LIST = Path("scripts") / "issue_bot_working_files.txt"


def names(list_file: Path) -> list[str]:
    """The working-file names, in file order, comments and blanks dropped."""
    out: list[str] = []
    for line in list_file.read_text(encoding="utf-8").splitlines():
        name = line.strip()
        if not name or name.startswith("#"):
            continue
        out.append(name)
    return out


def git(args: list[str], root: Path) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], cwd=str(root), capture_output=True, text=True)


def unstage(root: Path, list_file: Path) -> int:
    """`git reset --` every name that exists, so a name no run wrote is not an error."""
    if not list_file.is_file():
        print(f"[working-files] FAIL: {list_file} is missing — it is the ONE list of the files a "
              f"bot run writes (issue #543)", file=sys.stderr)
        return 1
    known = names(list_file)
    there = [n for n in known if (root / n).exists()]
    if not there:
        print(f"[working-files] nothing to unstage ({len(known)} name(s) known)")
        return 0
    # The old shell line ended `2>/dev/null || true`, which hid a real failure (a broken index,
    # a git that cannot read the tree). Here a non-zero exit is REPORTED.
    proc = git(["reset", "-q", "--", *there], root)
    if proc.returncode != 0:
        detail = (proc.stderr or proc.stdout).strip().splitlines()
        print(f"[working-files] git reset failed ({proc.returncode}): "
              f"{detail[0] if detail else 'no output'}", file=sys.stderr)
        return 1
    print(f"[working-files] unstaged {len(there)} working file(s): {', '.join(there)}")
    return 0


def check(root: Path, list_file: Path) -> int:
    """Every name on the list must be gitignored, or `git add -A` can carry it (issue #543)."""
    if not list_file.is_file():
        print(f"[working-files] FAIL: {list_file} is missing — the list is the one definition",
              file=sys.stderr)
        return 1
    known = names(list_file)
    if not known:
        print(f"[working-files] FAIL: {list_file} names nothing (a vacuous guard)",
              file=sys.stderr)
        return 1
    proc = subprocess.run(["git", "check-ignore", "--stdin"], cwd=str(root),
                          input="\n".join(known), capture_output=True, text=True)
    if proc.returncode not in (0, 1):
        print(f"[working-files] FAIL: git check-ignore could not read the tree: "
              f"{proc.stderr.strip()}", file=sys.stderr)
        return 1
    ignored = {line.strip() for line in proc.stdout.splitlines() if line.strip()}
    missing = [n for n in known if n not in ignored]
    if missing:
        print(f"[working-files] FAIL: not gitignored — `git add -A` can commit these: "
              f"{', '.join(missing)}", file=sys.stderr)
        return 1
    print(f"[working-files] OK: all {len(known)} name(s) are gitignored")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Unstage the bot's working files, from ONE list")
    ap.add_argument("--root", default=".", help="repository root (default: .)")
    ap.add_argument("--list", default=None, help=f"the list file (default: {LIST})")
    ap.add_argument("--check", action="store_true",
                    help="assert every name on the list is gitignored (never writes)")
    args = ap.parse_args(argv)
    root = Path(args.root).resolve()
    list_file = Path(args.list) if args.list else root / LIST
    if git(["rev-parse", "--git-dir"], root).returncode != 0:
        print(f"[working-files] FAIL: {root} is not a git checkout", file=sys.stderr)
        return 1
    return check(root, list_file) if args.check else unstage(root, list_file)


if __name__ == "__main__":
    raise SystemExit(main())
