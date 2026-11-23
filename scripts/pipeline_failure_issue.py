#!/usr/bin/env python3
"""Track the main CI after a failure: diagnose it from its logs and file the issue (issue #802).

The repo already alarms when a main pipeline is red (`make master-alarm`, `make sweep-alarm`) and
repairs red PRs (fix-bot's loop). What it never did is what a senior engineer does after a
failure: READ THE LOGS OF A FAILED MAIN-PIPELINE RUN, name the make target that failed, and turn
that diagnosis into a tracked issue that says how to reproduce it. Until this existed, a red
scheduled run (measured: qa-validate run 43106689969, the OpenSpec archive gate) produced an
email, not an artifact — the diagnosis was re-derived by whoever next opened the run page.

This is the filer half. It runs from `queued-alarm.yml`, which is DISPATCH-ONLY since issue #1029
(no `on.schedule` — the sweep is the owner's dispatch, never a slot GitHub owes), with the
DEFAULT `github.token` (rule 6e: the owner PAT cannot comment or open issues). For every
main-pipeline failure inside the window that is not yet
in the ledger `data/pipeline_failures.json` it:

  1. fetches the failed job's log ONCE (one retry), bounded to the tail;
  2. extracts a bounded error block — the `##[error]`, `make: *** [target]`, `FAIL ` and
     `FAILED` lines — never a raw dump;
  3. REDACTS it through the shared scrub seam (`scripts/scrub_log.redact`, rule 3f) BEFORE
     anything is written — the issue body must carry no secret in any spelling;
  4. files ONE `tech-debt` issue carrying: the run URL + id, the workflow + job + head sha, the
     EXACT `make <target>` reproduction command, the scrubbed error block, and the registered
     marker `<!-- pipeline-run-failure: <ISO8601Z> run=<id> -->` (rule 6j — one shape, in
     `scripts/bot_markers.py`), plus the declared message pattern (five sections, issue #771) so
     `make issue-message-check` parses it;
  5. appends the ledger entry (append-only, rule 3b: an entry is never rewritten or removed).

Dedup is the ledger (run id) plus a scan of issues (open OR closed) carrying the marker: one run
files once, ever. A log fetch that fails after one retry is recorded in the ledger as UNDIAGNOSED
with the reason — loudly, never silently — and the issue body then says the log was unreadable
rather than guessing at a cause. UNDIAGNOSED is not terminal: every sweep RE-READS the log of each
still-undiagnosed row and raises it append-only (issue #969) — a row filed before a reader defect
was fixed (the #923 class: 14 rows needed a manual change each) repairs itself on the next
scheduled run — but a still-UNREADABLE row is bounded (issue #986): after MAX_REDIAGNOSE_ATTEMPTS
(3) still-unreadable sweeps it is stamped TERMINAL `log_expired` (loud, once, and excluded from the
pending set) so a run whose log aged out of Actions retention drains the queue instead of printing
retry noise for ever. This script never fixes anything and never merges anything
(rule 6g: analysis files, a separate reviewed change fixes).

A MERGED FIX PR must RAISE its row (issue #1099): a separate stamp pass reads every unraised
row's issue close link — GitHub's OWN closing-keyword record (`closedByPullRequestsReferences`),
never a text guess — and when the issue is CLOSED by a MERGED PR whose diff carries a `tests/`
guard, raises `fix_pr` + `guard` onto the row. Append-only (rule 3b): keys are ADDED, a recorded
`guard` is never overwritten, and the raise rides the same ledger-PR landing as the filer's
append. An OPEN issue, an unmerged closing PR, a CLOSED issue closed with no closing PR and a
guardless merged close are each REPORTED loudly, never stamped: the pass names the landed fix, it
never launders the §6r requirement away. A failed read is loud per row and retried next sweep —
never the sweep's own failure.

The ATTRIBUTION pass (issue #1053) is the shape that pass cannot reach. Measured on the fetched
tip: the rows for runs 42976201014 / 42977708147 / 43047130543 (issues #826/#827/#828) carry a
re-diagnosed error block yet `fix_pr: null`, because their issues are OPEN and held by a verdict
label while the fix that actually landed was a DIFFERENT merged PR. `--attribute-report` prints
every diagnosed row that names no fix PR, with the reason read from GitHub (never a guess) and the
exact remedy command; `--attribute` raises ONE such row when a claim proves itself — the row exists
and is diagnosed (not `log_expired`, not still-undiagnosed), the PR is MERGED on GitHub's own
`mergedAt`, the guard is a `tests/test_*.py` module `make test` collects AND tied to that fix (its
diff, or the row's own recorded guard), a named `::test` exists in it, and the EVIDENCE passes the
issue-verdict evidence rule while naming something the fix touched. Every refusal is exit 2 with
nothing written; a row already naming a DIFFERENT fix PR is a refusal, and the same landed-fix
annotation (the registered `pipeline-ledger-stamp` marker) is posted once on the issue.

Exit: 0 report-only (filing IS the action); 2 when the pipeline state itself could not be read
(a silent clean over an unreadable API is the defect rule 6d refuses) or an attribution claim did
not prove itself.

Run: make pipeline-failure-issue REPO=<owner>/<repo> [WINDOW_HOURS=192] [DRY=1] [LEDGER=…]
Run: make pipeline-failure-ledger-pr-body RUN_URL=… [LEDGER=…]  (the ledger PR body, no gh calls)
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import bot_markers  # noqa: E402
import pr_body  # noqa: E402  (the five-section composer + the declared marker)
from scrub_log import redact  # noqa: E402  (rule 3f's redactor — the SAME seam)

LEDGER_DEFAULT = ROOT / "data" / "pipeline_failures.json"
LABEL = "tech-debt"

#: The MAIN pipelines (the ones AGENTS.md §6b names and the §8 guard table describes). A failure
#: in one of these after a merge to master or on its schedule is the state this tracks.
#: `security-scan.yml` (issue #1185) joins the list as a DISPATCH-ONLY pipeline: it has no push
#: and no schedule, so its dispatched runs are its ONLY mode of delivery — see DISPATCH_ONLY_PIPELINES.
MAIN_PIPELINES = (
    "qa-validate.yml",
    "refresh-bot.yml",
    "issue-bot.yml",
    "issue-review-bot.yml",
    "architecture-bot.yml",
    "queued-alarm.yml",
    "security-scan.yml",
)

#: The pipelines whose only trigger is `workflow_dispatch` (issue #1185). For a cron/push pipeline
#: a collaborator's manual dispatch is that person's own act and is not tracked (the #1029
#: partition). A dispatch-ONLY pipeline has no other delivery, so a concluded-bad dispatched run
#: is an accident — it must reach the ledger and become an issue, or rule 6m's scan coverage would
#: silently expire. Dedup stays run-id keyed, so a failing pipeline cannot spam the queue.
DISPATCH_ONLY_PIPELINES = ("security-scan.yml",)

#: A failure counts when it is CONCLUDED bad (a still-running or queued run belongs to
#: queued-alarm's own alarm, not to this filer).
BAD_CONCLUSIONS = ("failure", "cancelled")

#: Bounded extraction (the issue must carry a diagnosis, not a log dump).
MAX_LOG_TAIL_BYTES = 60_000
MAX_ERROR_LINES = 40

#: A still-failing re-read is bounded (issue #986): after this many consecutive still-failing
#: re-reads a row is stamped TERMINAL `log_expired` (loud, once) and the pending queue drains.
MAX_REDIAGNOSE_ATTEMPTS = 3

#: The shapes are TWO tiers (issue #1098). A STRONG shape is something only a failure prints —
#: GitHub's own `##[error]` decoration, a `make` refusal, a traceback, a guard's `REFUSED`. A SOFT
#: shape is a word a PASSING test also prints: `make test` echoes a planted fixture's `FAIL: m1:
#: engines not ordered newest-date-first` and a `PASSED 199 | FAILED 0` verdict line from a module
#: that SUCCEEDED, and the old flat scan let 43 of those fill the whole budget.
_STRONG_SHAPES = (
    "##[error]", "make: ***", "Traceback (most recent call last)", "refused:", "REFUSED",
)
_SOFT_SHAPES = ("FAIL: ", "FAIL ", "FAILED")
_ERROR_SHAPES = _STRONG_SHAPES + _SOFT_SHAPES

#: GitHub writes each step's output as a region — `##[group]<label>` … `##[endgroup]` — and writes
#: its `##[error]` decoration INSIDE the region of the step that ended the job. The timestamp
#: prefix is present in a real Actions log and absent in a recorded fixture.
_GROUP_LINE = re.compile(r"^(?:\S+\s+)?##\[(group|endgroup)\](.*)$")
#: The line `extract_error_block` appends when the cap forced it to leave lines out (issue #1098):
#: a dropped diagnosis is announced, never silently swallowed (rule 2).
ANCHORED_DROP_NOTE = ("[filer] {kept}/{want} error-shaped line(s) of the failing step region "
                      "`{region}` are quoted; {dropped} further error-shaped line(s) printed by "
                      "OTHER step regions were not quoted to stay within "
                      "MAX_ERROR_LINES={cap} (issue #1098).")
DROP_NOTE = ("[filer] {dropped} further error-shaped line(s) were not quoted "
             "(cap MAX_ERROR_LINES={cap}); the failing step's own region was kept whole")


def _gh(*args: str, check: bool = True, stdin: str | None = None) -> subprocess.CompletedProcess:
    cmd = ["gh", *args]
    proc = subprocess.run(cmd, capture_output=True, text=True, input=stdin)
    if check and proc.returncode != 0:
        raise RuntimeError(f"gh {' '.join(args[:3])} failed ({proc.returncode}): "
                           f"{(proc.stderr or proc.stdout).strip()[:400]}")
    return proc


def _gh_json(args: list[str]) -> object:
    return json.loads(_gh(*args).stdout or "null")


# ---------------------------------------------------------------------------
# the ledger (append-only, rule 3b)
# ---------------------------------------------------------------------------

def read_ledger(path: Path) -> dict:
    if not path.exists():
        return {"failures": []}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, ValueError) as exc:
        raise RuntimeError(f"ledger {path} is unreadable: {exc}") from None
    if not isinstance(data, dict) or not isinstance(data.get("failures"), list):
        raise RuntimeError(f"ledger {path} is not {{'failures': [...]}}")
    return data


def ledger_run_ids(ledger: dict) -> set:
    return {int(e.get("run_id", 0)) for e in ledger["failures"]}


def append_ledger(path: Path, ledger: dict, entry: dict) -> None:
    """Append one entry. NEVER rewrite or remove an existing one (rule 3b)."""
    ledger["failures"].append(entry)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(ledger, indent=2) + "\n", encoding="utf-8")


# ---------------------------------------------------------------------------
# finding the failures
# ---------------------------------------------------------------------------

def main_pipeline_failures(repo: str, window_hours: int, now: dt.datetime) -> list[dict]:
    """Concluded-bad runs of the main pipelines inside the window.

    A push to master (qa-validate runs on the merge) and a scheduled delivery (the bots' crons)
    are the states this tracks; a still-queued or running run belongs to the queued alarm, and a
    collaborator's manual dispatch is that person's own act.
    """
    cutoff = now - dt.timedelta(hours=window_hours)
    found: list[dict] = []
    for wf in MAIN_PIPELINES:
        runs = _gh_json([
            "run", "list", "--repo", repo, "--workflow", wf, "--limit", "30",
            "--json", "databaseId,workflowName,name,headBranch,headSha,event,createdAt,"
                      "conclusion,status,url",
        ])
        if not isinstance(runs, list):
            raise RuntimeError(f"run list for {wf} returned {type(runs).__name__}, not a list")
        for r in runs:
            if r.get("conclusion") not in BAD_CONCLUSIONS:
                continue
            created = _ts(r.get("createdAt"))
            if created is None or created < cutoff:
                continue
            tracked = (
                (r.get("event") == "push" and r.get("headBranch") == "master")
                or r.get("event") == "schedule"
                # A dispatch-ONLY pipeline (issue #1185): its dispatched runs are its only
                # delivery, so a concluded-bad one is an accident to file, not an act to skip.
                or (r.get("event") == "workflow_dispatch" and wf in DISPATCH_ONLY_PIPELINES)
            )
            if tracked:
                found.append(r)
    return found


def _ts(value: str | None) -> dt.datetime | None:
    if not value:
        return None
    try:
        return dt.datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=dt.timezone.utc)
    except ValueError:
        try:
            return dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None


# ---------------------------------------------------------------------------
# the PR-blockage pass (issue #1164)
# ---------------------------------------------------------------------------

#: A `pull_request`-triggered main-pipeline failure is recorded only when the SAME failure shape
#: blocks at least this many OPEN pull requests. One red PR is that PR author's own noise; two is
#: a fleet-wide blockage (a stale pin, a broken image) that no single PR can fix and that the
#: master/schedule window of `main_pipeline_failures` never sees (issue #1164).
PR_BLOCK_MIN_PRS = 2

#: The PR-blockage grace is DERIVED, not guessed (issue #1176). There is no sweep interval to
#: add to: `queued-alarm.yml` has been dispatch-only since issue #1029, so a cadence term would
#: name a cadence the repository no longer owes. The basis is the MEASURED #1164 outage
#: (qa-validate runs 44651246625 / 44651246366): a stale pin blocked every open PR's `auto-merge`
#: and was repaired by a pin raise the same day. One full day of repair window is that measured
#: bound rounded up, so a fix landing the next working day still clears the gate while an
#: unfixed fleet-wide blockage reds it. `PR_BLOCK_GRACE_HOURS` is assigned FROM this window —
#: a regression test refuses a bare-literal grace with no provenance.
PR_BLOCK_REPAIR_WINDOW_HOURS = 24
PR_BLOCK_GRACE_HOURS = PR_BLOCK_REPAIR_WINDOW_HOURS

#: A weekly sweep reads at most this many `pull_request` runs' logs. The byte cap on one log
#: does not bound the NUMBER of reads: 20 open PRs all red at the same step cost 20 fetches on
#: every sweep, and a filer with no read budget becomes the thing that times out (issue #1174).
PR_BLOCK_MAX_LOG_READS = 8


def bound_pr_block_runs(runs: list[dict], cap: int = PR_BLOCK_MAX_LOG_READS) -> tuple[list[dict], int]:
    """Keep the newest `cap` runs and return how many were left for a later sweep.

    `gh run list` is newest-first, so the capped set still contains the runs most likely to
    be blocking an open PR today; skipping older ones cannot lose a NEW blockage.
    """
    if cap < 1:
        raise ValueError("PR_BLOCK_MAX_LOG_READS must be at least 1")
    return runs[:cap], max(0, len(runs) - cap)


def failure_shape(block: list[str], targets: list[str], steps: list[str]) -> str:
    """The normalised signature deciding whether two failed runs are the SAME failure.

    Run ids, SHAs, timestamps and counts differ between two PRs hitting one defect, so the shape
    keeps only the stable skeleton: the failing step names, the `make` targets the log names, and
    the error block with every run-specific token collapsed. Two runs with the same shape are one
    error class, which is what makes "the SAME failure shape on two open PRs" decidable (issue
    #1164).

    The WHOLE bounded block is digested, not its first lines (issue #1175): `block` arrives from
    `extract_error_block`, already capped at `MAX_ERROR_LINES`, so the cap bounds the digest's
    input and the shape answers "the same failure" rather than "the same opening". A prefix
    digest merged two defects that share GitHub's boilerplate (`##[error]…`, `make: *** …`)
    and differ only later — the threshold is then met by two PRs blocked by different things,
    which is the one error this pass exists to avoid.

    The digest is ORDER-SENSITIVE on purpose: the skeleton is joined in the block's own order, so
    the same lines in a different order are two shapes. A set would hide a re-ordered traceback,
    and the digest stays deliberately cheap.
    """
    skeleton: list[str] = []
    for line in block:
        s = re.sub(r"\x1b\[[0-9;]*m", "", line).strip()
        if not s:
            continue
        s = re.sub(r"\b[0-9a-f]{7,40}\b", "<sha>", s)
        s = re.sub(r"\b\d[\d,]*\b", "<n>", s)
        skeleton.append(s)
    key = "|".join([*(steps or []), *(targets or []), *skeleton])
    return hashlib.sha1(key.encode("utf-8")).hexdigest()[:12]


def open_pr_branches(repo: str) -> set:
    """The head branches of the repo's OPEN pull requests (the PRs a blockage can be said to block).

    A non-list answer (gh missing, a transport error) is an empty set: the grouping then records
    nothing rather than claiming a blockage it could not see (the same indeterminate rule the link
    check uses for 429/5xx).
    """
    out = _gh_json(["pr", "list", "--repo", repo, "--state", "open", "--limit", "100",
                    "--json", "headRefName"])
    if not isinstance(out, list):
        return set()
    return {p.get("headRefName") for p in out if p.get("headRefName")}


def pr_block_candidates(runs: list[dict], cutoff: dt.datetime, open_branches: set) -> list[dict]:
    """The runs a PR-blockage read may be spent on — the cheap filters BEFORE the cap (issue #1405).

    The log-read cap exists to bound the number of LOG FETCHES, so it must be applied to the runs
    that can actually be a blockage: concluded-bad, on a branch that is still an OPEN pull request,
    and inside the window. Bounding the raw newest-first page first spends the budget on green and
    merged runs, so a shape blocking several open PRs is never grouped the moment newer green runs
    fill the page (measured: `log budget 8 run(s); skipped 22 run(s) beyond the cap` while every red
    open-PR run sat past the cap). Every filter here is cheap; only `failed_jobs`/`job_failure`
    touch the network.
    """
    out: list[dict] = []
    for r in runs:
        if r.get("conclusion") not in BAD_CONCLUSIONS:
            continue
        if r.get("headBranch") not in open_branches:
            continue
        created = _ts(r.get("createdAt"))
        if created is None or created < cutoff:
            continue
        out.append(r)
    return out


def pr_triggered_failures(repo: str, window_hours: int, now: dt.datetime,
                          stats: dict | None = None,
                          open_branches: set | None = None) -> list[dict]:
    """Concluded-bad `pull_request` runs of the main pipelines inside the window (issue #1164).

    Each item carries its failed job, the scrubbed error block, the `make` targets the log names,
    the failing steps, the log region and the normalised `shape`. A still-running or queued run
    belongs to the queued alarm, exactly as in `main_pipeline_failures`. At most
    `PR_BLOCK_MAX_LOG_READS` runs' LOGS are read per sweep, and they are the runs that survive the
    red/open-PR/window pre-filter (issue #1405), so the cap bounds reads rather than relevance; the
    skipped count is written to `stats` so the sweep can announce it (issue #1174).
    """
    cutoff = now - dt.timedelta(hours=window_hours)
    branches = open_pr_branches(repo) if open_branches is None else open_branches
    out: list[dict] = []
    skipped = 0
    for wf in MAIN_PIPELINES:
        runs = _gh_json([
            "run", "list", "--repo", repo, "--workflow", wf, "--event", "pull_request",
            "--limit", "30", "--json",
            "databaseId,workflowName,name,headBranch,headSha,event,createdAt,"
            "conclusion,status,url",
        ])
        if not isinstance(runs, list):
            raise RuntimeError(f"run list for {wf} returned {type(runs).__name__}, not a list")
        candidates = pr_block_candidates(runs, cutoff, branches)
        candidates, wf_skipped = bound_pr_block_runs(candidates)
        skipped += wf_skipped
        for r in candidates:
            try:
                jobs = failed_jobs(repo, int(r["databaseId"]))
            except (RuntimeError, ValueError, KeyError):
                continue
            for job in jobs:
                block, region, log_error = job_failure(repo, job)
                targets = failed_make_targets(block)
                steps = failing_step_names(job)
                out.append({"run": r, "job": job, "block": block, "targets": targets,
                            "steps": steps, "region": region, "log_error": log_error,
                            "shape": failure_shape(block, targets, steps)})
    if stats is not None:
        stats["pr_block_runs_skipped"] = skipped
    return out


def job_failure(repo: str, job: dict) -> tuple[list[str], str, str | None]:
    """The scrubbed error block, the log region and a read error for ONE failed job.

    The ONE extraction view (issue #1098, rule 6d): every pass that needs a failing job's log —
    the master/schedule filer and the PR-blockage pass (#1164) — comes through this seam, so
    `fetch_log` is reached exactly once and always with the job it belongs to. A second site
    reading the log a different way is what the wiring test refuses.
    """
    block: list[str] = []
    region = ""
    log_error = None
    try:
        log_text = fetch_log(repo, job["databaseId"])
        block = extract_error_block(log_text, job=job)
        region = error_region(log_text)
    except RuntimeError as exc:
        log_error = str(exc)
    return block, region, log_error


def group_pr_blockages(items: list[dict], open_branches: set) -> list[dict]:
    """Group PR-triggered failures by shape; keep a shape blocking >= PR_BLOCK_MIN_PRS OPEN PRs.

    A run whose head branch is NOT an open PR is dropped: a merged or closed branch is no longer
    blocked, and counting it would report a blockage that has already cleared.
    """
    groups: dict[str, list[dict]] = {}
    for it in items:
        branch = it["run"].get("headBranch")
        if branch not in open_branches:
            continue
        groups.setdefault(it["shape"], []).append(it)
    out: list[dict] = []
    for shape, members in groups.items():
        branches = sorted({m["run"]["headBranch"] for m in members})
        if len(branches) >= PR_BLOCK_MIN_PRS:
            out.append({"shape": shape,
                        "members": sorted(members, key=lambda m: m["run"]["databaseId"]),
                        "branches": branches})
    return out


def record_pr_blockages(repo: str, window_hours: int, ledger: dict, ledger_path: Path,
                        dry: bool, now: dt.datetime, known: set, already: set) -> list[str]:
    """File ONE issue per PR-blocking failure shape, and append its ledger row (issue #1164).

    The shape is the dedup key: a blockage already recorded (its earliest run in `known`, or a
    run an open issue already carries a marker for, in `already`) is skipped, so a long-running
    pin files once and is then tracked by `make pipeline-failure-guard-check` instead of being
    re-filed every sweep.
    """
    lines: list[str] = []
    stats: dict = {}
    try:
        open_branches = open_pr_branches(repo)
        items = pr_triggered_failures(repo, window_hours, now, stats, open_branches)
    except RuntimeError as exc:
        return [f"pr-blockage: READ FAILED: {exc}"]
    skipped = int(stats.get("pr_block_runs_skipped", 0))
    if skipped:
        lines.append(f"pr-blockage: log budget {PR_BLOCK_MAX_LOG_READS} run(s); "
                     f"skipped {skipped} run(s) beyond the cap")
    for group in group_pr_blockages(items, open_branches):
        first = group["members"][0]
        rid = int(first["run"]["databaseId"])
        if rid in known or rid in already:
            lines.append(f"skip pr-blockage shape {group['shape']}: run {rid} already recorded")
            continue
        if dry:
            lines.append(f"WOULD FILE pr-blockage shape {group['shape']} on "
                         f"{len(group['branches'])} open PR(s): {', '.join(group['branches'])} "
                         f"(run {rid})")
            continue
        issue = file_issue(repo, first["run"], first["job"], first["block"], first["targets"],
                           first["log_error"], now, steps=first["steps"], region=first["region"])
        append_ledger(ledger_path, ledger, {
            "run_id": rid, "workflow": first["run"].get("workflowName"),
            "job": first["job"].get("name"), "head_sha": first["run"].get("headSha"),
            "run_url": first["run"].get("url"), "created_utc": first["run"].get("createdAt"),
            "filed_utc": now.isoformat(), "targets": first["targets"],
            "issue_number": issue["number"], "issue_url": issue["url"],
            "fix_pr": None, "guard": None, "undiagnosed": first["log_error"],
            "failing_steps": first["steps"], "error_region": first["region"],
            "error_excerpt": redact("\n".join(first["block"]))[0] if first["block"] else None,
            # The PR-blockage half's OWN keys (rule 3b: additive — every key above is the filer's
            # existing shape, these four are ADDED).
            "trigger": "pull_request", "failure_shape": group["shape"],
            "blocked_prs": group["branches"], "pr_count": len(group["branches"]),
        })
        known.add(rid)
        lines.append(f"FILED {issue['url']} (pr-blockage shape {group['shape']}, "
                     f"{len(group['branches'])} open PR(s): {', '.join(group['branches'])})")
    return lines


def failed_jobs(repo: str, run_id: int) -> list[dict]:
    """The jobs of a run whose conclusion is bad (in job order).

    `gh run view --json jobs` names a job's id `databaseId` (not `id`) — the log endpoint
    wants that number.
    """
    data = _gh_json(["run", "view", str(run_id), "--repo", repo, "--json", "jobs"])
    jobs = (data or {}).get("jobs") if isinstance(data, dict) else None
    if not isinstance(jobs, list):
        raise RuntimeError(f"run view {run_id} returned no jobs list")
    bad = [j for j in jobs if j.get("conclusion") in BAD_CONCLUSIONS]
    for j in bad:
        if not isinstance(j.get("databaseId"), int):
            raise RuntimeError(f"run view {run_id}: job {j.get('name')!r} has no databaseId")
    return bad


_ESCAPE_CSI = re.compile(r"\x1b\[[0-9;?]*[ -/]*[@-~]")
_ESCAPE_OSC = re.compile(r"\x1b\][^\x07\x1b]*(?:\x07|\x1b\\)")


def strip_terminal_escapes(text: str) -> str:
    """Remove every terminal escape SEQUENCE (CSI, OSC, lone ESC) — issue #923.

    GitHub Actions wraps its `##[error]` decoration in ANSI color codes, so a plain
    `gh api …/logs` answer is full of them (gh refuses such logs outright). Stripping runs
    BEFORE extraction and scrubbing so escape bytes can never reach an issue body, while
    ordinary text — a bare `[31m` with no ESC, log prose — is left exactly as written.
    """
    text = _ESCAPE_OSC.sub("", text)
    text = _ESCAPE_CSI.sub("", text)
    return text.replace("\x1b", "")


def fetch_log(repo: str, job_id: int) -> str:
    """The job log, bounded to its tail; ONE retry, then a loud UNDIAGNOSED reason (never a
    silent empty log — an empty body would read as 'the run failed cleanly').

    The retry is not a repeat: it carries gh's OWN suggested `--allow-escape-sequences` (issue
    #923, measured: 12 issues #822–#833 filed UNDIAGNOSED because gh refuses any log containing
    terminal escape sequences — exactly what Actions' colored `##[error]` writes). Whatever
    arrives is stripped of escape sequences before the tail-bound, the extraction and the scrub.
    """
    last_err = ""
    for attempt in (1, 2):
        args = ["api", f"repos/{repo}/actions/jobs/{job_id}/logs"]
        if attempt == 2:
            args.append("--allow-escape-sequences")
        proc = _gh(*args, check=False)
        if proc.returncode == 0 and proc.stdout.strip():
            text = strip_terminal_escapes(proc.stdout)
            if len(text.encode("utf-8")) > MAX_LOG_TAIL_BYTES:
                text = text.encode("utf-8")[-MAX_LOG_TAIL_BYTES:].decode("utf-8", "replace")
                text = "[log bounded to its tail]\n" + text
            return text
        last_err = (proc.stderr or proc.stdout or "empty log").strip()[:300]
    raise RuntimeError(f"log fetch for job {job_id} failed twice: {last_err}")


def log_regions(log_text: str) -> list[dict]:
    """The log split into GitHub's per-step regions: `{"label": str, "lines": [(idx, line)]}`.

    Measured on job 132845951479 (qa-validate run 43725338063): the region headed
    `##[group]Run make openspec-check` holds `[openspec-index] FAIL OPENSPEC.md is stale or missing
    (2 active, 305 archived on disk)`, `make: *** [Makefile:367: openspec-index-check] Error 1` and
    GitHub's own `##[error]Process completed with exit code 2.` — the REGION boundary, not a keyword
    scan, is what tells a reader which step died. Text before the first marker (and a log carrying
    no marker at all) is one unlabeled region with label `""`; a `##[group]`/`##[endgroup]` line is
    structure and is never quoted as content.
    """
    regions: list[dict] = [{"label": "", "lines": []}]
    current = regions[0]
    for idx, raw in enumerate(log_text.splitlines()):
        m = _GROUP_LINE.match(raw)
        if m:
            if m.group(1) == "group":
                current = {"label": (m.group(2) or "").strip(), "lines": []}
                regions.append(current)
            continue
        current["lines"].append((idx, raw))
    return [r for r in regions if r["lines"] or r["label"]]


def failing_region(regions: list[dict]) -> dict | None:
    """The LAST region carrying GitHub's `##[error]` decoration — the step that ended the job.

    GitHub prints that decoration for the step it let the job fail on, inside that step's own
    region, so the anchor is GitHub's assertion and not an inference from a line of test chatter.
    `None` when the log carries no such decoration (a truncated log, a cancelled job): the caller
    has no region to prefer and extraction falls back to shape alone rather than inventing a region.
    """
    found: dict | None = None
    for region in regions:
        if any(_STRONG_SHAPES[0] in raw for _idx, raw in region["lines"]):
            found = region
    return found


def failing_step_names(job: dict) -> list[str]:
    """GitHub's OWN names for this job's steps that concluded bad — never inferred.

    `gh run view --json jobs` carries `steps: [{name, conclusion}]`: a step GitHub marked
    `failure` or `cancelled` is named, `success`/`skipped` is not. An empty list when the payload
    carries no steps — the log region then stands alone, and the issue says so instead of guessing
    (issue #1098).
    """
    steps = job.get("steps")
    if not isinstance(steps, list):
        return []
    return [s["name"] for s in steps
            if isinstance(s, dict) and s.get("conclusion") in BAD_CONCLUSIONS and s.get("name")]


def error_region(log_text: str) -> str:
    """The label of the log region the diagnosis came from (`""` when the log names none).

    The same `log_regions` + `failing_region` pair `extract_error_block` uses, so the region named
    in the issue and in the ledger is the region the quoted lines were actually taken from — one
    implementation, never a second view of the same log (rule 6d).
    """
    fail = failing_region(log_regions(log_text))
    return fail["label"] if fail else ""


def extract_error_block(log_text: str, job: dict | None = None) -> list[str]:
    """The bounded diagnosis: every error-shaped line, in order, capped — anchored on the STEP that
    ended the job (issue #1098).

    The budget is filled in TIERS: (0) a strong shape inside the failing region, (1) a soft shape
    there, (2) a strong shape anywhere else, (3) a soft shape anywhere else — which is what a
    PASSING module prints (`FAIL: m1: engines not ordered newest-date-first`, `PASSED 199 | FAILED
    0`), quoted only when room is left. Selection is by tier; presentation is log order; lines are
    de-duped and each capped to 500 characters. When the cap forces lines out the block ENDS with a
    `DROP_NOTE` line naming how many were left out, so a truncated diagnosis is loud (rule 2).
    Measured before this existed: 43 chatter lines consumed the whole 40-line budget on job
    132845951479 and the `openspec-index-check` refusal — hits #43-#45 — was never quoted, so the
    filed issue carried no reproduction command.

    `job` is accepted so a caller that also wants `failing_step_names(job)` extracts in the same
    call; the extraction never depends on it and the one-argument call is unchanged. An empty block
    still means "no error-shaped line at all" — the caller files UNDIAGNOSED rather than quoting an
    arbitrary window.
    """
    regions = log_regions(log_text)
    fail = failing_region(regions)
    candidates: list[tuple[int, int, str]] = []
    for region in regions:
        in_failure = fail is not None and region is fail
        for idx, raw in region["lines"]:
            line = raw.rstrip()[:500]
            strong = any(shape in line for shape in _STRONG_SHAPES)
            soft = any(shape in line for shape in _SOFT_SHAPES)
            if not (strong or soft):
                continue
            candidates.append(((0 if strong else 1) if in_failure
                               else (2 if strong else 3), idx, line))
    if not candidates:
        return []
    chatter = [c for c in candidates if c[0] == 3]
    unique_all = len({c[2] for c in candidates})
    in_fail_lines = {c[2] for c in candidates if c[0] in (0, 1)}
    limit = MAX_ERROR_LINES - 1 if unique_all > MAX_ERROR_LINES else MAX_ERROR_LINES
    seen: set[str] = set()
    chosen: list[tuple[int, str]] = []
    for tier in (0, 1, 2):
        for cand_tier, idx, line in candidates:
            if cand_tier != tier or line in seen:
                continue
            if len(chosen) >= limit:
                break
            seen.add(line)
            chosen.append((idx, line))
    for _cand_tier, idx, line in chatter:
        if len(chosen) >= limit or line in seen:
            continue
        seen.add(line)
        chosen.append((idx, line))
    chosen.sort(key=lambda c: c[0])
    out = [line for _idx, line in chosen]
    dropped = unique_all - len(seen)
    if dropped > 0:
        if fail is not None:
            kept = len(in_fail_lines & seen)
            out.append(ANCHORED_DROP_NOTE.format(kept=kept, want=len(in_fail_lines),
                                                 region=fail["label"], dropped=dropped,
                                                 cap=MAX_ERROR_LINES))
        else:
            out.append(DROP_NOTE.format(dropped=dropped, cap=MAX_ERROR_LINES))
    return out


_MAKEFILE_LINE_TARGET = re.compile(r"^[^\s:]+:\d+:\s*(\S.*)$")


def normalize_target(name: str) -> str:
    """One spelling of a failing target: the bare Makefile target name (issue #1054).

    A log's `make: *** [Makefile:1384: sweep-alarm]` line carries the Makefile's own
    `file:<line>: ` decoration inside the brackets; stored raw it reads as a line
    reference, not a reproduction command, and a `make Makefile:1384: sweep-alarm`
    command the filer quotes is not runnable. Sibling rows (issues #820-#829) already
    carry the bare name; this normaliser makes the ledger's `targets` uniformly the
    parseable `make <target>` for every reader and every pass.
    """
    stripped = (name or "").strip()
    m = _MAKEFILE_LINE_TARGET.match(stripped)
    return (m.group(1).strip() if m else stripped)


def normalize_ledger_targets(ledger: dict) -> int:
    """Normalise every stored row's targets in place; returns how many rows changed."""
    changed = 0
    for entry in ledger.get("failures", []):
        old = entry.get("targets") or []
        new = []
        for t in old:
            n = normalize_target(str(t))
            if n and n not in new:
                new.append(n)
        if new != old:
            entry["targets"] = new
            changed += 1
    return changed


def failed_make_targets(block: list[str]) -> list[str]:
    """The `make <target>` names the log itself shows as the failing commands (rule 6m: a gate
    is reached through make, so the reproduction command is `make <target>`) — each one normalised
    through `normalize_target`, the `Makefile:<line>: ` form included (issue #1054)."""
    targets: list[str] = []
    for line in block:
        # The drop note is the filer's own prose, not log evidence: a step-region label quoted
        # inside it ("Run make openspec-check") must never become a reproduction command.
        if line.startswith("[filer]"):
            continue
        for m in re.finditer(r"\bmake ([a-z][a-z0-9-]+)", line):
            name = normalize_target(m.group(1))
            if name and name not in targets:
                targets.append(name)
        for m in re.finditer(r"make: \*\*\* \[([^\]]+)\]", line):
            name = normalize_target(m.group(1))
            if name and name not in targets:
                targets.append(name)
    return targets


# ---------------------------------------------------------------------------
# dedup: the ledger AND open issues carrying the marker
# ---------------------------------------------------------------------------

def open_failure_issue_runs(repo: str) -> set:
    """run ids already filed by this filer (issues carrying pipeline-run-failure, OPEN OR CLOSED).

    `--state all` is the point: a fix that merged quickly closes its issue, and a scan of OPEN
    issues only would let the NEXT weekly sweep re-file the same run. One run files once, ever.
    """
    issues = _gh_json([
        "issue", "list", "--repo", repo, "--state", "all", "--label", LABEL, "--limit", "500",
        "--json", "number,title,body",
    ])
    if not isinstance(issues, list):
        raise RuntimeError("issue list returned a non-list")
    runs: set = set()
    for issue in issues:
        for hit in bot_markers.parse_markers(issue.get("body") or ""):
            if hit["name"] == bot_markers.marker_name("queued-alarm", "failure") and hit.get("run"):
                try:
                    runs.add(int(hit["run"]))
                except ValueError:
                    pass
    return runs


# ---------------------------------------------------------------------------
# the issue body (declared message pattern: ## Why / ## What / ## How / ## Benefits /
# ## Technical Solution — rule #771; validated by `make issue-message-check`)
# ---------------------------------------------------------------------------

def step_provenance(job: dict, steps: list[str] | None, region: str | None) -> str:
    """Name the failing step from the two sources GitHub itself gives, never from chatter.

    `steps` are the names GitHub's job payload marked bad (`failing_step_names`); `region` is the
    `##[group]` label of the log region the error block was taken from (the command that step ran).
    When a block yields no `make` target but the step IS known, the reader gets the step instead of
    a line of test chatter (issue #1098). When NEITHER is known the sentence says so plainly — a
    missing diagnosis is reported, never papered over.
    """
    parts: list[str] = []
    if steps:
        parts.append("Failing step(s) per GitHub's own job steps: "
                     + ", ".join(f"`{s}`" for s in steps) + ".")
    if region:
        parts.append(f"The error block was taken from the log region `{region}`.")
    if not parts:
        parts.append("GitHub's job payload names no failed step and the log carries no step region "
                     "— the block is the whole capped tail (issue #1098).")
    return " ".join(parts)


def compose_body(run: dict, job: dict, block: list[str], targets: list[str],
                 log_error: str | None, when: dt.datetime,
                 steps: list[str] | None = None, region: str | None = None) -> str:
    marker = bot_markers.start_marker(
        "queued-alarm", when, run=run["databaseId"], kind="failure")
    repro = " ".join(f"make {t}" for t in targets[:3]) if targets else \
        f"gh run view {run['databaseId']} --log  # read the job named in this issue"
    diagnosis = "\n".join(block) if block else \
        f"(the log could not be read: {log_error or 'no error-shaped line found'})"
    diagnosis = redact(diagnosis)[0]

    parts = [
        pr_body.ISSUE_PATTERN_MARKER,
        marker,
        "",
        "## Why",
        f"A main pipeline run concluded bad after landing on master or on its schedule: "
        f"`{run.get('workflowName')}` run [{run['databaseId']}]({run.get('url')}) "
        f"(event `{run.get('event')}`, head `{(run.get('headSha') or '')[:10]}`, "
        f"created {run.get('createdAt')}). Nobody reads failed-run logs daily; this issue is the "
        f"diagnosis so the cause is tracked instead of re-derived from the run page by the next "
        f"person who opens it (issue #802).",
        "",
        "## What",
        f"The job `{job.get('name')}` (conclusion `{job.get('conclusion')}`) failed. "
        + (f"Failing target(s) named by the log: {', '.join('`make ' + t + '`' for t in targets)}."
           if targets else "The log names no `make` target — the job step itself is the unit.")
        + " " + step_provenance(job, steps, region),
        "",
        "## How",
        "Reproduce on the base commit:\n\n"
        f"```bash\n{repro}\n```\n\n"
        "Error block (scrubbed via `make scrub-log`'s redactor before it was written — no "
        "secret in any spelling may enter an issue body):\n\n"
        f"```text\n{diagnosis}\n```\n",
        "",
        "## Benefits",
        "- The failure has a tracked artifact with the exact reproduction command, not just a "
        "run URL.\n- A fixed failure must land a guard test (the ledger gate, "
        "`make pipeline-failure-guard-check`) that fails when the same error class is "
        "reintroduced.\n- Dedup by run id + marker means one run never files twice.",
        "",
        "## Technical Solution",
        "- `make pipeline-failure-issue` (this filer, `scripts/pipeline_failure_issue.py`) "
        "runs from `queued-alarm.yml` after the master/sweep/freshness alarms.\n"
        "- The ledger `data/pipeline_failures.json` records every diagnosed run (append-only); "
        "`make pipeline-failure-guard-check` (qa-validate's `validate` job) refuses an issue "
        "closed without its fix PR + guard test, and an entry naming a fix PR whose guard test "
        "does not exist in `tests/`.\n- The fix lands as its own reviewed change (rule 6g); "
        "this filer never fixes anything.",
    ]
    body = "\n".join(parts)
    # The declared pattern is checked BEFORE posting: a body that skips, empties or misorders a
    # section would red `make issue-message-check` on the issue it just opened (issue #771).
    problems = pr_body.section_problems(body)
    if problems:
        raise RuntimeError("refusing to file a body that violates the message pattern: "
                           + "; ".join(problems))
    return body


def file_issue(repo: str, run: dict, job: dict, block: list[str], targets: list[str],
               log_error: str | None, when: dt.datetime,
               steps: list[str] | None = None, region: str | None = None) -> dict:
    title = (f"tech-debt: {run.get('workflowName')} / {job.get('name')} failed "
             f"(run {run['databaseId']}"
             + (f", {' + '.join(targets[:3])}" if targets else "") + ")")
    body = compose_body(run, job, block, targets, log_error, when, steps, region)
    out = _gh("issue", "create", "--repo", repo, "--title", title, "--body", body,
              "--label", LABEL)
    url = out.stdout.strip()
    # `--label` can exit 0 having applied nothing (issue #161): verify the label landed.
    number = url.rsplit("/", 1)[-1]
    labels = _gh_json(["issue", "view", number, "--repo", repo, "--json", "labels"])
    names = [l["name"] for l in labels.get("labels", [])]
    if LABEL not in names:
        _gh("issue", "edit", number, "--repo", repo, "--add-label", LABEL)
        labels = _gh_json(["issue", "view", number, "--repo", repo, "--json", "labels"])
        names = [l["name"] for l in labels.get("labels", [])]
        if LABEL not in names:
            raise RuntimeError(f"issue {number} was filed without the {LABEL} label")
    return {"number": number, "url": url, "title": title}


def _issue_number(entry: dict) -> int | None:
    """The issue number a re-diagnosis should annotate, from the ledger row's own fields.

    Prefer `issue_number` (an int or a numeric string); fall back to the trailing number of
    `issue_url` (`…/issues/<n>`). Returns None when the row cites no issue (e.g. a
    marker-matched row filed before the ledger existed) — a raise for such a row is
    comment-free (rule 2: the thread is the human's, but there is no thread here to write).
    """
    num = entry.get("issue_number")
    if num is not None:
        try:
            return int(num)
        except (TypeError, ValueError):
            pass
    m = re.search(r"/issues/([0-9]+)", str(entry.get("issue_url") or ""))
    return int(m.group(1)) if m else None


def _issue_comments(repo: str, number: int) -> list[dict]:
    """The whole comment thread of an issue, oldest-first, one JSON object per line (paginated)."""
    raw = _gh("api", f"repos/{repo}/issues/{number}/comments", "--paginate", "--jq", ".[]")
    out: list[dict] = []
    for line in raw.stdout.splitlines():
        if line.strip():
            out.append(json.loads(line))
    return out


def compose_rediagnose_comment(entry: dict, excerpt: str, targets: list[str],
                               when: dt.datetime) -> str:
    """The ONE comment posted on an issue whose UNDIAGNOSED row the sweep re-diagnosed.

    Carries the `pipeline-rediagnose` marker (`run=<rid>` is the dedup key) and quotes the landed
    scrubbed `error_excerpt` + `targets`, so the thread the row was filed on no longer reads
    "log unreadable" — the ledger is the machine's memory, the thread is the human's (issue #987).
    `excerpt` is already scrubbed by the caller before this is composed.
    """
    rid = entry.get("run_id") or 0
    targets_txt = ", ".join(f"`make {t}`" for t in targets) if targets else "(no make target named)"
    marker = bot_markers.rediagnose_marker(when, rid)
    return (
        "A UNDIAGNOSED main-pipeline failure was re-diagnosed on this sweep: the failed run's log "
        f"has been re-read and the diagnosis landed in `data/pipeline_failures.json` "
        f"(run {rid}). The issue body below is the ORIGINAL filing; this row in the ledger now "
        "carries `rediagnosed_utc`, a scrubbed `error_excerpt` and the grown `targets` (rule 3b: "
        "the `undiagnosed` field is KEPT).\n\n"
        f"**Targets (make):** {targets_txt}\n\n"
        "**Error block (scrubbed):**\n"
        "```text\n"
        f"{excerpt}\n"
        "```\n\n"
        f"{bot_markers.rediagnose_marker(when, rid)}"
    )


def post_rediagnose_comment(repo: str, entry: dict, excerpt: str, targets: list[str],
                            when: dt.datetime) -> int | None:
    """Post ONE marker-deduplicated comment on an issue whose row was re-diagnosed.

    Reads the issue's existing comments FIRST and skips when a `pipeline-rediagnose` marker for
    the same run id is already present — one comment per raised row, never per sweep (issue #987).
    Returns the issue number annotated, or None when the row cites no issue. Written with the
    default `github.token` (rule 6e: the owner PAT cannot comment — the caller `queued-alarm.yml`
    passes `GH_TOKEN: ${{ github.token }}`).
    """
    number = _issue_number(entry)
    if number is None:
        return None
    thread = "\n".join(c.get("body") or "" for c in _issue_comments(repo, number))
    rid = entry.get("run_id")
    # One comment PER RAISED ROW: dedup on THIS run's marker, so a thread carrying an older row's
    # re-diagnosis comment is still annotated for a newly-raised row (issue #987).
    if rid is not None and str(rid) in bot_markers.rediagnose_marker_runs(thread):
        return number  # this exact run is already annotated — never a second comment for it
    _gh("issue", "comment", str(number), "--repo", repo, "--body",
        compose_rediagnose_comment(entry, excerpt, targets, when))
    return number


# ---------------------------------------------------------------------------
# the re-diagnosis pass (issue #969): UNDIAGNOSED is not terminal
# ---------------------------------------------------------------------------

def _still_unreadable(entry: dict, rid: int, ledger: dict, ledger_path: Path, dry: bool,
                      now: dt.datetime, message: str) -> list[str]:
    """One still-unreadable re-read (issue #986): GROW the append-only attempt counter and, at the
    bound, stamp TERMINAL `log_expired` (loud, once). Persists the counter every sweep so it
    accumulates across weekly sweeps (rule 3b: growth only, `undiagnosed` KEPT, nothing removed).

    The two branches this guards are the retention symptom — GitHub purges run logs after the
    retention window, so `jobs unreadable again` / `log still unreadable` can never heal and must
    drain the pending queue instead of printing retry noise for ever. `requested` attempts must be
    written; `--dry` previews without writing.
    """
    entry["rediagnose_attempts"] = int(entry.get("rediagnose_attempts") or 0) + 1
    out = [f"rediagnose run {rid}: {message}"]
    if entry["rediagnose_attempts"] >= MAX_REDIAGNOSE_ATTEMPTS:
        entry["log_expired"] = message
        entry["log_expired_utc"] = now.isoformat()
        if dry:
            out.append(f"WOULD EXPIRE run {rid}: {message} — a {MAX_REDIAGNOSE_ATTEMPTS}th "
                       "still-unreadable sweep would stamp TERMINAL log_expired and drain the "
                       "pending queue (issue #986)")
        else:
            out.append(f"LOG EXPIRED run {rid}: {message} — after {MAX_REDIAGNOSE_ATTEMPTS} "
                       "still-unreadable sweeps the run's log aged out of Actions retention and can "
                       "never be diagnosed; the pending queue drains here (issue #986)")
    if not dry:
        ledger_path.write_text(json.dumps(ledger, indent=2) + "\n", encoding="utf-8")
    return out


def row_is_diagnosed(entry: dict) -> bool:
    """Does this ledger row carry a diagnosis at all? The ONE predicate (issue #1136).

    A row is diagnosed when EITHER reader landed an error block for it — the filer's own read or
    the re-diagnosis pass's re-read (both raise it into `error_excerpt`; the legacy
    `rediagnosed_excerpt` spelling is kept for rows written before #969's shape).

    The `undiagnosed` KEY is NOT the predicate, and reading it as one is the defect this seam
    exists to kill. The filer writes `"undiagnosed": log_error` (main(), the filing pass), so a
    row whose log read SUCCEEDED stores `undiagnosed: None` — a FALSY marker on a row that has no
    error block either. Measured in the shipped `data/pipeline_failures.json` (20 rows,
    2026-11-19): five rows — runs 43147240875, 43716345030, 43716362366, 43718826142, 43725338063
    (issues #1039–#1043) — carry `undiagnosed: None`, no `error_excerpt`, no
    `rediagnosed_excerpt`, no `log_expired`, yet each already names a landed `fix_pr` + `guard`.
    The marker-key filter answers `pending = []` for the WHOLE ledger, so no pass — and no future
    sweep — can ever recover WHICH failure those rows attribute, while
    `make pipeline-failure-guard-check` counted them as diagnosed. Every reader of the ledger now
    asks THIS question, through this one function (rule 6d).
    """
    return bool(entry.get("error_excerpt") or entry.get("rediagnosed_excerpt"))


def rediagnose_pending(ledger: dict) -> list[dict]:
    """The rows the re-diagnosis pass must fetch (issue #1136: selected by the ABSENCE of a
    diagnosis, never by the presence of an `undiagnosed` key).

    A row is pending when it names NEITHER `error_excerpt` NOR `rediagnosed_excerpt` and is not
    the terminal `log_expired` drain (issue #986) and has not already been raised this ledger's
    life (`rediagnosed_utc`, which the raise stamps TOGETHER with its `error_excerpt` — never on
    its own). Selection by the diagnosis itself therefore catches every shape a marker-key filter
    hides: a row stamped with `fix_pr` + `guard` by a ledger PR but never diagnosed, a row matched
    only by its issue marker, and the original still-UNDIAGNOSED filing.
    """
    return [e for e in ledger.get("failures", [])
            if not row_is_diagnosed(e) and not e.get("rediagnosed_utc")
            and not e.get("log_expired")]


def rediagnose_undiagnosed(repo: str, ledger: dict, ledger_path: Path, dry: bool,
                           now: dt.datetime) -> list[str]:
    """Re-read the log of every ledger row that carries NO diagnosis and raise it APPEND-ONLY.

    The filer files UNDIAGNOSED when its own log fetch fails (a reader defect, a transient API
    outage). Without this pass those rows stay UNDIAGNOSED forever: the #923 reader fix landed,
    yet all 14 rows filed before it needed a MANUAL change each (#820–#825). Each sweep therefore
    re-derives the failed job from the run's own job list, re-fetches through the
    escape-tolerant reader, and raises the row: keys ADDED (`rediagnosed_utc`, scrubbed
    `error_excerpt`, `rediagnosis_note`), `targets` GROWN only — no key removed, no value
    shrunk, the `undiagnosed` field KEPT (rule 3b). `fix_pr`/`guard` are untouched: attribution
    stays each fix's own decision (rule 6r). A readable log with no error-shaped line never
    marks the row done.

    A RE-READ THAT CANNOT READ THE RUN (issue #986) is bounded: each still-unreadable sweep (jobs
    unreadable again / log still unreadable — the retention symptom) GROWS the row's
    `rediagnose_attempts`, and after MAX_REDIAGNOSE_ATTEMPTS a TERMINAL `log_expired` state is
    stamped (loud, once) instead of retrying for ever. The row is then EXCLUDED from the pending
    set by `log_expired`, so the queue drains. The two structural branches (no failed job, a
    readable log with no error line) stay reported-and-retried per #969, not expired.

    The PENDING SET is selected by `rediagnose_pending` — the ABSENCE of a diagnosis (issue
    #1136), never by the presence of an `undiagnosed` key. The filer stores `"undiagnosed":
    log_error`, so a row whose log it DID read carries `undiagnosed: None`: a row stamped with
    `fix_pr` + `guard` and no error block was therefore selected by NO pass and stayed
    undiagnosable for ever — five such rows sit in the shipped ledger (runs 43147240875 /
    43716345030 / 43716362366 / 43718826142 / 43725338063, issues #1039–#1043). Selection by the
    diagnosis itself fetches them on the next sweep.
    """
    lines: list[str] = []
    pending = rediagnose_pending(ledger)
    for entry in pending:
        rid = int(entry.get("run_id", 0))
        job_name = entry.get("job")
        try:
            jobs = failed_jobs(repo, rid)
        except RuntimeError as exc:
            lines.extend(_still_unreadable(entry, rid, ledger, ledger_path, dry, now,
                                           f"jobs unreadable again: {exc}"))
            continue
        match = next((j for j in jobs if job_name is None or j.get("name") == job_name), None)
        if match is None:
            lines.append(f"rediagnose run {rid}: the run names no failed job {job_name!r} "
                         f"(jobs: {[j.get('name') for j in jobs]}) — row stays UNDIAGNOSED")
            continue
        try:
            log_text = fetch_log(repo, match["databaseId"])
            block = extract_error_block(log_text, job=match)
            region = error_region(log_text)
        except RuntimeError as exc:
            lines.extend(_still_unreadable(entry, rid, ledger, ledger_path, dry, now,
                                           f"log still unreadable: {exc}"))
            continue
        steps = failing_step_names(match)
        if not block:
            lines.append(f"rediagnose run {rid}: log readable but names no error-shaped line "
                         "— row stays UNDIAGNOSED")
            continue
        targets = failed_make_targets(block)
        excerpt = redact("\n".join(block))[0]
        if dry:
            lines.append(f"WOULD RAISE run {rid} (job {match.get('name')}): "
                         f"error_lines={len(block)} targets+={targets or '-'} "
                         f"steps={steps or '-'} region={region or '-'}")
            continue
        # The raise re-normalises the row's WHOLE targets list, old entries included
        # (issue #1054): a row that carried the `Makefile:<line>: ` form comes out of the
        # raise uniform with its sibling rows, the bare parseable `make <target>`.
        grown: list[str] = []
        for t in list(entry.get("targets") or []) + targets:
            n = normalize_target(str(t))
            if n and n not in grown:
                grown.append(n)
        # The ledger is the machine's memory; the issue thread is the human's. A raise that lands a
        # diagnosis must annotate the thread the row was filed on — ONE marker-deduplicated comment
        # per raised row, never per sweep (issue #987). The comment is posted BEFORE the row is
        # marked raised, so a raise always lands WITH its annotation: a comment the thread cannot
        # accept keeps the row pending and is reported loudly, retried next sweep (a raised row
        # with no thread annotation is exactly the gap this closes). A row that cites no issue is
        # raised comment-free.
        ann = "no issue cited"
        try:
            annotated = post_rediagnose_comment(repo, entry, excerpt, grown, now)
            if annotated is not None:
                ann = f"annotated issue #{annotated}"
        except RuntimeError as exc:
            lines.append(f"rediagnose run {rid}: thread annotation FAILED — row stays "
                         f"UNDIAGNOSED, retried next sweep: {exc}")
            continue
        entry["rediagnosed_utc"] = now.isoformat()
        entry["error_excerpt"] = excerpt
        entry["targets"] = grown
        entry["rediagnosis_note"] = (
            f"re-read on this sweep from job {match['databaseId']} ({match.get('name')}) by "
            f"make pipeline-failure-issue (issue #969); the original undiagnosed field is KEPT"
        )
        # Additive keys from the SAME seam the filing pass uses (issue #1098): a raised row names
        # the step GitHub marked bad and the region the re-read block came from.
        entry["failing_steps"] = steps
        entry["error_region"] = region
        ledger_path.write_text(json.dumps(ledger, indent=2) + "\n", encoding="utf-8")
        lines.append(f"REDIAGNOSED run {rid} (job {match.get('name')}): error block landed, "
                     f"targets={grown or '-'} steps={steps or '-'} region={region or '-'} — {ann}")
    return lines


# ---------------------------------------------------------------------------
# the stamp pass (issue #1099): a merged fix PR raises its ledger row
# ---------------------------------------------------------------------------

def issue_close_refs(repo: str, number: int) -> tuple[str | None, list[int]]:
    """(issue state, PR numbers whose squash closed this issue).

    `closedByPullRequestsReferences` is GitHub's OWN closing-keyword record — the
    measured closed issue #833 answers [1057]; a hand-closed issue answers []. The
    pass reads the link, never the prose: a close claim in a comment is not a fix.
    """
    proc = _gh("issue", "view", str(number), "--repo", repo,
               "--json", "state,closedByPullRequestsReferences")
    data = json.loads(proc.stdout)
    refs = data.get("closedByPullRequestsReferences") or []
    numbers = sorted({int(r["number"]) for r in refs if r.get("number")})
    return data.get("state"), numbers


def pr_close_view(repo: str, number: int) -> dict:
    """The PR's own merged state and its diff (path + changeType per file)."""
    proc = _gh("pr", "view", str(number), "--repo", repo,
               "--json", "number,title,mergedAt,files")
    return json.loads(proc.stdout)


def diff_guard_modules(files: list[dict]) -> list[str]:
    """Every `tests/test_*.py` module the PR's own diff touches, ADDED first.

    A fix that ADDS a `tests/test_*.py` module is the §6r shape and outranks a
    modified one; the measured #833 fix (PR #1057) modified its guard module, so a
    modified `tests/test_*.py` still counts. Anything outside `tests/` is not a guard.
    One list for both readers (rule 6d): the stamp pass takes the FIRST (issue #1099),
    the attribution pass requires a claim's guard to be IN the list (issue #1053).
    """
    touched: list[tuple[int, str]] = []
    for f in files:
        path = str(f.get("path") or "")
        if path.startswith("tests/") and path.endswith(".py") and "/test_" in path:
            touched.append((0 if f.get("changeType") == "ADDED" else 1, path))
    return [path for _, path in sorted(touched)]


def diff_guard(files: list[dict]) -> str | None:
    """The guard module the stamp pass stamps — the first of `diff_guard_modules`."""
    modules = diff_guard_modules(files)
    return modules[0] if modules else None


def compose_stamp_comment(entry: dict, pr_number: int, guard: str, merged_utc: str,
                         title: str, when: dt.datetime) -> str:
    """The ONE comment posted on an issue whose ledger row the stamp pass raised.

    Carries the registered `pipeline-ledger-stamp` marker (`run=<rid>` is the dedup key) and
    names the merged PR, its guard module and the exact keys the row now carries — the thread
    learns the fix landed without anyone re-reading the ledger by hand (issue #1099; the
    annotation pattern is the one issue #987 established for re-diagnosis).
    """
    rid = entry.get("run_id") or 0
    return (
        "This issue's pipeline-failure ledger row was RAISED on the sweep: a merged fix PR "
        f"closed the issue, so `make pipeline-failure-issue` stamped the row of run {rid} in "
        "`data/pipeline_failures.json` (issue #1099; rule 6r: the fix PR raises its row).\n\n"
        f"**Fix PR:** #{pr_number} — {title[:120]} (merged {merged_utc})\n\n"
        f"**Guard test:** `{guard}` — named from the PR's own `tests/` diff"
        + ("" if guard == (entry.get("guard") or guard)
           else f" (the row's recorded guard `{entry.get('guard')}` was kept)")
        + "\n\n"
        f"`make pipeline-failure-guard-check` now reads this row as a landed fix; a closed "
        "issue whose row names no fix PR stays RED at that gate.\n\n"
        f"{bot_markers.ledger_stamp_marker(when, rid)}"
    )


def post_stamp_comment(repo: str, entry: dict, pr_number: int, guard: str,
                       merged_utc: str, title: str, when: dt.datetime) -> int | None:
    """Post ONE marker-deduplicated annotation on the issue whose row was just raised.

    Reads the whole thread FIRST and skips when a `pipeline-ledger-stamp` marker for this run id
    is already present — one annotation per raised row, never per sweep. Returns the issue
    number annotated, or None when the row cites no issue. Written with the default
    `github.token` (rule 6e: the owner PAT cannot comment — `queued-alarm.yml` passes it).
    """
    number = _issue_number(entry)
    if number is None:
        return None
    thread = "\n".join(c.get("body") or "" for c in _issue_comments(repo, number))
    rid = entry.get("run_id")
    if rid is not None and str(rid) in bot_markers.parse_ledger_stamp_runs(thread):
        return number  # this exact raise is already annotated — never a second comment for it
    _gh("issue", "comment", str(number), "--repo", repo, "--body",
        compose_stamp_comment(entry, pr_number, guard, merged_utc, title, when))
    return number


def stamp_merged_fix_prs(repo: str, ledger: dict, ledger_path: Path, dry: bool,
                         now: dt.datetime) -> list[str]:
    """Raise every unraised row whose issue a MERGED guard-carrying fix PR closed.

    Rule 6r says the fix PR raises its ledger row with `fix_pr` + `guard`; until
    issue #1099 NOTHING did it automatically — keepers did it by hand (#1067 and
    the Nov-15 classification) and every unraised row held a red
    `make pipeline-failure-guard-check` plus a full keeper cycle before its issue
    could carry the #993 close-with-proof verdict. This pass: for each row whose
    `fix_pr` is empty (and that is not the terminal `log_expired` shape), read the
    row's issue; a CLOSED issue closed by a MERGED PR whose diff carries a
    `tests/` guard gains the keys `fix_pr`, `fix_pr_merged_utc`, `guard` (only if
    the row names none already — a recorded guard is never overwritten),
    `stamp_utc` and `stamp_note`, in place of the nulls the filer wrote. An OPEN
    issue is a fix in flight; a close with no closing PR is the keeper's act; a
    merged close with no `tests/` diff is the exact defect §6r exists to refuse —
    all three are REPORTED, never stamped. Idempotent: a stamped row is never
    touched again. `--dry` prints WOULD STAMP and writes nothing. A failed read
    is loud on the row and retried next sweep.
    """
    lines: list[str] = []
    for entry in ledger["failures"]:
        rid = int(entry.get("run_id", 0))
        if entry.get("fix_pr"):
            continue  # attributed — by a keeper or an earlier stamp; idempotent
        if entry.get("log_expired"):
            continue  # the terminal drain shape (#986) is not a fix raise
        number = entry.get("issue_number")
        if not number:
            lines.append(f"stamp run {rid}: the row cites no issue — nothing to stamp")
            continue
        try:
            state, pr_numbers = issue_close_refs(repo, int(number))
        except (RuntimeError, ValueError) as exc:
            lines.append(f"stamp run {rid}: issue #{number} read failed ({exc}) — "
                         "retried next sweep")
            continue
        if state != "CLOSED":
            lines.append(f"stamp run {rid}: issue #{number} is {state or 'INDETERMINATE'} "
                         "— fix in flight, not stamped")
            continue
        if not pr_numbers:
            lines.append(f"stamp run {rid}: issue #{number} CLOSED with no closing PR — "
                         "a manual close stays the keeper's act (rule 6r)")
            continue
        chosen: tuple[int, str, str, str] | None = None
        unmerged: list[int] = []
        guardless: list[int] = []
        for pr_number in pr_numbers:
            try:
                pr = pr_close_view(repo, pr_number)
            except (RuntimeError, ValueError) as exc:
                lines.append(f"stamp run {rid}: PR #{pr_number} read failed ({exc}) — "
                             "retried next sweep")
                continue
            if not pr.get("mergedAt"):
                unmerged.append(pr_number)
                continue
            guard = diff_guard(pr.get("files") or [])
            if not guard:
                guardless.append(pr_number)
                continue
            chosen = (pr_number, guard, str(pr.get("mergedAt") or ""), str(pr.get("title") or ""))
            break
        if chosen is None:
            if unmerged:
                lines.append(f"stamp run {rid}: closed by PR(s) "
                             f"{', '.join(f'#{p}' for p in unmerged)} not merged yet — "
                             "fix in flight, not stamped")
            if guardless:
                lines.append(f"STAMP run {rid}: closed by merged PR(s) "
                             f"{', '.join(f'#{p}' for p in guardless)} whose diff carries NO "
                             "tests/ guard — not stamped (rule 6r: a fix without its guard "
                             "test is the defect)")
            continue
        pr_number, guard, merged_utc, title = chosen
        kept_guard = entry.get("guard")
        verb = "WOULD STAMP" if dry else "STAMPED"
        lines.append(f"{verb} run {rid} (issue #{number}) -> fix_pr #{pr_number}, "
                     f"guard {kept_guard or guard}{' (recorded guard kept)' if kept_guard else ''}"
                     f", PR merged {merged_utc}")
        if dry:
            continue
        entry["fix_pr"] = int(pr_number)
        entry["fix_pr_merged_utc"] = merged_utc
        if not kept_guard:
            entry["guard"] = guard
        entry["stamp_utc"] = now.isoformat()
        entry["stamp_note"] = (
            f"raised by make pipeline-failure-issue (issue #1099): merged PR #{pr_number} "
            f"({title[:100]}) closed issue #{number}"
            + (f"; guard {guard} named from its diff" if not kept_guard
               else f"; the row's recorded guard {kept_guard} is KEPT (never overwritten, "
                    "rule 3b)")
        )
        ledger_path.write_text(json.dumps(ledger, indent=2) + "\n", encoding="utf-8")
        # The ledger row is the machine's memory; the thread is the human's. ONE marker-
        # deduplicated annotation per raised row (the #987 pattern), posted AFTER the row is
        # written so a comment failure never loses the raise.
        try:
            annotated = post_stamp_comment(repo, entry, pr_number, guard, merged_utc,
                                           title, now)
            if annotated is not None:
                lines.append(f"stamp run {rid}: issue #{number} annotated with the raise")
        except RuntimeError as exc:
            lines.append(f"stamp run {rid}: ledger row raised, but the issue annotation "
                         f"failed ({exc}) — the ledger carries it")
    return lines


# ---------------------------------------------------------------------------
# the attribution pass (issue #1053, rule 6r)
# ---------------------------------------------------------------------------

#: A REFUSED attribution: loud (exit 2), and NOTHING is written.
ATTRIBUTION_REFUSED = 2


class AttributionRefused(RuntimeError):
    """An attribution claim that GitHub or the tree does not back — never applied."""


def diagnosed_unattributed(ledger: dict) -> list[dict]:
    """Rows that carry a diagnosis but name no fix PR — the #1053 report set.

    The terminal `log_expired` drain (issue #986) and a still-undiagnosed row (re-diagnosis,
    issue #969 owns it) are excluded: this pass attributes a KNOWN error class to a landed fix,
    nothing else.
    """
    out: list[dict] = []
    for entry in ledger.get("failures", []):
        if entry.get("fix_pr") or entry.get("log_expired"):
            continue
        if not row_is_diagnosed(entry):
            continue
        out.append(entry)
    return out


def why_stamp_cannot_reach(repo: str, entry: dict) -> str:
    """WHY the automatic stamp pass cannot raise this row — read from GitHub, never guessed.

    The stamp pass (`stamp_merged_fix_prs`, issue #1099) reaches ONLY a row whose issue a MERGED,
    guard-carrying PR CLOSED. The measured rows issue #1053 is about (#826/#827/#828, runs
    42976201014 / 42977708147 / 43047130543) sit outside that shape: their issues are OPEN and
    held by a verdict label, while the fix that actually landed was a different merged PR. This
    reports which of those shapes a row is in, through the SAME reads the stamp pass uses.
    """
    number = entry.get("issue_number")
    if not number:
        return "the row cites no issue — nothing to read"
    try:
        state, pr_numbers = issue_close_refs(repo, int(number))
    except (RuntimeError, ValueError) as exc:
        return f"issue #{number} read failed ({exc}) — retried next sweep"
    if state != "CLOSED":
        return (f"issue #{number} is {state or 'INDETERMINATE'} — open, or held by a verdict "
                "label; the stamp pass stamps a CLOSED issue only")
    if not pr_numbers:
        return f"issue #{number} CLOSED with no closing PR — a manual close, the keeper's act"
    for pr_number in pr_numbers:
        try:
            pr = pr_close_view(repo, pr_number)
        except (RuntimeError, ValueError) as exc:
            return f"closing PR #{pr_number} read failed ({exc}) — retried next sweep"
        if not pr.get("mergedAt"):
            return f"issue #{number} closed by PR #{pr_number} which is not merged"
        if not diff_guard(pr.get("files") or []):
            return (f"issue #{number} closed by merged PR #{pr_number} whose diff carries no "
                    "tests/ guard — rule 6r refuses that fix")
    return f"issue #{number} closed by a merged guard-carrying PR — the stamp pass should have " \
           "raised it; re-run make pipeline-failure-issue"


def report_unattributed(repo: str, ledger: dict) -> list[str]:
    """Print every diagnosed row that names no fix PR, and the exact remedy (issue #1053).

    Writes NOTHING: this is the half that makes the gap loud on the sweep instead of leaving the
    rows as silent nulls that `make pipeline-failure-guard-check` only reads as a warning until a
    human opens the ledger.
    """
    rows = diagnosed_unattributed(ledger)
    lines: list[str] = []
    for entry in sorted(rows, key=lambda e: int(e.get("run_id") or 0)):
        rid = entry.get("run_id")
        targets = ", ".join(entry.get("targets") or []) or "-"
        lines.append(f"UNATTRIBUTED run {rid} ({entry.get('workflow')} / "
                     f"{entry.get('job') or '?'}) targets={targets} | "
                     f"{why_stamp_cannot_reach(repo, entry)}")
        lines.append(f"  remedy (only if a MERGED fix PR with a real guard exists for this "
                     f"error class): make pipeline-failure-attribute REPO={repo} "
                     f"RUN={rid} FIX_PR=<merged PR#> GUARD=tests/test_<guard>.py::<test> "
                     f"EVIDENCE=\"<path:line | make <target> that proves the class is fixed>\"")
    lines.append(f"pipeline-failure-attribute: unattributed_diagnosed_rows={len(rows)} "
                 "(a row with no fix PR is reported, never red; rule 6r)")
    return lines


def _guard_is_proven(guard: str, entry: dict, pr_modules: list[str]) -> str:
    """The claimed guard must exist as a collected module AND be tied to the fix (issue #1053).

    Tied means: it is a module the fix PR's own diff touches, OR the row already recorded it
    (rule 3b: a recorded guard is never overwritten). `guard_test_exists` is the SAME seam the
    ledger gate uses, so `fix_pr` + `guard` on the row means the same thing to both readers.
    """
    from pipeline_failure_guard_check import guard_test_exists  # the ONE seam (rule 6d)
    module = guard.split("::", 1)[0]
    if not guard_test_exists(module):
        raise AttributionRefused(
            f"guard {guard!r} is not a `tests/test_*.py` module `make test` collects")
    if "::" in guard:
        test = guard.partition("::")[2].strip()
        try:
            source = (ROOT / module).read_text(encoding="utf-8")
        except OSError as exc:
            raise AttributionRefused(f"guard module {module} unreadable: {exc}") from None
        if f"def {test}" not in source:
            raise AttributionRefused(
                f"guard {guard!r}: {module} does not define `{test}` — a guard must name a "
                "test that exists")
    recorded = str(entry.get("guard") or "")
    if recorded:
        if recorded != module:
            raise AttributionRefused(
                f"the row already records guard {recorded!r}; an attribution may not replace it "
                "(rule 3b) — claim that guard instead")
        return recorded
    if module not in pr_modules:
        raise AttributionRefused(
            f"guard {module} is not in the fix PR's own diff ({pr_modules or 'no tests/ file'} "
            "and the row records no guard) — the guard must come from the fix")
    return module


def _evidence_is_checkable(evidence: str, touched_paths: list[str], guard_module: str) -> str:
    """The evidence must name something a reviewer can re-run AND tie it to THIS fix."""
    from issue_verdict import evidence_is_checkable  # the ONE evidence rule (issue #494, rule 6e)
    text = (evidence or "").strip()
    if not text:
        raise AttributionRefused("an attribution owes EVIDENCE — a claim with no proof is prose")
    if "pipeline_failures.json" in text:
        raise AttributionRefused(
            "the evidence cites the ledger this pass writes — circular: the row is unattributed "
            "BECAUSE of the ledger's own state. Cite the tree (a path:line, a `make` target).")
    if not evidence_is_checkable(text):
        raise AttributionRefused(
            f"EVIDENCE {text[:120]!r} names nothing checkable — it must cite a path:line, a file "
            "under the repo, or a `make`/`python3`/`gh` command (issue #494)")
    for path in re.findall(r"(?:scripts|tests|data|\.github|openspec)/[\w./-]+|Makefile|AGENTS\.md",
                           text):
        if not (ROOT / path).exists():
            raise AttributionRefused(f"evidence cites {path!r}, which does not exist in the tree")
    linked = any(p in text for p in touched_paths) or guard_module in text
    if not linked:
        raise AttributionRefused(
            "the evidence names nothing this fix PR touched and does not name the guard module — "
            f"fix PR touched {touched_paths[:8] or 'no files'}; an attribution must link the "
            "claim to the fix it cites")
    return text


def compose_attribution_comment(entry: dict, pr_number: int, guard: str, merged_utc: str,
                                title: str, evidence: str, when: dt.datetime) -> str:
    """The ONE comment on an issue whose ledger row an ATTESTED attribution raised.

    Its own registered marker (`pipeline-attribution`, rule 6j — the stamp pass writes
    `pipeline-ledger-stamp`, so a thread says WHICH pass raised the row), `run=<rid>` is the dedup
    key, and the same honesty: it says the automatic pass could NOT reach this row and the raise
    therefore came from an attestation the seam verified.
    """
    rid = entry.get("run_id") or 0
    return (
        "This issue's pipeline-failure ledger row (run "
        f"{rid}) was ATTRIBUTED by an attestation: `make pipeline-failure-attribute` raised "
        "`fix_pr` + `guard` in `data/pipeline_failures.json` (issue #1053; rule 6r) because the "
        "automatic stamp pass could not reach it — that pass raises only a row whose issue a "
        "merged fix PR CLOSED.\n\n"
        f"**Fix PR:** #{pr_number} — {title[:120]} (merged {merged_utc})\n\n"
        f"**Guard test:** `{guard}` — proven collected by `make test` and tied to the fix PR\n\n"
        f"**Evidence:** {evidence}\n\n"
        "`make pipeline-failure-guard-check` now reads this row as a landed fix. An attribution "
        "whose PR is unmerged, whose guard is uncollected, or whose evidence names nothing the "
        "fix touched is REFUSED by the seam (exit 2) and never written.\n\n"
        f"{bot_markers.attribution_marker(when, rid)}"
    )


def post_attribution_comment(repo: str, entry: dict, pr_number: int, guard: str,
                             merged_utc: str, title: str, evidence: str,
                             when: dt.datetime) -> int | None:
    """Post ONE marker-deduplicated attribution annotation (the #987/#1099 pattern).

    Skips when a `pipeline-attribution` marker for this run id already exists — one annotation
    per raised row, never per sweep. Default `github.token` (rule 6e: the owner PAT cannot
    comment). Returns the issue number annotated, or None when the row cites no issue.
    """
    number = _issue_number(entry)
    if number is None:
        return None
    thread = "\n".join(c.get("body") or "" for c in _issue_comments(repo, number))
    rid = entry.get("run_id")
    if rid is not None and str(rid) in bot_markers.attribution_marker_runs(thread):
        return number
    _gh("issue", "comment", str(number), "--repo", repo, "--body",
        compose_attribution_comment(entry, pr_number, guard, merged_utc, title, evidence, when))
    return number


def attribute_claim(repo: str, ledger: dict, ledger_path: Path, claim: dict,
                    now: dt.datetime) -> list[str]:
    """Raise ONE ledger row on an attested fix PR — only after the claim proves itself.

    `claim` = {run, fix_pr, guard, evidence}. Proofs, in order (each refusal is loud and writes
    nothing): the row EXISTS and is diagnosed (not `log_expired`, not still-undiagnosed); the PR
    is MERGED (GitHub's `mergedAt`, never a text guess); the guard is a collected
    `tests/test_*.py` module tied to the fix (its diff, or the row's own recorded guard) and a
    named `::test` actually exists in it; the evidence is checkable and names the fix. A row that
    already carries THIS fix_pr is an idempotent no-op; a row carrying a DIFFERENT one is a
    refusal — one landed fix per row. Keys are added append-only (rule 3b) and the raise rides
    the same ledger-PR landing as the filer's append.
    """
    rid = int(claim["run"])
    entry = next((e for e in ledger["failures"] if int(e.get("run_id") or 0) == rid), None)
    if entry is None:
        raise AttributionRefused(f"no ledger row for run {rid} — nothing to attribute")
    if entry.get("log_expired"):
        raise AttributionRefused(
            f"run {rid} is the terminal `log_expired` drain (issue #986) — its error class was "
            "never known, so there is nothing to attribute")
    if not row_is_diagnosed(entry):
        raise AttributionRefused(
            f"run {rid} carries no diagnosis — re-diagnosis (issue #969/#986, selected by "
            "`rediagnose_pending` per issue #1136) owns it; an attribution pins a KNOWN error "
            "class, not a guess")
    claimed_pr = int(claim["fix_pr"])
    existing = entry.get("fix_pr")
    if existing:
        if int(existing) == claimed_pr:
            return [f"run {rid} already attributes fix PR #{claimed_pr} — no-op (idempotent)"]
        raise AttributionRefused(
            f"run {rid} already names fix PR #{existing}; a row carries ONE landed fix — an "
            "attribution may not replace it (rule 3b)")

    try:
        pr = pr_close_view(repo, claimed_pr)
    except (RuntimeError, ValueError) as exc:
        raise AttributionRefused(f"fix PR #{claimed_pr} read failed: {exc}") from None
    merged_utc = str(pr.get("mergedAt") or "")
    if not merged_utc:
        raise AttributionRefused(
            f"fix PR #{claimed_pr} is NOT merged (mergedAt empty) — an unmerged PR is a fix in "
            "flight, never an attribution")
    files = pr.get("files") or []
    modules = diff_guard_modules(files)
    touched = [str(f.get("path") or "") for f in files if f.get("path")]
    guard = _guard_is_proven(str(claim["guard"] or ""), entry, modules)
    evidence = _evidence_is_checkable(str(claim["evidence"] or ""), touched, guard)
    title = str(pr.get("title") or "")

    entry["fix_pr"] = claimed_pr
    entry["fix_pr_merged_utc"] = merged_utc
    if not entry.get("guard"):
        entry["guard"] = guard
    entry["stamp_utc"] = now.isoformat()
    entry["attribution_evidence"] = evidence
    entry["stamp_note"] = (
        f"attributed by `make pipeline-failure-attribute` (issue #1053): merged PR #{claimed_pr} "
        f"({title[:100]}) is the landed fix for this error class; guard {guard}; evidence: "
        f"{evidence[:200]}"
    )
    ledger_path.write_text(json.dumps(ledger, indent=2) + "\n", encoding="utf-8")
    lines = [f"ATTRIBUTED run {rid} -> fix_pr #{claimed_pr} (merged {merged_utc}), guard {guard}"]
    try:
        annotated = post_attribution_comment(repo, entry, claimed_pr, guard, merged_utc, title,
                                            evidence, now)
        if annotated is not None:
            lines.append(f"run {rid}: issue #{annotated} annotated with the attribution")
    except RuntimeError as exc:
        lines.append(f"run {rid}: ledger row raised, but the issue annotation failed ({exc}) "
                     "— the ledger carries it")
    return lines


# ---------------------------------------------------------------------------
# the sweep
# ---------------------------------------------------------------------------

def sweep(repo: str, window_hours: int, ledger_path: Path, dry: bool,
          now: dt.datetime) -> tuple[int, list[str]]:
    """File one issue per unfiled main-pipeline failure; append each to the ledger.

    -> (exit_code, lines). 2 only when the pipeline state could not be read at all.
    """
    lines: list[str] = []
    ledger = read_ledger(ledger_path)
    # One convergence pass per sweep (issue #1054): rows filed by the old extractor kept the
    # `Makefile:<line>: ` form; a sweep normalises the stored ledger to the uniform bare target,
    # exactly the form every sibling row and every reproduction command already uses. A ledger
    # that is already uniform is not rewritten — no churn, run ids untouched (rule 3b).
    normalised = normalize_ledger_targets(ledger)
    if normalised and not dry:
        ledger_path.write_text(json.dumps(ledger, indent=2) + "\n", encoding="utf-8")
        lines.append(f"targets normalised on {normalised} row(s): the `Makefile:<line>: ` form "
                     "became the bare target (issue #1054)")
    known = ledger_run_ids(ledger)
    try:
        runs = main_pipeline_failures(repo, window_hours, now)
        already = open_failure_issue_runs(repo) if runs else set()
    except RuntimeError as exc:
        print(f"pipeline-failure-issue: READ FAILED: {exc}", file=sys.stderr)
        return 2, [f"read-failed: {exc}"]

    filed = 0
    for run in sorted(runs, key=lambda r: r["databaseId"]):
        rid = int(run["databaseId"])
        if rid in known:
            continue
        if rid in already:
            lines.append(f"skip run {rid}: an open issue already carries its marker")
            if not dry:
                append_ledger(ledger_path, ledger, {
                    "run_id": rid, "workflow": run.get("workflowName"),
                    "job": None, "head_sha": run.get("headSha"), "run_url": run.get("url"),
                    "created_utc": run.get("createdAt"), "filed_utc": now.isoformat(),
                    "targets": [], "issue_number": None, "issue_url": None,
                    "fix_pr": None, "guard": None,
                    "note": "filed before the ledger existed (marker-matched)",
                })
                known.add(rid)
            continue
        try:
            jobs = failed_jobs(repo, rid)
        except RuntimeError as exc:
            lines.append(f"run {rid}: jobs unreadable: {exc}")
            continue
        for job in jobs:
            block, region, log_error = job_failure(repo, job)
            # GitHub's own verdict on WHICH step ended the job (issue #1098): quoted beside the
            # block, and named on the issue when the block yields no `make` target.
            steps = failing_step_names(job)
            targets = failed_make_targets(block)
            title_job = job.get("name") or "?"
            if dry:
                lines.append(
                    f"WOULD FILE: run {rid} job {title_job} targets={targets or '-'} "
                    f"steps={steps or '-'} region={region or '-'} "
                    f"error_lines={len(block) or log_error}")
                continue
            issue = file_issue(repo, run, job, block, targets, log_error, now,
                               steps=steps, region=region)
            append_ledger(ledger_path, ledger, {
                "run_id": rid, "workflow": run.get("workflowName"),
                "job": title_job, "head_sha": run.get("headSha"), "run_url": run.get("url"),
                "created_utc": run.get("createdAt"), "filed_utc": now.isoformat(),
                "targets": targets, "issue_number": issue["number"],
                "issue_url": issue["url"], "fix_pr": None, "guard": None,
                "undiagnosed": log_error,
                # Additive keys (rule 3b): the diagnosis names the step GitHub marked bad and the
                # log region the quoted lines were taken from (issue #1098).
                "failing_steps": steps, "error_region": region,
                # THE DIAGNOSIS IS RECORDED IN THE ROW, not only in the issue body (issue #1136).
                # A filed row whose log read succeeded stored `undiagnosed: None` and NO error
                # block, so the ledger could not say whether ANY reader had ever diagnosed it:
                # `rediagnose_pending` would re-fetch a row that was already diagnosed in this
                # very sweep (and annotate its own issue), while a row stamped with `fix_pr` +
                # `guard` and no block looked complete. Scrubbed through the SAME redactor as the
                # issue body (rule 3f) — the ledger is a tracked file.
                "error_excerpt": redact("\n".join(block))[0] if block else None,
            })
            known.add(rid)
            filed += 1
            lines.append(f"FILED {issue['url']} (run {rid}, job {title_job}, "
                         f"targets={targets or '-'}, steps={steps or '-'}, "
                         f"region={region or '-'}, log_error={log_error or 'no'})")
    # The re-diagnosis pass (issue #969): every still-undiagnosed row gets its log re-read on
    # THIS sweep — including a row filed UNDIAGNOSED moments ago above (the in-memory ledger
    # already holds it), so a transient log outage is repaired within the same sweep.
    lines.extend(rediagnose_undiagnosed(repo, ledger, ledger_path, dry, now))
    # The stamp pass (issue #1099): every row a MERGED fix PR closed gets its
    # `fix_pr` + `guard` raised append-only, so the §6r raise is a landed leg,
    # not keeper prose — and `make pipeline-failure-guard-check` stops seeing
    # stale nulls on closed issues. It runs AFTER re-diagnosis (a row repaired
    # this same sweep is still un-attributed) and rides the same landing.
    lines.extend(stamp_merged_fix_prs(repo, ledger, ledger_path, dry, now))
    # The PR-blockage pass (issue #1164): a `pull_request`-triggered run is invisible to the
    # master/schedule window above, yet a stale pin blocks EVERY open PR at the same step — a
    # larger outage than one red sweep. It files once per failure SHAPE shared by two or more
    # open PRs, then the guard tracks the row until a fix lands.
    if not already:
        try:
            already = open_failure_issue_runs(repo)
        except RuntimeError as exc:
            lines.append(f"pr-blockage: marker scan unreadable: {exc}")
    lines.extend(record_pr_blockages(repo, window_hours, ledger, ledger_path, dry, now,
                                     known, already))
    lines.append(f"pipeline-failure-issue: window={window_hours}h failures={len(runs)} "
                 f"filed={filed} ledger={ledger_path.name}")
    return 0, lines


# ---------------------------------------------------------------------------
# the ledger PR body (`make pipeline-failure-ledger-pr-body`)
# ---------------------------------------------------------------------------

def compose_ledger_pr_body(ledger_path: Path, run_url: str) -> str:
    """Body for the ledger-update PR (issue #802). Generated artifact: like the architecture PR
    body, it implements no issue and therefore carries NO closing keyword (rule 6e) — the issues
    it records are referenced (`refs #`), never closed here."""
    data = json.loads(ledger_path.read_text(encoding="utf-8"))
    entries = data.get("failures", [])
    parts = [
        "Generated ledger update (issue #802).",
        "",
        f"`make pipeline-failure-issue` ran on the scheduled sweep ({run_url}) and diagnosed the "
        "concluded-bad main-pipeline runs in its window; this PR commits the append-only entries "
        "it produced in `data/pipeline_failures.json` (rule 3b: append-only).",
        "",
        "| run | pipeline | job | issue |",
        "|---|---|---|---|",
    ]
    for entry in entries:
        issue = f"refs #{entry['issue_number']}" if entry.get("issue_number") else "marker-matched"
        jobs = entry.get("job") or ", ".join(entry.get("failed_jobs") or []) or "?"
        parts.append(f"| {entry['run_id']} | {entry.get('workflow')} | {jobs} | {issue} |")
    parts.append("")
    parts.append("Each issue is fixed in its own reviewed change; that change raises this ledger "
                 "row with its PR number and guard test, and "
                 "`make pipeline-failure-guard-check` refuses the close until it lands.")
    return "\n".join(parts) + "\n"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--repo", default=None,
                    help="owner/repo; required for the sweep, unused by --print-pr-body")
    # 192 h, not 24: the filer runs on the WEEKLY scheduled sweep (Wednesday). A 24 h window
    # would miss every failure that happened between two sweeps — the window must cover a full
    # cadence plus grace, and dedup (marker scan + ledger) makes the overlap harmless.
    ap.add_argument("--window-hours", type=int, default=192)
    ap.add_argument("--ledger", default=str(LEDGER_DEFAULT))
    ap.add_argument("--dry", action="store_true")
    ap.add_argument("--now", default=None, help="ISO8601Z override for the window (tests)")
    ap.add_argument("--print-pr-body", action="store_true",
                    help="print the ledger-update PR body from the ledger and exit (no gh calls)")
    # The attribution half (issue #1053): report the diagnosed rows that name no fix PR, and raise
    # ONE row on a claim that proves itself against GitHub and the tree.
    ap.add_argument("--attribute-report", action="store_true",
                    help="print every diagnosed row that names no fix PR, with why (no writes)")
    ap.add_argument("--attribute", action="store_true",
                    help="raise one ledger row on an attested fix PR (owes --run/--fix-pr/--guard/"
                         "--evidence)")
    ap.add_argument("--run", type=int, default=None, help="ledger run id to attribute")
    ap.add_argument("--fix-pr", type=int, default=None, help="the MERGED fix PR number")
    ap.add_argument("--guard", default="", help="tests/test_<guard>.py[::<test>]")
    ap.add_argument("--evidence", default="",
                    help="the checkable proof: a path:line, a file, or a make/python3/gh command")
    args = ap.parse_args(argv)
    if args.window_hours <= 0:
        print("pipeline-failure-issue: --window-hours must be > 0", file=sys.stderr)
        return 2
    if args.print_pr_body:
        try:
            sys.stdout.write(compose_ledger_pr_body(Path(args.ledger),
                                                    os.environ.get("RUN_URL", "")))
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            print(f"pipeline-failure-ledger-pr-body: {exc}", file=sys.stderr)
            return 2
        return 0
    if not args.repo:
        print("pipeline-failure-issue: --repo <owner/repo> is required for the sweep",
              file=sys.stderr)
        return 2
    now = (_ts(args.now) or dt.datetime.now(dt.timezone.utc)) if args.now \
        else dt.datetime.now(dt.timezone.utc)
    # The attribution half (issue #1053) runs instead of the sweep when asked: it reports the
    # diagnosed rows the stamp pass cannot reach, or raises ONE row on a proven claim.
    if args.attribute_report:
        try:
            ledger = read_ledger(Path(args.ledger))
        except RuntimeError as exc:
            print(f"pipeline-failure-attribute: {exc}", file=sys.stderr)
            return 2
        for line in report_unattributed(args.repo, ledger):
            print(line)
        return 0
    if args.attribute:
        if not (args.run and args.fix_pr and args.guard and args.evidence):
            print("pipeline-failure-attribute: --attribute owes --run <run-id> --fix-pr <merged "
                  "PR#> --guard tests/test_<guard>.py[::<test>] --evidence \"<path:line | make "
                  "target>\" — a claim with a missing part is never applied", file=sys.stderr)
            return ATTRIBUTION_REFUSED
        try:
            ledger = read_ledger(Path(args.ledger))
            lines = attribute_claim(args.repo, ledger, Path(args.ledger),
                                    {"run": args.run, "fix_pr": args.fix_pr,
                                     "guard": args.guard, "evidence": args.evidence}, now)
        except AttributionRefused as exc:
            print(f"pipeline-failure-attribute: REFUSED: {exc}", file=sys.stderr)
            return ATTRIBUTION_REFUSED
        except RuntimeError as exc:
            print(f"pipeline-failure-attribute: {exc}", file=sys.stderr)
            return 2
        for line in lines:
            print(line)
        return 0
    rc, lines = sweep(args.repo, args.window_hours, Path(args.ledger), args.dry, now)
    for line in lines:
        print(line)
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
