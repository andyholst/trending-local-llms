#!/usr/bin/env python3
"""The sweep's own outcome comment when a run dies before its verdict (the second half of #498).

A sweep that STARTED and then died posted the `issue-bot-start` marker and nothing else: the red
`implement` job lived only in the Actions tab (#488), and the issue kept showing an implementer in
flight for ever. These tests drive the REAL decision (`sweep_outcome.owed`) and the REAL CLI
against a stub `gh` on PATH — an external system, which is the only permitted stand-in. Nothing
here replaces the logic under test (rule 6m).

Run: python3 tests/test_sweep_outcome.py   (wired into `make _test` by the runner)
"""
from __future__ import annotations

import datetime as dt
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import bot_markers as bm  # noqa: E402
import sweep_outcome as S  # noqa: E402  (the module under test)

SCRIPT = ROOT / "scripts" / "sweep_outcome.py"
MAKEFILE = ROOT / "Makefile"
WORKFLOW = ROOT / ".github" / "workflows" / "issue-bot.yml"
RUN = "40194644167"
RUN_URL = f"https://github.com/andyholst/trending-local-llms/actions/runs/{RUN}"

#: A gh stub that answers the comment read and records what was posted (stdin included).
_GH_STUB = '''#!/usr/bin/env python3
import json, os, sys
from pathlib import Path
D = Path(os.environ["FAKE_GH_DIR"])
args = sys.argv[1:]
with (D / "calls.log").open("a") as fh:
    fh.write(json.dumps(args) + "\\n")
if (D / "fail-comments.txt").exists() and "comments" in " ".join(args):
    sys.stderr.write("HTTP 502\\n")
    sys.exit(1)
if args[:2] == ["issue", "comment"]:
    if "--body-file" in args and args[args.index("--body-file") + 1] == "-":
        body = sys.stdin.read()
    else:
        body = args[args.index("--body") + 1] if "--body" in args else ""
    with (D / "posted.jsonl").open("a") as fh:
        fh.write(json.dumps({"issue": args[2], "body": body}) + "\\n")
    print("https://github.com/x/y/issues/1#issuecomment-1")
    sys.exit(0)
if args[:1] == ["api"] and "/comments" in args[1]:
    print((D / "comments.json").read_text())
    sys.exit(0)
sys.exit(2)
'''

passed = failed = 0


def check(name: str, ok: bool, detail: object = "") -> None:
    global passed, failed
    if ok:
        passed += 1
        print(f"  ok  {name}")
    else:
        failed += 1
        print(f"  FAIL {name}  [{detail}]")


def env_for(td: Path, comments: list[dict] | None = None, fail: bool = False) -> dict:
    td.mkdir(parents=True, exist_ok=True)
    bin_dir = td / "bin"
    bin_dir.mkdir(exist_ok=True)
    gh = bin_dir / "gh"
    gh.write_text(_GH_STUB, encoding="utf-8")
    gh.chmod(0o755)
    (td / "calls.log").write_text("")
    (td / "comments.json").write_text(json.dumps(comments or []))
    if fail:
        (td / "fail-comments.txt").write_text("1")
    return {**os.environ, "PATH": f"{bin_dir}{os.pathsep}{os.environ['PATH']}",
            "FAKE_GH_DIR": str(td)}


def run(args: list[str], env: dict) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(SCRIPT), *args], env=env,
                          capture_output=True, text=True)


def posted(td: Path) -> list[dict]:
    path = td / "posted.jsonl"
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def test_the_decision_names_every_refusal() -> None:
    """The decision matrix: only `implemented, not closed, no verdict` owes a comment.

    Each refusal NAMES its reason — a silent skip and a skip for the wrong reason look the same in
    a log, and the second one is how the gap this closes stayed invisible.
    """
    print("sweep outcome: the decision matrix")
    cases = [
        # (implement, closed, verdict)                 -> owe?
        ((False, False, ""), False),
        ((True, True, ""), False),
        ((True, False, "implement"), False),
        ((True, False, "refine"), False),
        ((True, False, "close"), False),
        ((True, False, ""), True),
    ]
    for (implement, closed, verdict), want in cases:
        got, why = S.owed(implement=implement, closed=closed, verdict=verdict)
        check(f"owed(implement={implement}, closed={closed}, verdict={verdict!r}) is {want}",
              got is want and bool(why), why)


def test_the_body_carries_the_registered_marker() -> None:
    """The body starts with the marker REGISTERED in `scripts/bot_markers.py`, never a literal."""
    print("sweep outcome: the comment body")
    marker = bm.start_marker("issue-bot", dt.datetime(2026, 10, 28, 12, 0, 0, tzinfo=dt.timezone.utc),
                             RUN, kind="outcome")
    body = S.comment_body(issue="498", marker=marker, run_url=RUN_URL,
                          branch="ci/data-gap-498-slug",
                          stages={"resolve": "success", "implement": "failure",
                                  "verdict": "skipped"})
    parse = bm.parse_markers(body)
    check("the body carries the registered outcome marker",
          any(m["bot"] == "issue-bot" and m["kind"] == "outcome" for m in parse), parse)
    check("the marker carries this run's id",
          any(m.get("run") == RUN for m in parse), parse)
    check("the marker's name comes from the registry, never a literal here",
          bm.marker_name("issue-bot", "outcome") in body, bm.marker_name("issue-bot", "outcome"))
    check("the body names the run and the branch",
          RUN_URL in body and "ci/data-gap-498-slug" in body)
    check("the body names the stages, including the one that did not run",
          "implement=failure" in body and "verdict=skipped" in body, body)
    check("the body says nothing was committed/pushed/opened",
          "Nothing was committed, pushed or opened" in body)


def test_a_second_post_for_the_same_run_writes_nothing() -> None:
    """`--post` is ONCE PER RUN: its own marker (or already-fixed notice) suppresses a re-run,
    an EARLIER run's comment never does."""
    print("sweep outcome: the CLI, and once per run")
    with tempfile.TemporaryDirectory() as raw:
        td = Path(raw)
        env = env_for(td)
        args = ["--repo", "o/r", "--issue", "498", "--run-id", RUN, "--run-url", RUN_URL,
                "--branch", "b", "--stages", "resolve=success implement=failure verdict=skipped",
                "--now", "2026-10-28T12:00:00Z"]
        dry = run(args, env)
        check("a dry run exits 0", dry.returncode == 0, dry.stderr)
        check("a dry run prints the marker and read nothing from gh",
              bm.marker_name("issue-bot", "outcome") in dry.stdout
              and not (td / "calls.log").read_text().strip(), dry.stdout)

        first = run(args + ["--post"], env)
        calls = [json.loads(line) for line in (td / "calls.log").read_text().splitlines() if line]
        one = posted(td)
        check("--post exits 0", first.returncode == 0, first.stderr)
        check("--post writes exactly ONE comment", len(one) == 1, one)
        check("it posts with `gh issue comment <n> --body-file -`",
              any(c[:2] == ["issue", "comment"] and c[2] == "498" and "-" in c for c in calls), calls)
        check("the posted body is the composed one and carries the run id",
              one and f"run={RUN}" in one[0]["body"], one)

        # same run again, now with its own comment in the issue thread -> nothing
        again = run(args + ["--post"], env_for(td, comments=[{"createdAt": "2026-10-28T12:00:05Z",
                                                             "body": one[0]["body"]}]))
        check("a re-run of the same run id posts nothing", again.returncode == 0
              and "no duplicate" in again.stdout, again.stdout)
        check("…and it posted nothing", len(posted(td)) == 1, posted(td))

        # an EARLIER run's comment must not suppress this run
        earlier_marker = bm.start_marker(
            "issue-bot", dt.datetime(
                2026, 10, 28, 9, 0, 0, tzinfo=dt.timezone.utc),
            "39026771566", kind="outcome")
        later = run(args + ["--post"], env_for(td, comments=[
            {"createdAt": "2026-10-28T09:00:05Z",
             "body": f"{earlier_marker}\n\nThe sweep stopped before it could report an outcome."}]))
        check("an earlier run's outcome comment does not suppress this one",
              later.returncode == 0 and len(posted(td)) == 2, later.stdout)

        # the already-fixed notice for THIS run is an outcome too
        fixed = run(args + ["--post"], env_for(td, comments=[
            {"createdAt": "2026-10-28T12:01:00Z",
             "body": f"<!-- {bm.marker_name('issue-bot', 'already_fixed')}: {RUN} -->\n\nclosed"}]))
        check("the already-fixed notice for this run suppresses it",
              fixed.returncode == 0 and "already-fixed" in fixed.stdout
              and len(posted(td)) == 2, fixed.stdout)


def test_a_missing_or_unreadable_issue_is_loud() -> None:
    """Every refusal is LOUD (exit 2) and NONE of them writes — a tool that cannot read a run's
    state must never report a pass."""
    print("sweep outcome: refusals")
    with tempfile.TemporaryDirectory() as raw:
        td = Path(raw)
        base = ["--repo", "o/r", "--issue", "498", "--run-id", RUN, "--run-url", RUN_URL]
        closed = run(base + ["--post", "--closed"], env_for(td))
        check("a closed-while-in-flight run posts nothing",
              closed.returncode == 0 and "already-fixed" in closed.stdout, closed.stdout)
        for verdict in ("implement", "refine", "close"):
            res = run(base + ["--post", "--verdict", verdict], env_for(td))
            check(f"a '{verdict}' run posts nothing (its own step commented)",
                  res.returncode == 0 and "commented already" in res.stdout, res.stdout)
        nothing = run(base + ["--post", "--no-implement"], env_for(td))
        check("a run that resolved no open issue posts nothing",
              nothing.returncode == 0 and "nothing to comment on" in nothing.stdout, nothing.stdout)
        check("none of those wrote a comment", posted(td) == [], posted(td))

        missing = run(["--repo", "o/r", "--run-id", RUN], env_for(td))
        check("no issue is refused with exit 2", missing.returncode == 2
              and "no issue" in missing.stderr, missing.stderr)
        junk = run(["--repo", "o/r", "--issue", "not-a-number"], env_for(td))
        check("a non-numeric issue is refused with exit 2", junk.returncode == 2, junk.stderr)
        bad_now = run(base + ["--now", "yesterday"], env_for(td))
        check("an unparseable --now is refused with exit 2", bad_now.returncode == 2,
              bad_now.stderr)
        unreadable = run(base + ["--post"], env_for(td, fail=True))
        check("a gh that cannot read the thread is LOUD (exit 2), never a pass",
              unreadable.returncode == 2 and "failed" in unreadable.stderr, unreadable.stderr)
        check("…and nothing was posted on the unreadable path", posted(td) == [], posted(td))


def test_the_wiring_has_one_entry_point() -> None:
    """One entry point, called by the pipeline, and the body lives in the script (rules 6d/6m)."""
    print("sweep outcome: the wiring")
    makefile = MAKEFILE.read_text(encoding="utf-8")
    check("the Makefile carries `issue-outcome`", "\nissue-outcome:" in makefile)
    recipe = makefile.split("\nissue-outcome:", 1)[-1].split("\n\n", 1)[0]
    optional = ("--repo", "--run-id", "--run-url", "--branch", "--stages", "--verdict", "--closed")
    check("…and it never forwards an empty value (every optional one behind `$(if …)` on one line)",
          all(any(flag in ln and "$(if" in ln for ln in recipe.splitlines()) for flag in optional),
          recipe)
    check("…and it calls the script", "scripts/sweep_outcome.py" in makefile)
    wf = WORKFLOW.read_text(encoding="utf-8")
    check("issue-bot.yml calls `make issue-outcome`", "make issue-outcome" in wf)
    check("the script is reachable from no second implementation of the body",
          "The sweep stopped before it could report an outcome" not in wf,
          "the body belongs in the script")


def main() -> int:
    test_the_decision_names_every_refusal()
    test_the_body_carries_the_registered_marker()
    test_a_second_post_for_the_same_run_writes_nothing()
    test_a_missing_or_unreadable_issue_is_loud()
    test_the_wiring_has_one_entry_point()
    print(f"\nPASSED {passed} | FAILED {failed}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
