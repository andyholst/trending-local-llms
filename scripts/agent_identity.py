#!/usr/bin/env python3
"""ONE definition of the repository's agent identity (issue #325).

The identity existed as five hand-kept copies of one fact: the same two `git config` lines in
four workflows (`fix-bot.yml`, `issue-bot.yml` twice, `refresh-bot.yml`) plus the authorship
guard's `ALLOWED_EMAILS`. Issue #323 had to change the same lines in four places, and nothing
derived one from the other — so a new committing workflow copies whatever it finds, and a
change to the address reddens the whole fleet at once.

This module is the one place: the workflows consume it through `make git-identity`, and
`scripts/check_commit_authorship.py` reads the allowed sets from here.

Usage:
  python3 scripts/agent_identity.py --git-config      # set the identity in the current repo
  python3 scripts/agent_identity.py --json            # {name, email, allowed_names, allowed_emails}
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys

#: The identity every committing job uses and the authorship guard accepts (rule: the only
#: identities on this repo are Andy Holst and Asimov Agent).
AGENT_NAME = "Asimov Agent"
AGENT_EMAIL = "support@docondee.com"

#: What the authorship guard accepts as the OWNER. Matching is case-insensitive and the name
#: is compared with its punctuation squashed (see `check_commit_authorship.py`).
ALLOWED_NAMES = (
    "andy",
    "andy holst",
    "andyholst",
    "asimov",
    "asimov agent",
    "asimov-agent",
)

ALLOWED_EMAILS = (
    "andy.holst@protonmail.com",
    "andyholst@users.noreply.github.com",
    "asimov@example.com",
    "asimov@omarchy.local",
    "asimov-agent@users.noreply.github.com",
    "support@docondee.com",
    # The repository's own automation: allowed by NAME too, but listed so the pair is complete.
    "41898282+github-actions[bot]@users.noreply.github.com",
    "noreply@github.com",
)


def git_config() -> int:
    """Set the repo-local committer identity. Idempotent, and loud on failure."""
    for key, value in (("user.name", AGENT_NAME), ("user.email", AGENT_EMAIL)):
        proc = subprocess.run(["git", "config", key, value], capture_output=True, text=True)
        if proc.returncode != 0:
            print(f"[agent-identity] FAIL: git config {key} exited {proc.returncode}: "
                  f"{proc.stderr.strip()[:200]}", file=sys.stderr)
            return 1
    print(f"[agent-identity] {AGENT_NAME} <{AGENT_EMAIL}>")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="The repository's agent identity (issue #325)")
    ap.add_argument("--git-config", action="store_true",
                    help="set user.name/user.email in the current repository")
    ap.add_argument("--json", action="store_true", help="print the identity and the allowed sets")
    args = ap.parse_args()
    if args.json:
        print(json.dumps({"name": AGENT_NAME, "email": AGENT_EMAIL,
                          "allowed_names": list(ALLOWED_NAMES),
                          "allowed_emails": list(ALLOWED_EMAILS)}, indent=2))
        return 0
    if args.git_config:
        return git_config()
    ap.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
