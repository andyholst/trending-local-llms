#!/usr/bin/env python3
"""A merged PR must close the issue it implements (issue #284, AGENTS.md rule 6e).

GitHub binds a closing keyword to the ONE reference that follows it, and it does not
enumerate a list. Both ways that defeats the promise were measured in this repository:

  * PR #272's body said `Closes #271 and #276` — #271 closed on merge, #276 did not. The
    change was in `master`, the issue was open, and the only assertion anywhere was a
    marker word (`"closes #" in pr_run`), which cannot see it.
  * `refresh-bot.yml`'s refresh PR body ended with `Closes #1` — the CI pipeline META
    issue, closed since 2026-09-28. Every refresh PR carried a closing keyword for an
    issue it does not implement.

The real checker runs here: `scripts/pr_closure.py` is imported (its parser is the logic
under test) AND driven as a CLI over real event payload files, so the exit codes the
pipeline reads are exercised too. No stand-in for the product, no mocks (rule 6m).

Run standalone: python3 tests/test_pr_closure.py   or   make test
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import pr_closure as PC  # noqa: E402  (the real product)

from wiring import wired  # noqa: E402  (issues #176/#192)

SCRIPT = ROOT / "scripts" / "pr_closure.py"
MAKEFILE = (ROOT / "Makefile").read_text(encoding="utf-8")
QA_VALIDATE = (ROOT / ".github" / "workflows" / "qa-validate.yml").read_text(encoding="utf-8")
REFRESH_BOT = (ROOT / ".github" / "workflows" / "refresh-bot.yml").read_text(encoding="utf-8")

_PASS = 0
_FAIL = 0


def check(name: str, cond: bool, detail: object = "") -> None:
    global _PASS, _FAIL
    if cond:
        _PASS += 1
        print(f"  ok  {name}")
    else:
        _FAIL += 1
        print(f"FAIL {name}  {detail}")


def run_cli(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(SCRIPT), *args], capture_output=True, text=True)


def event_file(tmp: Path, name: str, payload: dict) -> Path:
    path = tmp / name
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def pr_event(body: str, ref: str) -> dict:
    """A real webhook payload, the shape `$GITHUB_EVENT_PATH` holds on a pull_request."""
    return {"action": "opened", "pull_request": {"body": body, "head": {"ref": ref}}}


# --------------------------------------------------------------------------------------
# The measured failures
# --------------------------------------------------------------------------------------

def test_a_chained_reference_closes_only_the_first_issue(tmp: Path) -> None:
    """PR #272: `Closes #271 and #276` merged green and left #276 open."""
    body = "Implements the seam.\n\nCloses #271 and #276\n"
    problems = PC.check(body, "ci/data-gap-271-x")
    check("chained: the measured body is REFUSED", bool(problems), problems)
    check("chained: the refusal names the issue that would stay open",
          any("#276" in p for p in problems), problems)
    check("chained: it explains that only the first reference binds",
          any("FIRST reference" in p for p in problems), problems)

    proc = run_cli("--branch", "ci/data-gap-271-x", "--body", body)
    check("chained: the CLI exits 1 (what the pipeline reads)", proc.returncode == 1, proc.stdout)
    check("chained: the refusal is on stderr, naming the problem",
          "REFUSED" in proc.stderr and "#276" in proc.stderr, proc.stderr)

    fixed = "Implements the seam.\n\nCloses #271\nCloses #276\n"
    check("chained: one keyword per issue PASSES", PC.check(fixed, "ci/data-gap-271-x") == [], "")


def test_a_refresh_pr_must_not_close_the_meta_issue(tmp: Path) -> None:
    """refresh-bot's body ended with `Closes #1` — the CI meta issue, long closed."""
    body = "Hermes CLI refresh. Auto-merged when qa-validate is green.\n\nCloses #1"
    problems = PC.check(body, "ci/trending-refresh-20261016-1200")
    check("refresh: a closing keyword on a branch that implements no issue is REFUSED",
          any("implements no issue" in p for p in problems), problems)
    check("refresh: the refusal says what to write instead",
          any("reference the tracking issue" in p for p in problems), problems)

    proc = run_cli("--branch", "ci/trending-refresh-20261016-1200", "--body", body)
    check("refresh: the CLI exits 1", proc.returncode == 1, proc.stdout)

    okay = "Hermes CLI refresh. Auto-merged when qa-validate is green. Refs #1"
    check("refresh: a plain reference PASSES", PC.check(okay, "ci/trending-refresh-20261016-1200") == [], "")
    check("refresh: the shipped body no longer closes the meta issue",
          "Closes #1" not in REFRESH_BOT and "Refs #1" in REFRESH_BOT, "")


def test_the_branch_issue_must_be_closed_by_its_own_keyword(tmp: Path) -> None:
    """A PR whose body never closes its own issue leaves it open for ever."""
    problems = PC.check("Implements it. See #266 for context.", "ci/data-gap-266-storage-offload-31-models")
    check("missing: a body with no closing keyword is REFUSED", bool(problems), problems)
    check("missing: the refusal names the branch's issue", any("#266" in p for p in problems), problems)
    check("missing: a bare reference is not a closing keyword",
          "closes" not in "Implements it. See #266 for context.".lower(), "")

    proc = run_cli("--branch", "ci/data-gap-266-storage-offload-31-models",
                   "--body", "Implements it. See #266 for context.")
    check("missing: the CLI exits 1", proc.returncode == 1, proc.stdout)
    check("missing: closing it properly PASSES",
          PC.check("Implements it.\n\nCloses #266\n", "ci/data-gap-266-storage-offload-31-models") == [], "")


# --------------------------------------------------------------------------------------
# The parser's edges
# --------------------------------------------------------------------------------------

def test_the_branch_encodes_the_issue_the_slug_may_not_confuse() -> None:
    """`ci/data-gap-266-storage-offload-31-models` implements #266, NOT the slug's 31."""
    check("branch: the implementer's branch takes its FIRST number",
          PC.implemented_issue("ci/data-gap-266-storage-offload-31-models") == 266, "")
    check("branch: a trailing issue number is read (`ci/pr-closure-284`)",
          PC.implemented_issue("ci/pr-closure-284") == 284, "")
    check("branch: a worktree branch is read (`ci/worktree-base-271`)",
          PC.implemented_issue("ci/worktree-base-271") == 271, "")
    check("branch: a refresh branch implements NOTHING (its number is a timestamp)",
          PC.implemented_issue("ci/trending-refresh-20261016-1200") is None, "")
    check("branch: no branch implements nothing", PC.implemented_issue(None) is None, "")


def test_every_closing_keyword_is_recognised() -> None:
    for keyword in ("close", "closes", "closed", "fix", "fixes", "fixed",
                    "resolve", "resolves", "resolved", "Closes", "FIXES", "Closes:"):
        body = f"{keyword} #12"
        check(f"keyword: `{keyword} #12` binds #12",
              PC.closing_bindings(body) == [(12, [12])], PC.closing_bindings(body))
    check("keyword: prose that mentions closing never binds",
          PC.closing_bindings("this closes the door on it") == [], "")
    check("keyword: a bare reference is not a closing keyword",
          PC.closing_bindings("see #12") == [], "")


def test_an_explicit_issue_overrides_the_branch() -> None:
    body = "Closes #99\n"
    check("explicit: --issue names the implemented issue",
          PC.check(body, "ci/whatever", issue=99) == [], "")
    check("explicit: a mismatch with the branch issue is refused",
          bool(PC.check(body, "ci/data-gap-12-x", issue=12)), "")


def test_code_quotes_the_rule_it_does_not_make_a_claim() -> None:
    """A body that QUOTES a closing keyword inside code is not closing anything.

    Measured on this change's own PR: the only `Closes #284` sat inside backticks, and GitHub's
    `closingIssuesReferences` came back EMPTY while a naive parse reported a binding — a false
    negative of exactly the class this guard exists to catch.
    """
    check("code: an inline code span does not bind",
          PC.closing_bindings(PC.visible_text("written as `Closes #12` in prose")) == [], "")
    check("code: a fenced block does not bind",
          PC.closing_bindings(PC.visible_text("```\nCloses #12\n```\n")) == [], "")
    check("code: a quoted bad example is invisible to the parser",
          PC.closing_bindings(PC.visible_text("we shipped `Closes #271 and #276` once")) == [], "")
    check("code: prose outside the code still binds",
          PC.closing_bindings(PC.visible_text("quoted below\n```\nCloses #1\n```\nCloses #12\n")) == [(12, [12])], "")

    quoted_only = "Explains the rule: `Closes #12` is what you write.\n"
    check("code: a body whose only keyword is quoted is REFUSED",
          bool(PC.check(quoted_only, "ci/data-gap-12-x")), PC.check(quoted_only, "ci/data-gap-12-x"))

    good = "Explains the rule: `Closes #12` is what you write.\n\nCloses #12\n"
    check("code: the same body WITH a real closing line passes",
          PC.check(good, "ci/data-gap-12-x") == [], PC.check(good, "ci/data-gap-12-x"))


# --------------------------------------------------------------------------------------
# The CLI, over real event payloads (what the pipeline actually runs)
# --------------------------------------------------------------------------------------

def test_the_cli_reads_the_webhook_payload_by_path(tmp: Path) -> None:
    good = event_file(tmp, "good.json", pr_event("Body.\n\nCloses #284\n", "ci/pr-closure-284"))
    proc = run_cli("--event", str(good))
    check("event: a correct PR exits 0", proc.returncode == 0, proc.stderr)
    check("event: it reports the branch and the issue it closes",
          "ci/pr-closure-284" in proc.stdout and "#284" in proc.stdout, proc.stdout)

    bad = event_file(tmp, "bad.json",
                     pr_event("Body.\n\nCloses #271 and #276\n", "ci/data-gap-271-x"))
    proc = run_cli("--event", str(bad))
    check("event: a chained reference exits 1", proc.returncode == 1, proc.stdout)
    check("event: it names the branch and the issue that would stay open",
          "ci/data-gap-271-x" in proc.stderr and "#276" in proc.stderr, proc.stderr)

    push = event_file(tmp, "push.json", {"ref": "refs/heads/master", "commits": []})
    proc = run_cli("--event", str(push))
    check("event: a push to master (no pull_request) is a green no-op",
          proc.returncode == 0 and "nothing to check" in proc.stdout, proc.stdout)


def test_the_pipeline_runs_it_on_every_pr() -> None:
    targets = set(re.findall(r"^([A-Za-z0-9_][A-Za-z0-9_.-]*):", MAKEFILE, re.M))
    check("Makefile: `pr-closure` exists (the seam CI and a human share)",
          "pr-closure" in targets, sorted(t for t in targets if "closure" in t))
    recipe = re.search(r"^pr-closure:.*\n((?:\t.*\n)+)", MAKEFILE, re.M)
    check("Makefile: it calls scripts/pr_closure.py",
          bool(recipe) and "pr_closure.py" in recipe.group(1), "")
    check("Makefile: the test is in the `_test` chain (rule 6d)",
          wired(__file__), "")
    check("qa-validate: the validate job runs `make pr-closure` on every PR",
          "make pr-closure" in QA_VALIDATE, "")
    check("qa-validate: it reads the payload by PATH, never interpolated into the run block",
          "GITHUB_EVENT_PATH" not in QA_VALIDATE.split("make pr-closure")[1][:400], "")


def main() -> int:
    print("a merged PR must close the issue it implements (issue #284)")
    tmp = Path(tempfile.mkdtemp(prefix="pr-closure-"))
    try:
        test_a_chained_reference_closes_only_the_first_issue(tmp)
        test_a_refresh_pr_must_not_close_the_meta_issue(tmp)
        test_the_branch_issue_must_be_closed_by_its_own_keyword(tmp)
        test_the_branch_encodes_the_issue_the_slug_may_not_confuse()
        test_every_closing_keyword_is_recognised()
        test_an_explicit_issue_overrides_the_branch()
        test_code_quotes_the_rule_it_does_not_make_a_claim()
        test_the_cli_reads_the_webhook_payload_by_path(tmp)
        test_the_pipeline_runs_it_on_every_pr()
    finally:
        import shutil
        shutil.rmtree(tmp, ignore_errors=True)
    print(f"\nPASSED {_PASS} | FAILED {_FAIL}")
    return 1 if _FAIL else 0


if __name__ == "__main__":
    raise SystemExit(main())
