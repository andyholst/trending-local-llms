#!/usr/bin/env python3
"""Hermetic checks for the queued-run alarm (issue #252).

A job whose runner label matches nothing does not FAIL — GitHub leaves it `queued` forever, so
the run never concludes and every PR's checks sit at "pending". This locks the alarm's decision
(scripts/queued_run_alarm.py) and its wiring, with a fake `gh` on PATH (the product's own code
runs; only the GitHub API is a stand-in):

  1. a job queued longer than the threshold is reported; one under it is not;
  2. the report names the runner label and the age;
  3. `--comment` posts ONE comment per run and never a second (the marker dedup);
  4. the workflow guards first (owner/collaborator/bot, schedule bypass) and calls `make queued-alarm`;
  5. the make target is real and passes REPO/MINUTES/COMMENT through.

Run standalone: python3 tests/test_queued_run_alarm.py   or   make test
"""
import datetime as dt
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import queued_run_alarm as q  # noqa: E402

WF = ROOT / ".github" / "workflows"
_PASS = 0
_FAIL = 0


def check(name: str, cond: bool, detail: str = ""):
    global _PASS, _FAIL
    if cond:
        _PASS += 1
        print(f"  ok  {name}")
    else:
        _FAIL += 1
        print(f"  FAIL {name} {detail}")


def _fake_gh(runs: list[dict], jobs: dict[int, list[dict]], comments: dict[int, list[dict]]):
    """A `gh` on PATH that answers exactly the calls the alarm builds (records argv)."""
    td = Path(tempfile.mkdtemp())
    gh = td / "gh"
    gh.write_text(f"""#!/usr/bin/env bash
echo "$@" >> "{td}/calls"
args="$*"
case "$1 $2" in
  "run list")  cat "{td}/runs"; exit 0 ;;
  "run view")  id=$(echo "$args" | grep -oE '[0-9]+' | head -1); cat "{td}/jobs"; exit 0 ;;
esac
case "$args" in
  *"POST"*"/comments"*) echo "posted" >> "{td}/posted"; exit 0 ;;
  *"/actions/jobs/"*) echo '{{}}'; exit 0 ;;
  *"/issues/"*"/comments"*) cat "{td}/comments"; exit 0 ;;
esac
exit 0
""")
    gh.chmod(0o755)
    (td / "runs").write_text(__import__("json").dumps(runs))
    (td / "jobs").write_text(__import__("json").dumps({"jobs": next(iter(jobs.values()), [])}))
    (td / "comments").write_text(__import__("json").dumps(next(iter(comments.values()), [])))
    (td / "posted").write_text("")
    return td


def _iso(minutes_ago: float) -> str:
    t = dt.datetime.now(dt.timezone.utc) - dt.timedelta(minutes=minutes_ago)
    return t.strftime("%Y-%m-%dT%H:%M:%SZ")


def test_a_long_queued_job_is_reported():
    # Given a run whose job has been queued 45 min
    td = _fake_gh(
        [{"databaseId": 1, "workflowName": "issue-bot", "headBranch": "master", "url": "u"}],
        {1: [{"name": "unit", "status": "queued", "startedAt": _iso(45),
              "labels": ["ubuntu-latest"], "runnerName": ""}]},
        {},
    )
    os.environ["PATH"] = f"{td}{os.pathsep}{os.environ['PATH']}"
    try:
        # When the alarm reads the repo
        rows = q.stuck_jobs("o/r", 30)
        # Then the job is reported, with its label and age
        check("alarm: a job queued 45m is reported", len(rows) == 1, rows)
        check("alarm: the row names the label", rows and rows[0]["labels"] == "ubuntu-latest", rows)
        check("alarm: the age is ~45 min", rows and 44 <= rows[0]["minutes"] <= 46, rows)
        # And a shorter queue is not
        check("alarm: render names the age and label",
              "ubuntu-latest" in q.render(rows, 30) and "min" in q.render(rows, 30))
    finally:
        pass


def test_a_short_queue_is_not_reported():
    # Given a job queued only 5 min
    td = _fake_gh(
        [{"databaseId": 2, "workflowName": "w", "headBranch": "master", "url": "u"}],
        {2: [{"name": "unit", "status": "queued", "startedAt": _iso(5), "labels": ["x"]}]},
        {},
    )
    os.environ["PATH"] = f"{td}{os.pathsep}{os.environ['PATH']}"
    # When the alarm reads the repo with a 30 min threshold
    rows = q.stuck_jobs("o/r", 30)
    # Then nothing is reported, and the empty report says so
    check("alarm: a job queued 5m is not reported", rows == [], rows)
    check("alarm: the empty report says nothing is stuck",
          "no job has been queued longer" in q.render([], 30))


def test_comment_is_posted_once_per_run():
    # Given a run with no alarm comment yet
    td = _fake_gh([], {}, {9: []})
    os.environ["PATH"] = f"{td}{os.pathsep}{os.environ['PATH']}"
    # When comment_run posts one
    q.comment_run("o/r", 9, "body")
    first = (td / "posted").read_text().count("posted")
    # Then exactly one was posted
    check("alarm: one comment posted", first == 1, first)
    # And when the marker already exists, a repeat posts nothing
    (td / "comments").write_text(__import__("json").dumps([{"body": "_<!-- queued-run-alarm -->_"}]))
    q.comment_run("o/r", 9, "body")
    check("alarm: a repeat posts nothing (marker dedup)",
          (td / "posted").read_text().count("posted") == 1)


def test_the_workflow_guards_first_and_calls_the_make_target():
    # Given the alarm workflow
    text = (WF / "queued-alarm.yml").read_text()
    jobs = re.search(r"^jobs:\n(.*)", text, re.S | re.M).group(1)
    # Then the guard is the first job and it admits owner/collaborator/bot + schedule
    first_job = next(l for l in jobs.splitlines()
                     if l.strip() and not l.lstrip().startswith("#"))
    check("wf: guard is the first job", first_job.lstrip().startswith("guard:"), first_job[:40])
    check("wf: the guard admits the bot itself", 'github-actions[bot]' in text)
    check("wf: the guard lets a scheduled run through", '"schedule"' in text)
    check("wf: it calls make queued-alarm", "make queued-alarm REPO=" in text)
    check("wf: it never runs a repo script directly",
          not re.search(r"^\s*python3 scripts/", text, re.M))
    check("wf: it has its own concurrency group", "group: queued-alarm" in text)


def test_the_make_target_passes_its_variables_through():
    # When the make target is printed
    r = subprocess.run(["make", "-n", "queued-alarm", "REPO=o/r", "MINUTES=15", "COMMENT=1"],
                       cwd=ROOT, capture_output=True, text=True, timeout=60)
    out = r.stdout + r.stderr
    # Then it runs the script with REPO/MINUTES and the comment flag
    check("make: queued-alarm runs the script with REPO",
          "scripts/queued_run_alarm.py --repo" in out and "--minutes" in out, out[-200:])
    check("make: queued-alarm honours COMMENT", "--comment" in out, out[-200:])


def main() -> int:
    test_a_long_queued_job_is_reported()
    test_a_short_queue_is_not_reported()
    test_comment_is_posted_once_per_run()
    test_the_workflow_guards_first_and_calls_the_make_target()
    test_the_make_target_passes_its_variables_through()
    print(f"\nPASSED {_PASS} | FAILED {_FAIL}")
    return 1 if _FAIL else 0


if __name__ == "__main__":
    raise SystemExit(main())
