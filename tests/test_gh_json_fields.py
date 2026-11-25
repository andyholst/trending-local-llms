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

Issue #1668 adds the same contract for `gh api <path> --jq <expr>`: a second recorded family
(`API_SHAPES`) keyed by the endpoint path tail, the same `--scan`, and guards that FAIL on the
base revision (which has no API_SHAPES at all).

Plain-script harness (the test image runs these as scripts, not pytest — the same
command CI runs must be the command you can run locally, rule 6m).
"""
import ast
import importlib.util
import json
import os
import re
import shutil
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
          contract.unknown_fields("some future command", ["whatever"]) == [], "")


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


#: Recorded from the REAL CLI on this repository (2026-11-20) by asking each subcommand for a
#: field it cannot answer and reading its own `Available fields:` answer. Issue #1160: the
#: contract covered `run list` only, so the other 50 reads failed at RUN time.
RECORDED_GH_FIELDS: dict[str, str] = {
    "run list": ("attempt, conclusion, createdAt, databaseId, displayTitle, event, "
                 "headBranch, headSha, name, number, startedAt, status, updatedAt, url, "
                 "workflowDatabaseId, workflowName"),
    "run view": ("attempt, conclusion, createdAt, databaseId, displayTitle, event, "
                 "headBranch, headSha, jobs, name, number, startedAt, status, updatedAt, "
                 "url, workflowDatabaseId, workflowName"),
    "pr list": ("additions, assignees, author, autoMergeRequest, baseRefName, baseRefOid, "
                "body, changedFiles, closed, closedAt, closingIssuesReferences, comments, "
                "commits, createdAt, deletions, files, fullDatabaseId, headRefName, "
                "headRefOid, headRepository, headRepositoryOwner, id, isCrossRepository, "
                "isDraft, labels, latestReviews, maintainerCanModify, mergeCommit, "
                "mergeStateStatus, mergeable, mergedAt, mergedBy, milestone, number, "
                "potentialMergeCommit, projectCards, projectItems, reactionGroups, "
                "reviewDecision, reviewRequests, reviews, state, statusCheckRollup, title, "
                "updatedAt, url"),
    "pr view": ("additions, assignees, author, autoMergeRequest, baseRefName, baseRefOid, "
                "body, changedFiles, closed, closedAt, closingIssuesReferences, comments, "
                "commits, createdAt, deletions, files, fullDatabaseId, headRefName, "
                "headRefOid, headRepository, headRepositoryOwner, id, isCrossRepository, "
                "isDraft, labels, latestReviews, maintainerCanModify, mergeCommit, "
                "mergeStateStatus, mergeable, mergedAt, mergedBy, milestone, number, "
                "potentialMergeCommit, projectCards, projectItems, reactionGroups, "
                "reviewDecision, reviewRequests, reviews, state, statusCheckRollup, title, "
                "updatedAt, url"),
    "issue list": ("assignees, author, blockedBy, blocking, body, closed, closedAt, "
                   "closedByPullRequestsReferences, comments, createdAt, id, isPinned, "
                   "issueType, labels, milestone, number, parent, projectCards, "
                   "projectItems, reactionGroups, state, stateReason, subIssues, "
                   "subIssuesSummary, title, updatedAt, url"),
    "issue view": ("assignees, author, blockedBy, blocking, body, closed, closedAt, "
                   "closedByPullRequestsReferences, comments, createdAt, id, isPinned, "
                   "issueType, labels, milestone, number, parent, projectCards, "
                   "projectItems, reactionGroups, state, stateReason, subIssues, "
                   "subIssuesSummary, title, updatedAt, url"),
    "label list": "color, createdAt, description, id, isDefault, name, updatedAt, url",
    "secret list": "name, numSelectedRepos, selectedReposURL, updatedAt, visibility",
    "workflow list": "id, name, path, state",
    "repo view": ("archivedAt, assignableUsers, codeOfConduct, contactLinks, createdAt, "
                  "defaultBranchRef, deleteBranchOnMerge, description, diskUsage, forkCount, "
                  "fundingLinks, hasDiscussionsEnabled, hasIssuesEnabled, hasProjectsEnabled, "
                  "hasWikiEnabled, homepageUrl, id, isArchived, isBlankIssuesEnabled, "
                  "isEmpty, isFork, isInOrganization, isMirror, isPrivate, "
                  "isSecurityPolicyEnabled, isTemplate, isUserConfigurationRepository, "
                  "issueTemplates, issues, labels, languages, latestRelease, licenseInfo, "
                  "mentionableUsers, mergeCommitAllowed, milestones, mirrorUrl, name, "
                  "nameWithOwner, openGraphImageUrl, owner, parent, primaryLanguage, "
                  "projects, projectsV2, pullRequestTemplates, pullRequests, pushedAt, "
                  "rebaseMergeAllowed, repositoryTopics, securityPolicyUrl, "
                  "squashMergeAllowed, sshUrl, stargazerCount, templateRepository, "
                  "updatedAt, url, usesCustomOpenGraphImage, viewerCanAdminister, "
                  "viewerDefaultCommitEmail, viewerDefaultMergeMethod, viewerHasStarred, "
                  "viewerPermission, viewerPossibleCommitEmails, viewerSubscription, "
                  "visibility, watchers"),
}


def test_every_recorded_field_set_is_the_real_cli_answer():
    """Issue #1160: the contract is only worth its keep if EVERY set is the CLI's own answer."""
    check("FIELD_SETS records exactly the commands the fixture transcribed",
          set(contract.FIELD_SETS) == set(RECORDED_GH_FIELDS),
          f"script-only: {sorted(set(contract.FIELD_SETS) - set(RECORDED_GH_FIELDS))}; "
          f"fixture-only: {sorted(set(RECORDED_GH_FIELDS) - set(contract.FIELD_SETS))}")
    for command, recorded in sorted(RECORDED_GH_FIELDS.items()):
        answer = {f.strip() for f in recorded.split(",") if f.strip()}
        check(f"{command}: the recorded set is exactly gh's Available-fields answer",
              contract.FIELD_SETS[command] == answer,
              f"script-only: {sorted(contract.FIELD_SETS[command] - answer)}; "
              f"cli-only: {sorted(answer - contract.FIELD_SETS[command])}")
    check("`run view` answers `jobs`, which `run list` does NOT",
          "jobs" in contract.FIELD_SETS["run view"] and "jobs" not in contract.FIELD_SETS["run list"],
          "")
    check("an UNRECORDED command still gets no opinion (never a false red)",
          contract.unknown_fields("some future command", ["whatever"]) == [], "")


#: One planted caller per subcommand: the command literally named, a field gh cannot answer.
def _planted_caller(command: str, field: str) -> str:
    return (f'import subprocess\nsubprocess.run(["gh", "{command.split()[0]}", '
            f'"{command.split()[1]}", "--json", "{field}"], capture_output=True)\n')


def test_the_scan_reads_every_subcommand_not_only_run_list():
    """Issue #1160's whole point: a drift in any of the 50 other reads must go RED."""
    for command in sorted(RECORDED_GH_FIELDS):
        td = Path(tempfile.mkdtemp())
        (td / "scripts").mkdir()
        (td / "scripts" / "caller.py").write_text(_planted_caller(command, "htmlUrl"))
        red = contract.scan_scripts(td)
        check(f"a planted unknown field in `gh {command} --json` is caught",
              len(red) == 1 and "caller.py" in red[0] and "htmlUrl" in red[0]
              and f"gh {command}" in red[0], red)
    # a supported field in a second subcommand stays green (the scan is not a blanket red)
    td = Path(tempfile.mkdtemp())
    (td / "scripts").mkdir()
    (td / "scripts" / "caller.py").write_text(_planted_caller("pr list", "number,title"))
    check("a supported `gh pr list --json` request is green (the scan opines per command)",
          contract.scan_scripts(td) == [], contract.scan_scripts(td))
    # an argparse `--json` flag is NOT a gh request and must not be read as one
    td = Path(tempfile.mkdtemp())
    (td / "scripts").mkdir()
    (td / "scripts" / "argparse.py").write_text(
        "import argparse\np = argparse.ArgumentParser()\np.add_argument('--json', action='store_true')\n")
    check("an argparse `--json` flag is not mistaken for a gh request",
          contract.scan_scripts(td) == [], contract.scan_scripts(td))


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
        check("`run view --json jobs` is a RECORDED request and is admitted (issue #1160)",
              jobs.returncode == 0, jobs.stderr[:200])


#: --------------------------------------------------------------------------- issue #1668
#: `gh api <path> --jq <expr>` names REST fields gh refuses only at RUN time — the same
#: build-time-vs-run-time hole #1158/#1160 closed for `--json`. The read surface below was
#: transcribed from live `gh api` reads on 2026-11-24; every family must stay recorded or the
#: tree scan reds, and an unrecorded path is a finding rather than a silent pass.
RECORDED_API_FAMILIES: dict[str, tuple[bool, set]] = {
    "issues/{}": (False, {".body", ".state"}),
    "pulls/{}": (False, {".merged", ".title", ".body", ".head.ref"}),
    "issues/{}/comments": (True, {".createdAt", ".body"}),
    "commits/{}": (False, {".commit.committer.date"}),
    "contents/{}": (False, {".content"}),
    "actions/workflows/{}/runs": (False, {".total_count"}),
    "actions/runs/{}": (False, {".actor.login", ".actor.type", ".triggering_actor.login"}),
}

#: The exact expression `scripts/pr_health.py::read_run_identity` sends (issue #1646) — the
#: residual this change exists to bring inside the contract.
PR_HEALTH_IDENTITY_EXPR = ('.actor.login + "|" + (.actor.type // "") + "|" + '
                           '(.triggering_actor.login // "")')


def _planted_api_caller(endpoint: str, expr: str) -> str:
    return ("import subprocess\n"
            f"subprocess.run([\"gh\", \"api\", {json.dumps(endpoint)}, \"--jq\", "
            f"{json.dumps(expr)}], capture_output=True)\n")


def _planted_api_tree(body: str) -> Path:
    td = Path(tempfile.mkdtemp())
    (td / "scripts").mkdir()
    (td / "scripts" / "caller.py").write_text(body)
    return td


def test_the_api_read_surface_is_recorded():
    """The base revision has no API_SHAPES at all, so this whole half is RED there."""
    shapes = getattr(contract, "API_SHAPES", None)
    check("API_SHAPES records exactly the endpoint families the tree reads",
          shapes is not None and set(shapes) == set(RECORDED_API_FAMILIES),
          sorted(shapes) if shapes is not None else "absent on the base revision")
    if shapes is None:
        return
    for family, (is_array, paths) in sorted(RECORDED_API_FAMILIES.items()):
        shape = shapes[family]
        check(f"{family}: array={is_array} with exactly the recorded read paths",
              bool(shape.array) == is_array and set(shape.paths) == paths,
              (shape.array, sorted(shape.paths)))
    check("a concrete slug, `{repo}` and `{owner}/{repo}` resolve to ONE family",
          contract.match_api_family("repos/andyholst/trending-local-llms/pulls/7")
          == contract.match_api_family("repos/{repo}/pulls/7")
          == contract.match_api_family("repos/{owner}/{repo}/pulls/{}") == "pulls/{}", "")
    check("a query string and a leading slash do not change the family",
          contract.match_api_family("/repos/{o}/{r}/actions/workflows/x.yml/runs?per_page=1")
          == "actions/workflows/{}/runs", "")
    check("the pr_health identity expression reads only recorded paths",
          contract.api_jq_problems("repos/{repo}/actions/runs/1", PR_HEALTH_IDENTITY_EXPR) == [],
          contract.api_jq_problems("repos/{repo}/actions/runs/1", PR_HEALTH_IDENTITY_EXPR))


def test_a_planted_jq_path_is_refused():
    """The measured gap: a `--jq` naming a renamed field must fail at BUILD time."""
    red = contract.scan_scripts(_planted_api_tree(
        _planted_api_caller("repos/o/r/actions/runs/1", '.actor.loginr + "|"')))
    check("a planted `--jq` typo goes RED, naming the file, line and path",
          len(red) == 1 and "caller.py" in red[0] and ".actor.loginr" in red[0]
          and re.search(r"caller\.py:\d+:", red[0]) is not None, red)
    check("the SAME expression with the real field name is green (not a blanket red)",
          contract.scan_scripts(_planted_api_tree(
              _planted_api_caller("repos/o/r/actions/runs/1", '.actor.login + "|"'))) == [], "")
    check("check_argv REFUSES a whole `gh api … --jq` argv naming an unknown path",
          any(".mergedAtX" in p for p in
              contract.check_argv(["api", "repos/o/r/pulls/1", "--jq", ".mergedAtX"])), "")
    check("check_argv admits the same argv naming a recorded path",
          contract.check_argv(["api", "repos/o/r/pulls/1", "--jq", ".merged"]) == [], "")


def test_an_unrecorded_endpoint_or_unreadable_expression_is_a_finding():
    """Never a silent pass: an endpoint outside the contract, or a value the AST cannot read."""
    unrecorded = contract.scan_scripts(_planted_api_tree(
        _planted_api_caller("repos/o/r/unknown/thing", ".x")))
    check("an endpoint family this contract does not record is a finding",
          len(unrecorded) == 1 and "does not record" in unrecorded[0], unrecorded)
    dynamic_endpoint = contract.scan_scripts(_planted_api_tree(
        'import os\nsubprocess.run(["gh", "api", os.environ["EP"], "--jq", ".x"],'
        " capture_output=True)\n"))
    check("an ENDPOINT the scan cannot read is a finding, never a silent pass",
          len(dynamic_endpoint) == 1 and "ENDPOINT" in dynamic_endpoint[0], dynamic_endpoint)
    dynamic_expr = contract.scan_scripts(_planted_api_tree(
        'import os\nsubprocess.run(["gh", "api", "repos/o/r/pulls/1", "--jq",'
        ' os.environ["JQ"]], capture_output=True)\n'))
    check("an EXPRESSION the scan cannot read is a finding, never a silent pass",
          len(dynamic_expr) == 1 and "EXPRESSION" in dynamic_expr[0], dynamic_expr)


def test_the_json_projection_and_fieldless_api_calls_are_exempt():
    """A CONSISTENT `--json … -q|--jq …` projection stays green, the fieldless `gh api` call
    stays exempt, and the five shipped composite sites stay green (issue #1676 pins their
    shapes so a later widening cannot sneak a silent pass back in)."""
    check("a CONSISTENT `gh <cmd> --json … (-q|--jq) …` stays green (path inside the list)",
          contract.check_argv(["pr", "list", "--json", "number,headRefName", "--jq",
                               '[.[] | select(.headRefName | startswith("x"))]']) == [], "")
    shipped_sites = [
        ("openspec_archive_check.py:108",
         ["repo", "view", "--json", "nameWithOwner", "-q", ".nameWithOwner"]),
        ("issue_verdict.py:417",
         ["repo", "view", "--json", "nameWithOwner", "--jq", ".nameWithOwner"]),
        ("issue_queue.py:194",
         ["repo", "view", "--json", "nameWithOwner", "-q", ".nameWithOwner"]),
        ("bot_health.py:183",
         ["repo", "view", "--json", "nameWithOwner", "-q", ".nameWithOwner"]),
        ("keeper_pr.py:161",
         ["pr", "list", "--state", "open", "--json",
          "number,headRefName,headRefOid,mergeStateStatus,statusCheckRollup",
          "--jq", '[.[] | select(.headRefName | startswith("fix/"))]']),
    ]
    for site, argv in shipped_sites:
        problems = contract.check_argv(argv)
        check(f"the shipped composite site {site} stays GREEN", problems == [], problems)
    check("a `gh api` call carrying no field expression stays exempt",
          contract.check_argv(["api", "repos/o/r/issues/1/comments", "--paginate",
                               "--slurp"]) == [], "")


def test_a_planted_json_projection_path_is_refused():
    """Issue #1676: a `-q|--jq` beside `--json` must re-read a field the SAME argv lists.

    RED-first: the base revision skips the whole projection half under `if "--json" not in
    argv`, so this planted `gh pr list --json number -q .title` returned `[]` there. It fails
    here as an ASSERTION, never a traceback (the old module still imports and runs).
    """
    planted = contract.check_argv(["pr", "list", "--json", "number", "-q", ".title"])
    check("a planted `--json number -q .title` is REFUSED, naming `.title`",
          len(planted) >= 1 and any(".title" in p for p in planted), planted)
    long_flag = contract.check_argv(["pr", "list", "--json", "number", "--jq", ".title"])
    check("the SAME plant through the long `--jq` flag is refused too",
          len(long_flag) >= 1 and any(".title" in p for p in long_flag), long_flag)
    check("the planted problem names the field list it was checked against",
          any("number" in p for p in planted), planted)
    check("a projection that DOES re-read a listed field stays green",
          contract.check_argv(["pr", "list", "--json", "number", "-q", ".number"]) == [], "")
    check("an expression `jq_paths` cannot read is tolerated (never a false red)",
          contract.jq_paths(".title{") is None
          and contract.check_argv(["pr", "list", "--json", "number", "-q", ".title{"]) == [],
          "")


def _base_revision_module():
    """Import `git show origin/master:scripts/gh_json_fields.py` as a throwaway module.

    RED-first seam for #1675: the base revision predates the boundary, so it carries neither
    constant and still makes the unqualified claim. It must IMPORT cleanly — no attribute that
    only exists after the fix is touched here — so the guard FAILs as an assertion on the base,
    never crashes mid-module and hides the later genuine failures. `safe.directory` is pinned
    because `make test` runs this inside a container as root over host-owned files: without it
    git exits 128 with "detected dubious ownership" and the check would red for the environment,
    not the claim (the same override `scripts/lint_syntax.py` and `tests/test_fleet_lifecycle.py`
    carry).
    """
    proc = subprocess.run(
        ["git", "-c", f"safe.directory={ROOT}", "-C", str(ROOT),
         "show", "origin/master:scripts/gh_json_fields.py"],
        capture_output=True, text=True)
    check("the base revision of scripts/gh_json_fields.py is readable through git",
          proc.returncode == 0 and bool(proc.stdout.strip()),
          f"rc={proc.returncode} {proc.stderr[:120]}")
    if proc.returncode != 0 or not proc.stdout.strip():
        return None
    handle = tempfile.NamedTemporaryFile("w", suffix=".py", delete=False, encoding="utf-8")
    try:
        handle.write(proc.stdout)
        handle.close()
        spec = importlib.util.spec_from_file_location("gh_json_fields_base", handle.name)
        if spec is None or spec.loader is None:
            return None
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    finally:
        os.unlink(handle.name)


def _base_has_the_boundary(module) -> bool:
    """True when a revision already declares the #1675 Python-side `.get()` boundary."""
    return getattr(module, "UNVALIDATED_PYTHON_API_READ_SITES", None) is not None


def test_the_scope_claim_matches_the_tree():
    """Issue #1675: the contract claims ONLY `--jq` projections; Python-side `.get()` picks are OUT OF SCOPE.

    RED-first across this PR's OWN merge: `_base_revision_module()` reads `origin/master`. While
    #1700 is open that revision predates the boundary, so the two BASE checks go RED — the guard
    proves it fails on the old, unqualified claim. Once #1700 squashes into master,
    `origin/master` IS the fixed module, so the arm asserts the boundary IS present instead of
    skipping: an unconditional "the base lacks the constants" assertion would go red forever on
    the next push run (reviewer blocker 2, reproduced `101 passed, 2 failed`). This is the shape
    `tests/test_auto_merge_rebase.py:912-920` uses for its own moving-ref seam. NON-VACUOUS: a
    scratch tree whose only `gh api` call picks its fields in PYTHON scans GREEN — the scan really
    is SILENT on Python picks, so the narrowed claim is TRUE rather than merely reworded — and the
    shipped discovery totals stay pinned, proving the change altered no verdict.
    """
    base = _base_revision_module()
    if base is None:
        return
    if _base_has_the_boundary(base):
        check("origin/master already carries the #1675 boundary constant (post-merge arm)",
              getattr(base, "UNVALIDATED_PYTHON_API_READ_SITES", None) == 18,
              getattr(base, "UNVALIDATED_PYTHON_API_READ_SITES", None))
        base_doc = base.__doc__ or ""
        check("origin/master's claim is qualified to `--jq` call sites (post-merge arm)",
              "so a `--jq` call site can never sit outside the contract silently" in base_doc, "")
    else:
        check("BASE revision carries no UNVALIDATED_PYTHON_API_READ_SITES constant (RED-first)",
              getattr(base, "UNVALIDATED_PYTHON_API_READ_SITES", None) is None,
              getattr(base, "UNVALIDATED_PYTHON_API_READ_SITES", None))
        base_doc = base.__doc__ or ""
        check("BASE revision still makes the UNQUALIFIED claim (no `--jq` qualifier)",
              "can never sit outside the contract silently" in base_doc
              and "so a `--jq` call site" not in base_doc, "")

    check("the shipped module declares the Python-side `.get()` surface OUT OF SCOPE",
          getattr(contract, "PYTHON_GET_FIELDS_OUT_OF_SCOPE", None) is True, "")
    check("the uncovered-site count is pinned at 18 of 32 read sites",
          getattr(contract, "UNVALIDATED_PYTHON_API_READ_SITES", None) == 18,
          getattr(contract, "UNVALIDATED_PYTHON_API_READ_SITES", None))
    doc = contract.__doc__ or ""
    check("the module docstring narrows the claim to `--jq` call sites",
          "so a `--jq` call site can never sit outside the contract silently" in doc, "")
    check("the module docstring states the BOUNDARY marker and the projection-only scope",
          "BOUNDARY (issue #1675): this contract validates ONLY `--jq`/`-q` projections" in doc,
          "")
    check("the module docstring carries the 32 / 18 / 2 counts",
          "32 `gh api` read sites" in doc and "18 of them naming a REST field" in doc
          and "2 name no field" in doc, "")
    api_doc = contract.api_jq_requests.__doc__ or ""
    check("`api_jq_requests` names the projection-only exemption and cites #1675",
          "NO `--jq`/`-q` expression" in api_doc and "out of scope" in api_doc
          and "#1675" in api_doc, "")

    pick = Path(tempfile.mkdtemp())
    try:
        (pick / "scripts").mkdir()
        (pick / "scripts" / "reader.py").write_text(
            "import json, subprocess\n"
            "out = subprocess.run([\"gh\", \"api\", \"repos/o/r/issues/1/comments\"],\n"
            "                     capture_output=True, text=True).stdout\n"
            "comment = json.loads(out)\n"
            "print(comment.get(\"created_at\"))\n")
        problems = contract.scan_scripts(pick)
        check("NON-VACUOUS: a `gh api` read that picks fields in PYTHON scans GREEN "
              "(the scan is silent on Python picks, so the narrowed claim is TRUE)",
              problems == [], problems[:6])
    finally:
        shutil.rmtree(pick, ignore_errors=True)

    problems = contract.scan_scripts(ROOT)
    check("the shipped tree scans GREEN (0 findings) — no scan behaviour change",
          problems == [], problems[:6])

    projected, without = [], []
    expressions = []
    for path in sorted((ROOT / "scripts").glob("*.py")):
        tree = ast.parse(path.read_text())
        consts = contract._string_bindings(tree)
        expressions.extend(expr for _, _, expr in contract.api_jq_requests(tree, consts))
        for node, tokens in contract._api_token_lists(tree):
            if "--json" in tokens or "api" not in tokens:
                continue
            key = (path.name, getattr(node, "lineno", 0))
            bucket = projected if any(t in ("--jq", "-q") for t in tokens) else without
            if key not in bucket:
                bucket.append(key)
    check("discovery totals are unchanged: 31 `gh api` token-lists (17 projecting, 14 not)",
          len(projected) + len(without) == 31 and len(projected) == 17 and len(without) == 14,
          f"{len(projected) + len(without)} total / {len(projected)} projecting / "
          f"{len(without)} not")
    identity = sum(1 for e in expressions if (e or "").strip() == ".[]")
    check("identity `.[]` projections: 5 (their Python side still picks fields)",
          identity == 5, identity)


def test_the_scan_reads_the_real_tree_and_sees_the_api_calls():
    """Green here AND non-vacuous: the scan really discovers the repository's `--jq` reads.

    `api_jq_requests` does not exist on the base revision, so it is read DEFENSIVELY — the guard
    must FAIL there, never crash mid-module and hide the later genuine failures.
    """
    problems = contract.scan_scripts(ROOT)
    check("scan_scripts is GREEN on this repository (`--json` AND `gh api --jq`)",
          problems == [], problems[:6])
    discover = getattr(contract, "api_jq_requests", None)
    bindings = getattr(contract, "_string_bindings", None)
    seen = 0
    if discover is not None and bindings is not None:
        for path in sorted((ROOT / "scripts").glob("*.py")):
            tree = ast.parse(path.read_text())
            seen += len(discover(tree, bindings(tree)))
    check("the scan DISCOVERS the repository's `gh api … --jq` calls (not a vacuous green)",
          seen >= 15, seen)


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
    test_every_recorded_field_set_is_the_real_cli_answer()
    test_the_seam_refuses_a_field_gh_cannot_answer()
    test_the_ghost_alarm_builds_its_request_through_the_seam()
    test_the_tree_scan_is_green_here_and_red_on_the_old_shape()
    test_the_scan_reads_every_subcommand_not_only_run_list()
    test_the_cli_modes_decide_loudly()
    test_the_ghost_stub_cannot_answer_a_query_the_real_gh_refuses()
    test_the_api_read_surface_is_recorded()
    test_a_planted_jq_path_is_refused()
    test_an_unrecorded_endpoint_or_unreadable_expression_is_a_finding()
    test_the_json_projection_and_fieldless_api_calls_are_exempt()
    test_a_planted_json_projection_path_is_refused()
    test_the_scope_claim_matches_the_tree()
    test_the_scan_reads_the_real_tree_and_sees_the_api_calls()
    test_the_scan_is_wired_where_ci_runs_it()
    print(f"\n{PASSED} passed, {FAILED} failed")
    return 1 if FAILED else 0


if __name__ == "__main__":
    sys.exit(main())
