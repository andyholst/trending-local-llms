#!/usr/bin/env python3
"""The refresh run's window is a real, parseable block on the artifacts a human opens (issue #199).

An in-flight refresh was invisible: four parallel searches run for ~12 minutes and only then does
`aggregate` open a PR, which carried no timestamps at all — so "which run wrote this, and when did
each leg start?" was answerable only from the Actions API, which a reviewer reading the PR page
cannot see.

These tests lock the three things that make the block worth having:

  1. it is composed from the REAL job timestamps — a recorded capture of an actual run renders
     exactly the expected block, and the numbers are the run's, not a wall clock's;
  2. its marker line is written by the SHARED helper, so the shared parser reads it back
     (the whole point of #197);
  3. it is wired where it must be — the `aggregate` PR body and the gap-issue body — and a run
     with NO new data fabricates no block at all.

Run: python3 tests/test_refresh_run_block.py   (wired into `make _test`)
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import bot_markers as bm  # noqa: E402
import refresh_run_block as rb  # noqa: E402

PASSED = 0
FAILED = 0

#: A REAL capture of the run that opened refresh PR #1's line of PRs: `gh api
#: repos/<o>/<r>/actions/runs/<id>` + `.../jobs`, trimmed to the fields the composer reads.
FIXTURE = ROOT / "tests" / "fixtures" / "refresh_run_jobs.json"


def check(name: str, ok: bool, detail: object = "") -> None:
    global PASSED, FAILED
    if ok:
        PASSED += 1
        print(f"  ok  {name}")
    else:
        FAILED += 1
        print(f"FAIL {name}  {detail}")


def rendered() -> str:
    """The block the composer prints for the recorded run."""
    payload = json.loads(FIXTURE.read_text())
    legs, aggregate, _ = rb.legs_and_aggregate(payload["jobs"])
    return rb.render(payload["run_started_at"], legs, aggregate,
                     payload["run_id"], payload["html_url"])


def test_the_real_run_renders_exactly_the_expected_block() -> None:
    """The block is the run's OWN timestamps, in the shape issue #199 specifies."""

    # Given  the recorded capture of a real refresh run
    payload = json.loads(FIXTURE.read_text())

    # When   the composer renders it
    block = rendered()

    # Then   the marker names the run and carries the run's start, not a clock reading now
    check("the marker line is the registered shape",
          f"<!-- refresh-bot-run: {payload['run_started_at']} run={payload['run_id']} -->" in block,
          block.splitlines()[0])
    # And    every leg's own start time is the one GitHub recorded for that job
    starts = {j["name"]: j["started_at"] for j in payload["jobs"]}
    check("each leg carries its own recorded start",
          all(f"{leg}={starts[f'search ({leg})']}" in block for leg in rb.LEGS),
          block.splitlines()[1])
    # And    the aggregate job's start and the run URL are there
    check("the aggregate start is the recorded one",
          f"aggregate={starts['aggregate']}" in block, block.splitlines()[1])
    check("the run URL is present", payload["html_url"] in block, block.splitlines()[2])


def test_the_shared_parser_reads_the_block() -> None:
    """The marker is written by the registry's own writer, so the registry's parser reads it."""

    # Given  a rendered block
    block = rendered()

    # When   the SHARED parser reads it (not a regex of this test's own)
    hit = bm.read_marker(block, "refresh-bot", "run")

    # Then   it resolves to the bot, the kind and the run
    check("parse_markers finds the refresh window", bool(bm.parse_markers(block)), block)
    check("read_marker resolves it", hit is not None and hit["run"] == "38802740520", hit)
    check("its timestamp parses as a time", bm.ts_of(block, "refresh-bot", "run") is not None, hit)


def test_legs_come_from_the_real_job_names() -> None:
    """A leg is matched by the job NAME the API returns, never by an index or a hardcoded order."""

    # Given  a job list whose legs are out of order and one backend is missing
    jobs = [
        {"name": "search (amd)", "started_at": "2026-10-15T20:33:50Z"},
        {"name": "search (nvidia)", "started_at": "2026-10-15T20:33:49Z"},
        {"name": "aggregate", "started_at": "2026-10-15T20:58:48Z"},
        {"name": "search (bogus)", "started_at": "2026-10-15T20:33:51Z"},
    ]

    # When   they are read
    legs, aggregate, _ = rb.legs_and_aggregate(jobs)

    # Then   the order in the list does not matter, a missing leg reads `unknown`, and a job
    #        that is not one of the four legs is not mistaken for one
    check("a leg is found by its name, not its position",
          legs.get("nvidia") == "2026-10-15T20:33:49Z" and legs.get("amd") == "2026-10-15T20:33:50Z", legs)
    check("a non-leg search job is not a leg", "bogus" not in legs, legs)
    check("a missing leg reads unknown, never invented",
          "metal=unknown" in rb.render("2026-10-15T20:32:13Z", legs, aggregate, "1", "u"),
          sorted(legs))


def test_a_run_we_cannot_read_is_loud() -> None:
    """A blocked or failed `gh` read must raise, never print a block with no numbers."""

    # Given  a `gh` on PATH that fails (the permitted external stand-in: a stub CLI)
    with tempfile.TemporaryDirectory() as td:
        stub = Path(td) / "gh"
        stub.write_text("#!/bin/sh\necho 'gh: API rate limit exceeded' >&2\nexit 1\n")
        stub.chmod(0o755)
        env = dict(os.environ, PATH=f"{td}:{os.environ['PATH']}")

        # When   the block is composed for a run whose read fails
        out = subprocess.run([sys.executable, "-c",
                              "import sys; sys.path.insert(0, 'scripts');"
                              "import refresh_run_block as r; print(r.current_block('o/r', '1'))"],
                             capture_output=True, text=True, env=env, cwd=ROOT)

        # Then   it exits non-zero and says why — no silent empty/clean block
        check("a failed read is loud, not an empty block",
              out.returncode != 0 and "rate limit" in (out.stderr + out.stdout), out.returncode)

    # And    with no run context at all (a hand run) the answer is empty, not invented
    with tempfile.TemporaryDirectory() as td:
        stub = Path(td) / "gh"
        stub.write_text("#!/bin/sh\necho '{}'\n")
        stub.chmod(0o755)
        env = {k: v for k, v in os.environ.items() if k not in ("GITHUB_RUN_ID", "GITHUB_REPOSITORY")}
        env["PATH"] = f"{td}:{env['PATH']}"
        out = subprocess.run([sys.executable, "-c",
                              "import sys; sys.path.insert(0, 'scripts');"
                              "import refresh_run_block as r; print(repr(r.current_block()))"],
                             capture_output=True, text=True, env=env, cwd=ROOT)
        check("no run context means no block (a local run has no run to describe)",
              out.returncode == 0 and "''" in out.stdout, out.stdout)


def test_the_workflow_stamps_the_pr_body_and_not_a_no_data_run() -> None:
    """`aggregate` composes the block into the PR body, and only on the path that opens one."""

    # Given  the refresh pipeline's PR step
    wf = yaml.safe_load((ROOT / ".github" / "workflows" / "refresh-bot.yml").read_text())
    if True in wf and "on" not in wf:
        wf["on"] = wf.pop(True)
    agg = wf["jobs"]["aggregate"]
    pr_step = next((s for s in agg["steps"] if s.get("id") == "pr"), {})
    run = pr_step.get("run", "")

    # Then   it composes the block through the make target and passes it as the PR body
    check("the PR step exists", bool(pr_step), [s.get("name") for s in agg["steps"]])
    check("it composes the block via make refresh-run-block", "make refresh-run-block" in run, run[:200])
    check("it passes the composed body to gh pr create", "--body-file" in run, run[-300:])
    check("it no longer inlines a hand-written body",
          '--body "' not in run, run[-300:])
    # And    the composition sits INSIDE the data-changed branch: the `--body-file` reference
    #        comes after the `else`, so a rebuild-only run with no new data never stamps one
    #        (no PR is created, so there is no artifact to stamp).
    #        (the block scalar is dedented, so the shell's own `else` starts the line)
    body_at = run.find("--body-file")
    else_m = re.search(r"^else\s*$", run, re.M)
    else_at = else_m.start() if else_m else -1
    check("the block is only composed on the PR path (after `else`)",
          else_at >= 0 and body_at > else_at, f"else={else_at} body={body_at}")


def test_the_gap_issue_carries_the_same_block() -> None:
    """An issue filed BY a refresh carries the block, from the same composer."""

    # Given  the gap filer
    src = (ROOT / "scripts" / "data_gap_analysis.py").read_text()

    # Then   it uses the one composer, and puts the block at the top of the body
    check("the gap filer imports the composer", "import refresh_run_block" in src, "")
    check("it embeds the current run's block", "refresh_run_block.current_block()" in src, "")
    check("the block goes at the TOP of the issue body",
          re.search(r"body = \[\*block\.splitlines\(\)", src) is not None, "")


def main() -> int:
    """Run every test in this file — a test defined but never called passes CI silently."""
    for test in (test_the_real_run_renders_exactly_the_expected_block,
                 test_the_shared_parser_reads_the_block,
                 test_legs_come_from_the_real_job_names,
                 test_a_run_we_cannot_read_is_loud,
                 test_the_workflow_stamps_the_pr_body_and_not_a_no_data_run,
                 test_the_gap_issue_carries_the_same_block):
        print(f"-- {test.__name__}")
        test()
    print(f"\nPASSED {PASSED} | FAILED {FAILED}")
    return 1 if FAILED else 0


if __name__ == "__main__":
    sys.exit(main())
