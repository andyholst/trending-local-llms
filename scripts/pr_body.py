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
import json
import re
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


#: The MESSAGE PATTERN (issue #771): every implementation PR body carries these five
#: `##`-headed sections in this exact order, each with at least one content line, then ends
#: with the single `Closes #<n>` claim (rule 6e). `section_problems()` is the ONE parser, and
#: `make pr-message-check` (the CI gate) and every test read the composer through it.
MESSAGE_SECTIONS = ("Why", "What", "How", "Benefits", "Technical Solution")

#: An issue AUTHOR that declares its body follows the MESSAGE PATTERN carries this marker.
#: The `issues` CI leg validates only DECLARED conformance: a data-gap/tech-debt issue has
#: its own structured schema (## Goal / ## Ranked gaps / the attribution marker) and must
#: not be forced through the five-section shape, while an issue that opts in is REFUSED the
#: moment it skips, empties or misorders a `##` section (issue #771).
ISSUE_PATTERN_MARKER = "<!-- issue-message-pattern -->"


def section_problems(text: str) -> list[str]:
    """Every message-pattern violation in `text`: a missing / repeated / out-of-order /
    empty section. An empty list means the text follows the message pattern."""

    problems: list[str] = []
    lines = text.splitlines()
    position: dict[str, int] = {}
    order: list[str] = []
    # A section ends at the NEXT markdown heading (`# … `), never at a line that merely
    # starts with `#` followed by a digit or word without a space — e.g. a body that reads
    # "#771 is a real gap…" is CONTENT, not a new heading.
    heading = re.compile(r"^#{1,6}[ \t]")
    for i, line in enumerate(lines):
        stripped = line.strip()
        for section in MESSAGE_SECTIONS:
            if stripped == f"## {section}":
                if section in position:
                    problems.append(f"the '## {section}' section appears more than once")
                else:
                    position[section] = i
                    order.append(section)
                break

    missing = [s for s in MESSAGE_SECTIONS if s not in position]
    if missing:
        problems.append("missing required section(s): "
                        + ", ".join(f"## {s}" for s in missing))

    present = [s for s in MESSAGE_SECTIONS if s in position]
    if order != present:
        problems.append("sections are out of order; expected "
                        + " ".join(f"## {s}" for s in present) + " but saw "
                        + " ".join(f"## {s}" for s in order))

    for section in MESSAGE_SECTIONS:
        if section not in position:
            continue
        start = position[section]
        end = next((j for j in range(start + 1, len(lines))
                    if heading.match(lines[j].strip())), len(lines))
        if not any(lines[k].strip() for k in range(start + 1, end)):
            problems.append(f"the '## {section}' section is empty (no content line)")
    return problems


def pr_message_problems(body: str, branch: str | None = None,
                        issue: int | None = None) -> list[str]:
    """Every message-pattern + closure problem for an implementation PR.

    The message pattern applies to the PRs that IMPLEMENT an issue — a refresh or architecture
    body is not a five-section artifact and must not be blocked by this gate. So the section
    check runs only when the branch (or an explicit `--issue`) names an issue the PR
    implements; `pr_closure.check` always runs, exactly as `make pr-closure` runs it today.
    """
    implemented = pr_closure.implemented_issue(branch)
    sections = section_problems(body) if (issue is not None or implemented is not None) else []
    return sections + pr_closure.check(body, branch, issue)


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
    # The implementation body carries the MESSAGE PATTERN (issue #771): the five `##`
    # sections in order, then the single closing claim. `section_problems()` /
    # `pr_message_problems()` parse this exact shape, and `make pr-message-check` in
    # `pr-closure.yml` gates it, so the composer and the CI gate cannot drift.
    return (
        f"Implements #{issue}{opened_from}.\n\n"
        "## Why\n\n"
        f"#{issue} is a real gap the analysis filed and no change has implemented yet; "
        "this PR is the tracked change that delivers it.\n\n"
        "## What\n\n"
        f"#{issue} is implemented additively: the OpenSpec-tracked implementation\n"
        "(proposal + capability spec in Given/When/Then + a tasks checklist with\n"
        "every box ticked), the code, and the updated tests in the SAME commit\n"
        "(rule 6b). No existing key is removed or narrowed and no value is shrunk; a\n"
        "new key is OPTIONAL. Any value that could not be traced to a real source is\n"
        "left unset and called out below.\n\n"
        "## How\n\n"
        "The change follows the repo's mandated path (rule 6f): it was created in\n"
        "`openspec/changes/` before any code, is listed in the root `OPENSPEC.md`\n"
        "index, and passes `make openspec-check`. Tests are updated in the same\n"
        "change so `make test` stays green; `ARCHITECTURE.md` and `AGENTS.md` are kept\n"
        "true when the change moves a target or a rule.\n\n"
        "## Benefits\n\n"
        f"A reviewer reads why/what/how/benefits/technical-solution in one place, the\n"
        f"issue closes on merge (`{closing_line(issue)}`), and the squash commit message\n"
        f"carries the same structure. The change is additive only and spec-tracked, so\n"
        f"nothing existing is lost. Whatever the implementation noticed but did not fix\n"
        f"is filed as its own `tech-debt` issue (linked to this PR) instead of being\n"
        f"folded into this change (analysis ships issues, rule 6g).\n\n"
        "## Technical Solution\n\n"
        "Files this change touches: `openspec/changes/<this-change>/"
        "{proposal,specs,tasks}.md`, the implementation module(s), and the tests\n"
        "updated in the same commit; the root `OPENSPEC.md` index and `ARCHITECTURE.md`\n"
        "are regenerated when the change moved them. Auto-merged (squash, branch\n"
        "deleted) by qa-validate once `validate` and `live-smoke` are green on the head\n"
        "commit. This body and the squash message are themselves validated by\n"
        "`make pr-message-check` in `pr-closure.yml` (issue #771).\n\n"
        f"{closing_line(issue)}\n"
    )


# The refresh body's contract sentence, kept HERE so the workflow redirects a target instead of
# building the text inline (issue #542). The run's WINDOW block is prepended by `refresh_body()`.
REFRESH_CONTRACT = (
    "Hermes CLI refresh (deepseek-v4-flash-0731 via Nous). Three separate per-backend searches "
    "(NVIDIA, Metal, CPU), each writing its own timestamped raw snapshot. No existing model "
    "removed. Auto-merged when qa-validate is green; red stays open for review. Refs #1"
)


class Empty(Exception):
    """A body that must not be published empty (or without its window block)."""


class RefusedClosing(Exception):
    """An architecture PR body must never carry a closing claim (rule 6e)."""


def refresh_body(window: str) -> str:
    """The refresh PR body: the run's WINDOW block first, then the contract a reviewer relies on.

    A body without the window is the defect #199 fixed, so an empty window is REFUSED here rather
    than published with a blank first section (issue #542).
    """
    if not window.strip():
        raise Empty("refusing to compose a refresh body with no window block (issue #199)")
    return window.rstrip("\n") + "\n\n" + REFRESH_CONTRACT + "\n"


def architecture_body(run_url: str) -> str:
    """The architecture PR body — and it must carry NO closing keyword (rule 6e).

    This PR implements no issue: it republishes a generated description, so `pr_closure` refuses a
    closing claim on it. The composer proves the absence instead of trusting the workflow.
    """
    body = (
        "A generated description was stale, so `make architecture-refresh` and/or "
        "`make openspec-index` rewrote it: `ARCHITECTURE.md` §10 when a pipeline's triggers, jobs "
        "or `make` targets changed, a script appeared, or the `README.md` sections changed — and "
        "`OPENSPEC.md` when a change landed on disk without its row (issue #526: two concurrent "
        "changes merge into ONE index, so master lists one change fewer than the tree holds).\n\n"
        "The block is derived from the tree (`scripts/architecture_bot.py`), so nothing here is "
        "invented. `make architecture-check` is green on this commit — the whole document, not only "
        "the regenerated block.\n\n"
        f"Run: {run_url}\n"
        "Tracking issue: #479 (referenced, never closed: this PR implements no issue)\n"
    )
    if any("closing keyword" in problem for problem in pr_closure.check(body, "")):
        raise RefusedClosing(body)
    return body


def _commit_issue(text: str) -> int | None:
    """The issue a squash COMMIT message implements, from the first `#<n>` in it.

    The repo's squash title names the issue (`fix(tech-debt): implement #518 …`) and the
    body ends with `Closes #<n>`, so the first reference IS the implemented issue — read
    from the artifact itself, never from a branch name, because a push-to-master squash
    lands on `refs/heads/master` which encodes nothing. The commit-message gate needs it to
    run the closure half of the check on the right issue.
    """
    m = re.search(r"#(\d+)", text)
    return int(m.group(1)) if m else None


def _read_issue_event(path: str) -> tuple[str, int | None]:
    """(issue body, issue number) from an `issues` webhook payload ($GITHUB_EVENT_PATH)."""
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    issue = data.get("issue") or {}
    return issue.get("body") or "", issue.get("number")


def _problems_for(artifact: str, text: str, branch: str | None = None,
                  issue: int | None = None) -> list[str]:
    """The MESSAGE-PATTERN + closure problems for one artifact (issue #771).

    artifact "issue" is the five `##` sections ONLY — an issue links its origin but
    closes nothing (rule 6e). artifact "pr" and "commit" are sections + closure
    (`pr_message_problems`): a PR closes the issue it implements, and the squash commit a
    merge lands closes it too. The closing-keyword semantics are always `pr_closure`'s.
    """
    if artifact == "issue":
        # An issue is validated only when it DECLARES conformance (the marker). A structured
        # data-gap / tech-debt issue carries its own schema (## Goal / ## Ranked gaps / the
        # attribution marker) and must not be forced through the five-section shape; an issue
        # that opts in is REFUSED when it skips, empties or misorders a `##` section.
        if ISSUE_PATTERN_MARKER not in text:
            return []
        return section_problems(text)
    return pr_message_problems(text, branch, issue)


def _check_message(args) -> int:
    """CLI seal for the message-pattern gates (issue #771): validate a PR body, an issue
    body, or a commit message against the message pattern (+ closure for PR/commit). When
    a webhook `--event` / `--issue-event` is passed, the artifact is read from the payload
    exactly as `pr-closure` does, so the gate reads the artifact on screen now (#290)."""
    if args.check_body_file or args.check_event:
        artifact, label = "pr", "pr-message-check"
    elif args.check_issue_file or (hasattr(args, "issue_event") and args.issue_event):
        artifact, label = "issue", "issue-message-check"
    elif args.check_commit_file:
        artifact, label = "commit", "commit-message-check"
    else:
        print("Usage: pr_body.py --check-body-file <f> [--branch <b>] | --event <payload> "
              "| --check-issue-file <f> | --issue-event <payload> | --check-commit-file <f> "
              "[--issue <n>]", file=sys.stderr)
        return 2

    text = branch = issue = None
    if artifact == "pr":
        if args.check_event:
            text, head = pr_closure.read_event(args.check_event)
            branch = args.branch or head
            if not text:
                print(f"[{label}] no pull_request body in this event — nothing to check.",
                      file=sys.stderr)
                return 0
        elif args.check_body_file:
            text = Path(args.check_body_file).read_text(encoding="utf-8")
            branch = args.branch
        issue = args.issue
    elif artifact == "issue":
        if args.issue_event:
            text, n = _read_issue_event(args.issue_event)
            issue = args.issue if args.issue is not None else n
            if not text:
                print(f"[{label}] no issue body in this event — nothing to check.",
                      file=sys.stderr)
                return 0
        elif args.check_issue_file:
            text = Path(args.check_issue_file).read_text(encoding="utf-8")
            issue = args.issue
    elif artifact == "commit":
        text = Path(args.check_commit_file).read_text(encoding="utf-8")
        branch = args.branch
        # A squash commit lands on refs/heads/master which encodes no issue — read the
        # implemented issue from the message itself (its title names the `#<n>`).
        issue = args.issue if args.issue is not None else _commit_issue(text)

    problems = _problems_for(artifact, text or "", branch, issue)
    if problems:
        print(f"[{label}] REFUSED: {branch or '(no branch)'} — {len(problems)} problem(s):",
              file=sys.stderr)
        for p in problems:
            print(f"  - {p}", file=sys.stderr)
        return 1
    print(f"[{label}] OK: follows the message pattern "
          f"({'#' + str(issue) if issue else '(no issue named)'}).")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Compose the implementation PR body (issue #287).")
    ap.add_argument("--issue", type=int, help="the issue this PR implements (body/title modes)")
    ap.add_argument("--branch", help="the head branch (a ci/data-gap-<n>-… branch must match)")
    ap.add_argument("--for", dest="mode", default="implementation",
                    choices=("implementation", "refresh", "architecture"),
                    help="which body to print (issue #542)")
    ap.add_argument("--window-file",
                    help="the refresh run's window block (default: compose it from the live run)")
    ap.add_argument("--run-url", default="", help="the architecture run URL")
    ap.add_argument("--title", action="store_true",
                    help="print the PR TITLE for --kind instead of the body (issue #541)")
    ap.add_argument("--check-body-file", dest="check_body_file",
                    help="validate a PR body FILE against the message pattern + closure")
    ap.add_argument("--check-issue-file", dest="check_issue_file",
                    help="validate an ISSUE body FILE against the message pattern (five sections)")
    ap.add_argument("--check-commit-file", dest="check_commit_file",
                    help="validate a COMMIT message FILE against the message pattern + closure")
    ap.add_argument("--event", dest="check_event",
                    help="webhook payload ($GITHUB_EVENT_PATH) to validate (like pr-closure)")
    ap.add_argument("--issue-event", dest="issue_event",
                    help="an `issues` webhook payload ($GITHUB_EVENT_PATH) to validate")
    # `--kind` is deliberately NOT `choices=`: the value comes from the issue's labels at run time,
    # and an unrecognised one must never stop a PR from opening — that would turn a mislabelled
    # issue into a bot that cannot land its own work (measured on PR #609, where a gh read that did
    # not answer made `--kind` a URL and argparse killed the push). An unknown kind falls back to
    # the default LOUDLY instead.
    ap.add_argument("--kind", default="data-gap",
                    help=f"the kind of issue this PR implements: {', '.join(sorted(KIND_TYPES))} "
                         f"(default: data-gap; anything else falls back with a warning)")
    args = ap.parse_args(argv)

    # The message-pattern/closure gate (issue #771): validate a PR body, an issue body or a
    # commit message instead of composing. Reached only through the `make *-message-check`
    # targets (rules 6d/6m).
    if (args.check_body_file or args.check_event or args.check_issue_file
            or args.issue_event or args.check_commit_file):
        return _check_message(args)

    # The two NON-implementation bodies (issue #542) — they close no issue, so they never
    # reach the `render()` path that binds a closing keyword.
    if args.mode == "architecture":
        try:
            sys.stdout.write(architecture_body(args.run_url))
        except RefusedClosing:
            print("[pr-body] REFUSED: an architecture body must carry no closing keyword",
                  file=sys.stderr)
            return 2
        return 0
    if args.mode == "refresh":
        window = Path(args.window_file).read_text(encoding="utf-8") if args.window_file else ""
        if not window:
            import refresh_run_block  # the ONE composer of the window block (issue #199)
            window = refresh_run_block.current_block()
        try:
            sys.stdout.write(refresh_body(window))
        except Empty as exc:
            print(f"[pr-body] REFUSED: {exc}", file=sys.stderr)
            return 2
        return 0

    if args.issue is None:
        print("Usage: pr_body.py --issue <n> [--branch <b>] | --for refresh|architecture",
              file=sys.stderr)
        return 2
    if args.kind not in KIND_TYPES:
        print(f"[pr-body] WARNING: unknown --kind {args.kind!r} (known: "
              f"{', '.join(sorted(KIND_TYPES))}) — falling back to 'data-gap'", file=sys.stderr)
        args.kind = "data-gap"
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
