#!/usr/bin/env python3
"""The implementation PR body is COMPOSED by a target, never spelled in a workflow heredoc
(issue #287).

`.github/workflows/issue-bot.yml` built the body with `cat > pr-body.md <<'BODY'` and appended
the closing keyword with `printf '\\ncloses #%s\\n'`. That body is the artifact that DECIDES
whether the issue closes on merge (AGENTS.md rule 6e), and it was the only PR artifact in the
pipeline with no target behind it:

  * no test could RUN it — the text lived inside a YAML block, so only a substring assertion
    could see it (the same weakness #289 fixed for the closing claim's check);
  * `make pr-closure` could only read what the shell had already written;
  * the wording said "the filed data-gap issue from the post-refresh analysis" even when the
    implementer was working a `tech-debt` issue, because the text could not branch on anything.

The ONE implementation (rules 6d/6m): `make pr-body ISSUE=<n> [BRANCH=<branch>]` prints the
body, and the workflow redirects it into `pr-body.md` and hands that file to
`gh pr create --body-file`. The closing claim comes from `closing_line()` in this module and is
checked by `scripts/pr_closure.py` in the tests, so the composer and the parser that guards the
merged PR cannot drift. When the branch itself encodes an issue (`ci/data-gap-<n>-…`) and it is
not the issue the body closes, the composer REFUSES (exit 2) instead of writing a body GitHub
would read as closing the wrong issue.

Usage:
    make pr-body ISSUE=287 BRANCH=ci/data-gap-287-slug > pr-body.md
    python3 scripts/pr_body.py --issue 287 --branch ci/data-gap-287-slug
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import pr_closure  # noqa: E402  (ONE derivation of "which issue does this branch implement")


class Mismatch(Exception):
    """The branch implements one issue and the body would close another."""


def closing_line(issue: int) -> str:
    """The ONE closing keyword line, bound to exactly one reference (rule 6e).

    Emitted here and nowhere else: `pr_closure.closing_bindings()` reads it back, so a chained
    reference (`Closes #1 and #2`, which GitHub binds only to #1) cannot be introduced silently.
    """
    return f"Closes #{issue}"


#: The Conventional-Commit type each label earns. A `tech-debt` issue is a fix; a
#: `data-gap-analysis` issue is a feature (it adds data/dimensions). Anything else is REFUSED
#: rather than guessed, because the title is the first line a reviewer reads (issue #541).
KIND_TYPES = {"tech-debt": "fix(tech-debt)", "data-gap": "feat(data-gap)"}


class UnknownKind(Exception):
    """The issue's label is not one this composer knows how to title."""


def title(issue: int, kind: str) -> str:
    """The implementation PR's TITLE, composed from the issue and the kind of work it is.

    The workflow used to spell `feat(data-gap): implement the #<n> gap analysis item` inline, so
    every PR — including the `tech-debt` ones the same sweep takes — was titled a data-gap change
    (issue #541). Composed here, it can branch on the label and a test can run it.
    """
    if issue < 1:
        raise UnknownKind(f"a PR title cannot name issue {issue}: the number must be positive")
    prefix = KIND_TYPES.get(kind)
    if prefix is None:
        raise UnknownKind(f"unknown issue kind {kind!r}; known: {sorted(KIND_TYPES)}")
    tail = ("from the post-refresh gap analysis" if kind == "data-gap"
            else "from the tech-debt the analysis filed")
    return f"{prefix}: implement #{issue} {tail}"


def render(issue: int, branch: str | None = None) -> str:
    """The whole implementation PR body for `issue`, opened from `branch`.

    Raises `Mismatch` when `branch` names a different issue: a body that closes the wrong issue
    is exactly the failure `make pr-closure` exists to refuse, and it must never leave this
    composer in the first place.
    """
    if issue < 1:
        raise Mismatch(f"a PR body cannot close issue {issue}: the number must be positive")
    if branch:
        implemented = pr_closure.implemented_issue(branch)
        if implemented is not None and implemented != issue:
            raise Mismatch(
                f"branch {branch!r} implements #{implemented}, but the body would close #{issue} "
                f"— on merge the wrong issue is the one that moves"
            )
    opened_from = f" (`{branch}`)" if branch else ""
    return f"""\
Implements #{issue}{opened_from}.

Spec-tracked: the change lives in `openspec/changes/` (proposal +
capability spec in Given/When/Then + a tasks checklist with every box
ticked), is listed in the root `OPENSPEC.md` index, and passes
`make openspec-check`.

Additive only: no existing key is removed or narrowed and no value is
shrunk; a new key is OPTIONAL. Any value that could not be traced to a
real source is left unset and called out in this body.

Analysis ships issues: whatever the implementation noticed but did not
fix is filed as its own `tech-debt` issue (linked to this PR) instead
of being folded into this change.

Auto-merged (squash, branch deleted) by qa-validate once `validate` and
`live-smoke` are green on the head commit.

{closing_line(issue)}
"""


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Compose the implementation PR body (issue #287).")
    ap.add_argument("--issue", type=int, required=True, help="the issue this PR implements")
    ap.add_argument("--branch", help="the head branch (a ci/data-gap-<n>-… branch must match)")
    ap.add_argument("--title", action="store_true",
                    help="print the PR TITLE for --kind instead of the body (issue #541)")
    ap.add_argument("--kind", default="data-gap", choices=sorted(KIND_TYPES),
                    help="the kind of issue this PR implements (default: data-gap)")
    args = ap.parse_args(argv)
    if args.title:
        try:
            print(title(args.issue, args.kind))
        except UnknownKind as exc:
            print(f"[pr-body] REFUSED: {exc}", file=sys.stderr)
            return 2
        return 0
    try:
        body = render(args.issue, args.branch)
    except Mismatch as exc:
        print(f"[pr-body] REFUSED: {exc}", file=sys.stderr)
        return 2
    sys.stdout.write(body)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
