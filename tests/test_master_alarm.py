#!/usr/bin/env python3
"""Hermetic checks for the red-master alarm (issue #527).

A deterministic gate in qa-validate's `validate` job runs on a `push` to master as well as on
PRs, and every repair path in this repo needs a PR — `dispatch-fixbot` (refresh/data-gap branches
only), `fix-bot` (refuses non-PR), `pr-health` (sweeps open PRs), `architecture-bot` (repairs only
ARCHITECTURE.md + OPENSPEC.md). So a gate that reds master AFTER `auto-merge` has no repairer and
stays silent until a human notices (measured: run 39625708799). This locks the ALARM's decision
(scripts/master_alarm.py) with a fake `gh` on PATH (the product's own code runs), plus the
KEEPER/ALARM table that the issue's "Done when" demands — `make test` FAILS when a gate in the
validate job is on neither list:

  1. a red newest push-to-master run is reported (exit 1) naming the run URL;
  2. a green / pending / absent run is not an alarm;
  3. EVERY `make <target>` the validate job runs is on the keeper OR the alarm list — a NEW gate
     added to the validate job without landing on one of the two lists reds this suite;
  4. the workflow guards first and calls `make master-alarm`;
  5. the make target is real and passes REPO/LIMIT through;
  6. AGENTS.md carries the alarm's rule and its section-8 guard row.

Run standalone: python3 tests/test_master_alarm.py   or   make test
"""
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import master_alarm as a  # noqa: E402

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


def _wf_text() -> str:
    text = (WF / "qa-validate.yml").read_text()
    return text.split("  validate:\n")[1].split("  live-smoke:\n")[0]


def _run_list_payload(runs):
    return json.dumps(runs)


def _fake_gh(runs, jobs=None):
    """A `gh` on PATH answering exactly the calls the alarm builds."""
    td = Path(tempfile.mkdtemp())
    gh = td / "gh"
    runs_json = _run_list_payload(runs)
    jobs_json = json.dumps({"jobs": jobs or []})
    gh.write_text(f"""#!/usr/bin/env bash
echo "$@" >> "{td}/calls"
args="$*"
case "$1 $2" in
  "run list") cat "{td}/runs"; exit 0 ;;
  "run view") id=$(echo "$args" | grep -oE '[0-9]+' | head -1); cat "{td}/jobsid$id"; exit 0 ;;
esac
exit 0
""")
    gh.chmod(0o755)
    (td / "runs").write_text(runs_json)
    # per-run jobs files so run view picks the right one
    for i, rj in enumerate(jobs or []):
        rid = (runs[i].get("databaseId") or 1) if i < len(runs) else 1
        (td / f"jobsid{rid}").write_text(json.dumps({"jobs": rj}))
    (td / "calls").write_text("")
    return td


def _set_path(td: Path):
    os.environ["PATH"] = f"{td}{os.pathsep}{os.environ['PATH']}"


def _green_run(rid=99):
    return {"databaseId": rid, "createdAt": "2026-11-11T00:00:00Z", "conclusion": "success",
            "status": "completed", "url": f"https://github.com/o/r/actions/runs/{rid}",
            "headBranch": "master", "displayTitle": "Merge pull request"}


def _red_run(rid=98):
    r = _green_run(rid)
    r["conclusion"] = "failure"
    return r


def test_a_red_run_is_reported():
    td = _fake_gh([_red_run()], [[{"name": "validate", "conclusion": "failure"}]])
    _set_path(td)
    rc, msg = a.verdict("o/r")
    check("alarm: a red newest push-to-master run exits 1", rc == 1, rc)
    check("alarm: the message names the run URL", "actions/runs/98" in msg, msg)
    check("alarm: the message names the failing job", "validate" in msg, msg)


def test_a_green_or_pending_or_absent_run_is_not_an_alarm():
    td = _fake_gh([_green_run()], [[{"name": "validate", "conclusion": "success"}]])
    _set_path(td)
    rc, msg = a.verdict("o/r")
    check("alarm: a green run exits 0", rc == 0, msg)

    pending = _green_run(97)
    pending["conclusion"] = None
    pending["status"] = "in_progress"
    td = _fake_gh([pending], [[{"name": "validate", "conclusion": None}]])
    _set_path(td)
    rc, msg = a.verdict("o/r")
    check("alarm: a pending run is not an alarm", rc == 0, msg)

    td = _fake_gh([])
    _set_path(td)
    rc, msg = a.verdict("o/r")
    check("alarm: no push-to-master run is not an alarm", rc == 0, msg)


def test_every_validate_gate_is_on_a_list():
    """The issue's core 'Done when': `make test` fails if a gate in validate is on neither list.

    Every `make <target>` the validate job runs must be a key of the master_alarm.GATES
    registry (a keeper or an alarm). A NEW gate added to the validate job without a registry
    entry reds this suite, so a gate can never again go red on master with no keeper and no
    alarm.
    """
    wf_text = _wf_text()
    unchecked = a.unchecked_gates(wf_text)
    check("gates: every validate-job `make` gate is on the keeper OR alarm list",
          not unchecked, f"uncovered={unchecked}")
    # keepers must actually name the bot that repairs the artifact (issue #479/#526).
    for gate in a.KEEPERS:
        keeper = a.GATES[gate][1]
        check(f"gates: keeper {gate!r} names a real repair pathway",
              keeper == "architecture-bot", f"{gate}->{keeper}")
    # the two lists are jointly exhaustive and disjoint over the registry.
    check("gates: keeper and alarm lists partition the registry",
          a.KEEPERS | a.ALARMED == set(a.GATES) and a.KEEPERS & a.ALARMED == set(),
          f"keep={a.KEEPERS} alarm={a.ALARMED}")


def test_every_validate_step_target_is_a_gate_of_the_validate_job():
    """The registry must not be silently empty: the real validate job names real gates."""
    wf_text = _wf_text()
    gates = a.validate_gates_from_trees(wf_text)
    check("gates: the validate job yields at least the known gates",
          {"architecture-check", "validate", "openspec-check", "test"} <= set(gates),
          gates)


def test_the_workflow_guards_first_and_calls_the_make_target():
    text = (WF / "queued-alarm.yml").read_text()
    jobs = re.search(r"^jobs:\n(.*)", text, re.S | re.M).group(1)
    first_job = next(l for l in jobs.splitlines()
                     if l.strip() and not l.lstrip().startswith("#"))
    check("wf: guard is the first job", first_job.lstrip().startswith("guard:"), first_job[:40])
    check("wf: the guard admits the bot itself", 'github-actions[bot]' in text)
    check("wf: the guard lets a scheduled run through", '"schedule"' in text)
    check("wf: it calls make master-alarm", "make master-alarm REPO=" in text)
    check("wf: it never runs a repo script directly",
          not re.search(r"^\s*python3 scripts/", text, re.M))
    check("wf: it has its own concurrency group", "group: queued-alarm" in text)
    check("wf: master-alarm itself uses github.token, not the owner PAT",
          # (issue #802 widened this from whole-file to step-scoped: the ledger-landing step
          # legitimately carries the owner PAT to push + open the ledger PR, the architecture-bot
          # pattern; what must NEVER carry it is the read-only master-alarm step itself)
          all("secrets.FIXBOT_DISPATCH_TOKEN" not in step
              for step in re.findall(r"- name: Fail loudly when the newest push-to-master.*?(?=\n      - name:|\n  [a-z]+:\n)", text, re.S))
          and "GH_TOKEN: ${{ github.token }}" in text,
          "the master-alarm step must not reach the owner PAT")


def test_the_make_target_passes_its_variables_through():
    r = subprocess.run(["make", "-n", "master-alarm", "REPO=o/r", "LIMIT=5"],
                       cwd=ROOT, capture_output=True, text=True, timeout=60)
    out = r.stdout + r.stderr
    check("make: master-alarm runs the script with REPO",
          "scripts/master_alarm.py --repo" in out and '"o/r"' in out, out[-200:])
    check("make: master-alarm honours LIMIT", "--limit" in out, out[-200:])


def test_agents_md_carries_the_rule_and_the_guard_row():
    text = (ROOT / "AGENTS.md").read_text()
    check("agents: the rule documents a red master as an alarm",
          "A deterministic gate that goes red on a push to master" in text
          or "red on a `push` to master" in text)
    check("agents: the rule names the make target the workflow calls",
          "make master-alarm" in text)
    check("agents: the rule names the alarm script",
          "scripts/master_alarm.py" in text)
    check("agents: the section-8 row names this test",
          "tests/test_master_alarm.py" in text)


def main() -> int:
    test_a_red_run_is_reported()
    test_a_green_or_pending_or_absent_run_is_not_an_alarm()
    test_every_validate_gate_is_on_a_list()
    test_every_validate_step_target_is_a_gate_of_the_validate_job()
    test_the_workflow_guards_first_and_calls_the_make_target()
    test_the_make_target_passes_its_variables_through()
    test_agents_md_carries_the_rule_and_the_guard_row()
    print(f"\nPASSED {_PASS} | FAILED {_FAIL}")
    return 1 if _FAIL else 0


if __name__ == "__main__":
    raise SystemExit(main())
