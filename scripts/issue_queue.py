#!/usr/bin/env python3
"""The implementer's queue — ONE implementation, read by both bots (issue #179).

`issue-bot.yml`'s `pick` job chooses ONE issue per sweep: the OLDEST open
`data-gap-analysis` issue that has no implementer yet (no `ci/data-gap-<n>-*`
branch and no open PR from one). The issue reviewer must never refine an issue
inside a window around an implementer start, and the implementer's `pick` must
skip an issue the reviewer is working on — so BOTH bots read the SAME rule from
this ONE script rather than keeping two copies of it in shell and Python
(AGENTS.md rule 6d: one path, no second implementation of the same stage).

What it prints (one line per candidate, in pick order — oldest first):

    issue=<n> position=<i> has_implementer=<0|1> last_implementer_activity=<ISO8601Z|none>
    window=<open|closed>
    reason=<run-in-flight|implementer-recent|next-sweep|reviewer-working|closed>
    started=<0|1> reply_recent=<0|1> review_recent=<0|1> impl_skip=<0|1>

  * `position` — 0-based index in the pick order. The sweep takes ONE issue per
    hour and always the oldest, so `position` IS hours-until-start, which is what
    makes REVIEW_GAP_HOURS measurable as the 3 h *before* a start.
  * `last_implementer_activity` — the newest of: a start comment
    (`<!-- issue-bot-start: <ISO8601Z> -->`, posted by `issue-bot.yml` before it
    implements), its outcome comment ("issue-bot ran for this issue", posted on
    every attempt, `if: always()`), the branch's newest commit, and the PR's
    `createdAt`/`updatedAt`.
  * `window` — `open` while the reviewer must not touch the issue's body:
    an implementer run is in flight (or its start comment is fresh — the comment
    is posted BEFORE `make implement-issue`, so it covers the whole run),
    implementer activity is younger than the gap, or the issue is within the
    next `gap` sweeps. `reason` says which.
  * `started` — an implementer has actually STARTED (as opposed to the issue
    merely being next in line): that is the case where the reviewer posts its
    one bounded reply instead of staying silent.
  * `reply_recent` — the reviewer already replied in this window (the
    `<!-- issue-review: window … -->` marker): one reply per window, never one
    per hour.
  * `review_recent` — the reviewer touched this issue within the gap: its own
    cooldown, so the same issue is not re-refined every hour.
  * `verdict` / `verdict_since` / `verdict_fresh` — the reviewer's VERDICT label
    (issue #200) and whether it is still fresh. A label carries no timestamp, so
    freshness comes from the newest reviewer marker comment on the issue: a
    verdict younger than VERDICT_TTL_HOURS (24) HOLDS the implementer
    (`impl_skip=1`, `reason=verdict-fresh`); an older one — e.g. a label left by
    a cancelled run — releases it (which is why the label alone was advisory
    before). With no reviewer marker at all the label is only reported.
  * ``decided`` — the implementer already SAID what this issue is (issue #210):
    ``agent:refined`` or ``agent:closed``, applied by ``scripts/issue_verdict.py``.
    A decided issue is held with no TTL — a human clearing the label releases it —
    because a verdict is a deliberate statement, not a clock.

`--skip-note` posts the ONE comment that says the implementer skipped an issue
because of a fresh verdict — idempotent per review round (the marker carries
`since=<the reviewer's timestamp>`, so a second sweep in the same round says
nothing), because the reviewer's judgement must be visible on the issue rather
than only in a bot's log.

Usage:
    python3 scripts/issue_queue.py [--repo OWNER/NAME] [--now ISO8601] [--gap-hours 3]
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import subprocess
import sys
from pathlib import Path

BRANCH_PREFIX = "ci/data-gap-"
# Every bot marker is defined ONCE in scripts/bot_markers.py (issue #197): this module READS the
# shapes it does not own, so a renamed or reworded marker can never leave this reader silently
# concluding "no implementer has started" (rule 6d). The sibling is found the same way
# scripts/issue_review.py finds this module.
sys.path.insert(0, str(Path(__file__).resolve().parent))

import bot_markers as bm  # noqa: E402
from env_int import env_int  # noqa: E402  (empty means missing — issue #487)

#: The implementer's OUTCOME comment is still matched by prose (issue #197 flags it). It is pinned
#: to the writer's sentence by `tests/test_bot_markers.py`, so a copy edit turns CI red instead of
#: silently stopping this reader's 3 h clock.
OUTCOME_TEXT = "issue-bot ran for this issue"
REVIEW_LABEL = "review-in-progress"
# The reviewer's VERDICT labels (issue #200): it looks at an issue and says what
# it is. The implementer must act on that judgement before it implements — an
# issue the reviewer called "not ready" is not implemented, and the sweep says so
# on the issue instead. `obsolete` / `duplicate` / `already-fixed` are expected to
# be closed by the reviewer WITH evidence; the hold is the safety net for the case
# where a verdict label outlives the run that set it.
VERDICT_LABELS = ("needs-refinement", "obsolete", "duplicate", "already-fixed")
# The implementer's own triage outcome (issue #210): once it has SAID what an
# issue is — refined, or closed with evidence — the sweep must not re-litigate the
# verdict every hour. `scripts/issue_verdict.py` applies one of these; the pick
# skips the issue while it carries one. Decided is a HOLD with no TTL on purpose:
# a human clearing the label is the release, because the verdict is a person's or
# the bot's deliberate statement, not a clock.
DECIDED_LABELS = ("agent:refined", "agent:closed")
#: The skip note's `since=` ATTRIBUTE (not a marker name): the reviewer's verdict timestamp,
#: which decides whether the note is idempotent for this review round. The marker itself is read
#: through the registry.
SKIP_SINCE_RE = re.compile(r"since=(" + bm.TS + r")")
#: How many held issues ONE sweep notes (issue #204): every fresh-verdict hold is
#: announced — the note exists to answer "why is nobody working on this?" — but a
#: pathological backlog must not turn a sweep into a comment storm. The remainder is
#: reported and noted by the next sweep.
MAX_SKIP_NOTES = 10


#: The CEILING on a verdict hold (issue #203). `VERDICT_TTL_HOURS` (24) makes a
#: verdict stale, but a reviewer that keeps re-dating it — a fresh marker every few
#: hours — keeps it fresh for ever, because freshness is measured from the NEWEST
#: marker. A hold older than this ceiling (measured from the OLDEST marker of the
#: unbroken chain) releases the issue: a verdict must not stall the queue
#: indefinitely, whatever keeps re-writing it.
VERDICT_MAX_HOLD_HOURS = 24 * 7


def verdict_chain_start(timestamps: list[dt.datetime], ttl_hours: int) -> dt.datetime | None:
    """The oldest marker of the unbroken reviewer chain ending at the newest.

    Two consecutive markers belong to one chain while they are less than `ttl_hours`
    apart, so "how long has this verdict been held" is the age of the chain's first
    link — not the age of the newest one, which any re-review resets.
    """
    ts = sorted((t for t in timestamps if t), reverse=True)
    if not ts:
        return None
    start = ts[0]
    window = dt.timedelta(hours=ttl_hours)
    for newer, older in zip(ts, ts[1:]):
        if (newer - older) < window:
            start = older
        else:
            break
    return start


def _gh(args: list[str], check: bool = True) -> str:
    """Run `gh` and return stdout. A failure is loud unless `check=False`."""
    proc = subprocess.run(["gh", *args], capture_output=True, text=True)
    if proc.returncode != 0:
        if check:
            raise SystemExit(f"[issue-queue] gh {' '.join(args)} failed: {proc.stderr.strip()}")
        return ""
    return proc.stdout


def parse_ts(value: str | None) -> dt.datetime | None:
    """Parse a GitHub ISO timestamp into an aware UTC datetime."""
    if not value:
        return None
    text = str(value).strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = dt.datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=dt.timezone.utc)
    return parsed.astimezone(dt.timezone.utc)


def now_utc(value: str | None = None) -> dt.datetime:
    """The clock: injected (`--now` / `ISSUE_REVIEW_NOW`), never the wall clock in tests."""
    injected = value or os.environ.get("ISSUE_REVIEW_NOW")
    parsed = parse_ts(injected)
    return parsed if parsed else dt.datetime.now(dt.timezone.utc)


def current_run() -> str:
    """This workflow run's id (env), or `local` for a hand-run."""
    return os.environ.get("GITHUB_RUN_ID") or "local"


def resolve_repo(explicit: str | None = None) -> str:
    if explicit:
        return explicit
    env = os.environ.get("GITHUB_REPOSITORY") or os.environ.get("REPO")
    if env:
        return env
    out = _gh(["repo", "view", "--json", "nameWithOwner", "-q", ".nameWithOwner"], check=False)
    if not out.strip():
        raise SystemExit("[issue-queue] no --repo, no GITHUB_REPOSITORY and no gh repo view result")
    return out.strip()


def _issues(repo: str, label: str) -> list[dict]:
    out = _gh(["issue", "list", "--repo", repo, "--label", label, "--state", "open",
               "--limit", "100", "--json", "number,createdAt,labels"])
    items = json.loads(out or "[]")
    return sorted(items, key=lambda i: i.get("createdAt") or "")


def _branches(repo: str) -> set[str]:
    out = _gh(["api", f"repos/{repo}/git/matching-refs/heads/{BRANCH_PREFIX}"], check=False)
    try:
        refs = json.loads(out or "[]")
    except json.JSONDecodeError:
        refs = []
    return {r["ref"].rsplit("/", 1)[-1] for r in refs if isinstance(r, dict) and "ref" in r}


def _pulls(repo: str) -> list[dict]:
    out = _gh(["pr", "list", "--repo", repo, "--state", "all", "--limit", "100",
               "--json", "number,headRefName,state,createdAt,updatedAt"], check=False)
    try:
        return json.loads(out or "[]")
    except json.JSONDecodeError:
        return []


def _comments(repo: str, number: int) -> list[dict]:
    out = _gh(["api", f"repos/{repo}/issues/{number}/comments?per_page=100",
               "--jq", "[.[] | {createdAt, body}]"], check=False)
    try:
        return json.loads(out or "[]")
    except json.JSONDecodeError:
        return []


def _branch_commit_ts(repo: str, branch: str) -> dt.datetime | None:
    out = _gh(["api", f"repos/{repo}/commits/{branch}", "--jq", ".commit.committer.date"], check=False)
    return parse_ts(out)


def newest(timestamps: list[dt.datetime | None]) -> dt.datetime | None:
    present = [t for t in timestamps if t is not None]
    return max(present) if present else None


def marker_run_id(body: str) -> str | None:
    """The run that wrote a reviewer marker (a run must not block itself)."""
    for m in bm.parse_markers(body or ""):
        if m.get("run"):
            return m["run"]
    return None


def build(repo: str, label: str, gap_hours: int, now: dt.datetime,
          run: str | None = None, verdict_ttl_hours: int = 24,
          max_hold_hours: int = VERDICT_MAX_HOLD_HOURS) -> list[dict]:
    """Every review candidate, in pick order, with its implementer window.

    `run` is THIS run's id: a reviewer marker this same run wrote is not a
    cooldown against itself (the mark is written before the guard re-checks —
    without this, a run would block its own write).
    """
    refs = _branches(repo)
    pulls = _pulls(repo)
    rows: list[dict] = []
    position = 0

    for issue in _issues(repo, label):
        number = int(issue["number"])
        labels = {l.get("name") for l in issue.get("labels") or []}
        branch = None
        for name in sorted(refs):
            if name.startswith(f"{BRANCH_PREFIX}{number}-"):
                branch = name
                break
        pull = next((p for p in pulls if p.get("headRefName") == branch), None) if branch else None
        has_implementer = bool(branch) or bool(pull and pull.get("state") == "open")
        if has_implementer:
            continue

        comments = _comments(repo, number)
        start_ts = newest([parse_ts(c.get("createdAt")) for c in comments
                           if bm.read_marker(c.get("body") or "", "issue-bot", "start")])
        start_marker_ts = newest([bm.ts_of(c.get("body") or "", "issue-bot", "start")
                                  for c in comments])
        outcome_ts = newest([parse_ts(c.get("createdAt")) for c in comments
                             if OUTCOME_TEXT in (c.get("body") or "")])
        # A reviewer's window is live work: BOTH its start marker and its window marker count
        # (the pre-#197 substring reader matched both by accident — `<!-- issue-review:` is a
        # prefix of `<!-- issue-review: window`). Expressed explicitly here, never by accident.
        def _review_marker(body: str) -> bool:
            return bool(bm.read_marker(body, "issue-review-bot", "start")
                        or bm.read_marker(body, "issue-review-bot", "window"))

        review_markers = [parse_ts(c.get("createdAt")) for c in comments
                          if _review_marker(c.get("body") or "")
                          and marker_run_id(c.get("body") or "") != run]
        review_ts = newest(review_markers)
        reply_ts = newest([parse_ts(c.get("createdAt")) for c in comments
                           if bm.read_marker(c.get("body") or "", "issue-review-bot", "window")
                           and marker_run_id(c.get("body") or "") != run])
        reviewer_label = REVIEW_LABEL in labels  # advisory; reported, never a hold
        branch_ts = _branch_commit_ts(repo, branch) if branch else None
        pull_ts = newest([parse_ts((pull or {}).get("createdAt")), parse_ts((pull or {}).get("updatedAt"))])
        activity = newest([start_ts, start_marker_ts, outcome_ts, branch_ts, pull_ts])

        def fresh(ts: dt.datetime | None) -> bool:
            return bool(ts) and (now - ts) < dt.timedelta(hours=gap_hours)

        # The implementer's START COMMENT is the ONLY in-flight signal (issue #193).
        # It is posted before `make implement-issue` reads the body (AGENTS.md rule 6j),
        # so it covers the whole run. The old backstop scanned `gh run list` for a
        # queued/in_progress run whose `displayTitle` contained `#<n>` — a field that
        # cannot identify an issue: a scheduled run's displayTitle is `issue-bot`, and
        # an `issues` run's is the issue TITLE (which may carry no number at all).
        # Measured on this repo: 12 runs, 10 of them `issues` with a title, 2 `schedule`
        # with `issue-bot` — so the backstop could never fire for a sweep and only fired
        # for a run the start comment already described. A signal that is never true is
        # not a backstop; it is coverage that is not there.
        started_recently = fresh(start_ts) or fresh(start_marker_ts)
        recent_activity = fresh(activity)
        # The reviewer's own window: a marker from ANOTHER run inside the gap.
        # The `review-in-progress` label alone is NOT enough — labels carry no
        # timestamp, so a label left by a cancelled run would stall the queue for
        # ever; the timestamped marker is what proves a review is live (the
        # workflow removes the label at the end of every run, `always()`).
        reviewer_recent = fresh(review_ts)
        # The reviewer's VERDICT (issue #200): a label carries no timestamp, so
        # freshness comes from the newest reviewer marker comment on this issue —
        # and an older verdict (a label left by a cancelled run) releases the
        # issue instead of stalling it for ever. Nothing here reads or writes a
        # label: the reviewer (or a human) owns those.
        decided_label = next((name for name in DECIDED_LABELS if name in labels), None)
        verdict_label = next((name for name in VERDICT_LABELS if name in labels), None)
        verdict_ts = newest([review_ts, reply_ts])
        # A DECIDED hold (`agent:refined` / `agent:closed`, applied by the implementer's
        # own verdict) carries no timestamp in the label, so it is dated from the verdict
        # MARKER — the comment that applied it (issue #449). Without this the queue held
        # the whole data-gap backlog for ever and every sweep reported a green
        # "backlog empty"; the decision stays a HUMAN one, but it must be announced.
        decided_ts = newest([bm.ts_of(c.get("body") or "", "issue-bot", "verdict")
                             for c in comments])
        # How long the CURRENT verdict has been held (issue #203): the unbroken chain
        # of reviewer markers, not the newest one — a re-review re-dates freshness but
        # does not restart the hold.
        verdict_chain = verdict_chain_start(review_markers, verdict_ttl_hours)
        verdict_held_hours = (int((now - verdict_chain).total_seconds() // 3600)
                              if verdict_chain else None)
        verdict_expired = (bool(verdict_label) and verdict_held_hours is not None
                           and verdict_held_hours >= max_hold_hours)
        verdict_fresh = (bool(verdict_label) and bool(verdict_ts)
                         and (now - verdict_ts) < dt.timedelta(hours=verdict_ttl_hours)
                         and not verdict_expired)
        impl_skip = reviewer_recent or verdict_fresh or bool(decided_label)
        next_sweep = (not impl_skip) and position < gap_hours
        if verdict_expired:
            reason = "verdict-expired"
        elif decided_label:
            reason = f"decided:{decided_label}"
        elif verdict_fresh:
            reason = "verdict-fresh"
        elif impl_skip:
            reason = "reviewer-working"
        elif started_recently:
            reason = "run-in-flight"
        elif recent_activity:
            reason = "implementer-recent"
        elif next_sweep:
            reason = "next-sweep"
        else:
            reason = "closed"

        label_row = reviewer_label
        row_position = -1 if impl_skip else position
        rows.append({
            "issue": number,
            "position": row_position,
            "has_implementer": 0,
            "last_implementer_activity": activity.strftime("%Y-%m-%dT%H:%M:%SZ") if activity else "none",
            "window": "closed" if reason == "closed" else "open",
            "reason": reason,
            "started": 1 if started_recently else 0,
            "reply_recent": 1 if fresh(reply_ts) else 0,
            "review_recent": 1 if reviewer_recent else 0,
            "impl_skip": 1 if impl_skip else 0,
            "reviewer_label": 1 if label_row else 0,
            "verdict": verdict_label or "-",
            "verdict_since": verdict_ts.strftime("%Y-%m-%dT%H:%M:%SZ") if verdict_ts and verdict_label else "none",
            "verdict_fresh": 1 if verdict_fresh else 0,
            "verdict_held_hours": verdict_held_hours if verdict_held_hours is not None else -1,
            "verdict_held_since": (verdict_chain.strftime("%Y-%m-%dT%H:%M:%SZ")
                                   if verdict_chain and verdict_label else "none"),
            "verdict_expired": 1 if verdict_expired else 0,
            "decided": decided_label or "-",
            "decided_since": (decided_ts.strftime("%Y-%m-%dT%H:%M:%SZ")
                              if decided_ts and decided_label else "none"),
            "branch": branch or "",
        })
        if not impl_skip:
            position += 1
    return rows


def render(rows: list[dict]) -> str:
    lines = []
    for r in rows:
        lines.append(
            f"issue={r['issue']} position={r['position']} has_implementer={r['has_implementer']} "
            f"last_implementer_activity={r['last_implementer_activity']} window={r['window']} "
            f"reason={r['reason']} started={r['started']} reply_recent={r['reply_recent']} "
            f"review_recent={r['review_recent']} impl_skip={r['impl_skip']} "
            f"verdict={r['verdict']} verdict_since={r['verdict_since']} "
            f"verdict_fresh={r['verdict_fresh']} "
            f"verdict_held_since={r['verdict_held_since']} "
            f"verdict_held_hours={r['verdict_held_hours']} "
            f"verdict_expired={r['verdict_expired']} decided={r['decided']} "
            f"decided_since={r['decided_since']}"
        )
    return "\n".join(lines)


def post_skip_note(repo: str, label: str, gap_hours: int, verdict_ttl_hours: int,
                   now: dt.datetime, run: str | None) -> int:
    """Say on EVERY issue the implementer skipped — a fresh VERDICT or a DECISION.

    One comment per issue per review round: the marker carries
    `since=<the reviewer's newest timestamp>`, so a later sweep in the same round
    finds it and says nothing (the same idempotence the filing path uses for its
    dedup markers). A comment, never a label: the verdict belongs to the reviewer.

    It used to note `held[0]` — ONE issue — so with two fresh verdicts the second
    stayed silent until the first released, which is exactly the "why is nobody
    working on this?" the note exists to answer (issue #204). The walk is bounded
    (MAX_SKIP_NOTES) so a pathological backlog cannot turn one sweep into a
    comment storm; the remainder is reported for the next sweep.
    """
    rows = build(repo, label, gap_hours, now, run, verdict_ttl_hours)
    # TWO holds are announced, because both park an issue the sweep will skip (issue #449):
    # the reviewer's fresh VERDICT (a label WITH a live timestamp), and the implementer's
    # own DECISION (`agent:refined` / `agent:closed`) — which the owner has ruled must stay
    # a HUMAN's call, so it must never be silent. The decided hold used to print nothing at
    # all: `held` only ever selected `verdict_fresh` rows, so the sweep said
    # "no fresh verdict holds the queue — nothing to note" while four issues sat parked.
    held = [(r, "verdict") for r in sorted((r for r in rows if r["verdict_fresh"] == 1),
                                          key=lambda r: r["issue"])]
    held += [(r, "decided") for r in sorted((r for r in rows if r["decided"] != "-"),
                                            key=lambda r: r["issue"])]
    if not held:
        print("[issue-queue] nothing holds the queue — no note to post")
        return 0

    posted, skipped, batch = 0, 0, held[:MAX_SKIP_NOTES]
    for row, kind in batch:
        number = row["issue"]
        since = row["verdict_since"] if kind == "verdict" else row["decided_since"]
        already = False
        for comment in _comments(repo, number):
            body = comment.get("body") or ""
            found = SKIP_SINCE_RE.search(body)
            if (bm.read_marker(body, "issue-bot", "skip") and found
                    and found.group(1).rstrip("Z") == since.rstrip("Z")):
                already = True
                break
        if already:
            print(f"[issue-queue] #{number} already noted for verdict_since={since} — no duplicate comment")
            skipped += 1
            continue

        if kind == "verdict":
            label_text = row["verdict"]
            lines = [
                f"**Not picked by the implementer: the reviewer holds this issue "
                f"(`{label_text}`).**",
                "",
                f"- verdict: `{label_text}` — the issue reviewer judged this issue not "
                f"ready to implement",
                f"- since: {since} (the reviewer's newest marker on this issue; a verdict is "
                f"fresh for {verdict_ttl_hours} h)",
                "",
                "The hourly sweep will take this issue again once the verdict is stale, or as",
                "soon as the reviewer (or a human) clears the label. Nothing was implemented.",
            ]
        else:
            label_text = row["decided"]
            lines = [
                f"**Not picked by the implementer: this issue already carries a decision "
                f"(`{label_text}`) — it needs a HUMAN, not another sweep.**",
                "",
                f"- label: `{label_text}` — the implementer triaged this issue and applied its "
                f"own verdict, so it will not be implemented as it stands",
                f"- since: {since} (the verdict marker that applied it; the label itself "
                f"carries no timestamp, which is why the queue dates the hold from the marker)",
                "",
                "This hold has NO expiry: a label cannot prove how old it is, so the queue will "
                "never release it on its own. To move it: refine the issue and remove "
                f"`{label_text}`, or close it. Nothing was implemented.",
            ]
        text = "\n".join([
            f"<!-- {bm.marker_name('issue-bot', 'skip')}: {now.strftime('%Y-%m-%dT%H:%M:%SZ')} "
            f"verdict={label_text} since={since} -->",
            *lines,
        ])
        _gh(["issue", "comment", str(number), "--repo", repo, "--body", text])
        print(f"[issue-queue] #{number}: skip note posted ({kind}={label_text} since={since})")
        posted += 1

    if len(held) > len(batch):
        print(f"[issue-queue] {len(held) - len(batch)} more held issue(s) not noted in this "
              f"sweep (MAX_SKIP_NOTES={MAX_SKIP_NOTES}) — the next sweep notes them")
    print(f"[issue-queue] skip notes: {posted} posted, {skipped} already noted "
          f"({sum(1 for r, k in held if k == 'verdict')} held by a fresh verdict, "
          f"{sum(1 for r, k in held if k == 'decided')} by a decision)")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="The implementer's queue, for both bots (issue #179)")
    ap.add_argument("--repo", default=None)
    ap.add_argument("--label", default="data-gap-analysis")
    ap.add_argument("--gap-hours", type=int, default=env_int("REVIEW_GAP_HOURS", 3))
    ap.add_argument("--verdict-ttl-hours", type=int,
                    default=env_int("VERDICT_TTL_HOURS", 24))
    ap.add_argument("--verdict-max-hold-hours", type=int,
                    default=env_int("VERDICT_MAX_HOLD_HOURS",
                                    VERDICT_MAX_HOLD_HOURS),
                    help="how long a verdict may be held in total, across re-reviews (issue #203)")
    ap.add_argument("--skip-note", action="store_true",
                    help="post the ONE 'skipped: the reviewer holds this issue' comment (issue #200)")
    ap.add_argument("--now", default=None)
    ap.add_argument("--run", default=None, help="this run's id (a run never blocks itself)")
    args = ap.parse_args(argv)

    repo = resolve_repo(args.repo)
    now = now_utc(args.now)
    run = args.run or current_run()
    if args.skip_note:
        return post_skip_note(repo, args.label, args.gap_hours, args.verdict_ttl_hours, now, run)
    rows = build(repo, args.label, args.gap_hours, now, run, args.verdict_ttl_hours,
                 args.verdict_max_hold_hours)
    text = render(rows)
    if text:
        print(text)
    for row in rows:
        if row["verdict_expired"] == 1:
            print(f"[issue-queue] #{row['issue']}: verdict `{row['verdict']}` had been held for "
                  f"{row['verdict_held_hours']} h (ceiling {args.verdict_max_hold_hours} h) — the hold "
                  f"EXPIRES and the sweep may take the issue; a reviewer that keeps re-dating it "
                  f"cannot stall the queue for ever", file=sys.stderr)
    open_windows = [r for r in rows if r["window"] == "open"]
    print(f"[issue-queue] repo={repo} now={now.strftime('%Y-%m-%dT%H:%M:%SZ')} "
          f"gap={args.gap_hours}h candidates={len(rows)} windows_open={len(open_windows)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
