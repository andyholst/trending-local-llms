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
                          comments={"176": [{"createdAt": hours_ago(0.1), "body": "<!-- issue-bot-start: x -->"},
                                            {"createdAt": hours_ago(0.05), "body": "<!-- issue-review: window x -->"}]})
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
    check("queue: the implementer's pick runs the same target",
          "make issue-queue" in bot, bot[:400])
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
                                         "body": "<!-- issue-review: x run=otherrun -->"}]})

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


def main() -> int:
    print("issue reviewer: one queue, one 3 h window, two bots (issue #179)")
    test_the_window_opens_and_closes_at_the_three_hour_boundary()
    test_the_next_three_sweeps_are_the_window_before_a_start()
    test_a_fresh_start_comment_means_started_not_merely_next()
    test_pick_takes_the_oldest_issue_outside_the_window()
    test_a_run_never_blocks_its_own_guard_but_another_run_does()
    test_a_stale_label_never_holds_the_queue_for_ever()
    test_pick_replies_once_to_a_started_implementer_and_then_goes_quiet()
    test_guard_blocks_the_write_when_the_implementer_starts_mid_review()
    test_mark_sets_the_label_and_never_writes_a_body_marker_for_the_window_path()
    test_body_hash_and_finish_are_the_write_proof_and_the_cleanup()
    test_the_reviewer_reads_the_one_queue_the_implementer_reads()
    test_the_clock_is_injected_never_read_from_the_wall_clock()
    test_a_fresh_verdict_holds_the_implementer()
    test_a_stale_verdict_releases_the_issue()
    test_a_label_without_any_reviewer_marker_never_holds()
    test_skip_note_is_posted_once_per_review_round()
    test_the_implementer_never_edits_a_label_or_a_body_when_it_skips()
    test_a_decided_issue_is_skipped_by_the_shared_queue()
    print(f"\nPASSED {_PASS} | FAILED {_FAIL}")
    return 1 if _FAIL else 0


if __name__ == "__main__":
    raise SystemExit(main())
