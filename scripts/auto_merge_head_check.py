#!/usr/bin/env python3
"""#1184: refuse an auto-merge squash when the PR head moved after validation.

`qa-validate`'s `auto-merge` job decides to squash the head it saw in the
`pull_request` event. Between that event and the `gh pr merge` step a host push
(`git push --force-with-lease` from the rebase/review flow, rule 6s) can move the
branch. The old job passed the STALE event SHA to `--match-head-commit`, so
GitHub refused the squash with `Head branch was modified. Review and try the
merge again.` while the run reported the merge job as failed and left the PR
BLOCKED with green checks from a head that was never validated.

This seam is the read+decision, run in its OWN step immediately before the
squash so the window is as small as possible (rule 6d: the verdict lives here,
the workflow only follows it). It re-reads the PR head from GitHub and compares
it to the event head the checks were green on:

  - `head_moved=false`: the head is the one that was validated, merge proceeds.
  - `head_moved=true`: the head moved; the workflow SKIPS the squash loudly.
    The push that moved it already fired a fresh `pull_request` run, so the new
    head is re-validated by GitHub and THAT run lands the merge. No false red.

A failed gh read is exit 2 (never a silent "no move" that would merge a stale
head — rule 6n). No token value is ever printed; reads use the default token.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gh_json_fields  # noqa: E402  (the ONE gh --json field contract — rule 6d)

#: The single field this seam needs, built through the ONE gh field contract so
#: a field gh cannot answer refuses the BUILD rather than failing at run time.
HEAD_FIELD = gh_json_fields.request("pr view", "headRefOid")


def head_verdict(event_sha: str, current_sha: str) -> str:
    """The pure DECISION (rule 6d): `same`, `moved`, or `unreadable`.

    A missing SHA (an empty event head, or a PR whose head could not be read)
    is `unreadable` — never quietly folded into `same`, which would merge a
    head nobody validated. Comparison is case-insensitive (git SHAs are hex).
    """
    event = str(event_sha or "").strip()
    current = str(current_sha or "").strip()
    if not event or not current:
        return "unreadable"
    return "same" if event.lower() == current.lower() else "moved"


def read_head(repo: str, pr: str, gh=subprocess.run) -> str:
    """Read the PR's CURRENT headRefOid through gh (an external system stand-in
    is permitted for non-e2e tests; rule 6m). Returns '' on any failed read —
    the verdict turns that into `unreadable`, never a green merge."""
    # Ask for the JSON OBJECT and extract the field HERE, in Python. Using
    # `--jq .headRefOid` makes gh print a BARE string (no quotes); parsing that
    # with json.loads raises "Extra data: line 1 column 2", which turned a
    # valid, moved-or-same head into a READ FAILED and blocked the squash.
    # Requesting the object keeps ONE parse path that a stub can faithfully
    # reproduce (rule 6m).
    args = (["gh", "pr", "view", pr, "--repo", repo, "--json", HEAD_FIELD]
            if repo else
            ["gh", "pr", "view", pr, "--json", HEAD_FIELD])
    problems = gh_json_fields.check_argv(args)
    if problems:
        raise RuntimeError("gh --json asks for a field gh cannot answer: "
                           + "; ".join(problems))
    result = gh(args, capture_output=True, text=True)
    if getattr(result, "returncode", 1) != 0:
        raise RuntimeError(f"gh pr view failed: {str(getattr(result, 'stderr', ''))[:200]}")
    try:
        data = json.loads(getattr(result, "stdout", "") or "")
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"gh pr view answered non-JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise RuntimeError(f"gh pr view answered unexpected shape: {type(data).__name__}")
    return str(data.get(HEAD_FIELD, "") or "")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--pr", required=True, help="pull request number")
    ap.add_argument("--repo", default="", help="owner/name (default: gh resolution)")
    ap.add_argument("--event-head", default="",
                    help="the head SHA the pull_request event validated")
    args = ap.parse_args()

    try:
        current = read_head(args.repo, args.pr)
    except (RuntimeError, ValueError) as exc:
        print(f"[auto-merge-head-check] READ FAILED (exit 2, never a stale merge): {exc}",
              file=sys.stderr)
        return 2

    verdict = head_verdict(args.event_head, current)
    # Fail CLOSED: only a proved-`same` head may report false. `moved` and
    # `unreadable` both refuse the squash (the workflow skips on true).
    moved = verdict != "same"
    print(f"head_current={current}")
    print(f"head_moved={'true' if moved else 'false'}")
    if verdict == "unreadable":
        # Unreadable is NOT a clean pass: refuse the squash too, naming why.
        print("[auto-merge-head-check] REFUSE: head SHA unreadable "
              f"(event={args.event_head or '<empty>'}, current={current or '<empty>'}) "
              "— never squash a head that was not proved validated.")
    elif moved:
        print("[auto-merge-head-check] REFUSE: PR head moved between validation and squash "
              f"(validated={args.event_head}, current={current}). Skipping this merge; "
              "the push that moved the head fired a fresh pull_request run which "
              "re-validates the new head and lands the merge.")
    else:
        print(f"[auto-merge-head-check] OK: head {current[:12]} is the validated head; "
              "merge may proceed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
