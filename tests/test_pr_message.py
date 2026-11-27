#!/usr/bin/env python3
"""The MESSAGE PATTERN: each issue / PR body / commit message carries the five `##` sections
(Why / What / How / Benefits / Technical Solution) and closes exactly the issue it implements
(issue #771).

`scripts/pr_body.py::render` composes the implementation body with the sections, and the new
`scripts/pr_body.py::section_problems` / `pr_message_problems` are the ONE parser — read by the
`--check-body-file` CLI, by `make pr-message-check`, and by these tests — so the composer and
the CI gate cannot drift. The gate applies to the PRs that IMPLEMENT an issue; a refresh or
architecture body (no issue) is not a five-section artifact and must not be blocked.

Run:  python3 tests/test_pr_message.py   or   make test
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "scripts" / "pr_body.py"
sys.path.insert(0, str(ROOT / "scripts"))

import pr_body  # noqa: E402
import pr_closure  # noqa: E402

_PASS = 0
_FAIL = 0

BRANCH = "ci/message-pattern-771"


def check(name: str, ok: bool, detail: object = "") -> None:
    global _PASS, _FAIL
    if ok:
        _PASS += 1
        print(f"  ok  {name}")
    else:
        _FAIL += 1
        print(f"FAIL {name}  {detail}")


def conforming_body() -> str:
    """A minimal body that satisfies section_problems and closes #771."""
    return "\n".join([
        "## Why", "a real gap the analysis filed", "",
        "## What", "the tracked implementation", "",
        "## How", "the mandated path", "",
        "## Benefits", "a reviewable change", "",
        "## Technical Solution", "the files and the tests", "",
        "Closes #771", "",
    ])


def test_the_composed_body_follows_the_message_pattern() -> None:
    # Given  the composer, asked for the issue this branch implements
    body = pr_body.render(771, BRANCH)

    # Then   it starts and ends with the anchors the closure tests already lock
    check("pattern: the body names the issue and the branch",
          body.startswith("Implements #771") and BRANCH in body, body[:120])
    check("pattern: the body ends with its single closing claim",
          body.rstrip().endswith("Closes #771"), body[-80:])
    # And    it carries the five sections in order, and the ONE parser sees no problem
    check("pattern: all five sections present in order",
          all(f"## {s}" in body for s in pr_body.MESSAGE_SECTIONS), pr_body.MESSAGE_SECTIONS)
    check("pattern: section_problems reports nothing",
          pr_body.section_problems(body) == [], pr_body.section_problems(body))
    check("pattern: pr_message_problems reports nothing (closure + sections)",
          pr_body.pr_message_problems(body, BRANCH) == [],
          pr_body.pr_message_problems(body, BRANCH))


def test_a_body_that_skips_a_section_is_refused() -> None:
    # Given  a body with every section present
    base = conforming_body()
    check("pattern: the conforming body passes", pr_body.section_problems(base) == [],
          pr_body.section_problems(base))

    # Then   removing any one section is refused and the refusal names THAT section
    for section in pr_body.MESSAGE_SECTIONS:
        header = f"## {section}"
        # Split out this section's block (header + its first content line + blank)
        lines = base.splitlines()
        idx = lines.index(header)
        removed = "\n".join(lines[:idx] + lines[idx + 2:])
        problems = pr_body.section_problems(removed)
        check(f"pattern: a body missing {header} is refused",
              problems != [] and f"## {section}" in problems[0], problems)

    # And    an empty section (header then the next header) is refused
    empty = "\n".join(["## Why", "why", "", "## What", "", "## How", "how", "",
                       "## Benefits", "b", "", "## Technical Solution", "t", ""])
    empty_problems = pr_body.section_problems(empty)
    check("pattern: an empty '## What' is refused",
          any("empty" in p and "What" in p for p in empty_problems), empty_problems)

    # And    out-of-order sections are refused by name
    swapped = "\n".join(["## Why", "w", "", "## How", "h", "", "## What", "w2", "",
                         "## Benefits", "b", "", "## Technical Solution", "t", ""])
    order_problems = pr_body.section_problems(swapped)
    check("pattern: out-of-order sections are refused",
          any("out of order" in p for p in order_problems), order_problems)


def test_the_pr_message_cli_refuses_a_non_conforming_body_by_name() -> None:
    def run(body: str, branch: str) -> subprocess.CompletedProcess:
        with tempfile.TemporaryDirectory() as td:
            f = Path(td) / "body.md"
            f.write_text(body)
            return subprocess.run(
                [sys.executable, str(SCRIPT), "--check-body-file", str(f), "--branch", branch],
                capture_output=True, text=True)

    # Given  a conforming implementation body and a branch that encodes its issue
    ok = run(conforming_body(), BRANCH)
    check("CLI: a conforming body passes", ok.returncode == 0 and "OK" in ok.stdout,
          (ok.returncode, ok.stdout[-200:]))

    # Then   a body missing a section is REFUSED and names the missing section on stderr
    missing_what = conforming_body().replace("\n## What\n", "\n## WhatFiller\n", 1)
    bad = run(missing_what, BRANCH)
    check("CLI: a body missing a section fails with a non-zero exit",
          bad.returncode == 1, (bad.returncode, bad.stderr[-300:]))
    check("CLI: the refusal names the missing section",
          "REFUSED" in bad.stderr and "## What" in bad.stderr, bad.stderr[-400:])


def test_commit_cli_refuses_a_non_conforming_message() -> None:
    def run(msg: str) -> subprocess.CompletedProcess:
        with tempfile.TemporaryDirectory() as td:
            f = Path(td) / "msg.txt"
            f.write_text(msg)
            return subprocess.run(
                [sys.executable, str(SCRIPT), "--check-commit-file", str(f)],
                capture_output=True, text=True)

    # Given  a conforming squash message (the five sections + its own Closes claim)
    good = run(conforming_body())
    check("commit: a conforming squash message passes",
          good.returncode == 0 and "OK" in good.stdout, (good.returncode, good.stdout[-200:]))

    # Then   a message that skips a section is REFUSED and names it on stderr
    bad = run(conforming_body().replace("\n## What\n", "\n## WhatFiller\n", 1))
    check("commit: a message missing a section fails non-zero",
          bad.returncode == 1, (bad.returncode, bad.stderr[-300:]))
    check("commit: the refusal names the missing section",
          "REFUSED" in bad.stderr and "## What" in bad.stderr, bad.stderr[-400:])


def test_the_commit_gate_discriminates_an_archive_squash() -> None:
    """The push gate reads the CLAIM, not the first `#<n>` (issue #852).

    Rule 6f makes an archive commit mandatory for every merged change. The gate refused
    `8965a45` ("archive the merged log-tail-honored and per-round-log-capture changes
    #845/#846 left active (#851)") for missing the five sections AND "implements #845" —
    an archive that implements nothing. Discrimination must not go the other way either:
    a commit that CLAIMS an implementation is still held to sections + its own closes.
    """
    def run(msg: str) -> subprocess.CompletedProcess:
        with tempfile.TemporaryDirectory() as td:
            f = Path(td) / "msg.txt"
            f.write_text(msg)
            return subprocess.run(
                [sys.executable, str(SCRIPT), "--check-commit-file", str(f)],
                capture_output=True, text=True)

    # Given  the exact archive commit message that went red (run 43216532672 on 8965a45)
    archive = ("chore(openspec): archive the merged log-tail-honored and per-round-log-"
               "capture changes #845/#846 left active (#851)\n\n"
               "Refs: openspec/changes/log-tail-honored-in-fix-loop-rounds\n"
               "Refs: openspec/changes/per-round-log-tail-capture\n")
    # Then   it passes: an archive names references and claims no implementation
    ok = run(archive)
    check("commit #852: an archive commit naming merged PRs is not forced to be an implementation",
          ok.returncode == 0, (ok.returncode, ok.stdout[-200:], ok.stderr[-300:]))

    # And    the old first-`#<n>` reading still refuses the same claim shape a real
    #        implementation carries — discrimination must not gut the gate
    claim_no_sections = ("fix(tech-debt): implement #635 from the tech-debt the analysis opened\n\n"
                         "some prose without the five sections\n")
    bad = run(claim_no_sections)
    check("commit #852: an 'implement #635' title without the sections stays refused",
          bad.returncode == 1 and "## Why" in bad.stderr, (bad.returncode, bad.stderr[-300:]))

    # And    a claim whose closing keyword binds ANOTHER number is still refused
    misbound = conforming_body().replace("Closes #771", "Closes #999", 1)
    misbound = ("fix(tech-debt): implement #771 from the tech-debt the analysis opened\n\n"
                + misbound)
    wrong = run(misbound)
    check("commit #852: an implement #771 claim closed by 'Closes #999' is refused",
          wrong.returncode == 1 and "#771" in wrong.stderr, (wrong.returncode, wrong.stderr[-300:]))

    # And    the composer's own squash message (title claim + sections + own closes) passes
    full = run(pr_body.title(771, "tech-debt") + "\n\n" + conforming_body())
    check("commit #852: the composed squash message passes",
          full.returncode == 0, (full.returncode, full.stderr[-200:]))

    # And    the unit discrimination itself: title verb or closing binding, never a bare number
    check("claim: archive title claims nothing",
          pr_closure.implemented_issue_from_message(archive) is None)
    check("claim: an 'implement #635' title claims 635",
          pr_closure.implemented_issue_from_message("fix(tech-debt): implement #635 from …") == 635)
    check("claim: a closing binding in the body claims its issue",
          pr_closure.implemented_issue_from_message("chore(ci): retire the old seam\n\nCloses #814") == 814)
    check("claim: a verb inside a code quote is prose, not a claim",
          pr_closure.implemented_issue_from_message("chore(openspec): archive\n\n"
                                                    "The doc says `implement #635` verbatim.") is None)


def test_the_commit_claim_parser_lives_in_pr_closure() -> None:
    # Given  the rule that the claim parser has ONE home (rule 6d)
    # Then   the IMPLEMENT_CLAIM pattern exists in pr_closure.py and nowhere else in scripts/,
    #        and pr_body._commit_issue delegates to it rather than keeping its own regex.
    scripts = (ROOT / "scripts")
    carriers = [p.name for p in sorted(scripts.glob("*.py"))
                if "IMPLEMENT_CLAIM" in p.read_text(encoding="utf-8")]
    check("one home: only scripts/pr_closure.py carries the commit-claim pattern",
          carriers == ["pr_closure.py"], carriers)
    body_src = (scripts / "pr_body.py").read_text(encoding="utf-8")
    check("one home: _commit_issue delegates to pr_closure.implemented_issue_from_message",
          "pr_closure.implemented_issue_from_message(text)" in body_src)


def test_declared_issue_is_validated_and_legacy_passes() -> None:
    def run(body: str) -> subprocess.CompletedProcess:
        with tempfile.TemporaryDirectory() as td:
            f = Path(td) / "issue.md"
            f.write_text(body)
            return subprocess.run(
                [sys.executable, str(SCRIPT), "--check-issue-file", str(f)],
                capture_output=True, text=True)

    # Given  a legacy structured data-gap issue with NO marker (own schema)
    legacy = "## Goal\nClose the gaps.\n## Ranked gaps\n- none\n"
    # Then   it is NOT forced through the five-section shape and passes
    ok_legacy = run(legacy)
    check("issue: a legacy structured issue passes (no marker)",
          ok_legacy.returncode == 0, (ok_legacy.returncode, ok_legacy.stderr[-200:]))

    # And    a declared (marker) issue that follows the pattern passes
    declared_ok = run(pr_body.ISSUE_PATTERN_MARKER + "\n" + conforming_body())
    check("issue: a declared pattern issue that conforms passes",
          declared_ok.returncode == 0, (declared_ok.returncode, declared_ok.stderr[-300:]))

    # And    a declared issue that skips a section is REFUSED by name
    declared_bad = run(pr_body.ISSUE_PATTERN_MARKER + "\n"
                       + conforming_body().replace("\n## How\n", "\n## HowFiller\n", 1))
    check("issue: a declared issue missing a section is refused",
          declared_bad.returncode == 1 and "## How" in declared_bad.stderr,
          (declared_bad.returncode, declared_bad.stderr[-400:]))


def test_a_non_implementation_pr_is_not_forced_to_carry_the_sections() -> None:
    # Given  a refresh branch (it encodes a timestamp, not an issue) and a window+contract body
    refresh_branch = "ci/trending-refresh-20261111-000000"
    body = ("<!-- refresh-bot-run: 2026-11-11T06:00:00Z run=1 -->\n"
            "started=… legs: nvidia=… · aggregate=…\n")

    # Then   the message-pattern gate skips the sections (nothing to implement)
    check("gate: a refresh body is not forced to carry the sections",
          pr_body.pr_message_problems(body, refresh_branch)
          == pr_closure.check(body, refresh_branch),
          pr_body.pr_message_problems(body, refresh_branch))


def test_the_squash_title_is_a_conventional_commit() -> None:
    # Given  an issue of each kind the composer knows
    # Then   the squash title is a Conventional-Commit of the right type, naming the issue
    pattern = re.compile(r"^(feat|fix)\((tech-debt|data-gap)\): implement #771 from ")
    for kind, prefix in (("data-gap", "feat(data-gap)"), ("tech-debt", "fix(tech-debt)")):
        title = pr_body.title(771, kind)
        check(f"title: a {kind} issue is titled {prefix}",
              title.startswith(prefix) and f"#771" in title, title)
        check(f"title: '{kind}' matches the conventional shape", bool(pattern.match(title)), title)


def test_the_live_pr_preflight_refuses_a_body_the_check_rejects() -> None:
    """Issue #1710: a lane can refuse to claim/hand over a branch whose LIVE PR body fails
    the same gate CI will apply. The only stand-in is the external `gh` CLI (rule 6m)."""
    import os

    stub = """#!/bin/sh
printf '%s\\n' "$@" > "$TLL_STUB_ARGV"
if [ "$TLL_STUB_GH_RC" = "1" ]; then
  echo 'not found' >&2
  exit 1
fi
cat "$TLL_STUB_PR_JSON"
"""

    def run(body: str, branch: str, *, gh_fails: bool = False,
            via_make: bool = False) -> tuple[subprocess.CompletedProcess, str, str]:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            payload = root / "pr.json"
            payload.write_text(json.dumps({"body": body, "headRefName": branch}))
            argv_log = root / "argv.txt"
            bin_dir = root / "bin"
            bin_dir.mkdir()
            gh = bin_dir / "gh"
            gh.write_text(stub)
            gh.chmod(0o755)
            env = dict(os.environ)
            env["PATH"] = str(bin_dir) + os.pathsep + env.get("PATH", "")
            env["TLL_STUB_PR_JSON"] = str(payload)
            env["TLL_STUB_ARGV"] = str(argv_log)
            env["TLL_STUB_GH_RC"] = "1" if gh_fails else "0"
            env["PYTHONDONTWRITEBYTECODE"] = "1"
            cmd = (["make", "pr-message-check", "PR=4242"] if via_make else
                   [sys.executable, str(SCRIPT), "--check-live-pr", "4242"])
            proc = subprocess.run(cmd, cwd=ROOT if via_make else None, env=env,
                                  capture_output=True, text=True)
            return proc, argv_log.read_text() if argv_log.exists() else "", str(root)

    # Given  a conforming live body on a branch that encodes its issue
    ok, argv, _ = run(conforming_body(), BRANCH)
    check("live-PR preflight: a conforming body passes",
          ok.returncode == 0 and "OK" in ok.stdout, (ok.returncode, ok.stderr[-200:]))
    check("live-PR preflight: one recorded gh field set, no invented call",
          "pr\nview\n4242\n--json\nbody,headRefName\n" in argv, argv)

    # Then   a body CI refuses is refused HERE, naming the missing section
    bad, _, _ = run(conforming_body().replace("\n## What\n", "\n## WhatFiller\n", 1), BRANCH)
    check("live-PR preflight: a body missing a section is refused",
          bad.returncode == 1 and "REFUSED" in bad.stderr and "## What" in bad.stderr,
          (bad.returncode, bad.stderr[-300:]))

    # And    an unreadable PR is loud (exit 2), never a silent clean
    unreadable, _, _ = run(conforming_body(), BRANCH, gh_fails=True)
    check("live-PR preflight: a failed gh read is loud",
          unreadable.returncode == 2 and "cannot read PR #4242" in unreadable.stderr,
          (unreadable.returncode, unreadable.stderr[-200:]))

    # And    the same seam is reachable from the lane's Makefile, not only the script
    made_ok, made_argv, _ = run(conforming_body(), BRANCH, via_make=True)
    check("live-PR preflight: make pr-message-check PR=<n> passes a good body",
          made_ok.returncode == 0, (made_ok.returncode, made_ok.stderr[-200:]))
    check("live-PR preflight: the Makefile reads the live PR, not a stale file",
          "pr\nview\n4242\n--json\nbody,headRefName\n" in made_argv, made_argv)
    made_bad, _, _ = run(conforming_body().replace("\n## Benefits\n", "\n## BenefitsX\n", 1),
                         BRANCH, via_make=True)
    check("live-PR preflight: make pr-message-check PR=<n> refuses a bad body",
          made_bad.returncode != 0 and "REFUSED" in made_bad.stderr,
          (made_bad.returncode, made_bad.stderr[-300:]))


FILING_LANE_PROMPTS = (
    "agents/tll-reviewer/skills/tll-reviewer/SKILL.md",
    "agents/tll-tester/skills/tll-tester/SKILL.md",
    "agents/tll-planner/skills/tll-planner/SKILL.md",
    # #1814: the architect filed an opt-in body missing ## Technical Solution (#1808);
    # #1730's pre-file check was wired into only three of the filing lanes.
    "agents/tll-architect/skills/tll-architect/SKILL.md",
)


def test_a_filing_lane_validates_its_draft_issue_body_before_create() -> None:
    """A bot-filed issue body cannot red the `issues` branch of pr-closure (issue #1730).

    The filing lanes use the ONE validator the CI gate runs -- `make issue-message-check
    BODY_FILE=` -- before `gh issue create`, so no second parser creeps into a lane prompt.
    """
    for rel in FILING_LANE_PROMPTS:
        src = (ROOT / rel).read_text()
        pre = src.find("make issue-message-check BODY_FILE=")
        create = src.find("gh issue create")
        check(f"{rel}: names the issue-body preflight", pre >= 0,
              "no BODY_FILE seam in the filing prompt")
        check(f"{rel}: preflight precedes gh issue create",
              pre >= 0 and create >= 0
              and src.find("issue-message-check") < create,
              "the create instruction appears before the validator")

    makefile = (ROOT / "Makefile").read_text()
    recipe = makefile.split("issue-message-check:", 1)[-1].split("\n\n", 1)[0]
    check("issue-message-check forwards BODY_FILE to --check-issue-file",
          '--check-issue-file "$(BODY_FILE)"' in recipe, recipe[:300])
    check("pr_body.py owns the --check-issue-file seam",
          '"--check-issue-file"' in (ROOT / "scripts" / "pr_body.py").read_text())


def main() -> int:
    print("pr-message pattern (issue #771)")
    test_the_composed_body_follows_the_message_pattern()
    test_a_body_that_skips_a_section_is_refused()
    test_the_pr_message_cli_refuses_a_non_conforming_body_by_name()
    test_the_live_pr_preflight_refuses_a_body_the_check_rejects()
    test_commit_cli_refuses_a_non_conforming_message()
    test_the_commit_gate_discriminates_an_archive_squash()
    test_the_commit_claim_parser_lives_in_pr_closure()
    test_declared_issue_is_validated_and_legacy_passes()
    test_a_filing_lane_validates_its_draft_issue_body_before_create()
    test_a_non_implementation_pr_is_not_forced_to_carry_the_sections()
    test_the_squash_title_is_a_conventional_commit()
    print(f"\nPASSED {_PASS} | FAILED {_FAIL}")
    return 1 if _FAIL else 0


if __name__ == "__main__":
    raise SystemExit(main())
