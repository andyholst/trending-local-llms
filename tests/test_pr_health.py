#!/usr/bin/env python3
"""A silent PR is an alarm, not an empty check list (issue #442).

Measured: PR #439 was `CONFLICTING` and had **zero** workflow runs — GitHub cannot build the
`refs/pull/N/merge` commit for a conflicting PR, so `validate`, `live-smoke`, `pr-closure` and
`auto-merge` are ABSENT rather than failed. PR #436 then showed the second half: green checks
over a commit nobody had updated, because the repair went to a local branch named differently
from the PR's head.

These tests drive the REAL script against a stub `gh` on PATH (an external system: the GitHub
API is what it talks to, and the script's own requests and decision still run).

Run:  python3 tests/test_pr_health.py   or   make test
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "scripts" / "pr_health.py"
sys.path.insert(0, str(ROOT / "scripts"))

import pr_health as PH  # noqa: E402

_PASS = 0
_FAIL = 0

#: A stub `gh`: `pr list` answers from $FAKE_PRS, `run list` from $FAKE_RUNS_<n> (a JSON array,
#: empty = no runs), `pr view` from $FAKE_COMMENTS, and `pr comment` appends to $FAKE_POSTED.
STUB = """#!/bin/sh
case "$1 $2" in
  "pr list") cat "$FAKE_PRS" ;;
  "pr view") cat "${FAKE_COMMENTS:-/dev/null}" 2>/dev/null || echo '{"comments":[]}' ;;
  "pr comment") echo "$7" >> "$FAKE_POSTED"; echo "posted" ;;
  "run list")
    for a in "$@"; do case "$a" in */) ;; esac; done
    n=""
    prev=""
    for a in "$@"; do
      if [ "$prev" = "--commit" ]; then n="$a"; fi
      prev="$a"
    done
    f=$(eval "echo \\$FAKE_RUNS_$(echo "$n" | tr -cd 'a-f0-9' | cut -c1-7)")
    if [ -n "$f" ] && [ -f "$f" ]; then cat "$f"; else echo "[]"; fi ;;
  *) echo "unexpected: $*" >&2; exit 3 ;;
esac
"""


def check(name, cond, detail: object = ""):
    global _PASS, _FAIL
    if cond:
        _PASS += 1
        print(f"  ok  {name}")
    else:
        _FAIL += 1
        print(f"  FAIL {name}" + (f"  [{detail}]" if detail else ""))


def run(prs: list, runs: dict[str, int], comments: str = "", comment: bool = False):
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        (td / "prs.json").write_text(json.dumps(prs))
        (td / "comments.json").write_text(comments or json.dumps({"comments": []}))
        (td / "posted").write_text("")
        env = {**os.environ, "PATH": f"{td}:{os.environ['PATH']}",
               "FAKE_PRS": str(td / "prs.json"), "FAKE_COMMENTS": str(td / "comments.json"),
               "FAKE_POSTED": str(td / "posted")}
        for oid, count in runs.items():
            f = td / f"runs_{oid}.json"
            f.write_text(json.dumps([{"databaseId": i} for i in range(count)]))
            env[f"FAKE_RUNS_{oid[:7]}"] = str(f)
        (td / "gh").write_text(STUB)
        (td / "gh").chmod(0o755)
        args = [sys.executable, str(SCRIPT), "--repo", "o/r"] + (["--comment"] if comment else [])
        proc = subprocess.run(args, capture_output=True, text=True, env=env)
        return proc, (td / "posted").read_text()


def pr(number, head, mergeable="MERGEABLE", state="CLEAN", draft=False, oid=None):
    return {"number": number, "title": f"PR {number}", "headRefName": head, "isDraft": draft,
            "mergeable": mergeable, "mergeStateStatus": state,
            "headRefOid": oid or (f"a{number:06d}" + "0" * 33)}


def test_a_conflicting_pr_is_silent_and_named():
    proc, _ = run([pr(439, "fix/x-413", mergeable="CONFLICTING", state="DIRTY")],
                  {"a000439" + "0" * 33: 0})
    check("silent: a conflicting PR with no runs exits 1 (loud)", proc.returncode == 1, proc.stdout)
    check("silent: it names the PR and its head branch",
          "#439" in proc.stdout and "fix/x-413" in proc.stdout, proc.stdout)
    check("silent: it says WHY no workflow runs",
          "no merge commit" in proc.stdout and "NO workflow runs" in proc.stdout, proc.stdout)


def test_a_healthy_pr_is_not_flagged():
    proc, _ = run([pr(1, "fix/ok")], {"a000001" + "0" * 33: 3})
    check("silent: a mergeable PR with runs exits 0", proc.returncode == 0, proc.stdout)
    check("silent: it says nothing was silent", "0 silent" in proc.stdout, proc.stdout)


def test_a_pr_whose_pipeline_never_started_is_flagged_too():
    # No conflict, but no runs either: a renamed workflow or a disabled Actions tab — the
    # second reason, kept apart from the first on purpose.
    proc, _ = run([pr(2, "fix/never-started")], {"a000002" + "0" * 33: 0})
    check("silent: a PR with no runs and no conflict still fails", proc.returncode == 1,
          proc.stdout)
    check("silent: its reason is the missing runs, not a conflict",
          "no check runs" in proc.stdout and "CONFLICTING" not in proc.stdout, proc.stdout)


def test_drafts_are_left_alone():
    proc, _ = run([pr(3, "fix/draft", mergeable="CONFLICTING", state="DIRTY", draft=True)], {})
    check("silent: a draft PR is not an alarm", proc.returncode == 0, proc.stdout)
    check("silent: it is not even counted", "0 open non-draft PR(s)" in proc.stdout, proc.stdout)


def test_the_comment_carries_the_fix_and_is_deduplicated():
    prs = [pr(436, "fix/storage-offload-detector-413", mergeable="CONFLICTING", state="DIRTY")]
    runs = {"a000436" + "0" * 33: 0}
    proc, posted = run(prs, runs, comment=True)
    check("silent: --comment posts the flag", "flagged" in proc.stdout and "pr-health-alarm" in posted,
          posted)
    check("silent: the comment names the PR's head branch in the push shape",
          "refs/heads/<PR head>" in posted, posted)
    check("silent: it names the worktree resume", "make worktree-resume BRANCH=" in posted, posted)
    # A second sweep that finds our marker does NOT comment again (the queue alarm's contract).
    proc2, posted2 = run(prs, runs, comment=True,
                         comments=json.dumps({"comments": [{"body": f"<!-- {PH.MARKER} -->"}]}))
    check("silent: a second sweep does not comment again",
          "already flagged" in proc2.stdout and "pr-health-alarm" not in posted2, posted2)


def test_the_decision_is_pure_and_the_reasons_are_separate():
    prs = [pr(1, "a"), pr(2, "b", mergeable="CONFLICTING", state="DIRTY"), pr(3, "c")]
    out = PH.findings(prs, {1: 2, 2: 0, 3: 0})
    check("silent: only the affected PRs are returned", [f["number"] for f in out] == [2, 3], out)
    check("silent: the conflicting one carries the conflict reason",
          any("CONFLICTING" in r for r in out[0]["reasons"]), out[0]["reasons"])
    check("silent: the quiet one carries only the missing-runs reason",
          out[1]["reasons"] == ["no check runs on its head commit"], out[1]["reasons"])


def test_a_gh_failure_is_loud():
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        (td / "gh").write_text("#!/bin/sh\necho 'HTTP 502' >&2\nexit 1\n")
        (td / "gh").chmod(0o755)
        env = {**os.environ, "PATH": f"{td}:{os.environ['PATH']}"}
        proc = subprocess.run([sys.executable, str(SCRIPT), "--repo", "o/r"],
                              capture_output=True, text=True, env=env)
    check("silent: an unreadable state exits 2, never 0", proc.returncode == 2, proc.stdout)
    check("silent: the refusal quotes gh", "502" in proc.stderr, proc.stderr)


def test_the_sweep_is_wired_to_a_target_a_workflow_and_a_guard():
    mk = (ROOT / "Makefile").read_text()
    check("silent: a make target runs the sweep", "python3 scripts/pr_health.py" in mk, "")
    wf = (ROOT / ".github" / "workflows" / "pr-health.yml").read_text()
    check("silent: the workflow calls it through the Makefile", "make pr-health" in wf, "")
    check("silent: the guard is the FIRST job (rule 6j)",
          wf.index("guard:") < wf.index("sweep:"), wf[:400])
    check("silent: it is a scheduled sweep with the bypass",
          "schedule" in wf and "workflow_dispatch" in wf, "")
    # A PR comment needs `pull-requests: write`, and the comment uses the DEFAULT token
    # (rule 6b): the owner PAT has no PR scope, so a refused comment would leave the sweep
    # green over a silent PR.
    check("silent: it may comment (pull-requests: write)", "pull-requests: write" in wf, "")
    # TWO tokens, deliberately (issue #475): the COMMENT uses the default token (rule 6b —
    # the owner PAT has no comment scope), while DISPATCHING a workflow is an Actions write
    # and needs the PAT. Each step must carry its own.
    comment_step = wf[wf.index("Flag every silent open PR"):]
    repair_step = wf[wf.index("Dispatch the repair"):wf.index("Flag every silent open PR")]
    check("silent: the comment step uses the default token",
          "GH_TOKEN: ${{ github.token }}" in comment_step, comment_step[:300])
    check("silent: the repair step uses the owner PAT (dispatching is an Actions write)",
          "FIXBOT_DISPATCH_TOKEN" in repair_step, repair_step[:300])
    check("silent: the repair step asks the target for a repair",
          "REPAIR=1" in repair_step, repair_step[:300])
    # The #231 coverage map must name it: no PR runs a cron-only pipeline.
    tw = (ROOT / "tests" / "test_workflows.py").read_text()
    check("silent: it is classified in DISPATCH_ONLY_COVERAGE",
          '"pr-health.yml"' in tw, "")


def test_only_a_bot_branch_is_repaired_and_the_cap_holds():
    """Issue #475: the sweep REPAIRS a `ci/…` PR itself (a conflicting PR runs no workflows,
    so this is the only trigger that fires) and never touches a human's branch, where the
    bot would be pushing someone else's work."""
    silent = [
        {"number": 1, "head": "ci/trending-refresh-20261020-1136", "reasons": ["x"]},
        {"number": 2, "head": "ci/data-gap-449-x", "reasons": ["x"]},
        {"number": 3, "head": "fix/hardware-is-not-an-engine", "reasons": ["x"]},
        {"number": 4, "head": "", "reasons": ["x"]},
    ]
    picked = [f["number"] for f in PH.repair_targets(silent)]
    check("repair: both ci/ branches are dispatched", picked == [1, 2], picked)
    check("repair: a human's branch is left alone", 3 not in picked, picked)
    check("repair: an empty head is never dispatched", 4 not in picked, picked)
    check("repair: every silent PR is still reported", len(silent) == 4, "")


def test_an_empty_setting_means_missing():
    """#487: `MAX_FIXBOT_COMMITS=` (set, empty) crashed `int("")` on every sweep."""
    from env_int import EnvSettingError, env_float, env_int
    os.environ.pop("PH_TEST_INT", None)
    check("env_int: unset -> the default", env_int("PH_TEST_INT", 2) == 2)
    os.environ["PH_TEST_INT"] = ""
    check("env_int: EMPTY -> the default (the measured bug)", env_int("PH_TEST_INT", 2) == 2)
    os.environ["PH_TEST_INT"] = "   "
    check("env_int: whitespace -> the default", env_int("PH_TEST_INT", 2) == 2)
    os.environ["PH_TEST_INT"] = "3"
    check("env_int: a value is read", env_int("PH_TEST_INT", 2) == 3)
    os.environ["PH_TEST_INT"] = " 3 "
    check("env_int: a padded value is read", env_int("PH_TEST_INT", 2) == 3)
    os.environ["PH_TEST_INT"] = "2.5"
    try:
        env_int("PH_TEST_INT", 2)
        raised = ""
    except EnvSettingError as exc:
        raised = str(exc)
    check("env_int: garbage fails LOUDLY and names the variable",
          "PH_TEST_INT" in raised and "not a number" in raised, raised)
    os.environ.pop("PH_TEST_INT", None)
    os.environ["PH_TEST_FLOAT"] = ""
    check("env_float: EMPTY -> the default", env_float("PH_TEST_FLOAT", 2.5) == 2.5)
    os.environ.pop("PH_TEST_FLOAT", None)


def test_the_real_target_survives_an_empty_max():
    """The EXACT production call: `make pr-health REPO=… COMMENT=1` with no MAX.

    Measured on run 39530945300: the public target forwarded
    `MAX_FIXBOT_COMMITS=""`, `int("")` raised, and the sweep — the alarm for a
    silent PR — was itself silently refused. This runs the real Makefile, the real
    script, and only stands in for the network (a stub `gh` on PATH).
    """
    with tempfile.TemporaryDirectory() as d:
        td = Path(d)
        stub_dir = td / "bin"
        stub_dir.mkdir()
        stub = stub_dir / "gh"
        stub.write_text(STUB, encoding="utf-8")
        stub.chmod(0o755)
        prs = td / "prs.json"
        prs.write_text("[]", encoding="utf-8")
        env = {k: v for k, v in os.environ.items() if k not in
               ("MAX_FIXBOT_COMMITS", "FAKE_COMMENTS", "FAKE_POSTED")}
        env.update({"PATH": f"{stub_dir}:{env['PATH']}", "FAKE_PRS": str(prs),
                    "FAKE_POSTED": str(td / "posted")})
        env.pop("GH_TOKEN", None)
        r = subprocess.run(["make", "pr-health", "REPO=x/y", "COMMENT=1"], cwd=str(ROOT),
                           capture_output=True, text=True, env=env)
        check("make pr-health: an UNSET max does not crash the sweep", r.returncode == 0,
              (r.stdout + r.stderr)[-400:])
        check("make pr-health: it actually ran and reported", "[pr-health]" in r.stdout,
              r.stdout[-200:])
        check("make pr-health: no traceback anywhere", "Traceback" not in (r.stdout + r.stderr))
        r = subprocess.run(["make", "pr-health", "REPO=x/y", "COMMENT=1", "MAX_FIXBOT_COMMITS="],
                           cwd=str(ROOT), capture_output=True, text=True, env=env)
        check("make pr-health: an EXPLICITLY empty max is the same no-crash", r.returncode == 0,
              (r.stdout + r.stderr)[-400:])
        r = subprocess.run(["make", "pr-health", "REPO=x/y", "MAX_FIXBOT_COMMITS=abc"],
                           cwd=str(ROOT), capture_output=True, text=True, env=env)
        check("make pr-health: a non-numeric max stays LOUD", r.returncode != 0
              and "MAX_FIXBOT_COMMITS" in (r.stdout + r.stderr), (r.stdout + r.stderr)[-300:])


def test_no_script_reads_a_number_straight_from_the_environment():
    """One implementation: a new `int(os.environ…)` would reintroduce #487 elsewhere."""
    bare = []
    for path in sorted((ROOT / "scripts").glob("*.py")):
        if path.name == "env_int.py":
            continue
        text = path.read_text(encoding="utf-8")
        for n, line in enumerate(text.splitlines(), 1):
            if "int(os.environ" in line or "float(os.environ" in line:
                bare.append(f"scripts/{path.name}:{n}")
    check("env_int: no script reads an int/float straight from the environment",
          not bare, bare)


def test_sweep_never_exports_an_empty_setting():
    mk = (ROOT / "Makefile").read_text(encoding="utf-8")
    check("wiring: the public target forwards MAX_FIXBOT_COMMITS only when SET",
          'MAX_FIXBOT_COMMITS="$(MAX_FIXBOT_COMMITS)"\n' not in mk.split("pr-health:", 1)[-1],
          mk.split("pr-health:", 1)[-1][:300])


def main() -> int:
    print("silent PR alarm (issue #442)")
    test_a_conflicting_pr_is_silent_and_named()
    test_a_healthy_pr_is_not_flagged()
    test_a_pr_whose_pipeline_never_started_is_flagged_too()
    test_drafts_are_left_alone()
    test_the_comment_carries_the_fix_and_is_deduplicated()
    test_the_decision_is_pure_and_the_reasons_are_separate()
    test_a_gh_failure_is_loud()
    test_the_sweep_is_wired_to_a_target_a_workflow_and_a_guard()
    test_only_a_bot_branch_is_repaired_and_the_cap_holds()
    test_an_empty_setting_means_missing()
    test_the_real_target_survives_an_empty_max()
    test_no_script_reads_a_number_straight_from_the_environment()
    test_sweep_never_exports_an_empty_setting()
    print(f"\nPASSED {_PASS} | FAILED {_FAIL}")
    return 1 if _FAIL else 0


if __name__ == "__main__":
    raise SystemExit(main())
