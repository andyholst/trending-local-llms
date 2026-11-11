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
FAKE_SECRET = "gho_FAKE0123456789fakefake"

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
2026-11-11T20:06:02Z the auth header was Bearer gho_FAKE0123456789fakefake and it printed here
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
      view)
        if [ -f "$d/issue-state.json" ]; then cat "$d/issue-state.json"
        else echo '{"labels": [{"name": "tech-debt"}]}'; fi ;;
      edit) exit 0 ;;
      *) echo "stub gh: unhandled: $*" >&2; exit 1 ;;
    esac ;;
  api)
    if [ -e "$d/log-fail" ]; then echo "stub gh: job logs unavailable (502)" >&2; exit 1; fi
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


def main() -> int:
    print("pipeline failure filer: a red main pipeline is diagnosed, not re-derived (issue #802)")
    test_filing_diagnoses_every_failure_with_the_log_error_block()
    test_ledger_and_marker_dedup_file_one_run_once_ever()
    test_undiagnosed_filing_is_loud_never_a_skip()
    test_read_failures_exit_2_never_a_fake_clean()
    test_dry_run_previews_without_writing_anything()
    test_pure_halves_extract_targets_dedupe_and_cap()
    test_ledger_pr_body_is_generated_and_carries_no_closing_keyword()
    test_wiring_rulebook_and_registry()
    print(f"\nPASSED {_checks_passed} | FAILED {_checks_failed}")
    return 0 if _checks_failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
