#!/usr/bin/env python3
"""Behavioural tests for the issue reviewer's deterministic core (issue #179).

Two scheduled bots share ONE queue of `data-gap-analysis` issues: `issue-bot`
implements one per hour (oldest first), the issue reviewer refines the ones no
implementer has started. They must never write the same issue at the same time,
so the reviewer refuses to touch an issue inside a window around an implementer
start — REVIEW_GAP_HOURS (3) before the sweep reaches it and the same 3 h after
it started.

These tests drive the REAL scripts (`scripts/issue_queue.py`,
`scripts/issue_review.py`). The `gh` CLI is the replaced EXTERNAL system — a stub
on PATH that records its argv and answers from control files — so the queue rule,
the window arithmetic, the pick, the TOCTOU guard and the marker writes are the
product's own code, unmocked.

Time is INJECTED (`--now` / `ISSUE_REVIEW_NOW`) in every case: a boundary test
that reads the wall clock cannot assert 2 h 59 m vs 3 h 01 m (precedent: the
`test_readme_generated_*` clock-independence guard, issue #88).

Wired into `make test` (rule 6d).
"""
from __future__ import annotations

import importlib.util
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
QUEUE = ROOT / "scripts" / "issue_queue.py"
REVIEW = ROOT / "scripts" / "issue_review.py"
BOT_WF = ROOT / ".github" / "workflows" / "issue-bot.yml"

# A fixed instant, 30 days BEFORE the wall clock: every case below is written
# relative to it, so an implementation that read `datetime.now()` would classify
# every fixture as ancient (window closed) and fail these tests.
NOW = "2026-09-14T12:00:00Z"

_PASS = 0
_FAIL = 0


def check(name, cond, detail=""):
    global _PASS, _FAIL
    if cond:
        _PASS += 1
        print(f"  ok  {name}")
    else:
        _FAIL += 1
        print(f"  FAIL {name}" + (f"  [{detail}]" if detail else ""))


def hours_ago(hours: float) -> str:
    import datetime as dt
    base = dt.datetime.fromisoformat(NOW.replace("Z", "+00:00"))
    return (base - dt.timedelta(hours=hours)).strftime("%Y-%m-%dT%H:%M:%SZ")


# The gh stub: records every argv, and answers the reads both scripts make from
# control files under $FAKE_GH_DIR. Comments written back are appended to
# comments-posted.jsonl so a test can assert what was posted.
_GH_STUB = '''#!/usr/bin/env python3
import json, os, sys
from pathlib import Path
D = Path(os.environ["FAKE_GH_DIR"])
args = sys.argv[1:]
with Path(os.environ["FAKE_GH_LOG"]).open("a") as fh:
    fh.write(json.dumps(args) + "\\n")

def fixture(name, default):
    p = D / name
    if not p.exists():
        return default
    text = p.read_text()
    if name.endswith(".txt"):
        return text
    return json.loads(text)

def out(value):
    print(value if isinstance(value, str) else json.dumps(value))

head = args[:2]
if head == ["issue", "list"]:
    out(fixture("issues.json", []))
elif head == ["issue", "comment"]:
    body = args[args.index("--body") + 1] if "--body" in args else ""
    with (D / "comments-posted.jsonl").open("a") as fh:
        fh.write(json.dumps({"issue": args[2], "body": body}) + "\\n")
elif head in (["issue", "edit"], ["label", "create"], ["pr", "create"]):
    pass
elif head == ["pr", "list"]:
    out(fixture("pulls.json", []))
elif head == ["run", "list"]:
    out(fixture("runs.json", []))
elif head == ["label", "list"]:
    out(fixture("labels.json", []))
elif head == ["repo", "view"]:
    out(fixture("repo.txt", "andyholst/trending-local-llms"))
elif head[:1] == ["api"]:
    url = args[1]
    if "/git/matching-refs/" in url:
        out(fixture("branches.json", []))
    elif "/comments?per_page=100" in url:
        number = url.split("/issues/")[1].split("/")[0]
        comments = fixture("comments.json", {}).get(number, [])
        out([{"createdAt": c["createdAt"], "body": c["body"]} for c in comments])
    elif "/commits/" in url:
        out(fixture("commit-date.txt", ""))
    else:
        number = url.rsplit("/", 1)[-1]
        out(fixture("bodies.json", {}).get(number, ""))
else:
    sys.exit(2)
'''


def env_for(td: Path, *, issues=None, branches=None, pulls=None, runs=None,
            comments=None, bodies=None, labels=None, paths=None) -> dict:
    """A PATH with the gh stub in front, plus the control files it reads."""
    td.mkdir(parents=True, exist_ok=True)
    bin_dir = td / "bin"
    bin_dir.mkdir(exist_ok=True)
    gh = bin_dir / "gh"
    gh.write_text(_GH_STUB, encoding="utf-8")
    gh.chmod(0o755)
    log = td / "calls.log"
    log.write_text("", encoding="utf-8")
    (td / "issues.json").write_text(json.dumps(issues if issues is not None else []))
    (td / "branches.json").write_text(json.dumps(branches if branches is not None else []))
    (td / "pulls.json").write_text(json.dumps(pulls if pulls is not None else []))
    (td / "runs.json").write_text(json.dumps(runs if runs is not None else []))
    (td / "comments.json").write_text(json.dumps(comments if comments is not None else {}))
    (td / "bodies.json").write_text(json.dumps(bodies if bodies is not None else {}))
    (td / "labels.json").write_text(json.dumps(labels if labels is not None else []))
    for name, text in (paths or {}).items():
        (td / name).write_text(text)
    return {
        **os.environ,
        "PATH": f"{bin_dir}{os.pathsep}{os.environ['PATH']}",
        "FAKE_GH_DIR": str(td),
        "FAKE_GH_LOG": str(log),
        "ISSUE_REVIEW_NOW": "",
    }


def run(script: Path, *args: str, env: dict):
    return subprocess.run([sys.executable, str(script), *args], env=env,
                          capture_output=True, text=True)


def parse(text: str) -> dict:
    """The machine-readable `key=value` lines a workflow parses with sed."""
    out = {}
    for line in text.splitlines():
        line = line.strip()
        if "=" in line and " " not in line:
            key, _, value = line.partition("=")
            out[key] = value
    return out


def candidate(number: int, created: str = "2026-01-01T00:00:00Z", labels=None) -> dict:
    return {"number": number, "createdAt": created,
            "labels": [{"name": n} for n in (labels or [])]}


def four_issues() -> list[dict]:
    """Four candidates in createdAt order: positions 0,1,2,3 (i.e. hours to start)."""
    return [candidate(163, "2026-01-01T00:00:00Z"), candidate(174, "2026-01-02T00:00:00Z"),
            candidate(175, "2026-01-03T00:00:00Z"), candidate(176, "2026-01-04T00:00:00Z")]


def test_the_real_issue_pick_prints_exactly_one_line():
    """Issue #578: the REAL `make issue-pick` must print ONE `issue=` line and nothing else.

    A step test that stubs `make` cannot prove this: the stub prints the value alone, which
    removes exactly the line the real recipe contributes. Measured in production (runs
    40190558547, 40194644167): `OUT=$(make issue-pick)` captured
    `python3 scripts/issue_queue.py --pick …` as its first line, so `PICK="${OUT#issue=}"`
    became that command plus the value and the step refused it as "not a number" — the sweep
    implemented nothing for two hours. So this test runs the recipe itself, with the `gh` stub
    on PATH (the EXTERNAL system), and asserts the shape the workflow's reader depends on.
    """

    # Given a takeable issue and a `gh` that answers from fixtures
    with tempfile.TemporaryDirectory() as td:
        env = env_for(Path(td), issues=four_issues())

        # When  the REAL target runs, exactly as the sweep runs it
        # `--no-print-directory`: a NESTED make (this test runs inside `make _test`, which exports
        # MAKEFLAGS) prints "make[1]: Entering directory …" on stdout, which is make's own banner
        # and not the recipe's value — the production caller runs `OUT=$(make issue-pick)` from a
        # shell STEP, where no such banner exists. CI measured it: the first run of this test saw
        # ['make[1]: Entering directory \'/workspace\'', 'issue=163', "make[1]: Leaving …"].
        proc = subprocess.run(["make", "--no-print-directory", "issue-pick"],
                              cwd=str(ROOT), env=env, capture_output=True, text=True)

    lines = [line for line in proc.stdout.splitlines() if line.strip()]
    # Then  stdout is ONE `issue=<n>` line — the value, not the command that produced it
    check("real make issue-pick: it succeeds", proc.returncode == 0,
          (proc.returncode, proc.stdout[-300:], proc.stderr[-300:]))
    check("real make issue-pick: stdout is exactly ONE line",
          len(lines) == 1, lines)
    check("real make issue-pick: the line is `issue=<number>` and nothing else",
          bool(lines) and re.fullmatch(r"issue=\d+", lines[0].strip()) is not None, lines)
    check("real make issue-pick: no line is the recipe's own echo (the #578 defect)",
          not any(line.strip().startswith(("python3", "make ", "sed ")) for line in lines), lines)
    check("real make issue-pick: the reasoning goes to stderr, never to the value's stream",
          "issue-queue" in proc.stderr, proc.stderr[-300:])


def test_the_queue_attributes_a_run_by_its_start_comment_not_its_title():
    """Issue #193: the in-flight backstop matched `f"#{n}" in displayTitle` — a field
    that cannot identify an issue. Measured on this repo: a scheduled run's
    displayTitle is `issue-bot`, an `issues` run's is the issue TITLE (which often
    carries no number). So the backstop never fired for a sweep, and fired by accident
    for a run the start comment already described. The start comment is the signal."""

    # Given an in-progress run whose displayTitle CONTAINS the issue number
    runs = [{"databaseId": 1, "status": "in_progress", "event": "issues",
             "createdAt": hours_ago(0.2), "displayTitle": "Implement #176 right now"}]

    # And   an issue with NO start comment
    with tempfile.TemporaryDirectory() as td:
        env = env_for(Path(td), issues=four_issues(), runs=runs)
        proc = run(QUEUE, "--repo", "o/r", "--now", NOW, env=env)
        calls = [json.loads(l) for l in (Path(td) / "calls.log").read_text().splitlines() if l.strip()]

    row = [l for l in proc.stdout.splitlines() if l.startswith("issue=176 ")]
    check("displayTitle: the row is emitted", len(row) == 1, proc.stdout)
    # Then  the title is not attribution: not started, window open
    check("displayTitle: a run whose TITLE mentions the issue does not mark it started",
          bool(row) and "started=0" in row[0], row[:1])
    check("displayTitle: and it is not reported as a run in flight",
          bool(row) and "reason=run-in-flight" not in row[0], row[:1])
    # And   the queue does not ask for a field it cannot use
    check("displayTitle: the queue no longer calls `gh run list`",
          not any(c[:2] == ["run", "list"] for c in calls), calls[:3])

    # Given a fresh START COMMENT, the same issue IS started (the real signal)
    with tempfile.TemporaryDirectory() as td:
        env = env_for(Path(td), issues=four_issues(), runs=runs,
                      comments={"176": [{"createdAt": hours_ago(0.1),
                                         "body": "<!-- issue-bot-start: " + hours_ago(0.1) + " -->"}]})
        proc = run(QUEUE, "--repo", "o/r", "--now", NOW, env=env)
    started = [l for l in proc.stdout.splitlines() if l.startswith("issue=176 ")]
    check("displayTitle: a fresh start comment still marks it started",
          bool(started) and "started=1" in started[0], started[:1])


def test_the_window_opens_and_closes_at_the_three_hour_boundary():
    """2 h 59 m after implementer activity DEFERS the issue; 3 h 01 m reviews it."""

    # Given the oldest three candidates are within the implementer's next 3 sweeps
    # and the fourth is 2 h 59 m past an implementer outcome comment
    for hours, expected in ((2.9833, "implementer-recent"), (3.0166, "closed")):
        with tempfile.TemporaryDirectory() as td:
            fixture_dir = Path(td)
            env = env_for(
                fixture_dir, issues=four_issues(),
                comments={"176": [{"createdAt": hours_ago(hours), "body": "issue-bot ran for this issue (one implementer per issue)."}]},
            )

            # When  the queue is built at the injected instant
            proc = run(QUEUE, "--repo", "o/r", "--now", NOW, env=env)

    # Then  only the 3 h 01 m case is reviewable, and the boundary is the gap
            row = [l for l in proc.stdout.splitlines() if l.startswith("issue=176 ")]
            check(f"boundary {hours:.4f} h: row emitted", len(row) == 1, proc.stdout)
            if row:
                check(f"boundary {hours:.4f} h: reason is {expected}",
                      f"reason={expected}" in row[0], row[0])
                check(f"boundary {hours:.4f} h: window is {'open' if expected != 'closed' else 'closed'}",
                      f"window={'open' if expected != 'closed' else 'closed'}" in row[0], row[0])


def test_the_next_three_sweeps_are_the_window_before_a_start():
    """`position < gap` is the 3 h before a start — the sweep takes one issue/hour."""

    # Given four candidates, none touched by an implementer
    with tempfile.TemporaryDirectory() as td:
        env = env_for(Path(td), issues=four_issues())

        # When  the queue is built
        proc = run(QUEUE, "--repo", "o/r", "--now", NOW, env=env)

    # Then  positions 0-2 are inside the window (the next 3 sweeps) and 3 is not
    check("next-sweep: issue 163 (position 0) is deferred", "issue=163 position=0" in proc.stdout
          and "reason=next-sweep" in proc.stdout, proc.stdout)
    check("next-sweep: issue 176 (position 3) is reviewable",
          "issue=176 position=3" in proc.stdout.replace("window=closed", "window=closed"), proc.stdout)
    rows = {line.split()[0]: line for line in proc.stdout.splitlines() if line.startswith("issue=")}
    check("next-sweep: 176 window is closed",
          "window=closed" in (rows.get("issue=176") or "window=open"), rows.get("issue=176") or "")


def test_a_fresh_start_comment_means_started_not_merely_next():
    """A start comment posted before `make implement-issue` marks a STARTED issue."""

    # Given an issue whose start comment is 20 minutes old
    with tempfile.TemporaryDirectory() as td:
        env = env_for(Path(td), issues=four_issues(),
                      comments={"176": [{"createdAt": hours_ago(0.33),
                                         "body": "<!-- issue-bot-start: " + hours_ago(0.33) + " -->"}]})

        # When  the queue is built
        proc = run(QUEUE, "--repo", "o/r", "--now", NOW, env=env)

    # Then  it is started with a run in flight, not "next sweep"
    row = [l for l in proc.stdout.splitlines() if l.startswith("issue=176 ")][0]
    check("start comment: started=1", "started=1" in row, row)
    check("start comment: reason=run-in-flight", "reason=run-in-flight" in row, row)


def test_pick_takes_the_oldest_issue_outside_the_window():
    """One issue per run, and it is the oldest REVIEWABLE one — not the head."""

    # Given only the 4th candidate is outside the window
    with tempfile.TemporaryDirectory() as td:
        env = env_for(Path(td), issues=four_issues())

        # When  the reviewer picks
        proc = run(REVIEW, "--pick", "--repo", "o/r", "--now", NOW, env=env)

    # Then  it takes 176, its body, and says why
    decision = parse(proc.stdout)
    check("pick: the head is deferred, the 4th is reviewed",
          decision.get("issue") == "176" and decision.get("action") == "review"
          and decision.get("path") == "body", proc.stdout)
    check("pick: the reason names the closed window",
          decision.get("reason") == "window-closed", proc.stdout)


def test_pick_replies_once_to_a_started_implementer_and_then_goes_quiet():
    """The window path: one bounded reply per window, never one per hour."""

    # Given a started issue with no reviewer reply yet
    started = {"176": [{"createdAt": hours_ago(0.5),
                        "body": "<!-- issue-bot-start: " + hours_ago(0.5) + " -->"}]}
    with tempfile.TemporaryDirectory() as td:
        env = env_for(Path(td), issues=four_issues(), comments=started)

        # When  the reviewer picks with every candidate inside a window
        proc = run(REVIEW, "--pick", "--repo", "o/r", "--now", NOW, env=env)

    # Then  it takes the reply path (no body edit)
    decision = parse(proc.stdout)
    check("window: a started issue is answered on the issue, not in the body",
          decision.get("action") == "window" and decision.get("path") == "window"
          and decision.get("issue") == "176", proc.stdout)

    # Given it already replied in this window
    replied = {"176": started["176"] + [{"createdAt": hours_ago(0.2),
                                         "body": "<!-- issue-review: window " + hours_ago(0.2) + " --> reminders"}]}
    with tempfile.TemporaryDirectory() as td:
        env = env_for(Path(td), issues=four_issues(), comments=replied)

        # When  it picks again in the same window
        proc = run(REVIEW, "--pick", "--repo", "o/r", "--now", NOW, env=env)

    # Then  it does nothing at all — no second reply, no churn
    decision = parse(proc.stdout)
    check("window: one reply per window",
          decision.get("action") == "none" and decision.get("reason") == "all-deferred", proc.stdout)


def _shipped_pick_step() -> str:
    """The reviewer workflow's OWN `Pick ONE issue` run block, as shipped."""
    import yaml
    wf = yaml.safe_load((ROOT / ".github" / "workflows" / "issue-review-bot.yml").read_text())
    for s in wf["jobs"]["pick"]["steps"]:
        if s.get("id") == "pick":
            return s["run"]
    raise AssertionError("the pick step is missing from issue-review-bot.yml")


def _run_pick_step(step: str, pick_stdout: str, td: Path) -> subprocess.CompletedProcess:
    """Run the shipped step with a stub `make` that prints the REAL pick output.

    The stub is the EXTERNAL system (the make target is exercised by the pick test
    above); the step's own parsing, validation and $GITHUB_OUTPUT write are the
    product code under test.
    """
    bin_dir = td / "step-bin"
    bin_dir.mkdir(parents=True, exist_ok=True)
    out_file = td / "pick.out"
    out_file.write_text(pick_stdout)
    stub = bin_dir / "make"
    stub.write_text(f'#!/bin/sh\ncat "{out_file}"\n')
    stub.chmod(0o755)
    gh_output = td / "github-output"
    gh_output.write_text("")
    env = {**os.environ, "PATH": f"{bin_dir}{os.pathsep}{os.environ['PATH']}",
           "GITHUB_OUTPUT": str(gh_output), "FORCED": "", "GH_TOKEN": "x", "REPO": "o/r"}
    proc = subprocess.run(["bash", "-e", "-c", step], env=env, cwd=td,
                          capture_output=True, text=True)
    proc.github_output = gh_output.read_text()  # type: ignore[attr-defined]
    return proc


def test_the_pick_output_the_workflow_parses_is_a_number():
    """Issue #344: the `issue=` line carries the NUMBER, and the shipped step reads it.

    Measured (run 39040689085): the diagnostics rode on the `issue=` line, so ISSUE
    became `266 position=-1 window=open reason=…` - `gh issue view` failed and the
    `always()` close died in argparse (`unrecognized arguments`).
    """

    # Given a four-candidate queue, exactly one of them reviewable
    with tempfile.TemporaryDirectory() as td:
        env = env_for(Path(td), issues=four_issues())

        # When  the REAL picker runs
        proc = run(REVIEW, "--pick", "--repo", "o/r", "--now", NOW, env=env)

    # Then  exactly one line starts with `issue=` and it is the number alone
    issue_lines = [l for l in proc.stdout.splitlines() if l.startswith("issue=")]
    check("pick shape: exactly ONE `issue=` line (diagnostics never ride on it)",
          len(issue_lines) == 1, proc.stdout)
    check("pick shape: the `issue=` value is the number, with no diagnostics",
          issue_lines and issue_lines[0] == "issue=176", issue_lines)
    check("pick shape: every candidate is reported on a `candidate=` line",
          sum(l.startswith("candidate=") for l in proc.stdout.splitlines()) == 4, proc.stdout)

    # When  the workflow's OWN shipped step parses that stdout
    with tempfile.TemporaryDirectory() as td:
        shipped = _run_pick_step(_shipped_pick_step(), proc.stdout, Path(td))

    # Then  $GITHUB_OUTPUT gets the number, and nothing else
    check("pick parse: the shipped step succeeds", shipped.returncode == 0,
          shipped.stdout + shipped.stderr)
    keyed = dict(l.split("=", 1) for l in shipped.github_output.splitlines() if "=" in l)
    check("pick parse: `issue=` is the number the pick decided",
          keyed.get("issue") == "176", shipped.github_output)
    check("pick parse: the value is numeric (never a tail)",
          keyed.get("issue", "").isdigit(), shipped.github_output)
    check("pick parse: action/path/reason survive the parse",
          (keyed.get("action"), keyed.get("path"), keyed.get("reason"))
          == ("review", "body", "window-closed"), shipped.github_output)

    # Given the PRE-FIX shape, whose diagnostics rode on the `issue=` line
    old_shape = "issue=266 position=-1 window=open reason=decided:agent:refined started=0\n" \
                "action=review\nissue=266\npath=body\nreason=window-closed\n"
    with tempfile.TemporaryDirectory() as td:
        legacy = _run_pick_step(_shipped_pick_step(), old_shape, Path(td))

    # Then  the step REFUSES it: a value carrying whitespace is a producer defect, and
    #       silently taking its first token (the old `awk '{print $1}'`) is the
    #       truncation issue #548 exists for. A refused pick never spends a job on a
    #       guessed number.
    check("pick parse: a whitespace-carrying value is refused loudly, never truncated",
          legacy.returncode != 0 and "carries whitespace" in (legacy.stdout + legacy.stderr),
          legacy.stdout + legacy.stderr + "|" + getattr(legacy, "github_output", ""))

    # Given a value that is not a number at all
    broken = "action=review\nissue=not-a-number\npath=body\nreason=window-closed\n"
    with tempfile.TemporaryDirectory() as td:
        refused = _run_pick_step(_shipped_pick_step(), broken, Path(td))

    # Then  the step fails LOUDLY instead of spending a job on it
    check("pick parse: a non-numeric issue is refused loudly",
          refused.returncode != 0 and "not an issue number" in (refused.stdout + refused.stderr),
          refused.stdout + refused.stderr)


def test_a_reviewer_target_refuses_a_non_numeric_issue():
    """The measured failure value must die in the target, naming the parse defect."""

    # Given the exact value run 39040689085 fed to `make review-issue-finish`
    bad = "266 position=-1 window=open reason=decided:agent:refined started=0"

    # When  the target runs
    proc = subprocess.run(["make", "-s", "review-issue-finish", f"ISSUE={bad}"],
                          cwd=ROOT, capture_output=True, text=True)

    # Then  it exits non-zero and says what the value must be
    check("make guard: a diagnostic-carrying ISSUE is refused",
          proc.returncode != 0, proc.stdout + proc.stderr)
    check("make guard: the message names the defect",
          "must be the issue NUMBER" in (proc.stdout + proc.stderr)
          and "issue #344" in (proc.stdout + proc.stderr), proc.stdout + proc.stderr)


def test_guard_blocks_the_write_when_the_implementer_starts_mid_review():
    """The TOCTOU re-check: a body rewrite is refused once the window opens."""

    # Given a candidate outside the window whose implementer starts 5 minutes ago
    with tempfile.TemporaryDirectory() as td:
        stopping = env_for(Path(td), issues=four_issues())

        # When  the reviewer re-checks before writing
        ok = run(REVIEW, "--guard", "176", "--for", "body", "--repo", "o/r", "--now", NOW, env=stopping)

    # Then  the write is allowed while the window is closed
    check("guard(body): allowed outside the window", ok.returncode == 0 and "guard=ok" in ok.stdout,
          f"rc={ok.returncode} {ok.stdout}{ok.stderr}")

    # Given the implementer posted its start comment while the review ran
    with tempfile.TemporaryDirectory() as td:
        started = env_for(Path(td), issues=four_issues(),
                          comments={"176": [{"createdAt": hours_ago(0.1),
                                             "body": "<!-- issue-bot-start: " + hours_ago(0.1) + " -->"}]})

        # When  the reviewer re-checks before writing
        blocked = run(REVIEW, "--guard", "176", "--for", "body", "--repo", "o/r", "--now", NOW, env=started)

    # Then  the write is refused and the reason is named
    check("guard(body): blocked once the implementer started",
          blocked.returncode != 0 and "guard=blocked reason=window-open" in blocked.stdout,
          f"rc={blocked.returncode} {blocked.stdout}")

    # And the reply path is refused once a reply already exists
    with tempfile.TemporaryDirectory() as td:
        replied = env_for(Path(td), issues=four_issues(),
                          comments={"176": [{"createdAt": hours_ago(0.1), "body": "<!-- issue-bot-start: " + hours_ago(0.1) + " -->"},
                                            {"createdAt": hours_ago(0.05), "body": "<!-- issue-review: window " + hours_ago(0.05) + " -->"}]})
        again = run(REVIEW, "--guard", "176", "--for", "window", "--repo", "o/r", "--now", NOW, env=replied)

    check("guard(window): blocked when the window was already answered",
          again.returncode != 0 and "already-replied" in again.stdout, again.stdout)


def test_mark_sets_the_label_and_never_writes_a_body_marker_for_the_window_path():
    """The marker the implementer defers to: a label plus one comment (body path)."""

    # Given a candidate outside the window
    with tempfile.TemporaryDirectory() as td:
        td_path = Path(td)
        env = env_for(td_path, issues=four_issues(), bodies={"176": "the body"})

        # When  the reviewer opens its window for a body rewrite
        proc = run(REVIEW, "--mark", "176", "--path", "body", "--repo", "o/r", "--now", NOW,
                   "--run", "testrun", env=env)

        # Then  the label is applied and the marker comment names the instant
        log = (td_path / "calls.log").read_text()
        posted = (td_path / "comments-posted.jsonl").read_text() if (td_path / "comments-posted.jsonl").exists() else ""
        check("mark(body): the chain label is applied",
              "review-in-progress" in log and '"issue", "edit"' in log, log)
        check("mark(body): the marker comment carries the instant and the run id",
              f"<!-- issue-review: {NOW} run=testrun -->" in posted, posted)
        check("mark(body): the body hash is printed for the write proof",
              "body_sha=" in proc.stdout, proc.stdout)

    # Given the reviewer instead opens the window to REPLY on the issue
    with tempfile.TemporaryDirectory() as td:
        td_path = Path(td)
        env = env_for(td_path, issues=four_issues(), bodies={"176": "the body"})

        # When  it marks the window path
        proc = run(REVIEW, "--mark", "176", "--path", "window", "--repo", "o/r", "--now", NOW, env=env)

        # Then  no marker comment is posted (the reply carries it) — only the label
        posted_exists = (td_path / "comments-posted.jsonl").exists()
        check("mark(window): no standalone marker comment is posted", not posted_exists, proc.stdout)
        check("mark(window): the instant to embed in the reply is printed",
              f"marker_iso={NOW}" in proc.stdout and "body_sha=" in proc.stdout, proc.stdout)


def test_body_hash_and_finish_are_the_write_proof_and_the_cleanup():
    """`--body-hash` proves the window path edited nothing; `--finish` closes it."""

    # Given a candidate with body text
    with tempfile.TemporaryDirectory() as td:
        td_path = Path(td)
        env = env_for(td_path, issues=four_issues(), bodies={"176": "the body"})

        # When  the body hash is read twice, and the window is closed
        first = run(REVIEW, "--body-hash", "176", "--repo", "o/r", "--now", NOW, env=env)
        second = run(REVIEW, "--body-hash", "176", "--repo", "o/r", "--now", NOW, env=env)
        finish = run(REVIEW, "--finish", "176", "--repo", "o/r", "--now", NOW, env=env)
        calls = (td_path / "calls.log").read_text()

    # Then  the hash is stable and the label removal is issued
    check("body-hash: stable and printed", "body_sha=" in first.stdout
          and first.stdout == second.stdout, first.stdout)
    check("finish: the label is removed", finish.returncode == 0
          and "review-in-progress" in calls, finish.stdout)


def test_a_stale_label_never_holds_the_queue_for_ever():
    """The label is advisory: only a timestamped marker can defer the implementer."""

    # Given an issue carrying `review-in-progress` but no reviewer marker (a
    # cancelled run's leftover — labels carry no timestamp)
    issues = four_issues()
    issues[3] = candidate(176, "2026-01-04T00:00:00Z", labels=["review-in-progress"])
    with tempfile.TemporaryDirectory() as td:
        env = env_for(Path(td), issues=issues)

        # When  both bots read the shared queue
        proc = run(QUEUE, "--repo", "o/r", "--now", NOW, env=env)

    # Then  the issue is NOT held: it is outside the window and reviewable
    row = [l for l in proc.stdout.splitlines() if l.startswith("issue=176 ")][0]
    check("liveness: a bare label does not defer the implementer",
          "impl_skip=0" in row and "position=3" in row and "window=closed" in row, row)


def test_the_reviewer_reads_the_one_queue_the_implementer_reads():
    """One queue, one window: no second copy of the pick rule (rule 6d)."""

    # Given the reviewer's script and the implementer's workflow
    review_src = REVIEW.read_text()
    _module()  # imports issue_queue — a hard dependency, asserted below
    bot = BOT_WF.read_text()

    # Then  the reviewer imports the shared queue and the bot's pick calls it
    check("queue: the reviewer imports issue_queue instead of re-implementing it",
          "import issue_queue as iq" in review_src, review_src[:400])
    step = _shipped_sweep_step()
    check("queue: the implementer's pick copies the producer's own line, never a sed of the row",
          "make issue-pick" in step and "sed -n 's/^issue=" not in step, step[:600])
    check("queue: the window gap is one variable, not a literal per bot",
          "REVIEW_GAP_HOURS := 3" in (ROOT / "Makefile").read_text()
          and "REVIEW_GAP_HOURS" in review_src, "")


def _module():
    spec = importlib.util.spec_from_file_location("issue_queue", QUEUE)
    assert spec and spec.loader, QUEUE
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_a_run_never_blocks_its_own_guard_but_another_run_does():
    """The marker carries the run id: the mark cannot block the run that wrote it."""

    # Given this run already marked the issue (its own marker, 5 minutes old)
    own = {"176": [{"createdAt": hours_ago(0.08),
                    "body": "<!-- issue-review: " + hours_ago(0.08) + " run=testrun -->"}]}
    with tempfile.TemporaryDirectory() as td:
        env = env_for(Path(td), issues=four_issues(), comments=own)

        # When  the same run re-checks before writing
        mine = run(REVIEW, "--guard", "176", "--for", "body", "--repo", "o/r", "--now", NOW,
                   "--run", "testrun", env=env)

    # Then  it may still write — its own mark is not a cooldown
    check("run id: a run is not blocked by its own marker",
          mine.returncode == 0 and "guard=ok" in mine.stdout, f"rc={mine.returncode} {mine.stdout}")

    # Given a DIFFERENT run marked the issue 5 minutes ago
    with tempfile.TemporaryDirectory() as td:
        env = env_for(Path(td), issues=four_issues(), comments=own)

        # When  this run (a different id) re-checks before writing
        other = run(REVIEW, "--guard", "176", "--for", "body", "--repo", "o/r", "--now", NOW,
                    "--run", "otherrun", env=env)

    # Then  it defers: another review is live on this issue
    check("run id: another run's marker defers this one",
          other.returncode != 0 and "reviewed-recently" in other.stdout, f"rc={other.returncode} {other.stdout}")

    # And the implementer defers to a review in flight (the label it sets)
    with tempfile.TemporaryDirectory() as td:
        env = env_for(Path(td), issues=four_issues(),
                      comments={"176": [{"createdAt": hours_ago(0.08),
                                         "body": "<!-- issue-review: " + hours_ago(0.08) + " run=otherrun -->"}]})

        # When  the queue is read as the implementer's pick reads it
        proc = run(QUEUE, "--repo", "o/r", "--now", NOW, "--run", "testrun", env=env)

    # Then  the marked issue is out of the implementer's pick order
    row = [l for l in proc.stdout.splitlines() if l.startswith("issue=176 ")][0]
    check("implementer: a reviewer's live window is skipped, not picked",
          "impl_skip=1" in row and "position=-1" in row and "reason=reviewer-working" in row, row)


def test_the_clock_is_injected_never_read_from_the_wall_clock():
    """Every fixture is 30 days stale: a wall-clock read would flip every verdict."""

    # Given fixtures written relative to an instant 30 days before the wall clock
    with tempfile.TemporaryDirectory() as td:
        env = env_for(Path(td), issues=four_issues(),
                      comments={"176": [{"createdAt": hours_ago(2.9833), "body": "issue-bot ran for this issue"}]})

        # When  the queue is built with the injected clock
        proc = run(QUEUE, "--repo", "o/r", "--now", NOW, env=env)

    # Then  the 2 h 59 m activity is still fresh — impossible on a wall-clock read
    row = [l for l in proc.stdout.splitlines() if l.startswith("issue=176 ")]
    check("clock: a 30-day-old fixture is fresh against the injected now",
          bool(row) and "reason=implementer-recent" in row[0], proc.stdout)


REVIEW_MARKER = "<!-- issue-review:"

def _verdict_fixture(td: Path, hours: float | None, label: str = "needs-refinement"):
    """Issues #163 (oldest, labelled + reviewed) and #174 (next), with the marker."""
    comments = {}
    if hours is not None:
        comments["163"] = [{"createdAt": hours_ago(hours),
                            "body": f"{REVIEW_MARKER} {hours_ago(hours)} run=1 -->\nReviewed: needs refinement."}]
    return env_for(td, issues=[candidate(163, labels=[label]), candidate(174)], comments=comments)


def test_a_reviewer_that_keeps_re_dating_a_verdict_cannot_hold_for_ever():
    """Issue #203: freshness is measured from the NEWEST reviewer marker, so a
    re-review every few hours kept a verdict fresh for ever and the issue was never
    picked. The hold now has a ceiling, measured from the OLDEST marker of the
    unbroken chain."""
    import datetime as _dt

    # Given a reviewer that re-dated the same verdict every 20 h for 200 h
    #   … with the NEWEST marker 6 h old, so it is not "the reviewer is working now"
    hours = [200, 180, 160, 140, 120, 100, 80, 60, 40, 20, 6]
    comments = {"163": [{"createdAt": hours_ago(h),
                         "body": f"<!-- issue-review: {hours_ago(h)} run={i} -->\nReviewed."}
                        for i, h in enumerate(hours, start=1)]}
    with tempfile.TemporaryDirectory() as td:
        fixture = Path(td)
        env = env_for(fixture, issues=[candidate(163, labels=["needs-refinement"])], comments=comments)
        proc = run(QUEUE, "--repo", "o/r", "--now", NOW, env=env)
    row = [l for l in proc.stdout.splitlines() if l.startswith("issue=163 ")]

    # Then  the hold has EXPIRED: it is reported, and the sweep may take the issue
    check("ceiling: the row is emitted", len(row) == 1, proc.stdout)
    check("ceiling: the hold is reported as expired", bool(row) and "verdict_expired=1" in row[0], row[:1])
    check("ceiling: it is no longer a verdict hold",
          bool(row) and "verdict_fresh=0" in row[0] and "impl_skip=0" in row[0], row[:1])
    check("ceiling: the reason says why", bool(row) and "reason=verdict-expired" in row[0], row[:1])
    check("ceiling: the issue is back in the pick order",
          bool(row) and "position=0" in row[0], row[:1])
    # … and it says how long the verdict had been held, from the CHAIN's first marker
    check("ceiling: the held duration is the whole chain, not the newest marker",
          bool(row) and "verdict_held_hours=200" in row[0], row[:1])
    check("ceiling: the log shouts that the hold expired",
          "EXPIRES" in proc.stderr and "200 h" in proc.stderr, proc.stderr[-400:])

    # Given a SHORT chain (40 h), the hold is still fresh and still holds
    short = {"163": [{"createdAt": hours_ago(h),
                      "body": f"<!-- issue-review: {hours_ago(h)} run={i} -->\nReviewed."}
                     for i, h in enumerate([40, 20, 1], start=1)]}
    with tempfile.TemporaryDirectory() as td:
        env = env_for(Path(td), issues=[candidate(163, labels=["needs-refinement"])], comments=short)
        proc = run(QUEUE, "--repo", "o/r", "--now", NOW, env=env)
    held = [l for l in proc.stdout.splitlines() if l.startswith("issue=163 ")]
    check("ceiling: a short chain still holds", bool(held) and "verdict_fresh=1" in held[0]
          and "impl_skip=1" in held[0], held[:1])
    check("ceiling: and it reports the 40 h it has been held",
          bool(held) and "verdict_held_hours=40" in held[0], held[:1])


def test_the_verdict_chain_breaks_across_a_stale_gap():
    """The chain is contiguous: a marker older than the TTL does not extend the hold."""
    import datetime as _dt
    mod = _module()
    ttl = 24
    now = _dt.datetime.fromisoformat(NOW.replace("Z", "+00:00"))

    # Given markers 2 h and 300 h old (a gap far wider than the TTL)
    start = mod.verdict_chain_start([now - _dt.timedelta(hours=2), now - _dt.timedelta(hours=300)], ttl)

    # Then  the chain is the newest link only
    check("chain: a stale gap does not extend the hold",
          start is not None and (now - start).total_seconds() // 3600 == 2, start)
    check("chain: no markers means no hold", mod.verdict_chain_start([], ttl) is None, "")


def test_a_fresh_verdict_holds_the_implementer():
    """A `needs-refinement` verdict younger than the TTL holds the sweep off that issue."""

    # Given the oldest issue carries a verdict label and a reviewer marker 2 h old
    with tempfile.TemporaryDirectory() as td:
        env = _verdict_fixture(Path(td), 2.0)

        # When  the shared queue is built at the injected instant
        proc = run(QUEUE, "--repo", "o/r", "--now", NOW, env=env)
        rows = {line.split()[0]: line for line in proc.stdout.splitlines() if line.startswith("issue=")}

    # Then  the held issue is out of the pick order and marked as such
    held = rows.get("issue=163", "")
    check("fresh verdict: the issue is held", "impl_skip=1" in held, held)
    check("fresh verdict: the reason names the verdict", "reason=verdict-fresh" in held, held)
    check("fresh verdict: it is out of the pick order", "position=-1" in held, held)
    check("fresh verdict: the verdict and its timestamp are reported",
          "verdict=needs-refinement" in held and f"verdict_since={hours_ago(2.0)}" in held, held)
    check("fresh verdict: verdict_fresh is 1", "verdict_fresh=1" in held, held)
    check("fresh verdict: the NEXT issue is what the sweep takes",
          rows.get("issue=174", "").split()[1] == "position=0", rows.get("issue=174", ""))


def test_a_stale_verdict_releases_the_issue():
    """The same label with a marker older than the TTL does NOT hold for ever."""

    # Given the verdict marker is 25 h old (a label left by a cancelled run)
    with tempfile.TemporaryDirectory() as td:
        env = _verdict_fixture(Path(td), 25.0)

        # When  the queue is built
        proc = run(QUEUE, "--repo", "o/r", "--now", NOW, env=env)
        held = [l for l in proc.stdout.splitlines() if l.startswith("issue=163 ")]

    # Then  the issue is back in the queue, with the verdict still reported
    check("stale verdict: the issue is in the pick order", held and "position=0" in held[0], str(held))
    check("stale verdict: it is not skipped", held and "impl_skip=0" in held[0], str(held))
    check("stale verdict: verdict_fresh is 0", held and "verdict_fresh=0" in held[0], str(held))
    check("stale verdict: the verdict is still visible", held and "verdict=needs-refinement" in held[0], str(held))


def test_a_label_without_any_reviewer_marker_never_holds():
    """A label with no reviewer marker at all has no timestamp, so it cannot hold."""

    # Given the label is present but the issue has no reviewer comment
    with tempfile.TemporaryDirectory() as td:
        env = _verdict_fixture(Path(td), None)

        # When  the queue is built
        proc = run(QUEUE, "--repo", "o/r", "--now", NOW, env=env)
        row = [l for l in proc.stdout.splitlines() if l.startswith("issue=163 ")]

    # Then  it is reported but never a hold
    check("label only: the verdict is reported", row and "verdict=needs-refinement" in row[0], str(row))
    check("label only: since is none", row and "verdict_since=none" in row[0], str(row))
    check("label only: never a hold", row and "impl_skip=0" in row[0] and "verdict_fresh=0" in row[0], str(row))



def test_a_decided_hold_is_announced_on_the_issue():
    """Issue #449: `agent:refined` / `agent:closed` is the implementer's own verdict, and the
    owner's ruling is that releasing it stays a HUMAN decision — a label carries no
    timestamp, so the queue must never expire it by itself. What it must NOT do is stay
    silent: the sweep announced only `verdict_fresh` holds, so four parked issues printed
    "no fresh verdict holds the queue — nothing to note" while nothing was ever implemented.
    """
    with tempfile.TemporaryDirectory() as td:
        fixture = Path(td)
        applied = hours_ago(5.0)
        env = env_for(
            fixture,
            issues=[candidate(163, labels=["agent:refined"]), candidate(174)],
            comments={"163": [{"createdAt": applied,
                               "body": f"<!-- issue-bot-verdict: refine {applied} -->\n"
                                       "Triaged: needs refinement."}]},
        )
        # When the queue is built and the note runs
        proc = run(QUEUE, "--repo", "o/r", "--now", NOW, env=env)
        rows = [l for l in proc.stdout.splitlines() if l.startswith("issue=163 ")]
        run(QUEUE, "--skip-note", "--repo", "o/r", "--now", NOW, env=env)
        posted = [json.loads(l) for l in (fixture / "comments-posted.jsonl").read_text().splitlines()]

    # Then  the hold is reported WITH its date, and announced as a human's call
    check("decided: the row reports the decision",
          bool(rows) and "decided=agent:refined" in rows[0], str(rows[:1]))
    check("decided: the row dates it from the verdict marker",
          bool(rows) and f"decided_since={applied}" in rows[0], str(rows[:1]))
    check("decided: exactly one note is posted", len(posted) == 1, str(posted))
    check("decided: it names the label", bool(posted) and "agent:refined" in posted[0]["body"], str(posted))
    check("decided: it says a HUMAN must release it",
          bool(posted) and "needs a HUMAN" in posted[0]["body"], str(posted))
    check("decided: it says the hold has no expiry",
          bool(posted) and "NO expiry" in posted[0]["body"], str(posted))
    check("decided: the marker carries the label and the marker's stamp",
          bool(posted) and "issue-bot-skip:" in posted[0]["body"]
          and "verdict=agent:refined" in posted[0]["body"]
          and f"since={applied}" in posted[0]["body"], str(posted))


def test_the_queue_reads_both_labels_as_one_oldest_first_list():
    """Issue #494: the sweep reads `data-gap-analysis` AND `tech-debt` — one issue per run, and
    the two labels compete on AGE, not on which list was read first."""

    # Given  one issue under each label (the stub answers every `issue list` with all of them,
    #        which is exactly the double-return a multi-label union has to dedupe)
    with tempfile.TemporaryDirectory() as td:
        fixture = Path(td)
        env = env_for(fixture, issues=[candidate(163, labels=["data-gap-analysis"]),
                                       candidate(174, labels=["tech-debt"])])
        proc = run(QUEUE, "--repo", "o/r", "--now", NOW, env=env)
        calls = [json.loads(l) for l in (fixture / "calls.log").read_text().splitlines()]

    # Then  both labels were asked for, once each
    asked = [c[c.index("--label") + 1] for c in calls if "--label" in c and len(c) > c.index("--label") + 1]
    check("queue: it asks for BOTH labels",
          sorted(asked) == ["data-gap-analysis", "tech-debt"], str(asked))
    rows = [line for line in proc.stdout.splitlines() if line.startswith("issue=")]
    # …and the result is ONE list: each issue once, one head, however many labels returned it
    check("queue: each issue appears once, even though both lists returned it",
          len({r.split()[0] for r in rows}) == len(rows) == 2, str(rows))
    check("queue: exactly one position=0 (ONE issue per run)",
          sum("position=0" in r for r in rows) == 1, str(rows))


def test_skip_note_is_posted_once_per_review_round():
    """`--skip-note` says it ON the issue, once per reviewer timestamp, and edits no label."""

    # Given a held issue with no skip note yet
    with tempfile.TemporaryDirectory() as td:
        fixture = Path(td)
        env = _verdict_fixture(fixture, 2.0)

        # When  the note runs
        first = run(QUEUE, "--skip-note", "--repo", "o/r", "--now", NOW, env=env)
        posted = [json.loads(l) for l in (fixture / "comments-posted.jsonl").read_text().splitlines()]
        calls = [json.loads(l) for l in (fixture / "calls.log").read_text().splitlines()]
        # … and the SAME round runs again (the note is now on the issue)
        comments = json.loads((fixture / "comments.json").read_text())
        comments.setdefault("163", []).append({"createdAt": NOW, "body": posted[0]["body"]})
        (fixture / "comments.json").write_text(json.dumps(comments))
        second = run(QUEUE, "--skip-note", "--repo", "o/r", "--now", NOW, env=env)
        calls_after = [json.loads(l) for l in (fixture / "calls.log").read_text().splitlines()]

    # Then  one comment carries the marker (verdict + the reviewer's timestamp)…
    check("skip note: exactly one comment posted", len(posted) == 1, str(posted))
    check("skip note: it is the held issue", posted and posted[0]["issue"] == "163", str(posted))
    check("skip note: the marker carries the verdict and its since", posted and
          "issue-bot-skip:" in posted[0]["body"] and "verdict=needs-refinement" in posted[0]["body"]
          and f"since={hours_ago(2.0)}" in posted[0]["body"], str(posted))
    check("skip note: it says nothing was implemented", posted and "Nothing was implemented" in posted[0]["body"],
          str(posted))
    # … and it is idempotent per round
    check("skip note: the second run posts nothing", "already noted" in second.stdout, second.stdout)
    check("skip note: still exactly one comment", len([c for c in calls_after if c[:2] == ["issue", "comment"]]) == 1,
          str(calls_after))



def test_the_skip_note_covers_every_held_issue():
    """Issue #204: the note used to describe `held[0]` — ONE issue — so with two fresh
    verdicts the second stayed silent, which is the "why is nobody working on this?"
    the comment exists to answer."""

    # Given TWO issues, each with its own fresh verdict label and reviewer marker
    marker = lambda h: {"createdAt": hours_ago(h), "body": f"{REVIEW_MARKER} {hours_ago(h)} run=1 -->\nReviewed."}
    comments = {"163": [marker(2.0)], "174": [marker(1.0)]}
    with tempfile.TemporaryDirectory() as td:
        fixture = Path(td)
        env = env_for(fixture, issues=[candidate(163, labels=["needs-refinement"]),
                                       candidate(174, labels=["needs-refinement"])],
                      comments=comments)

        # When  the sweep notes the holds
        first = run(QUEUE, "--skip-note", "--repo", "o/r", "--now", NOW, env=env)
        posted = [json.loads(l) for l in (fixture / "comments-posted.jsonl").read_text().splitlines()]

        # … and the SAME round runs again, with both notes now on their issues
        stored = json.loads((fixture / "comments.json").read_text())
        for c in posted:
            stored.setdefault(c["issue"], []).append({"createdAt": NOW, "body": c["body"]})
        (fixture / "comments.json").write_text(json.dumps(stored))
        second = run(QUEUE, "--skip-note", "--repo", "o/r", "--now", NOW, env=env)
        posted_again = (fixture / "comments-posted.jsonl").read_text().splitlines()

    # Then  BOTH held issues are noted, once each
    check("skip note: one comment per held issue", len(posted) == 2, str(posted))
    check("skip note: it covers both issues", sorted(c["issue"] for c in posted) == ["163", "174"],
          str([c["issue"] for c in posted]))
    check("skip note: each note carries its own verdict timestamp",
          any(f"since={hours_ago(2.0)}" in c["body"] for c in posted)
          and any(f"since={hours_ago(1.0)}" in c["body"] for c in posted), str(posted))
    check("skip note: the run reports what it did",
          "2 posted" in first.stdout and "2 held" in first.stdout, first.stdout)
    # … and the round is idempotent per issue
    check("skip note: a second run in the same round posts nothing new",
          len(posted_again) == 2 and "2 already noted" in second.stdout, second.stdout)

    # Given MORE held issues than the bound (MAX_SKIP_NOTES = 10)
    numbers = list(range(200, 212))
    with tempfile.TemporaryDirectory() as td:
        fixture = Path(td)
        env = env_for(fixture,
                      issues=[candidate(n, labels=["needs-refinement"]) for n in numbers],
                      comments={str(n): [marker(2.0)] for n in numbers})
        proc = run(QUEUE, "--skip-note", "--repo", "o/r", "--now", NOW, env=env)
        many = [json.loads(l) for l in (fixture / "comments-posted.jsonl").read_text().splitlines()]

    check("skip note: the walk is bounded", len(many) == 10, len(many))
    check("skip note: the bound is owned by the script, not the shell",
          "MAX_SKIP_NOTES" in (ROOT / "scripts" / "issue_queue.py").read_text()
          and "MAX_SKIP_NOTES = 10" in (ROOT / "scripts" / "issue_queue.py").read_text(), "")
    check("skip note: it says what it left for the next sweep",
          "more held issue(s) not noted in this sweep" in proc.stdout, proc.stdout[-300:])


def test_a_decided_issue_is_skipped_by_the_shared_queue():
    """Issue #210: once the implementer has SAID what an issue is, the sweep must
    not re-litigate the verdict every hour."""

    # Given the oldest issue carries the implementer's own verdict label
    for label in ("agent:refined", "agent:closed"):
        with tempfile.TemporaryDirectory() as td:
            env = env_for(Path(td), issues=[candidate(163, labels=[label]), candidate(174)])

            # When  the shared queue is built
            proc = run(QUEUE, "--repo", "o/r", "--now", NOW, env=env)
            row = [l for l in proc.stdout.splitlines() if l.startswith("issue=163 ")][0]
            nxt = [l for l in proc.stdout.splitlines() if l.startswith("issue=174 ")][0]

        # Then  the decided issue is held (out of the pick order) and the next one is taken
        check(f"{label}: the issue is skipped", "impl_skip=1" in row, row)
        check(f"{label}: the reason names the verdict", f"reason=decided:{label}" in row, row)
        check(f"{label}: it is out of the pick order", "position=-1" in row, row)
        check(f"{label}: the label is reported", f"decided={label}" in row, row)
        check(f"{label}: the NEXT issue is what the sweep takes",
              nxt.split()[1] == "position=0", nxt)

def test_the_implementer_never_edits_a_label_or_a_body_when_it_skips():
    """Skipping is a COMMENT: no label write, no body edit, ever."""

    # Given a held issue
    with tempfile.TemporaryDirectory() as td:
        fixture = Path(td)
        env = _verdict_fixture(fixture, 2.0)

        # When  the skip note runs
        run(QUEUE, "--skip-note", "--repo", "o/r", "--now", NOW, env=env)
        calls = [json.loads(l) for l in (fixture / "calls.log").read_text().splitlines()]

    # Then  the only write is a comment
    check("skip: no `issue edit`", not any(c[:2] == ["issue", "edit"] for c in calls), str(calls))
    check("skip: no label write", not any(c[0] == "label" for c in calls), str(calls))
    check("skip: the write is exactly one comment",
          [c[:2] for c in calls if c[:2] == ["issue", "comment"]] == [["issue", "comment"]], str(calls))


def _shipped_sweep_step() -> str:
    """The IMPLEMENTER workflow's OWN `Pick the oldest …` run block, as shipped."""
    import yaml
    wf = yaml.safe_load(BOT_WF.read_text())
    for s in wf["jobs"]["pick"]["steps"]:
        if s.get("id") == "pick":
            return s["run"]
    raise AssertionError("the pick step is missing from issue-bot.yml")


def test_the_sweep_reads_the_producers_own_pick_line():
    """Issues #547/#548: the sweep COPIES the producer's value instead of slicing its row.

    The workflow used to re-derive its pick with a `sed` expression of its own while the
    reviewer used `sed | awk '{print $1}'`: two hand-rolled readers of one producer, and
    only the reviewer's was driven by a test against the real output. Now the producer
    prints the one line the sweep needs, both readers take a value WHOLE, and a value
    outside the token shape is refused rather than truncated.
    """

    # Given the queue the REAL producer reads
    with tempfile.TemporaryDirectory() as td:
        env = env_for(Path(td), issues=four_issues())
        proc = run(QUEUE, "--pick", "--repo", "o/r", "--now", NOW, env=env)

    # Then  stdout is exactly ONE key=value line — there is nothing left to slice
    lines = [l for l in proc.stdout.splitlines() if l]
    check("sweep pick: the producer prints ONE key=value line",
          lines == ["issue=163"], proc.stdout)
    check("sweep pick: the value is a number", lines and lines[0][len("issue="):].isdigit(),
          proc.stdout)
    check("sweep pick: its reasoning goes to stderr, never onto the value's line",
          "[issue-queue] pick:" in proc.stderr, proc.stderr)

    # When the workflow's OWN shipped step reads that stdout
    with tempfile.TemporaryDirectory() as td:
        shipped = _run_pick_step(_shipped_sweep_step(), proc.stdout, Path(td))
    keyed = dict(l.split("=", 1)
                 for l in getattr(shipped, "github_output", "").splitlines() if "=" in l)
    check("sweep parse: the shipped step succeeds", shipped.returncode == 0,
          shipped.stdout + shipped.stderr)
    check("sweep parse: `issue=` is the number the producer decided",
          keyed.get("issue") == "163", getattr(shipped, "github_output", ""))

    # Given an EMPTY backlog (the producer prints an empty value, never a guess)
    with tempfile.TemporaryDirectory() as td:
        empty = _run_pick_step(_shipped_sweep_step(), "issue=\n", Path(td))
    empty_keys = dict(l.split("=", 1)
                      for l in getattr(empty, "github_output", "").splitlines() if "=" in l)
    check("sweep parse: an empty backlog is an empty issue=, and a green step",
          empty.returncode == 0 and empty_keys.get("issue") == "",
          empty.stdout + empty.stderr + getattr(empty, "github_output", ""))

    # Given a value that is not a number at all
    with tempfile.TemporaryDirectory() as td:
        broken = _run_pick_step(_shipped_sweep_step(), "issue=not-a-number\n", Path(td))
    check("sweep parse: a non-numeric pick is refused loudly",
          broken.returncode != 0 and "not a number" in (broken.stdout + broken.stderr),
          broken.stdout + broken.stderr)


def test_a_value_outside_the_token_shape_is_refused_by_the_producer():
    """Issue #548: a value that would be cut by a whitespace-splitting reader is REFUSED.

    The mechanism only holds if the producer refuses it: a reader that takes the value
    whole would otherwise carry `window open` into `$GITHUB_OUTPUT`, and one that splits
    would silently keep `window`.
    """
    iq = _module()

    # Given values a whitespace-splitting reader would truncate
    for bad in ("window open", "two\nlines", "tab\there"):
        try:
            iq.checked("reason", bad)
        except SystemExit as exc:
            check(f"producer refuses {bad!r}, naming the key",
                  "REFUSED" in str(exc) and "reason" in str(exc), str(exc))
        else:
            check(f"producer refuses {bad!r}", False, "no SystemExit")

    # Then  a legitimate token passes through unchanged
    check("producer passes a real token through",
          iq.checked("reason", "window-open:open") == "window-open:open"
          and iq.checked("issue", 163) == "163")

    # And   an enumerated key refuses a value outside its set
    try:
        iq.checked("action", "bogus", allowed=("review", "window", "none"))
    except SystemExit as exc:
        check("producer refuses an action outside its enum", "REFUSED" in str(exc), str(exc))
    else:
        check("producer refuses an action outside its enum", False, "no SystemExit")


def main() -> int:
    print("issue reviewer: one queue, one 3 h window, two bots (issue #179)")
    test_the_real_issue_pick_prints_exactly_one_line()
    test_the_queue_attributes_a_run_by_its_start_comment_not_its_title()
    test_the_window_opens_and_closes_at_the_three_hour_boundary()
    test_the_next_three_sweeps_are_the_window_before_a_start()
    test_a_fresh_start_comment_means_started_not_merely_next()
    test_pick_takes_the_oldest_issue_outside_the_window()
    test_a_run_never_blocks_its_own_guard_but_another_run_does()
    test_a_stale_label_never_holds_the_queue_for_ever()
    test_pick_replies_once_to_a_started_implementer_and_then_goes_quiet()
    test_the_pick_output_the_workflow_parses_is_a_number()
    test_the_sweep_reads_the_producers_own_pick_line()
    test_a_value_outside_the_token_shape_is_refused_by_the_producer()
    test_a_reviewer_target_refuses_a_non_numeric_issue()
    test_guard_blocks_the_write_when_the_implementer_starts_mid_review()
    test_mark_sets_the_label_and_never_writes_a_body_marker_for_the_window_path()
    test_body_hash_and_finish_are_the_write_proof_and_the_cleanup()
    test_the_reviewer_reads_the_one_queue_the_implementer_reads()
    test_the_clock_is_injected_never_read_from_the_wall_clock()
    test_a_reviewer_that_keeps_re_dating_a_verdict_cannot_hold_for_ever()
    test_the_verdict_chain_breaks_across_a_stale_gap()
    test_a_fresh_verdict_holds_the_implementer()
    test_a_stale_verdict_releases_the_issue()
    test_a_label_without_any_reviewer_marker_never_holds()
    test_a_decided_hold_is_announced_on_the_issue()
    test_the_queue_reads_both_labels_as_one_oldest_first_list()
    test_skip_note_is_posted_once_per_review_round()
    test_the_skip_note_covers_every_held_issue()
    test_the_implementer_never_edits_a_label_or_a_body_when_it_skips()
    test_a_decided_issue_is_skipped_by_the_shared_queue()
    print(f"\nPASSED {_PASS} | FAILED {_FAIL}")
    return 1 if _FAIL else 0


if __name__ == "__main__":
    raise SystemExit(main())
