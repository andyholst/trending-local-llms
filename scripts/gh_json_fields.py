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

Every set below is transcribed from the real CLI's own `Available fields:` answer for that
subcommand (recorded 2026-11-20); none is invented. A command with no recorded set gets NO
opinion (`unknown_fields` returns `[]`) — adding one means recording the CLI's answer first.

Exit codes: 0 = no problem, 1 = a field gh cannot answer (or an unreadable `--json`
expression), 2 = the scan itself could not read the tree (never a silent clean).
"""
from __future__ import annotations

import argparse
import ast
import shlex
import sys
from pathlib import Path

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
    """Problems with a `gh` argv list: a `--json` field gh cannot answer for that command."""
    argv = [str(a) for a in argv]
    if argv and argv[0] == "gh":
        argv = argv[1:]
    cmd = command_path(argv)
    problems = []
    for i, token in enumerate(argv):
        if token != "--json":
            continue
        if i + 1 >= len(argv):
            problems.append("--json with no field list")
            continue
        if cmd is None:
            problems.append(f"--json {argv[i + 1]!r} for a command this contract does not name")
            continue
        problems.extend(f"--json {cmd}: unknown field {field!r}"
                        for field in unknown_fields(cmd, [argv[i + 1]]))
    return problems


def _literal_string(node) -> str | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    return None


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
              f"for fields gh can answer ({len(FIELD_SETS)} commands recorded)")
        return 0
    ap.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())
