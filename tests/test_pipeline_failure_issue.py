#!/usr/bin/env python3
"""The main-pipeline failure filer (issue #802, AGENTS.md rule 6r).

Drives the REAL `scripts/pipeline_failure_issue.py` end to end against a stub `gh` on PATH — an
EXTERNAL system, the only permitted stand-in (rule 6m): every decision (window, event filter,
error extraction, target parsing, scrubbing, marker, dedup, ledger) is executed by the product.
Nothing here replaces the logic under test.

The failures this locks (measured, the state that earned issue #802): qa-validate run 43314856961
and refresh-bot run 43329124945 were red on `master` for hours and NO artifact carried their
error text — the diagnosis existed only in run logs nobody re-opened. The filer must turn every
concluded-bad main-pipeline run (push-to-master or schedule) into a `tech-debt` issue carrying
the log's OWN error block, and the ledger + guard gate must keep it fixed.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path
import datetime as dt

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import pipeline_failure_issue as F  # noqa: E402  (imported for the pure halves only)
import bot_markers as bm  # noqa: E402

FILER = ROOT / "scripts" / "pipeline_failure_issue.py"
QUEUE_WF = ROOT / ".github" / "workflows" / "queued-alarm.yml"
QA_WF = ROOT / ".github" / "workflows" / "qa-validate.yml"
MAKEFILE = ROOT / "Makefile"
COMMITTED_LEDGER = ROOT / "data" / "pipeline_failures.json"

REPO = "octo/repo"
#: A fixed "now" so the window is arithmetic, not wall-clock (a date-relative fixture ages out —
#: the issue #88 lesson).
NOW = "2026-11-11T22:00:00Z"
#: A FAKE credential planted in the stub log; NOUS_API_KEY is one of scrub_log's SECRET_VARS, so
#: the filer's redactor must mask it in every spelling before any of it reaches an issue body.
FAKE_SECRET = "fake-secret-value-1"  # NOT a credential SHAPE (nerve_key_check, rule 3e):
# scrub_log redacts it by NAME from the environment, which is exactly what the test verifies.

#: The canned qa-validate.yml runs: one push-to-master failure (in window), one success, one
#: manual dispatch (a collaborator's act, never tracked), one failure OUT of the window, and one
#: scheduled cancellation (a dropped cron — tracked like a failure).
RUNS_QA = [
    {"databaseId": 100, "workflowName": "qa-validate.yml", "name": "fix", "headBranch": "master",
     "headSha": "a" * 40, "event": "push", "createdAt": "2026-11-11T20:00:00Z",
     "conclusion": "failure", "status": "completed",
     "url": "https://github.com/octo/repo/actions/runs/100"},
    {"databaseId": 101, "workflowName": "qa-validate.yml", "name": "ok", "headBranch": "master",
     "headSha": "b" * 40, "event": "push", "createdAt": "2026-11-11T20:30:00Z",
     "conclusion": "success", "status": "completed",
     "url": "https://github.com/octo/repo/actions/runs/101"},
    {"databaseId": 102, "workflowName": "qa-validate.yml", "name": "manual", "headBranch": "master",
     "headSha": "c" * 40, "event": "workflow_dispatch", "createdAt": "2026-11-11T20:40:00Z",
     "conclusion": "failure", "status": "completed",
     "url": "https://github.com/octo/repo/actions/runs/102"},
    {"databaseId": 103, "workflowName": "qa-validate.yml", "name": "old", "headBranch": "master",
     "headSha": "d" * 40, "event": "push", "createdAt": "2026-11-01T10:00:00Z",
     "conclusion": "failure", "status": "completed",
     "url": "https://github.com/octo/repo/actions/runs/103"},
    {"databaseId": 104, "workflowName": "qa-validate.yml", "name": "sweep", "headBranch": "master",
     "headSha": "e" * 40, "event": "schedule", "createdAt": "2026-11-11T19:00:00Z",
     "conclusion": "cancelled", "status": "completed",
     "url": "https://github.com/octo/repo/actions/runs/104"},
]

JOBS_100 = {"jobs": [
    {"databaseId": 900, "name": "validate", "conclusion": "failure"},
    {"databaseId": 901, "name": "live-smoke", "conclusion": "success"}]}
JOBS_104 = {"jobs": [{"databaseId": 904, "name": "alarm", "conclusion": "cancelled"}]}

#: A job log with error-shaped lines (dedupable), a filler line, and the planted secret — the
#: exact shape a real runner log has (2026-11-11T…Z prefixes) including a secret that leaked.
LOG_TEXT = """2026-11-11T20:04:00Z ##[group]Run make validate
2026-11-11T20:04:01Z with: python3 scripts/validate.py --only data
2026-11-11T20:05:00Z warning: an unrelated warning line
2026-11-11T20:06:00Z ##[error]The process '/usr/bin/make' failed with exit code 2
2026-11-11T20:06:00Z make: *** [validate] Error 1
2026-11-11T20:06:00Z make: *** [validate] Error 1
2026-11-11T20:06:01Z Traceback (most recent call last):
2026-11-11T20:06:01Z ValueError: model bonsai-2-27b lost a measurement
2026-11-11T20:06:02Z the auth header was Bearer fake-secret-value-1 and it printed here
2026-11-11T20:06:03Z ##[error]Process completed with exit code 2.
"""

#: The measured shape of qa-validate run 45240782844, which filed #1459: earlier regions hold a
#: PASSING module's chatter, and the LAST `##[error]` region — a thin CI shell step, not a test
#: module — holds only the two lines that diagnose the run. Issue #1466: those two lines must be
#: quoted FIRST, with the chatter after an explicit filler marker.
THIN_REGION_LOG = "\n".join([
    "2026-11-23T18:50:40Z ##[group]Run make test",
    "2026-11-23T18:50:41Z   FAIL: m1: engines not ordered newest-date-first",
    "2026-11-23T18:50:42Z PASSED 199 | FAILED 0",
    "2026-11-23T18:50:43Z ##[endgroup]",
    "2026-11-23T18:50:44Z ##[group]Run set -euo pipefail",
    '2026-11-23T18:50:45Z echo "[merge-tree-index] FAIL: the index is stale on master + this PR."',
    "2026-11-23T18:50:46Z ##[error]Process completed with exit code 1.",
    "2026-11-23T18:50:47Z ##[endgroup]",
]) + "\n"

#: A failing region that genuinely HOLDS the diagnosis: EVERY error-shaped line is inside it, so
#: nothing is filler and the block keeps today's order byte-for-byte.
REGION_HOLDS_LOG = "\n".join([
    "2026-11-23T18:50:44Z ##[group]Run make openspec-check",
    "2026-11-23T18:50:45Z [openspec-index] FAIL OPENSPEC.md is stale or missing (2 active)",
    "2026-11-23T18:50:46Z make: *** [Makefile:367: openspec-index-check] Error 1",
    "2026-11-23T18:50:47Z ##[error]Process completed with exit code 2.",
    "2026-11-23T18:50:48Z ##[endgroup]",
]) + "\n"

STUB_GH = """#!/usr/bin/env bash
# Stub `gh` for tests/test_pipeline_failure_issue.py: canned answers keyed off the subcommand,
# everything it files captured under $PIPESTUB_DIR. The product under test never sees a mock —
# only this external stand-in for the GitHub API (rule 6m).
set -uo pipefail
d="$PIPESTUB_DIR"
bump() { local n; n=$(cat "$d/$1" 2>/dev/null || echo 0); n=$((n+1)); echo "$n" > "$d/$1"; echo "$n"; }
case "$1" in
  run)
    case "$2" in
      list)
        if [ -e "$d/runlist-fail" ]; then echo "stub gh: run list refused (502)" >&2; exit 1; fi
        wf=""; ev=""; prev=""
        for a in "$@"; do
          [ "$prev" = "--workflow" ] && wf="$a"
          [ "$prev" = "--event" ] && ev="$a"
          prev="$a"
        done
        # An event-filtered read (the PR-blockage pass, issue #1164) has its OWN fixture: the
        # master/schedule fixture must never be mistaken for a `pull_request`-triggered run list.
        f="$d/runs-${wf//./_}.json"
        [ -n "$ev" ] && f="$d/runs-${wf//./_}-${ev}.json"
        if [ -f "$f" ]; then cat "$f"; else echo "[]"; fi ;;
      view)
        f="$d/jobs-$3.json"
        if [ -f "$f" ]; then cat "$f"; else echo '{"jobs": []}'; fi ;;
      *) echo "stub gh: unhandled: $*" >&2; exit 1 ;;
    esac ;;
  issue)
    case "$2" in
      list)
        if [ -e "$d/issuelist-fail" ]; then echo "stub gh: issue list refused" >&2; exit 1; fi
        if [ -f "$d/issues.json" ]; then cat "$d/issues.json"; else echo "[]"; fi ;;
      create)
        title=""; body=""; prev=""
        for a in "$@"; do
          if [ "$prev" = "--title" ]; then title="$a"; fi
          if [ "$prev" = "--body" ]; then body="$a"; fi
          prev="$a"
        done
        n=$(bump create-count)
        printf '%s' "$title" > "$d/title-$n.txt"
        printf '%s' "$body" > "$d/body-$n.txt"
        echo "https://github.com/octo/repo/issues/424${n}" ;;
      comment)
        # `gh issue comment <number> --repo <repo> --body <text>` — capture, never no-op.
        number="$3"; body=""; prev=""
        for a in "$@"; do
          if [ "$prev" = "--body" ]; then body="$a"; fi
          prev="$a"
        done
        m=$(bump comment-count)
        printf '%s' "$body" > "$d/comment-$number-$m.txt"
        echo "https://github.com/octo/repo/issues/$number#issuecomment-${m}" ;;
      view)
        if [ -f "$d/issue-view-$3.json" ]; then cat "$d/issue-view-$3.json"
        elif [ -f "$d/issue-state.json" ]; then cat "$d/issue-state.json"
        else echo '{"labels": [{"name": "tech-debt"}]}'; fi ;;
      edit) exit 0 ;;
      *) echo "stub gh: unhandled: $*" >&2; exit 1 ;;
    esac ;;
  pr)
    case "$2" in
      list)
        # `gh pr list --state open --json headRefName` — the open PRs a blockage can block
        # (issue #1164). Absent fixture = no open PRs, so nothing is recorded.
        if [ -f "$d/open-prs.json" ]; then cat "$d/open-prs.json"; else echo "[]"; fi ;;
      view)
        # `gh pr view <n> --repo <repo> --json number,title,mergedAt,files` — the stamp pass
        # (issue #1099) reads each closing PR's merged state and its diff through this.
        f="$d/pr-$3.json"
        if [ -f "$f" ]; then cat "$f"
        else echo '{"number": '"$3"', "mergedAt": null, "files": []}'; fi ;;
      *) echo "stub gh: unhandled: $*" >&2; exit 1 ;;
    esac ;;
  api)
    # `gh api repos/.../issues/<n>/comments ...` — the thread the re-diagnosis dedup reads.
    # Serve a canned comment list (each line one JSON object) or an empty thread.
    if [[ " $* " == *"/comments"* ]]; then
      # bash-native extraction, no sed backreferences (which mangle through this test's write path)
      url="$2"; num=""
      [[ "$url" =~ /issues/([0-9]+)/comments ]] && num="${BASH_REMATCH[1]}"
      if [ -n "$num" ] && [ -f "$d/thread-$num.json" ]; then cat "$d/thread-$num.json"; fi
      exit 0
    fi
    if [ -e "$d/log-fail" ]; then echo "stub gh: job logs unavailable (502)" >&2; exit 1; fi
    if [ -e "$d/log-escape" ]; then
      # gh's measured refusal (issue #923): a plain logs fetch on an escape-bearing log is
      # refused verbatim; ONLY a call carrying gh's own suggested flag gets the log.
      case " $* " in
        *" --allow-escape-sequences "*) cat "$d/log-escape.txt" ;;
        *) echo "gh: the response contains terminal escape sequences; pass --allow-escape-sequences to output it anyway" >&2; exit 1 ;;
      esac
      exit 0
    fi
    cat "$d/log.txt" ;;
  *) echo "stub gh: unhandled: $*" >&2; exit 1 ;;
esac
"""

_checks_passed = 0
_checks_failed = 0


def check(name: str, ok: bool, detail: str = "") -> None:
    global _checks_passed, _checks_failed
    if ok:
        _checks_passed += 1
        print(f"  ok   {name}")
    else:
        _checks_failed += 1
        print(f"  FAIL {name}" + (f"\n       {detail}" if detail else ""))


def make_scene(tmp: Path, canned: dict) -> dict:
    """Build the stub bin + canned data; return the env the product runs under."""
    bindir = tmp / "bin"
    bindir.mkdir(parents=True, exist_ok=True)
    stub = bindir / "gh"
    stub.write_text(STUB_GH)
    stub.chmod(0o755)
    canned_dir = tmp / "canned"
    canned_dir.mkdir(parents=True, exist_ok=True)
    for name, content in canned.items():
        text = content if isinstance(content, str) else json.dumps(content)
        (canned_dir / name).write_text(text)
    env = dict(os.environ)
    env["PATH"] = f"{bindir}{os.pathsep}{env['PATH']}"
    env["PIPESTUB_DIR"] = str(canned_dir)
    # A live credential the redactor reads BY NAME (rule 3e): the planted FAKE_SECRET in the
    # canned log is this variable's value, and it must never reach an issue body.
    env["NOUS_API_KEY"] = FAKE_SECRET
    env.pop("GITHUB_REPOSITORY", None)
    return env


def run_filer(env: dict, ledger: Path, *extra: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(FILER), "--repo", REPO, "--ledger", str(ledger), "--now", NOW,
         *extra],
        capture_output=True, text=True, timeout=120, env=env)


BASE_CANNED = {
    "runs-qa-validate_yml.json": RUNS_QA,
    "jobs-100.json": JOBS_100,
    "jobs-104.json": JOBS_104,
    "log.txt": LOG_TEXT,
    "issues.json": [],
}


def test_filing_diagnoses_every_failure_with_the_log_error_block() -> None:
    print("\nfiling: every concluded-bad push-to-master/schedule main-pipeline run files one issue")
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        env = make_scene(tmp, BASE_CANNED)
        ledger = tmp / "ledger.json"
        proc = run_filer(env, ledger)
        check("exit 0", proc.returncode == 0, proc.stderr)
        count = int((tmp / "canned" / "create-count").read_text().strip())
        check("exactly TWO issues filed (100 push-master, 104 schedule; 101/102/103 refused)",
              count == 2, f"create-count={count}\n{proc.stdout}")
        # Filed oldest-first: pick each filed body by its own run-id marker, never by position.
        bodies = {p.name: p.read_text() for p in (tmp / "canned").glob("body-*.txt")}
        titles = {p.name: p.read_text() for p in (tmp / "canned").glob("title-*.txt")}
        body = next(b for b in bodies.values() if "run=100" in b)
        title = next(t for t in titles.values() if "run 100" in t)
        check("title names the workflow, job and run",
              "qa-validate.yml" in title and "validate" in title, title)
        check("body carries the run-id marker", "<!-- pipeline-run-failure: " in body
              and "run=100" in body, "")
        marker = bm.read_marker(body, "queued-alarm", "failure")
        check("the marker parses through the shared parser (rule 6j)",
              marker is not None and marker["run"] == "100", str(marker))
        check("body carries the log's error block (deduped)",
              "make: *** [validate] Error 1" in body
              and body.count("make: *** [validate] Error 1") == 1, "")
        check("body names the reproduction from the log", "make validate" in body, "")
        for section in ("## Why", "## What", "## How", "## Benefits", "## Technical Solution"):
            check(f"body has the message-pattern section {section}", section in body, "")
        check("sections are in order", body.find("## Why") < body.find("## What")
              < body.find("## How") < body.find("## Benefits") < body.find("## Technical Solution"),
              "")
        check("the planted secret NEVER reaches the body (scrubbed)",
              FAKE_SECRET not in body, "SECRET LEAKED INTO ISSUE BODY")
        check("the scrubbed line shows the mask instead", body.count("***") >= 1, "")
        # The ledger records both runs with their filing.
        data = json.loads(ledger.read_text())
        rows = {e["run_id"]: e for e in data["failures"]}
        check("ledger records run 100 and run 104", set(rows) == {100, 104}, str(sorted(rows)))
        check("ledger row links the filed issue", rows[100]["issue_number"] is not None
              and rows[100]["fix_pr"] is None and rows[100]["guard"] is None, str(rows[100]))
        check("ledger row names the failing job and targets",
              rows[100]["job"] == "validate" and rows[100]["targets"] == ["validate"],
              str(rows[100]))
        check("the scheduled cancellation is tracked like a failure",
              rows[104]["job"] == "alarm", str(rows[104]))
        # Issue #1136: THE DIAGNOSIS IS RECORDED IN THE ROW. A filed row stored the error block
        # only in the issue body, so the ledger could not tell whether the run had EVER been
        # diagnosed — `rediagnose_pending` selected every freshly-filed row (it carries
        # `undiagnosed: None`) and re-fetched and self-annotated it in the same sweep.
        check("the filed row carries its own error block",
              "make: *** [validate] Error 1" in (rows[100].get("error_excerpt") or ""),
              str(rows[100])[:400])
        check("the row's diagnosis is SCRUBBED (the ledger is a tracked file, rule 3f)",
              FAKE_SECRET not in (rows[100].get("error_excerpt") or ""),
              "SECRET LEAKED INTO THE LEDGER ROW")
        check("a row diagnosed at filing is NOT re-fetched by the same sweep's re-diagnosis pass",
              "REDIAGNOSED run 100" not in proc.stdout and "REDIAGNOSED run 104" not in proc.stdout,
              proc.stdout)
        check("no self-annotation comment was written for a freshly filed row",
              not list((tmp / "canned").glob("comment-*.txt")),
              str([q.name for q in (tmp / "canned").glob("comment-*.txt")]))


def test_ledger_and_marker_dedup_file_one_run_once_ever() -> None:
    print("\ndedup: the ledger AND a --state all marker scan both remember a filed run")
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        env = make_scene(tmp, BASE_CANNED)
        ledger = tmp / "ledger.json"
        first = run_filer(env, ledger)
        check("first run files", first.returncode == 0 and
              int((tmp / "canned" / "create-count").read_text().strip()) == 2, first.stdout)
        second = run_filer(env, ledger)
        check("re-run files NOTHING (ledger run-ids)", second.returncode == 0 and
              int((tmp / "canned" / "create-count").read_text().strip()) == 2, second.stdout)
    # A CLOSED marker issue (fix merged quickly) must also stop a re-file next sweep — the
    # marker scan reads --state all, not just open issues.
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        canned = dict(BASE_CANNED)
        canned["issues.json"] = [{
            "number": 777, "title": "already filed",
            "state": "CLOSED",
            "body": "<!-- pipeline-run-failure: 2026-11-11T20:59:00Z run=100 -->",
        }]
        env = make_scene(tmp, canned)
        ledger = tmp / "ledger.json"
        proc = run_filer(env, ledger)
        created = int((tmp / "canned" / "create-count").read_text().strip()) if \
            (tmp / "canned" / "create-count").exists() else 0
        check("run 100 (CLOSED marker issue) files again: NO", created == 1,
              f"create-count={created}\n{proc.stdout}")
        data = json.loads(ledger.read_text())
        row100 = next(e for e in data["failures"] if e["run_id"] == 100)
        check("marker-matched run still lands in the ledger (with a note)",
              "marker-matched" in (row100.get("note") or ""), str(row100))


def test_undiagnosed_filing_is_loud_never_a_skip() -> None:
    print("\nundiagnosed: an unreadable log files an issue SAYING the log could not be read")
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        canned = dict(BASE_CANNED)
        canned["log-fail"] = ""  # the api branch exits 1
        env = make_scene(tmp, canned)
        ledger = tmp / "ledger.json"
        proc = run_filer(env, ledger)
        check("exit 0 (filing still happens)", proc.returncode == 0, proc.stderr)
        bodies = {p.name: p.read_text() for p in (tmp / "canned").glob("body-*.txt")}
        body = next(b for b in bodies.values() if "run=100" in b)
        check("body names the log failure", "could not be read" in body, body[:200])
        data = json.loads(ledger.read_text())
        check("ledger records every entry as undiagnosed",
              all(e["undiagnosed"] for e in data["failures"]), str(data["failures"]))
        check("and names NO error block — the row stays in the re-diagnosis pending set (issue #1136)",
              all(e.get("error_excerpt") is None for e in data["failures"]), str(data["failures"]))


def test_an_escape_refused_log_is_diagnosed_on_the_flag_retry() -> None:
    print("\nescape retry: gh's refusal is answered by gh's own suggested flag, not by UNDIAGNOSED (issue #923)")
    canned = {
        "runs-qa-validate_yml.json": [
            {"databaseId": 110, "workflowName": "qa-validate.yml", "name": "escape-run",
             "headBranch": "master", "headSha": "f" * 40, "event": "push",
             "createdAt": "2026-11-12T19:00:00Z", "conclusion": "failure", "status": "completed",
             "url": "https://github.com/octo/repo/actions/runs/110"}],
        "jobs-110.json": {"jobs": [{"databaseId": 910, "name": "implement", "conclusion": "failure"}]},
        # A marker file (empty content) arms the refusal branch; the colored log is the answer
        # ONLY to the flag-carrying call — the exact live shape gh produced for 12 real failures.
        "log-escape": "",
        "log-escape.txt": (
            "2026-11-12T19:04:00Z \x1b[31;1m##[error]\x1b[0mscripts/fix_loop.sh died: boom\n"
            "2026-11-12T19:04:01Z \x1b[33mmake: *** [implement-issue] Error 1\x1b[0m\n"
            "2026-11-12T19:04:02Z \x1b]0;runner window title\x07the auth header was Bearer fake-secret-value-1\n"
            "2026-11-12T19:04:03Z \x1b[2J\x1b[1H\x1b[31;1m##[error]Process completed with exit code 2.\x1b[0m\n"
        ),
        "issues.json": [],
    }
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        env = make_scene(tmp, canned)
        ledger = tmp / "ledger.json"
        proc = run_filer(env, ledger)
        check("exit 0", proc.returncode == 0, proc.stderr)
        count = int((tmp / "canned" / "create-count").read_text().strip())
        check("exactly ONE issue filed", count == 1, f"create-count={count}\n{proc.stdout}")
        body = (tmp / "canned" / "body-1.txt").read_text()
        check("the colored log's error lines landed in the body",
              "make: *** [implement-issue] Error 1" in body and "boom" in body,
              body[:400])
        check("NO escape character anywhere in the filed body", "\x1b" not in body,
              "ESCAPE BYTE LEAKED INTO ISSUE BODY")
        check("the gh refusal text is NOT in the body (the log WAS read)",
              "terminal escape sequences" not in body, "")
        check("the body is a diagnosis, not UNDIAGNOSED",
              "UNDIAGNOSED" not in body and "could not be read" not in body, body[:400])
        check("the planted secret is still scrubbed out", FAKE_SECRET not in body,
              "SECRET LEAKED INTO ISSUE BODY")
        data = json.loads(ledger.read_text())
        row = {e["run_id"]: e for e in data["failures"]}[110]
        check("the ledger row carries the diagnosis (job + reproduction target)",
              row["job"] == "implement" and "implement-issue" in row["targets"], str(row))


def test_strip_terminal_escapes_leaves_plain_text_intact() -> None:
    print("\nstrip helper: sequences removed, ordinary text untouched")
    s = F.strip_terminal_escapes
    check("CSI color pair removed", s("\x1b[31;1mred\x1b[0m") == "red", repr(s("\x1b[31;1mred\x1b[0m")))
    check("OSC window title removed (BEL-terminated)", s("\x1b]0;title\x07after") == "after", "")
    check("CSI private sequences removed", s("\x1b[?25lcursor\x1b[?25h") == "cursor", "")
    check("erase/position CSI removed", s("\x1b[2Kline\x1b[1A") == "line", "")
    check("a bare bracket-number with NO ESC is NOT touched",
          s("plain [31m text stays") == "plain [31m text stays", "")
    check("a lone ESC is removed", s("lone \x1b ESC") == "lone  ESC", "")
    check("log prose survives byte-identical",
          s("2026-11-12T19:04:01Z make: *** [x] Error 1\n")
          == "2026-11-12T19:04:01Z make: *** [x] Error 1\n", "")


def test_read_failures_exit_2_never_a_fake_clean() -> None:
    print("\nread state: an unreadable pipeline state exits 2, not a silent 0")
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        canned = dict(BASE_CANNED)
        canned["runlist-fail"] = ""
        env = make_scene(tmp, canned)
        proc = run_filer(env, tmp / "ledger.json")
        check("run list refused -> exit 2 naming READ FAILED",
              proc.returncode == 2 and "READ FAILED" in proc.stderr, f"{proc.returncode}\n{proc.stderr}")
        check("nothing was filed", not (tmp / "canned" / "create-count").exists(), "")
        check("no ledger was written", not (tmp / "ledger.json").exists(), "")


def test_dry_run_previews_without_writing_anything() -> None:
    print("\ndry: --dry prints WOULD FILE and files/writes nothing")
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        env = make_scene(tmp, BASE_CANNED)
        ledger = tmp / "ledger.json"
        proc = run_filer(env, ledger, "--dry")
        check("exit 0 with WOULD FILE lines", proc.returncode == 0
              and "WOULD FILE" in proc.stdout, proc.stdout)
        check("no issue was created", not (tmp / "canned" / "create-count").exists(), "")
        check("no ledger was written", not ledger.exists(), "")


def test_pure_halves_extract_targets_dedupe_and_cap() -> None:
    print("\npure halves: extraction is bounded, deduped, and reads the make targets the log names")
    block = F.extract_error_block(LOG_TEXT)
    joined = "\n".join(block)
    check("error lines are deduplicated",
          joined.count("make: *** [validate] Error 1") == 1, str(block))
    check("non-error filler lines are not collected",
          not any("unrelated warning" in line for line in block), str(block))
    check("targets come from the log itself",
          F.failed_make_targets(block) == ["validate"], str(block))
    many = "\n".join(f"##[error] distinct failure number {i}" for i in range(200))
    capped = F.extract_error_block(many)
    check("the block is capped (never a log dump)", len(capped) == F.MAX_ERROR_LINES,
          str(len(capped)))
    check("a make: *** [name] line yields the target name",
          F.failed_make_targets(["make: *** [architecture-check] Error 2"]) == ["architecture-check"],
          "")


def test_a_thin_failing_region_is_quoted_before_earlier_chatter() -> None:
    print("\n#1466: the failing region's own lines come FIRST; filler is marked, never ahead")
    block = F.extract_error_block(THIN_REGION_LOG)
    check("the two diagnosing lines open the block",
          len(block) >= 2 and "merge-tree-index" in block[0] and "##[error]" in block[1],
          str(block[:3]))
    check("no passing-module chatter precedes the diagnosis",
          not any(("PASSED 199" in line or "FAIL: m1" in line) for line in block[:2]), str(block[:2]))
    marker = next((i for i, line in enumerate(block) if line.startswith("[filer]")), None)
    check("an explicit [filer] filler marker separates the region from the rest",
          marker == 2, str(block))
    check("the marker names how many filler lines follow and the region they are NOT from",
          marker is not None and "2 further error-shaped line(s)" in block[marker]
          and "Run set -euo pipefail" in block[marker],
          block[marker] if marker is not None else "")
    check("every chatter line sits AFTER the marker",
          marker is not None and all(i > marker for i, line in enumerate(block)
                                     if "PASSED 199" in line or "FAIL: m1" in line), str(block))
    check("the block stays within the cap", len(block) <= F.MAX_ERROR_LINES, str(len(block)))
    check("the filler marker is never read as a reproduction command",
          F.failed_make_targets(block) == [], str(F.failed_make_targets(block)))


def test_a_region_holding_the_diagnosis_keeps_today_s_order() -> None:
    print("\n#1466: a region that genuinely holds the diagnosis keeps today's order, no filler")
    block = F.extract_error_block(REGION_HOLDS_LOG)
    expected = [
        "2026-11-23T18:50:45Z [openspec-index] FAIL OPENSPEC.md is stale or missing (2 active)",
        "2026-11-23T18:50:46Z make: *** [Makefile:367: openspec-index-check] Error 1",
        "2026-11-23T18:50:47Z ##[error]Process completed with exit code 2.",
    ]
    check("the block is exactly the region's lines in log order", block == expected, str(block))
    check("no filler marker and no drop note are invented",
          not any(line.startswith("[filer]") for line in block), str(block))


def test_ledger_pr_body_is_generated_and_carries_no_closing_keyword() -> None:
    print("\nledger PR body: composed from the ledger, references issues, closes none (rule 6e)")
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        ledger = tmp / "ledger.json"
        ledger.write_text(json.dumps({"failures": [
            {"run_id": 100, "workflow": "qa-validate.yml", "job": "validate",
             "issue_number": "4241", "fix_pr": None, "guard": None},
            {"run_id": 104, "workflow": "qa-validate.yml", "job": "alarm",
             "issue_number": None, "fix_pr": None, "guard": None},
        ]}))
        env = make_scene(tmp, BASE_CANNED)
        proc = subprocess.run(
            ["make", "-C", str(ROOT), "pipeline-failure-ledger-pr-body",
             f"LEDGER={ledger}", "RUN_URL=https://example/actions/runs/7"],
            capture_output=True, text=True, timeout=120, env=env)
        check("make target prints the body", proc.returncode == 0, proc.stderr)
        body = proc.stdout
        check("body names the sweep run URL", "example/actions/runs/7" in body, body[:200])
        check("body tables the recorded runs with refs",
              "| 100 | qa-validate.yml | validate | refs #4241 |" in body
              and "marker-matched" in body, body)
        check("body carries NO closing keyword (it records issues, never closes them)",
              "loses #" not in body and "closes" not in body.lower(), body)


def test_wiring_rulebook_and_registry() -> None:
    print("\nwiring: Makefile, queued-alarm, qa-validate, marker registry, committed ledger")
    makefile = MAKEFILE.read_text()
    for target in ("pipeline-failure-issue:", "_pipeline-failure-issue:",
                   "pipeline-failure-guard-check:", "pipeline-failure-ledger-pr-body:"):
        check(f"Makefile defines {target}", target in makefile, "")
    queue = QUEUE_WF.read_text()
    check("queued-alarm runs the filer through the Makefile",
          "make pipeline-failure-issue" in queue, "")
    check("queued-alarm lands the ledger append as a PR through the ONE keeper seam (#869)",
          "make keeper-pr" in queue
          and "BODY_TARGET=pipeline-failure-ledger-pr-body" in queue, "")
    check("the ledger PR step fires only when the filer changed the ledger "
          "(the seam's nothing-to-land case is pinned by tests/test_keeper_pr.py)",
          "FILE=data/pipeline_failures.json" in queue
          and "BRANCH_PREFIX=ci/pipeline-failure-ledger" in queue, "")
    qa = QA_WF.read_text()
    check("qa-validate runs the guard as a step", "make pipeline-failure-guard-check" in qa, "")
    check("the filer marker is registered (rule 6j)",
          bm.REGISTRY.get("queued-alarm", {}).get("failure") == "pipeline-run-failure"
          and ("queued-alarm", "failure") in bm.WRITTEN, "")
    # The re-diagnosis annotation marker (issue #987) is REGISTERED (rule 6j): its AGENTS.md §6j
    # table row landed through an attended run (the rule 3c sign-off), so it moved from the
    # UNREGISTERED_OWED seam into REGISTRY + WRITTEN; the §6j table and the registry are pinned
    # equal by tests/test_bot_markers.py::test_agents_md_table_names_the_same_markers.
    check("the rediagnose annotation marker is REGISTERED (rule 6j, issue #987)",
          bm.REGISTRY.get("queued-alarm", {}).get("rediagnose") == bm.REDIAGNOSE_NAME
          and ("queued-alarm", "rediagnose") in bm.WRITTEN
          and bm.UNREGISTERED_OWED.get(bm.REDIAGNOSE_NAME) is None,
          f"{bm.REGISTRY.get('queued-alarm')} / owed={bm.UNREGISTERED_OWED}")
    check("the rediagnose marker's shape round-trips its writer and parser",
          bm.rediagnose_marker_run(bm.rediagnose_marker(
              dt.datetime(2026, 11, 15, 8, 0, tzinfo=dt.timezone.utc), 123)) == "123", "")
    sys.path.insert(0, str(ROOT / "scripts"))
    import master_alarm
    gates = (set(getattr(master_alarm, "GATES", ()))
             | set(getattr(master_alarm, "ALARM_ONLY", ()))
             | set(getattr(master_alarm, "KEEPER", ())))
    check("the guard is a named gate in the master_alarm registry",
          "pipeline-failure-guard-check" in gates, str(sorted(gates)))
    committed = json.loads(COMMITTED_LEDGER.read_text())
    rows = {e["run_id"]: e for e in committed["failures"]}
    check("the measured failure is seeded in the ledger (run ids, not prose)",
          43088760321 in rows, str(sorted(rows)))
    seed = rows[43088760321]
    check("the seed row carries the real chain: issue #800, fix PR #808, a real guard test",
          str(seed.get("issue_number")) == "800" and str(seed.get("fix_pr")) == "808"
          and seed.get("guard") == "tests/test_openspec_archive_check.py"
          and (ROOT / "tests" / "test_openspec_archive_check.py").exists(), str(seed))
    agents = (ROOT / "AGENTS.md").read_text()
    check("AGENTS.md carries rule 6r naming both make targets",
          "6r." in agents and "make pipeline-failure-issue" in agents
          and "make pipeline-failure-guard-check" in agents, "")
    check("AGENTS.md §8 names this test as the guard row",
          "tests/test_pipeline_failure_issue.py" in agents, "")


def test_the_module_docstring_names_the_dispatch_only_entry_point() -> None:
    print("\ndocstring: the filer's entry point is dispatch-only, with no weekly/Wednesday claim")
    source = FILER.read_text(encoding="utf-8")
    doc = source.split('"""')[1]
    check("the module docstring names the filer's entry point",
          "queued-alarm.yml" in doc, "")
    check("the module docstring states the entry point is dispatch-only (#1029)",
          "dispatch-only" in doc.lower(), doc[:200])
    check("the module docstring makes no weekly cadence claim",
          "weekly" not in doc.lower(), doc[:200])
    check("the module docstring names no Wednesday slot",
          "wednesday" not in doc.lower(), "")
    # Read the `on:` block structurally: the workflow's own comments legitimately say
    # "schedule" (they explain why there is none), so a substring scan is wrong.
    on_lines, inside = [], False
    for line in QUEUE_WF.read_text(encoding="utf-8").splitlines():
        if line.startswith("on:"):
            inside = True
            continue
        if inside:
            if line and not line[0].isspace():
                break
            on_lines.append(line)
    check("the workflow's own `on:` block agrees — no schedule trigger",
          not any(re.match(r"\s+schedule:\s*$", line) for line in on_lines),
          "\n".join(on_lines)[:200])


def _seed_ledger(tmp: Path, entries: list[dict]) -> Path:
    """Write a pre-existing ledger (a past filed run) so the sweep enters in the re-diagnosis
    state rather than filing."""
    ledger = tmp / "ledger.json"
    ledger.write_text(json.dumps({"failures": entries}))
    return ledger


UNDIAG_ROW = {
    "run_id": 100, "workflow": "qa-validate.yml", "job": "validate",
    "head_sha": "a" * 40, "run_url": "https://github.com/octo/repo/actions/runs/100",
    "created_utc": "2026-11-11T20:00:00Z", "filed_utc": "2026-11-11T21:00:00Z",
    "targets": [], "issue_number": "824", "issue_url": "https://github.com/octo/repo/issues/824",
    "fix_pr": None, "guard": None,
    "undiagnosed": "log fetch for job 900 failed twice: gh refused the escape-bearing log",
}
MARKER_MATCHED_ROW = {
    "run_id": 104, "workflow": "qa-validate.yml", "job": "alarm",
    "head_sha": "e" * 40, "run_url": "https://github.com/octo/repo/actions/runs/104",
    "created_utc": "2026-11-11T19:00:00Z", "filed_utc": "2026-11-11T21:00:00Z",
    "targets": [], "issue_number": None, "issue_url": None,
    "fix_pr": None, "guard": None,
    "note": "filed before the ledger existed (marker-matched)",
    # Issue #1136: the fixture states the diagnosis it really has — the shipped ledger's
    # marker-matched row (run 43088760321) DOES carry an `error_excerpt`. A row with NO error
    # block is `STAMPED_WITHOUT_DIAGNOSIS_ROW` below: the shape the old pending filter could not
    # see at all, and the shape the re-diagnosis pass must now fetch.
    "error_excerpt": "make: *** [Makefile:1384: sweep-alarm] Error 2",
}

# The measured shape of issue #1136, copied from data/pipeline_failures.json run 43147240875:
# stamped with a landed `fix_pr` + `guard` by a ledger PR, `undiagnosed: None` (the filer's own
# read SUCCEEDED, so the key stores null), and NO error block — so the old marker-key filter
# selected nothing and no pass could ever name the failure this row attributes a fix to.
STAMPED_WITHOUT_DIAGNOSIS_ROW = {
    "run_id": 777, "workflow": "queued-alarm.yml", "job": "sweep",
    "head_sha": "7" * 40, "run_url": "https://github.com/octo/repo/actions/runs/777",
    "issue_url": "https://api.github.com/repos/octo/repo/issues/55", "issue_number": 55,
    "created_utc": "2026-11-12T22:11:29Z", "filed_utc": "2026-11-12T22:11:29Z",
    "targets": ["openspec-check"], "undiagnosed": None,
    "stamp_utc": "2026-11-15T14:56:48Z", "stamp_note": "fix PR #922 merged 2026-11-14T19:49:37Z",
    "fix_pr": 922, "guard": "tests/test_owed_rows.py",
}


def test_rediagnose_pass_raises_a_still_undiagnosed_row_from_the_readable_log() -> None:
    print("\nrediagnose (#969): a planted UNDIAGNOSED row becomes diagnosed on the next sweep")
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        env = make_scene(tmp, BASE_CANNED)
        ledger = _seed_ledger(tmp, [dict(UNDIAG_ROW), dict(MARKER_MATCHED_ROW)])
        proc = run_filer(env, ledger)
        check("exit 0", proc.returncode == 0, proc.stderr)
        check("the pass names the raised run", "REDIAGNOSED run 100" in proc.stdout, proc.stdout)
        check("NO new issue is filed for a run the ledger already knows",
              not (tmp / "canned" / "create-count").exists(), proc.stdout)
        data = json.loads(ledger.read_text())
        row = {e["run_id"]: e for e in data["failures"]}[100]
        check("rediagnosed_utc stamped", bool(row.get("rediagnosed_utc")), str(row))
        check("error_excerpt carries the log's own block",
              "make: *** [validate] Error 1" in row.get("error_excerpt", ""), str(row)[:300])
        check("the planted secret is masked in the raised row (rule 3f redaction)",
              FAKE_SECRET not in row.get("error_excerpt", "")
              and "***" in row.get("error_excerpt", ""), row.get("error_excerpt", "")[:200])
        check("targets GROWN from the log (was [])", row.get("targets") == ["validate"], str(row))
        check("the original undiagnosed field is KEPT (rule 3b additive)",
              row.get("undiagnosed") == UNDIAG_ROW["undiagnosed"], str(row)[:300])
        check("fix_pr/guard stay null — attribution is each fix's own decision",
              row.get("fix_pr") is None and row.get("guard") is None, str(row))
        check("a note names the seam that raised it", "#969" in row.get("rediagnosis_note", ""),
              str(row))
        row104 = {e["run_id"]: e for e in data["failures"]}[104]
        # Issue #1136: the row is untouched because it ALREADY carries its diagnosis
        # (`error_excerpt`), not because a marker key is missing from it.
        check("a row that already carries its diagnosis is never re-fetched",
              "rediagnosed_utc" not in row104 and row104.get("error_excerpt"), str(row104))
        # Re-run: nothing left pending, nothing rewritten.
        before = ledger.read_text()
        second = run_filer(env, ledger)
        check("re-sweep raises nothing again (rediagnosed_utc ends the queue)",
              second.returncode == 0 and "REDIAGNOSED" not in second.stdout
              and ledger.read_text() == before, second.stdout)


def test_a_raise_annotates_the_cited_issue_once() -> None:
    print("\\nrediagnose annotation (#987): a raise posts ONE marker-deduplicated comment on the cited issue")
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        canned = dict(BASE_CANNED)
        # Issue 824's thread carries an unrelated comment (the original filing reply-ish), NO
        # pipeline-rediagnose marker — so the raise must post exactly one annotation.
        canned["thread-824.json"] = '{"id": 1, "createdAt": "2026-11-11T21:05:00Z", "body": "an unrelated note"}\n'
        env = make_scene(tmp, canned)
        ledger = _seed_ledger(tmp, [dict(UNDIAG_ROW)])
        proc = run_filer(env, ledger)
        check("exit 0", proc.returncode == 0, proc.stderr)
        check("the pass names the annotation", "annotated issue #824" in proc.stdout, proc.stdout)
        data = json.loads(ledger.read_text())
        row = data["failures"][0]
        check("the row is raised", bool(row.get("rediagnosed_utc")), str(row)[:200])
        comments = sorted((tmp / "canned").glob("comment-*.txt"))
        check("exactly ONE comment was posted on the cited issue", len(comments) == 1,
              ", ".join(p.name for p in comments))
        body = comments[0].read_text()
        check("the comment carries the registered marker name (issue #987, rule 6j)",
              "<!-- pipeline-rediagnose: " in body, body[:200])
        check("the marker carries the run id (dedup key)", "run=100 -->" in body, body[-120:])
        check("the comment quotes the landed targets", "`make validate`" in body, body[:300])
        check("the comment quotes the scrubbed error excerpt",
              "make: *** [validate] Error 1" in body, body[:400])
        # The excerpt is scrubbed through the SAME redactor as the filed issue (rule 3f): the
        # planted FAKE_SECRET must never reach the thread, in any spelling.
        check("the planted secret NEVER reaches the comment (scrubbed)",
              FAKE_SECRET not in body, "SECRET LEAKED INTO THREAD COMMENT")
        check("the marker parses through the shared rediagnose parser (rule 6j)",
              str(row["run_id"]) in bm.rediagnose_marker_runs(body), "")


def test_a_raise_does_not_double_annotate() -> None:
    print("\\nrediagnose annotation dedup: a thread already carrying the marker for this run is not commented twice")
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        canned = dict(BASE_CANNED)
        canned["thread-824.json"] = (
            '{"id": 1, "createdAt": "2026-11-11T21:05:00Z", "body": '
            '"<!-- pipeline-rediagnose: 2026-11-11T21:05:00Z run=100 --> first annotation"}\n')
        env = make_scene(tmp, canned)
        ledger = _seed_ledger(tmp, [dict(UNDIAG_ROW)])
        proc = run_filer(env, ledger)
        check("exit 0", proc.returncode == 0, proc.stderr)
        data = json.loads(ledger.read_text())
        row = data["failures"][0]
        check("the row IS still raised (dedup skips only the comment, never the raise)",
              bool(row.get("rediagnosed_utc")), str(row)[:200])
        comments = list((tmp / "canned").glob("comment-*.txt"))
        check("NO second comment is posted for a run already annotated",
              len(comments) == 0, ", ".join(p.name for p in comments))
        check("the pass still reports the raise", "REDIAGNOSED run 100" in proc.stdout, proc.stdout)


def test_a_raise_with_no_issue_cites_no_thread() -> None:
    print("\\nrediagnose annotation: a row citing no issue is raised without attempting a comment")
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        noissue = dict(UNDIAG_ROW)
        noissue["issue_number"] = None
        noissue["issue_url"] = None
        env = make_scene(tmp, BASE_CANNED)
        ledger = _seed_ledger(tmp, [noissue])
        proc = run_filer(env, ledger)
        check("exit 0", proc.returncode == 0, proc.stderr)
        check("the pass says no issue is cited", "no issue cited" in proc.stdout, proc.stdout)
        data = json.loads(ledger.read_text())
        row = data["failures"][0]
        check("the row IS still raised (no-issue is never a reason not to raise)",
              bool(row.get("rediagnosed_utc")), str(row)[:200])
        check("NO comment is posted (no thread to write)",
              not (tmp / "canned" / "comment-count").exists(), "")
        check("NO comment API read is made",
              not (tmp / "canned" / "thread-824.json").exists(), "")


def test_a_still_unreadable_log_leaves_the_row_undiagnosed_and_retries_next_sweep() -> None:
    print("\nrediagnose retry: a log still refused keeps the row pending, loudly, never 'done'")
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        canned = dict(BASE_CANNED)
        canned["log-fail"] = ""
        env = make_scene(tmp, canned)
        # Seed BOTH scene runs so nothing new is filed and only the re-diagnosis pass moves.
        ledger = _seed_ledger(tmp, [dict(UNDIAG_ROW), dict(MARKER_MATCHED_ROW)])
        before = ledger.read_text()
        proc = run_filer(env, ledger)
        check("exit 0 (a refused re-read is not the sweep's failure)",
              proc.returncode == 0, proc.stderr)
        check("the refusal is LOUD on the line", "rediagnose run 100: log still unreadable"
              in proc.stdout, proc.stdout)
        data = json.loads(ledger.read_text())
        row = {e["run_id"]: e for e in data["failures"]}[100]
        check("the row gains NO rediagnosed_utc — it stays pending",
              "rediagnosed_utc" not in row, str(row)[:300])
        check("the row stays eligible — no log_expired yet (issue #986)",
              "log_expired" not in row, str(row)[:300])
        check("the row records the FIRST append-only still-unreadable attempt (issue #986)",
              row.get("rediagnose_attempts") == 1, str(row)[:300])
        check("the ledger file gained only the attempt counter (rule 3b additive, nothing removed)",
              ledger.read_text() != before and "rediagnose_attempts" in ledger.read_text(), "")
    # A row naming a job the run's job list no longer has is reported, not guessed at.
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        env = make_scene(tmp, BASE_CANNED)
        ghost = dict(UNDIAG_ROW)
        ghost["job"] = "no-such-job"
        # Seed run 104 as marker-matched so the schedule run is not filed or re-diagnosed by the
        # sweep — only the ghost's own row is under test.
        ledger = _seed_ledger(tmp, [ghost, dict(MARKER_MATCHED_ROW)])
        before2 = ledger.read_text()
        proc = run_filer(env, ledger)
        check("a job-name mismatch is named, and the row stays UNDIAGNOSED",
              proc.returncode == 0 and "no failed job 'no-such-job'" in proc.stdout
              and "rediagnosed_utc" not in json.loads(ledger.read_text())["failures"][0],
              proc.stdout)
        check("a structural (non-retention) mismatch does not grow the attempt counter (issue #986)",
              "rediagnose_attempts" not in json.loads(ledger.read_text())["failures"][0]
              and ledger.read_text() == before2, proc.stdout)


def test_a_run_that_ages_out_stamps_log_expired_and_drains_the_queue() -> None:
    print("\nlog expired (issue #986): a run that ages out of retention is stamped TERMINAL, once")
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        canned = dict(BASE_CANNED)
        canned["log-fail"] = ""
        env = make_scene(tmp, canned)
        # Give the row MAX-1 failed attempts already: this sweep is the bounded last one.
        aged = dict(UNDIAG_ROW)
        aged["rediagnose_attempts"] = F.MAX_REDIAGNOSE_ATTEMPTS - 1
        # Seed run 104 as marker-matched so the schedule run is not filed/rediagnosed by the sweep
        # — only run 100's aged row is under test.
        ledger = _seed_ledger(tmp, [aged, dict(MARKER_MATCHED_ROW)])
        proc = run_filer(env, ledger)
        check("exit 0", proc.returncode == 0, proc.stderr)
        check("the terminal stamp is LOUD", "LOG EXPIRED run 100" in proc.stdout, proc.stdout)
        data = json.loads(ledger.read_text())
        row = {e["run_id"]: e for e in data["failures"]}[100]
        check("the row carries the TERMINAL log_expired state with its reason",
              row.get("log_expired") and "log still unreadable" in row["log_expired"],
              str(row)[:300])
        check("the counter reached the bound", row.get("rediagnose_attempts") == F.MAX_REDIAGNOSE_ATTEMPTS,
              str(row)[:300])
        check("the original undiagnosed field is KEPT (rule 3b additive)",
              row.get("undiagnosed") == UNDIAG_ROW["undiagnosed"], str(row)[:300])
        # Re-sweep: the row is now EXCLUDED from pending, so the queue drains — no re-read, no line.
        data2 = json.loads(ledger.read_text())
        before = json.dumps(data2)
        second = run_filer(env, ledger)
        check("a re-sweep no longer touches the drained row (no re-read, no line)",
              second.returncode == 0 and "rediagnose run 100" not in second.stdout
              and json.loads(ledger.read_text()) == data2 and json.dumps(json.loads(ledger.read_text())) == before,
              second.stdout)


def test_log_expired_dry_mode_previews_the_stamp_and_writes_nothing() -> None:
    print("\nlog expired dry: --dry previews WOULD EXPIRE without writing the ledger (issue #986)")
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        canned = dict(BASE_CANNED)
        canned["log-fail"] = ""
        env = make_scene(tmp, canned)
        aged = dict(UNDIAG_ROW)
        aged["rediagnose_attempts"] = F.MAX_REDIAGNOSE_ATTEMPTS - 1
        ledger = _seed_ledger(tmp, [aged])
        before = ledger.read_text()
        proc = run_filer(env, ledger, "--dry")
        check("exit 0", proc.returncode == 0, proc.stderr)
        check("dry prints the WOULD EXPIRE preview",
              "WOULD EXPIRE run 100" in proc.stdout, proc.stdout)
        check("dry writes NOTHING to the ledger", ledger.read_text() == before, "")


def test_a_rediagnosed_row_is_never_re_fetched_and_dry_previews_without_writing() -> None:
    print("\nrediagnose bounds: done rows are skipped; --dry previews WOULD RAISE and writes nothing")
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        canned = dict(BASE_CANNED)
        canned["log-fail"] = ""  # ANY log call would fail — a done row must not trigger one
        env = make_scene(tmp, canned)
        done = dict(UNDIAG_ROW)
        done["rediagnosed_utc"] = "2026-11-12T00:00:00+00:00"
        done["error_excerpt"] = "make: *** [validate] Error 1"
        ledger = _seed_ledger(tmp, [done, dict(MARKER_MATCHED_ROW)])
        before = ledger.read_text()
        proc = run_filer(env, ledger)
        check("a rediagnosed row is not re-fetched and prints no rediagnose line",
              proc.returncode == 0 and "rediagnose run 100" not in proc.stdout
              and ledger.read_text() == before, proc.stdout)
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        env = make_scene(tmp, BASE_CANNED)
        ledger = _seed_ledger(tmp, [dict(UNDIAG_ROW)])
        before = ledger.read_text()
        proc = run_filer(env, ledger, "--dry")
        check("--dry prints the preview", "WOULD RAISE run 100" in proc.stdout, proc.stdout)
        check("--dry writes NOTHING to the ledger", ledger.read_text() == before, "")


def test_the_makefile_line_target_form_normalises_to_the_bare_target() -> None:
    print("\nnormalise (#1054): Makefile:<line>: <name> becomes the bare target at extraction")
    check("the bracketed file:line form normalises to the bare target",
          F.failed_make_targets(["make: *** [Makefile:1384: sweep-alarm] Error 2"])
          == ["sweep-alarm"], "")
    check("the plain bracketed form is unchanged",
          F.failed_make_targets(["make: *** [validate] Error 1"]) == ["validate"], "")
    check("the two forms of one target dedupe to ONE name",
          F.failed_make_targets(["make: *** [validate] Error 1",
                                 "make: *** [Makefile:1231: validate] Error 2"])
          == ["validate"], "")
    check("normalize_target passes a bare name through",
          F.normalize_target("live-smoke") == "live-smoke", "")
    check("normalize_target strips the file:line decoration",
          F.normalize_target("Makefile:1379: owed-rows-check") == "owed-rows-check", "")


def test_a_sweep_normalises_stored_rows_and_leaves_a_uniform_ledger_untouched() -> None:
    print("\nnormalise (#1054): a sweep converges stored rows; a uniform ledger is not rewritten")
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        env = make_scene(tmp, BASE_CANNED)
        warped = dict(UNDIAG_ROW)
        warped["run_id"] = 777
        warped["undiagnosed"] = None
        warped["targets"] = ["Makefile:1231: _implement-issue", "live-smoke"]
        warped["job"] = "implement"
        clean = dict(MARKER_MATCHED_ROW)
        clean["targets"] = ["validate"]
        ledger = _seed_ledger(tmp, [warped, clean, dict(UNDIAG_ROW)])
        before = ledger.read_text()
        proc = run_filer(env, ledger)
        check("exit 0", proc.returncode == 0, proc.stderr)
        check("the sweep names the normalisation", "targets normalised on" in proc.stdout,
              proc.stdout)
        data = json.loads(ledger.read_text())
        rows = {e["run_id"]: e for e in data["failures"]}
        check("every stored run id SURVIVES the normalisation (rule 3b: no row lost)",
              set(rows) == {777, 104, 100}, str(sorted(rows)))
        check("the warped row's targets are the bare parseable names",
              rows[777]["targets"] == ["_implement-issue", "live-smoke"], str(rows[777]))
        check("the raise re-normalises its own row's grown targets (100)",
              rows[100]["targets"] == ["validate"], str(rows[100]))
        check("a row that was already uniform is byte-identical",
              {k: v for k, v in rows[104].items()} == {k: v for k, v in clean.items()},
              str(rows[104]))
        # Second sweep on the now-uniform ledger: the file is not rewritten again.
        after = ledger.read_text()
        ledger2 = _seed_ledger(tmp, json.loads(after)["failures"])
        ledger2.write_text(after)
        quiet_bytes = after
        proc2 = run_filer(env, ledger2)
        check("a uniform ledger stays untouched (no churn)", proc2.returncode == 0
              and ledger2.read_text() == quiet_bytes
              and "targets normalised on" not in proc2.stdout, proc2.stdout)
        assert before != after  # the warped ledger really did change


def test_a_raise_renormalises_the_row_s_existing_warped_targets() -> None:
    print("\nnormalise (#1054): a raise outputs uniform targets even from a warped row")
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        env = make_scene(tmp, BASE_CANNED)
        warped = dict(UNDIAG_ROW)  # run 100, undiagnosed, log readable in this scene
        warped["targets"] = ["Makefile:1384: validate"]
        ledger = _seed_ledger(tmp, [warped])
        proc = run_filer(env, ledger)
        check("exit 0", proc.returncode == 0, proc.stderr)
        row = {e["run_id"]: e for e in json.loads(ledger.read_text())["failures"]}[100]
        check("the raised row's targets are uniform bare names",
              row.get("targets") == ["validate"], str(row))
        check("the raise still happened (rediagnosed_utc stamped)",
              bool(row.get("rediagnosed_utc")), str(row)[:200])


# ---------------------------------------------------------------------------
# the stamp pass (issue #1099): a merged fix PR raises its ledger row
# ---------------------------------------------------------------------------

#: A planted row in the exact shape every closed row held before the stamp pass existed:
#: filed, diagnosed, closed by a merged fix PR — and `fix_pr: null`, waiting for a manual
#: keeper cycle. Run 150 is OUTSIDE the canned run list, so this sweep files and re-diagnoses
#: nothing; the stamp pass is the only new behaviour the scene exercises.
STAMP_TARGET = {
    "run_id": 150, "workflow": "qa-validate.yml", "job": "validate",
    "head_sha": "f" * 40, "run_url": "https://github.com/octo/repo/actions/runs/150",
    "created_utc": "2026-11-10T06:10:00Z", "filed_utc": "2026-11-10T07:00:00Z",
    "targets": ["validate"], "issue_number": "931",
    "issue_url": "https://github.com/octo/repo/issues/931",
    "fix_pr": None, "guard": None,
    "rediagnosed_utc": "2026-11-10T07:30:00Z",
    "error_excerpt": "make: *** [validate] Error 2",
}

#: The measured close link shape: the closed issue #833 answers closedByPullRequestsReferences
#: [1057] (verified live 2026-11-17). The planted fixture mirrors it per issue number.
def closed_refs(prs: list[int]) -> str:
    return json.dumps({"state": "CLOSED", "closedByPullRequestsReferences":
                       [{"number": p, "url": f"https://github.com/octo/repo/pull/{p}"}
                        for p in prs]})


def merged_pr(number: int, files: list[dict], title: str = "") -> str:
    return json.dumps({"number": number, "mergedAt": "2026-11-12T09:00:00Z",
                       "title": title or f"fix(ci): the planted fix #{number} (issue #931)",
                       "files": files})


def open_issue() -> str:
    return json.dumps({"state": "OPEN", "closedByPullRequestsReferences": []})


def _stamp_ledger(tmp: Path, target: dict) -> Path:
    """Seed the run-list runs (100, 104) as KNOWN rows so the sweep files/rediagnoses nothing
    and the stamp pass sees only planted rows."""
    diagnosed_100 = dict(UNDIAG_ROW)
    diagnosed_100.pop("undiagnosed")
    diagnosed_100["rediagnosed_utc"] = "2026-11-11T21:30:00Z"
    return _seed_ledger(tmp, [dict(MARKER_MATCHED_ROW), diagnosed_100, dict(target)])


def _row_for(ledger: Path, run_id: int) -> dict:
    return {e["run_id"]: e for e in json.loads(ledger.read_text())[
        "failures"]}[run_id]


def test_a_stamped_row_with_no_error_block_is_pending_and_gets_diagnosed() -> None:
    """Issue #1136: the pending set is the ABSENCE of a diagnosis, not the `undiagnosed` key."""
    print("\nrediagnose selection (#1136): a stamped row with no error block is fetched and raised")
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        canned = dict(BASE_CANNED)
        canned["jobs-777.json"] = {"jobs": [{"databaseId": 977, "name": "sweep",
                                             "conclusion": "failure"}]}
        env = make_scene(tmp, canned)
        diagnosed_100 = dict(UNDIAG_ROW)
        diagnosed_100.pop("undiagnosed")
        diagnosed_100["rediagnosed_utc"] = "2026-11-11T21:30:00Z"
        diagnosed_100["error_excerpt"] = "make: *** [validate] Error 1"
        seeded = [dict(MARKER_MATCHED_ROW), diagnosed_100, dict(STAMPED_WITHOUT_DIAGNOSIS_ROW)]
        ledger = _seed_ledger(tmp, seeded)
        # The defect, proven on the ledger itself before the sweep runs: this is the PRE-#1136
        # filter spelled here in the test (the product no longer carries it — rule 6d), and it
        # selects nothing, because a row whose log read SUCCEEDED stores `undiagnosed: None`.
        legacy_pending = [e["run_id"] for e in seeded
                          if e.get("undiagnosed") and not e.get("log_expired")]
        new_pending = [e["run_id"] for e in F.rediagnose_pending({"failures": seeded})]
        check("the old marker-key filter selected NOTHING (the #1136 blind spot)",
              legacy_pending == [], str(legacy_pending))
        check("the diagnosis-absence filter selects the stamped errorless row",
              new_pending == [777], str(new_pending))
        proc = run_filer(env, ledger)
        check("exit 0", proc.returncode == 0, proc.stderr)
        check("the sweep names the raise", "REDIAGNOSED run 777" in proc.stdout, proc.stdout)
        rows = {e["run_id"]: e for e in json.loads(ledger.read_text())["failures"]}
        row = rows[777]
        check("the error block lands", "make: *** [validate] Error 1" in row.get("error_excerpt", ""),
              str(row)[:400])
        check("rediagnosed_utc stamped", bool(row.get("rediagnosed_utc")), str(row))
        check("the stamp pass's keys are KEPT (rule 3b append-only)",
              row.get("fix_pr") == STAMPED_WITHOUT_DIAGNOSIS_ROW["fix_pr"]
              and row.get("guard") == STAMPED_WITHOUT_DIAGNOSIS_ROW["guard"]
              and row.get("stamp_utc") == STAMPED_WITHOUT_DIAGNOSIS_ROW["stamp_utc"]
              and row.get("stamp_note") == STAMPED_WITHOUT_DIAGNOSIS_ROW["stamp_note"], str(row))
        check("the `undiagnosed` key is KEPT (null, never removed)",
              "undiagnosed" in row and row["undiagnosed"] is None, str(row))
        check("targets grown, never shrunk",
              set(STAMPED_WITHOUT_DIAGNOSIS_ROW["targets"]) <= set(row.get("targets", [])),
              str(row.get("targets")))
        check("an already-diagnosed marker-matched row is byte-identical",
              rows[104] == MARKER_MATCHED_ROW, str(rows[104])[:400])
        check("an already-raised row is byte-identical", rows[100] == diagnosed_100, str(rows[100]))
        before = ledger.read_text()
        second = run_filer(env, ledger)
        check("re-sweep: nothing pending, nothing rewritten",
              second.returncode == 0 and "REDIAGNOSED" not in second.stdout
              and ledger.read_text() == before, second.stdout)


def test_the_committed_ledger_s_errorless_rows_are_exactly_the_pending_set() -> None:
    """Issue #1136 on the SHIPPED data: every fix-claimed row carrying no error block is pending.

    Data-driven, not a frozen five-run set: the sweep's re-diagnosis pass (#969/#1136) legitimately
    raises `error_excerpt` into each row and the keeper ledger PR lands that append (rule 3b), so
    a hard-coded 'the five runs #1039-#1043' expectation self-destructs when the pipeline does its
    job. Compute the expected set from the row dicts, independently of `rediagnose_pending`.
    """
    print("\nrediagnose selection (#1136): the shipped ledger's errorless rows are pending")
    committed = json.loads(COMMITTED_LEDGER.read_text())
    rows = committed["failures"]

    def has_error_block(e: dict) -> bool:
        # Independent of row_is_diagnosed (the seam under test): the two keys the raise uses.
        return bool(e.get("error_excerpt") or e.get("rediagnosed_excerpt"))

    # A row is pending when it carries no error block under either spelling, was not already
    # raised this ledger's life, and is not the terminal log_expired drain (issue #986).
    expected = {e["run_id"] for e in rows
                if not has_error_block(e) and not e.get("rediagnosed_utc")
                and not e.get("log_expired")}
    pending = {e["run_id"] for e in F.rediagnose_pending(committed)}
    check("the errorless, unraised rows are exactly the pending set",
          pending == expected, f"pending={sorted(pending)} expected={sorted(expected)}")
    errorless = {e["run_id"] for e in rows if not has_error_block(e) and not e.get("log_expired")}
    check("every errorless row (bar the terminal drain) is pending — no row is invisible",
          errorless == pending, f"{sorted(errorless)} vs {sorted(pending)}")
    check("every fix-claimed row is diagnosed or pending — none invisible",
          {e["run_id"] for e in rows if e.get("fix_pr")} - pending
          == {e["run_id"] for e in rows if e.get("fix_pr") and has_error_block(e)}, "")


def test_a_closed_row_is_stamped_from_the_merged_guard_carrying_pr_that_closed_it() -> None:
    print("\nstamp (#1099): CLOSED + merged closing PR with a tests/ guard -> fix_pr raised")
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        canned = dict(BASE_CANNED)
        canned["issue-view-931.json"] = closed_refs([940])
        canned["pr-940.json"] = merged_pr(940, [
            {"path": "Makefile", "changeType": "MODIFIED"},
            {"path": "tests/test_planted_guard.py", "changeType": "ADDED"},
        ])
        env = make_scene(tmp, canned)
        ledger = _stamp_ledger(tmp, STAMP_TARGET)
        proc = run_filer(env, ledger)
        check("exit 0", proc.returncode == 0, proc.stderr)
        check("the pass names the raised row", "STAMPED run 150" in proc.stdout, proc.stdout)
        row = _row_for(ledger, 150)
        check("fix_pr raised to the closing PR", row.get("fix_pr") == 940, str(row))
        check("guard named from the PR's ADDED tests/ module",
              row.get("guard") == "tests/test_planted_guard.py", str(row))
        check("merged_at recorded", row.get("fix_pr_merged_utc") == "2026-11-12T09:00:00Z",
              str(row))
        check("the stamp records WHEN and WHY",
              bool(row.get("stamp_utc")) and "#1099" in row.get("stamp_note", "")
              and "closed issue #931" in row.get("stamp_note", ""), str(row))
        check("append-only (rule 3b): every filer field survives unchanged",
              all(row.get(k) == v for k, v in STAMP_TARGET.items()
                  if k not in ("fix_pr", "guard")), str(row)[:400])
        check("a row the pass skipped keeps its nulls (run 104 cites no issue)",
              _row_for(ledger, 104) == MARKER_MATCHED_ROW, str(_row_for(ledger, 104)))
        check("the CLOSED issue gets its annotation on the thread",
              any(p.name.startswith("comment-931-") for p in (tmp / "canned").glob("comment-*.txt"))
              and any("<!-- pipeline-ledger-stamp:" in p.read_text()
                      and "run=150" in p.read_text()
                      and "issue #1099" in p.read_text()
                      for p in (tmp / "canned").glob("comment-931-*.txt")),
              ", ".join(p.name for p in (tmp / "canned").glob("comment-*.txt")))


def test_the_stamp_prefers_the_guard_module_the_merged_pr_added() -> None:
    print("\nstamp (#1099): an ADDED tests/ module outranks a modified one in the diff")
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        canned = dict(BASE_CANNED)
        canned["issue-view-931.json"] = closed_refs([940])
        canned["pr-940.json"] = merged_pr(940, [
            {"path": "tests/test_sibling.py", "changeType": "MODIFIED"},
            {"path": "tests/test_planted_guard.py", "changeType": "ADDED"},
        ])
        env = make_scene(tmp, canned)
        ledger = _stamp_ledger(tmp, STAMP_TARGET)
        proc = run_filer(env, ledger)
        check("the ADDED module is the guard", _row_for(ledger, 150).get("guard")
              == "tests/test_planted_guard.py", proc.stdout)


def test_a_merged_fix_pr_that_only_modified_its_guard_module_still_raises_the_row() -> None:
    print("\nstamp (#1099): the measured #833 shape — PR #1057 MODIFIED tests/test_implement_stream.py")
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        canned = dict(BASE_CANNED)
        canned["issue-view-932.json"] = closed_refs([941])
        canned["pr-941.json"] = merged_pr(941, [
            {"path": "tests/test_implement_stream.py", "changeType": "MODIFIED"},
            {"path": "docs/notes.md", "changeType": "ADDED"},
        ])
        env = make_scene(tmp, canned)
        target = dict(STAMP_TARGET, issue_number="932")
        ledger = _stamp_ledger(tmp, target)
        proc = run_filer(env, ledger)
        check("a MODIFIED tests/ module still counts as the guard",
              "STAMPED run 150" in proc.stdout
              and _row_for(ledger, 150).get("guard") == "tests/test_implement_stream.py",
              proc.stdout)


def test_a_closed_issue_with_no_closing_pr_stays_the_keeper_s_act() -> None:
    print("\nstamp (#1099): CLOSED with closedByPullRequestsReferences [] -> never stamped")
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        canned = dict(BASE_CANNED)
        canned["issue-view-933.json"] = closed_refs([])
        env = make_scene(tmp, canned)
        target = dict(STAMP_TARGET, issue_number="933")
        ledger = _stamp_ledger(tmp, target)
        before = ledger.read_text()
        proc = run_filer(env, ledger)
        check("the pass says the manual close stays the keeper's act",
              "issue #933 CLOSED with no closing PR" in proc.stdout
              and "keeper" in proc.stdout, proc.stdout)
        check("no fix_pr was invented and nothing was written",
              _row_for(ledger, 150).get("fix_pr") is None and ledger.read_text() == before,
              str(_row_for(ledger, 150)))


def test_an_open_issue_row_is_reported_as_a_fix_in_flight_never_stamped() -> None:
    print("\nstamp (#1099): an OPEN issue row is a fix in flight, reported not stamped")
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        canned = dict(BASE_CANNED)
        canned["issue-view-934.json"] = open_issue()
        env = make_scene(tmp, canned)
        target = dict(STAMP_TARGET, issue_number="934")
        ledger = _stamp_ledger(tmp, target)
        before = ledger.read_text()
        proc = run_filer(env, ledger)
        check("the pass names it in flight", "issue #934 is OPEN — fix in flight" in proc.stdout,
              proc.stdout)
        check("the row keeps its nulls (the §6r in-flight report stays)",
              _row_for(ledger, 150).get("fix_pr") is None and ledger.read_text() == before, "")


def test_a_closing_pr_not_merged_yet_is_reported_and_retried_next_sweep() -> None:
    print("\nstamp (#1099): a closing PR that is not merged yet is NOT merged evidence")
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        canned = dict(BASE_CANNED)
        canned["issue-view-935.json"] = closed_refs([944])
        canned["pr-944.json"] = json.dumps({"number": 944, "mergedAt": None,
                                            "title": "open fix", "files": [
                                                {"path": "tests/test_planted_guard.py",
                                                 "changeType": "ADDED"}]})
        env = make_scene(tmp, canned)
        target = dict(STAMP_TARGET, issue_number="935")
        ledger = _stamp_ledger(tmp, target)
        before = ledger.read_text()
        proc = run_filer(env, ledger)
        check("the pass names the unmerged PR and defers",
              "PR(s) #944 not merged yet" in proc.stdout, proc.stdout)
        check("exit 0 — the sweep survives for the other rows",
              proc.returncode == 0 and ledger.read_text() == before, proc.stderr)


def test_a_merged_close_whose_diff_carries_no_guard_test_is_refused_loudly() -> None:
    print("\nstamp (#1099): merged close, no tests/ file in the diff -> loud refusal, no stamp")
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        canned = dict(BASE_CANNED)
        canned["issue-view-936.json"] = closed_refs([945])
        canned["pr-945.json"] = merged_pr(945, [{"path": "scripts/fixer.py",
                                                 "changeType": "MODIFIED"}])
        env = make_scene(tmp, canned)
        target = dict(STAMP_TARGET, issue_number="936")
        ledger = _stamp_ledger(tmp, target)
        before = ledger.read_text()
        proc = run_filer(env, ledger)
        check("the guardless merged close is reported as the §6r defect",
              "diff carries NO tests/ guard" in proc.stdout
              and "fix without its guard test is the defect" in proc.stdout, proc.stdout)
        check("no fix_pr is stamped onto a guardless close",
              _row_for(ledger, 150).get("fix_pr") is None and ledger.read_text() == before, "")


def test_the_stamp_raises_the_merged_guarded_close_when_another_closing_pr_is_unmerged() -> None:
    print("\nstamp (#1099): several closing PRs — the merged, guarded one is raised")
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        canned = dict(BASE_CANNED)
        canned["issue-view-937.json"] = closed_refs([946, 947])
        canned["pr-946.json"] = json.dumps({"number": 946, "mergedAt": None,
                                            "title": "still open", "files": []})
        canned["pr-947.json"] = merged_pr(947, [{"path": "tests/test_planted_guard.py",
                                                 "changeType": "ADDED"}])
        env = make_scene(tmp, canned)
        target = dict(STAMP_TARGET, issue_number="937")
        ledger = _stamp_ledger(tmp, target)
        proc = run_filer(env, ledger)
        row = _row_for(ledger, 150)
        check("the MERGED guarded PR is the one raised",
              "STAMPED run 150" in proc.stdout and row.get("fix_pr") == 947
              and row.get("guard") == "tests/test_planted_guard.py", proc.stdout)


def test_the_stamp_never_overwrites_a_guard_the_row_already_records() -> None:
    print("\nstamp (#1099): a row that already names a guard keeps it (rule 3b)")
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        canned = dict(BASE_CANNED)
        canned["issue-view-938.json"] = closed_refs([948])
        canned["pr-948.json"] = merged_pr(948, [{"path": "tests/test_other.py",
                                                 "changeType": "ADDED"}])
        env = make_scene(tmp, canned)
        target = dict(STAMP_TARGET, issue_number="938",
                      guard="tests/test_pipeline_failure_guard.py")
        ledger = _stamp_ledger(tmp, target)
        proc = run_filer(env, ledger)
        row = _row_for(ledger, 150)
        check("fix_pr is raised while the recorded guard survives",
              row.get("fix_pr") == 948
              and row.get("guard") == "tests/test_pipeline_failure_guard.py", str(row))
        check("the note says the recorded guard was KEPT",
              "KEPT" in row.get("stamp_note", ""), str(row))


def test_the_stamp_pass_is_idempotent_across_sweeps() -> None:
    print("\nstamp (#1099): a stamped row is never re-read, re-written or double-stamped")
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        canned = dict(BASE_CANNED)
        canned["issue-view-931.json"] = closed_refs([940])
        canned["pr-940.json"] = merged_pr(940, [{"path": "tests/test_planted_guard.py",
                                                 "changeType": "ADDED"}])
        env = make_scene(tmp, canned)
        ledger = _stamp_ledger(tmp, STAMP_TARGET)
        first = run_filer(env, ledger)
        check("first sweep stamps", "STAMPED run 150" in first.stdout, first.stdout)
        before = ledger.read_text()
        second = run_filer(env, ledger)
        check("second sweep never re-stamps the row",
              "run 150" not in second.stdout
              and ledger.read_text() == before, second.stdout)


def test_a_stamp_read_failure_is_loud_on_its_row_and_never_fatal_to_the_sweep() -> None:
    print("\nstamp (#1099): a corrupt close-link read is a loud per-row retry, not a crash")
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        canned = dict(BASE_CANNED)
        canned["issue-view-931.json"] = "{corrupt json{{"  # unreadable close link
        env = make_scene(tmp, canned)
        ledger = _stamp_ledger(tmp, STAMP_TARGET)
        before = ledger.read_text()
        proc = run_filer(env, ledger)
        check("the failed read is named on its row",
              "issue #931 read failed" in proc.stdout, proc.stdout)
        check("the sweep still finishes (exit 0) and the row keeps its nulls",
              proc.returncode == 0 and _row_for(ledger, 150).get("fix_pr") is None
              and ledger.read_text() == before, proc.stderr)


def test_a_row_citing_no_issue_is_reported_and_writes_nothing() -> None:
    print("\nstamp (#1099): a row with no issue_number is reported, never guessed at")
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        env = make_scene(tmp, dict(BASE_CANNED))
        target = dict(STAMP_TARGET, issue_number=None, issue_url=None)
        ledger = _stamp_ledger(tmp, target)
        before = ledger.read_text()
        proc = run_filer(env, ledger)
        check("the pass names the row that cites no issue",
              "cites no issue — nothing to stamp" in proc.stdout, proc.stdout)
        check("nothing written", ledger.read_text() == before
              and _row_for(ledger, 150).get("fix_pr") is None, "")


def test_dry_mode_previews_the_stamp_and_writes_nothing() -> None:
    print("\nstamp (#1099): --dry prints WOULD STAMP and leaves the ledger byte-identical")
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        canned = dict(BASE_CANNED)
        canned["issue-view-931.json"] = closed_refs([940])
        canned["pr-940.json"] = merged_pr(940, [{"path": "tests/test_planted_guard.py",
                                                 "changeType": "ADDED"}])
        env = make_scene(tmp, canned)
        ledger = _stamp_ledger(tmp, STAMP_TARGET)
        before = ledger.read_text()
        proc = run_filer(env, ledger, "--dry")
        check("the preview is named", "WOULD STAMP run 150" in proc.stdout, proc.stdout)
        check("no STAMPED claim, no annotation, no write",
              "STAMPED run 150" not in proc.stdout
              and not list((tmp / "canned").glob("comment-931-*.txt"))
              and ledger.read_text() == before, proc.stdout)


def test_the_stamp_rides_the_filer_s_ledger_pr_landing_through_the_makefile() -> None:
    print("\nstamp wiring (#1099): the pass lives in make pipeline-failure-issue, "
          "landed by the ledger-PR keeper step")
    src = FILER.read_text()
    check("the sweep calls the stamp pass",
          "stamp_merged_fix_prs" in src and "lines.extend(stamp_merged_fix_prs" in src, "")
    check("the stamp annotation marker is REGISTERED (rule 6j) and written by the pass",
          bm.LEDGER_STAMP_NAME == "pipeline-ledger-stamp"
          and bm.marker_name("queued-alarm", "stamp") == bm.LEDGER_STAMP_NAME
          and ("queued-alarm", "stamp") in bm.WRITTEN
          and "ledger_stamp_marker" in src
          and bm.parse_ledger_stamp_run(bm.ledger_stamp_marker(
              dt.datetime(2026, 11, 17, 6, 0, tzinfo=dt.timezone.utc), 123)) == "123",
          f"{bm.REGISTRY.get('queued-alarm')} / {bm.WRITTEN}")
    makefile = MAKEFILE.read_text()
    check("the Makefile documents the stamp pass on the filer target",
          "stamp pass" in makefile and "#1099" in makefile, "")
    queue = QUEUE_WF.read_text()
    check("queued-alarm runs the filer (the stamp's host) through the Makefile",
          "make pipeline-failure-issue" in queue, "")
    check("a stamp rides the same landed append: the sweep's keeper-pr step lands the ledger",
          "make keeper-pr" in queue
          and "FILE=data/pipeline_failures.json" in queue
          and "ci/pipeline-failure-ledger" in queue, "")
    agents = (ROOT / "AGENTS.md").read_text()
    check("the rulebook names the automatic raise (issue #1099)",
          "stamp" in agents and "#1099" in agents, "")


def test_failure_shape_groups_the_same_defect_and_separates_others() -> None:
    print("\nshape (#1164): two PRs hitting one defect share a shape; a different step does not")
    block = ["##[error]The process '/usr/bin/make' failed with exit code 2",
             "make: *** [validate] Error 1",
             "run 44651246625 died at sha " + "a" * 40]
    other = ["##[error]Process completed with exit code 1", "make: *** [lint] Error 1"]
    a = F.failure_shape(block, ["validate"], ["Prepare runner images"])
    b = F.failure_shape(block, ["validate"], ["Prepare runner images"])
    check("the same failure block + steps + targets is ONE shape", a == b, f"{a} vs {b}")
    # Run-specific tokens (a sha, a count) must NOT split one defect into two shapes.
    c = F.failure_shape(["##[error]The process '/usr/bin/make' failed with exit code 2",
                         "make: *** [validate] Error 1",
                         "run 999999999999 died at sha " + "b" * 40],
                        ["validate"], ["Prepare runner images"])
    check("a different run id / sha is the SAME shape (normalised)", a == c, f"{a} vs {c}")
    d = F.failure_shape(block, ["validate"], ["Run tests"])
    check("a different failing step is a DIFFERENT shape", a != d, f"{a} vs {d}")
    e = F.failure_shape(other, ["lint"], ["Prepare runner images"])
    check("a different error block is a DIFFERENT shape", a != e, f"{a} vs {e}")
    check("the shape is a stable short digest", len(a) == 12, a)
    # Issue #1175: the digest covers the WHOLE bounded block, not an 8-line prefix. Two defects
    # that share GitHub's boilerplate and differ only LATER are two shapes, never one — the
    # planted blocks are longer than the old 8-line window and identical inside it.
    prefix = ["##[error]The process '/usr/bin/make' failed with exit code 2",
              "make: *** [validate] Error 1"] + [f"  common boilerplate line {i}" for i in range(9)]
    tail_a = ["Traceback (most recent call last):",
              '  File "scripts/ensure_image.py", line 1, in <module>',
              "AssertionError: the installed agent is NOT the pinned version"]
    tail_b = ["Traceback (most recent call last):",
              '  File "scripts/run_tests.sh", line 9, in <module>',
              "AssertionError: the suite captured no [test] line"]
    sa = F.failure_shape([*prefix, *tail_a], ["validate"], ["Run tests"])
    sb = F.failure_shape([*prefix, *tail_b], ["validate"], ["Run tests"])
    check("#1175: two failures sharing a prefix but differing later are DIFFERENT shapes",
          sa != sb, f"{sa} vs {sb}")
    check("#1175: the same full block is still ONE shape",
          sa == F.failure_shape([*prefix, *tail_a], ["validate"], ["Run tests"]), sa)
    # RED on the old shape: the pair is byte-identical inside the pre-change 8-line window, so
    # `skeleton[:8]` digested the same key for both and recorded ONE blockage for two defects.
    norm_a = [re.sub(r"\x1b\[[0-9;]*m", "", l).strip() for l in [*prefix, *tail_a]]
    norm_b = [re.sub(r"\x1b\[[0-9;]*m", "", l).strip() for l in [*prefix, *tail_b]]
    check("#1175: the pair is identical inside the OLD 8-line window (the pre-change digest collided)",
          norm_a[:8] == norm_b[:8], f"{norm_a[:8]} vs {norm_b[:8]}")
    src = (ROOT / "scripts" / "pipeline_failure_issue.py").read_text(encoding="utf-8")
    check("#1175: the prefix slice is gone from the seam", "skeleton[:8]" not in src, src[:200])


def test_group_pr_blockages_needs_two_open_prs_and_drops_closed_branches() -> None:
    print("\ngrouping (#1164): a shape blocking two OPEN PRs is kept; one PR or a merged branch is not")
    def item(run_id, branch, shape):
        return {"run": {"databaseId": run_id, "headBranch": branch}, "shape": shape}
    open_branches = {"ci/a", "ci/b", "ci/c"}
    groups = F.group_pr_blockages(
        [item(1, "ci/a", "s1"), item(2, "ci/b", "s1"),      # one defect, two open PRs -> kept
         item(3, "ci/c", "s2"),                              # a lone PR -> dropped
         item(4, "ci/merged", "s1")],                        # branch no longer open -> dropped
        open_branches)
    check("exactly one group survives", len(groups) == 1, str(groups))
    g = groups[0]
    check("the group is the shared shape", g["shape"] == "s1", g["shape"])
    check("the group names both blocked open PRs", g["branches"] == ["ci/a", "ci/b"], str(g["branches"]))
    check("the group's members are the two runs, oldest first",
          [m["run"]["databaseId"] for m in g["members"]] == [1, 2], str(g["members"]))
    # An unreadable open-PR list (gh missing / a transport error) is an EMPTY set: nothing is
    # recorded rather than a blockage claimed from an unread state.
    check("no open PRs readable -> nothing grouped",
          F.group_pr_blockages([item(1, "ci/a", "s1"), item(2, "ci/b", "s1")], set()) == [], "")
    check("one open PR is that author's own noise, never a blockage",
          F.group_pr_blockages([item(1, "ci/a", "s1")], {"ci/a"}) == [], "")


PR_RUNS = [
    {"databaseId": 700, "workflowName": "qa-validate.yml", "name": "validate",
     "headBranch": "ci/a", "headSha": "d" * 40, "event": "pull_request",
     "createdAt": "2026-11-11T21:00:00Z", "conclusion": "failure", "status": "completed",
     "url": "https://github.com/octo/repo/actions/runs/700"},
    {"databaseId": 701, "workflowName": "qa-validate.yml", "name": "validate",
     "headBranch": "ci/b", "headSha": "e" * 40, "event": "pull_request",
     "createdAt": "2026-11-11T21:10:00Z", "conclusion": "failure", "status": "completed",
     "url": "https://github.com/octo/repo/actions/runs/701"},
    # A merged branch: no longer blocked, so it must not count toward the two-PR threshold.
    {"databaseId": 702, "workflowName": "qa-validate.yml", "name": "validate",
     "headBranch": "ci/merged", "headSha": "f" * 40, "event": "pull_request",
     "createdAt": "2026-11-11T21:20:00Z", "conclusion": "failure", "status": "completed",
     "url": "https://github.com/octo/repo/actions/runs/702"},
    # A DIFFERENT failure shape on a third open PR: one PR, never recorded.
    {"databaseId": 703, "workflowName": "qa-validate.yml", "name": "validate",
     "headBranch": "ci/c", "headSha": "0" * 40, "event": "pull_request",
     "createdAt": "2026-11-11T21:30:00Z", "conclusion": "failure", "status": "completed",
     "url": "https://github.com/octo/repo/actions/runs/703"},
]

PR_JOBS_IMAGE = {"jobs": [
    {"databaseId": 910, "name": "validate", "conclusion": "failure",
     "steps": [{"name": "Prepare runner images", "conclusion": "failure"}]}]}
PR_JOBS_OTHER = {"jobs": [
    {"databaseId": 913, "name": "validate", "conclusion": "failure",
     "steps": [{"name": "Run tests", "conclusion": "failure"}]}]}


def test_pr_blockage_pass_records_a_shared_failure_shape_once() -> None:
    print("\nPR-blockage (#1164): a shape shared by two OPEN PRs files ONE issue + ledger row")
    canned = dict(BASE_CANNED)
    canned["runs-qa-validate_yml-pull_request.json"] = PR_RUNS
    canned["open-prs.json"] = [{"headRefName": "ci/a"}, {"headRefName": "ci/b"},
                               {"headRefName": "ci/c"}]
    canned["jobs-700.json"] = PR_JOBS_IMAGE
    canned["jobs-701.json"] = PR_JOBS_IMAGE
    canned["jobs-702.json"] = PR_JOBS_IMAGE
    canned["jobs-703.json"] = PR_JOBS_OTHER
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        env = make_scene(tmp, canned)
        ledger = tmp / "ledger.json"
        proc = run_filer(env, ledger)
        check("exit 0", proc.returncode == 0, proc.stderr)
        count = int((tmp / "canned" / "create-count").read_text().strip())
        check("three issues filed: the two master/schedule runs plus ONE PR-blockage",
              count == 3, f"create-count={count}\n{proc.stdout}")
        bodies = {p.name: p.read_text() for p in (tmp / "canned").glob("body-*.txt")}
        pr_body_txt = next((b for b in bodies.values() if "run=700" in b), None)
        check("the PR-blockage body carries the run-700 marker", pr_body_txt is not None,
              str(list(bodies)))
        if pr_body_txt:
            check("the PR-blockage body carries the scrubbed error block",
                  "make: *** [validate] Error 1" in pr_body_txt, pr_body_txt[-400:])
            check("the planted secret never reaches the PR-blockage body",
                  FAKE_SECRET not in pr_body_txt, pr_body_txt[-400:])
            check("the PR-blockage body declares the message pattern (rule 6j)",
                  all(s in pr_body_txt for s in
                      ("## Why", "## What", "## How", "## Benefits", "## Technical Solution")),
                  pr_body_txt[:400])
        data = json.loads(ledger.read_text())
        rows = [e for e in data["failures"] if e.get("trigger") == "pull_request"]
        check("exactly one PR-blockage ledger row", len(rows) == 1, str(rows))
        if rows:
            row = rows[0]
            check("the row names the two blocked OPEN PRs, not the merged branch",
                  row.get("blocked_prs") == ["ci/a", "ci/b"], str(row.get("blocked_prs")))
            check("the row's pr_count is 2", row.get("pr_count") == 2, str(row.get("pr_count")))
            check("the row carries a failure shape",
                  isinstance(row.get("failure_shape"), str) and row["failure_shape"], "")
            check("the row names the issue it filed", row.get("issue_number") is not None, "")
            check("the row's own run is the earliest of the group", row.get("run_id") == 700,
                  str(row.get("run_id")))
            check("the row keeps the filer's existing keys (append-only, rule 3b)",
                  all(k in row for k in ("targets", "error_excerpt", "filed_utc", "undiagnosed")),
                  str(sorted(row)))
        # IDEMPOTENT: a second sweep must not re-file the same blockage.
        proc2 = run_filer(env, ledger)
        count2 = int((tmp / "canned" / "create-count").read_text().strip())
        check("a second sweep files nothing more", proc2.returncode == 0 and count2 == count,
              f"count {count} -> {count2}\n{proc2.stdout}")
        rows2 = [e for e in json.loads(ledger.read_text())["failures"]
                 if e.get("trigger") == "pull_request"]
        check("the ledger still holds exactly one PR-blockage row", len(rows2) == 1, str(rows2))


def test_pr_blockage_dry_run_previews_without_writing() -> None:
    print("\nPR-blockage (#1164): --dry previews the filing and writes nothing")
    canned = dict(BASE_CANNED)
    canned["runs-qa-validate_yml-pull_request.json"] = PR_RUNS
    canned["open-prs.json"] = [{"headRefName": "ci/a"}, {"headRefName": "ci/b"}]
    canned["jobs-700.json"] = PR_JOBS_IMAGE
    canned["jobs-701.json"] = PR_JOBS_IMAGE
    canned["jobs-702.json"] = PR_JOBS_IMAGE
    canned["jobs-703.json"] = PR_JOBS_OTHER
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        env = make_scene(tmp, canned)
        ledger = tmp / "ledger.json"
        proc = run_filer(env, ledger, "--dry")
        check("exit 0", proc.returncode == 0, proc.stderr)
        check("the preview names the shape and both PRs",
              "WOULD FILE pr-blockage" in proc.stdout and "ci/a" in proc.stdout
              and "ci/b" in proc.stdout, proc.stdout)
        check("--dry files no PR-blockage issue",
              not any("run=700" in p.read_text()
                      for p in (tmp / "canned").glob("body-*.txt")), "")
        # --dry writes nothing at all, so the ledger may not even exist — read it as empty.
        written = ledger.exists() and json.loads(ledger.read_text())["failures"] or []
        check("--dry appends no PR-blockage row",
              [e for e in written if e.get("trigger") == "pull_request"] == [], str(written))


def test_pr_blockage_log_read_budget_is_bounded_and_announced() -> None:
    print("\nPR-blockage (#1174): the sweep has a bounded log-read budget and says what it skipped")
    src = FILER.read_text(encoding="utf-8")
    cap = getattr(F, "PR_BLOCK_MAX_LOG_READS", None)
    check("the cap is a positive integer", isinstance(cap, int) and cap >= 1, str(cap))
    bound = getattr(F, "bound_pr_block_runs", None)
    check("the real bound seam exists", callable(bound), str(bound))
    if callable(bound) and isinstance(cap, int) and cap >= 1:
        runs = [{"databaseId": n} for n in range(20)]
        kept, skipped = bound(runs, cap)
        check("only the capped newest runs are kept",
              len(kept) == cap and [r["databaseId"] for r in kept] == list(range(cap)),
              str([r["databaseId"] for r in kept]))
        check("the skipped count is exact", skipped == 20 - cap, str(skipped))
        try:
            bound(runs, 0)
        except ValueError:
            check("a zero cap is refused, never a silent whole-read", True, "")
        else:
            check("a zero cap is refused, never a silent whole-read", False, "no ValueError")
    check("the collection pass bounds the CANDIDATE list, not the raw page",
          "bound_pr_block_runs(candidates)" in src, "")
    check("the cheap pre-filter is its own seam", "pr_block_candidates(runs, cutoff, branches)" in src, "")
    check("the sweep line announces the budget and the skipped count",
          "log budget" in src and "skipped" in src, "")


#: Eight NEWER GREEN `pull_request` runs that fill the whole log-read budget on the base revision.
#: Their only job is to sit ahead of two red runs on open branches: bounding the raw newest-first
#: page first (issue #1405) keeps exactly these eight and never sees the red ones.
GREEN_RUNS_AHEAD = [
    {"databaseId": 710 + i, "workflowName": "qa-validate.yml", "name": "validate",
     "headBranch": f"ci/green{i}", "headSha": "1" * 40, "event": "pull_request",
     "createdAt": f"2026-11-11T{21 + i // 60:02d}:{(40 + i) % 60:02d}:00Z",
     "conclusion": "success", "status": "completed",
     "url": f"https://github.com/octo/repo/actions/runs/{710 + i}"}
    for i in range(8)
]


def test_the_read_cap_is_spent_after_the_red_open_pr_filter() -> None:
    print("\nPR-blockage (#1405): newer green runs cannot crowd a red OPEN-PR run out of the read set")
    cap = getattr(F, "PR_BLOCK_MAX_LOG_READS", None)
    check("the cap equals the planted green crowd size", isinstance(cap, int) and cap == 8,
          str(cap))
    canned = dict(BASE_CANNED)
    # Newest-first: the green crowd, then the two red runs on two different OPEN branches.
    canned["runs-qa-validate_yml-pull_request.json"] = GREEN_RUNS_AHEAD + PR_RUNS
    canned["open-prs.json"] = [{"headRefName": "ci/a"}, {"headRefName": "ci/b"},
                               {"headRefName": "ci/c"}]
    canned["jobs-700.json"] = PR_JOBS_IMAGE
    canned["jobs-701.json"] = PR_JOBS_IMAGE
    canned["jobs-703.json"] = PR_JOBS_OTHER
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        env = make_scene(tmp, canned)
        ledger = tmp / "ledger.json"
        proc = run_filer(env, ledger)
        check("exit 0", proc.returncode == 0, proc.stderr)
        bodies = {p.name: p.read_text() for p in (tmp / "canned").glob("body-*.txt")}
        pr_body_txt = next((b for b in bodies.values() if "run=700" in b), None)
        check("the red OPEN-PR shape IS grouped and filed despite the green crowd",
              pr_body_txt is not None, f"bodies={list(bodies)}\n{proc.stdout}")
        rows = [e for e in json.loads(ledger.read_text())["failures"]
                if e.get("trigger") == "pull_request"]
        check("exactly one PR-blockage row survives the crowd", len(rows) == 1, str(rows))
        if rows:
            check("the row still names the two blocked OPEN PRs",
                  rows[0].get("blocked_prs") == ["ci/a", "ci/b"], str(rows[0].get("blocked_prs")))
        check("no skipped-red-run line is invented for the discarded green runs",
              "skipped" not in proc.stdout or "skipped 0" in proc.stdout, proc.stdout)


def test_the_open_pr_branch_set_is_read_once_and_passed_down() -> None:
    print("\nPR-blockage (#1405): the open-PR branch set is computed once and passed into the pass")
    import inspect
    sig = inspect.signature(F.pr_triggered_failures)
    check("the collection pass accepts the caller's open-branch set",
          "open_branches" in sig.parameters, str(sig))
    src = FILER.read_text(encoding="utf-8")
    check("record_pr_blockages passes its own set into the pass",
          "items = pr_triggered_failures(repo, window_hours, now, stats, open_branches)" in src, "")
    check("the collection pass reads the branches itself only when handed none",
          "open_pr_branches(repo) if open_branches is None" in src, "")


def main() -> int:
    print("pipeline failure filer: a red main pipeline is diagnosed, not re-derived (issue #802)")
    test_filing_diagnoses_every_failure_with_the_log_error_block()
    test_ledger_and_marker_dedup_file_one_run_once_ever()
    test_undiagnosed_filing_is_loud_never_a_skip()
    test_rediagnose_pass_raises_a_still_undiagnosed_row_from_the_readable_log()
    test_a_raise_annotates_the_cited_issue_once()
    test_a_raise_does_not_double_annotate()
    test_a_raise_with_no_issue_cites_no_thread()
    test_a_still_unreadable_log_leaves_the_row_undiagnosed_and_retries_next_sweep()
    test_a_run_that_ages_out_stamps_log_expired_and_drains_the_queue()
    test_log_expired_dry_mode_previews_the_stamp_and_writes_nothing()
    test_a_rediagnosed_row_is_never_re_fetched_and_dry_previews_without_writing()
    test_an_escape_refused_log_is_diagnosed_on_the_flag_retry()
    test_strip_terminal_escapes_leaves_plain_text_intact()
    test_read_failures_exit_2_never_a_fake_clean()
    test_dry_run_previews_without_writing_anything()
    test_pure_halves_extract_targets_dedupe_and_cap()
    test_a_thin_failing_region_is_quoted_before_earlier_chatter()
    test_a_region_holding_the_diagnosis_keeps_today_s_order()
    test_the_makefile_line_target_form_normalises_to_the_bare_target()
    test_a_sweep_normalises_stored_rows_and_leaves_a_uniform_ledger_untouched()
    test_a_raise_renormalises_the_row_s_existing_warped_targets()
    test_a_stamped_row_with_no_error_block_is_pending_and_gets_diagnosed()
    test_the_committed_ledger_s_errorless_rows_are_exactly_the_pending_set()
    test_a_closed_row_is_stamped_from_the_merged_guard_carrying_pr_that_closed_it()
    test_the_stamp_prefers_the_guard_module_the_merged_pr_added()
    test_a_merged_fix_pr_that_only_modified_its_guard_module_still_raises_the_row()
    test_a_closed_issue_with_no_closing_pr_stays_the_keeper_s_act()
    test_an_open_issue_row_is_reported_as_a_fix_in_flight_never_stamped()
    test_a_closing_pr_not_merged_yet_is_reported_and_retried_next_sweep()
    test_a_merged_close_whose_diff_carries_no_guard_test_is_refused_loudly()
    test_the_stamp_raises_the_merged_guarded_close_when_another_closing_pr_is_unmerged()
    test_the_stamp_never_overwrites_a_guard_the_row_already_records()
    test_the_stamp_pass_is_idempotent_across_sweeps()
    test_a_stamp_read_failure_is_loud_on_its_row_and_never_fatal_to_the_sweep()
    test_a_row_citing_no_issue_is_reported_and_writes_nothing()
    test_dry_mode_previews_the_stamp_and_writes_nothing()
    test_the_stamp_rides_the_filer_s_ledger_pr_landing_through_the_makefile()
    test_ledger_pr_body_is_generated_and_carries_no_closing_keyword()
    test_wiring_rulebook_and_registry()
    test_the_module_docstring_names_the_dispatch_only_entry_point()
    test_failure_shape_groups_the_same_defect_and_separates_others()
    test_group_pr_blockages_needs_two_open_prs_and_drops_closed_branches()
    test_pr_blockage_pass_records_a_shared_failure_shape_once()
    test_pr_blockage_dry_run_previews_without_writing()
    test_pr_blockage_log_read_budget_is_bounded_and_announced()
    test_the_read_cap_is_spent_after_the_red_open_pr_filter()
    test_the_open_pr_branch_set_is_read_once_and_passed_down()
    print(f"\nPASSED {_checks_passed} | FAILED {_checks_failed}")
    return 0 if _checks_failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
