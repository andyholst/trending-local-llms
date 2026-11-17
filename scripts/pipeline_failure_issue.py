#!/usr/bin/env python3
"""Track the main CI after a failure: diagnose it from its logs and file the issue (issue #802).

The repo already alarms when a main pipeline is red (`make master-alarm`, `make sweep-alarm`) and
repairs red PRs (fix-bot's loop). What it never did is what a senior engineer does after a
failure: READ THE LOGS OF A FAILED MAIN-PIPELINE RUN, name the make target that failed, and turn
that diagnosis into a tracked issue that says how to reproduce it. Until this existed, a red
scheduled run (measured: qa-validate run 43106689969, the OpenSpec archive gate) produced an
email, not an artifact — the diagnosis was re-derived by whoever next opened the run page.

This is the filer half. It runs from `queued-alarm.yml` (weekly, Wednesday, like every other
scheduled sweep — the weekly-cadence pin) with the DEFAULT `github.token` (rule 6e: the owner PAT
cannot comment or open issues). For every main-pipeline failure inside the window that is not yet
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

Exit: 0 report-only (filing IS the action); 2 when the pipeline state itself could not be read
(a silent clean over an unreadable API is the defect rule 6d refuses).

Run: make pipeline-failure-issue REPO=<owner>/<repo> [WINDOW_HOURS=192] [DRY=1] [LEDGER=…]
Run: make pipeline-failure-ledger-pr-body RUN_URL=… [LEDGER=…]  (the ledger PR body, no gh calls)
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

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import bot_markers  # noqa: E402
import pr_body  # noqa: E402  (the five-section composer + the declared marker)
from scrub_log import redact  # noqa: E402  (rule 3f's redactor — the SAME seam)

LEDGER_DEFAULT = ROOT / "data" / "pipeline_failures.json"
LABEL = "tech-debt"

#: The MAIN pipelines (the ones AGENTS.md §6b names and the §8 guard table describes). A failure
#: in one of these after a merge to master or on its schedule is the state this tracks.
MAIN_PIPELINES = (
    "qa-validate.yml",
    "refresh-bot.yml",
    "issue-bot.yml",
    "issue-review-bot.yml",
    "architecture-bot.yml",
    "queued-alarm.yml",
)

#: A failure counts when it is CONCLUDED bad (a still-running or queued run belongs to
#: queued-alarm's own alarm, not to this filer).
BAD_CONCLUSIONS = ("failure", "cancelled")

#: Bounded extraction (the issue must carry a diagnosis, not a log dump).
MAX_LOG_TAIL_BYTES = 60_000
MAX_ERROR_LINES = 40

#: A still-failing re-read is bounded (issue #986): after this many consecutive still-failing
#: re-reads a row is stamped TERMINAL `log_expired` (loud, once) and the pending queue drains.
MAX_REDIAGNOSE_ATTEMPTS = 3

_ERROR_SHAPES = (
    "##[error]", "make: ***", "FAIL: ", "FAIL ", "FAILED", "Traceback (most recent call last)",
    "refused:", "REFUSED",
)


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


def extract_error_block(log_text: str) -> list[str]:
    """The bounded diagnosis: every error-shaped line, in order, capped (never the whole log)."""
    lines = log_text.splitlines()
    hits: list[str] = []
    for line in lines:
        if any(shape in line for shape in _ERROR_SHAPES):
            hits.append(line.rstrip()[:500])
    # De-duplicate while keeping order, then cap.
    seen: set[str] = set()
    out: list[str] = []
    for h in hits:
        if h in seen:
            continue
        seen.add(h)
        out.append(h)
        if len(out) >= MAX_ERROR_LINES:
            break
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

def compose_body(run: dict, job: dict, block: list[str], targets: list[str],
                 log_error: str | None, when: dt.datetime) -> str:
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
           if targets else "The log names no `make` target — the job step itself is the unit."),
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
               log_error: str | None, when: dt.datetime) -> dict:
    title = (f"tech-debt: {run.get('workflowName')} / {job.get('name')} failed "
             f"(run {run['databaseId']}"
             + (f", {' + '.join(targets[:3])}" if targets else "") + ")")
    body = compose_body(run, job, block, targets, log_error, when)
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


def rediagnose_undiagnosed(repo: str, ledger: dict, ledger_path: Path, dry: bool,
                           now: dt.datetime) -> list[str]:
    """Re-read the log of every still-UNDIAGNOSED ledger row and raise it APPEND-ONLY.

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
    """
    lines: list[str] = []
    pending = [e for e in ledger["failures"]
               if e.get("undiagnosed") and not e.get("rediagnosed_utc")
               and not e.get("log_expired")]
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
            block = extract_error_block(fetch_log(repo, match["databaseId"]))
        except RuntimeError as exc:
            lines.extend(_still_unreadable(entry, rid, ledger, ledger_path, dry, now,
                                           f"log still unreadable: {exc}"))
            continue
        if not block:
            lines.append(f"rediagnose run {rid}: log readable but names no error-shaped line "
                         "— row stays UNDIAGNOSED")
            continue
        targets = failed_make_targets(block)
        excerpt = redact("\n".join(block))[0]
        if dry:
            lines.append(f"WOULD RAISE run {rid} (job {match.get('name')}): "
                         f"error_lines={len(block)} targets+={targets or '-'}")
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
        ledger_path.write_text(json.dumps(ledger, indent=2) + "\n", encoding="utf-8")
        lines.append(f"REDIAGNOSED run {rid} (job {match.get('name')}): error block landed, "
                     f"targets={grown or '-'} — {ann}")
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
            block: list[str] = []
            log_error = None
            try:
                block = extract_error_block(fetch_log(repo, job["databaseId"]))
            except RuntimeError as exc:
                log_error = str(exc)
            targets = failed_make_targets(block)
            title_job = job.get("name") or "?"
            if dry:
                lines.append(
                    f"WOULD FILE: run {rid} job {title_job} targets={targets or '-'} "
                    f"error_lines={len(block) or log_error}")
                continue
            issue = file_issue(repo, run, job, block, targets, log_error, now)
            append_ledger(ledger_path, ledger, {
                "run_id": rid, "workflow": run.get("workflowName"),
                "job": title_job, "head_sha": run.get("headSha"), "run_url": run.get("url"),
                "created_utc": run.get("createdAt"), "filed_utc": now.isoformat(),
                "targets": targets, "issue_number": issue["number"],
                "issue_url": issue["url"], "fix_pr": None, "guard": None,
                "undiagnosed": log_error,
            })
            known.add(rid)
            filed += 1
            lines.append(f"FILED {issue['url']} (run {rid}, job {title_job}, "
                         f"targets={targets or '-'}, log_error={log_error or 'no'})")
    # The re-diagnosis pass (issue #969): every still-undiagnosed row gets its log re-read on
    # THIS sweep — including a row filed UNDIAGNOSED moments ago above (the in-memory ledger
    # already holds it), so a transient log outage is repaired within the same sweep.
    lines.extend(rediagnose_undiagnosed(repo, ledger, ledger_path, dry, now))
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
    rc, lines = sweep(args.repo, args.window_hours, Path(args.ledger), args.dry, now)
    for line in lines:
        print(line)
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
