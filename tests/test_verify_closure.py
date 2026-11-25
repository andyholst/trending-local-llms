#!/usr/bin/env python3
"""After the merge: is the issue the PR claimed to close actually CLOSED? (issue #288)

`make pr-closure` PREDICTS the closure from GitHub's parser semantics; it cannot prove the
outcome. Measured on PR #272: `Closes #271 and #276` closed #271 and left #276 open after the
merge, and every job stayed green.

These tests run the REAL script against a stub `gh` on PATH (an EXTERNAL system: the GitHub API
is what the script talks to, and the script's own request building and decision still run).

Run:  python3 tests/test_verify_closure.py   or   make test
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "scripts" / "verify_closure.py"
WORKFLOW = ROOT / ".github" / "workflows" / "qa-validate.yml"
PAT = "secrets.FIXBOT_DISPATCH_TOKEN"

_PASS = 0
_FAIL = 0

#: A stub `gh`: it answers `pr view` from $FAKE_PR_JSON and `issue view` from
#: $FAKE_ISSUE_<n>_JSON, so the script's parsing and decision are the real ones.
STUB = """#!/bin/sh
case "$1 $2" in
  "pr view") cat "$FAKE_PR_JSON" ;;
  "issue view") eval "cat \\${FAKE_ISSUE_${3}_JSON}" ;;
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


def run(pr: dict, issues: dict[int, str] | None = None, **env_extra):
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        (td / "pr.json").write_text(json.dumps(pr))
        env = {**os.environ, "PATH": f"{td}:{os.environ['PATH']}",
               "FAKE_PR_JSON": str(td / "pr.json"),
               "VERIFY_CLOSURE_ATTEMPTS": "1", "VERIFY_CLOSURE_DELAY_S": "0", **env_extra}
        for n, state in (issues or {}).items():
            f = td / f"issue{n}.json"
            f.write_text(json.dumps({"state": state}))
            env[f"FAKE_ISSUE_{n}_JSON"] = str(f)
        (td / "gh").write_text(STUB)
        (td / "gh").chmod(0o755)
        return subprocess.run([sys.executable, str(SCRIPT), "--pr", "272", "--repo", "o/r"],
                              capture_output=True, text=True, env=env)


def test_a_merge_that_closed_its_issue_passes():
    proc = run({"state": "MERGED", "body": "closes #271", "closingIssuesReferences": [
        {"number": 271, "state": "CLOSED"}]})
    check("closure: a merged PR whose issue closed exits 0", proc.returncode == 0, proc.stderr)
    check("closure: it says so", "closed all 1 issue" in proc.stdout, proc.stdout)


def test_a_merge_that_left_the_issue_open_fails_loudly():
    # The measured PR #272 shape: the body chained two references, one bound, one did not.
    proc = run({"state": "MERGED", "body": "Closes #271 and #276",
                "closingIssuesReferences": [{"number": 271, "state": "CLOSED"},
                                            {"number": 276}]},
               issues={276: "OPEN"})
    check("closure: an issue left OPEN fails the job", proc.returncode == 1, proc.stdout)
    check("closure: the message names the issue and its state",
          "#276" in proc.stderr and "OPEN" in proc.stderr, proc.stderr)
    check("closure: it names the rule the body broke", "rule 6e" in proc.stderr, proc.stderr)


def test_a_reference_without_a_state_is_read_from_the_issue():
    proc = run({"state": "MERGED", "body": "closes #9", "closingIssuesReferences": [{"number": 9}]},
               issues={9: "CLOSED"})
    check("closure: a missing state is fetched from the issue", proc.returncode == 0,
          proc.stdout + proc.stderr)


def test_a_pr_that_closes_nothing_is_not_a_failure():
    proc = run({"state": "MERGED", "body": "references #304, no closing keyword",
                "closingIssuesReferences": []})
    check("closure: a PR that closes nothing exits 0", proc.returncode == 0, proc.stderr)
    check("closure: … and says so", "claims to close no issue" in proc.stdout, proc.stdout)


def test_an_unreadable_state_is_loud_never_a_pass():
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        (td / "gh").write_text("#!/bin/sh\necho 'HTTP 403' >&2\nexit 1\n")
        (td / "gh").chmod(0o755)
        env = {**os.environ, "PATH": f"{td}:{os.environ['PATH']}"}
        proc = subprocess.run([sys.executable, str(SCRIPT), "--pr", "1"],
                              capture_output=True, text=True, env=env)
    check("closure: a gh failure is a LOUD exit, not a pass", proc.returncode != 0, proc.stdout)
    check("closure: the refusal quotes gh", "exited 1" in proc.stderr, proc.stderr)


def test_the_check_is_wired_to_a_target_and_the_merge_job():
    mk = (ROOT / "Makefile").read_text()
    check("closure: a make target runs the script",
          "python3 scripts/verify_closure.py" in mk, "")
    wf = (ROOT / ".github" / "workflows" / "qa-validate.yml").read_text()
    check("closure: the merge job verifies what it closed", "make verify-closure" in wf, "")


def _auto_merge_steps(text: str) -> list[dict]:
    return yaml.safe_load(text)["jobs"]["auto-merge"]["steps"]


def _closure_wiring_problems(steps: list[dict], permissions: dict) -> list[str]:
    """The closure proof must read ISSUES with a credential that can, and the squash
    must keep its owner-PAT path byte-identical (issue #1677).

    `scripts/verify_closure.py::open_references` falls through to
    `gh issue view <n> --json state` whenever a `closingIssuesReferences` entry omits
    `state` — which GitHub always omits (measured on PRs #1658 / #1670) — so the proof
    needs a token with the Issues scope. The owner PAT declares none (AGENTS.md §6b),
    and the pre-#1677 wiring ran the proof inside the squash step under that PAT: the
    read answered `HTTP 401: Bad credentials` AFTER the squash had already landed.
    """
    problems: list[str] = []
    verify = [s for s in steps if "make verify-closure" in str(s.get("run", ""))]
    if len(verify) != 1:
        return [f"auto-merge: {len(verify)} steps run `make verify-closure` (want exactly one)"]
    token = str((verify[0].get("env") or {}).get("GH_TOKEN", ""))
    if not token:
        problems.append("the closure proof runs with NO GH_TOKEN — `gh` would answer 401")
    elif PAT in token:
        problems.append(
            f"the closure proof runs under the owner PAT ({PAT}), which carries no Issues "
            "scope (§6b): its `gh issue view <n> --json state` answers HTTP 401 after a merge")
    elif "github.token" not in token:
        problems.append(f"the closure proof runs under {token!r}, not the default github.token")
    perms = permissions or {}
    for scope in ("issues", "pull-requests"):
        if str(perms.get(scope, "")).lower() != "read":
            problems.append(
                f"auto-merge job permissions lack `{scope}: read` — the proof reads issues "
                "AND the PR itself")

    merge = [s for s in steps if "gh pr merge" in str(s.get("run", ""))]
    if len(merge) != 1:
        problems.append(f"auto-merge: {len(merge)} steps squash-merge (want exactly one)")
    else:
        env = merge[0].get("env") or {}
        run = str(merge[0].get("run", ""))
        if PAT not in str(env.get("GH_TOKEN", "")):
            problems.append("the squash no longer merges under the owner PAT — the merge path moved")
        for needle in ("--squash", "--delete-branch", "--match-head-commit"):
            if needle not in run:
                problems.append(f"the squash lost {needle} — the squash path is not byte-identical")
    return problems


def test_the_merge_job_proves_closure_with_a_credential_that_can_read_issues():
    """Issue #1677: the post-squash proof must not inherit the owner PAT.

    RED on the old wiring (the proof inside the squash step, under the PAT that has no
    Issues scope) and GREEN only when the proof carries the default token with the
    scopes it reads.
    """
    doc = yaml.safe_load(WORKFLOW.read_text())
    job = doc["jobs"]["auto-merge"]
    steps = job["steps"]

    check("closure: the auto-merge job carries exactly one closure-proof step",
          len([s for s in steps if "make verify-closure" in str(s.get("run", ""))]) == 1)
    shipped = _closure_wiring_problems(steps, job.get("permissions"))
    check("closure: the shipped wiring reads issues with a credential that can", shipped == [], shipped)

    # Planted: the proof moved back under the owner PAT (the pre-#1677 shape).
    planted_doc = yaml.safe_load(WORKFLOW.read_text())
    planted = planted_doc["jobs"]["auto-merge"]
    for s in planted["steps"]:
        if "make verify-closure" in str(s.get("run", "")):
            s.setdefault("env", {})["GH_TOKEN"] = "${{ " + PAT + " }"
    planted_problems = _closure_wiring_problems(planted["steps"], planted.get("permissions"))
    check("closure: a proof under the owner PAT is refused by this guard",
          any("no Issues scope" in p for p in planted_problems), planted_problems)

    # Planted: the proof dropped the default token AND the job its scopes.
    bare_doc = yaml.safe_load(WORKFLOW.read_text())
    bare = bare_doc["jobs"]["auto-merge"]
    for s in bare["steps"]:
        if "make verify-closure" in str(s.get("run", "")):
            (s.get("env") or {}).pop("GH_TOKEN", None)
    bare["permissions"] = {"contents": "write"}
    bare_problems = _closure_wiring_problems(bare["steps"], bare.get("permissions"))
    check("closure: a keyless proof and a job without the read scopes are refused",
          any("NO GH_TOKEN" in p for p in bare_problems)
          and sum("read`" in p for p in bare_problems) >= 2, bare_problems)

    # The guard is RED on origin/master's wiring (rule 6c).
    base = subprocess.run(["git", "-C", str(ROOT), "show",
                           "origin/master:.github/workflows/qa-validate.yml"],
                          capture_output=True, text=True)
    if base.returncode == 0:
        base_problems = _closure_wiring_problems(
            _auto_merge_steps(base.stdout), yaml.safe_load(base.stdout)["jobs"]["auto-merge"].get("permissions"))
        check("closure: origin/master's PAT-wired proof is refused by this guard",
              bool(base_problems), base_problems)


def main() -> int:
    print("verify the issue actually closed (issue #288)")
    test_a_merge_that_closed_its_issue_passes()
    test_a_merge_that_left_the_issue_open_fails_loudly()
    test_a_reference_without_a_state_is_read_from_the_issue()
    test_a_pr_that_closes_nothing_is_not_a_failure()
    test_an_unreadable_state_is_loud_never_a_pass()
    test_the_check_is_wired_to_a_target_and_the_merge_job()
    test_the_merge_job_proves_closure_with_a_credential_that_can_read_issues()
    print(f"\nPASSED {_PASS} | FAILED {_FAIL}")
    return 1 if _FAIL else 0


if __name__ == "__main__":
    raise SystemExit(main())
