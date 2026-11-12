"""tests/test_workflow_guards.py — the §6j tree-wide guard scan (issue #816).

Two halves, both required by rule 6c:
  * the REAL scripts/check_workflow_guards.py against the REAL tree goes green:
    every workflow scanned, each real guard script executed for every caller class;
  * planted fixture workflows go RED for every way a pipeline can escape the rule —
    no guard, an `environment:` approval gate, a guard that needs a job, a guard
    that touches a secret, a cron without the schedule bypass, a repository event
    the guard refuses, a guard that would admit a stranger, a job that skips the
    guard, a trigger outside the decided decision surface.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import check_workflow_guards as scan  # noqa: E402  (the ONE implementation; LSP can't see the sys.path)

# The real guard script (queued-alarm's), as a fixture template — fixtures plant ONE
# defect each into an otherwise-correct pipeline.
GUARD = """          if [ "$EVENT" = "schedule" ]; then
            echo "Scheduled run - allowed."
            exit 0
          fi
          for u in "$ACTOR" "$TRIGGER"; do
            if [ "$u" = "$OWNER" ]; then continue; fi
            if [ "$u" = "github-actions[bot]" ]; then continue; fi
            perm=$(gh api "repos/$REPO/collaborators/$u/permission" --jq .permission 2>/dev/null || echo none)
            case "$perm" in
              admin|maintain|write) ;;
              *) exit 1 ;;
            esac
          done
"""
GUARD_JOB = """  guard:
    runs-on: ubuntu-latest
    steps:
      - name: Owner / collaborator trigger guard
        run: |
""" + GUARD


def _wf(on_block: str, jobs_block: str) -> str:
    return f"name: fixture\non:\n{on_block}\njobs:\n{jobs_block}\n"


# name -> (workflow text, substring the scanner MUST report for it)
FIXTURES = {
    "no_guard.yml": (
        _wf("  workflow_dispatch:\n",
            "  work:\n    runs-on: ubuntu-latest\n    steps:\n      - name: build\n        run: |\n          echo build\n"),
        "no guard job found",
    ),
    "environment_gate.yml": (
        _wf("  workflow_dispatch:\n",
            GUARD_JOB
            + "  work:\n    needs: guard\n    environment: Production\n    runs-on: ubuntu-latest\n    steps:\n      - name: do\n        run: |\n          echo gated\n"),
        "uses environment:",
    ),
    "guard_needs_work.yml": (
        _wf("  workflow_dispatch:\n",
            "  guard:\n    needs: prep\n    runs-on: ubuntu-latest\n    steps:\n      - name: Owner / collaborator trigger guard\n        run: |\n"
            + GUARD
            + "  prep:\n    runs-on: ubuntu-latest\n    steps:\n      - name: p\n        run: |\n          echo p\n"),
        "guard job 'guard' needs",
    ),
    "guard_secret.yml": (
        _wf("  workflow_dispatch:\n",
            GUARD_JOB.replace(
                "        run: |",
                "        env:\n          TOKEN: ${{ secrets.NOUS_API_KEY }}\n        run: |", 1)
            + "  work:\n    needs: guard\n    runs-on: ubuntu-latest\n    steps:\n      - name: do\n        run: |\n          echo ok\n"),
        "touches a secret",
    ),
    "cron_without_bypass.yml": (
        _wf("  schedule:\n    - cron: '7 3 * * 3'\n  workflow_dispatch:\n",
            GUARD_JOB.replace("\n".join(GUARD.splitlines()[:4]) + "\n", "")
            + "  work:\n    needs: guard\n    runs-on: ubuntu-latest\n    steps:\n      - name: do\n        run: |\n          echo cron\n"),
        "schedule bypass",
    ),
    "repo_event_refused.yml": (
        _wf("  push:\n    branches: [master]\n",
            GUARD_JOB
            + "  work:\n    needs: guard\n    runs-on: ubuntu-latest\n    steps:\n      - name: do\n        run: |\n          echo push\n"),
        "must admit the repository event",
    ),
    "stranger_admitted.yml": (
        _wf("  workflow_dispatch:\n",
            GUARD_JOB.replace('|| echo none)', '|| echo write)').replace('admin|maintain|write)', 'admin|maintain|write|read)')
            + "  work:\n    needs: guard\n    runs-on: ubuntu-latest\n    steps:\n      - name: do\n        run: |\n          echo lax\n"),
        "guard must refuse stranger",
    ),
    "job_skips_guard.yml": (
        _wf("  workflow_dispatch:\n",
            GUARD_JOB
            + "  work:\n    runs-on: ubuntu-latest\n    steps:\n      - name: do\n        run: |\n          echo before the guard\n"),
        "does not need the guard",
    ),
    "odd_trigger.yml": (
        _wf("  repository_dispatch:\n",
            GUARD_JOB
            + "  work:\n    needs: guard\n    runs-on: ubuntu-latest\n    steps:\n      - name: do\n        run: |\n          echo odd\n"),
        "neither a repository event nor guarded by caller class",
    ),
}


def _fixture_tree(tmp: Path) -> Path:
    tree = tmp / "repo"
    wfs = tree / ".github" / "workflows"
    wfs.mkdir(parents=True)
    for fname, (text, _needle) in FIXTURES.items():
        (wfs / fname).write_text(text)
    return tree


def test_the_real_tree_scans_green_and_covers_every_workflow():
    reports, problems = scan.scan_tree(ROOT)
    names = {f.name for f in (ROOT / scan.WF_DIR).glob("*.yml")}
    assert problems == [], problems
    scanned = {r.split(" ", 1)[1].split(":")[0] for r in reports}
    assert scanned == names, f"the scan missed workflows: {names - scanned}"
    assert all("guard-job=guard" in r for r in reports), reports


def test_the_real_guard_scripts_decide_every_caller_class():
    """Not a shape match: the actual guard shell from every dispatchable workflow is
    executed against the caller table (rule 6m: run the logic, do not fake it)."""
    ran = 0
    for f in sorted((ROOT / scan.WF_DIR).glob("*.yml")):
        wf = scan.parse_workflow(f.read_text())
        if "workflow_dispatch" not in wf["on"]:
            continue
        _guard_job, step = scan.find_guard_step(wf)
        for ev, actor, trigger, want, label in scan.GUARD_CALLERS:
            rc, out = scan.run_guard_script(step["run"], ev, actor, trigger, scan.GUARD_PERMS)
            assert (rc == 0) == (want == 0), f"{f.name} {label}: rc={rc} {out}"
            ran += 1
    assert ran >= 9 * 8, f"expected the caller classes run against every dispatchable workflow, ran {ran}"


def test_a_scheduled_pipeline_starts_from_no_human():
    """The cron bypass is executed with NO caller identity: schedule passes even with
    an empty actor — a scheduled start never depends on a person."""
    wf = scan.parse_workflow((ROOT / scan.WF_DIR / "refresh-bot.yml").read_text())
    _job, step = scan.find_guard_step(wf)
    rc, out = scan.run_guard_script(step["run"], "schedule", "", "", scan.GUARD_PERMS)
    assert rc == 0, out


def test_repository_events_are_admitted_whatever_the_actor():
    """A PR is validated whatever its author; push/issues events are started by
    GitHub for the repo (issue #771). Executed, not asserted from prose."""
    for fname in ("qa-validate.yml", "pr-closure.yml", "issue-bot.yml"):
        wf = scan.parse_workflow((ROOT / scan.WF_DIR / fname).read_text())
        _job, step = scan.find_guard_step(wf)
        for ev in wf["on"]:
            if ev in scan.REPO_EVENTS:
                rc, out = scan.run_guard_script(step["run"], ev, "stranger", "stranger", scan.GUARD_PERMS)
                assert rc == 0, f"{fname} {ev}: rc={rc} {out}"


def test_planted_fixtures_go_red_for_each_escape(tmp_path):
    tree = _fixture_tree(tmp_path)
    _reports, problems = scan.scan_tree(tree)
    joined = "\n".join(problems)
    for fname, (_text, needle) in FIXTURES.items():
        matching = [p for p in problems if p.startswith(fname)]
        assert matching, f"{fname} passed the scan"
        assert any(needle in p for p in matching), \
            f"{fname} must fail with '{needle}'; its problems:\n{joined}"


def test_main_exits_loud_on_the_fixture_tree(tmp_path, capsys):
    tree = _fixture_tree(tmp_path)
    assert scan.main([str(tree)]) == 1, "a fixture tree must exit 1, never a silent clean"
    out = capsys.readouterr().out
    assert "problem(s)" in out and "RED" in out


def test_main_exits_2_when_the_tree_cannot_be_read(tmp_path, capsys):
    assert scan.main([str(tmp_path / "not-a-repo")]) == 2
    assert "cannot read the tree" in capsys.readouterr().err


def test_the_scan_is_wired_through_the_makefile_into_lint():
    makefile = (ROOT / "Makefile").read_text()
    assert "python3 scripts/check_workflow_guards.py" in makefile
    assert "$(MAKE) --no-print-directory check-workflow-guards" in makefile
    lint = makefile.split("lint: ##", 1)[1].split("\n\n", 1)[0]
    assert "check-workflow-guards" in lint, "the scan must ride make lint — the gate every PR, bot round and human runs"
    # and lint is reached by the pipeline (qa-validate + fix_loop), per rule 6m
    qa = (ROOT / ".github" / "workflows" / "qa-validate.yml").read_text()
    loop = (ROOT / "scripts" / "fix_loop.sh").read_text()
    assert "make lint" in qa, "qa-validate must run make lint"
    assert "lint" in loop, "fix_loop must run lint as its first check"


def test_parse_workflow_reads_triggers_needs_and_guard_run():
    text = """name: demo
on:
  schedule:
    - cron: '19 4 * * 3'
  workflow_dispatch:
jobs:
  guard:
    runs-on: ubuntu-latest
    steps:
      - name: Owner / collaborator trigger guard
        run: |
          echo "guard $ACTOR $TRIGGER $OWNER"
  work:
    needs: [guard, prep]
    runs-on: ubuntu-latest
    steps:
      - name: do
        run: |
          echo hi
  prep:
    needs: guard
    steps:
      - name: p
        run: echo p
"""
    wf = scan.parse_workflow(text)
    assert wf["on"] == ["schedule", "workflow_dispatch"]
    assert wf["jobs"]["work"]["needs"] == ["guard", "prep"]
    assert wf["jobs"]["prep"]["needs"] == ["guard"]
    guard_job, step = scan.find_guard_step(wf)
    assert guard_job == "guard"
    assert 'echo "guard $ACTOR $TRIGGER $OWNER"' in step["run"]


def test_a_second_pipeline_with_an_environment_gate_fails_the_scan(tmp_path):
    """The exact scenario the owner reported: another agent's PR added a manual
    approval gate. A tree carrying it turns the scan red — rule 6c."""
    tree = tmp_path / "repo"
    wfs = tree / ".github" / "workflows"
    wfs.mkdir(parents=True)
    real = (ROOT / scan.WF_DIR / "bot-health.yml").read_text()
    (wfs / "ok.yml").write_text(real)
    (wfs / "gated.yml").write_text(real.replace("  health:\n", "  health:\n    environment: Production\n", 1))
    reports, problems = scan.scan_tree(tree)
    assert len(reports) == 2
    assert any("gated.yml" in p and "environment:" in p for p in problems), problems
    assert not any("ok.yml" in p for p in problems), problems
