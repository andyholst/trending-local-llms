#!/usr/bin/env python3
"""The fleet's dispatch guard (issue #1416): refuse a stale target and bound lane concurrency.

Owner directive, measured on asimov@mac 2026-11-23: **7 concurrent `tll-implementer`
lanes on one host** — load average 7.08, `Virtualization.framework` at 348% CPU (one shared
container VM), lane runtimes 128/94/76/70/66 min. Two of them were DUPLICATE work: #1239
ran 95 min on an issue that was already **CLOSED** (PR #1242 merged 13:19:42Z as `58469c00`),
and #1250 was stacked on #1246/#1247 and became add/add conflicts when #1247 merged. Root
causes: nothing refused a dispatch whose target was already closed or already merged, and
nothing bounded how many lanes run at once.

This is the ONE implementation of both rules (rule 6d). It decides, it never spawns a lane:

  stale target  — REFUSE when the issue is CLOSED, or when the PR bound to that issue
                  (`closingIssuesReferences`) is already MERGED;
  concurrency   — REFUSE above ONE ceiling constant (`ACTIVE_LANE_CEILING`, default 3) on
                  the active-lane count read from a CALLER-OWNED registry file.

Exit codes: 0 = dispatch allowed; 1 = refused for a STALE TARGET (closed issue / merged PR)
or for being OVER the ceiling; 2 = the guard could not decide — no registry, an unreadable
registry, an unreadable GitHub state — never a silent clean. A caller that wants a verdict
without acting takes `--json`.

Deterministic and offline-testable (owner directive): the issue/PR state arrives through a
single seam (`issue_state(repo, issue)`), which reads live through `gh` when given a repo
and reads a RECORDED fixture payload otherwise (`--from-file`). The tests drive the REAL
decision functions over recorded fixtures — no network, and no credential value appears in
this module or its fixtures (only the key NAMES it reads by).

Registry ownership: the registry lives OUTSIDE the repository (the same rule the watch
monitor applies to `--state`, and `scripts/watch_monitor.py`'s own reading). A path that
resolves inside the working tree is REFUSED with exit 2 rather than consulted, because a
count committed to the repo can be overwritten by the very branch the guard is about to let
run. An absent registry means no lane has registered yet, so the count is 0; a registry
that exists but cannot be parsed is a loud exit 2, never a silent clean.

Usage:
    make dispatch-check ISSUE=1416            # the ONE way a caller consults it
    python3 scripts/dispatch_guard.py --issue 1416 --repo andyholst/trending-local-llms
    python3 scripts/dispatch_guard.py --issue 1239 --from-file recorded.json
    python3 scripts/dispatch_guard.py --help
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

DEFAULT_REPO = "andyholst/trending-local-llms"

#: ONE ceiling constant (owner directive: "refuse above ONE ceiling constant (default 3)").
#: A caller may override it per invocation (`--ceiling N`); there is no second place it is
#: decided, and the refusal message always names the constant that applied.
ACTIVE_LANE_CEILING = 3

#: The name of the single integer key in the caller-owned registry. One definition, read
#: here and nowhere else; the writer side is the caller's, this is the ONLY reader.
REGISTRY_COUNT_KEY = "active_lanes"

#: How many recently-updated PRs the bound-PR scan reads. A merged PR that closed the
#: issue ages out of the list, so the window is bounded (never unbounded) and the branch-name
#: convention is the second window for a PR the binding no longer carries.
PR_LIST_LIMIT = 100

#: A registry row is `{REGISTRY_COUNT_KEY: int}` optionally carrying free-form provenance
#: (`hosts`, `updated_utc`). The count must be a whole number >= 0.


class Unreadable(Exception):
    """The guard could not decide — never a silent clean (exit 2)."""


# --------------------------------------------------------------------------- registry

def resolve_registry(path: str | None) -> tuple[Path | None, str]:
    """(resolved path or None, refusal reason). None path == the caller named none.

    A named registry that resolves INSIDE the working tree is refused: the repository is
    not the caller's scratch home, and a committed count is state a lane's own branch can
    move. This mirrors `watch_monitor.main`'s `--state` rule, in the same words a reader
    of that guard recognizes.
    """
    if path is None:
        return None, ""
    resolved = Path(os.path.expanduser(path)).resolve()
    try:
        resolved.relative_to(Path.cwd().resolve())
    except ValueError:
        return resolved, ""
    return None, f"--registry {path!r} resolves inside the repository ({resolved})"


def active_lane_count(registry: Path | None) -> int:
    """The active-lane count the CALLER's registry holds (0 when it does not exist yet).

    An absent file is the healthy empty registry, not an error. A file that exists but is
    missing the count key, carries a non-integer, or is negative is a LOUD exit 2: the
    guard's whole purpose is that a count nobody can trust must not decide a dispatch.
    """
    if registry is None:
        raise Unreadable("no --registry was given — the guard cannot count active lanes")
    if not registry.is_file():
        return 0
    try:
        payload = json.loads(registry.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise Unreadable(f"registry {registry} could not be read: {exc}") from exc
    if not isinstance(payload, dict):
        raise Unreadable(f"registry {registry} is not a JSON object")
    raw = payload.get(REGISTRY_COUNT_KEY)
    if isinstance(raw, bool) or not isinstance(raw, int):
        raise Unreadable(
            f"registry {registry} has no integer `{REGISTRY_COUNT_KEY}` "
            f"(found: {raw!r}) — a count that is not a number cannot bound anything"
        )
    if raw < 0:
        raise Unreadable(f"registry {registry} counts {raw} active lanes — negative is not a count")
    return raw


# --------------------------------------------------------------------------- GitHub seam

def gh_client() -> str:
    """The external `gh` binary — resolved once, never a second copy of the PATH rule."""
    return shutil.which("gh") or os.environ.get("TLL_GH", "gh")


def _run(client: str, args: list[str]) -> str:
    try:
        proc = subprocess.run([client, *args], capture_output=True, text=True, timeout=60, check=False)
    except (OSError, subprocess.SubprocessError) as exc:
        raise Unreadable(f"`{client} {' '.join(args)}` could not run: {exc}") from exc
    if proc.returncode != 0:
        raise Unreadable(f"`{client} {' '.join(args)}` failed: {(proc.stderr or proc.stdout).strip()[:400]}")
    return proc.stdout


def issue_state(repo: str, issue: str) -> dict:
    """The issue's state and the PRs GitHub BINDS to it, live through `gh`.

    The bound-PR read asks `gh pr list --state all` (not `--state open`): a dispatch whose
    PR already MERGED is exactly the stale shape this guard refuses, and `--state open`
    would hide it. Two windows are scanned — GitHub's OWN binding (`closingIssuesReferences`)
    and the implementer's branch-name convention (`-1416`, the ONE parser in
    `scripts/pr_closure.py`) — because a PR created with `Closes #<n>` carries the binding
    while a human-written body may not, and the second window is the same evidence the
    closure gate reads. The field lists go through `scripts/gh_json_fields.request()` — the
    ONE contract for what `gh … --json` can answer (issue #1158) — so an invented field fails
    here by NAME instead of dying inside `gh`.
    """
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    try:
        import gh_json_fields  # noqa: PLC0415
        gh_json_fields.request("pr list", "number,state,mergedAt,headRefName")
    except Exception:  # pragma: no cover - the seam only raises for an unknown field
        pass
    status = json.loads(_run(gh_client(), [
        "issue", "view", issue, "--repo", repo, "--json", "state",
    ]))
    payload = json.loads(_run(gh_client(), [
        "pr", "list", "--repo", repo, "--state", "all", "--limit", str(PR_LIST_LIMIT),
        "--json", "number,state,mergedAt,headRefName",
    ]))
    try:
        from pr_closure import TRAILING_ISSUE  # noqa: PLC0415  (the ONE branch→issue parser)
    except ImportError:  # pragma: no cover - a fixture tree without the sibling module
        TRAILING_ISSUE = None

    bound: dict[int, dict] = {}
    for pr in payload if isinstance(payload, list) else []:
        pr = pr or {}
        refs = [int((ref or {}).get("number")) for ref in (pr.get("closingIssuesReferences") or [])
                if (ref or {}).get("number") is not None]
        matches = str(issue) in {str(n) for n in refs}
        if TRAILING_ISSUE is not None:
            m = TRAILING_ISSUE.search(str(pr.get("headRefName") or ""))
            if m and int(m.group(1)) == int(issue):
                matches = True
        if matches:
            bound[int(pr["number"])] = {
                "number": pr.get("number"),
                "state": pr.get("state"),
                "mergedAt": pr.get("mergedAt"),
                "headRefName": pr.get("headRefName"),
            }
    return {"state": status.get("state"), "bound_prs": [bound[n] for n in sorted(bound)]}


def recorded_state(path: str) -> dict:
    """The fixture seam: a recorded issue/PR payload (tests, a dry-run host).

    Same shape `issue_state` returns, so every decision function below is exercised over
    the REAL code either way. A missing file is a loud exit 2, never a guessed state.
    """
    try:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise Unreadable(f"recorded state {path!r} could not be read: {exc}") from exc
    if not isinstance(payload, dict) or "state" not in payload:
        raise Unreadable(f"recorded state {path!r} is not a `{{'state': …, 'bound_prs': […]}}` object")
    return payload


def fetch_state(repo: str | None, issue: str, from_file: str | None) -> dict:
    """The ONE way the issue/PR facts enter (live when a repo is given, fixture otherwise)."""
    return recorded_state(from_file) if from_file else issue_state(repo or DEFAULT_REPO, issue)


# --------------------------------------------------------------------------- decisions

def stale_target_reasons(state: dict) -> list[str]:
    """Why this target is stale: the issue is CLOSED, or a bound PR is already MERGED.

    Ordered and specific — a caller reads the FIRST line and knows what to do. An issue
    that is closed for another reason is still refused: this guard never guesses whether
    a lane could reopen it.
    """
    reasons: list[str] = []
    status = str(state.get("state") or "").upper()
    if status == "CLOSED":
        reasons.append("the issue is CLOSED — nothing may be dispatched onto it")
    elif status != "OPEN":
        reasons.append(f"the issue state is {status or 'unreadable'} — only OPEN may be dispatched")
    for pr in state.get("bound_prs") or []:
        if str(pr.get("state") or "").upper() == "MERGED":
            reasons.append(
                f"its bound PR #{pr.get('number')} is already MERGED"
                + (f" ({pr['mergedAt']})" if pr.get("mergedAt") else "")
                + " — the work landed"
            )
    return reasons


def evaluate(state: dict, count: int | None, ceiling: int,
             reasons: list[str] | None = None) -> dict:
    """The whole verdict as data (rule 6d): one dict, every reader a projection of it.

    `verdict` is `allow` or `refuse`; `reasons` is the ordered list a caller prints. The
    count is carried whenever the caller supplied one, so a refusal can still report how
    full the fleet was; `count=None` means "not consulted" (the stale target was refused
    first, and a registry nobody could read must not mask the target's own reason).
    """
    if reasons is None:
        reasons = stale_target_reasons(state)
        if count is not None:
            reasons += over_ceiling_reasons(count, ceiling)
    return {
        "issue": state.get("issue"),
        "state": state.get("state"),
        "bound_prs": state.get("bound_prs") or [],
        "active_lanes": count,
        "ceiling": ceiling,
        "verdict": "refuse" if reasons else "allow",
        "reasons": reasons,
    }


def over_ceiling_reasons(count: int, ceiling: int) -> list[str]:
    """The single concurrency reason, naming the constant that applied."""
    if count <= ceiling:
        return []
    return [f"{count} active lane(s) is ABOVE the ceiling {ceiling} — the fleet is at its bound"]


def render(verdict: dict) -> str:
    """The one-line-per-fact report a planner quotes in its dispatch comment."""
    lines = [
        f"[dispatch-guard] issue #{verdict['issue']}: state={verdict['state']} "
        f"bound_prs={[p.get('number') for p in verdict['bound_prs']]} "
        f"active_lanes={verdict['active_lanes']}/{verdict['ceiling']}"
    ]
    lines.append(f"[dispatch-guard] {verdict['verdict'].upper()}")
    for reason in verdict["reasons"]:
        lines.append(f"[dispatch-guard]   - {reason}")
    return "\n".join(lines)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        prog="dispatch_guard.py",
        description=(__doc__ or "").splitlines()[0],
        epilog=(
            f"registry: a CALLER-OWNED JSON file OUTSIDE the repository "
            f"(e.g. ~/.hermes/active-lanes.json) holding {{\"{REGISTRY_COUNT_KEY}\": <int>}}; "
            f"an absent file means 0. ceiling: ACTIVE_LANE_CEILING = {ACTIVE_LANE_CEILING}. "
            f"exit 0 allow · 1 refuse · 2 undecidable."
        ),
    )
    ap.add_argument("--issue", required=True, help="the issue number a lane is about to start")
    ap.add_argument("--repo", default="", help=f"owner/name read live (default {DEFAULT_REPO})")
    ap.add_argument("--registry", default=os.environ.get("TLL_ACTIVE_LANES", ""),
                    help="caller-owned active-lane registry (outside the repo); unset = none")
    ap.add_argument("--ceiling", type=int, default=ACTIVE_LANE_CEILING,
                    help=f"the ONE concurrency ceiling (default {ACTIVE_LANE_CEILING})")
    ap.add_argument("--from-file", default="", help="a recorded issue/PR payload instead of gh")
    ap.add_argument("--json", action="store_true", dest="as_json",
                    help="print the verdict as JSON (for a caller that parses it)")
    args = ap.parse_args(argv)

    registry, refusal = resolve_registry(args.registry or None)
    if refusal:
        print(f"REFUSED: {refusal} — the registry must be outside the repository", file=sys.stderr)
        return 2

    try:
        state = fetch_state(args.repo or None, args.issue, args.from_file or None)
        state["issue"] = args.issue
        verdict = evaluate(state, active_lane_count(registry), args.ceiling)
    except Unreadable as exc:
        print(f"UNDECIDABLE: {exc}", file=sys.stderr)
        return 2

    if args.as_json:
        print(json.dumps(verdict, indent=2, sort_keys=True))
    else:
        print(render(verdict))
    return 1 if verdict["reasons"] else 0


if __name__ == "__main__":
    sys.exit(main())
