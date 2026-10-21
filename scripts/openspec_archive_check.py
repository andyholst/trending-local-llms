#!/usr/bin/env python3
"""An ACTIVE OpenSpec change must not name a MERGED pull request (issue #183).

Rule 6f gives every change a life: `make openspec-new` creates it, the capability
spec and `tasks.md` describe it, `OPENSPEC.md` lists it — and then **nothing said
when it ends**. Measured on `master` when this check was written: 115 changes
"active", 0 archived, `openspec/changes/archive/` empty, and six of those active
changes named a `PR:` that GitHub reports as merged (#173, #180, #189, #374,
#379, #384). The index's own count was therefore not a measure of in-flight work:
a merged change and an unfinished one looked identical.

The rule this enforces (AGENTS.md 6f): in the PR that completes a change — once
its `PR:` line is known — that PR runs `make openspec-archive NAME=<change>` and
`make openspec-index`, so the change lands in `openspec/changes/archive/` with the
index regenerated in one commit.

This is the ONE implementation (rule 6d) of the check:

  * an ACTIVE change whose `PR:` line names a MERGED PR is a failure (exit 1),
    naming the change, the PR and the two commands that fix it;
  * an active change with no `PR:` line is skipped — there is nothing to assert;
  * an ARCHIVED change is skipped — a merged PR is its expected state;
  * a GitHub read that fails is LOUD (exit 2): a check that could not see the
    state must never report it as clean (rule 6d's "a scan that proves nothing").

PR state is read through `gh` (the same tool the pipeline uses for every GitHub
fact): `gh api repos/<owner>/<repo>/pulls/<n> --jq .merged`. The repository comes
from `--repo`, else `GITHUB_REPOSITORY`, else `gh`'s own resolution.

Usage:
    python3 scripts/openspec_archive_check.py
    python3 scripts/openspec_archive_check.py --repo andyholst/trending-local-llms
"""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from openspec_index import discover, _refs  # noqa: E402  (one parser, one layout — rule 6d)

REPO_ROOT = Path(__file__).resolve().parent.parent
_PR_NUMBER = re.compile(r"#(\d+)")


def _gh(args: list[str]) -> str:
    """Run `gh` and return its stdout; every failure is LOUD (raises)."""
    try:
        r = subprocess.run(["gh", *args], capture_output=True, text=True)
    except FileNotFoundError as exc:  # no gh on PATH: we cannot see any PR state
        raise RuntimeError(
            "`gh` is not installed — the PR state of a change cannot be checked "
            "(install gh, or read the check's evidence by hand)"
        ) from exc
    if r.returncode != 0:
        raise RuntimeError(f"gh {' '.join(args)} failed: {(r.stderr or r.stdout).strip()}")
    return r.stdout.strip()


def pr_number(ref: str | None) -> int | None:
    """`#189` -> 189; `—`, ``, `none` and anything else without a number -> None."""
    m = _PR_NUMBER.search(ref or "")
    return int(m.group(1)) if m else None


def resolve_repo(explicit: str | None = None) -> str:
    """`owner/name` from the flag, then the Actions environment, then gh itself."""
    if explicit:
        return explicit
    if os.environ.get("GITHUB_REPOSITORY"):
        return os.environ["GITHUB_REPOSITORY"]
    return _gh(["repo", "view", "--json", "nameWithOwner", "-q", ".nameWithOwner"])


def merged_lookup(repo: str):
    """A cached `int -> bool` PR-merged reader (one API call per distinct PR)."""
    cache: dict[int, bool] = {}

    def merged(n: int) -> bool:
        if n not in cache:
            out = _gh(["api", f"repos/{repo}/pulls/{n}", "--jq", ".merged"])
            if out not in {"true", "false"}:
                raise RuntimeError(f"gh api repos/{repo}/pulls/{n} answered {out!r}, not true/false")
            cache[n] = out == "true"
        return cache[n]

    return merged


def violations(active: list[tuple[str, Path]], merged) -> list[tuple[str, int]]:
    """The active changes whose `PR:` line names a merged PR, in tree order."""
    out: list[tuple[str, int]] = []
    for name, path in active:
        n = pr_number(_refs(path / "proposal.md").get("PR"))
        if n is not None and merged(n):
            out.append((name, n))
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Fail when an active OpenSpec change names a merged PR")
    ap.add_argument("--repo", default=None, help="owner/name (default: $GITHUB_REPOSITORY, else gh's own resolution)")
    ap.add_argument("--root", default=str(REPO_ROOT), help="repository root (default: this checkout)")
    a = ap.parse_args(argv)

    root = Path(a.root)
    active, archived = discover(root / "openspec" / "changes")
    with_pr = [
        (name, path)
        for name, path in active
        if pr_number(_refs(path / "proposal.md").get("PR")) is not None
    ]

    if not with_pr:
        print(
            f"[archive-check] OK: {len(active)} active change(s), none names a PR "
            f"({len(archived)} archived) — nothing to assert"
        )
        return 0

    try:
        repo = resolve_repo(a.repo)
        bad = violations(active, merged_lookup(repo))
    except RuntimeError as exc:
        print(f"[archive-check] FAIL cannot read PR state: {exc}", file=sys.stderr)
        return 2

    if not bad:
        print(
            f"[archive-check] OK: {len(active)} active change(s), {len(with_pr)} naming a PR, "
            f"none of them merged ({len(archived)} archived)"
        )
        return 0

    print(
        f"[archive-check] FAIL {len(bad)} active change(s) name a MERGED PR but still sit in "
        f"openspec/changes/ (rule 6f):",
        file=sys.stderr,
    )
    for name, n in bad:
        print(
            f"[archive-check]   {name} — PR #{n} is merged: run "
            f"`make openspec-archive NAME={name}` and `make openspec-index` in the PR that "
            f"completes the change",
            file=sys.stderr,
        )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
