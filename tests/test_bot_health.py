#!/usr/bin/env python3
"""A cron pipeline that is red on every run has an alarm of its own (issue #488).

`pr-health` failed on every scheduled sweep for days with a traceback nobody saw, and the failing
step was the one whose job is to make a silent PR loud: its silence removed its own alarm. `queued-
alarm` (#252) and `sweep-alarm` (#497) each read a DIFFERENT silence; nothing read "this pipeline's
own cron is failing", which is the level above both.

These tests drive the REAL script with a stub `gh` on PATH (the GitHub API is the external system),
and read the REAL workflow so the wiring is proved, not asserted by prose.

Run:  python3 tests/test_bot_health.py    or   make test
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "scripts" / "bot_health.py"

_PASS = 0
_FAIL = 0


def check(name, cond, detail=None):
    global _PASS, _FAIL
    if cond:
        _PASS += 1
        print(f"  ok  {name}")
    else:
        _FAIL += 1
        shown = "" if detail is None or detail == "" else f"  [{detail}]"
        print(f"  FAIL {name}{shown}")


def stub_gh(td: Path, answers: dict[str, list[dict]], fail: bool = False) -> dict:
    """A `gh` that answers `run list --workflow X` from `answers` (list of runs per workflow)."""
    bin_ = td / "bin"
    bin_.mkdir(exist_ok=True)
    (td / "answers.json").write_text(json.dumps(answers))
    gh = bin_ / "gh"
    gh.write_text(
        "#!/usr/bin/env python3\n"
        "import json, os, sys\n"
        "from pathlib import Path\n"
        "args = sys.argv[1:]\n"
        f"if os.environ.get('FAIL_GH') == '1':\n"
        "    sys.stderr.write('HTTP 502: bad gateway\\n'); sys.exit(1)\n"
        "d = Path(os.environ['FAKE_DIR'])\n"
        "if args[:2] == ['repo', 'view']:\n"
        "    print('o/r'); sys.exit(0)\n"
        "wf = args[args.index('--workflow') + 1] if '--workflow' in args else ''\n"
        "answers = json.loads((d / 'answers.json').read_text())\n"
        "print(json.dumps(answers.get(wf, [])))\n")
    gh.chmod(0o755)
    return {**os.environ, "PATH": f"{bin_}{os.pathsep}{os.environ['PATH']}", "FAKE_DIR": str(td)}


def run(*args: str, env: dict):
    return subprocess.run([sys.executable, str(SCRIPT), *args],
                          capture_output=True, text=True, env=env)


def red(n: int = 3) -> list[dict]:
    return [{"conclusion": "failure", "databaseId": i, "createdAt": "2026-10-25T00:00:00Z",
             "url": f"https://example/run/{i}"} for i in range(n)]


def green(n: int = 3) -> list[dict]:
    return [{"conclusion": "success", "databaseId": i, "createdAt": "2026-10-25T00:00:00Z",
             "url": f"https://example/run/{i}"} for i in range(n)]


def pipeline_list() -> list[str]:
    out = subprocess.run([sys.executable, str(SCRIPT), "--root", str(ROOT), "--list"],
                         capture_output=True, text=True)
    return [line for line in out.stdout.splitlines() if line.strip()]


def test_the_pipeline_list_is_derived_and_not_vacuous():
    names = pipeline_list()
    # (owner directive 2026-11-15, issue #1029) ONLY refresh-bot carries a cron, so a CRON-only
    # read made every dispatch-only bot invisible — including this alarm's own red runs (#1186).
    refresh = "refresh-bot.yml"
    check("pipelines: the list is non-vacuous", len(names) >= 1, names)
    check("pipelines: the ONLY cron pipeline is still watched", refresh in names, names)
    check("pipelines: a dispatch-only pipeline is watched by ROLE (#1186)",
          "bot-health.yml" in names and "queued-alarm.yml" in names, names)
    check("pipelines: a PR-exercised pipeline is not watched",
          "qa-validate.yml" not in names and "pr-closure.yml" not in names, names)
    check("pipelines: a dispatch-only PUBLISHER is watched too (#1186)",
          "publish-agent-image.yml" in names, names)


def test_a_pipeline_red_on_every_run_fails_the_sweep():
    with tempfile.TemporaryDirectory() as d:
        td = Path(d)
        env = stub_gh(td, {name: red(3) for name in pipeline_list()})
        p = run("--root", str(ROOT), "--repo", "o/r", "--limit", "3", env=env)
        check("red: the sweep exits non-zero", p.returncode == 1, (p.returncode, p.stderr[-300:]))
        check("red: it NAMES a run URL a human can open",
              "https://example/run/0" in (p.stdout + p.stderr), p.stdout[-300:])
        check("red: it names how many pipelines are red", "watched pipeline(s) are red" in p.stderr,
              p.stderr[-300:])


def test_one_green_run_is_enough_to_stay_quiet():
    # Two cron pipelines are PLANTED in a sandbox root (issue #1029 left only refresh-bot
    # scheduled in the real tree; the multi-pipeline behaviour is proven end to end, not
    # assumed): a green run inside the window keeps ITS pipeline quiet, the sweep still
    # fails for the others.
    with tempfile.TemporaryDirectory() as d:
        td = Path(d)
        wf = td / ".github" / "workflows"
        wf.mkdir(parents=True)
        for name in ("slow.yml", "fast.yml"):
            (wf / name).write_text(
                "on:\n  schedule:\n    - cron: \"7 * * * 3\"\njobs:\n  x: {}\n")
        answers = {"slow.yml": red(3), "fast.yml": [red(1)[0]] + green(2)}
        env = stub_gh(td, answers)
        p = run("--root", str(td), "--repo", "o/r", "--limit", "3", env=env)
        check("mixed: a green run inside the window keeps that pipeline quiet",
              "ok   fast.yml" in p.stdout, p.stdout[:300])
        check("mixed: the sweep still fails for the OTHERS", p.returncode == 1, p.returncode)


def test_a_young_pipeline_is_not_a_failure():
    with tempfile.TemporaryDirectory() as d:
        td = Path(d)
        names = pipeline_list()
        answers = {n: green(3) for n in names}
        answers[names[0]] = red(1)                       # only ONE run recorded so far
        env = stub_gh(td, answers)
        p = run("--root", str(ROOT), "--repo", "o/r", "--limit", "3", env=env)
        check("young: a pipeline with fewer runs than the window is not red",
              p.returncode == 0 and "only 1 " in p.stdout and "run(s) so far" in p.stdout,
              (p.returncode, p.stdout[:300]))


def test_an_unanswerable_gh_is_loud_not_clean():
    with tempfile.TemporaryDirectory() as d:
        td = Path(d)
        env = stub_gh(td, {}, fail=True)
        env["FAIL_GH"] = "1"
        p = run("--root", str(ROOT), "--repo", "o/r", env=env)
        check("gh down: the sweep exits non-zero rather than reporting a clean bill of health",
              p.returncode != 0, p.returncode)
        check("gh down: it says gh failed", "gh run list" in p.stderr, p.stderr[:200])


def test_a_limit_of_zero_is_refused():
    with tempfile.TemporaryDirectory() as d:
        td = Path(d)
        env = stub_gh(td, {})
        p = run("--root", str(ROOT), "--repo", "o/r", "--limit", "0", env=env)
        check("limit: 0 checks nothing and is refused", p.returncode == 2, p.returncode)


def test_the_workflow_carries_a_guard_a_cron_and_the_target():
    wf = (ROOT / ".github" / "workflows" / "bot-health.yml").read_text()
    # (owner directive 2026-11-15, issue #1029) bot-health is dispatch-only: NO cron.
    check("workflow: NO schedule: trigger (dispatch-only, #1029)",
          "\n  schedule:\n" not in wf, wf[:200])
    check("workflow: it has a guard job FIRST", wf.index("guard:") < wf.index("health:"), "")
    check("workflow: it calls the target", "make bot-health" in wf, "")
    check("workflow: it is read-only (no issues: write)", "issues: write" not in wf, "")
    suites = (ROOT / "tests" / "test_workflows.py").read_text()
    check("wiring: the guard is registered in BOT_GUARDS",
          '"bot-health.yml", "guard"' in suites, "")


def test_dispatch_only_pipelines_are_watched_by_role():
    """Issue #1186: the pipeline set is chosen by ROLE, not by the presence of a cron line."""
    with tempfile.TemporaryDirectory() as d:
        td = Path(d)
        wf = td / ".github" / "workflows"
        wf.mkdir(parents=True)
        (wf / "cron-bot.yml").write_text(
            "on:\n  schedule:\n    - cron: \"7 * * * 3\"\n  workflow_dispatch:\njobs:\n  x: {}\n")
        (wf / "dispatch-bot.yml").write_text(
            "on:\n  workflow_dispatch:\n    inputs:\n      limit:\n        default: \"3\"\njobs:\n  x: {}\n")
        (wf / "pr-bot.yml").write_text("on:\n  pull_request:\njobs:\n  x: {}\n")
        p = subprocess.run([sys.executable, str(SCRIPT), "--root", str(td), "--list"],
                           capture_output=True, text=True)
        names = [line for line in p.stdout.splitlines() if line.strip()]
        check("role: a cron pipeline is still watched", "cron-bot.yml" in names, names)
        check("role: a dispatch-only pipeline is watched (#1186)", "dispatch-bot.yml" in names, names)
        check("role: a PR-exercised pipeline is NOT watched", "pr-bot.yml" not in names, names)


def test_a_dispatch_only_pipeline_red_on_every_dispatch_run_fails_the_sweep():
    """Issue #1186: the alarm reads a dispatch-only pipeline's `workflow_dispatch` runs."""
    with tempfile.TemporaryDirectory() as d:
        td = Path(d)
        wf = td / ".github" / "workflows"
        wf.mkdir(parents=True)
        (wf / "dispatch-bot.yml").write_text("on:\n  workflow_dispatch:\njobs:\n  x: {}\n")
        bin_ = td / "bin"
        bin_.mkdir()
        (bin_ / "gh").write_text(
            "#!/usr/bin/env python3\n"
            "import json, sys\n"
            "a = sys.argv[1:]\n"
            "if a[:2] == ['repo', 'view']:\n    print('o/r'); sys.exit(0)\n"
            "if '--event' not in a or a[a.index('--event') + 1] != 'workflow_dispatch':\n"
            "    print('[]'); sys.exit(0)\n"
            "print(json.dumps([{'conclusion': 'failure', 'databaseId': i,\n"
            "                   'url': f'https://example/dispatch/{i}'} for i in range(3)]))\n")
        (bin_ / "gh").chmod(0o755)
        env = {**os.environ, "PATH": f"{bin_}{os.pathsep}{os.environ['PATH']}"}
        p = run("--root", str(td), "--repo", "o/r", "--limit", "3", env=env)
        check("dispatch: all-red dispatch runs fail the sweep (#1186)", p.returncode == 1,
              (p.returncode, p.stdout[-300:], p.stderr[-300:]))
        check("dispatch: it names the dispatch run URL",
              "https://example/dispatch/0" in (p.stdout + p.stderr), p.stdout[-300:])


def test_the_failure_filer_watches_the_bot_health_pipeline():
    """Rule 6r / issue #1186: a red bot-health dispatch must reach the ledger and an issue."""
    import datetime as dt
    sys.path.insert(0, str(ROOT / "scripts"))
    import pipeline_failure_issue as pfi

    check("filer: bot-health.yml is a MAIN pipeline (#1186)",
          "bot-health.yml" in pfi.MAIN_PIPELINES, pfi.MAIN_PIPELINES)
    check("filer: bot-health.yml is declared dispatch-only (#1186)",
          "bot-health.yml" in pfi.DISPATCH_ONLY_PIPELINES, pfi.DISPATCH_ONLY_PIPELINES)

    now = dt.datetime(2026, 11, 24, 2, 0, 0, tzinfo=dt.timezone.utc)
    rows = [{"databaseId": 555, "workflowName": "bot-health.yml", "name": "bot health",
             "headBranch": "master", "headSha": "f" * 40, "event": "workflow_dispatch",
             "createdAt": "2026-11-24T01:00:00Z", "conclusion": "failure", "status": "completed",
             "url": "https://example/bot-health/555"}]
    with tempfile.TemporaryDirectory() as d:
        env = stub_gh(Path(d), {"bot-health.yml": rows})
        saved = dict(os.environ)
        os.environ.clear()
        os.environ.update(env)
        try:
            picked = {r["databaseId"] for r in pfi.main_pipeline_failures("o/r", 24, now)}
        finally:
            os.environ.clear()
            os.environ.update(saved)
    check("filer: a red dispatched bot-health run is SELECTED (#1186)", 555 in picked, picked)


def main() -> int:
    print("bot health: a red cron or dispatch-only pipeline is loud (issues #488/#1186)")
    test_the_pipeline_list_is_derived_and_not_vacuous()
    test_a_pipeline_red_on_every_run_fails_the_sweep()
    test_one_green_run_is_enough_to_stay_quiet()
    test_a_young_pipeline_is_not_a_failure()
    test_an_unanswerable_gh_is_loud_not_clean()
    test_a_limit_of_zero_is_refused()
    test_the_workflow_carries_a_guard_a_cron_and_the_target()
    test_dispatch_only_pipelines_are_watched_by_role()
    test_a_dispatch_only_pipeline_red_on_every_dispatch_run_fails_the_sweep()
    test_the_failure_filer_watches_the_bot_health_pipeline()
    print(f"PASSED {_PASS} | FAILED {_FAIL}")
    return 0 if _FAIL == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
