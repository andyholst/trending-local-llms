#!/usr/bin/env python3
"""Rule 1's mechanical guard (issue #959): the base branch must carry protection.

AGENTS.md Rule 1 forbids pushing `master` directly, but until #959 nothing
enforced it: `gh api …/branches/master/protection` answered 404 and two direct
pushes landed on 2026-11-14 (`e571aa3`, `4c7c555`, committer `Mr. Asimov`, not
the `GitHub <noreply@github.com>` squash identity). This guard is the DETECTION
half: it reads the base branch's protection — live through `gh api` (the
external system rule 6m allows the real client to call), or from a RECORDED
payload via `--from-file` (the fixture seam tests use) — and refuses any shape
that is not the one admitting ONLY qa-validate's `auto-merge` squash:

  required_status_checks.strict is true,
  required_status_checks.contexts name each auto-merge gate check
  (`validate`, `live-smoke` — a context may be bare or `workflow / job`),
  enforce_admins is true.

Exit contract: 0 = the shape is in place; 1 = protection absent or relaxed,
naming every gap; 2 = the read itself failed (gh missing, gh error other than
404, malformed payload). A guard that cannot read is NEVER a silent clean.
It is read-only: it never PUTs or edits a setting — applying the protection is
an owner-approved repository-settings act (issue #959).
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys

#: The checks `auto-merge` already gates on (AGENTS.md rule 6e): protection must
#: require exactly at least these, so the merge path protection admits IS the
#: pipeline's merge path.
REQUIRED_CHECKS = ("validate", "live-smoke")


def context_tokens(contexts: list) -> set:
    """Normalized context names: a GitHub Actions required context may be bare
    (`validate`) or workflow-prefixed (`qa-validate / validate`)."""
    return {str(c).split("/")[-1].strip() for c in contexts}


def verdict(protection) -> list:
    """The problems with a protection payload (None == GitHub answered 404)."""
    if protection is None:
        return ["no branch protection at all (GitHub answered 404) — a direct push to the base branch would LAND"]
    problems = []
    required = protection.get("required_status_checks")
    if required is None:
        problems.append("required_status_checks is null — every gate check is optional")
    else:
        if required.get("strict") is not True:
            problems.append("required_status_checks.strict is not true — a PR may merge behind its base")
        tokens = context_tokens(required.get("contexts") or [])
        for check in REQUIRED_CHECKS:
            if check not in tokens:
                problems.append(
                    f"required context '{check}' is missing (protection names: {sorted(tokens) or 'nothing'})"
                )
    ea = protection.get("enforce_admins")
    ea_ok = ea is True or (isinstance(ea, dict) and ea.get("enabled") is True)
    if not ea_ok:
        problems.append("enforce_admins is not true — an admin (or an owner token) could still push directly")
    return problems


def read_recorded(path: str):
    """A recorded protection payload (tests' fixture seam): the real client
    parses the real GitHub body, including the 404 shape `gh` answers for an
    unprotected branch."""
    with open(path, encoding="utf-8") as fh:
        payload = json.load(fh)
    if isinstance(payload, dict) and str(payload.get("status", "")) == "404":
        return None
    return payload


def read_live(repo: str, branch: str):
    """Live read through `gh api` (external system, rule 6m). 404 == unprotected;
    any other gh failure is loud (exit 2 via the caller)."""
    proc = subprocess.run(
        ["gh", "api", f"repos/{repo}/branches/{branch}/protection"],
        capture_output=True,
        text=True,
    )
    if proc.returncode == 0:
        return json.loads(proc.stdout)
    if "404" in proc.stderr:
        return None
    raise RuntimeError(f"gh api could not read the protection: {proc.stderr.strip()[:400]}")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    ap.add_argument("--repo", default="", help="owner/name to read live through gh")
    ap.add_argument("--branch", default="master", help="the base branch (default master)")
    ap.add_argument("--from-file", default="", help="check a RECORDED protection payload instead")
    args = ap.parse_args(argv)

    if not args.repo and not args.from_file:
        print("usage: check_branch_protection.py --repo <owner/name> | --from-file <recorded.json>", file=sys.stderr)
        return 2

    try:
        protection = read_recorded(args.from_file) if args.from_file else read_live(args.repo, args.branch)
    except (OSError, ValueError, RuntimeError) as exc:
        print(f"branch-protection guard: UNREADABLE read — {exc}", file=sys.stderr)
        return 2

    problems = verdict(protection)
    if problems:
        print(f"branch-protection guard: FAIL — {args.branch} is not guarded the way auto-merge needs:")
        for p in problems:
            print(f"  - {p}")
        print("remedy: restore the recorded protection shape (see openspec proposal master-push-guard-959); "
              "applying it is an owner-approved repository-settings act.")
        return 1

    required = (protection or {}).get("required_status_checks") or {}
    print(
        f"branch-protection guard: OK — {args.branch} is protected "
        f"(strict=True, contexts={sorted(context_tokens(required.get('contexts') or []))}, "
        f"enforce_admins=True): a direct push is refused and only the auto-merge squash lands."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
