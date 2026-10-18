#!/usr/bin/env python3
"""Fail LOUDLY when an environment variable a leg needs is missing or empty.

A leg that cannot authenticate must not run: issue #357's search legs had the key in their
environment and still failed, because nothing checked — the agent was left to discover it, narrate
the search, and write `export FIRECRAWL_API_KEY=<what to put here>` into an open log. Same
principle as `make model-caps` / `make hermes-smoke` (issue #209): a pre-flight that proves nothing
is worse than none, and a missing credential is a pipeline defect, never a data problem.

An empty value counts as missing: GitHub renders an unset secret as an empty string, so `set but
empty` is the shape a missing secret takes at run time — measured on the step's own listing, where
a populated one appears as `***` and an absent one as nothing after the colon.

The VALUE is never printed and never measured for length in the output: the check reports only the
NAME and whether it was set, so it can never become the leak it exists to prevent.

Usage:
    python3 scripts/require_env.py FIRECRAWL_API_KEY [ANOTHER_NAME ...]
    python3 scripts/require_env.py --why "the search legs cannot scrape without it" NAME
"""
from __future__ import annotations

import argparse
import os
import sys


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Fail loudly when a required environment variable is missing or empty.")
    parser.add_argument("names", nargs="+", help="the environment variables that must be set and non-empty")
    parser.add_argument("--why", default=None, help="why they are needed, quoted in the failure")
    parser.add_argument("--allow-unconfigured", action="store_true",
                        help="explicit opt-out for a local run (never set in CI)")
    args = parser.parse_args(argv)

    if args.allow_unconfigured:
        print("[require-env] NOT CONFIGURED (--allow-unconfigured): the check is skipped, and nothing "
              "about the credential was verified.")
        return 0

    missing = [n for n in args.names if not os.environ.get(n)]
    for name in args.names:
        print(f"[require-env] {name}: {'set (value never printed)' if os.environ.get(name) else 'MISSING or EMPTY'}")
    if not missing:
        return 0

    print(f"[require-env] FATAL: {', '.join(missing)} is missing or empty"
          + (f" — {args.why}" if args.why else ""), file=sys.stderr)
    print("[require-env] A leg that cannot authenticate must not run: set the value in the provider AND in "
          "the repository secret (`gh secret set <NAME> -R <owner>/<repo>`, the value on stdin, never in "
          "argv). See AGENTS.md §3d/§3e.", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
