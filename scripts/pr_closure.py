#!/usr/bin/env python3
"""Does this PR close the issue it implements? (issue #284, AGENTS.md rule 6e)

GitHub binds a closing keyword to the reference that immediately follows it — it does
not enumerate a list. So `Closes #271 and #276` closes #271 and leaves #276 open, and a
PR whose branch implements nothing can still carry a closing keyword for some other
issue. Both were measured in this repository:

  * PR #272's body said `Closes #271 and #276`; #271 closed on merge, #276 did not.
    The change was in `master`, the issue was open, and nothing in the pipeline noticed.
  * `refresh-bot.yml`'s refresh PR body ends with `Closes #1` — the *CI pipeline meta
    issue*, closed since 2026-09-28. Every refresh PR carries a closing keyword for an
    issue it does not implement.

A PR body is the only artifact whose whole purpose is "this merge closes that issue",
and the only one in the pipeline with no guard on its content. The marker-word
assertion in `tests/test_workflows.py` (`"closes #" in pr_run`) cannot see either shape.

This is the ONE implementation (rule 6d/6m) of the check. It reads the head branch and
the body from the webhook payload (`--event "$GITHUB_EVENT_PATH"`, so nothing is ever
interpolated into a `run:` block) or from files, derives the issue the branch
implements, and fails when:

  1. a closing keyword is followed by more than one reference — only the first binds;
  2. the issue the branch implements is not closed by its own keyword;
  3. a PR that implements no issue carries a closing keyword at all.

Run: python3 scripts/pr_closure.py --event "$GITHUB_EVENT_PATH"
     python3 scripts/pr_closure.py --branch ci/data-gap-266-x --body-file body.md
     python3 scripts/pr_closure.py --branch ci/pr-closure-284 --body "Closes #284"
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

# GitHub's closing keywords. `close|closes|closed|fix|fixes|fixed|resolve|resolves|resolved`,
# optionally followed by `:` — then the reference.
KEYWORD = r"(?:close[sd]?|fix(?:e[sd])?|resolve[sd]?)"
# A closing keyword and the references that follow it in the SAME clause. GitHub binds
# ONE reference per keyword, so `closes #1 and #2` links #1 and leaves #2 open — the
# separators a writer actually uses (and, `,`, `&`, `+`, `/`, plain whitespace) are
# captured on purpose, so that second reference is VISIBLE and refusable rather than
# silently dropped. A prose separator (`Closes #1 in #2`) correctly ends the clause.
REF_LIST = r"#\d+(?:(?:\s*(?:,|and|&|\+|/)\s*|\s+)#\d+)*"
CLOSING = re.compile(rf"\b{KEYWORD}\b\s*:?\s*({REF_LIST})", re.IGNORECASE)
REF = re.compile(r"#(\d+)")
# An inline code span: GitHub does not link a reference inside one.
INLINE_CODE = re.compile(r"`[^`\n]*`")

# Branches that encode an issue: the implementer's `ci/data-gap-<issue>-<slug>` and the
# agents' `ci/<topic>-<issue>`. A refresh branch (`ci/trending-refresh-<UTC>`) encodes a
# TIMESTAMP, not an issue, and implements none.
REFRESH_BRANCH = re.compile(r"^ci/trending-refresh-")
DATA_GAP_BRANCH = re.compile(r"^ci/data-gap-(\d+)-")
TRAILING_ISSUE = re.compile(r"-(\d+)$")


def visible_text(body: str) -> str:
    """The body as GitHub's reference parser reads it: CODE IS NOT A CLAIM.

    A closing keyword inside a fenced block or an inline code span is not linked — measured on
    this change's own PR: its body said `Closes #284` inside backticks and nothing else, and
    GitHub's `closingIssuesReferences` came back EMPTY. Parsing that as a binding is a false
    negative of exactly the kind this guard exists to prevent (green check, open issue), so the
    quoted examples a PR body uses to explain the rule must not count as closing claims.
    """
    lines, out, fence = body.splitlines(), [], None
    for line in lines:
        stripped = line.lstrip()
        marker = stripped[:3]
        if marker in ("```", "~~~"):
            fence = None if fence == marker else (marker if fence is None else fence)
            continue
        if fence is None:
            out.append(INLINE_CODE.sub(" ", line))
    return "\n".join(out)


class Failure(Exception):
    """A PR whose closing references do not do what the body says they do."""


def implemented_issue(branch: str | None) -> int | None:
    """The issue a branch implements, from its name — or None when it implements none.

    The convention is explicit first: `ci/data-gap-<issue>-<slug>` is the implementer's
    branch and its FIRST number is the issue (the slug may carry numbers of its own,
    e.g. `ci/data-gap-266-storage-offload-31-models`). Otherwise the LAST number is the
    issue (`ci/pr-closure-284`, `ci/worktree-base-271`). A refresh branch encodes a
    timestamp and implements no issue.
    """
    if not branch:
        return None
    if REFRESH_BRANCH.match(branch):
        return None
    if m := DATA_GAP_BRANCH.match(branch):
        return int(m.group(1))
    if m := TRAILING_ISSUE.search(branch):
        return int(m.group(1))
    return None


def closing_bindings(body: str) -> list[tuple[int, list[int]]]:
    """Every closing keyword in the body, as (the reference that binds, all references seen).

    `(271, [271, 276])` for `Closes #271 and #276`: 271 binds, 276 does not.
    """
    bindings: list[tuple[int, list[int]]] = []
    for match in CLOSING.finditer(body):
        refs = [int(n) for n in REF.findall(match.group(1))]
        if refs:
            bindings.append((refs[0], refs))
    return bindings


def check(body: str, branch: str | None, issue: int | None = None) -> list[str]:
    """Return the problems with this body. An empty list means it is correct."""
    problems: list[str] = []
    body = visible_text(body)          # code quotes an example; it does not make a claim
    binds = closing_bindings(body)
    closes = {first for first, _ in binds}
    wanted = issue if issue is not None else implemented_issue(branch)

    for first, refs in binds:
        extra = [n for n in refs[1:]]
        if extra:
            problems.append(
                f"`#{first}` binds only the FIRST reference: "
                f"{' '.join('#' + str(n) for n in extra)} would stay open "
                f"(write `Closes #{first}` and `Closes #{extra[0]}` on their own lines)"
            )

    if wanted is None:
        if closes:
            problems.append(
                f"this PR implements no issue (branch {branch!r}), so it must not close one — "
                f"it closes {' '.join('#' + str(n) for n in sorted(closes))}; "
                f"reference the tracking issue instead of closing it"
            )
    elif wanted not in closes:
        problems.append(
            f"the branch implements #{wanted}, but no closing keyword binds to it "
            f"(found: {', '.join('#' + str(n) for n in sorted(closes)) or 'none'}) — "
            f"on merge the issue stays open"
        )
    return problems


def read_event(path: str) -> tuple[str, str | None]:
    """(body, head ref) from a webhook payload — a PR event, or empty for anything else."""
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    pr = data.get("pull_request") or {}
    return pr.get("body") or "", (pr.get("head") or {}).get("ref")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Does this PR close the issue it implements?")
    src = ap.add_mutually_exclusive_group()
    src.add_argument("--event", help="webhook payload ($GITHUB_EVENT_PATH) — preferred in CI")
    src.add_argument("--body-file", help="the PR body on disk")
    src.add_argument("--body", help="the PR body as an argument")
    ap.add_argument("--branch", help="the head branch (or read it from --event)")
    ap.add_argument("--issue", type=int, help="the implemented issue, when the branch does not encode it")
    args = ap.parse_args(argv)

    branch = args.branch
    if args.event:
        body, head = read_event(args.event)
        branch = branch or head
        if not body and not branch:
            print("[pr-closure] no pull_request in this event — nothing to check.")
            return 0
    elif args.body_file:
        body = Path(args.body_file).read_text(encoding="utf-8")
    else:
        body = args.body or ""

    problems = check(body, branch, args.issue)
    wanted = args.issue if args.issue is not None else implemented_issue(branch)
    # Report what GITHUB would bind: the same code-stripped view the check uses, so a quoted
    # example is never printed as if the PR were closing that issue.
    binds = closing_bindings(visible_text(body))
    for first, refs in binds:
        print(f"[pr-closure] `#{first}` ← {' '.join('#' + str(n) for n in refs)}")
    if problems:
        print(f"[pr-closure] REFUSED: {branch or '(no branch)'} implements "
              f"{'#' + str(wanted) if wanted else 'no issue'} — "
              f"{len(problems)} problem(s):", file=sys.stderr)
        for p in problems:
            print(f"  - {p}", file=sys.stderr)
        return 1
    print(f"[pr-closure] OK: {branch or '(no branch)'} closes "
          f"{'#' + str(wanted) if wanted else 'no issue'} — "
          f"{len(binds)} closing keyword(s), each binding one reference.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
