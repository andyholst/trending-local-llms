#!/usr/bin/env python3
"""The filer's error block must name the FAILING STEP, not whatever filled the cap (issue #1098).

Drives the REAL `scripts/pipeline_failure_issue.py`: the pure seams directly, and the filing and
re-diagnosis passes end to end through the stub `gh` fixture imported from
`tests/test_pipeline_failure_issue.py` (rule 6m: an EXTERNAL stand-in for the GitHub API, never a
replacement for the logic under test).

What this locks, measured on the real failure (qa-validate run 43725338063, job 132845951479): the
job's 60 KB log tail held 46 error-shaped lines in its last 60 KB, 43 of them printed by steps
that SUCCEEDED (`FAIL: m1: engines not ordered newest-date-first`, `PASSED 199 | FAILED 0`), and the
three lines that diagnosed the run — `[openspec-index] FAIL OPENSPEC.md is stale or missing (2
active, 305 archived on disk)`, `make: *** [Makefile:367: openspec-index-check] Error 1`,
`##[error]Process completed with exit code 2.` — were hits #43-#45 and were CUT by the 40-line cap.
Ledger rows 43716345030 / 43716362366 / 43718826142 / 43725338063 therefore carry `targets: []` and
issues #1040-#1043 were filed quoting a passing module's fixture chatter: the reproduction command
the filer promises was never read. RED against the pre-#1098 extractor — check it by running this
module against `git show origin/master:scripts/pipeline_failure_issue.py`: the two diagnosis lines
below are absent there.
"""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "tests"))

import pipeline_failure_issue as F  # noqa: E402
import test_pipeline_failure_issue as PF  # noqa: E402  (the stub-gh fixture, imported not copied)

check = PF.check
TS = "2026-11-15T14:50:"

#: The two lines that diagnose the measured failure, exactly as the runner printed them.
INDEX_STALE = ("[openspec-index] FAIL OPENSPEC.md is stale or missing (2 active, 305 archived on "
               "disk) — run `make openspec-index`")
REFUSAL = "make: *** [Makefile:367: openspec-index-check] Error 1"
EXIT_LINE = "##[error]Process completed with exit code 2."

#: GitHub's OWN names for the steps of job 132845951479 (measured: `gh run view 43725338063 --json
#: jobs` → the OpenSpec gate step is `failure`, everything after it is `skipped`).
STEPS = [
    {"name": "Set up job", "conclusion": "success"},
    {"name": "Run actions/checkout", "conclusion": "success"},
    {"name": "Run make image-ensure", "conclusion": "success"},
    {"name": "OpenSpec gate (changes validate, tasks ticked, index current)",
     "conclusion": "failure"},
    {"name": "Pipeline-failure ledger (every closed failure carries its guard; issue #1053)",
     "conclusion": "skipped"},
    {"name": "Architecture description (rule 6h)", "conclusion": "skipped"},
    {"name": "Run unit tests (in container)", "conclusion": "skipped"},
    {"name": "Post Checkout", "conclusion": "success"},
    {"name": "Complete job", "conclusion": "success"},
]
FAILED_STEP = "OpenSpec gate (changes validate, tasks ticked, index current)"
#: What the failing region's error-shaped lines name: the guard line's quoted run of
#: `make openspec-index` and the make refusal's bracketed target. The step's own echoed command is
#: not error-shaped, so it is not in the block, and the filer's drop note is skipped by
#: `failed_make_targets` — a target comes from a LOG line or not at all (issue #1098).
DIAG_TARGETS = ["openspec-index", "openspec-index-check"]
FAILED_REGION = "Run make openspec-check"


def chatter_lines(minute: int, n: int) -> list[str]:
    """What a PASSING module prints: a planted fixture's `FAIL:` verdicts and its own tally.

    Every line is unique (the extractor de-dupes), so a budget that fills with chatter is filling
    with chatter, not with copies of one line — and the planted count is above the cap on purpose:
    the measured job had 43 of them before the diagnosis line arrived.
    """
    out = [f"2026-11-15T15:{minute + i // 60:02d}:{i % 60:02d}Z   FAIL: m1: engine 'llama.cpp' tps "
           f"is not a clean number: '~{200 + i} decode'" for i in range(n)]
    out.append("2026-11-15T15:59:59Z PASSED 199 | FAILED 0")
    return out


#: A quoted line keeps its runner timestamp, so a needle is matched INSIDE a line, never as one.
def quoted(block: list[str], needle: str) -> bool:
    return any(needle in line for line in block)


#: The measured log shape: succeeded regions full of verdict chatter, then the region GitHub's own
#: `##[error]` decoration marks as the step that ended the job.
MEASURED_LOG = "\n".join(
    [f"{TS}00Z ##[group]Run make secret-scan-self-test",
     "2026-11-15T14:50:01Z gitleaks detected 0 secrets",
     f"{TS}02Z ##[endgroup]",
     f"{TS}06Z ##[group]Run make validate"]
    + chatter_lines(0, 60)
    + ["2026-11-15T15:01:59Z ##[endgroup]",
       "2026-11-15T15:02:11Z ##[group]Run make test"]
    + chatter_lines(20, 60)
    + ["2026-11-15T15:03:59Z ##[endgroup]",
       f"2026-11-15T15:04:20Z ##[group]{FAILED_REGION}",
       "2026-11-15T15:04:21Z make openspec-check",
       f"2026-11-15T15:04:22Z {INDEX_STALE}",
       f"2026-11-15T15:04:23Z {REFUSAL}",
       f"2026-11-15T15:04:24Z {EXIT_LINE}",
       "2026-11-15T15:04:25Z ##[endgroup]",
       "2026-11-15T14:52:30Z ##[group]Post Checkout",
       "2026-11-15T14:52:31Z Job cleanup complete",
       "2026-11-15T14:52:32Z ##[endgroup]"]
) + "\n"

JOBS_MEASURED = {"jobs": [
    {"databaseId": 900, "name": "validate", "conclusion": "failure", "steps": STEPS},
    {"databaseId": 901, "name": "live-smoke", "conclusion": "skipped"},
]}


def _canned() -> dict:
    return {
        # The filer's candidate scan pages the REST `actions/runs` feed (issue #1467), so the
        # fixture is the REAL snake_case row shape the feed serves — the product's ONE projection
        # runs for real instead of being bypassed by a pre-projected fixture.
        "window-qa-validate_yml-none-p1.json": PF.RUNS_QA_REST,
        "jobs-100.json": JOBS_MEASURED,
        "jobs-104.json": PF.JOBS_104,
        "log.txt": MEASURED_LOG,
        "issues.json": [],
    }


def test_a_passing_module_s_chatter_cannot_crowd_out_the_refusal_that_ended_the_job() -> None:
    print("\n#1098: the diagnosis survives the cap; a passing module's chatter does not own it")
    block = F.extract_error_block(MEASURED_LOG)
    check("the make refusal that ended the job is quoted", quoted(block, REFUSAL),
          "\n".join(block[-6:]))
    check("the guard line explaining the refusal is quoted", quoted(block, INDEX_STALE),
          "\n".join(block[:6]))
    check("GitHub's own error decoration is quoted", quoted(block, EXIT_LINE),
          "\n".join(block[-6:]))
    check("the block stays within the cap", len(block) <= F.MAX_ERROR_LINES, str(len(block)))
    check("the reproduction targets the failing region names are now derived",
          F.failed_make_targets(block) == DIAG_TARGETS, str(F.failed_make_targets(block)))
    check("the filer's own drop note never becomes a reproduction command",
          F.failed_make_targets([F.ANCHORED_DROP_NOTE.format(
              kept=3, want=3, region="Run make openspec-check", dropped=85, cap=40)]) == [],
          F.ANCHORED_DROP_NOTE.format(kept=3, want=3, region="Run make openspec-check",
                                      dropped=85, cap=40))
    # The measured old behaviour: 40 lines of `FAIL: m1:` and no refusal. The new tiers let the
    # diagnosis in FIRST, so chatter is what loses.
    chatter = [line for line in block if "FAIL: m1" in line]
    check("chatter is what fills the SPARE room, never the diagnosis",
          len(chatter) <= F.MAX_ERROR_LINES - 4, str(len(chatter)))


def test_the_failing_step_is_named_from_github_s_own_steps_and_the_log_region() -> None:
    print("\n#1098: two real sources name the step — GitHub's steps[] and the ##[group] label")
    regions = F.log_regions(MEASURED_LOG)
    labels = [r["label"] for r in regions]
    check("the log splits into GitHub's step regions", FAILED_REGION in labels, str(labels))
    failed = next(r for r in regions if r["label"] == FAILED_REGION)
    check("a region's lines are its CONTENT; the ##[group] marker is the label, never a line",
          all(not raw.lstrip().startswith("##[") for _i, raw in failed["lines"])
          and any(INDEX_STALE in raw for _i, raw in failed["lines"]), str(failed)[:300])
    check("the failing region is the one carrying ##[error]",
          F.failing_region(regions)["label"] == FAILED_REGION, str(labels))
    check("error_region names the region the block came from",
          F.error_region(MEASURED_LOG) == FAILED_REGION, F.error_region(MEASURED_LOG))
    check("failing_step_names answers ONLY the step GitHub marked bad",
          F.failing_step_names(JOBS_MEASURED["jobs"][0]) == [FAILED_STEP],
          str(F.failing_step_names(JOBS_MEASURED["jobs"][0])))
    check("a skipped step is not a failing step",
          "Run unit tests (in container)" not in F.failing_step_names(JOBS_MEASURED["jobs"][0]), "")
    check("a payload with no steps names nothing rather than guessing",
          F.failing_step_names({"name": "validate"}) == [], "")
    check("the provenance sentence names both sources",
          FAILED_STEP in F.step_provenance(JOBS_MEASURED["jobs"][0], [FAILED_STEP],
                                           FAILED_REGION)
          and FAILED_REGION in F.step_provenance({}, [FAILED_STEP], FAILED_REGION),
          F.step_provenance(JOBS_MEASURED["jobs"][0], [FAILED_STEP], FAILED_REGION))
    check("and says so plainly when neither source exists",
          "no failed step" in F.step_provenance({}, [], ""), F.step_provenance({}, [], ""))


def test_chatter_dropped_for_room_is_announced_in_the_block() -> None:
    print("\n#1098: a truncated diagnosis is loud (rule 2), never a silent cut")
    block = F.extract_error_block(MEASURED_LOG)
    note = block[-1]
    check("the block ends with the drop note", note.startswith("[filer]"), note)
    check("the note names how many lines were left out and the cap",
          "further error-shaped line(s)" in note and "were not quoted" in note
          and f"MAX_ERROR_LINES={F.MAX_ERROR_LINES}" in note, note)
    check("the note names the failing region it DID quote in full",
          FAILED_REGION in note          and "3/3" in note, note)
    check("the filer's own drop note is never read as a reproduction command",
          "openspec-check" not in F.failed_make_targets(block),
          str(F.failed_make_targets(block)))
    failing = F.failing_region(F.log_regions(MEASURED_LOG))
    wanted = [raw.rstrip() for _i, raw in failing["lines"]
              if any(s in raw for s in F._STRONG_SHAPES + F._SOFT_SHAPES)]
    missing = [w for w in wanted if not any(w in line for line in block)]
    check("EVERY error-shaped line of the failing region survives the cap", not missing,
          str(missing))
    region_lines = {raw.rstrip() for _i, raw in failing["lines"]}
    seq = [("marker" if line.startswith("[filer]")
            else ("region" if line in region_lines else "other"))
           for line in block[:-1]]
    order = {"region": 0, "marker": 1, "other": 2}
    check("the failing region's lines come FIRST, then the filler marker, then other-step lines",
          seq == sorted(seq, key=lambda s: order[s]), str(seq))
    quoted = [line for line in block[:-1] if not line.startswith("[filer]")]
    region_idx = [MEASURED_LOG.splitlines().index(line) for line in quoted if line in region_lines]
    other_idx = [MEASURED_LOG.splitlines().index(line) for line in quoted if line not in region_lines]
    check("quoted lines keep their log order WITHIN each group",
          region_idx == sorted(region_idx) and other_idx == sorted(other_idx),
          str((region_idx, other_idx)))


def test_a_log_without_group_markers_still_yields_a_diagnosis() -> None:
    print("\n#1098: an ungrouped (truncated) log still yields the strong lines, invents no region")
    ungroupled = "\n".join(line for line in MEASURED_LOG.splitlines()
                           if "##[group" not in line and "##[endgroup" not in line)
    block = F.extract_error_block(ungroupled)
    check("the refusal is still quoted", quoted(block, REFUSAL), "\n".join(block[:4]))
    check("GitHub's error decoration is still quoted", quoted(block, EXIT_LINE),
          "\n".join(block[:4]))
    check("no region is invented for a log that names none", F.error_region(ungroupled) == "",
          F.error_region(ungroupled))
    check("a log with no error-shaped line yields NO block (the caller files UNDIAGNOSED)",
          F.extract_error_block("2026-11-15T14:52:00Z everything finished cleanly\n") == [], "")


def test_the_ledger_row_carries_the_diagnosis_and_re_diagnosis_reuses_the_seam() -> None:
    print("\n#1098: filed issue + ledger row name the step; a re-diagnosis raises the same keys")
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        env = PF.make_scene(tmp, _canned())
        ledger = tmp / "ledger.json"
        proc = PF.run_filer(env, ledger)
        check("sweep exits 0", proc.returncode == 0, proc.stderr)
        check("the sweep line names the step and the region it read",
              FAILED_STEP in proc.stdout and FAILED_REGION in proc.stdout, proc.stdout[:500])
        bodies = {p.name: p.read_text() for p in (tmp / "canned").glob("body-*.txt")}
        body = next(b for b in bodies.values() if "run=100" in b)
        check("the filed body names the step GitHub marked bad", FAILED_STEP in body, body[:400])
        check("the filed body names the log region the block came from", FAILED_REGION in body,
              body[:400])
        check("the filed body quotes the refusal, not only chatter", REFUSAL in body, body[:600])
        check("the reproduction command is the target the refusal names",
              "make openspec-index-check" in body, body[:600])
        check("every message-pattern section is still there (rule #771)",
              all(s in body for s in ("## Why", "## What", "## How", "## Benefits",
                                      "## Technical Solution")), body[:200])
        row = {e["run_id"]: e for e in json.loads(ledger.read_text())["failures"]}[100]
        check("the ledger row records the failing step (additive key)",
              row.get("failing_steps") == [FAILED_STEP], str(row)[:300])
        check("the ledger row records the error region (additive key)",
              row.get("error_region") == FAILED_REGION, str(row)[:300])
        check("the row's targets are the diagnosis, not empty",
              row.get("targets") == DIAG_TARGETS, str(row)[:300])
        check("no existing key was removed from a filing row",
              {"run_id", "workflow", "job", "targets", "issue_number", "fix_pr", "guard",
               "undiagnosed"} <= set(row), str(sorted(row))[:300])

    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        env = PF.make_scene(tmp, _canned())
        row = dict(PF.UNDIAG_ROW)
        ledger = PF._seed_ledger(tmp, [row])
        proc = PF.run_filer(env, ledger)
        check("rediagnose pass runs", proc.returncode == 0 and "REDIAGNOSED run 100" in proc.stdout,
              proc.stdout[:400])
        raised = {e["run_id"]: e for e in json.loads(ledger.read_text())["failures"]}[100]
        check("the raised excerpt came from the failing region (same seam)",
              REFUSAL in raised.get("error_excerpt", ""), str(raised.get("error_excerpt"))[:300])
        check("the raised row names the step", raised.get("failing_steps") == [FAILED_STEP],
              str(raised)[:300])
        check("the raised row names the region", raised.get("error_region") == FAILED_REGION,
              str(raised)[:300])
        check("targets GROWN only, the original undiagnosed field KEPT (rule 3b)",
              raised.get("targets") == DIAG_TARGETS
              and raised.get("undiagnosed") == row["undiagnosed"], str(raised)[:400])


def test_every_extraction_call_site_passes_the_job() -> None:
    print("\n#1098 wiring: no call site extracts the log without the job it belongs to")
    src = (ROOT / "scripts" / "pipeline_failure_issue.py").read_text()
    check("the sweep extracts anchored on its job", 'extract_error_block(log_text, job=job)' in src,
          "")
    check("the re-diagnosis pass extracts anchored on its job",
          'extract_error_block(log_text, job=match)' in src, "")
    check("no extraction reads the log a second time through a different view",
          src.count("fetch_log(repo, job[\"databaseId\"])") == 1
          and src.count("fetch_log(repo, match[\"databaseId\"])") == 1, "")
    check("the Makefile still files through the one target (rule 6m)",
          "pipeline-failure-issue" in (ROOT / "Makefile").read_text()
          and "make pipeline-failure-issue" in (ROOT / ".github" / "workflows"
                                                / "queued-alarm.yml").read_text(), "")


def main() -> int:
    test_a_passing_module_s_chatter_cannot_crowd_out_the_refusal_that_ended_the_job()
    test_the_failing_step_is_named_from_github_s_own_steps_and_the_log_region()
    test_chatter_dropped_for_room_is_announced_in_the_block()
    test_a_log_without_group_markers_still_yields_a_diagnosis()
    test_the_ledger_row_carries_the_diagnosis_and_re_diagnosis_reuses_the_seam()
    test_every_extraction_call_site_passes_the_job()
    print(f"\nPASSED {PF._checks_passed} | FAILED {PF._checks_failed}")
    return 0 if PF._checks_failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
