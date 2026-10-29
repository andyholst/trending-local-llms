#!/usr/bin/env python3
"""The implementation PR body is composed by a TARGET, and it closes the issue it names
(issue #287).

`.github/workflows/issue-bot.yml` built the body with `cat > pr-body.md <<'BODY'` and appended
the closing keyword with `printf`. That body is the artifact that decides whether the issue
closes on merge (AGENTS.md rule 6e), and it was the only PR artifact in the pipeline with no
target behind it — so no test could RUN it, `make pr-closure` could only read what the shell had
already written, and its wording said "the filed data-gap issue" even for a `tech-debt` issue.

These tests drive the REAL composer and the REAL Makefile recipe, and the shipped workflow step
end to end (only `gh`, an external system, is stubbed — rule 6m), then hand the body it produced
to the same parser the pipeline uses (`scripts/pr_closure.py`), so the composer and the guard
that reads merged PRs cannot drift.

Run:  python3 tests/test_pr_body.py   or   make test
"""
from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "scripts" / "pr_body.py"
sys.path.insert(0, str(ROOT / "scripts"))

import pr_body  # noqa: E402
import pr_closure  # noqa: E402

_PASS = 0
_FAIL = 0

BRANCH = "ci/data-gap-287-tech-debt-the-pr-body-is-assembled-by-in"


def check(name: str, ok: bool, detail: object = "") -> None:
    global _PASS, _FAIL
    if ok:
        _PASS += 1
        print(f"  ok  {name}")
    else:
        _FAIL += 1
        print(f"FAIL {name}  {detail}")


def _workflow_step(name: str) -> dict:
    wf = yaml.safe_load((ROOT / ".github" / "workflows" / "issue-bot.yml").read_text())
    for s in wf["jobs"]["implement"]["steps"]:
        if name.lower() in str(s.get("name", "")).lower():
            return s
    raise AssertionError(f"no step named {name!r} in issue-bot.yml")


def _run_step(issue: str = "287") -> tuple[int, str, str, str]:
    """Execute the REAL "Open the PR" step in the checkout with a stub `gh`.

    Only `gh` is a stand-in (the GitHub API is the external system); `make pr-body` and the
    composer run for real, in the repo root, because that is how the workflow runs them.
    """
    pr = _workflow_step("Open the PR")
    td = Path(tempfile.mkdtemp())
    try:
        bin_ = td / "bin"
        bin_.mkdir()
        gh = bin_ / "gh"
        gh.write_text("""#!/bin/sh
printf "%s\\n" "$*" >> "$TD/gh.log"
case "$1" in
  api) printf '%s\\n' 'data-gap' ;;   # what the step's --jq prints for a data-gap issue
  *)
    prev=""
    for a in "$@"; do
      [ "$prev" = "--body-file" ] && cp "$a" "$TD/body.md"
      prev="$a"
    done
    echo "https://example.invalid/pull/1"
    ;;
esac
""")
        gh.chmod(0o755)
        env = dict(os.environ, PATH=f"{bin_}{os.pathsep}{os.environ['PATH']}", TD=str(td),
                   ISSUE=issue, BRANCH=f"ci/data-gap-{issue}-slug", REPO="o/r",
                   GH_TOKEN="x", GITHUB_OUTPUT=str(td / "out"))
        # The step's own literal env (e.g. MAKEFLAGS, which keeps make's directory banner
        # out of the body) applies exactly as it does in the job.
        env.update({k: str(v) for k, v in (pr.get("env") or {}).items() if "${{" not in str(v)})
        p = subprocess.run(["bash", "-e", "-c", pr["run"]], cwd=ROOT, env=env,
                           capture_output=True, text=True)
        log = (td / "gh.log").read_text() if (td / "gh.log").exists() else ""
        body = (td / "body.md").read_text() if (td / "body.md").exists() else ""
        return p.returncode, p.stdout + p.stderr, log, body
    finally:
        (ROOT / "pr-body.md").unlink(missing_ok=True)
        shutil.rmtree(td, ignore_errors=True)


def test_the_composed_body_closes_exactly_the_issue_it_implements() -> None:
    # Given  the composer, asked for the issue this branch implements
    body = pr_body.render(287, BRANCH)

    # Then   the pipeline's OWN parser finds nothing wrong with it
    problems = pr_closure.check(body, BRANCH)
    check("pr-body: the body closes the issue its branch implements", problems == [], problems)

    # And    exactly one closing keyword binds exactly one reference
    binds = pr_closure.closing_bindings(pr_closure.visible_text(body))
    check("pr-body: one closing keyword, binding one reference", binds == [(287, [287])], binds)

    # And    the body names the issue it implements (a reader, not only GitHub, can tell)
    check("pr-body: the body names the issue and the branch",
          "Implements #287" in body and BRANCH in body, body[:120])

    # And    the two shapes that broke the pipeline in reality are still refused by the
    #        same parser, so this test is not vacuous
    for bad, why in (("closes #271 and #276", "a chained reference"), ("closes #999", "the wrong issue")):
        check(f"pr-body: the parser would refuse {why}", pr_closure.check(bad, BRANCH) != [], bad)


def test_a_branch_that_implements_another_issue_is_refused() -> None:
    # Given  a body that would close #287, opened from #376's branch
    try:
        pr_body.render(287, "ci/data-gap-376-slug")
        refused, detail = False, "render() wrote a body for the wrong issue"
    except pr_body.Mismatch as exc:
        refused, detail = True, str(exc)
    check("pr-body: a branch implementing another issue is refused", refused, detail)
    check("pr-body: the refusal names both issues",
          "376" in str(detail) and "287" in str(detail), detail)

    # And    the CLI refuses it too, with a non-zero exit and the reason on stderr (never a
    #        half-written body on stdout that the step would redirect into pr-body.md)
    p = subprocess.run([sys.executable, str(SCRIPT), "--issue", "287",
                        "--branch", "ci/data-gap-376-slug"], capture_output=True, text=True)
    check("pr-body: the CLI exits 2 and keeps stdout empty", p.returncode == 2 and p.stdout == "",
          f"rc={p.returncode} stdout={p.stdout[:120]!r}")
    check("pr-body: the CLI says why on stderr", "REFUSED" in p.stderr and "376" in p.stderr,
          p.stderr[:200])


def test_the_cli_prints_the_body_on_stdout() -> None:
    # Given  the script invoked the way the make target invokes it
    p = subprocess.run([sys.executable, str(SCRIPT), "--issue", "287", "--branch", BRANCH],
                       capture_output=True, text=True)

    # Then   stdout IS the body — nothing else — so redirecting it produces the file GitHub reads
    check("pr-body: the CLI exits 0", p.returncode == 0, p.stderr[-300:])
    check("pr-body: stdout is exactly the composed body", p.stdout == pr_body.render(287, BRANCH),
          p.stdout[:200])
    check("pr-body: the body ends with its single closing claim",
          p.stdout.rstrip().endswith("Closes #287"), p.stdout[-80:])


def test_the_target_prints_the_body_and_a_missing_issue_is_a_usage_error() -> None:
    # Given  the public target a workflow calls
    env = dict(os.environ, MAKEFLAGS="--no-print-directory")
    p = subprocess.run(["make", "pr-body", "ISSUE=287", f"BRANCH={BRANCH}"], cwd=ROOT,
                       capture_output=True, text=True, env=env)
    # Then   it prints the BODY and no echoed recipe line (`@`-silenced), or the redirect the
    #        workflow performs would put `python3 scripts/pr_body.py …` inside the PR body
    check("pr-body: make pr-body succeeds", p.returncode == 0, p.stderr[-400:])
    check("pr-body: make echoes no recipe line into the body",
          p.stdout.startswith("Implements #287") and "python3 scripts/pr_body.py" not in p.stdout,
          p.stdout[:160])

    # And    an invocation with no issue refuses instead of composing a body for issue 0
    bad = subprocess.run(["make", "pr-body"], cwd=ROOT, capture_output=True, text=True, env=env)
    check("pr-body: a missing ISSUE is a usage error", bad.returncode != 0 and "Usage:" in bad.stdout,
          f"rc={bad.returncode} {bad.stdout[:160]}")


def test_the_issue_bot_step_composes_the_body_through_the_target() -> None:
    # Given  the shipped "Open the PR" step
    pr = _workflow_step("Open the PR")
    run = pr.get("run", "")

    # Then   its body comes from the target, not from a heredoc in the YAML (the defect #287)
    check("pr-body: the step composes the body with make pr-body", "make pr-body" in run, run[:300])
    check("pr-body: no heredoc body is spelled in the workflow",
          "<<'BODY'" not in run and "cat > pr-body.md" not in run, run[:300])
    check("pr-body: the step no longer appends the closing keyword itself",
          "printf" not in run, run[:300])

    # And    the composed file is what `gh` is handed
    check("pr-body: the PR is created from the composed body file",
          "--body-file pr-body.md" in run, run[-200:])


def test_the_shipped_step_hands_a_closure_correct_body_to_gh() -> None:
    # Given  the step EXECUTED (real make recipe, real composer, stub gh)
    rc, out, log, body = _run_step("287")

    # Then   it opens a PR with a non-empty body file
    check("pr-body: the executed step opens the PR", rc == 0 and "--body-file" in log, out[-400:])
    check("pr-body: the body it hands gh is non-empty", bool(body.strip()), body[:200])

    # And    that body closes EXACTLY the issue its branch implements (rule 6e)
    problems = pr_closure.check(body, "ci/data-gap-287-slug")
    check("pr-body: the shipped body closes the issue it implements", problems == [], problems)
    check("pr-body: the shipped body names the issue",
          "Implements #287" in body and body.rstrip().endswith("Closes #287"),
          body[:160])


def test_the_other_two_pr_bodies_are_composed_too():
    """Issue #542: the refresh and architecture bodies were built INSIDE the workflows.

    `refresh-bot.yml` used a `{ … } > "$PR_BODY"` block and `architecture-bot.yml` four `printf`
    lines, so neither text could be rendered locally or run by a test — the defect #287 fixed for
    the implementer's body. The architecture body additionally must carry NO closing keyword
    (rule 6e: it implements no issue).
    """
    def make(*args):
        return subprocess.run(["make", "--no-print-directory", *args],
                              cwd=str(ROOT), capture_output=True, text=True)

    # Given a window block, the refresh body is that block + the contract, byte for byte
    with tempfile.TemporaryDirectory() as td:
        window = Path(td) / "w.md"
        window.write_text("<!-- refresh-bot-run: 2026-10-25T06:00:00Z run=1 -->\n"
                          "started=… legs: nvidia=… · aggregate=…\n")
        refresh = make("refresh-pr-body", f"WINDOW_FILE={window}")
        empty = make("refresh-pr-body", f"WINDOW_FILE={Path(td) / 'missing.md'}")
        check("refresh body: the target succeeds", refresh.returncode == 0, refresh.stderr[-300:])
        check("refresh body: the WINDOW block comes first",
              refresh.stdout.startswith("<!-- refresh-bot-run:"), refresh.stdout[:120])
        check("refresh body: the contract sentence follows",
              "Auto-merged when qa-validate is green" in refresh.stdout, refresh.stdout[-200:])
        check("refresh body: an unreadable window is REFUSED, never a blank first section",
              empty.returncode != 0, empty.stdout + empty.stderr)

    # And  the architecture body carries NO closing keyword, and names the run
    arch = make("architecture-pr-body", "RUN_URL=https://example/run/1")
    check("architecture body: the target succeeds", arch.returncode == 0, arch.stderr[-300:])
    check("architecture body: it names the run", "Run: https://example/run/1" in arch.stdout,
          arch.stdout[-200:])
    check("architecture body: it carries NO closing keyword (rule 6e)",
          pr_closure.check(arch.stdout, "") == []
          or not any("closing" in p for p in pr_closure.check(arch.stdout, "")),
          pr_closure.check(arch.stdout, ""))
    check("architecture body: it references #479 without closing it",
          "#479" in arch.stdout and "never closed" in arch.stdout, arch.stdout[-200:])

    # And  neither workflow builds its body inline any more
    rf = (ROOT / ".github" / "workflows" / "refresh-bot.yml").read_text()
    ab = (ROOT / ".github" / "workflows" / "architecture-bot.yml").read_text()
    check("workflow: refresh-bot redirects the target", "make refresh-pr-body > \"$PR_BODY\"" in rf, "")
    check("workflow: refresh-bot carries no inline contract sentence",
          "Hermes CLI refresh (deepseek-v4-flash-0731 via Nous)" not in rf, "")
    check("workflow: architecture-bot pipes the target into gh",
          "make architecture-pr-body RUN_URL=\"$RUN_URL\" | gh pr create" in ab, "")
    check("workflow: architecture-bot carries no inline body printf",
          "A generated description was stale" not in ab, "")
def test_the_pr_title_is_composed_from_the_issue_kind():
    """Issue #541: the title was inline and called every PR a "data-gap" change.

    The sweep takes BOTH `data-gap-analysis` and `tech-debt` issues, so a `tech-debt` fix was
    titled `feat(data-gap): implement the #<n> gap analysis item` — wrong kind, wrong artifact, and
    unreachable by any test because the text lived inside the workflow.
    """
    def run(*args):
        return subprocess.run(["make", "--no-print-directory", "pr-title", *args],
                              cwd=str(ROOT), capture_output=True, text=True)

    tech = run("ISSUE=541", "KIND=tech-debt")
    gap = run("ISSUE=541", "KIND=data-gap")
    bogus = run("ISSUE=541", "KIND=bogus")
    missing = run("KIND=tech-debt")

    check("pr-title: a tech-debt issue is titled a FIX",
          tech.returncode == 0 and tech.stdout.startswith("fix(tech-debt): "), tech.stdout)
    check("pr-title: it names the issue", "#541" in tech.stdout, tech.stdout)
    check("pr-title: a data-gap issue is titled a FEAT",
          gap.returncode == 0 and gap.stdout.startswith("feat(data-gap): "), gap.stdout)
    # An unknown kind must NOT stop the PR from opening — it is a `gh` label read at run time, and
    # refusing there killed the bot's push step in production (PR #609). It falls back to the
    # default and SAYS SO, which is "never silently guessed".
    check("pr-title: an unknown kind falls back to the default kind",
          bogus.returncode == 0 and bogus.stdout.startswith("feat(data-gap): "),
          bogus.stdout + bogus.stderr)
    check("pr-title: and the fallback is announced, never silent",
          "unknown --kind" in bogus.stderr, bogus.stderr)
    check("pr-title: a missing ISSUE is a usage error", missing.returncode != 0,
          missing.stdout + missing.stderr)
    check("pr-title: the recipe is silenced, so a CAPTURE holds the title alone",
          not any(line.startswith("python3") for line in tech.stdout.splitlines()), tech.stdout)

    # And   the shipped step composes it instead of spelling it
    wf = (ROOT / ".github" / "workflows" / "issue-bot.yml").read_text()
    check("workflow: the inline title is gone",
          "implement the #$ISSUE gap analysis item" not in wf)
    check("workflow: the step composes the title through the target",
          "make pr-title ISSUE=\"$ISSUE\" KIND=\"$KIND\"" in wf, "")
    check("workflow: the kind comes from the issue's labels, not a constant",
          "index(\"tech-debt\")" in wf, "")


def test_an_unrecognised_kind_falls_back_instead_of_refusing():
    """Issue #541: the kind is read from the issue's labels at run time, so it is not a constant.

    Measured on PR #609: `argparse(choices=...)` made an unexpected value exit 2 in the middle of
    the bot's push step, so no PR was ever created. A mislabelled issue must not block the work.
    """
    proc = subprocess.run([sys.executable, str(SCRIPT), "--issue", "7", "--title",
                           "--kind", "https://example.invalid/pull/1"],
                          capture_output=True, text=True)
    check("kind: an unknown --kind still prints a title", proc.returncode == 0,
          (proc.returncode, proc.stderr[-200:]))
    check("kind: it falls back to the data-gap title", proc.stdout.strip() != "",
          proc.stdout[:120])
    check("kind: and it says so loudly on stderr", "unknown --kind" in proc.stderr,
          proc.stderr[-200:])


def main() -> int:
    print("pr-body composer (issue #287)")
    test_the_composed_body_closes_exactly_the_issue_it_implements()
    test_a_branch_that_implements_another_issue_is_refused()
    test_the_cli_prints_the_body_on_stdout()
    test_the_target_prints_the_body_and_a_missing_issue_is_a_usage_error()
    test_the_issue_bot_step_composes_the_body_through_the_target()
    test_the_other_two_pr_bodies_are_composed_too()
    test_the_pr_title_is_composed_from_the_issue_kind()
    test_the_shipped_step_hands_a_closure_correct_body_to_gh()
    test_an_unrecognised_kind_falls_back_instead_of_refusing()
    print(f"\nPASSED {_PASS} | FAILED {_FAIL}")
    return 1 if _FAIL else 0


if __name__ == "__main__":
    raise SystemExit(main())
