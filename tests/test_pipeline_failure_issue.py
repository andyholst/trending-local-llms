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
        wf=""; prev=""
        for a in "$@"; do [ "$prev" = "--workflow" ] && wf="$a"; prev="$a"; done
        f="$d/runs-${wf//./_}.json"
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
        if [ -f "$d/issue-state.json" ]; then cat "$d/issue-state.json"
        else echo '{"labels": [{"name": "tech-debt"}]}'; fi ;;
      edit) exit 0 ;;
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
    check("queued-alarm lands the ledger append as a PR through the Makefile",
          "make pipeline-failure-ledger-pr-body" in queue, "")
    check("the ledger PR step only fires when the filer changed the ledger",
          "git diff --quiet -- data/pipeline_failures.json" in queue, "")
    qa = QA_WF.read_text()
    check("qa-validate runs the guard as a step", "make pipeline-failure-guard-check" in qa, "")
    check("the filer marker is registered (rule 6j)",
          bm.REGISTRY.get("queued-alarm", {}).get("failure") == "pipeline-run-failure"
          and ("queued-alarm", "failure") in bm.WRITTEN, "")
    # The re-diagnosis annotation marker (issue #987) is declared via the UNREGISTERED_OWED seam —
    # its AGENTS.md §6j table row is owed to rule 3c (a protected file a headless leg cannot write),
    # so it lives here with the issue that lands the registration, a ONE-place named shape, and a
    # writer + parser in the tree (the reverse-guard scan accepts it through UNREGISTERED_OWED).
    check("the rediagnose annotation marker is DECLARED with its landing issue (rule 6j/3c)",
          bm.UNREGISTERED_OWED.get(bm.REDIAGNOSE_NAME) == 987, str(bm.UNREGISTERED_OWED))
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
        check("a row that was never UNDIAGNOSED is untouched",
              "rediagnosed_utc" not in row104, str(row104))
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
    test_ledger_pr_body_is_generated_and_carries_no_closing_keyword()
    test_wiring_rulebook_and_registry()
    print(f"\nPASSED {_checks_passed} | FAILED {_checks_failed}")
    return 0 if _checks_failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
