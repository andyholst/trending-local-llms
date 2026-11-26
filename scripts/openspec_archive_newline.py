#!/usr/bin/env python3
"""Give every text file an OpenSpec archive just created a final newline.

`make openspec-archive NAME=<change>` runs `openspec archive <name> -y`; the CLI
writes the archived `.openspec.yaml` without a trailing 0x0a. That file is still
untracked at that instant, so rule 6i's `make lint-fix` (file set = `git
ls-files`) cannot see it and the delivery's first `qa-validate/validate` reds at
the newline lint step on a file its own pipeline created (issue #1782, measured
on PR #1774's head `000772fe`, run `45838927284`).

The seam runs host-side immediately after the CLI archive, over the real
bind-mounted tree: it appends exactly one 0x0a to each text file under
`openspec/changes/archive/<name>/` that lacks one. Empty files, files already
ending with a newline, and files carrying a NUL byte in their first 8000 bytes
(binary) are left byte-identical. It is idempotent and additive — no existing
byte is ever removed or rewritten (rule 3b). A missing archive dir is refused
loudly rather than reported as a vacuous clean.

Reached only through `make openspec-archive` (rules 6d/6m); exercised by
`tests/test_openspec_archive_newline.py` in `make test`.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


class MissingArchiveDir(Exception):
    """No directory was created for the named archive."""


def resolve_archive(root: Path, name: str) -> Path:
    """Find the directory the CLI created for `name`.

    `openspec archive <name> -y` moves the change to
    `openspec/changes/archive/<name>` on some versions and to the
    date-prefixed `openspec/changes/archive/<YYYY-MM-DD>-<name>` on others
    (measured 2026-11-26: the latter). Accept both; prefer an exact match,
    otherwise the lexically newest date-prefixed dir. Refuse loudly when
    neither exists, so a no-op can never be reported as a clean archive.
    """
    archive_root = root / "openspec" / "changes" / "archive"
    if not archive_root.is_dir():
        raise MissingArchiveDir(f"no archived change dir for {name!r} under {archive_root}")
    exact = archive_root / name
    if exact.is_dir():
        return exact
    dated = sorted(
        (p for p in archive_root.iterdir()
         if p.is_dir() and p.name.endswith("-" + name)),
        key=lambda p: p.name,
    )
    if dated:
        return dated[-1]
    raise MissingArchiveDir(f"no archived change dir for {name!r} under {archive_root}")


def ensure_newlines(root: Path, name: str) -> list[str]:
    """Append a final newline to archived text files that lack one.

    Returns the repo-relative paths that were changed (empty on a no-op).
    """
    archive = resolve_archive(root, name)
    fixed: list[str] = []
    for path in sorted(archive.rglob("*")):
        if not path.is_file():
            continue
        data = path.read_bytes()
        if not data or data.endswith(b"\n") or b"\x00" in data[:8000]:
            continue
        path.write_bytes(data + b"\n")
        fixed.append(str(path.relative_to(root)))
    return fixed


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--name", required=True, help="the archived change name")
    parser.add_argument("--root", default=str(ROOT), help="repo root (default: this repo)")
    args = parser.parse_args(argv)
    root = Path(args.root)
    try:
        fixed = ensure_newlines(root, args.name)
    except MissingArchiveDir as exc:
        print(f"[openspec-newline] REFUSED: {exc}", file=sys.stderr)
        return 2
    if fixed:
        print("[openspec-newline] appended final newline: " + ", ".join(fixed))
    else:
        print("[openspec-newline] OK: every archived text file ends with a newline")
    return 0


if __name__ == "__main__":
    sys.exit(main())
