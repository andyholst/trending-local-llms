#!/usr/bin/env python3
"""ONE contract for the fields `gh … --json` can answer (issues #1158, #1160).

`gh <cmd> --json <fields>` REFUSES a field that command cannot answer. Measured on
this repository's CLI (2026-11-20):

    $ gh run list --repo andyholst/trending-local-llms --limit 1 --json htmlUrl
    Unknown JSON field: "htmlUrl"
    Available fields:
        attempt, conclusion, createdAt, databaseId, displayTitle, event, headBranch,
        headSha, name, number, startedAt, status, updatedAt, url,
        workflowDatabaseId, workflowName

`scripts/ghost_run_alarm.py` asked for `htmlUrl`, so `make ghost-run-alarm` — the ONE
alarm that watches `pull_request` runs carrying ZERO jobs (issue #1115) — died on its own
read (`exit 2`, "Unknown JSON field") and never once named a ghost, while the test stub that
answered ANY requested field kept `make test` green. A request the real CLI refuses must not
be able to pass the suite, so the field sets live HERE, once (rule 6d), and are used three
ways:

  * `request(command, fields)` — the seam a script builds its `--json` list through: an
    invented or renamed field raises here, before `gh` is called, and names the field.
  * `check_argv(argv)` — the seam a test stub `gh` validates a REQUEST through, so a stub
    can no longer answer a query the real CLI would refuse (rule 6m: the stub is an external
    system, not a contract-free echo).
  * `scan_scripts(root)` — the tree-wide scan `make lint` runs: EVERY `gh … --json …` call
    in `scripts/` is read and every field it asks for is checked against that command's set,
    so a second call site cannot drift silently. Issue #1158 covered `run list` only, which
    left 50 other reads failing at RUN time — the exact shape that hid for the whole life of
    the ghost alarm (issue #1160).

`gh api <path> --jq '<expr>'` names fields the SAME way (issue #1668): the REST answer is not
a `--json` field list, so `--scan` also reads every `gh api … --jq …` call in `scripts/`
through a SECOND recorded family (`API_SHAPES`, keyed by the endpoint path tail) and refuses
a path the recorded answer shape does not carry. `scripts/pr_health.py::read_run_identity`
reads `.actor.login + "|" + (.actor.type // "") + "|" + (.triggering_actor.login // "")` with
nothing validating it — the same build-time-vs-run-time hole #1158/#1160 closed for `--json`,
now closed for `--jq`.

The `--json … -q|--jq …` exemption carries its reason, so `check_argv()` enforces it (issue
#1676): when the SAME argv lists `--json <fields>` AND projects that answer through `-q|--jq`,
every path the expression reads must name one of those fields. Otherwise gh answers objects
carrying only the listed fields and the projection yields `null` at RUN time — measured:
`gh pr list --json number -q .title` passed green while `.title` was never requested.

Every set below is transcribed from the real CLI's own `Available fields:` answer for that
subcommand (recorded 2026-11-20), and every `API_SHAPES` entry from a live `gh api` read
(recorded 2026-11-24); none is invented. A command or endpoint family with no recorded set
gets NO opinion at request-BUILD time — but the TREE SCAN treats an unrecorded one as a
finding, so a `--jq` call site can never sit outside the contract silently.

BOUNDARY (issue #1675): this contract validates ONLY `--jq`/`-q` projections. A `gh api`
read that picks its fields in PYTHON — `payload.get("created_at")`,
`(c.get("user") or {}).get("login")`, `row["ref"]` — is OUT OF SCOPE and unchecked: `.get()`
answers `None` for a renamed field, so such a read fails only at RUN time. Measured on
origin/master `e93bc67d`: 32 `gh api` read sites in scripts/, 18 of them naming a REST field
in Python — 13 carrying no projection (one of them, refresh_run_block.py:105, is invisible to
the token-list scan because its prefix is the tuple constant `GH_API = ("gh", "api")`) plus 5
identity `--jq .[]` sites whose Python side still picks fields; 2 name no field
(pipeline_failure_issue.py:822 `/actions/jobs/{}/logs` is a log blob, queued_run_alarm.py:132
`-X POST -f` writes). Re-derive: `grep -rn '"api"' scripts/ | grep -v gh_json_fields.py` plus
the `GH_API` splat form.

SLICE 1 (issue #1683) now closes a RECORDED subset of that boundary: 13 no-projection
`gh api` sites — 12 found by token-list discovery plus the invisible `GH_API = ("gh",
"api")` tuple splat at `refresh_run_block.py:105` — are listed in `API_PYTHON_READ_SITES`
with their read scopes, and `API_PYTHON_FIELDS` records each family's REST answer fields.
`scan_file` runs `api_python_read_problems(tree)` as one extra pass, so a `.get("created_at")`
renamed to `.get("createdAt")` or a `r["ref"]` subscript renamed on those sites is a finding
with file:line at BUILD time. Registration is explicit, not inferred.

SLICE 2 (issue #1711) registers the 5 identity `--jq .[]` sites whose Python side still
picks fields — `announce_image_fallback.py`, `issue_thread.py`, `owed_rows_check.py`,
`pipeline_failure_issue.py`, `sweep_outcome.py` — as 5 more `API_PYTHON_READ_SITES`
records, adding `user`/`login` to the existing `issues/{}/comments` family. The `blocked`
partition keeps the whole-object half of `issue_thread.render` / `owed_rows_check.thread`
out of the identity answer's source set, so neither half false-reds. The 2 genuine
no-field sites and the general `.get()` surface stay OUT OF SCOPE for their own later slices.

Exit codes: 0 = no problem, 1 = a field or path gh cannot answer (or an unreadable
expression), 2 = the scan itself could not read the tree (never a silent clean).
"""
from __future__ import annotations

import argparse
import ast
import re
import shlex
import sys
from pathlib import Path
from typing import NamedTuple

#: Issue #1675: the Python-side REST read surface is OUT OF SCOPE for this contract.
#: Pinned on origin/master e93bc67d: 32 `gh api` read sites, 18 naming a field in Python.
PYTHON_GET_FIELDS_OUT_OF_SCOPE = True
UNVALIDATED_PYTHON_API_READ_SITES = 18

# --------------------------------------------------------------------------- recorded sets
# `gh run list` — `url` is gh's field for a run's HTML link; `htmlUrl` has NEVER existed.
RUN_LIST_FIELDS = frozenset({
    "attempt",
    "conclusion",
    "createdAt",
    "databaseId",
    "displayTitle",
    "event",
    "headBranch",
    "headSha",
    "name",
    "number",
    "startedAt",
    "status",
    "updatedAt",
    "url",
    "workflowDatabaseId",
    "workflowName",
})

# `gh run view` — the same surface PLUS `jobs`, which only the single-run read answers.
RUN_VIEW_FIELDS = frozenset(RUN_LIST_FIELDS | {"jobs"})

# `gh pr list` and `gh pr view` answer the same field set.
PR_FIELDS = frozenset({
    "additions",
    "assignees",
    "author",
    "autoMergeRequest",
    "baseRefName",
    "baseRefOid",
    "body",
    "changedFiles",
    "closed",
    "closedAt",
    "closingIssuesReferences",
    "comments",
    "commits",
    "createdAt",
    "deletions",
    "files",
    "fullDatabaseId",
    "headRefName",
    "headRefOid",
    "headRepository",
    "headRepositoryOwner",
    "id",
    "isCrossRepository",
    "isDraft",
    "labels",
    "latestReviews",
    "maintainerCanModify",
    "mergeCommit",
    "mergeStateStatus",
    "mergeable",
    "mergedAt",
    "mergedBy",
    "milestone",
    "number",
    "potentialMergeCommit",
    "projectCards",
    "projectItems",
    "reactionGroups",
    "reviewDecision",
    "reviewRequests",
    "reviews",
    "state",
    "statusCheckRollup",
    "title",
    "updatedAt",
    "url",
})

# `gh issue list` and `gh issue view` answer the same field set.
ISSUE_FIELDS = frozenset({
    "assignees",
    "author",
    "blockedBy",
    "blocking",
    "body",
    "closed",
    "closedAt",
    "closedByPullRequestsReferences",
    "comments",
    "createdAt",
    "id",
    "isPinned",
    "issueType",
    "labels",
    "milestone",
    "number",
    "parent",
    "projectCards",
    "projectItems",
    "reactionGroups",
    "state",
    "stateReason",
    "subIssues",
    "subIssuesSummary",
    "title",
    "updatedAt",
    "url",
})

LABEL_LIST_FIELDS = frozenset({
    "color",
    "createdAt",
    "description",
    "id",
    "isDefault",
    "name",
    "updatedAt",
    "url",
})

SECRET_LIST_FIELDS = frozenset({
    "name",
    "numSelectedRepos",
    "selectedReposURL",
    "updatedAt",
    "visibility",
})

WORKFLOW_LIST_FIELDS = frozenset({
    "id",
    "name",
    "path",
    "state",
})

REPO_VIEW_FIELDS = frozenset({
    "archivedAt",
    "assignableUsers",
    "codeOfConduct",
    "contactLinks",
    "createdAt",
    "defaultBranchRef",
    "deleteBranchOnMerge",
    "description",
    "diskUsage",
    "forkCount",
    "fundingLinks",
    "hasDiscussionsEnabled",
    "hasIssuesEnabled",
    "hasProjectsEnabled",
    "hasWikiEnabled",
    "homepageUrl",
    "id",
    "isArchived",
    "isBlankIssuesEnabled",
    "isEmpty",
    "isFork",
    "isInOrganization",
    "isMirror",
    "isPrivate",
    "isSecurityPolicyEnabled",
    "isTemplate",
    "isUserConfigurationRepository",
    "issueTemplates",
    "issues",
    "labels",
    "languages",
    "latestRelease",
    "licenseInfo",
    "mentionableUsers",
    "mergeCommitAllowed",
    "milestones",
    "mirrorUrl",
    "name",
    "nameWithOwner",
    "openGraphImageUrl",
    "owner",
    "parent",
    "primaryLanguage",
    "projects",
    "projectsV2",
    "pullRequestTemplates",
    "pullRequests",
    "pushedAt",
    "rebaseMergeAllowed",
    "repositoryTopics",
    "securityPolicyUrl",
    "squashMergeAllowed",
    "sshUrl",
    "stargazerCount",
    "templateRepository",
    "updatedAt",
    "url",
    "usesCustomOpenGraphImage",
    "viewerCanAdminister",
    "viewerDefaultCommitEmail",
    "viewerDefaultMergeMethod",
    "viewerHasStarred",
    "viewerPermission",
    "viewerPossibleCommitEmails",
    "viewerSubscription",
    "visibility",
    "watchers",
})

#: Every gh subcommand this repo asks fields of, and the fields gh answers for it.
FIELD_SETS: dict[str, frozenset[str]] = {
    "run list": RUN_LIST_FIELDS,
    "run view": RUN_VIEW_FIELDS,
    "pr list": PR_FIELDS,
    "pr view": PR_FIELDS,
    "issue list": ISSUE_FIELDS,
    "issue view": ISSUE_FIELDS,
    "label list": LABEL_LIST_FIELDS,
    "secret list": SECRET_LIST_FIELDS,
    "workflow list": WORKFLOW_LIST_FIELDS,
    "repo view": REPO_VIEW_FIELDS,
}

#: The name the #1158 tests and scripts already import (rule 6d: one table, many readers).
SUPPORTED_BY_COMMAND = FIELD_SETS


# --------------------------------------------------------------------------- gh api shapes
class ApiShape(NamedTuple):
    """The recorded read surface of one `gh api` endpoint family (issue #1668).

    `array` says whether the answer is a JSON ARRAY (then `paths` belong to each ELEMENT) or an
    OBJECT (then they belong to the root). A path is a dotted `--jq` reference such as
    `.actor.login`; a depth-0 path against an array answer is itself a finding.
    """

    array: bool
    paths: frozenset[str]


#: `gh api <path> --jq <expr>` names REST fields the same way `gh <cmd> --json <field>` does,
#: and gh refuses an unknown `--jq` path only at RUN time. Each family is keyed by the endpoint
#: path TAIL — everything after `repos/<owner>/<repo>/` — matched as a suffix, so `{repo}`,
#: `{owner}/{repo}` and a concrete `andyholst/trending-local-llms` all resolve to ONE family.
#: Every entry records the paths THIS REPOSITORY reads from that answer, transcribed from a live
#: `gh api` read (2026-11-24); an unrecorded path is a finding, exactly as an unrecorded
#: `--json` field is. Recording the whole recursive payload instead (~1000 paths across these
#: seven endpoints) would record fields no reader touches and rot silently when GitHub adds one.
API_SHAPES: dict[str, ApiShape] = {
    # `repos/{o}/{r}/issues/{n}` — `.body` (issue_review), `.state` (openspec_archive_check).
    "issues/{}": ApiShape(array=False, paths=frozenset({".body", ".state"})),
    # `repos/{o}/{r}/pulls/{n}` — what the closure check reads off a PR.
    "pulls/{}": ApiShape(array=False, paths=frozenset(
        {".merged", ".title", ".body", ".head.ref"})),
    # `repos/{o}/{r}/issues/{n}/comments` — a paginated ARRAY of comment objects; issue_queue
    # projects `[.[] | {createdAt, body}]`, the other readers take `.[]` whole.
    "issues/{}/comments": ApiShape(array=True, paths=frozenset({".createdAt", ".body"})),
    # `repos/{o}/{r}/commits/{ref}` — the commit's own committer date (issue_queue).
    "commits/{}": ApiShape(array=False, paths=frozenset({".commit.committer.date"})),
    # `repos/{o}/{r}/contents/{path}` — the base64 file content (keeper_pr).
    "contents/{}": ApiShape(array=False, paths=frozenset({".content"})),
    # `repos/{o}/{r}/actions/workflows/{file}/runs` — the page total (code_review).
    "actions/workflows/{}/runs": ApiShape(array=False, paths=frozenset({".total_count"})),
    # `repos/{o}/{r}/actions/runs/{run}` — WHO started a run (pr_health, issue #1646).
    "actions/runs/{}": ApiShape(array=False, paths=frozenset(
        {".actor.login", ".actor.type", ".triggering_actor.login"})),
}


# --------------------------------------------------------------------------- gh api Python reads
class ApiPythonReadSite(NamedTuple):
    """One recorded no-projection `gh api` read (issue #1683, slice 1).

    `caller` holds the request (or the endpoint literal), `root` names the local receiving
    the parsed answer, `elements` names loop vars bound to its items, and `readers` are the
    helper functions that pick fields from those names. `fields` is the field set re-derived
    by `api_python_read_problems`; `exclude` names keys read off an ALREADY-PROJECTED shape
    (`gh run view --json jobs`, already validated by `FIELD_SETS`), and `blocked` names a
    local carrying a PROJECTED row (the `run` built by `_project_run` in
    `pipeline_failure_issue.py`) so a pick from it is not attributed to this REST answer.
    Attribution is REGISTRY + ROOT, never "every `.get()` in the file".
    """

    file: str
    caller: str
    family: object
    root: tuple[str, ...]
    elements: tuple[str, ...]
    readers: tuple[str, ...]
    fields: frozenset[str]
    exclude: frozenset[str] = frozenset()
    blocked: frozenset[str] = frozenset()


#: The REST answer fields THIS REPOSITORY actually reads, per recorded family (issue #1683).
#: Same discipline as `API_SHAPES`: transcribe what the tree reads, not the whole recursive
#: payload, so a renamed field is a finding while GitHub adding an unused field is not.
#: Keys are endpoint path tails, or a tuple for a site whose endpoint is built dynamically.
API_PYTHON_FIELDS: dict[object, frozenset[str]] = {
    "branches/{}": frozenset({"required_status_checks", "strict", "contexts",
                              "enforce_admins", "enabled"}),
    "issues/comments": frozenset({"created_at", "user", "login", "id"}),
    "issues/{}/comments": frozenset({"body", "id", "comment_id", "created_at", "createdAt",
                                     "user", "login"}),
    "releases/latest": frozenset({"tag_name"}),
    "git/matching-refs/heads/{}": frozenset({"ref"}),
    "issues/{}": frozenset({"title", "body"}),
    "actions/runs?{}": frozenset({"workflow_runs", "id", "workflow_name", "name",
                                   "head_branch", "head_sha", "event", "created_at",
                                   "conclusion", "status", "html_url"}),
    "actions/jobs/{}": frozenset({"labels", "runnerName", "runner_name", "name",
                                   "id", "status", "started_at", "conclusion"}),
    ("issues", "pulls", "actions/runs", "commits"): frozenset({
        "workflow_runs", "head_branch", "event", "pull_requests", "number", "id",
        "status", "conclusion", "name", "sha", "body"}),
    ("actions/runs/{}", "actions/runs/{}/jobs"): frozenset({
        "html_url", "run_started_at", "jobs", "name", "started_at"}),
}

#: The 18 recorded sites that name a REST field in Python: 13 no-projection sites from
#: slice 1 (12 found by `_api_token_lists`, plus the `GH_API = ("gh", "api")` tuple splat in
#: `refresh_run_block.py:105` that discovery cannot see) and the 5 identity `--jq .[]` sites
#: from slice 2 (issue #1711). The 2 genuine no-field sites and the full analyzer stay later.
API_PYTHON_READ_SITES: tuple[ApiPythonReadSite, ...] = (
    ApiPythonReadSite("check_branch_protection.py", "main", "branches/{}",
                      ("protection",), (), ("verdict", "main"),
                      frozenset({"required_status_checks", "strict", "contexts",
                                 "enforce_admins", "enabled"})),
    ApiPythonReadSite("comment_monitor.py", "comment_ids", "issues/comments",
                      ("batch",), ("c",), (),
                      frozenset({"created_at", "user", "login", "id"})),
    ApiPythonReadSite("comment_watch.py", "gh_comments", "issues/comments",
                      ("payload", "comments"), ("c",), ("unseen",),
                      frozenset({"created_at", "user", "login"})),
    ApiPythonReadSite("dispatch_guard.py", "issue_comments", "issues/{}/comments",
                      ("payload",), ("page", "item", "raw"), ("normalize_comments",),
                      frozenset({"body", "id", "comment_id", "created_at", "createdAt"})),
    ApiPythonReadSite("hermes_pin_freshness.py", "read_channel", "releases/latest",
                      ("payload",), (), ("channel_tag",), frozenset({"tag_name"})),
    ApiPythonReadSite("issue_queue.py", "_branches", "git/matching-refs/heads/{}",
                      ("refs",), ("r",), (), frozenset({"ref"})),
    ApiPythonReadSite("issue_thread.py", "main", "issues/{}",
                      ("issue",), (), ("render",), frozenset({"title", "body"})),
    ApiPythonReadSite("owed_rows_check.py", "read_thread", "issues/{}",
                      ("issue", "issue_json"), (), ("thread",), frozenset({"body"})),
    ApiPythonReadSite("pipeline_failure_issue.py", "window_runs", "actions/runs?{}",
                      ("payload",), ("rows", "r", "row"), ("_project_run",),
                      frozenset({"workflow_runs", "id", "name",
                                 "head_branch", "head_sha", "event", "created_at",
                                 "conclusion", "status", "html_url"}),
                      blocked=frozenset({"run", "projected"})),
    ApiPythonReadSite("queued_run_alarm.py", "stuck_jobs", "actions/jobs/{}",
                      ("detail", "job"), (), ("stuck_jobs",),
                      frozenset({"labels", "runnerName", "runner_name", "name"}),
                      exclude=frozenset({"status", "startedAt", "databaseId", "url",
                                         "minutes", "jobs"}),
                      blocked=frozenset({"run", "jobs"})),
    ApiPythonReadSite("queued_run_alarm.py", "comment_run", "issues/{}/comments",
                      ("existing",), ("c",), (), frozenset({"body"})),
    ApiPythonReadSite("watch_monitor.py", "fetch_payload",
                      ("issues", "pulls", "actions/runs", "commits"),
                      ("payload", "runs_payload", "run"), ("rows", "r"),
                      ("marker_state", "pull_token", "inject_run_prs"),
                      frozenset({"workflow_runs", "head_branch", "event", "pull_requests",
                                 "number", "id", "status", "conclusion", "name", "sha"}),
                      exclude=frozenset({"comments", "runs", "master", "run_prs",
                                         "COMMENTS_V2_KEY"})),
    ApiPythonReadSite("refresh_run_block.py", "fetch",
                      ("actions/runs/{}", "actions/runs/{}/jobs"),
                      ("meta", "jobs"), ("job",), ("legs_and_aggregate",),
                      frozenset({"html_url", "run_started_at", "jobs", "name",
                                 "started_at"})),
    # Slice 2 / issue #1711: the 5 identity `--jq .[]` sites. `blocked` keeps the
    # whole-object half of a shared reader out of this identity answer's source set.
    ApiPythonReadSite("announce_image_fallback.py", "read_comments", "issues/{}/comments",
                      ("out", "comments"), ("comment",), ("already_announced",),
                      frozenset({"body"})),
    ApiPythonReadSite("issue_thread.py", "main", "issues/{}/comments",
                      ("raw", "comments"), ("c",), ("render",),
                      frozenset({"user", "login", "created_at", "body"}),
                      blocked=frozenset({"issue"})),
    ApiPythonReadSite("owed_rows_check.py", "read_thread", "issues/{}/comments",
                      ("raw", "comments"), ("c",), ("thread",),
                      frozenset({"created_at", "body"}),
                      blocked=frozenset({"issue", "issue_json"})),
    ApiPythonReadSite("pipeline_failure_issue.py", "_issue_comments", "issues/{}/comments",
                      ("raw",), ("c",),
                      ("post_rediagnose_comment", "post_stamp_comment",
                       "post_attribution_comment"),
                      frozenset({"body"})),
    ApiPythonReadSite("sweep_outcome.py", "_comments", "issues/{}/comments",
                      ("out", "comments"), ("comment",), ("already_said",),
                      frozenset({"createdAt", "body"})),
)

_IDENT = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
_JQ_STRING = re.compile(r'"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'')


def _api_template(path) -> str:
    """Normalize an endpoint literal: drop the query string and leading `/`, collapse every
    `{...}` placeholder to `{}`."""
    text = str(path).split("?", 1)[0].strip().lstrip("/")
    return re.sub(r"\{[^}]*\}", "{}", text)


def match_api_family(path) -> str | None:
    """The recorded `gh api` family an endpoint names, or None when it names none.

    Matched as a path-TAIL suffix, longest family first, so the owner/repo prefix never decides
    the family and two spellings of the same endpoint cannot drift apart. A `{}` segment in the
    FAMILY is a wildcard for one path segment (`contents/{}` covers `contents/OPENSPEC.md` and
    `contents/anything`); a concrete segment must match exactly.
    """
    segments = [s for s in _api_template(path).split("/") if s]
    for family in sorted(API_SHAPES, key=lambda f: -len(f.split("/"))):
        head = family.split("/")
        if len(head) > len(segments):
            continue
        tail = segments[-len(head):]
        if all(key == "{}" or key == seg for key, seg in zip(head, tail)):
            return family
    return None


def jq_paths(expr: str):
    """`(depth, dotted-path)` pairs a `--jq` expression READS, or None when unreadable.

    `depth` counts the `.[]`/`[]` iterations the path sits under: depth 0 is the response root,
    depth >= 1 is the array element. String literals are skipped, a `.a.b` chain is one path,
    `{a, b}` object construction contributes its shorthand identifiers. Anything the scan cannot
    confidently read returns None — the caller reports it, never silently passes.
    """
    text = _JQ_STRING.sub(" ", str(expr))
    found: list[tuple[int, str]] = []
    depth = 0
    i = 0
    while i < len(text):
        ch = text[i]
        if ch == "[" and text[i:i + 2] == "[]":
            depth += 1
            i += 2
            continue
        if ch == ".":
            m = _IDENT.match(text, i + 1)
            if not m:
                i += 1
                continue
            parts = [m.group(0)]
            j = m.end()
            while j < len(text) and text[j] == ".":
                m2 = _IDENT.match(text, j + 1)
                if not m2:
                    break
                parts.append(m2.group(0))
                j = m2.end()
            found.append((depth, "." + ".".join(parts)))
            i = j
            continue
        if ch == "{":
            end = text.find("}", i)
            if end < 0:
                return None
            for item in text[i + 1:end].split(","):
                item = item.strip()
                m = _IDENT.match(item, 0)
                if m and m.end() == len(item):       # shorthand `{createdAt, body}`
                    found.append((depth, "." + m.group(0)))
            i = end + 1
            continue
        i += 1
    return found


def api_jq_problems(endpoint: str, expr: str) -> list[str]:
    """Problems with one `gh api <endpoint> --jq <expr>` request ([] when it reads only
    recorded paths). Bare messages — the caller prefixes `file:line` / the argv context."""
    family = match_api_family(endpoint)
    if family is None:
        return [f"`gh api {endpoint} --jq` names an endpoint family this contract does not "
                "record — record the endpoint's read fields first"]
    shape = API_SHAPES[family]
    paths = jq_paths(expr)
    if paths is None:
        return [f"`gh api {family} --jq {expr}` is an expression this scan cannot read — "
                "build it as a literal or a module constant"]
    problems = []
    for depth, path in paths:
        if (depth == 0) == shape.array:
            where = "from the array element" if depth else "from the root"
            what = "an array" if shape.array else "an object"
            problems.append(f"`gh api {family} --jq {expr}` reads {path} {where}, but the "
                            f"recorded answer is {what}")
        elif path not in shape.paths:
            problems.append(f"`gh api {family} --jq {expr}` asks for {path}, which the recorded "
                            f"answer shape of that endpoint does not carry (recorded: "
                            f"{', '.join(sorted(shape.paths)) or 'none'})")
    return problems


# --------------------------------------------------------------------------- Python-side read extractor
_PYTHON_ANSWER_WRAPPERS = frozenset({"_gh_json", "_gh", "_run", "json.loads", "as_list"})


def _py_unwrap(node):
    """Peel a guarded/defaulted expression to the value it actually reads from."""
    for _ in range(8):
        if isinstance(node, ast.BoolOp) and node.values:
            node = node.values[0]
        elif isinstance(node, ast.IfExp):
            node = node.body
        elif isinstance(node, ast.NamedExpr):
            node = node.value
        elif isinstance(node, ast.Starred):
            node = node.value
        else:
            return node
    return node


def _py_const(node) -> str | None:
    node = _py_unwrap(node)
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    return None


def _py_call_name(node) -> str | None:
    func = node.func
    if isinstance(func, ast.Attribute):
        return func.attr
    return getattr(func, "id", None)


def _py_resolves(node, sources: set[str], loop_pairs: dict[str, frozenset[str]]) -> bool:
    """True when an expression is rooted at a registered answer/root/element name.

    `(x or {}).get("login")`, `if`/`else` defaults, `rows[0]`, `as_list(payload.get(...))`
    and the known answer wrappers (`_gh_json`, `_gh`, `_run`, `json.loads`) all resolve;
    an unrelated local (`os.environ.get("ISSUE")`, `raw.get(...)`) does not.
    """
    node = _py_unwrap(node)
    if isinstance(node, ast.Name):
        return node.id in sources
    if isinstance(node, ast.Call):
        if isinstance(node.func, ast.Attribute) and node.func.attr == "get" and node.args:
            return _py_resolves(node.func.value, sources, loop_pairs)
        if _py_call_name(node) in _PYTHON_ANSWER_WRAPPERS:
            return True
        return any(_py_resolves(arg, sources, loop_pairs) for arg in node.args)
    if isinstance(node, ast.Subscript):
        return _py_resolves(node.value, sources, loop_pairs)
    if isinstance(node, (ast.ListComp, ast.GeneratorExp)):
        return any(_py_resolves(g.iter, sources, loop_pairs) for g in node.generators)
    return False


def _py_pair_fields(tree: ast.Module) -> dict[str, frozenset[str]]:
    """Module-level `NAME = (("camel", "snake"), …)` tables -> their second column.

    `pipeline_failure_issue._RUN_ROW_FIELDS` holds the REST names the tree reads off an
    `actions/runs` row through a loop variable, so the extractor derives those literal
    names from the tree instead of hard-coding them here.
    """
    pairs: dict[str, frozenset[str]] = {}
    for node in tree.body:
        if not isinstance(node, ast.Assign) or not isinstance(node.targets[0], ast.Name):
            continue
        value = node.value
        if not isinstance(value, (ast.Tuple, ast.List)):
            continue
        fields = []
        for elt in value.elts:
            if not isinstance(elt, (ast.Tuple, ast.List)) or len(elt.elts) != 2:
                fields = []
                break
            first, second = _py_const(elt.elts[0]), _py_const(elt.elts[1])
            if first is None or second is None:
                fields = []
                break
            fields.append(second)
        if fields:
            pairs[node.targets[0].id] = frozenset(fields)
    return pairs


def api_python_read_problems(tree: ast.Module, file: str | None = None) -> list[str]:
    """Bare `line: problem` messages for the registered Python-side `gh api` reads.

    Each record is re-derived from the tree: walk `caller` plus its `readers`, collect
    literal keys whose receiver is `root`, an `elements` var, or a value derived from
    them by a recorded `.get()` chain, then require extracted == recorded and every
    extracted name to be a field of that answer's recorded family. An unknown name OR
    a set mismatch is a finding — a renamed REST field can no longer hide behind
    `.get()`'s `None`. With `file` set only that script's records are checked; bare,
    each applicable record is checked against whatever tree is handed in.
    """
    functions: dict[str, list] = {}
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            functions.setdefault(node.name, []).append(node)
    loop_pairs: dict[str, frozenset[str]] = {}
    pair_fields = _py_pair_fields(tree)
    for node in ast.walk(tree):
        if isinstance(node, (ast.For, ast.comprehension)) and isinstance(node.target, ast.Tuple):
            iterator = node.iter
            if isinstance(iterator, ast.Name) and iterator.id in pair_fields:
                for elt in node.target.elts:
                    if isinstance(elt, ast.Name):
                        loop_pairs[elt.id] = pair_fields[iterator.id]

    problems: list[str] = []
    for site in API_PYTHON_READ_SITES:
        if file is not None and site.file != file:
            continue
        anchor = functions.get(site.caller, [])
        at = getattr(anchor[0], "lineno", 0) if anchor else 0
        scopes = [node for name in (site.caller, *site.readers)
                  for node in functions.get(name, [])]
        if not scopes:
            problems.append(f"{at}: registered Python read scope {site.caller} "
                            f"({site.file}) is missing — the site cannot be checked")
            continue
        sources = (set(site.root) | set(site.elements)) - set(site.blocked)
        for _ in range(5):                      # fixed point over locals derived from root
            added: set[str] = set()
            for scope in scopes:
                for node in ast.walk(scope):
                    if isinstance(node, ast.Assign) and isinstance(node.targets[0], ast.Name):
                        if _py_resolves(node.value, sources, loop_pairs):
                            added.add(node.targets[0].id)
                    elif isinstance(node, (ast.For, ast.comprehension)):
                        targets = ([node.target.id] if isinstance(node.target, ast.Name)
                                   else [e.id for e in node.target.elts
                                         if isinstance(e, ast.Name)]
                                   if isinstance(node.target, ast.Tuple) else [])
                        if _py_resolves(node.iter, sources, loop_pairs):
                            added.update(targets)
            added -= set(site.blocked)
            if added <= sources:
                break
            sources |= added

        found: dict[str, int] = {}
        for scope in scopes:
            for node in ast.walk(scope):
                if (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                        and node.func.attr == "get" and node.args):
                    if not _py_resolves(node.func.value, sources, loop_pairs):
                        continue
                    arg = _py_unwrap(node.args[0])
                    keys = []
                    if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                        keys = [arg.value]
                    elif isinstance(arg, ast.Name) and arg.id in loop_pairs:
                        keys = sorted(loop_pairs[arg.id])
                    for key in keys:
                        if key not in site.exclude:
                            found.setdefault(key, node.lineno)
                elif isinstance(node, ast.Subscript):
                    key = _py_const(node.slice)
                    if (key is not None and key not in site.exclude
                            and _py_resolves(node.value, sources, loop_pairs)):
                        found.setdefault(key, node.lineno)

        recorded = set(site.fields)
        for key in sorted(set(found) - recorded):
            problems.append(
                f"{found[key]}: Python read of {key!r} off the recorded `gh api "
                f"{site.family}` answer is not recorded — a renamed REST field fails "
                "only at RUN time (issue #1683)")
        for key in sorted(recorded - set(found)):
            problems.append(f"{at}: recorded Python read field {key!r} at "
                            f"{site.file}:{site.caller} is no longer read by the tree "
                            "— re-record the site")
        expected = API_PYTHON_FIELDS.get(site.family)
        if expected is None:
            problems.append(f"{at}: `gh api {site.family}` Python read family is not "
                            "recorded in API_PYTHON_FIELDS")
        else:
            for key in sorted(set(found) - set(expected)):
                problems.append(f"{found[key]}: Python pick {key!r} is not a recorded "
                                f"field of the `gh api {site.family}` answer")
    return problems


def parse_fields(text: str) -> list[str]:
    """Split a `--json` argument into field names, preserving order."""
    return [part.strip() for part in str(text).split(",") if part.strip()]


def unknown_fields(command: str, fields) -> list[str]:
    """The fields gh cannot answer for `command` ([] when every field is supported, and
    [] when `command` is not in the recorded table — no opinion, never a false red)."""
    supported = SUPPORTED_BY_COMMAND.get(command)
    if supported is None:
        return []
    return [field for field in parse_fields(",".join(fields)) if field not in supported]


def request(command: str, fields: str) -> str:
    """Build a `--json` field list, REFUSING a field gh cannot answer (rule 6d: one seam).

    A script that spells a field wrong fails HERE — naming the field and the command —
    instead of getting a cryptic non-zero `gh` exit far from the typo.
    """
    bad = unknown_fields(command, [fields])
    if bad:
        raise ValueError(
            f"gh {command} --json asks for field(s) gh cannot answer: {', '.join(bad)} "
            f"(supported: {', '.join(sorted(SUPPORTED_BY_COMMAND[command]))}; "
            f"scripts/gh_json_fields.py, issue #1158)"
        )
    return fields


def command_path(argv) -> str | None:
    """The recorded gh command an argv list names, or None when it names none.

    The leading non-flag tokens are matched against the recorded table, so a positional
    argument after the subcommand (`gh run view 123 --json jobs`) does not become part of
    the command.
    """
    parts = []
    for token in argv:
        token = str(token)
        if token.startswith("-"):
            break
        parts.append(token)
    for command in sorted(FIELD_SETS, key=lambda c: -len(c.split())):
        head = command.split()
        if parts[:len(head)] == head:
            return command
    return None


def check_argv(argv) -> list[str]:
    """Problems with a `gh` argv list: a `--json` field gh cannot answer for that command, and
    (issue #1676) a `-q|--jq` projection that reads a field its own `--json` list omits."""
    argv = [str(a) for a in argv]
    if argv and argv[0] == "gh":
        argv = argv[1:]
    cmd = command_path(argv)
    problems = []
    listed: list[str] = []
    for i, token in enumerate(argv):
        if token != "--json":
            continue
        if i + 1 >= len(argv):
            problems.append("--json with no field list")
            continue
        listed.extend(parse_fields(argv[i + 1]))
        if cmd is None:
            problems.append(f"--json {argv[i + 1]!r} for a command this contract does not name")
            continue
        problems.extend(f"--json {cmd}: unknown field {field!r}"
                        for field in unknown_fields(cmd, [argv[i + 1]]))
    # issue #1676 — enforce the exemption's STATED reason. The `#1668` exemption above lets a
    # `--jq`/`-q` projection sit beside a `--json` field list because "that half already validated
    # the field this projection re-reads" — but nothing checked it, so `gh pr list --json number
    # -q .title` passed green while gh answered objects carrying only `number` and `.title`
    # yielded null at RUN time. When BOTH are present, every path the expression READS must name
    # one of the SAME argv's listed fields. `jq_paths` returning None stays tolerated (the grammar
    # deliberately refuses what it cannot read), the depth of an array iteration is irrelevant,
    # and the TOP-LEVEL segment is the field the projection re-reads.
    if listed:
        allowed = frozenset(listed)
        for i, token in enumerate(argv):
            if token not in ("--jq", "-q") or i + 1 >= len(argv):
                continue
            paths = jq_paths(argv[i + 1])
            if paths is None:
                continue
            for _depth, path in paths:
                field = path.lstrip(".").split(".", 1)[0]
                if field and field not in allowed:
                    problems.append(
                        f"{token} {argv[i + 1]!r} reads {path}, which the SAME argv's --json "
                        f"field list does not carry (listed: {', '.join(listed)})")
    # `gh api <endpoint> --jq <expr>` (issue #1668) — a field gh refuses only at RUN time.
    # Exempt when the SAME argv carries `--json`: that projection is now checked against the
    # listed fields in the issue-#1676 block above (the second path grammar over projected
    # output stays out of scope).
    if "--json" not in argv:
        for i, token in enumerate(argv):
            if token != "api":
                continue
            endpoint = next((argv[k] for k in range(i + 1, len(argv))
                             if not argv[k].startswith("-") and "/" in argv[k]), None)
            expression = next((argv[j + 1] for j in range(i + 1, len(argv))
                               if argv[j] in ("--jq", "-q") and j + 1 < len(argv)), None)
            if endpoint is None or expression is None:
                continue
            problems.extend(api_jq_problems(endpoint, expression))
    return problems


def _literal_string(node) -> str | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    return None


def _template_string(node) -> str | None:
    """A string literal, or an f-string rendered with `{}` placeholders for its expressions."""
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.JoinedStr):
        parts = []
        for value in node.values:
            parts.append(str(value.value) if isinstance(value, ast.Constant) else "{}")
        return "".join(parts)
    return None


def _string_bindings(tree: ast.Module) -> dict[str, str]:
    """Every `NAME = "<literal or f-string>"` binding in the module, at ANY scope.

    A name bound to two DIFFERENT values is dropped (unresolved) rather than guessed — the same
    discipline `_module_constants` applies to module-level `--json` field lists.
    """
    bindings: dict[str, str] = {}
    ambiguous: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign) or len(node.targets) != 1:
            continue
        target = node.targets[0]
        if not isinstance(target, ast.Name):
            continue
        value = _template_string(node.value)
        if value is None:
            continue
        name = target.id
        if name in bindings and bindings[name] != value:
            ambiguous.add(name)
        else:
            bindings[name] = value
    for name in ambiguous:
        bindings.pop(name, None)
    return bindings


def _api_token_lists(tree: ast.Module):
    """Every list literal and call-argument list as (node, [template-string or Name-id or None]).

    Unlike `_token_lists` (which keeps only plain literals so a DYNAMIC `--json` list stays
    UNRESOLVED), an f-string here becomes its `{}` TEMPLATE — an endpoint built as
    `f"repos/{repo}/issues/{n}"` still names its family.
    """
    for node in ast.walk(tree):
        if isinstance(node, ast.List):
            seq = node.elts
        elif isinstance(node, ast.Call):
            seq = node.args
        else:
            continue
        tokens = []
        for elt in seq:
            text = _template_string(elt)
            tokens.append(elt.id if text is None and isinstance(elt, ast.Name) else text)
        yield node, tokens


def _resolve_token(token, constants: dict[str, str]) -> str | None:
    """A token list entry as text: a literal stays itself, a Name resolves through the bindings."""
    if token is None:
        return None
    return constants.get(token, token)


def api_jq_requests(tree: ast.Module, constants: dict[str, str]):
    """(lineno, endpoint-or-None, expression-or-None) for every `gh api <path> --jq <expr>`.

    Two documented exemptions (issue #1668): a call carrying `--json` (that half already
    validates every field the command answers, and the projection re-reads it), and a call with
    NO `--jq`/`-q` expression. That exempts the ABSENCE OF A PROJECTION only: a
    no-projection read may still pick its fields in Python, and those picks are out of scope
    (issue #1675) — `--slurp`, `-f` and `-X POST` are not evidence that a call "names no field".
    """
    found = []
    for node, tokens in _api_token_lists(tree):
        if "--json" in tokens:
            continue
        for i, token in enumerate(tokens):
            if token != "api":
                continue
            endpoint = None
            for candidate in tokens[i + 1:]:
                value = _resolve_token(candidate, constants)
                if value is None or value.startswith("-") or "/" not in value:
                    continue
                endpoint = value
                break
            expression = None
            jq_at = next((j for j in range(i + 1, len(tokens)) if tokens[j] in ("--jq", "-q")), None)
            if jq_at is None:
                continue                 # no --jq/-q projection: exempt (Python-side field picks are out of scope, #1675)
            if jq_at + 1 < len(tokens):
                expression = _resolve_token(tokens[jq_at + 1], constants)
            found.append((getattr(node, "lineno", 0), endpoint, expression))
    return found


def _request_call_literal(node) -> str | None:
    """The field-list literal inside a `gh_json_fields.request("<cmd>", "<fields>")` call.

    A constant built THROUGH this module still has to be readable by the scan, or the seam
    would blind the very gate that exists to read the requests.
    """
    if not isinstance(node, ast.Call):
        return None
    func = node.func
    name = func.attr if isinstance(func, ast.Attribute) else getattr(func, "id", None)
    if name != "request" or len(node.args) < 2:
        return None
    return _literal_string(node.args[1])


def _module_constants(tree: ast.Module) -> dict[str, str]:
    """Module-level `NAME = "…"` string constants (adjacent literals are one Constant),
    including a `NAME = gh_json_fields.request("<cmd>", "<fields>")` built through this seam."""
    constants: dict[str, str] = {}
    for node in tree.body:
        if isinstance(node, ast.Assign) and isinstance(node.targets[0], ast.Name):
            value = _literal_string(node.value) or _request_call_literal(node.value)
            if value is not None:
                constants[node.targets[0].id] = value
    return constants


def _token_lists(tree: ast.Module):
    """Every list literal and call-argument list, as (node, [token or None])."""
    for node in ast.walk(tree):
        if isinstance(node, ast.List):
            seq = node.elts
        elif isinstance(node, ast.Call):
            seq = node.args
        else:
            continue
        tokens = []
        for elt in seq:
            text = _literal_string(elt)
            tokens.append(elt.id if text is None and isinstance(elt, ast.Name) else text)
        yield node, tokens


UNRESOLVED = "<unresolved --json field list>"


def command_before(tokens, end: int) -> str | None:
    """The recorded gh command a token sequence names BEFORE index `end`.

    Both parts must be string LITERALS: a helper that forwards a variable (`_gh_json(repo,
    "run", "list", …)`) still names its command literally, while a flag value that happens to
    equal a subcommand word cannot be mistaken for one.
    """
    for i in range(max(0, end - 1)):
        a, b = tokens[i], tokens[i + 1]
        if isinstance(a, str) and isinstance(b, str) and f"{a} {b}" in FIELD_SETS:
            return f"{a} {b}"
    return None


def gh_requests(tree: ast.Module) -> list[tuple[int, str | None, str]]:
    """(lineno, command-or-None, field-list-text) for every `gh … --json …` call in the module.

    A `--json` with no following token is an argparse flag, not a gh request. A `--json`
    whose field list is not a literal or a known module constant is reported as UNRESOLVED so
    the scan can never be satisfied by a dynamic field list.
    """
    constants = _module_constants(tree)
    found = []
    for node, tokens in _token_lists(tree):
        for i, token in enumerate(tokens):
            if token != "--json" or i + 1 >= len(tokens):
                continue
            cmd = command_before(tokens, i)
            value = tokens[i + 1]
            if value in constants:
                fields = constants[value]
            elif value is None:
                fields = UNRESOLVED
            else:
                fields = value
            found.append((getattr(node, "lineno", 0), cmd, fields))
    return found


def scan_file(path: Path) -> list[str]:
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except (OSError, SyntaxError) as exc:
        return [f"{path}: UNREADABLE ({exc})"]
    problems = []
    for lineno, cmd, fields in gh_requests(tree):
        if fields == UNRESOLVED:
            problems.append(f"{path}:{lineno}: a `gh … --json` field list this scan cannot "
                            "read — build it through gh_json_fields.request()")
            continue
        if cmd is None:
            problems.append(f"{path}:{lineno}: a `gh … --json {fields}` request whose command "
                            "this contract does not name — record the command's "
                            "`Available fields:` answer first")
            continue
        for field in unknown_fields(cmd, [fields]):
            problems.append(f"{path}:{lineno}: `gh {cmd} --json` asks for {field!r}, "
                            f"which gh cannot answer (supported: "
                            f"{', '.join(sorted(FIELD_SETS[cmd]))})")
    constants = _string_bindings(tree)
    for lineno, endpoint, expression in api_jq_requests(tree, constants):
        if endpoint is None:
            problems.append(f"{path}:{lineno}: a `gh api … --jq` request whose ENDPOINT this "
                            "scan cannot read — build it as a literal or a module constant")
            continue
        if expression is None:
            problems.append(f"{path}:{lineno}: a `gh api {endpoint} --jq` request whose "
                            "EXPRESSION this scan cannot read — build it as a literal or a "
                            "module constant")
            continue
        for problem in api_jq_problems(endpoint, expression):
            problems.append(f"{path}:{lineno}: {problem}")
    # issue #1683 slice 1: one extra pass over the REGISTERED no-projection Python reads.
    # The `--jq` path above is untouched, so a green tree stays green; a planted rename
    # on any of the 13 sites is now a finding with file:line (bare messages get the path).
    for problem in api_python_read_problems(tree, path.name):
        problems.append(f"{path}:{problem}")
    return problems


def scan_scripts(root: Path) -> list[str]:
    scripts = root / "scripts"
    if not scripts.is_dir():
        raise FileNotFoundError(f"no scripts/ under {root}")
    problems: list[str] = []
    for path in sorted(scripts.glob("*.py")):
        problems.extend(scan_file(path))
    return problems


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="the one gh --json field contract")
    ap.add_argument("--fields", action="store_true", help="print the recorded field sets")
    ap.add_argument("--check-command", metavar="CMD", help="command path to opine on")
    ap.add_argument("--check-fields", metavar="FIELDS", help="a --json field list to validate")
    ap.add_argument("--check-argv", default=None, metavar="GH-COMMAND",
                    help="a whole `gh …` command line (quoted) to validate; the stub gh calls this")
    ap.add_argument("--scan", action="store_true", help="scan scripts/ for gh --json fields")
    ap.add_argument("--root", default=None, help="repository root for --scan")
    args = ap.parse_args(argv)

    if args.fields:
        for command in sorted(FIELD_SETS):
            print(f"{command}: " + ", ".join(sorted(FIELD_SETS[command])))
        return 0
    if args.check_command is not None or args.check_fields is not None:
        if args.check_command is None or args.check_fields is None:
            print("[gh-json-fields] --check-command and --check-fields go together")
            return 2
        bad = unknown_fields(args.check_command, [args.check_fields])
        if bad:
            print(f"Unknown JSON field: {bad[0]!r} for gh {args.check_command}")
            return 1
        print(f"[gh-json-fields] OK gh {args.check_command} --json {args.check_fields}")
        return 0
    if args.check_argv is not None:
        problems = check_argv(shlex.split(args.check_argv))
        if problems:
            for problem in problems:
                print(f"Unknown JSON field ({problem})")
            return 1
        print("[gh-json-fields] OK")
        return 0
    if args.scan:
        try:
            problems = scan_scripts(Path(args.root) if args.root else Path(__file__).resolve().parent.parent)
        except (OSError, FileNotFoundError) as exc:
            print(f"[gh-json-fields] SCAN UNREADABLE (exit 2, never a silent clean): {exc}")
            return 2
        if problems:
            print(f"[gh-json-fields] FAIL {len(problems)} gh --json request(s) ask for "
                  "fields gh cannot answer:")
            for problem in problems:
                print(f"  {problem}")
            return 1
        print(f"[gh-json-fields] OK every `gh … --json` request in scripts/ asks only "
              f"for fields gh can answer, and every `gh api … --jq` path is one the recorded "
              f"endpoint shape carries ({len(FIELD_SETS)} commands, {len(API_SHAPES)} api "
              f"families recorded)")
        return 0
    ap.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())
