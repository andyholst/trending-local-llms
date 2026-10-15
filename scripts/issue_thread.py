#!/usr/bin/env python3
"""Render an issue's WHOLE thread for the implementer (issue #210).

The comment thread IS part of the specification. An issue whose fifth comment
narrows the request ("only for the ROCm table"), or which a merged PR has already
satisfied, must not be implemented from its body alone — and the implementer read
only the body (`gh api … --jq '.title, "", .body'`), while the reviewer was told
to "review the WHOLE thread". This renders what both should see:

    <title>

    <body>

    ## Comments (oldest first)

    ### @<author> — <ISO8601Z>

    <comment body>
    …

    ## Your decision (REQUIRED)
    … the TRIAGE grammar the implementer answers with, written to `triage.md` …

Usage:  issue_thread.py --issue <n> [--repo <owner/name>] > issue.md
Exit:   0 rendered; 2 when the issue cannot be read (never a silent empty file —
        an implementer with no input must fail loudly, not guess).

Env: REPO (or --repo), GH_TOKEN for the read.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys

INSTRUCTION = """\
## Your decision (REQUIRED)

The thread ABOVE is part of the specification: read it before you decide. Then
write your verdict to `triage.md` at the repo root, in exactly this form:

    TRIAGE: implement | refine | close

- `implement` — the thread is consistent with the body and the issue is
  implementable as written. Then implement it as usual (no extra lines needed).
- `refine` — it is NOT implementable as written (a comment narrows or changes it,
  acceptance criteria are missing, two readings are possible). Then add:

      REFINED: <the restatement that WOULD be implementable, with acceptance
      criteria, the scope boundary and what is out of scope>

  You do NOT implement it: no code change, no PR.
- `close` — it is obsolete, a duplicate, or already fixed. Then add BOTH:

      EVIDENCE: <the proof: a file:line, a command and its output, or a measured
      behaviour — never an opinion>
      REASON: <why that evidence means the issue is done/superseded>

  You do NOT implement it: no code change, no PR. A `close` with no EVIDENCE
  block is REFUSED and this run fails — closing without proof is how a real gap
  gets buried.

Rules that do not change: implement ONLY when the verdict is `implement`; the
AGENTS.md gates still apply; write `findings.md` for whatever you noticed
(rule 6g); never push, never merge.
"""


def _gh(*args: str) -> str:
    out = subprocess.run(["gh", *args], text=True, capture_output=True)
    if out.returncode != 0:
        raise SystemExit(f"[issue-thread] gh {' '.join(args)} failed: {out.stderr.strip()}")
    return out.stdout


def render(issue: dict, comments: list[dict]) -> str:
    """The thread as markdown: body first, then every comment oldest-first."""
    parts = [f"# {issue.get('title', '').strip()}", "", (issue.get("body") or "").strip(), ""]
    if comments:
        parts += ["## Comments (oldest first)", ""]
        for c in comments:
            author = (c.get("user") or {}).get("login", "someone")
            at = c.get("created_at", "")
            body = (c.get("body") or "").strip()
            parts += [f"### @{author} — {at}", "", body, ""]
    else:
        parts += ["## Comments", "", "(none — the body is the whole thread)", ""]
    parts.append(INSTRUCTION)
    return "\n".join(parts)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Render an issue's thread for the implementer (#210)")
    ap.add_argument("--repo", default=os.environ.get("REPO", ""))
    ap.add_argument("--issue", default=os.environ.get("ISSUE", ""))
    args = ap.parse_args(argv)
    if not args.issue:
        raise SystemExit("[issue-thread] no issue number (--issue or ISSUE=...)")

    # `repos/{owner}/{repo}/…` is what the workflow uses (`REPO=owner/name`); the
    # bare placeholder form is what `gh api` fills in when a human runs it by hand.
    base = f"repos/{args.repo}" if args.repo else "repos/{owner}/{repo}"
    issue = json.loads(_gh("api", f"{base}/issues/{args.issue}"))
    # --paginate + `.[]` yields one JSON object per line, so a multi-page thread
    # parses correctly instead of failing on concatenated arrays.
    raw = _gh("api", f"{base}/issues/{args.issue}/comments", "--paginate", "--jq", ".[]")
    comments = [json.loads(l) for l in raw.splitlines() if l.strip()]
    sys.stdout.write(render(issue, comments))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
