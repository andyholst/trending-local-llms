#!/usr/bin/env python3
"""Control-flow tests for scripts/fix_loop.sh (the fix-bot repair loop).

The fix-bot never fixed a PR before: its loop ran under `bash -e` (died on the
first red check), never ran `make validate`, never stopped when green, and
pushed whether or not anything was fixed. These tests run the REAL script with
MAKE pointed at a small recorder that plays a scripted sequence of check results
(the Hermes call itself is exercised live by `make hermes-smoke`).

  - green on entry            -> 0 fix calls, exit 0
  - red, fixed by round 1     -> 1 fix call, stops, exit 0
  - red forever               -> FIX_ROUNDS fix calls, exit 1, report kept
  - make fix crashing         -> loop keeps going (no bash -e abort)
  - report content            -> failing check output lands in qa-report.txt
  - every check runs          -> validate, validate-search, validate-mapped, test
  - reasoning budget burnt    -> same round retried once with HERMES_FIX_REASONING=none
                                 (PR #80: 2 of 3 rounds wrote nothing at 'low')
  - report = failing check only -> passing checks' unit-suite noise stays out

Run:  python3 tests/test_fix_loop.py   or   make test
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LOOP = ROOT / "scripts" / "fix_loop.sh"

_PASS = 0
_FAIL = 0


def check(name, cond, detail: object = ""):
    global _PASS, _FAIL
    if cond:
        _PASS += 1
        print(f"  ok  {name}")
    else:
        _FAIL += 1
        print(f"  FAIL {name}" + (f"  [{detail}]" if detail else ""))


# Recorder: logs every target to calls.log. `validate` fails while the
# remaining-red counter in state/red is > 0; each `make fix` decrements it
# (FIX_EXIT controls fix's own exit code).
RECORDER = r"""#!/usr/bin/env bash
d="$(dirname "$0")"
echo "$*" | tr ' ' '+' >> "$d/calls.log"
red=$(cat "$d/red")
case "$1" in
  fix)
    [ "${FIX_SLEEP:-0}" -gt 0 ] && sleep "${FIX_SLEEP}"
    if [ "${BUDGET_BURN:-0}" = "1" ] && [ "$2" != "HERMES_FIX_REASONING=none" ]; then
      echo "No visible answer was produced. The model hit its output-token limit on every continuation attempt - its reasoning consumed the entire budget each time."
      exit 2
    fi
    [ "$red" -gt 0 ] && echo $((red - 1)) > "$d/red"
    exit "${FIX_EXIT:-0}" ;;
  validate-search)
    echo "  ok  mapping: id match"
    echo "  FAIL: m1: duplicate model ids in models.json: ['m1']"
    if [ "${VS_RED:-0}" = "1" ]; then echo "  FAIL mapping: real regression"; echo "PASSED 4 | FAILED 1"; exit 1; fi
    echo "PASSED 5 | FAILED 0"; exit 0 ;;
  validate)
    if [ "$red" -gt 0 ]; then echo "  FAIL: qwen3.8-27b: engine 'oMLX' has no repo url"; exit 1; fi
    echo "QA PASSED"; exit 0 ;;
  test)
    # negative tests print validator FAIL lines from their fixtures - noise
    echo "  FAIL: m1: duplicate model ids in models.json: ['m1']"
    if [ "${TEST_RED:-0}" = "1" ]; then echo "  FAIL readme-render: trend cell"; echo "PASSED 9 | FAILED 1"; exit 1; fi
    echo "PASSED 10 | FAILED 0"; exit 0 ;;
  *) echo "PASSED 1 | FAILED 0"; exit 0 ;;
esac
"""


def run(red: int, rounds: int = 3, fix_exit: int = 0, test_red: int = 0, budget_burn: int = 0,
        vs_red: int = 0, require_findings: int = 0, fix_sleep: int = 0, cwd: Path | None = None,
        fix_timeout: int = 0, base_merge: str = "0", extra_env: dict | None = None):
    td = Path(tempfile.mkdtemp())
    rec = td / "make"
    rec.write_text(RECORDER)
    rec.chmod(0o755)
    (td / "red").write_text(str(red))
    (td / "calls.log").write_text("")
    env = dict(os.environ, MAKE=str(rec), FIX_ROUNDS=str(rounds),
               QA_REPORT=str(td / "qa-report.txt"), FIX_EXIT=str(fix_exit), TEST_RED=str(test_red),
               BUDGET_BURN=str(budget_burn), VS_RED=str(vs_red),
               REQUIRE_FINDINGS=str(require_findings), FIX_SLEEP=str(fix_sleep),
               # The base merge is OFF unless a test asks for it: the loop must never
               # touch the repository this suite runs in (issue #383), and the tests
               # that drive it build their own real git repository.
               FIX_BASE_MERGE=base_merge)
    if fix_timeout:
        env["HERMES_FIX_TIMEOUT"] = str(fix_timeout)
    if extra_env:
        env.update(extra_env)
    # cwd=td by default: the loop is hermetic — it must never run in (or merge into)
    # the checkout this suite was started from.
    p = subprocess.run(["bash", str(LOOP)], env=env, capture_output=True, text=True, timeout=120,
                       cwd=str(cwd or td))
    calls = [c.split("+")[0] for c in (td / "calls.log").read_text().split()]
    raw_calls = (td / "calls.log").read_text().split()
    report = (td / "qa-report.txt").read_text() if (td / "qa-report.txt").exists() else ""
    if cwd is None:
        shutil.rmtree(td)
    run.raw_calls = raw_calls
    run.tmpdir = td
    return p.returncode, calls, report, p.stdout


def test_green_on_entry():
    rc, calls, _, _ = run(red=0)
    check("green: exit 0", rc == 0, rc)
    check("green: no hermes fix call", "fix" not in calls, calls)
    # issue #172: the OpenSpec gate runs BEFORE the network-bound `validate` (so
    # a stale index / unticked task is reported without paying for link checks),
    # and the unit suite still runs last.
    check("green: checks fast -> slow (lint first, gates before validate, unit suite last)",
          calls == ["lint", "validate-search", "validate-mapped", "openspec-check",
                    "architecture-check", "validate", "test"], calls)


def test_fixed_in_round_one():
    rc, calls, _, out = run(red=1)
    check("round1: exit 0", rc == 0, out[-300:])
    check("round1: exactly one fix call", calls.count("fix") == 1, calls)
    check("round1: stops once green (2 check passes, no more fixes)", calls.count("validate") == 2, calls)


def test_red_forever_gives_up():
    rc, calls, report, out = run(red=99, rounds=3)
    check("red: exit 1", rc == 1, rc)
    check("red: capped at FIX_ROUNDS fix calls", calls.count("fix") == 3, calls)
    check("red: final re-check after the last fix", calls.count("validate") == 4, calls)
    check("red: report holds the real failure line", "engine 'oMLX' has no repo url" in report, report[:200])
    check("red: report marks which check failed", "=== make validate: FAILED ===" in report, report[:300])
    check("red: summary printed for the log", "manual review" in out, out[-300:])


def test_fix_crash_does_not_abort_loop():
    rc, calls, _, _ = run(red=1, fix_exit=2)
    check("crash: a non-zero make fix does not abort the loop", rc == 0 and calls.count("validate") == 2, calls)


def test_stops_at_first_red_and_skips_unit_suite():
    rc, calls, report, out = run(red=99, rounds=1)
    check("speed: 'make test' never runs while a validate check is red", "test" not in calls, calls)
    check("speed: nothing after the first red check in a round",
          calls[:6] == ["lint", "validate-search", "validate-mapped", "openspec-check",
                        "architecture-check", "validate"]
          and calls[6] == "fix", calls)


def test_findings_check_only_for_implementation_runs():
    """`make findings-check` is demanded of an IMPLEMENTATION run, not of fix-bot.

    Issue #172 (rule 6g): issue-bot sets REQUIRE_FINDINGS=1, so a run that skipped
    the analysis is RED and Hermes has to write it; fix-bot repairs a data PR
    nobody implemented by hand, so it must NOT demand a findings file that never
    had a reason to exist.
    """
    # Given a green fix-bot run (no implementation flag)
    rc, calls, _, _ = run(red=0)

    # Then  the data-repair loop never demands the analysis file
    check("findings: fix-bot's loop does not run findings-check", "findings-check" not in calls, calls)

    # Given an implementation run (issue-bot sets REQUIRE_FINDINGS=1)
    rc, calls, _, _ = run(red=0, require_findings=1)

    # Then  the analysis check runs as part of the loop
    check("findings: an implementation run runs findings-check before validate",
          "findings-check" in calls and calls.index("findings-check") < calls.index("validate"), calls)


def test_unit_suite_failure_is_red():
    rc, calls, report, out = run(red=0, rounds=1, test_red=1)
    check("suite: validates green but a unit test red -> loop is red", rc == 1, out[-200:])
    check("suite: the unit-test failure reaches the summary", "FAIL readme-render: trend cell" in out, out[-300:])


def test_summary_drops_fixture_noise():
    rc, calls, report, out = run(red=0, rounds=1, test_red=1)
    summary = out.split("still RED", 1)[-1]
    check("summary: negative-test fixture lines ('FAIL: m1 ...') are not reported",
          "FAIL: m1" not in summary, summary[-300:])
    check("summary: the failing suite total is reported", "PASSED 9 | FAILED 1" in summary, summary[-300:])
    rc, calls, report, out = run(red=99, rounds=1)
    check("summary: real validator failures are reported",
          "engine 'oMLX' has no repo url" in out.split("still RED", 1)[-1], out[-300:])


def test_budget_burn_retries_with_reasoning_off():
    rc, calls, _, out = run(red=1, rounds=3, budget_burn=1)
    raw = run.raw_calls
    check("budget: retried in the same round with HERMES_FIX_REASONING=none",
          "fix+HERMES_FIX_REASONING=none" in raw, raw)
    check("budget: the retry fixes it in round 1 (one round, then green)",
          rc == 0 and calls.count("validate") == 2, raw)
    check("budget: the retry is announced in the log", "retrying this round with HERMES_FIX_REASONING=none" in out,
          out[-300:])
    rc, calls, _, out = run(red=1, rounds=3, fix_exit=2)
    check("budget: an ordinary make-fix failure is NOT retried with reasoning off",
          not any("HERMES_FIX_REASONING=none" in c for c in run.raw_calls), run.raw_calls)


def test_report_holds_only_the_failing_check():
    rc, calls, report, out = run(red=99, rounds=1)
    check("report: names the checks that passed",
          "checks passed: lint validate-search validate-mapped openspec-check architecture-check" in report,
          report[:200])
    check("report: no output from passing checks (their fixture noise)", "FAIL: m1" not in report, report[:300])
    rc, calls, report, out = run(red=0, rounds=1, vs_red=1)
    summary = out.split("still RED", 1)[-1]
    check("summary: a unit-suite failure inside validate-search is reported",
          "FAIL mapping: real regression" in summary, summary[-300:])
    check("summary: fixture lines inside validate-search are dropped", "FAIL: m1" not in summary, summary[-300:])


def test_round_cap_respected():
    rc, calls, _, _ = run(red=99, rounds=1)
    check("cap: FIX_ROUNDS=1 -> one fix call", calls.count("fix") == 1 and rc == 1, calls)


def test_a_hung_round_is_bounded_by_the_loop():
    """Issue #383, measured on run 39124432576: one Hermes round ran 1 h 58 m and was
    killed by the JOB's `timeout-minutes: 120`, so the loop's own failure path never
    ran and the PR was left with nothing. Every round is bounded, reported, and can
    never cost the job's budget."""
    rc, calls, report, out = run(red=99, rounds=3, fix_sleep=5, fix_timeout=1)
    check("bound: the round is aborted by the LOOP, not by the job limit",
          "TIMED OUT after 1s" in out, out[-500:])
    check("bound: the timeout is recorded in qa-report.txt (what the PR comment shows)",
          "TIMED OUT after 1s" in report, report[-300:])
    check("bound: the loop still ends through its OWN path (red, capped rounds)",
          rc == 1 and calls.count("fix") == 3, f"rc={rc} {calls}")


def test_scratch_notes_stay_out_of_the_tree():
    """Issue #390: the loop records a timed-out / no-progress round in a notes file it
    folds into the report. Writing it as `$REPORT.notes` put it in the repo root, and a
    bot's `git add -A` committed an empty `qa-report.txt.notes` into PR #387. The notes
    are the loop's own scratch: they must never appear next to the report."""
    if not shutil.which("bash"):
        print("  SKIP notes: bash not available")
        return
    td = Path(tempfile.mkdtemp())
    try:
        rec = td / "make"
        rec.write_text(RECORDER)
        rec.chmod(0o755)
        (td / "red").write_text("99")
        (td / "calls.log").write_text("")
        # QA_REPORT relative to the loop's cwd is the production shape (`qa-report.txt`
        # in the repo root), and a timed-out round is what makes a NON-empty note.
        env = dict(os.environ, MAKE=str(rec), FIX_ROUNDS="1", QA_REPORT="qa-report.txt",
                   FIX_BASE_MERGE="0", HERMES_FIX_TIMEOUT="1", FIX_SLEEP="5")
        subprocess.run(["bash", str(LOOP)], cwd=str(td), env=env, capture_output=True,
                       text=True, timeout=120)
        report = (td / "qa-report.txt").read_text() if (td / "qa-report.txt").exists() else ""
        leftovers = sorted(p.name for p in td.iterdir() if p.name.endswith(".notes"))
        check("notes: no scratch file is created beside the report (issue #390)",
              leftovers == [], leftovers)
        check("notes: the timeout still reaches qa-report.txt through the scratch file",
              "TIMED OUT after 1s" in report, report[-300:])
    finally:
        shutil.rmtree(td, ignore_errors=True)


def test_no_scratch_report_file_is_tracked():
    """Issue #390, follow-up: the notes fix stopped the loop CREATING the file, but a
    file already tracked stays tracked — PR #387 had merged the 0-byte
    `qa-report.txt.notes` into master. Nothing may be tracked in the loop's scratch
    class (the report, its siblings, the PR comment body)."""
    if not shutil.which("git") or not (ROOT / ".git").exists():
        print("  SKIP tracked scratch: not a git checkout")
        return
    out = subprocess.run(
        ["git", "ls-files", "--", "qa-report.txt", "qa-report.txt.*", "comment.md"],
        cwd=str(ROOT), capture_output=True, text=True)
    tracked = [p for p in out.stdout.split() if p]
    check("scratch: no qa-report*/comment.md scratch file is tracked (issue #390)",
          tracked == [], tracked)


def test_base_merge_is_skipped_outside_a_checkout():
    """The base merge must be a no-op outside a git checkout (issue #383): it can
    never fail the loop, and the checks still run."""
    rc, calls, _, out = run(red=0, base_merge="1")
    check("base: outside a git checkout the merge is skipped loudly",
          "not a git checkout — skipping the base merge" in out, out[-400:])
    check("base: the checks still run", bool(calls) and calls[0] == "lint", calls)
    check("base: and the loop is still green", rc == 0, rc)


def test_the_base_is_merged_before_any_llm_round():
    """Issue #383: a red refresh PR is usually red because the BASE moved — a
    contract, a prompt, an ingest rule — and no repair of the branch's own tree can
    fix a rule the branch does not have. Real `git` in a real repository (rule 6m)."""
    if not shutil.which("git"):
        print("  SKIP base merge: git not installed")
        return
    root = Path(tempfile.mkdtemp())
    origin, work, clone = root / "origin.git", root / "work", root / "clone"
    ident = (["git", "config", "user.email", "t@example.com"], ["git", "config", "user.name", "t"])

    def git(*args, cwd):
        subprocess.run(["git", *args], cwd=str(cwd), check=True, capture_output=True)

    subprocess.run(["git", "init", "-q", "--bare", str(origin)], check=True)
    subprocess.run(["git", "init", "-q", str(work)], check=True)
    for c in ident:
        git(*c[1:], cwd=work)
    (work / "base.txt").write_text("base\n")
    git("add", ".", cwd=work)
    git("commit", "-qm", "base", cwd=work)
    git("branch", "-M", "master", cwd=work)
    git("remote", "add", "origin", str(origin), cwd=work)
    git("push", "-q", "origin", "master", cwd=work)
    subprocess.run(["git", "clone", "-q", str(origin), str(clone)], check=True)
    for c in ident:
        git(*c[1:], cwd=clone)

    # The BASE moves AFTER the branch was cut: the fix the branch does not have.
    (work / "the-base-fix.txt").write_text("fixed on the base\n")
    git("add", ".", cwd=work)
    git("commit", "-qm", "the base fix", cwd=work)
    git("push", "-q", "origin", "master", cwd=work)

    rc, calls, _, out = run(red=0, base_merge="1", cwd=clone)
    merged = subprocess.run(["git", "log", "--oneline"], cwd=str(clone),
                            capture_output=True, text=True).stdout
    check("base: the branch is brought up to the base BEFORE any LLM round",
          "the base fix" in merged, merged[:200])
    check("base: the merge is reported in the log",
          "merging the base in BEFORE any LLM round" in out, out[-500:])
    check("base: a failure the base already fixed costs ZERO LLM rounds",
          calls.count("fix") == 0, calls)
    check("base: the loop is green afterwards", rc == 0, rc)
    shutil.rmtree(root, ignore_errors=True)


def test_a_round_that_changes_nothing_stops_the_loop():
    """Issue #383: a round that leaves the failure byte-identical AND the tree
    untouched is a fix that did not stick — it must not buy the remaining rounds.
    Real `git` in a real repository, because the check is only asked in a checkout."""
    if not shutil.which("git"):
        print("  SKIP no-progress: git not installed")
        return
    repo = Path(tempfile.mkdtemp())
    subprocess.run(["git", "init", "-q", str(repo)], check=True)
    for c in (("user.email", "t@example.com"), ("user.name", "t")):
        subprocess.run(["git", "config", *c], cwd=str(repo), check=True)
    (repo / "f.txt").write_text("x\n")
    subprocess.run(["git", "add", "."], cwd=str(repo), check=True)
    subprocess.run(["git", "commit", "-qm", "init"], cwd=str(repo), check=True)

    rc, calls, report, out = run(red=99, rounds=3, base_merge="0", cwd=repo)
    check("progress: the loop stops after the round that changed nothing",
          calls.count("fix") == 1, calls)
    check("progress: the log says why", "fixed nothing" in out, out[-500:])
    check("progress: the reason is recorded in qa-report.txt", "no progress" in report, report[-300:])
    check("progress: and the loop is red, not green", rc == 1, rc)
    shutil.rmtree(repo, ignore_errors=True)


def test_a_conflicting_base_merge_is_handed_to_a_round_and_aborted_if_hopeless():
    """Issue #475: a base that moved onto the SAME lines used to make the loop give up at
    once (`git merge --abort`), so the PR waited for a human. The conflict is now a REPAIR:
    the hunks go into the report the round reads, the round runs, and the merge is completed
    when the tree comes back clean — or aborted at the end, so nothing half-merged is pushed.
    Real `git` in a real repository (rule 6m)."""
    if not shutil.which("git") or not shutil.which("awk"):
        print("  SKIP conflict repair: git/awk not installed")
        return
    root = Path(tempfile.mkdtemp())
    origin, work, clone = root / "origin.git", root / "work", root / "clone"
    ident = (("user.email", "t@example.com"), ("user.name", "t"))

    def git(*args, cwd):
        subprocess.run(["git", *args], cwd=str(cwd), check=True, capture_output=True)

    subprocess.run(["git", "init", "-q", "--bare", str(origin)], check=True)
    subprocess.run(["git", "init", "-q", str(work)], check=True)
    for c in ident:
        git("config", *c, cwd=work)
    (work / "same-line.txt").write_text("base\n")
    git("add", ".", cwd=work)
    git("commit", "-qm", "base", cwd=work)
    git("branch", "-M", "master", cwd=work)
    git("remote", "add", "origin", str(origin), cwd=work)
    git("push", "-q", "origin", "master", cwd=work)
    subprocess.run(["git", "clone", "-q", str(origin), str(clone)], check=True)
    for c in ident:
        git("config", *c, cwd=clone)

    # The BRANCH edits the line…
    (clone / "same-line.txt").write_text("branch wins\n")
    git("commit", "-qam", "the branch edit", cwd=clone)
    # …and so does the BASE, on the same line: a guaranteed conflict.
    (work / "same-line.txt").write_text("base wins\n")
    git("commit", "-qam", "the base edit", cwd=work)
    git("push", "-q", "origin", "master", cwd=work)

    rc, calls, report, out = run(red=99, rounds=1, base_merge="1", cwd=clone)
    status = subprocess.run(["git", "status", "--porcelain"], cwd=str(clone),
                            capture_output=True, text=True).stdout
    head = subprocess.run(["git", "log", "--oneline", "-1"], cwd=str(clone),
                          capture_output=True, text=True).stdout

    check("conflict: the loop NAMES the conflicted path", "CONFLICTED in: same-line.txt" in out, out[-600:])
    check("conflict: a Hermes round is asked to resolve it", calls.count("fix") == 1, calls)
    check("conflict: the report carries the hunks the round must resolve",
          "<<<<<<<" in report and "same-line.txt" in report, report[-400:])
    check("conflict: the report says generated artifacts are regenerated, not hand-merged",
          "REGENERATED" in report, report[-400:])
    check("conflict: unresolved after the rounds, the merge is ABORTED",
          "aborted it" in out, out[-500:])
    check("conflict: nothing half-merged is left in the tree",
          "<<<<<<<" not in status and "UU" not in status, status)
    check("conflict: the branch's own commit is untouched", "the branch edit" in head, head)
    check("conflict: the loop stays red for a human", rc == 1, rc)
    shutil.rmtree(root, ignore_errors=True)


def main() -> int:
    if not shutil.which("bash"):
        print("SKIP: bash not available")
        return 0
    print("fix_loop.sh control flow")
    test_green_on_entry()
    test_fixed_in_round_one()
    test_red_forever_gives_up()
    test_fix_crash_does_not_abort_loop()
    test_round_cap_respected()
    test_stops_at_first_red_and_skips_unit_suite()
    test_findings_check_only_for_implementation_runs()
    test_unit_suite_failure_is_red()
    test_summary_drops_fixture_noise()
    test_budget_burn_retries_with_reasoning_off()
    test_report_holds_only_the_failing_check()
    test_a_hung_round_is_bounded_by_the_loop()
    test_scratch_notes_stay_out_of_the_tree()
    test_no_scratch_report_file_is_tracked()
    test_base_merge_is_skipped_outside_a_checkout()
    test_the_base_is_merged_before_any_llm_round()
    test_a_round_that_changes_nothing_stops_the_loop()
    test_a_conflicting_base_merge_is_handed_to_a_round_and_aborted_if_hopeless()
    print(f"\nPASSED {_PASS} | FAILED {_FAIL}")
    return 1 if _FAIL else 0


if __name__ == "__main__":
    raise SystemExit(main())
