#!/usr/bin/env python3
"""An ACTIVE OpenSpec change must not sit completed-and-forgotten (issues #183/#513).

Rule 6f gives every change a life: `make openspec-new` creates it, the capability
spec and `tasks.md` describe it, `OPENSPEC.md` lists it — and then **nothing said
when it ends**. Measured on `master` when the first half of this check was
written: 115 changes "active", 0 archived, `openspec/changes/archive/` empty,
and six of those active changes named a `PR:` that GitHub reports as merged
(#173, #180, #189, #374, #379, #384). The index's own count was therefore not a
measure of in-flight work: a merged change and an unfinished one looked
identical.

That first half could only assert the lifecycle WHERE A `PR:` LINE EXISTS. A
change written without one — every change created before #183, plus every change
whose author did not know its PR number at authoring time — was merged and
forgotten while the guard reported OK. Measuring that gap (issue #513): 110 of
111 active changes carried no `PR:` line yet referenced a CLOSED issue (a merged
PR had implemented them); the index's active count overstated in-flight work.

So the check has TWO prongs, both reading GitHub state through `gh` (the same
tool the pipelines use for every GitHub fact):

  * an ACTIVE change whose `PR:` line names a MERGED PR is a failure (exit 1),
    naming the change, the PR and the archive command to run;
  * an ACTIVE change with NO `PR:` line whose `Issue:` names a CLOSED issue is a
    failure (exit 1), naming the change, the issue and the same remedy — the
    work is done (its issue closed when the completing PR merged) but the PR was
    never recorded, so the change never reached archive/ alone.
  * an active change with NO `PR:` and NO issue is skipped — there is nothing to
    assert; an ARCHIVED change is skipped — a merged PR is its expected state.

The second prong is what makes the guard NON-vacuous: before it, a change with
no `PR:` line was invisible. A GitHub read that fails is LOUD (exit 2): a check
that could not see the state must never report it as clean (rule 6d's "a scan
that proves nothing").

An issue is "closed" when `gh api repos/<o>/<r>/issues/<n>`'s `.state` says so
— the issue's end when the change's PR merged (`closes #n`). The remedy is the
same archive move the merged-PR prong teaches, never inventing the missing PR
number (rule 2).

The repository comes from `--repo`, else `GITHUB_REPOSITORY`, else `gh`'s own
resolution. Usage:
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
    except FileNotFoundError as exc:  # no gh on PATH: we cannot see any state
        raise RuntimeError(
            "`gh` is not installed — the PR/issue state of a change cannot be checked "
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


def issue_closed_lookup(repo: str):
    """A cached `int -> bool` "is this issue CLOSED" reader (one API call each)."""
    cache: dict[int, bool] = {}

    def closed(n: int) -> bool:
        if n not in cache:
            out = _gh(["api", f"repos/{repo}/issues/{n}", "--jq", ".state"])
            if out not in {"open", "closed"}:
                raise RuntimeError(f"gh api repos/{repo}/issues/{n} answered {out!r}, not open/closed")
            cache[n] = out == "closed"
        return cache[n]

    return closed


def violations(active: list[tuple[str, Path]], merged, issue_closed) -> tuple[list[tuple[str, int]], list[tuple[str, int]]]:
    """(merged-PR, closed-issue) violations among the active changes, in tree order.

    A change that names a PR is judged on the PR only — it HAS a recorded
    reference, so the primary prong owns it. A change with no PR line falls to
    the Issue prong: its issue being closed means the work ended without the PR
    ever being recorded, which is exactly the state the guard exists to surface.
    """
    bad_merged: list[tuple[str, int]] = []
    bad_closed: list[tuple[str, int]] = []
    for name, path in active:
        refs = _refs(path / "proposal.md")
        n_pr = pr_number(refs.get("PR"))
        if n_pr is not None:
            if merged(n_pr):
                bad_merged.append((name, n_pr))
            continue
        n_issue = pr_number(refs.get("Issue"))
        if n_issue is not None and issue_closed(n_issue):
            bad_closed.append((name, n_issue))
    return bad_merged, bad_closed


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description="Fail when an active OpenSpec change names a merged PR, or "
                    "references a closed issue without a recorded PR"
    )
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
    with_issue = [
        (name, path)
        for name, path in active
        if pr_number(_refs(path / "proposal.md").get("PR")) is None
        and pr_number(_refs(path / "proposal.md").get("Issue")) is not None
    ]

    if not with_pr and not with_issue:
        print(
            f"[archive-check] OK: {len(active)} active change(s), none names a PR and none "
            f"references an issue ({len(archived)} archived) — nothing to assert"
        )
        return 0

    try:
        repo = resolve_repo(a.repo)
        bad_merged, bad_closed = violations(active, merged_lookup(repo), issue_closed_lookup(repo))
    except RuntimeError as exc:
        print(f"[archive-check] FAIL cannot read PR/issue state: {exc}", file=sys.stderr)
        return 2

    if not bad_merged and not bad_closed:
        print(
            f"[archive-check] OK: {len(active)} active change(s), {len(with_pr)} naming a PR "
            f"(none merged), {len(with_issue)} naming only an issue (none closed), "
            f"({len(archived)} archived)"
        )
        return 0

    print(
        f"[archive-check] FAIL {len(bad_merged) + len(bad_closed)} active change(s) sit in "
        f"openspec/changes/ whose work is already done (rules 6f/#513):",
        file=sys.stderr,
    )
    for name, n in bad_merged:
        print(
            f"[archive-check]   {name} — PR #{n} is merged: run "
            f"`make openspec-archive NAME={name}` and `make openspec-index` in the PR that "
            f"completes the change",
            file=sys.stderr,
        )
    for name, n in bad_closed:
        print(
            f"[archive-check]   {name} — issue #{n} is closed but no `PR:` line was ever "
            f"recorded (its completing PR merged without one): run "
            f"`make openspec-archive NAME={name}` and `make openspec-index`",
            file=sys.stderr,
        )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
