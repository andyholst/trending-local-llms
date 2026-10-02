#!/usr/bin/env python3
"""Workflow wiring tests: refresh-bot -> qa-validate -> fix-bot.

Every one of these encodes a failure that actually happened in CI and that no
data test could see:

  - refresh PR authored by github-actions[bot] -> qa-validate held for a manual
    approval click (needs the owner PAT on checkout + `gh pr create`)
  - fix-bot dispatched at PR-open, before validation existed, without the
    failure report (must be dispatched by qa-validate, after `validate` fails)
  - fix-bot `workflow_run` trigger silently suppressed / double-firing
  - fix-bot looping under `bash -e`, never running `make validate`, committing
    with no git identity, pushing with GITHUB_TOKEN (CI never re-runs)
  - nothing live-tested the search / Hermes path on a PR

Parses the REAL .github/workflows/*.yml with PyYAML.

Run:  python3 tests/test_workflows.py   or   make test
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WF = ROOT / ".github" / "workflows"

try:
    import yaml
except ImportError:  # pragma: no cover
    print("SKIP: PyYAML not installed (it is in requirements-test.txt)")
    raise SystemExit(0)

PAT = "secrets.FIXBOT_DISPATCH_TOKEN"
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


def load(name: str) -> dict:
    d = yaml.safe_load((WF / name).read_text())
    # PyYAML (YAML 1.1) parses the bare key `on` as boolean True
    if True in d and "on" not in d:
        d["on"] = d.pop(True)
    return d


def steps(job: dict) -> list[dict]:
    return job.get("steps", [])


def step(job: dict, needle: str) -> dict:
    for s in steps(job):
        if needle.lower() in s.get("name", "").lower():
            return s
    return {}


def run_text(job: dict) -> str:
    return "\n".join(s.get("run", "") for s in steps(job))


def test_refresh_bot():
    wf = load("refresh-bot.yml")
    search = wf["jobs"]["search"]
    agg = wf["jobs"]["aggregate"]
    check("refresh: search matrix is exactly nvidia/metal/cpu",
          search["strategy"]["matrix"]["backend"] == ["nvidia", "metal", "cpu"],
          search["strategy"]["matrix"])
    order = [s.get("run", "").strip() for s in steps(search) if s.get("run")]
    def idx(sub):
        return next((i for i, r in enumerate(order) if sub in r), -1)
    check("refresh: 3s reachability smoke runs before the search",
          0 <= idx("_search-smoke") < idx("make search-"), order)
    check("refresh: hermes routing smoke runs before the search",
          0 <= idx("make hermes-smoke") < idx("make search-"), order)
    check("refresh: model-caps check runs before the search",
          0 <= idx("make model-caps") < idx("make search-"), order)
    checkout = step(agg, "checkout")
    check("refresh: aggregate checkout uses the owner PAT (push as owner)",
          PAT in str(checkout.get("with", {}).get("token", "")), checkout)
    pr = step(agg, "open PR")
    check("refresh: PR is created with the owner PAT (no approval gate)",
          PAT in str(pr.get("env", {}).get("GH_TOKEN", "")), pr.get("env"))
    check("refresh: does NOT dispatch fix-bot itself (qa-validate does, after validating)",
          "gh workflow run" not in run_text(agg), "")
    check("refresh: aggregate runs even if a search leg failed", "always()" in str(agg.get("if", "")), agg.get("if"))


def test_qa_validate():
    wf = load("qa-validate.yml")
    jobs = wf["jobs"]
    pr_paths = wf["on"]["pull_request"].get("paths", [])
    check("qa: workflow-only PRs are validated too (no !.github/** exclusion)",
          "!.github/**" not in pr_paths, pr_paths)
    v = run_text(jobs["validate"])
    for t in ("make validate", "make validate-search", "make validate-mapped", "make test"):
        check(f"qa: validate job runs `{t}`", t in v, "")
    check("qa: validate job has no network-dependent targets",
          "validate-fetch" not in v and "smoke" not in v, v)
    live = run_text(jobs.get("live-smoke", {}))
    for b in ("nvidia", "metal", "cpu"):
        check(f"qa: live search smoke for {b}", f"BACKEND={b}" in live, "")
    check("qa: live hermes routing smoke", "make hermes-smoke" in live, "")
    check("qa: live model-caps check", "make model-caps" in live, "")
    check("qa: live --require-hits search", "make validate-fetch" in live, "")
    d = jobs.get("dispatch-fixbot", {})
    cond = str(d.get("if", ""))
    check("qa: dispatch-fixbot needs the deterministic validate job",
          d.get("needs") in ("validate", ["validate"]), d.get("needs"))
    check("qa: dispatch-fixbot only on failure", "failure()" in cond, cond)
    check("qa: dispatch-fixbot only for refresh PR branches", "ci/trending-refresh-" in cond, cond)
    check("qa: dispatch-fixbot only for same-repo PRs", "head.repo.full_name" in cond, cond)
    ds = (steps(d) or [{}])[0]
    check("qa: dispatch uses the owner PAT (GITHUB_TOKEN gets HTTP 403)",
          PAT in str(ds.get("env", {}).get("GH_TOKEN", "")), ds.get("env"))
    check("qa: dispatch passes pr_number + branch", "pr_number=" in ds.get("run", "") and "branch=" in ds.get("run", ""), "")
    check("qa: dispatch capped by prior fix-bot commits", "MAX_FIXBOT_COMMITS" in ds.get("run", ""), "")


def test_fix_bot():
    wf = load("fix-bot.yml")
    on = wf["on"]
    check("fix: no workflow_run trigger (double-fire / suppressed for bot PRs)",
          "workflow_run" not in on, list(on))
    check("fix: dispatchable with pr_number + branch",
          {"pr_number", "branch"} <= set((on.get("workflow_dispatch") or {}).get("inputs", {})), "")
    check("fix: one run per PR at a time", "concurrency" in wf, "")
    job = wf["jobs"]["fix"]
    resolve = step(job, "resolve")
    check("fix: refuses master/main", "master|main" in resolve.get("run", ""), "")
    co = step(job, "checkout")
    check("fix: checkout with owner PAT (push re-triggers qa-validate)",
          PAT in str(co.get("with", {}).get("token", "")), co.get("with"))
    rt = run_text(job)
    check("fix: hermes routing smoke before the loop", "make hermes-smoke" in rt, "")
    loop = step(job, "fix loop")
    check("fix: runs scripts/fix_loop.sh", "scripts/fix_loop.sh" in loop.get("run", ""), "")
    check("fix: loop step tolerates a red loop (set +e) and reports green/red",
          "set +e" in loop.get("run", "") and "green=" in loop.get("run", ""), "")
    push = step(job, "commit + push")
    check("fix: push gated on a green loop", "green == 'true'" in str(push.get("if", "")), push.get("if"))
    check("fix: git identity configured before commit",
          "git config user.name" in push.get("run", "") and "git config user.email" in push.get("run", ""), "")
    check("fix: commit message prefix matches qa-validate's cap counter",
          'git commit -m "fix-bot:' in push.get("run", ""), "")
    check("fix: qa-report.txt is never committed", ":!qa-report.txt" in push.get("run", ""), "")
    rep = step(job, "report result")
    check("fix: result always reported on the PR",
          "always()" in str(rep.get("if", "")) and "gh pr comment" in rep.get("run", ""), "")


def _deps(jobs: dict, name: str) -> set:
    """All jobs `name` depends on, transitively."""
    out, todo = set(), [name]
    while todo:
        n = jobs[todo.pop()].get("needs", [])
        for d in ([n] if isinstance(n, str) else n):
            if d not in out:
                out.add(d)
                todo.append(d)
    return out


def _guard_ok(run: str) -> bool:
    return ("github.repository_owner" in run or "$OWNER" in run) and "TRIGGER" in run and "ACTOR" in run


def test_owner_guards():
    """#67: every refresh-bot job is gated by an owner check that also covers
    re-runs (triggering_actor); aggregate can't run on a refused guard; fix-bot
    checks the owner before any step that touches a secret."""
    wf = load("refresh-bot.yml")
    jobs = wf["jobs"]
    g = jobs.get("guard", {})
    gstep = (steps(g) or [{}])[0]
    genv = gstep.get("env", {})
    check("access: refresh-bot has a 'guard' job", bool(g), list(jobs))
    check("access: guard compares actor AND triggering_actor to the owner",
          "github.actor" in str(genv.get("ACTOR")) and "github.triggering_actor" in str(genv.get("TRIGGER"))
          and "repository_owner" in str(genv.get("OWNER")) and _guard_ok(gstep.get("run", "")), genv)
    check("access: guard lets the daily schedule through", '"schedule"' in gstep.get("run", ""))
    check("access: guard uses env, not inline ${{ }} in the script (no injection)",
          "${{" not in gstep.get("run", ""))
    for name in jobs:
        if name != "guard":
            check(f"access: refresh-bot job '{name}' depends on guard", "guard" in _deps(jobs, name), _deps(jobs, name))
    cond = str(jobs["aggregate"].get("if", ""))
    check("access: aggregate requires guard success (not bare always())",
          "needs.guard.result == 'success'" in cond, cond)
    check("access: aggregate requires build success", "needs.build.result == 'success'" in cond, cond)
    conc = wf.get("concurrency", {})
    check("concurrency: refresh-bot runs queue (group set, no cancel)",
          bool(conc.get("group")) and conc.get("cancel-in-progress") is False, conc)

    fb = load("fix-bot.yml")["jobs"]["fix"]
    first = (steps(fb) or [{}])[0]
    check("access: fix-bot's FIRST step is the owner guard", "owner" in first.get("name", "").lower(), first.get("name"))
    check("access: fix-bot guard checks actor AND triggering_actor",
          "github.triggering_actor" in str(first.get("env", {}).get("TRIGGER")) and _guard_ok(first.get("run", "")))
    secret_steps = [i for i, st in enumerate(steps(fb)) if "secrets." in str(st)]
    check("access: no fix-bot step uses a secret before the guard", min(secret_steps or [99]) > 0, secret_steps)


def test_nothing_pushes_master():
    for f in sorted(WF.glob("*.yml")):
        t = f.read_text()
        bad = [l.strip() for l in t.splitlines()
               if "git push" in l and ("master" in l or "main" in l)]
        check(f"no-master: {f.name} never pushes master/main", not bad, bad)
        check(f"no-master: {f.name} never merges a PR", "gh pr merge" not in t, "")


def main() -> int:
    print("workflow wiring: refresh-bot -> qa-validate -> fix-bot")
    test_refresh_bot()
    test_qa_validate()
    test_fix_bot()
    test_owner_guards()
    test_nothing_pushes_master()
    print(f"\nPASSED {_PASS} | FAILED {_FAIL}")
    return 1 if _FAIL else 0


if __name__ == "__main__":
    raise SystemExit(main())
