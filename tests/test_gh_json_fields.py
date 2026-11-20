"""tests/test_gh_json_fields.py — the ONE gh `--json` field contract (issue #1158).

The measured defect: `scripts/ghost_run_alarm.py` asked `gh run list` for `htmlUrl`, a
field gh HAS NEVER HAD, so `make ghost-run-alarm` — the only alarm that watches
`pull_request` runs carrying ZERO jobs — exited 2 on its own read and never once named a
ghost, while the test stub answered ANY requested field and kept `make test` green.

Four halves, all required by rule 6c:
  * the recorded field set is the REAL CLI's own answer (recorded fixture);
  * the seam refuses an invented field at request-build time and in check_argv;
  * the tree-wide scan is green on this repository and RED on the pre-change shape
    (the old field list planted in a scratch scripts/ tree), and loud (exit 2) when it
    cannot read the tree at all;
  * the ghost alarm's own stub gh now REFUSES a request the real gh refuses, and the
    scan is bundled into `make lint` — the gate CI actually runs (rules 6d/6m).

Plain-script harness (the test image runs these as scripts, not pytest — the same
command CI runs must be the command you can run locally, rule 6m).
"""
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "tests"))

import gh_json_fields as contract  # noqa: E402  (the ONE implementation; LSP can't see the sys.path)

PASSED = FAILED = 0


def check(name: str, ok: bool, detail: object = "") -> None:
    global PASSED, FAILED
    if ok:
        PASSED += 1
        print(f"  ok  {name}")
    else:
        FAILED += 1
        print(f"FAIL {name}  {detail}")


#: Recorded from the REAL CLI on this repository (2026-11-20):
#:   $ gh run list --repo andyholst/trending-local-llms --limit 1 --json htmlUrl
#:   Unknown JSON field: "htmlUrl"
#:   Available fields: attempt, conclusion, createdAt, databaseId, displayTitle, event,
#:   headBranch, headSha, name, number, startedAt, status, updatedAt, url,
#:   workflowDatabaseId, workflowName
RECORDED_GH_RUN_LIST_FIELDS = """
    attempt, conclusion, createdAt, databaseId, displayTitle, event, headBranch,
    headSha, name, number, startedAt, status, updatedAt, url,
    workflowDatabaseId, workflowName
"""

#: The field list `scripts/ghost_run_alarm.py` asked BEFORE issue #1158 — the shape every
#: guard below must go RED on.
OLD_GHOST_REQUEST = ("databaseId,workflowName,name,headBranch,headSha,status,conclusion,"
                     "createdAt,htmlUrl")


def test_the_field_set_is_the_real_cli_answer():
    recorded = {f.strip() for f in RECORDED_GH_RUN_LIST_FIELDS.split(",") if f.strip()}
    check("RUN_LIST_FIELDS is exactly the real `gh run list` Available-fields answer",
          contract.RUN_LIST_FIELDS == recorded,
          f"script-only: {sorted(contract.RUN_LIST_FIELDS - recorded)}; "
          f"cli-only: {sorted(recorded - contract.RUN_LIST_FIELDS)}")
    check("gh's run link field is `url` and `htmlUrl` is NOT in the contract",
          "url" in contract.RUN_LIST_FIELDS and "htmlUrl" not in contract.RUN_LIST_FIELDS, "")
    check("a command this module has not recorded gets NO opinion (never a false red)",
          contract.unknown_fields("run view", ["jobs"]) == []
          and contract.unknown_fields("some future command", ["whatever"]) == [], "")


def test_the_seam_refuses_a_field_gh_cannot_answer():
    ok = contract.request("run list", "databaseId,url")
    check("request() passes a supported field list through unchanged",
          ok == "databaseId,url", ok)
    try:
        contract.request("run list", OLD_GHOST_REQUEST)
        refused = None
    except ValueError as exc:
        refused = str(exc)
    check("request() REFUSES the pre-change ghost request, naming htmlUrl",
          refused is not None and "htmlUrl" in refused and "run list" in refused, refused)
    problems = contract.check_argv(["run", "list", "--workflow", "qa-validate.yml",
                                    "--json", OLD_GHOST_REQUEST])
    check("check_argv names the unknown field of a whole gh argv list",
          len(problems) == 1 and "htmlUrl" in problems[0], problems)
    check("check_argv is quiet for a supported argv",
          contract.check_argv(["run", "list", "--json", "databaseId,conclusion"]) == [], "")
    check("command_path reads `run list` out of an argv (not the flags)",
          contract.command_path(["run", "list", "--workflow", "x", "--json", "url"]) == "run list", "")


def test_the_ghost_alarm_builds_its_request_through_the_seam():
    import ghost_run_alarm as GA
    check("ghost_run_alarm.RUNS_JSON asks only for fields gh can answer",
          contract.unknown_fields("run list", [GA.RUNS_JSON]) == [], GA.RUNS_JSON)
    check("the alarm asks for `url` (the field gh answers), never `htmlUrl`",
          "url" in GA.RUNS_JSON.split(",") and "htmlUrl" not in GA.RUNS_JSON, GA.RUNS_JSON)
    src = (ROOT / "scripts" / "ghost_run_alarm.py").read_text()
    check("the request is built through gh_json_fields.request (one seam, rule 6d)",
          "gh_json_fields.request(" in src, src[:200])
    check("the alarm validates every gh request it makes before calling gh",
          "gh_json_fields.check_argv(" in src, "")
    check("the rendered ghost line prints the `url` gh answered",
          "g.get('url')" in src and "htmlUrl" not in src, "")


def _scratch_scripts_tree(field_list: str, extra: str = "") -> Path:
    """A scratch repository whose scripts/ holds one planted `gh run list` caller."""
    td = Path(tempfile.mkdtemp())
    (td / "scripts").mkdir()
    (td / "scripts" / "caller.py").write_text(
        "#!/usr/bin/env python3\nimport subprocess\n"
        f"RUNS_JSON = {json.dumps(field_list)}\n"
        'def fetch(repo):\n'
        '    return subprocess.run(["gh", "run", "list", "--workflow", "x", "--json",\n'
        '                           RUNS_JSON, "--repo", repo], capture_output=True)\n'
        + extra)
    return td


def test_the_tree_scan_is_green_here_and_red_on_the_old_shape():
    problems = contract.scan_scripts(ROOT)
    check("scan_scripts is GREEN on this repository (every gh run list field is one gh answers)",
          problems == [], problems[:6])

    planted = _scratch_scripts_tree(OLD_GHOST_REQUEST)
    red = contract.scan_scripts(planted)
    check("the scan is RED on the pre-change ghost field list (names file, line and field)",
          len(red) == 1 and "caller.py" in red[0] and "htmlUrl" in red[0]
          and re.search(r"caller\.py:\d+:", red[0]) is not None
          and "gh run list" in red[0], red)

    inline = _scratch_scripts_tree("databaseId,url")
    (inline / "scripts" / "inline.py").write_text(
        'import subprocess\nsubprocess.run(["gh", "run", "list", "--json",\n'
        '                           "databaseId,htmlUrl"], capture_output=True)\n')
    red2 = contract.scan_scripts(inline)
    check("an INLINE invented field in a second caller is caught too (no second copy drifts)",
          any("inline.py" in p and "htmlUrl" in p for p in red2), red2)

    dynamic = _scratch_scripts_tree("databaseId,url", extra=(
        'import os\nsubprocess.run(["gh", "run", "list", "--json",\n'
        '                           os.environ["FIELDS"]], capture_output=True)\n'))
    red3 = contract.scan_scripts(dynamic)
    check("a `--json` field list the scan cannot READ is a finding, never a silent pass",
          any("cannot read" in p for p in red3), red3)

    empty = Path(tempfile.mkdtemp())
    try:
        contract.scan_scripts(empty)
        loud = "raised"
    except FileNotFoundError:
        loud = "raised"
    check("a tree without scripts/ raises (the CLI reports exit 2), never a vacuous clean",
          loud == "raised", loud)


def _run_cli(*args: str, root: Path | None = None) -> subprocess.CompletedProcess:
    cmd = [sys.executable, str(ROOT / "scripts" / "gh_json_fields.py"), *args]
    if root is not None:
        cmd += ["--root", str(root)]
    return subprocess.run(cmd, capture_output=True, text=True)


def test_the_cli_modes_decide_loudly():
    here = _run_cli("--scan")
    check("`make lint`'s `--scan` is exit 0 on this tree", here.returncode == 0,
          here.stdout[:200])
    planted = _scratch_scripts_tree(OLD_GHOST_REQUEST)
    red = _run_cli("--scan", root=planted)
    check("`--scan` on the planted old shape exits 1 naming the file and the field",
          red.returncode == 1 and "htmlUrl" in red.stdout and "caller.py" in red.stdout,
          red.stdout[:300])
    missing = _run_cli("--scan", root=Path(tempfile.mkdtemp()))
    check("an unreadable tree exits 2, loudly (never a silent clean)",
          missing.returncode == 2 and "SCAN UNREADABLE" in missing.stdout, missing.stdout[:200])
    bad = _run_cli("--check-argv", "gh run list --json databaseId,htmlUrl")
    check("--check-argv refuses what the real gh refuses (the stub's seam)",
          bad.returncode == 1 and "Unknown JSON field" in bad.stdout, bad.stdout[:200])
    good = _run_cli("--check-argv", "gh run list --workflow x --json databaseId,url")
    check("--check-argv admits a supported request", good.returncode == 0, good.stdout[:200])


#: The ghost alarm's stub gh (tests/test_auto_merge_rebase.py) validates every --json
#: REQUEST through the seam, so a request the real CLI refuses can never be answered here.
def _stub_gh_dir(td: Path) -> dict:
    import test_auto_merge_rebase as TA
    (td / "gh").write_text(TA.STUB_GH_RUNS)
    (td / "gh").chmod(0o755)
    (td / "runs.json").write_text("[]")
    (td / "jobs").mkdir()
    (td / "jobs" / "7.json").write_text("[]")
    return {**os.environ, "PATH": f"{td}:{os.environ['PATH']}",
            "FAKE_RUNS": str(td / "runs.json"), "FAKE_JOBS_DIR": str(td / "jobs"),
            "GH_LOG": str(td / "gh.log"), "PYTHON": sys.executable,
            "GH_FIELD_CONTRACT": str(ROOT / "scripts" / "gh_json_fields.py")}


def test_the_ghost_stub_cannot_answer_a_query_the_real_gh_refuses():
    """Rule 6m: the stub is an EXTERNAL system, not a contract-free echo. It must refuse the
    exact request the measured defect sent, and answer the fixed one."""
    with tempfile.TemporaryDirectory() as td:
        env = _stub_gh_dir(Path(td))
        refused = subprocess.run(["gh", "run", "list", "--workflow", "qa-validate.yml",
                                  "--json", OLD_GHOST_REQUEST, "--repo", "o/r"],
                                 capture_output=True, text=True, env=env)
        check("the stub refuses `--json …htmlUrl` the way gh does (exit 1, named)",
              refused.returncode != 0 and "Unknown JSON field" in (refused.stderr + refused.stdout),
              (refused.stderr + refused.stdout)[:200])
        answered = subprocess.run(["gh", "run", "list", "--workflow", "qa-validate.yml",
                                   "--json", "databaseId,url", "--repo", "o/r"],
                                  capture_output=True, text=True, env=env)
        check("the stub answers the fixed request", answered.returncode == 0,
              answered.stderr[:200])
        jobs = subprocess.run(["gh", "run", "view", "7", "--json", "jobs", "--repo", "o/r"],
                              capture_output=True, text=True, env=env)
        check("a command the contract has not recorded is left alone (run view --json jobs)",
              jobs.returncode == 0, jobs.stderr[:200])


def test_the_scan_is_wired_where_ci_runs_it():
    """Rules 6d/6m: a check nothing runs is a defect — the target must exist, run the script,
    and be bundled into `make lint`, which qa-validate's `validate` job runs first."""
    makefile = (ROOT / "Makefile").read_text()
    lines = makefile.splitlines()
    idx = next((i for i, l in enumerate(lines)
                if l.startswith("_check-gh-json-fields:")), None)
    check("Makefile defines `_check-gh-json-fields` running the scan",
          idx is not None and "python3 scripts/gh_json_fields.py --scan" in lines[idx + 1],
          lines[idx:idx + 3] if idx is not None else "no recipe")
    check("the internal recipe is .PHONY", ".PHONY: _check-gh-json-fields" in makefile, "")
    check("the public target `check-gh-json-fields` delegates to it",
          "check-gh-json-fields: ##" in makefile
          and "$(MAKE) --no-print-directory _check-gh-json-fields" in makefile, "")
    lint_block = []
    for i, line in enumerate(lines):
        if line.startswith("lint: "):
            j = i + 1
            while j < len(lines) and (lines[j].startswith("\t") or not lines[j].strip()):
                if not lines[j].strip():
                    break
                lint_block.append(lines[j])
                j += 1
            break
    check("`make lint` bundles check-gh-json-fields",
          any("check-gh-json-fields" in l for l in lint_block), lint_block)
    qa = (ROOT / ".github" / "workflows" / "qa-validate.yml").read_text()
    check("qa-validate's validate job runs `make lint` (the gate the scan lands in)",
          "make lint" in qa, "")
    queued = (ROOT / ".github" / "workflows" / "queued-alarm.yml").read_text()
    check("queued-alarm still runs make ghost-run-alarm (the alarm the fix unblocks)",
          "make ghost-run-alarm" in queued, "")
    check("no script reaches the contract past the Makefile (rule 6m: the only direct caller is lint)",
          sum(1 for p in sorted((ROOT / ".github" / "workflows").glob("*.yml"))
              if "scripts/gh_json_fields.py" in p.read_text()) == 0, "")


def main() -> int:
    test_the_field_set_is_the_real_cli_answer()
    test_the_seam_refuses_a_field_gh_cannot_answer()
    test_the_ghost_alarm_builds_its_request_through_the_seam()
    test_the_tree_scan_is_green_here_and_red_on_the_old_shape()
    test_the_cli_modes_decide_loudly()
    test_the_ghost_stub_cannot_answer_a_query_the_real_gh_refuses()
    test_the_scan_is_wired_where_ci_runs_it()
    print(f"\n{PASSED} passed, {FAILED} failed")
    return 1 if FAILED else 0


if __name__ == "__main__":
    sys.exit(main())
