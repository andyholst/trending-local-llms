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
rather than guessing at a cause. This script never fixes anything and never merges anything
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


def failed_make_targets(block: list[str]) -> list[str]:
    """The `make <target>` names the log itself shows as the failing commands (rule 6m: a gate
    is reached through make, so the reproduction command is `make <target>`)."""
    import re
    targets: list[str] = []
    for line in block:
        for m in re.finditer(r"\bmake ([a-z][a-z0-9-]+)", line):
            if m.group(1) not in targets:
                targets.append(m.group(1))
        for m in re.finditer(r"make: \*\*\* \[([^\]]+)\]", line):
            if m.group(1) not in targets:
                targets.append(m.group(1))
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
