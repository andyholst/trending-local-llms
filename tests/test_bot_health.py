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
    check("pipelines: the list is non-vacuous", len(names) >= 5, names)
    # qa-validate is NOT here on purpose: it runs on PRs and pushes, not on a cron — a pipeline
    # with no scheduled runs has no "red on every run" to read (it is covered by pr-health).
    for expected in ("refresh-bot.yml", "queued-alarm.yml", "pr-health.yml", "bot-health.yml"):
        check(f"pipelines: {expected} is a cron pipeline of this repo", expected in names, names)
    check("pipelines: a NON-cron workflow is not in the list",
          "publish-agent-image.yml" not in names, names)


def test_a_pipeline_red_on_every_run_fails_the_sweep():
    with tempfile.TemporaryDirectory() as d:
        td = Path(d)
        env = stub_gh(td, {name: red(3) for name in pipeline_list()})
        p = run("--root", str(ROOT), "--repo", "o/r", "--limit", "3", env=env)
        check("red: the sweep exits non-zero", p.returncode == 1, (p.returncode, p.stderr[-300:]))
        check("red: it NAMES a run URL a human can open",
              "https://example/run/0" in (p.stdout + p.stderr), p.stdout[-300:])
        check("red: it names how many pipelines are red", "cron pipeline(s) are red" in p.stderr,
              p.stderr[-300:])


def test_one_green_run_is_enough_to_stay_quiet():
    with tempfile.TemporaryDirectory() as d:
        td = Path(d)
        names = pipeline_list()
        answers = {n: red(3) for n in names}
        answers[names[0]] = [red(1)[0]] + green(2)      # one green inside the window
        env = stub_gh(td, answers)
        p = run("--root", str(ROOT), "--repo", "o/r", "--limit", "3", env=env)
        check("mixed: a green run inside the window keeps that pipeline quiet",
              f"ok   {names[0]}" in p.stdout, p.stdout[:300])
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
              p.returncode == 0 and "only 1 scheduled run(s) so far" in p.stdout,
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
    check("workflow: it runs on a cron", "cron:" in wf, "")
    check("workflow: it has a guard job FIRST", wf.index("guard:") < wf.index("health:"), "")
    check("workflow: it calls the target", "make bot-health" in wf, "")
    check("workflow: it is read-only (no issues: write)", "issues: write" not in wf, "")
    suites = (ROOT / "tests" / "test_workflows.py").read_text()
    check("wiring: the guard is registered in BOT_GUARDS",
          '"bot-health.yml", "guard"' in suites, "")


def main() -> int:
    print("bot health: a red cron pipeline is loud (issue #488)")
    test_the_pipeline_list_is_derived_and_not_vacuous()
    test_a_pipeline_red_on_every_run_fails_the_sweep()
    test_one_green_run_is_enough_to_stay_quiet()
    test_a_young_pipeline_is_not_a_failure()
    test_an_unanswerable_gh_is_loud_not_clean()
    test_a_limit_of_zero_is_refused()
    test_the_workflow_carries_a_guard_a_cron_and_the_target()
    print(f"PASSED {_PASS} | FAILED {_FAIL}")
    return 0 if _FAIL == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
