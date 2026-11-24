#!/usr/bin/env python3
"""Report-only stale working-claim sweep for the fleet board (#1265 design section 5, Child 1).

A stale working-claim blocks a shared branch with NO automatic signal: measured 2026-11-24 by
`tll-planner`, issue #1563's bot branch sat DIRTY/behind 3 for ~80 minutes under a claim that
never pushed, and PR #1561 needed three interventions in the same class. Two hosts guessing
differently about the same thread is the defect; the DECISION therefore lives HERE, in one
repo-owned deterministic seam (rule 6d), and the woken agent executes it instead of reasoning
about ages.

    make stale-claim-sweep            # live: READ-ONLY scan, prints one S: line per crossing
    make stale-claim-sweep CHECK=1    # offline contract, no network (the CI shape)

Output, one line per claim that crosses a threshold, NEWEST-LAST:

    S:<issue>:<claim-id>:<verdict>     verdict in {stale, released}

`<claim-id>` is `sha1(author + created_at + issue + body)[:12]`, computed from fields the API
already returns, so it is stable across ticks and needs no state file. `released` is the higher
verdict: the claim is unanswered past the release bound.

Grace (`#1265` section 2a, PINNED here as module constants — Child 2), with a `Makefile ?=`
override per bound and a floor the offline contract refuses to cross:

    SILENT claim   (no CI evidence):  STALE after 90 min   -> PING;  RELEASE after 180 min
    LIVE-RUN claim (run id attached): STALE after 180 min  -> PING;  RELEASE after 360 min

A claim counts as run-bearing when its OWN text carries a CI run id (`R:<id>`) or a PR number
(`PR #<n>`); the bound doubles because CI itself consumes wall clock.

The three authority limits (`#1265` section 3, named in `AUTHORITY_LIMITS`), enforced by the pure
half: a HUMAN-OWNED claim is never swept (the lane token is not one of the eight fleet lanes); a
LIVE-RUN/OPEN-PR claim is never swept under the silent bounds (it gets the doubled pair); and an
ALREADY-TERMINAL thread is never swept (a newer `done`/`handover`/`pr`/`reviewing`/`status`
comment, or a closed issue). Silence is the only stale signal trusted here.

This seam EMITS nothing and WRITES nothing: no comment, no label, no branch, no state file. It
is a report the caller reads. Dedup is available to the caller through the pure function's
`announced` argument (the claim ids it has already acted on); Child 4's writing half owns that
memory. An unreadable thread is a LOUD exit 2, never a silent clean.

The external `gh` CLI is the only stand-in a test needs; the request-building and the decision
here are the real product (rule 6m).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Collection, Iterable

DEFAULT_REPO = "andyholst/trending-local-llms"
ROOT = Path(__file__).resolve().parents[1]

#: The marker prefix. A detector marker, the same class as watch_monitor's C:/R:/M:/H: — it is
#: deliberately NOT registered in bot_markers.REGISTRY (that dict is the BOT-WINDOW registry).
MARKER_PREFIX = "S:"

#: Grace thresholds, in seconds (`#1265` section 2a). PINNED HERE, in ONE place, so two hosts
#: compute identical verdicts on the same thread; each pair is a `Makefile ?=` override and the
#: offline contract refuses any value below its floor (Child 2).
STALE_AFTER_SECONDS = 90 * 60        # SILENT claim: PING at 90 min
RELEASE_AFTER_SECONDS = 180 * 60     # SILENT claim: release at 180 min
#: A run-bearing claim gets twice the bound: CI itself consumes wall clock.
LIVE_RUN_MULTIPLIER = 2
LIVE_RUN_STALE_SECONDS = STALE_AFTER_SECONDS * LIVE_RUN_MULTIPLIER      # 180 min
LIVE_RUN_RELEASE_SECONDS = RELEASE_AFTER_SECONDS * LIVE_RUN_MULTIPLIER  # 360 min

#: The floors a caller may NOT tighten past (`make stale-claim-sweep CHECK=1` refuses them, and
#: the contract also asserts the PINNED values sit at or above their own floor): no claim is
#: called stale inside an hour, none released inside two hours, and the live-run pair keeps the
#: same proportions. Mirrors `watch_monitor.CLAIM_SETTLE_FLOOR_SECONDS`.
STALE_FLOOR_SECONDS = 60 * 60
RELEASE_FLOOR_SECONDS = 120 * 60
LIVE_RUN_STALE_FLOOR_SECONDS = LIVE_RUN_MULTIPLIER * STALE_FLOOR_SECONDS      # 120 min
LIVE_RUN_RELEASE_FLOOR_SECONDS = LIVE_RUN_MULTIPLIER * RELEASE_FLOOR_SECONDS  # 240 min

#: The three authority limits (`#1265` section 3), named so a reader can enumerate them:
#:
#:   "human"    the claim's lane is not one of the eight fleet lanes — the owner's and any
#:               collaborator's claim is NEVER swept (rule 6v reserves human acts).
#:   "live-run" the claim's own text carries a CI run id (`R:<id>`) or a PR number (`PR #<n>`)
#:               — it is NEVER swept under the SILENT bounds; the DOUBLED pair applies because
#:               CI itself consumes wall clock.
#:   "terminal" the issue is CLOSED, or the newest comment already moved the thread on (a
#:               `done`/`handover`/`pr`/`reviewing`/`status` line) — no claim is left to sweep.
AUTHORITY_LIMITS = ("human", "live-run", "terminal")
REFUSAL_HUMAN = "human"
REFUSAL_LIVE_RUN = "live-run"
REFUSAL_TERMINAL = "terminal"

#: `BOT <lane> · working on #<id> · …` — the AGENTS.md section 7b claim grammar. The middle dot
#: is `·`; `•` is accepted so a hand-typed variant cannot slip past as "not a claim".
#: A host may stamp its machine id before or after the lane token: the fleet's real claims are
#: `BOT tll-implementer · working on #N` and `BOT tll-implementer (host asimov@omarchy) · working
#: on #N`, and an older dispatch shape is `asimov@omarchy · BOT tll-implementer · working on #N`.
#: Accepting all three keeps the live sweep from reading as "nothing is stale" on the very board
#: it exists for; the lane token still decides fleet membership.
_HOST_STAMP = r"(?:[A-Za-z0-9_.-]+@[A-Za-z0-9_.-]+\s*[·•]\s*)?"
_CLAIM = re.compile(
    r"^\s*" + _HOST_STAMP +
    r"BOT\s+(?P<lane>[a-z0-9][a-z0-9-]*)(?:\s*\(host\s+[^)]+\))?\s*[·•]\s*"
    r"working on\s+#(?P<issue>\d+)\b")
#: A CI run id or a PR number attached to the claim's own text.
_RUN_ID = re.compile(r"\bR:\d+\b")
_PR_ID = re.compile(r"\bPR\s+#\d+\b")
#: Signed work comments that already moved a thread on (the newest-comment discriminators).
_DONE = re.compile(r"^\s*BOT\s+[a-z0-9][a-z0-9-]*\s*[·•]\s*done\s+#\d+\b")
_PR_LINE = re.compile(r"^\s*BOT\s+[a-z0-9][a-z0-9-]*\s*[·•]\s*pr\s+#\d+\b")
_REVIEWING = re.compile(r"^\s*BOT\s+[a-z0-9][a-z0-9-]*\s*[·•]\s*reviewing\s+#\d+\b")
_RELEASED = re.compile(r"^\s*BOT\s+[a-z0-9][a-z0-9-]*\s*[·•]\s*released\s+#\d+\b")


@dataclass(frozen=True)
class Comment:
    """One issue-comment row, reduced to the fields the decision reads."""

    id: str | int
    author: str
    created_at: datetime
    body: str


@dataclass(frozen=True)
class Thread:
    """One open issue and its comments, oldest-first as GitHub returns them."""

    number: int
    state: str
    comments: tuple[Comment, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class Verdict:
    """One claim that crossed a threshold."""

    issue: int
    claim_id: str
    kind: str  # "stale" | "released"
    age_seconds: int
    created_at: datetime

    def marker(self) -> str:
        return f"{MARKER_PREFIX}{self.issue}:{self.claim_id}:{self.kind}"


def parse_timestamp(value: object) -> datetime | None:
    """GitHub's ISO-8601 `createdAt` as an aware UTC datetime, or None when unreadable."""
    if not isinstance(value, str) or not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def claim_token(author: str, created_at: str, issue: int, body: str) -> str:
    """The stable per-claim id: `sha1(author + created_at + issue + body)[:12]` (`#1265` 1a)."""
    raw = f"{author}\n{created_at}\n{int(issue)}\n{body}"
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:12]


def parse_working_claim(body: object) -> tuple[str, int] | None:
    """`(lane, issue)` when `body` is a signed `working on` claim, else None."""
    if not isinstance(body, str):
        return None
    match = _CLAIM.match(body)
    if not match:
        return None
    return match.group("lane"), int(match.group("issue"))


def is_run_bearing(body: object) -> bool:
    """True when the claim's OWN text attaches a CI run id or a PR number (`#1265` 2a).

    This is the "live-run" authority limit: such a claim is NEVER swept under the silent bounds,
    it gets the doubled pair instead.
    """
    if not isinstance(body, str):
        return False
    return bool(_RUN_ID.search(body) or _PR_ID.search(body))


def is_human_claim(lane: str, lanes: Collection[str]) -> bool:
    """True when the claim's lane is outside the eight fleet lanes (the "human" limit, `#1265` 3A).

    The owner's and any collaborator's claim is never stale — rule 6v reserves human acts.
    """
    return lane not in set(lanes)


def is_terminal_thread(thread: Thread) -> bool:
    """True when a CLOSED issue, an empty thread, or one whose newest comment already moved on.

    The "terminal" limit (`#1265` 3C): a `done`/`handover`/`pr`/`reviewing`/`status` line, or any
    comment that is not a signed working-claim, means no claim is left to sweep.
    """
    if str(thread.state).strip().lower() != "open":
        return True
    newest = newest_comment(thread)
    if newest is None:
        return True
    return parse_working_claim(newest.body) is None


def newest_comment(thread: Thread) -> Comment | None:
    """The thread's newest comment by `createdAt` (id breaks an exact tie), or None."""
    if not thread.comments:
        return None
    return max(thread.comments, key=lambda c: (c.created_at, str(c.id)))


def fleet_lanes(root: Path | None = None) -> tuple[str, ...]:
    """The eight fleet lanes, DERIVED from `agents/tll-*/SOUL.md` (never a hand-kept list)."""
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import agent_model_chain  # noqa: E402  (lazy: the pure half above needs no tree)

    return tuple(agent_model_chain.fleet_lanes(root or ROOT))


def sweep_thread(thread: Thread, *, now: datetime, lanes: Collection[str] | None = None,
                 stale_after: int = STALE_AFTER_SECONDS,
                 release_after: int = RELEASE_AFTER_SECONDS,
                 live_stale_after: int = LIVE_RUN_STALE_SECONDS,
                 live_release_after: int = LIVE_RUN_RELEASE_SECONDS,
                 announced: Iterable[str] = ()) -> list[Verdict]:
    """Every threshold this thread's newest comment crosses — normally zero or one verdict.

    The decision, in order: a CLOSED or already-terminal thread has no claim to sweep; a claim by
    a non-fleet lane is a human's and is never stale; a claim naming a different issue is not this
    thread's claim; a run-bearing claim (`R:<id>` / `PR #<n>`) is never measured against the SILENT
    pair — it gets the doubled bounds; a fresh claim crosses nothing; and a claim the caller
    already announced is not re-reported (second-tick dedup).
    """
    if is_terminal_thread(thread):
        return []
    newest = newest_comment(thread)
    if newest is None:
        return []
    parsed = parse_working_claim(newest.body)
    if parsed is None:
        return []
    lane, named_issue = parsed
    known = set(fleet_lanes() if lanes is None else lanes)
    if is_human_claim(lane, known) or named_issue != thread.number:
        return []
    age = (now - newest.created_at).total_seconds()
    if age < 0:
        age = 0.0
    stale, release = stale_after, release_after
    if is_run_bearing(newest.body):
        stale, release = live_stale_after, live_release_after
    if age >= release:
        kind = "released"
    elif age >= stale:
        kind = "stale"
    else:
        return []
    created_raw = newest.created_at.isoformat()
    verdict = Verdict(
        issue=thread.number,
        claim_id=claim_token(newest.author, created_raw, thread.number, newest.body),
        kind=kind,
        age_seconds=int(age),
        created_at=newest.created_at,
    )
    if verdict.claim_id in set(announced):
        return []
    return [verdict]


def sweep_threads(threads: Iterable[Thread], *, now: datetime,
                  lanes: Collection[str] | None = None,
                  stale_after: int = STALE_AFTER_SECONDS,
                  release_after: int = RELEASE_AFTER_SECONDS,
                  live_stale_after: int = LIVE_RUN_STALE_SECONDS,
                  live_release_after: int = LIVE_RUN_RELEASE_SECONDS,
                  announced: Iterable[str] = ()) -> list[Verdict]:
    """Every thread's verdicts, NEWEST-LAST as the design's output contract states."""
    found: list[Verdict] = []
    for thread in threads:
        found.extend(sweep_thread(thread, now=now, lanes=lanes, stale_after=stale_after,
                                  release_after=release_after, live_stale_after=live_stale_after,
                                  live_release_after=live_release_after, announced=announced))
    return sorted(found, key=lambda v: (v.created_at, v.issue, v.claim_id))


# --------------------------------------------------------------------------- thin gh layer
def gh_client() -> str:
    return shutil.which("gh") or os.environ.get("TLL_GH", "gh")


def _gh(client: str, args: list[str]) -> str:
    """Run one `gh` command, raising on a non-zero exit or unparseable output."""
    proc = subprocess.run([client, *args], capture_output=True, text=True, timeout=60, check=False)
    if proc.returncode != 0:
        raise RuntimeError(f"gh {' '.join(args)} failed: {proc.stderr.strip() or 'non-zero exit'}")
    return proc.stdout


def comment_from_row(row: dict) -> Comment | None:
    """A `gh issue view --json comments` row as a Comment, or None when it cannot be read."""
    created = parse_timestamp(row.get("createdAt"))
    author = row.get("author")
    login = author.get("login") if isinstance(author, dict) else None
    cid = row.get("id")
    body = row.get("body")
    # `gh issue view --json comments` answers GraphQL node ids (strings) on a REST-shaped row;
    # a numeric id is accepted too. An unreadable row contributes no comment rather than
    # silently dropping the whole thread.
    if cid is None or isinstance(cid, bool) or not isinstance(cid, (int, str)):
        return None
    if isinstance(cid, str) and not cid.strip():
        return None
    if not isinstance(login, str) or created is None:
        return None
    return Comment(id=cid, author=login, created_at=created, body=body if isinstance(body, str) else "")


def thread_from_row(row: dict) -> Thread:
    """A `gh issue view --json number,state,comments` row as a Thread."""
    number = row.get("number")
    state = row.get("state")
    comments: list[Comment] = []
    for raw in row.get("comments") or []:
        if isinstance(raw, dict):
            comment = comment_from_row(raw)
            if comment is not None:
                comments.append(comment)
    comments.sort(key=lambda c: (c.created_at, str(c.id)))
    return Thread(number=number if isinstance(number, int) else 0,
                  state=str(state).strip().lower() if isinstance(state, str) else "",
                  comments=tuple(comments))


def fetch_open_threads(repo: str, client: str, limit: int = 200) -> list[Thread]:
    """Every OPEN issue and its comments, through `gh` alone.

    An unreadable LIST or THREAD raises — the caller turns that into a loud exit 2 rather than a
    partial report that reads as "nothing is stale" (the house style of every seam here).
    """
    listed = json.loads(_gh(client, ["issue", "list", "--repo", repo, "--state", "open",
                                     "--limit", str(limit), "--json", "number"]) or "[]")
    numbers = [row["number"] for row in listed
               if isinstance(row, dict) and isinstance(row.get("number"), int)]
    threads: list[Thread] = []
    for number in numbers:
        row = json.loads(_gh(client, ["issue", "view", str(number), "--repo", repo,
                                      "--json", "number,state,comments"]) or "{}")
        if not isinstance(row, dict):
            raise RuntimeError(f"gh issue view {number} returned no object")
        threads.append(thread_from_row(row))
    return threads


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--repo", default=os.environ.get("TLL_REPO", DEFAULT_REPO))
    ap.add_argument("--gh", default=None, help="explicit gh path for stripped cron environments")
    ap.add_argument("--limit", type=int, default=200,
                    help=f"cap on the open issues walked (default 200)")
    ap.add_argument("--check", action="store_true",
                    help="offline contract check; no network, no state")
    ap.add_argument("--stale-after", type=int, default=STALE_AFTER_SECONDS,
                    dest="stale_after", help=f"seconds before a SILENT claim is stale "
                                            f"(default {STALE_AFTER_SECONDS})")
    ap.add_argument("--release-after", type=int, default=RELEASE_AFTER_SECONDS,
                    dest="release_after", help=f"seconds before a SILENT claim is released "
                                               f"(default {RELEASE_AFTER_SECONDS})")
    ap.add_argument("--live-stale-after", type=int, default=LIVE_RUN_STALE_SECONDS,
                    dest="live_stale_after", help=f"seconds before a RUN-BEARING claim is stale "
                                                  f"(default {LIVE_RUN_STALE_SECONDS})")
    ap.add_argument("--live-release-after", type=int, default=LIVE_RUN_RELEASE_SECONDS,
                    dest="live_release_after", help=f"seconds before a RUN-BEARING claim is "
                                                    f"released (default {LIVE_RUN_RELEASE_SECONDS})")
    args = ap.parse_args(argv)

    if args.check:
        problems: list[str] = []
        pairs = (
            ("silent", args.stale_after, args.release_after),
            ("live-run", args.live_stale_after, args.live_release_after),
        )
        for label, stale, release in pairs:
            if stale <= 0 or release <= stale:
                problems.append(f"the {label} grace pair is not positive and ordered: "
                                f"stale={stale}s release={release}s")
        floors = (
            ("STALE_AFTER_SECONDS", STALE_AFTER_SECONDS, STALE_FLOOR_SECONDS),
            ("RELEASE_AFTER_SECONDS", RELEASE_AFTER_SECONDS, RELEASE_FLOOR_SECONDS),
            ("LIVE_RUN_STALE_SECONDS", LIVE_RUN_STALE_SECONDS, LIVE_RUN_STALE_FLOOR_SECONDS),
            ("LIVE_RUN_RELEASE_SECONDS", LIVE_RUN_RELEASE_SECONDS, LIVE_RUN_RELEASE_FLOOR_SECONDS),
        )
        for name, value, floor in floors:
            if value < floor:
                problems.append(f"the pinned {name}={value}s is below its {floor}s floor")
        override_floors = (
            ("--stale-after", args.stale_after, STALE_FLOOR_SECONDS),
            ("--release-after", args.release_after, RELEASE_FLOOR_SECONDS),
            ("--live-stale-after", args.live_stale_after, LIVE_RUN_STALE_FLOOR_SECONDS),
            ("--live-release-after", args.live_release_after, LIVE_RUN_RELEASE_FLOOR_SECONDS),
        )
        for flag, value, floor in override_floors:
            if value < floor:
                problems.append(f"{flag}={value}s is below the {floor}s floor")
        samples = (
            "BOT tll-implementer · working on #1610 · branch b · blocked on none · next y",
            "BOT tll-implementer (host asimov@omarchy) · working on #1610 · branch b",
            "asimov@omarchy · BOT tll-implementer · working on #1610 · branch b",
        )
        if any(parse_working_claim(sample) != ("tll-implementer", 1610) for sample in samples):
            problems.append("the working-claim grammar no longer parses every signed shape")
        plain = samples[0]
        if is_run_bearing(plain) or not is_run_bearing(f"{plain} — run R:12345"):
            problems.append("the run-bearing test no longer separates a plain claim from a run one")
        if AUTHORITY_LIMITS != (REFUSAL_HUMAN, REFUSAL_LIVE_RUN, REFUSAL_TERMINAL):
            problems.append("the three authority limits are no longer named together")
        if MARKER_PREFIX != "S:":
            problems.append("the marker prefix changed")
        if problems:
            for problem in problems:
                print(f"CHECK FAILED: {problem}", file=sys.stderr)
            return 2
        print(f"[stale-claim-sweep] OK: {MARKER_PREFIX}<issue>:<claim-id>:<stale|released>, "
              f"grace silent stale={args.stale_after}s release={args.release_after}s, "
              f"live-run stale={args.live_stale_after}s release={args.live_release_after}s "
              f"(x{LIVE_RUN_MULTIPLIER} when the claim carries a run id), floors "
              f"{STALE_FLOOR_SECONDS}/{RELEASE_FLOOR_SECONDS}/"
              f"{LIVE_RUN_STALE_FLOOR_SECONDS}/{LIVE_RUN_RELEASE_FLOOR_SECONDS}s, "
              f"read-only, no state")
        return 0

    try:
        threads = fetch_open_threads(args.repo, args.gh or gh_client(), args.limit)
    except Exception as exc:  # a partial report would read as "nothing is stale"
        print(f"[stale-claim-sweep] READ FAILED: {exc}", file=sys.stderr)
        return 2

    now = datetime.now(timezone.utc)
    for verdict in sweep_threads(threads, now=now, stale_after=args.stale_after,
                                release_after=args.release_after,
                                live_stale_after=args.live_stale_after,
                                live_release_after=args.live_release_after):
        print(verdict.marker())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
