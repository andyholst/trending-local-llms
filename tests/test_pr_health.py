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
import shutil
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


def run(prs: list, runs: dict[str, int], comments: str = "", comment: bool = False,
        held=(), extra=()):
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
            concl = "action_required" if oid in held else "success"
            f.write_text(json.dumps([{"databaseId": i, "conclusion": concl}
                                     for i in range(count)]))
            env[f"FAKE_RUNS_{oid[:7]}"] = str(f)
        (td / "gh").write_text(STUB)
        (td / "gh").chmod(0o755)
        args = [sys.executable, str(SCRIPT), "--repo", "o/r"] + (["--comment"] if comment else []) + list(extra)
        proc = subprocess.run(args, capture_output=True, text=True, env=env)
        return proc, (td / "posted").read_text()


def pr(number, head, mergeable="MERGEABLE", state="CLEAN", draft=False, oid=None,
       author=None, closing=()):
    row = {"number": number, "title": f"PR {number}", "headRefName": head, "isDraft": draft,
           "mergeable": mergeable, "mergeStateStatus": state,
           "headRefOid": oid or (f"a{number:06d}" + "0" * 33),
           "closingIssuesReferences": [{"number": n} for n in closing]}
    if author is not None:
        row["author"] = author
    return row


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


def test_a_pr_whose_runs_are_all_held_for_approval_is_flagged():
    # The THIRD silence (issue #1123), measured on PR #1116 (head b10716488d, 2026-11-17):
    # a bot PR whose head commit edits .github/workflows/ gets every pipeline run on that
    # head concluded `action_required` — GitHub holds the branch's own workflows for a
    # collaborator's approval, so NO job executes, `gh pr checks` is empty, and the state
    # stays UNSTABLE forever. The old sweep read only the run COUNT and called it healthy.
    oid = "a000116" + "0" * 33
    proc, _ = run([pr(1116, "tech-debt-rebase-keeper-push-with-owner-pat-1115", oid=oid)],
                  {oid: 2}, held=[oid])
    check("hold: a PR whose head runs are all action_required exits 1",
          proc.returncode == 1, proc.stdout)
    check("hold: the reason names the approval hold",
          "HELD FOR APPROVAL" in proc.stdout, proc.stdout)
    check("hold: it is NOT mis-reported as missing runs (the runs exist)",
          "no check runs" not in proc.stdout, proc.stdout)
    check("hold: it is NOT mis-reported as a conflict",
          "CONFLICTING" not in proc.stdout, proc.stdout)


def test_a_held_pr_and_a_ran_pr_are_separated():
    held_oid = "a000116" + "0" * 33
    ok_oid = "a000022" + "0" * 33
    proc, _ = run([pr(1116, "held/workflows", oid=held_oid), pr(22, "fix/ran-fine")],
                  {held_oid: 2, ok_oid: 3}, held=[held_oid])
    check("hold: only the held PR is silent", proc.returncode == 1 and "1 silent" in proc.stdout,
          proc.stdout)
    check("hold: the PR whose runs executed is not flagged", "#22" not in proc.stdout,
          proc.stdout)
    check("hold: the pure decision agrees with the sweep",
          [f["number"] for f in PH.findings([pr(1116, "held"), pr(22, "ok")],
                                            {1116: 2, 22: 3}, {1116: 2, 22: 0})] == [1116])


def test_the_hold_comment_names_the_human_approval_remedy():
    oid = "a000116" + "0" * 33
    prs = [pr(1116, "tech-debt-held-workflows-1123", oid=oid)]
    proc, posted = run(prs, {oid: 2}, held=[oid], comment=True)
    check("hold: --comment posts the flag", "pr-health-alarm" in posted, posted)
    check("hold: the comment names how to release the hold",
          "Review pending workflows" in posted and "approv" in posted.lower(), posted)
    check("hold: the comment says approving is a human collaborator's act (rule 6t)",
          "rule 6t" in posted, posted)
    check("hold: the comment does NOT tell anyone to rebase (the hold is not a stale base)",
          "make worktree-resume" not in posted, posted)
    proc2, posted2 = run(prs, {oid: 2}, held=[oid], comment=True,
                         comments=json.dumps({"comments": [{"body": f"<!-- {PH.MARKER} -->"}]}))
    check("hold: a second sweep does not comment again",
          "already flagged" in proc2.stdout and "pr-health-alarm" not in posted2, posted2)


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
    # (issue #1029) pr-health is DISPATCH-ONLY: no `schedule:` trigger — but its guard
    # script still admits a schedule event (the bypass text stays).
    check("silent: dispatch-only sweep (no schedule: trigger, #1029) with the bypass intact",
          "\n  schedule:\n" not in wf and '"schedule"' in wf and "workflow_dispatch" in wf, wf[:300])
    # A PR comment needs `pull-requests: write`, and the comment uses the DEFAULT token
    # (rule 6b): the owner PAT has no PR scope, so a refused comment would leave the sweep
    # green over a silent PR.
    check("silent: it may comment (pull-requests: write)", "pull-requests: write" in wf, "")
    # TWO tokens, deliberately (issue #475): the COMMENT uses the default token (rule 6b —
    # the owner PAT has no comment scope), while DISPATCHING a workflow is an Actions write
    # and needs the PAT. Each step must carry its own.
    comment_step = wf[wf.index("Rebase drifted bot PRs and flag every silent open PR"):]
    check("silent: the sweep step uses the default token",
          "GH_TOKEN: ${{ github.token }}" in comment_step, comment_step[:300])
    # Issue #818: the same step carries the rebaser half — REBASE=1 — and the job may push
    # a rebased bot branch back to its PR head (contents: write on the sweep job), on a
    # full-history checkout (a shallow clone cannot rebase).
    check("rebaser: the step calls make pr-health with REBASE=1",
          "make pr-health" in comment_step and "REBASE=1" in comment_step, comment_step[:400])
    check("rebaser: the sweep job may push (contents: write)",
          "contents: write" in wf[wf.index("  sweep:"):], wf[wf.index("  sweep:"):200])
    check("rebaser: the checkout carries full history (fetch-depth: 0)",
          "fetch-depth: 0" in wf[wf.index("  sweep:"):])
    mk = (ROOT / "Makefile").read_text(encoding="utf-8")
    check("rebaser: the Makefile forwards REBASE to the flag",
          '$(if $(REBASE),--rebase,)' in mk, "")
    # Issue #814: the sweep REPORTS only — the dispatch-to-fix-bot step was deleted
    # with the repair pipeline, and re-adding it re-adds this red.
    check("silent: the sweep dispatches no repairer (report-only since #814)",
          "Dispatch the repair" not in wf and "workflow_dispatch" not in wf[wf.index("jobs:"):],
          wf[wf.index("jobs:"):wf.index("jobs:")+400])
    # The #231 coverage map must name it: no PR runs a cron-only pipeline.
    tw = (ROOT / "tests" / "test_workflows.py").read_text()
    check("silent: it is classified in DISPATCH_ONLY_COVERAGE",
          '"pr-health.yml"' in tw, "")


def test_a_silent_pr_is_reported_and_nothing_is_dispatched():
    """Issue #814: the sweep REPORTS every silent PR and dispatches no repairer.

    (The old shape — #475 — had it dispatch fix-bot for `ci/…` PRs. The repair
    pipeline was retired, so a dispatched PR would sit `queued` for a job that no
    longer exists; the sweep's only output is the flagged PR plus its remedy.)"""
    src = SCRIPT.read_text(encoding="utf-8")
    check("retired: the sweep script carries no dispatch/repair path",
          "workflow_dispatch" not in src and "repair_targets" not in src and "--repair" not in src,
          "")
    wf = (ROOT / ".github" / "workflows" / "pr-health.yml").read_text()
    check("retired: the workflow has no Dispatch step and no dispatch trigger in its jobs",
          "Dispatch the repair" not in wf and "workflow_dispatch" not in wf[wf.index("jobs:"):],
          wf[wf.index("jobs:"):][:300])
    silent = [{"number": n, "head": h, "mergeStateStatus": "DIRTY", "isDraft": False,
               "headRepo": {"full_name": "o/r"}, "updatedAt": "2026-11-11T00:00:00Z"}
              for n, h in ((1, "ci/trending-refresh-x"), (2, "fix/human-branch"))]
    flagged = PH.findings(silent, {1: 1, 2: 0})
    check("retired: findings() still classifies every silent PR, ci/ branches included",
          all("reasons" in f for f in flagged), flagged)


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


def test_the_real_target_runs_report_only():
    """The EXACT production call: `make pr-health REPO=… COMMENT=1`, report-only.

    Measured on run 39530945300 (issue #487): the public target forwarded
    `MAX_FIXBOT_COMMITS=""`, `int("")` raised, and the sweep was itself silently
    refused. Issue #814 retired the variable with the repair pipeline; the sweep
    now runs with no settings at all. This runs the real Makefile, the real
    script, and only stands in for the network (a stub `gh` on PATH)."""
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
        check("make pr-health: the report-only sweep runs clean", r.returncode == 0,
              (r.stdout + r.stderr)[-400:])
        check("make pr-health: it actually ran and reported", "[pr-health]" in r.stdout,
              r.stdout[-200:])
        check("make pr-health: no traceback anywhere", "Traceback" not in (r.stdout + r.stderr))
        mk = (ROOT / "Makefile").read_text(encoding="utf-8")
        check("wiring: the retired MAX_FIXBOT_COMMITS lives in no pr-health recipe",
              "MAX_FIXBOT_COMMITS" not in mk.split("pr-health:", 1)[-1][:400],
              mk.split("pr-health:", 1)[-1][:200])


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


def test_rebase_plan_classifies_by_ownership_and_conflict():
    """The DECISION half (rule 6d): ci/ branches are the sweep's to rebase, everything
    else is untouchable, and a CONFLICTING bot PR is never auto-rebased (issue #818)."""
    plan = PH.rebase_plan([
        pr(1, "ci/data-gap-7-x"),
        pr(2, "fix/human-branch"),
        pr(3, "ci/clash-y", mergeable="CONFLICTING", state="DIRTY"),
        pr(4, "ci/draft-z", draft=True),
        pr(5, "keeper/human-z"),
        pr(6, "tech-debt-slug-955"),
        pr(7, "issue-523-tech-debt"),
        pr(8, "data-gap-42-y"),
        pr(9, "feature/human-idea"),
    ])
    by = {p["number"]: p["action"] for p in plan}
    check("plan: a clean ci/ branch is rebase-if-behind", by[1] == "rebase-if-behind", plan)
    check("plan: a human branch is never rewritten", by[2] == "human-branch" and by[5] == "human-branch" and by[9] == "human-branch", plan)
    check("plan: a CONFLICTING bot PR is reported, never auto-rebased", by[3] == "conflict", plan)
    check("plan: a draft is not touched at all", 4 not in by, plan)
    check("plan: the agent-session shapes (tech-debt-/data-gap-/issue-) are the sweep's to rebase",
          by[6] == "rebase-if-behind" and by[7] == "rebase-if-behind" and by[8] == "rebase-if-behind", plan)


def test_ownership_is_decided_by_author_not_branch_prefix():
    """Issue #1295: the §6s sweep missed agent PRs named fix/feat/rule and would rewrite a
    human PR named ci/. The AUTHOR decides, not the branch prefix. Issue #1349: the agent
    login is a GitHub *User*, so `is_bot` is `false` for a real agent PR — the login is
    checked too, and the fixture carries the LIVE spelling (`is_bot: False`)."""
    bot = {"login": "asimov-agent", "is_bot": False}  # the live shape (issue #1349)
    human = {"login": "andyholst", "is_bot": False}
    plan = PH.rebase_plan([
        pr(1, "fix/agent-owned", author=bot),
        pr(2, "feat/agent-owned", author=bot),
        pr(3, "rule/agent-owned", author=bot),
        pr(4, "ci/human-owned", author=human),
        pr(5, "tech-debt-human", author=human),
        pr(6, "fix/agent-conflict", author=bot, mergeable="CONFLICTING", state="DIRTY"),
        pr(7, "fix/no-author-data"),
        pr(8, "ci/no-author-data"),
    ])
    by = {p["number"]: p["action"] for p in plan}
    check("agent-authored fix/feat/rule PRs are the sweep's to rebase (#1295/#1349)",
          by[1] == "rebase-if-behind" and by[2] == "rebase-if-behind"
          and by[3] == "rebase-if-behind", plan)
    check("human-authored ci/tech-debt- PRs are reported, never rewritten (#1295)",
          by[4] == "human-branch" and by[5] == "human-branch", plan)
    check("a conflicting bot PR is still never auto-rebased", by[6] == "conflict", plan)
    check("no author data falls back to the prefix",
          by[7] == "human-branch" and by[8] == "rebase-if-behind", plan)
    src = SCRIPT.read_text(encoding="utf-8")
    check("the live gh query actually requests the author field",
          "headRefOid,author" in src, "")
    check("the fixture carries the live is_bot spelling (false for the agent login)",
          bot["is_bot"] is False, bot)


def test_agent_login_is_bot_owned_when_is_bot_is_false():
    """Issue #1349: the LIVE queue answers `author.is_bot == false` for every open PR,
    including the agent login `asimov-agent` (a GitHub *User*, not a Bot). A key on `is_bot`
    alone returned `{'human-branch': 22}` and the §6s rebaser never rebased anything."""
    check("an agent-login PR is bot-owned even with is_bot false (#1349)",
          PH.is_bot_owned({"author": {"login": "asimov-agent", "is_bot": False}}), "")
    check("a human login is never bot-owned, whatever the branch (#1295)",
          not PH.is_bot_owned({"author": {"login": "andyholst", "is_bot": False},
                               "headRefName": "ci/human"}), "")
    check("is_bot true is still sufficient",
          PH.is_bot_owned({"author": {"login": "someone", "is_bot": True}}), "")
    check("no author data still falls back to the prefix",
          PH.is_bot_owned({"headRefName": "ci/data-gap-1-x"})
          and not PH.is_bot_owned({"headRefName": "fix/no-author-data"}), "")
    src = SCRIPT.read_text(encoding="utf-8")
    check("the login set comes from the ONE identity module",
          "from agent_identity import AGENT_LOGINS" in src
          or "from scripts.agent_identity import AGENT_LOGINS" in src, "")


def _gitfx(cwd, *args):
    return subprocess.run(["git", "-C", str(cwd), *args], capture_output=True, text=True)


def _commit_fx(cwd, path, text, msg):
    (cwd / path).write_text(text, encoding="utf-8")
    _gitfx(cwd, "add", "-A")
    r = _gitfx(cwd, "-c", "user.name=fixture", "-c", "user.email=fixture@example.com",
               "commit", "-q", "-m", msg)
    assert r.returncode == 0, r.stderr


def test_a_behind_clean_bot_branch_is_rebased_and_pushed_and_a_human_branch_is_never_rewritten():
    """End-to-end through the REAL script against a REAL git remote (rule 6m: the external
    system is a local repository the real git talks to; only `gh` is stubbed).

    Planted: a behind-and-clean `ci/` PR branch, a behind HUMAN branch, a CONFLICTING `ci/`
    branch, and an already-current `ci/` branch. Done-when of issue #818: the first is
    rebased onto the base with its own commit intact; the others are byte-identical."""
    with tempfile.TemporaryDirectory() as d:
        td = Path(d)
        origin = td / "origin.git"
        assert _gitfx(td, "init", "--bare", "-q", str(origin)).returncode == 0
        seed = td / "seed"
        seed.mkdir()
        assert _gitfx(seed, "init", "-q", "-b", "master").returncode == 0
        _commit_fx(seed, "base.txt", "base\n", "base commit")
        base_oid = _gitfx(seed, "rev-parse", "HEAD").stdout.strip()
        _gitfx(seed, "remote", "add", "origin", str(origin))
        _gitfx(seed, "push", "-q", "origin", "master")

        # behind-and-clean bot branch (its file is nowhere else touched)
        _gitfx(seed, "checkout", "-q", "-b", "ci/data-gap-7-x", base_oid)
        _commit_fx(seed, "feature.txt", "feature\n", "feat: the PR's own commit")
        _gitfx(seed, "push", "-q", "origin", "ci/data-gap-7-x")

        # master moves ahead on a different file
        _gitfx(seed, "checkout", "-q", "master")
        _commit_fx(seed, "other.txt", "other\n", "master moves ahead")
        _gitfx(seed, "push", "-q", "origin", "master")

        # behind HUMAN-owned branch — must stay byte-identical
        _gitfx(seed, "checkout", "-q", "-b", "fix/human-behind", base_oid)
        _commit_fx(seed, "human.txt", "human\n", "human work")
        _gitfx(seed, "push", "-q", "origin", "fix/human-behind")

        # behind CONFLICTING bot branch (edits the same line master moved)
        _gitfx(seed, "checkout", "-q", "-b", "ci/clash-8-y", base_oid)
        _commit_fx(seed, "base.txt", "clash from the branch\n", "conflicting edit")
        _gitfx(seed, "push", "-q", "origin", "ci/clash-8-y")

        # already-current bot branch (cut from the CURRENT master tip, explicitly)
        _gitfx(seed, "checkout", "-q", "-b", "ci/current-9-z", "refs/remotes/origin/master")
        _commit_fx(seed, "fresh.txt", "fresh\n", "current work")
        _gitfx(seed, "push", "-q", "origin", "ci/current-9-z")

        clone = td / "clone"
        assert _gitfx(td, "clone", "-q", str(origin), str(clone)).returncode == 0

        def oid(ref):
            return _gitfx(clone, "rev-parse", ref).stdout.strip()

        before = {b: oid(f"refs/remotes/origin/{b}")
                  for b in ("ci/data-gap-7-x", "fix/human-behind", "ci/clash-8-y",
                            "ci/current-9-z", "master")}
        prs = [
            pr(7, "ci/data-gap-7-x", oid=before["ci/data-gap-7-x"]),
            pr(8, "ci/clash-8-y", mergeable="CONFLICTING", state="DIRTY",
               oid=before["ci/clash-8-y"]),
            pr(9, "ci/current-9-z", oid=before["ci/current-9-z"]),
            pr(10, "fix/human-behind", oid=before["fix/human-behind"]),
        ]
        runs = {p["headRefOid"]: 1 for p in prs}  # none silent: the rebaser is orthogonal
        with tempfile.TemporaryDirectory() as s:
            sd = Path(s)
            (sd / "gh").write_text(STUB, encoding="utf-8")
            (sd / "gh").chmod(0o755)
            (sd / "prs.json").write_text(json.dumps(prs), encoding="utf-8")
            (sd / "posted").write_text("")
            env = {**os.environ, "PATH": f"{sd}:{os.environ['PATH']}",
                   "FAKE_PRS": str(sd / "prs.json"), "FAKE_POSTED": str(sd / "posted")}
            for oid_, _ in runs.items():
                f = sd / "runs.json"
                f.write_text(json.dumps([{"databaseId": 1}]), encoding="utf-8")
                env[f"FAKE_RUNS_{oid_[:7]}"] = str(f)
            proc = subprocess.run(
                [sys.executable, str(SCRIPT), "--repo", "o/r", "--rebase",
                 "--dir", str(clone)], capture_output=True, text=True, env=env)
        check("rebaser: the run reports the rebase",
              "rebaser #7" in proc.stdout and "REBASED" in proc.stdout,
              proc.stdout + proc.stderr)
        _gitfx(clone, "fetch", "-q", "origin", "+refs/heads/*:refs/remotes/origin/*")
        check("rebaser: the behind clean ci/ branch now carries origin/master as an ancestor",
              _gitfx(clone, "merge-base", "--is-ancestor", "refs/remotes/origin/master",
                     "refs/remotes/origin/ci/data-gap-7-x").returncode == 0, "")
        log = _gitfx(clone, "log", "--oneline", "refs/remotes/origin/ci/data-gap-7-x").stdout
        check("rebaser: the branch's own commit survived the rebase",
              "feat: the PR's own commit" in log, log)
        check("rebaser: a human-owned branch is byte-identical (never rewritten)",
              oid("refs/remotes/origin/fix/human-behind") == before["fix/human-behind"], "")
        check("rebaser: a CONFLICTING bot branch is byte-identical (never auto-rebased)",
              oid("refs/remotes/origin/ci/clash-8-y") == before["ci/clash-8-y"], "")
        check("rebaser: an already-current branch is not churned",
              oid("refs/remotes/origin/ci/current-9-z") == before["ci/current-9-z"], "")
        check("rebaser: master itself is untouched",
              oid("refs/remotes/origin/master") == before["master"], "")


def test_the_rebaser_regenerates_the_index_on_the_rebased_tree():
    """Issue #1049: a sweep rebase regenerates `OPENSPEC.md` on the rebased tree
    BEFORE the lease push, and the regenerated file is the tree's OWN generator's
    output (`openspec-index --check` green on the pushed head).

    Measured: rebased bot branches 45fb245/5df9735/28bf765/9a5830a went red at
    `openspec-index-check` because their committed index predated archives that
    landed on master after the branch was cut — the sweep rebased them but never
    re-rendered the index."""
    with tempfile.TemporaryDirectory() as d:
        td = Path(d)
        origin = td / "origin.git"
        assert _gitfx(td, "init", "--bare", "-q", str(origin)).returncode == 0
        seed = td / "seed"
        seed.mkdir()
        assert _gitfx(seed, "init", "-q", "-b", "master").returncode == 0
        _commit_fx(seed, "base.txt", "base\n", "base commit")
        # the tree carries the REAL generator (and its one helper) + a valid
        # openspec/ change + the generated index, exactly as the product repo does
        (seed / "scripts").mkdir()
        shutil.copy(ROOT / "scripts" / "openspec_index.py", seed / "scripts" / "openspec_index.py")
        shutil.copy(ROOT / "scripts" / "task_boxes.py", seed / "scripts" / "task_boxes.py")
        (seed / "openspec" / "changes" / "change-one").mkdir(parents=True)
        (seed / "openspec" / "changes" / "change-one" / "proposal.md").write_text(
            "# Change One\n\nIssue: #7\n\n## Why\n\nFixture change.\n", encoding="utf-8")
        (seed / "openspec" / "changes" / "change-one" / "tasks.md").write_text(
            "# Tasks\n\n- [x] land one\n", encoding="utf-8")
        gen = subprocess.run([sys.executable, str(seed / "scripts" / "openspec_index.py"), "--write"],
                             capture_output=True, text=True, cwd=str(seed))
        assert gen.returncode == 0, gen.stderr
        _gitfx(seed, "add", "-A")
        r = _gitfx(seed, "-c", "user.name=fixture", "-c", "user.email=fixture@example.com",
                   "commit", "-q", "-m", "seed: openspec tree with a current index")
        assert r.returncode == 0, r.stderr
        base_oid = _gitfx(seed, "rev-parse", "HEAD").stdout.strip()
        _gitfx(seed, "remote", "add", "origin", str(origin))
        _gitfx(seed, "push", "-q", "origin", "master")

        # the PR branch: its committed OPENSPEC.md is CURRENT for the CUT-TIME tree
        _gitfx(seed, "checkout", "-q", "-b", "ci/data-gap-7-x", base_oid)
        _commit_fx(seed, "feature.txt", "feature\n", "feat: branch work")
        _gitfx(seed, "push", "-q", "origin", "ci/data-gap-7-x")
        branch_oid = _gitfx(seed, "rev-parse", "HEAD").stdout.strip()

        # master moves: the change gets ARCHIVED (the merge-wave shape)
        _gitfx(seed, "checkout", "-q", "master")
        (seed / "openspec" / "changes" / "archive").mkdir(parents=True, exist_ok=True)
        _gitfx(seed, "mv", "openspec/changes/change-one", "openspec/changes/archive/2026-11-16-one")
        _gitfx(seed, "-c", "user.name=Test Bot", "-c", "user.email=test-bot@example.com",
               "commit", "-q", "-m", "archive: the change closed on master")
        _gitfx(seed, "push", "-q", "origin", "master")

        clone = td / "clone"
        assert _gitfx(td, "clone", "-q", str(origin), str(clone)).returncode == 0

        prs = [pr(7, "ci/data-gap-7-x", oid=branch_oid)]
        sd = td / "stub"
        sd.mkdir()
        (sd / "gh").write_text(STUB, encoding="utf-8")
        (sd / "gh").chmod(0o755)
        (sd / "prs.json").write_text(json.dumps(prs), encoding="utf-8")
        (sd / "posted").write_text("", encoding="utf-8")
        runs_file = sd / "runs.json"
        runs_file.write_text(json.dumps([{"databaseId": 1}]), encoding="utf-8")
        env = {**os.environ, "PATH": f"{sd}:{os.environ['PATH']}",
               "FAKE_PRS": str(sd / "prs.json"), "FAKE_POSTED": str(sd / "posted"),
               "FAKE_COMMENTS": str(sd / "comments.json"),
               f"FAKE_RUNS_{branch_oid[:7]}": str(runs_file)}
        proc = subprocess.run([sys.executable, str(SCRIPT), "--repo", "o/r", "--rebase",
                               "--dir", str(clone)], capture_output=True, text=True, env=env)
        _gitfx(clone, "fetch", "-q", "origin", "+refs/heads/*:refs/remotes/origin/*")

        check("index-at-merge-time: the sweep reports the rebase AND the regeneration",
              "REBASED" in proc.stdout and "OPENSPEC.md regenerated" in proc.stdout,
              proc.stdout + proc.stderr)
        log = _gitfx(clone, "log", "--format=%s", "refs/remotes/origin/ci/data-gap-7-x").stdout
        check("index-at-merge-time: the regeneration commit is on the pushed head",
              "regenerate the index on the rebased tree" in log, log)
        head_index = _gitfx(clone, "show",
                            "refs/remotes/origin/ci/data-gap-7-x:OPENSPEC.md").stdout
        check("index-at-merge-time: the pushed index lists the archive, not an active change",
              "2026-11-16-one" in head_index and "Active changes: **0**" in head_index,
              head_index[:200])
        check("index-at-merge-time: the old committed index claimed an active change",
              "Active changes: **1**" in _gitfx(clone, "show",
                                                f"{branch_oid}:OPENSPEC.md").stdout)
        wt = td / "check-wt"
        _gitfx(clone, "worktree", "add", "--detach", str(wt), "refs/remotes/origin/ci/data-gap-7-x")
        chk = subprocess.run([sys.executable, str(wt / "scripts" / "openspec_index.py"), "--check"],
                             capture_output=True, text=True, cwd=str(wt))
        check("index-at-merge-time: openspec-index --check is GREEN on the pushed head",
              chk.returncode == 0, chk.stdout + chk.stderr)
        _gitfx(clone, "worktree", "remove", "--force", str(wt))


def test_a_failed_rebase_round_announces_on_the_pr_thread_once():
    """End-to-end (issue #964's Done-when): a rebase the sweep TRIED and git refused must
    leave an artifact ON the PR thread, not only a stdout line in a scheduled run's log.

    Planted: a behind `ci/` branch whose rebase git rejects while GitHub-side facts still say
    MERGEABLE/CLEAN (the measured shape — GitHub has not yet labelled the PR CONFLICTING, so
    the sweep attempts it), plus a behind-and-clean `ci/` branch that rebases fine. Round 1
    with --rebase --comment: exactly ONE marker-stamped comment on the failing PR naming the
    remedy, the failed branch byte-identical, and NOTHING posted for the landed rebase.
    Round 2 on the same (branch, head), seeing its own marker on the thread: nothing new."""
    with tempfile.TemporaryDirectory() as d:
        td = Path(d)
        origin = td / "origin.git"
        assert _gitfx(td, "init", "--bare", "-q", str(origin)).returncode == 0
        seed = td / "seed"
        seed.mkdir()
        assert _gitfx(seed, "init", "-q", "-b", "master").returncode == 0
        _commit_fx(seed, "base.txt", "base\n", "base commit")
        base_oid = _gitfx(seed, "rev-parse", "HEAD").stdout.strip()
        _gitfx(seed, "remote", "add", "origin", str(origin))
        _gitfx(seed, "push", "-q", "origin", "master")

        # behind-and-clean bot branch: rebases fine, must NOT be announced
        _gitfx(seed, "checkout", "-q", "-b", "ci/clean-12-b", base_oid)
        _commit_fx(seed, "feature.txt", "feature\n", "feat: clean work")
        _gitfx(seed, "push", "-q", "origin", "ci/clean-12-b")

        # master moves ahead ON THE FILE the other branch edits
        _gitfx(seed, "checkout", "-q", "master")
        _commit_fx(seed, "base.txt", "base moved on master\n", "master moves ahead")
        _gitfx(seed, "push", "-q", "origin", "master")

        # behind bot branch whose rebase git rejects — GitHub-side facts still CLEAN
        _gitfx(seed, "checkout", "-q", "-b", "ci/clash-11-a", base_oid)
        _commit_fx(seed, "base.txt", "clash from the branch\n", "conflicting edit")
        _gitfx(seed, "push", "-q", "origin", "ci/clash-11-a")

        clone = td / "clone"
        assert _gitfx(td, "clone", "-q", str(origin), str(clone)).returncode == 0

        def oid(ref):
            return _gitfx(clone, "rev-parse", ref).stdout.strip()

        before = {b: oid(f"refs/remotes/origin/{b}")
                  for b in ("ci/clash-11-a", "ci/clean-12-b", "master")}
        prs = [pr(11, "ci/clash-11-a", oid=before["ci/clash-11-a"]),
               pr(12, "ci/clean-12-b", oid=before["ci/clean-12-b"])]
        runs = {p["headRefOid"]: 1 for p in prs}  # none silent: the announcement is the rebaser's own

        sd = td / "stub"
        sd.mkdir()
        (sd / "gh").write_text(STUB, encoding="utf-8")
        (sd / "gh").chmod(0o755)
        (sd / "prs.json").write_text(json.dumps(prs), encoding="utf-8")
        (sd / "posted").write_text("", encoding="utf-8")
        (sd / "comments.json").write_text(json.dumps({"comments": []}), encoding="utf-8")

        def sweep():
            env = {**os.environ, "PATH": f"{sd}:{os.environ['PATH']}",
                   "FAKE_PRS": str(sd / "prs.json"), "FAKE_POSTED": str(sd / "posted"),
                   "FAKE_COMMENTS": str(sd / "comments.json")}
            runs_file = sd / "runs.json"
            runs_file.write_text(json.dumps([{"databaseId": 1}]), encoding="utf-8")
            for oid_ in runs:
                env[f"FAKE_RUNS_{oid_[:7]}"] = str(runs_file)
            return subprocess.run([sys.executable, str(SCRIPT), "--repo", "o/r",
                                   "--rebase", "--comment", "--dir", str(clone)],
                                  capture_output=True, text=True, env=env)

        proc = sweep()
        posted = (sd / "posted").read_text(encoding="utf-8")
        key = PH.rebase_run_key("ci/clash-11-a", before["ci/clash-11-a"])
        check("failed rebase: the run says git refused the attempt",
              "kept: rebase conflicted" in proc.stdout, proc.stdout + proc.stderr)
        check("failed rebase: the round announces itself on the PR thread",
              "announced the failed rebase" in proc.stdout, proc.stdout + proc.stderr)
        check("failed rebase: exactly ONE comment posted for the failed (branch, head)",
              posted.count(PH.REBASE_MARKER) == 1, posted[:400])
        rb = [h for h in PH.parse_markers(posted) if h["kind"] == "rebase_failed"]
        check("failed rebase: the comment carries the registered marker stamped with the failed pair",
              len(rb) == 1 and rb[0]["bot"] == "pr-health" and rb[0]["run"] == key,
              posted[:300])
        check("failed rebase: the comment names the failure and the concrete remedy",
              "rebase conflicted" in posted and "make base-rebase BRANCH=ci/clash-11-a" in posted
              and "worktree-resume" in posted, posted[:400])
        check("failed rebase: the remedy names the branch worktree as the invocation dir (#1335)",
              "cd <worktree for ci/clash-11-a>" in posted
              and "not the shared `master` clone" in posted, posted[:500])
        check("failed rebase: a LANDED rebase posts nothing",
              "ci/clean-12-b" not in posted, posted[:400])
        _gitfx(clone, "fetch", "-q", "origin", "+refs/heads/*:refs/remotes/origin/*")
        check("failed rebase: the failed branch stays byte-identical (never force-pushed)",
              oid("refs/remotes/origin/ci/clash-11-a") == before["ci/clash-11-a"], "")
        check("failed rebase: the clean branch still rebased fine",
              _gitfx(clone, "merge-base", "--is-ancestor", "refs/remotes/origin/master",
                     "refs/remotes/origin/ci/clean-12-b").returncode == 0, "")
        check("failed rebase: master itself is untouched",
              oid("refs/remotes/origin/master") == before["master"], "")

        # Round 2: the thread now carries this round's marker — nothing new is posted.
        (sd / "comments.json").write_text(json.dumps({"comments": [{"body": posted}]}),
                                          encoding="utf-8")
        proc2 = sweep()
        posted2 = (sd / "posted").read_text(encoding="utf-8")
        check("failed rebase: the same failed round is announced ONCE (shared marker parser dedups)",
              "already announced" in proc2.stdout and posted2 == posted,
              proc2.stdout + proc2.stderr)


def test_a_bound_draft_pr_is_named_with_its_issue():
    """Issue #1563: a DRAFT carrying a bound issue must be NAMED with that issue number.

    `findings` has always skipped drafts ("a draft is allowed to be quiet"), which is why
    nothing named a finished change parked as a draft. The verdict is the NEW pure seam,
    exercised over the real fixture shape: a GitHub `closingIssuesReferences` binding, and
    the issue its branch encodes as the fallback.
    """
    bound = pr(9, "fix/draft-with-issue", draft=True, closing=[1563])
    found = PH.draft_findings([bound])
    check("draft: a bound draft is reported", len(found) == 1, found)
    check("draft: it names the bound issue number", found[0]["issues"] == [1563], found)
    check("draft: it names the PR and its head", found[0]["number"] == 9
          and found[0]["head"] == "fix/draft-with-issue", found)
    check("draft: it names the rule (READY, never draft)",
          "READY" in found[0]["reasons"][0] and "draft" in found[0]["reasons"][0].lower(),
          found[0]["reasons"])
    # The branch-encoded fallback: no closingIssuesReferences, but the branch ends in -42.
    by_branch = PH.draft_findings([pr(10, "fix/foo-42", draft=True)])
    check("draft: a branch-encoded issue binds too",
          len(by_branch) == 1 and by_branch[0]["issues"] == [42], by_branch)
    # A ready PR is not a draft verdict, even with a bound issue.
    check("draft: a READY PR is never a draft verdict",
          PH.draft_findings([pr(11, "fix/ready-7", closing=[7])]) == [], "")
    # The full sweep NAMES the draft and its issue on stdout while keeping findings unchanged.
    proc, _ = run([bound], {})
    check("draft: the sweep prints the bound issue and the PR",
          "DRAFT #9" in proc.stdout and "#1563" in proc.stdout, proc.stdout)
    check("draft: the silent-PR verdict is unchanged (a draft is still not silent)",
          "0 silent" in proc.stdout, proc.stdout)


def test_a_bound_draft_pr_fails_the_draft_only_assertion():
    """Issue #1563: the CI-side assertion exits 1 on a bound draft, 0 otherwise."""
    # Given the real CLI with --draft-only, a stub gh answering a bound draft (offline)
    bound = pr(12, "fix/draft-99", draft=True, closing=[99])
    proc, _ = run([bound], {}, extra=["--draft-only"])
    check("draft-only: a bound draft is a RED gate", proc.returncode == 1,
          proc.stdout + proc.stderr)
    check("draft-only: it still NAMES the issue", "#99" in proc.stdout, proc.stdout)
    # An unbound draft (unfinished work) is green — report status, never open a PR.
    proc, _ = run([pr(13, "fix/unfinished", draft=True)], {}, extra=["--draft-only"])
    check("draft-only: an unbound draft is NOT a gate", proc.returncode == 0, proc.stdout)
    # A ready PR with a bound issue is green.
    proc, _ = run([pr(14, "fix/ready-8", closing=[8])], {}, extra=["--draft-only"])
    check("draft-only: a ready PR with a bound issue is green", proc.returncode == 0,
          proc.stdout)
    # --help documents the ready-for-review rule.
    helper = subprocess.run([sys.executable, str(SCRIPT), "--help"],
                            capture_output=True, text=True)
    check("draft-only: --help names the ready-for-review rule",
          "--draft-only" in helper.stdout
          and "ready" in helper.stdout.lower() and "draft" in helper.stdout.lower(),
          helper.stdout)


def test_an_unbound_draft_is_not_a_stall():
    """A genuine unfinished draft binds no issue: it is not named and stays out of the gate."""
    check("draft: no bound issue, no verdict",
          PH.draft_findings([pr(15, "fix/wip", draft=True)]) == [], "")
    # A keeper/refresh branch encodes no issue even when its head carries a number elsewhere.
    check("draft: a refresh branch does not encode an issue",
          PH.bound_issues({"headRefName": "ci/trending-refresh-20261124",
                           "closingIssuesReferences": []}) == [], "")


def test_the_ready_rule_is_wired_to_the_makefile_and_workflow():
    """The rule reaches the fleet through the existing Makefile + pr-health workflow."""
    mk = (ROOT / "Makefile").read_text()
    check("wiring: make pr-draft-check calls the --draft-only seam",
          "_pr-draft-check:" in mk and "--draft-only" in mk
          and "pr-draft-check: ##" in mk, "")
    wf = (ROOT / ".github" / "workflows" / "pr-health.yml").read_text()
    check("wiring: the pr-health workflow runs make pr-draft-check",
          "run: make pr-draft-check" in wf, "")
    check("wiring: no new schedule: trigger was added to pr-health.yml",
          "\n  schedule:" not in wf, wf[:400])


def test_the_lane_skills_say_open_every_pr_ready_never_draft():
    """The rule is stated in BOTH lane contracts the planner and implementer read."""
    for lane in ("tll-planner", "tll-implementer"):
        text = (ROOT / "agents" / lane / "skills" / lane / "SKILL.md").read_text()
        check(f"skill: {lane} says open every PR READY (never draft)",
              "Open every PR READY (never draft)" in text, "")
        check(f"skill: {lane} says unfinished work is reported, not opened as a draft",
              "report status on the issue instead of opening a PR" in text, "")


def main() -> int:
    print("silent PR alarm (issue #442)")
    test_a_conflicting_pr_is_silent_and_named()
    test_a_healthy_pr_is_not_flagged()
    test_a_pr_whose_pipeline_never_started_is_flagged_too()
    test_a_pr_whose_runs_are_all_held_for_approval_is_flagged()
    test_a_held_pr_and_a_ran_pr_are_separated()
    test_the_hold_comment_names_the_human_approval_remedy()
    test_drafts_are_left_alone()
    test_the_comment_carries_the_fix_and_is_deduplicated()
    test_the_decision_is_pure_and_the_reasons_are_separate()
    test_a_gh_failure_is_loud()
    test_the_sweep_is_wired_to_a_target_a_workflow_and_a_guard()
    test_a_silent_pr_is_reported_and_nothing_is_dispatched()
    test_an_empty_setting_means_missing()
    test_the_real_target_runs_report_only()
    test_no_script_reads_a_number_straight_from_the_environment()
    test_rebase_plan_classifies_by_ownership_and_conflict()
    test_ownership_is_decided_by_author_not_branch_prefix()
    test_agent_login_is_bot_owned_when_is_bot_is_false()
    test_a_behind_clean_bot_branch_is_rebased_and_pushed_and_a_human_branch_is_never_rewritten()
    test_the_rebaser_regenerates_the_index_on_the_rebased_tree()
    test_a_failed_rebase_round_announces_on_the_pr_thread_once()
    test_a_bound_draft_pr_is_named_with_its_issue()
    test_a_bound_draft_pr_fails_the_draft_only_assertion()
    test_an_unbound_draft_is_not_a_stall()
    test_the_ready_rule_is_wired_to_the_makefile_and_workflow()
    test_the_lane_skills_say_open_every_pr_ready_never_draft()
    print(f"\nPASSED {_PASS} | FAILED {_FAIL}")
    return 1 if _FAIL else 0


if __name__ == "__main__":
    raise SystemExit(main())
