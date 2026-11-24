#!/usr/bin/env python3
"""The fleet's dispatch guard (issue #1416): refuse a stale target and bound lane concurrency.

Owner directive, measured on asimov@mac 2026-11-23: **7 concurrent `tll-implementer`
lanes on one host** — load average 7.08, `Virtualization.framework` at 348% CPU (one shared
container VM), lane runtimes 128/94/76/70/66 min. Two of them were DUPLICATE work: #1239
ran 95 min on an issue that was already **CLOSED** (PR #1242 merged 13:19:42Z as `58469c00`),
and #1250 was stacked on #1246/#1247 and became add/add conflicts when #1247 merged. Root
causes: nothing refused a dispatch whose target was already closed or already merged, and
nothing bounded how many lanes run at once.

This is the ONE implementation of the dispatch rules (rule 6d). It decides, it never spawns a lane:

  stale target  — REFUSE when the issue is CLOSED, or when the PR bound to that issue
                  (`closingIssuesReferences`) is already MERGED;
  concurrency   — REFUSE above ONE ceiling constant (`ACTIVE_LANE_CEILING`, default 3) on
                  the active-lane count read from a CALLER-OWNED registry file;
  shared files  — REFUSE when a `--claim <repo-relative path>` overlaps a path another
                  ACTIVE lane already claims in that same registry (issue #1458), naming
                  the holding lane.
  cross-host    — REFUSE when ANOTHER host holds a NEWER ACTIVE working-claim on the SAME
                  issue (issue #1569), read from the ISSUE THREAD every host shares: the
                  signed `BOT <lane> · working on #<id>` / `· dispatch #<id>` markers, their
                  machine line (`user@host`) and their `createdAt`. The refusal names the
                  holding host, lane and comment id. A caller whose OWN marker is the newest
                  is ALLOWED to re-dispatch; a claim whose host cannot be named does not
                  block (the guard refuses a DIFFERENT, named host, never invents one).

Exit codes: 0 = dispatch allowed; 1 = refused for a STALE TARGET (closed issue / merged PR),
for being OVER the ceiling, for a shared-file CLAIM overlapping an ACTIVE lane, or for a
NEWER ACTIVE working-claim held by ANOTHER host on the issue thread;
2 = the guard could not decide — no registry, an unreadable registry, an unreadable
GitHub state — never a silent clean. A caller that wants a verdict without acting takes
`--json`.

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
    make dispatch-check ISSUE=1458 CLAIMS="agents/tll-planner/skills/tll-planner/SKILL.md"
    python3 scripts/dispatch_guard.py --issue 1416 --repo andyholst/trending-local-llms
    python3 scripts/dispatch_guard.py --issue 1239 --from-file recorded.json
    python3 scripts/dispatch_guard.py --issue 1458 --claim agents/x --claim docs/y --from-file f.json
    python3 scripts/dispatch_guard.py --issue 1569 --from-file f.json --comments-file thread.json
    python3 scripts/dispatch_guard.py --help

The registry's per-lane rows (`lanes`, issue #1458) carry the shared files each lane will
touch; the overlap check reads them ONLY when at least one `--claim` (or `CLAIMS=`) is
given, so a claim-free invocation behaves exactly as it did before the check existed.

The cross-host half (#1569) reads the issue's comments through the SAME seam discipline:
live through `gh api repos/<repo>/issues/<n>/comments --paginate --slurp` when a repo is
given, a RECORDED thread otherwise (`--comments-file`, or a `comments` list inside the
`--from-file` payload). The tests drive the REAL parser over recorded threads — no network,
and no credential value appears in this module or its fixtures.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import shlex
import shutil
import socket
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

#: The registry's per-lane rows: `lanes` is a list (or a lane-keyed object) of
#: `{lane|name|id|profile, state|status, claims: [<repo-relative path>, …]}` entries. A row
#: whose state is `active` HOLDS its claims against another dispatch; any other state
#: (`finished`, …) does not. Absent or empty means no lane has declared claims yet, which
#: is the backward-compatible shape every pre-#1458 registry already has.
REGISTRY_LANES_KEY = "lanes"

#: How many recently-updated PRs the bound-PR scan reads. A merged PR that closed the
#: issue ages out of the list, so the window is bounded (never unbounded) and the branch-name
#: convention is the second window for a PR the binding no longer carries.
PR_LIST_LIMIT = 100

#: The env var that pins the caller's machine id (`user@host`, rule 6u). Unset = derive it
#: from the host (`getpass.getuser()` + the first label of `socket.gethostname()`), which is
#: the same identity the fleet writes into its claims.
MACHINE_ENV = "TLL_MACHINE"

#: The signed markers that HOLD an issue (issue #1569). A planner's `dispatch` names the lane
#: it is about to start; a lane's `working on` is the claim itself. Both are read because the
#: collision this guard prevents happens BETWEEN the dispatch and the lane's first comment.
CLAIM_KINDS = ("working on", "dispatch")

#: The signed markers that RELEASE an issue, so a claim that landed or moved on cannot block
#: the next dispatch forever: the implementer's delivery/handover (`pr`), its signed end
#: (`done`), and the reviewer taking over (`reviewing`).
RELEASE_KINDS = ("done", "pr", "reviewing")

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


def _read_registry(registry: Path | None) -> dict:
    """The caller's registry payload; `{}` when the file does not exist yet.

    An absent file is the healthy empty registry, not an error. A file that exists but is
    unreadable or not a JSON object is a LOUD exit 2: the guard's whole purpose is that a
    state nobody can trust must not decide a dispatch.
    """
    if registry is None:
        raise Unreadable("no --registry was given — the guard cannot count active lanes")
    if not registry.is_file():
        return {}
    try:
        payload = json.loads(registry.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise Unreadable(f"registry {registry} could not be read: {exc}") from exc
    if not isinstance(payload, dict):
        raise Unreadable(f"registry {registry} is not a JSON object")
    return payload


def active_lane_count(registry: Path | None) -> int:
    """The active-lane count the CALLER's registry holds (0 when it does not exist yet).

    The count must be a whole number >= 0; anything else is a LOUD exit 2.
    """
    if registry is None:
        raise Unreadable("no --registry was given — the guard cannot count active lanes")
    if not registry.is_file():
        return 0
    payload = _read_registry(registry)
    raw = payload.get(REGISTRY_COUNT_KEY)
    if isinstance(raw, bool) or not isinstance(raw, int):
        raise Unreadable(
            f"registry {registry} has no integer `{REGISTRY_COUNT_KEY}` "
            f"(found: {raw!r}) — a count that is not a number cannot bound anything"
        )
    if raw < 0:
        raise Unreadable(f"registry {registry} counts {raw} active lanes — negative is not a count")
    return raw


def lane_entries(registry: Path | None) -> list[dict]:
    """The registry's per-lane rows, normalized to `{lane, state, claims}` (issue #1458).

    `lanes` may be a list of row objects or an object keyed by lane name; each row carries
    its display name (`lane`/`name`/`id`/`profile`), its `state`/`status`, and its
    repo-relative `claims`. An ABSENT key is the pre-#1458 shape and yields no rows, so a
    claim-free invocation never consults it. A present-but-malformed `lanes`/`claims` value
    is a loud exit 2, never a silent clean: a collision the guard cannot see is the defect
    this check exists to prevent.
    """
    raw = _read_registry(registry).get(REGISTRY_LANES_KEY)
    if raw is None:
        return []
    if isinstance(raw, dict):
        items = [{"lane": str(key), **value} for key, value in raw.items() if isinstance(value, dict)]
    elif isinstance(raw, list):
        items = [row for row in raw if isinstance(row, dict)]
    else:
        raise Unreadable(
            f"registry {registry} has a `{REGISTRY_LANES_KEY}` that is neither a list nor "
            f"an object (found: {type(raw).__name__})"
        )
    rows: list[dict] = []
    for item in items:
        name = next((str(item[key]) for key in ("lane", "name", "id", "profile") if item.get(key)), "")
        state = str(item.get("state", item.get("status", ""))).strip().lower()
        claims = item.get("claims")
        if claims is None:
            paths: tuple[str, ...] = ()
        elif isinstance(claims, (list, tuple)):
            if any(not isinstance(path, str) for path in claims):
                raise Unreadable(
                    f"registry {registry} lane {name or '<unnamed>'!r} has a `claims` entry "
                    f"that is not a path string"
                )
            paths = tuple(claims)
        else:
            raise Unreadable(
                f"registry {registry} lane {name or '<unnamed>'!r} has a `claims` that is "
                f"not a list (found: {type(claims).__name__})"
            )
        rows.append({"lane": name or "<unnamed>", "state": state, "claims": paths})
    return rows


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


# --------------------------------------------------------------------------- issue thread

#: A signed marker in a comment body: `BOT <lane> · <kind> #<issue>`, optionally carrying
#: `(host <user@host>)` between the lane and the middle dot (the shape rule 6u(b) asks a
#: claim to name). `kind` is one of CLAIM_KINDS / RELEASE_KINDS.
_MARKER_KINDS = "|".join(re.escape(kind) for kind in CLAIM_KINDS + RELEASE_KINDS)
_MARKER = re.compile(
    r"BOT\s+(?P<lane>[A-Za-z0-9][\w.-]*)\s*"
    r"(?:\(\s*host\s+(?P<host>[^)]+?)\s*\)\s*)?"
    r"\u00b7\s*(?P<kind>" + _MARKER_KINDS + r")\s*#(?P<issue>\d+)"
)

#: The machine line forms a comment actually carries: `(host user@host)`, a line that starts
#: `user@host ·` (the LOOK/status/WITHDRAW shape), or a `· user@host ·` span (the STATUS
#: marker shape). An arbitrary `user@host` token in prose is deliberately NOT read: real
#: dispatch comments QUOTE other hosts' markers, and attributing a claim to a host that was
#: merely mentioned is worse than leaving it unattributed.
_HOST_PAREN = re.compile(r"\(\s*host\s+([^)]+?)\s*\)")
_LINE_MACHINE = re.compile(r"(?m)^[ \t]*(?:[-*]\s+)?(?P<m>[A-Za-z0-9._-]+@[A-Za-z0-9._-]+)\b")
_DOT_MACHINE = re.compile(r"\u00b7\s*(?P<m>[A-Za-z0-9._-]+@[A-Za-z0-9._-]+)\s*\u00b7")


def default_machine() -> str:
    """The caller's own machine id (`user@host`), the identity its claims are compared to.

    Derived from the host rather than configured, so a fresh machine needs no setup; the
    first label of the hostname keeps `andy@Andys-MacBook-Pro.local` equal to the machine id
    `andy@Andys-MacBook-Pro` the fleet writes. `TLL_MACHINE` overrides it per invocation.
    """
    try:
        import getpass

        user = getpass.getuser()
    except Exception:  # pragma: no cover - an odd host with no passwd database
        user = os.environ.get("USER") or os.environ.get("LOGNAME") or "unknown"
    host = socket.gethostname().split(".")[0] or "localhost"
    return f"{user}@{host}"


def _machine_key(value: str) -> tuple[str, str]:
    """Case/label-insensitive identity: `asimov@omarchy.local` == `asimov@omarchy`."""
    text = str(value or "").strip().lower()
    user, sep, host = text.partition("@")
    if not sep:
        return (text, "")
    return (user.strip(), host.split(".")[0])


def same_machine(a: str, b: str) -> bool:
    """True when two machine ids name the SAME host."""
    return bool(a) and bool(b) and _machine_key(a) == _machine_key(b)


def comment_markers(body: str) -> list[dict]:
    """Every signed claim/release marker in one comment body.

    Returns `{lane, kind, issue, host}` rows in document order; `host` is the parenthetical
    `(host …)` when the marker itself carries one, else None.
    """
    out: list[dict] = []
    for m in _MARKER.finditer(body or ""):
        out.append({
            "lane": m.group("lane"),
            "kind": m.group("kind"),
            "issue": int(m.group("issue")),
            "host": (m.group("host").strip() if m.group("host") else None),
        })
    return out


def comment_machine(body: str) -> str | None:
    """The machine id a comment names about itself, or None when it names none.

    A claim written before rule 6u carried no identity at all, so this reads the spellings
    the fleet actually uses: `(host …)`, a line that starts `user@host ·`, or a
    `· user@host ·` span. Prose that merely MENTIONS a host (a dispatch quoting another
    host's claim) is not read — the guard never attributes a claim to a mentioned host.
    """
    m = _HOST_PAREN.search(body or "")
    if not m:
        m = _LINE_MACHINE.search(body or "")
    if not m:
        m = _DOT_MACHINE.search(body or "")
    if not m:
        return None
    if m.re is _HOST_PAREN:
        return m.group(1).strip()
    return m.group("m").strip()


def normalize_comments(comments) -> list[dict]:
    """Recorded/live comments to sorted `{id, body, created, machine}` rows (oldest first).

    Both API spellings are accepted (`created_at` from REST, `createdAt` from `gh --json`).
    """
    rows: list[dict] = []
    for raw in comments or []:
        if not isinstance(raw, dict):
            continue
        body = str(raw.get("body") or "")
        cid = raw.get("id") if raw.get("id") is not None else raw.get("comment_id")
        rows.append({
            "id": cid,
            "body": body,
            "created": str(raw.get("created_at") or raw.get("createdAt") or ""),
            "machine": comment_machine(body),
        })
    rows.sort(key=lambda row: (row["created"], str(row["id"])))
    return rows


def _epoch(text: str) -> float:
    """A comment's `createdAt` as seconds (0.0 when unparseable — nearest-neighbour only)."""
    try:
        return dt.datetime.fromisoformat(str(text).strip().replace("Z", "+00:00")).timestamp()
    except (ValueError, TypeError):
        return 0.0


def attribute_machines(rows: list[dict]) -> list[dict]:
    """Fill a claim whose OWN comment names no host from the NEAREST comment that does.

    The fleet's real threads mix identity-bearing and identity-free comments (a planner
    dispatch carries none; the LOOK/status lines around a claim do). Nearest-by-time is the
    attribution a human reader makes anyway; ties prefer the earlier comment. A thread with
    no machine id anywhere stays unattributed — the guard never invents a host.
    """
    known = [row for row in rows if row["machine"]]
    for row in rows:
        if row["machine"]:
            continue
        best = None
        best_key = None
        for other in known:
            key = (abs(_epoch(other["created"]) - _epoch(row["created"])),
                   0 if other["created"] <= row["created"] else 1)
            if best_key is None or key < best_key:
                best_key, best = key, other
        row["machine"] = best["machine"] if best else None
    return rows


def active_claim(rows: list[dict], issue: str) -> dict | None:
    """The NEWEST ACTIVE working-claim on `issue`, or None when nothing holds it.

    Claims and releases are replayed oldest-first by `(createdAt, comment id)`: a claim sets
    the holder, a later release (`done`/`pr`/`reviewing`) clears it. The survivor is the
    holder a second host must be refused against. Markers naming ANOTHER issue are ignored.
    """
    events: list[tuple[str, str, dict, dict]] = []
    for row in rows:
        for marker in comment_markers(row["body"]):
            if str(marker["issue"]) != str(issue):
                continue
            if marker["kind"] in CLAIM_KINDS or marker["kind"] in RELEASE_KINDS:
                events.append((row["created"], str(row["id"]), row, marker))
    events.sort(key=lambda event: (event[0], event[1]))
    holder: dict | None = None
    for _, _, row, marker in events:
        if marker["kind"] in CLAIM_KINDS:
            holder = {
                "comment_id": row["id"],
                "lane": marker["lane"],
                "kind": marker["kind"],
                "machine": marker["host"] or row["machine"],
                "created": row["created"],
            }
        else:
            holder = None
    return holder


def cross_host_reasons(holder: dict | None, machine: str) -> list[str]:
    """Why another host's ACTIVE claim blocks this dispatch (#1569), naming it.

    Refuses ONLY a DIFFERENT, NAMED host: the refusal must quote the holding host, lane and
    comment id, so a claim whose host cannot be read is reported as allowed rather than
    inventing a collision the thread does not state. The caller's own newest claim allows.
    """
    if not holder:
        return []
    holding = holder.get("machine")
    if not holding:
        return []
    if machine and same_machine(holding, machine):
        return []
    return [
        f"another host holds a NEWER ACTIVE working-claim: host {holding}, "
        f"lane {holder['lane']}, comment {holder['comment_id']} ({holder['created']}) "
        f"— one lane per issue across hosts"
    ]


def issue_comments(repo: str, issue: str) -> list[dict]:
    """The issue's comment thread, live through `gh api` (numeric ids + `created_at`)."""
    payload = json.loads(_run(gh_client(), [
        "api", "--paginate", "--slurp", f"repos/{repo}/issues/{issue}/comments",
    ]))
    rows: list[dict] = []
    if isinstance(payload, list):
        for page in payload:
            if isinstance(page, list):
                rows.extend(item for item in page if isinstance(item, dict))
            elif isinstance(page, dict):
                rows.append(page)
    return rows


def recorded_comments(path: str) -> list[dict]:
    """The fixture seam for the thread: a recorded list of comments (offline, no network).

    Accepts the plain list shape, the `--slurp` list-of-pages shape, or an object carrying
    a `comments` list. A missing/unreadable file is a loud exit 2, never an empty clean.
    """
    try:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise Unreadable(f"recorded comments {path!r} could not be read: {exc}") from exc
    if isinstance(payload, dict):
        payload = payload.get("comments") or []
    if not isinstance(payload, list):
        raise Unreadable(f"recorded comments {path!r} is not a list of comments")
    rows: list[dict] = []
    for item in payload:
        if isinstance(item, list):
            rows.extend(entry for entry in item if isinstance(entry, dict))
        elif isinstance(item, dict):
            rows.append(item)
    return rows


# --------------------------------------------------------------------------- shared files

def normalize_repo_path(raw: str) -> tuple[str, str]:
    """(normalized repo-relative path, refusal reason); a non-empty reason means unusable.

    A claim is REPO-RELATIVE by contract, so an absolute path (including one that points
    inside this checkout) and any path that climbs out with `..` are refused: the guard
    compares claims against other lanes' claims as repository paths, and a path in any
    other form cannot be compared honestly.
    """
    text = str(raw).strip()
    if not text:
        return "", "--claim needs a repo-relative path, not an empty value"
    if os.path.isabs(text) or text.startswith("~"):
        return "", (f"--claim {raw!r} must be a REPO-RELATIVE path, not an absolute "
                    f"(in-repo) path")
    parts = [part for part in text.split("/") if part not in ("", ".")]
    if any(part == ".." for part in parts):
        return "", f"--claim {raw!r} escapes the repository (`..` is not a repo-relative path)"
    if not parts:
        return "", f"--claim {raw!r} is not a repo-relative path"
    return "/".join(parts), ""


def paths_overlap(a: str, b: str) -> bool:
    """True when two normalized paths name the same file or one contains the other.

    Segment-boundary containment (not a raw string prefix): claiming a directory covers
    every file under it, so a lane holding `agents/x` blocks a dispatch onto
    `agents/x/SKILL.md`, and equality covers the exact-mirror race #1458 measured.
    """
    return a == b or a.startswith(b + "/") or b.startswith(a + "/")


def normalized_claims(claims: list[str]) -> tuple[list[str], list[str]]:
    """(usable normalized claims, refusal reasons for the unusable ones)."""
    usable: list[str] = []
    refusals: list[str] = []
    for raw in claims:
        path, refusal = normalize_repo_path(raw)
        if refusal:
            refusals.append(refusal)
        else:
            usable.append(path)
    return usable, refusals


def overlap_reasons(claims: list[str], lanes: list[dict]) -> list[str]:
    """One reason per ACTIVE-lane collision, naming the HOLDING lane (issue #1458).

    A FINISHED lane's claims do not block: its work landed or stopped, so the path is free.
    """
    reasons: list[str] = []
    for claim in claims:
        for lane in lanes:
            if lane.get("state") != "active":
                continue
            for held in lane.get("claims") or ():
                held_norm, _ = normalize_repo_path(held)
                if held_norm and paths_overlap(claim, held_norm):
                    reasons.append(
                        f"--claim {claim!r} overlaps {held_norm!r}, already claimed by ACTIVE "
                        f"lane {lane.get('lane')!r} — one lane per target path"
                    )
                    break
    return reasons


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
             reasons: list[str] | None = None,
             claims: list[str] | None = None,
             lanes: list[dict] | None = None,
             holder: dict | None = None,
             machine: str | None = None) -> dict:
    """The whole verdict as data (rule 6d): one dict, every reader a projection of it.

    `verdict` is `allow` or `refuse`; `reasons` is the ordered list a caller prints. The
    count is carried whenever the caller supplied one, so a refusal can still report how
    full the fleet was; `count=None` means "not consulted" (the stale target was refused
    first, and a registry nobody could read must not mask the target's own reason).

    `claims`/`lanes` are the shared-file check (#1458) and are consulted ONLY when at least
    one claim is given: with no claims this function returns exactly the pre-#1458 verdict.
    `holder`/`machine` are the cross-host check (#1569): an ACTIVE working-claim on the
    issue thread held by a DIFFERENT named host refuses, alongside every earlier check.
    """
    if reasons is None:
        reasons = stale_target_reasons(state)
        if count is not None:
            reasons += over_ceiling_reasons(count, ceiling)
        if claims:
            usable, unusable = normalized_claims(claims)
            reasons += unusable
            if lanes is not None:
                reasons += overlap_reasons(usable, lanes)
        if holder is not None:
            reasons += cross_host_reasons(holder, machine or "")
    return {
        "issue": state.get("issue"),
        "state": state.get("state"),
        "bound_prs": state.get("bound_prs") or [],
        "active_lanes": count,
        "ceiling": ceiling,
        "claims": list(claims or []),
        "thread_holder": holder,
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
    if verdict.get("claims"):
        lines.append(f"[dispatch-guard]   claims={verdict['claims']}")
    holder = verdict.get("thread_holder")
    if holder:
        lines.append(
            f"[dispatch-guard]   thread_holder={holder.get('machine') or 'unattributed'} "
            f"lane={holder.get('lane')} comment={holder.get('comment_id')}"
        )
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
            f"claims: repeat --claim <repo-relative path> (or CLAIMS=\"p1 p2\") to refuse an "
            f"overlap with a path an ACTIVE registry lane already claims; no --claim = the "
            f"pre-#1458 check only. cross-host: the issue's comments are read through gh "
            f"(or --comments-file offline) and a NEWER ACTIVE working-claim held by another "
            f"named host refuses; --machine/TLL_MACHINE names the caller. "
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
    ap.add_argument("--comments-file", default="",
                    help="a RECORDED issue-thread payload (offline; tests use it). Live mode "
                         "reads the issue's comments through gh")
    ap.add_argument("--machine", default=os.environ.get(MACHINE_ENV, ""),
                    help="the caller's machine id (user@host); default derives it from the "
                         "host (first hostname label), and a claim by the SAME host allows")
    ap.add_argument("--claim", action="append", default=[], metavar="PATH",
                    help="a REPO-RELATIVE path this dispatch will touch; repeatable "
                         "(or CLAIMS=\"p1 p2\") — refuses when an ACTIVE registry lane "
                         "already claims an overlapping path")
    ap.add_argument("--json", action="store_true", dest="as_json",
                    help="print the verdict as JSON (for a caller that parses it)")
    args = ap.parse_args(argv)

    registry, refusal = resolve_registry(args.registry or None)
    if refusal:
        print(f"REFUSED: {refusal} — the registry must be outside the repository", file=sys.stderr)
        return 2

    claims = list(args.claim) + shlex.split(os.environ.get("CLAIMS", ""))

    try:
        state = fetch_state(args.repo or None, args.issue, args.from_file or None)
        state["issue"] = args.issue
        count = active_lane_count(registry)
        lanes = lane_entries(registry) if claims else []
        if args.from_file:
            raw_comments = (recorded_comments(args.comments_file) if args.comments_file
                            else (state.get("comments") or []))
        else:
            raw_comments = issue_comments(args.repo or DEFAULT_REPO, args.issue)
        rows = attribute_machines(normalize_comments(raw_comments))
        holder = active_claim(rows, args.issue)
        machine = args.machine.strip() or default_machine()
        verdict = evaluate(state, count, args.ceiling, claims=claims, lanes=lanes,
                           holder=holder, machine=machine)
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
