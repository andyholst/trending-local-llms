#!/usr/bin/env python3
"""The ledger ATTRIBUTION seam (issue #1053, AGENTS.md rule 6r).

The stamp pass (issue #1099) raises `fix_pr` + `guard` onto a ledger row only when a MERGED,
guard-carrying PR CLOSED that row's issue. The measured exceptions are issue #1053's three rows —
#826 (run 42976201014), #827 (run 42977708147), #828 (run 43047130543): their issues are OPEN and
held by an `agent:refined` verdict hold (rule 6j: a decided hold has no expiry), while the fix that
actually landed was a DIFFERENT merged PR. Without an attribution half, those rows sit with a null
`fix_pr` forever and a landed fix has no honest way to be recorded.

This suite drives the REAL `scripts/pipeline_failure_issue.py` attribution pass end to end against
the stub `gh` fixture from `tests/test_pipeline_failure_issue.py` — an EXTERNAL stand-in for the
GitHub API only (rule 6m): every decision (row lookup, merged state, guard proof, evidence proof,
annotation dedup, the append-only raise) is executed by the product. Nothing here replaces the
logic under test. The fixture is IMPORTED, not copied (rule 6d: one fixture, no drift).

The refusals this locks: an unmerged PR, a guard `make test` does not collect, a guard the fix PR's
own diff never names, evidence that names nothing the fix touched (or cites the ledger the pass
writes), a claim on an undiagnosed/expired row, a claim that would replace a recorded fix. Each
refusal exits 2 and writes NOTHING. And the skeptic's closure: a `CLOSED:` verdict that cites a
ledger run is accepted ONLY when that row names a merged fix PR + a collected guard — so an
attribution can be made exactly once, by proof, never by prose.
"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "tests"))

import bot_markers as bm  # noqa: E402
import test_pipeline_failure_issue as PF  # noqa: E402  (the stub-gh fixture, imported not copied)

FILER = ROOT / "scripts" / "pipeline_failure_issue.py"
VERDICT = ROOT / "scripts" / "issue_verdict.py"
MAKEFILE = ROOT / "Makefile"
QUEUE_WF = ROOT / ".github" / "workflows" / "queued-alarm.yml"
AGENTS = ROOT / "AGENTS.md"

REPO = PF.REPO
NOW = PF.NOW
#: The measured rows issue #1053 is about: OPEN issues held by a verdict label, fix landed elsewhere.
HELD_ROW = {
    "run_id": 42976201014,
    "run_url": "https://github.com/octo/repo/actions/runs/42976201014",
    "workflow": "issue-bot.yml",
    "job": "implement",
    "targets": ["implement-issue"],
    "error_excerpt": "make: *** [Makefile:1384: implement-issue] Error 2",
    "issue_number": 826,
    "issue_url": "https://github.com/octo/repo/issues/826",
    "filed_utc": "2026-11-12T06:00:00Z",
}
#: A landed fix that did NOT close the issue: merged, and its diff carries the guard module.
FIX_PR = {
    "number": 1101,
    "title": "fix(pipeline-failure): land the ledger append as a reviewed PR",
    "mergedAt": "2026-11-16T10:00:00Z",
    "files": [
        {"path": "scripts/pipeline_failure_issue.py", "changeType": "MODIFIED"},
        {"path": "tests/test_pipeline_failure_issue.py", "changeType": "MODIFIED"},
    ],
}
#: A merged PR whose diff touches no test at all — never a fix under rule 6r.
FIX_PR_NO_GUARD = {
    "number": 1102,
    "title": "chore: reword a docstring",
    "mergedAt": "2026-11-16T11:00:00Z",
    "files": [{"path": "README.md", "changeType": "MODIFIED"}],
}
#: An OPEN PR — a fix in flight, never an attribution.
FIX_PR_UNMERGED = {
    "number": 1103,
    "title": "fix: a fix still under review",
    "mergedAt": None,
    "files": [{"path": "tests/test_pipeline_failure_issue.py", "changeType": "ADDED"}],
}
ISSUE_OPEN = {"state": "OPEN", "closedByPullRequestsReferences": []}
ISSUE_CLOSED_NO_PR = {"state": "CLOSED", "closedByPullRequestsReferences": []}

#: Real modules in this tree (`guard_test_exists` reads the tree, so claims must name real ones).
GUARD = "tests/test_pipeline_failure_issue.py"
GUARD_QUALIFIED = f"{GUARD}::test_filing_diagnoses_every_failure_with_the_log_error_block"
#: The guard module IS in FIX_PR's diff, so this evidence is tied to the fix (and cites the seam).
EVIDENCE = "make pipeline-failure-issue — scripts/pipeline_failure_issue.py stamps a merged fix PR"

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


def scene(tmp: Path, canned: dict) -> dict:
    return PF.make_scene(tmp, canned)


def write_ledger(tmp: Path, rows: list[dict]) -> Path:
    path = tmp / "ledger.json"
    path.write_text(json.dumps({"failures": rows}, indent=2) + "\n", encoding="utf-8")
    return path


def run_attr(env: dict, ledger: Path, *extra: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(FILER), "--repo", REPO, "--ledger", str(ledger), "--now", NOW, *extra],
        capture_output=True, text=True, timeout=120, env=env)


def rows_of(ledger: Path) -> list[dict]:
    return json.loads(ledger.read_text(encoding="utf-8"))["failures"]


def comments_written(tmp: Path) -> list[str]:
    out = []
    for p in sorted((tmp / "canned").glob("comment-*.txt")):
        out.append(p.read_text(encoding="utf-8"))
    return out


BASE_CANNED = {
    "runs-issue-bot_yml.json": [],
    "runs-qa-validate_yml.json": [],
    "runs-refresh-bot_yml.json": [],
    "runs-issue-review-bot_yml.json": [],
    "runs-architecture-bot_yml.json": [],
    "runs-queued-alarm_yml.json": [],
    "issues.json": [],
    "issue-view-826.json": ISSUE_OPEN,
    "pr-1101.json": FIX_PR,
    "pr-1102.json": FIX_PR_NO_GUARD,
    "pr-1103.json": FIX_PR_UNMERGED,
    # The stub serves a comment thread as one JSON object PER LINE; an empty thread is an
    # empty file, not "[]" (which would parse as one comment that is a list).
    "thread-826.json": "",
}


# ---------------------------------------------------------------------------
# the raise
# ---------------------------------------------------------------------------

def _attribution_step(wf: str) -> str:
    """The attribution step's own block in queued-alarm.yml (from its name to the next step)."""
    lines = wf.splitlines()
    start = next(i for i, ln in enumerate(lines)
                 if "Report unattributed diagnosed rows" in ln)
    end = next((i for i in range(start + 1, len(lines)) if lines[i].lstrip().startswith("- name:")),
               len(lines))
    return "\n".join(lines[start:end])


def test_an_open_verdict_held_row_raises_from_a_merged_guard_carrying_fix() -> None:
    print("\nattribution: an OPEN verdict-held row raises from an attested merged fix PR")
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        env = scene(tmp, dict(BASE_CANNED))
        ledger = write_ledger(tmp, [dict(HELD_ROW)])
        before = ledger.read_text()
        proc = run_attr(env, ledger, "--attribute", "--run", str(HELD_ROW["run_id"]),
                        "--fix-pr", "1101", "--guard", GUARD_QUALIFIED, "--evidence", EVIDENCE)
        check("exit 0", proc.returncode == 0, proc.stderr)
        check("names the raise", "ATTRIBUTED run 42976201014" in proc.stdout, proc.stdout)
        row = rows_of(ledger)[0]
        check("fix_pr raised", row.get("fix_pr") == 1101, str(row))
        check("guard raised", row.get("guard") == GUARD, str(row))
        check("merged stamp recorded", bool(row.get("fix_pr_merged_utc")), str(row))
        check("evidence recorded", EVIDENCE in (row.get("attribution_evidence") or ""), str(row))
        check("the note names the seam", "pipeline-failure-attribute" in (row.get("stamp_note") or ""),
              str(row))
        # rule 3b: nothing the row already carried was removed or shrunk.
        check("every original key survives",
              all(k in row for k in HELD_ROW), str(sorted(row)))
        check("targets preserved", row.get("targets") == HELD_ROW["targets"], str(row))
        check("the append grew the row", len(row) > len(HELD_ROW), str(row))
        thread = comments_written(tmp)
        check("ONE annotation comment", len(thread) == 1, "\n".join(thread))
        body = thread[0] if thread else ""
        check("the annotation carries the attribution marker",
              bm.attribution_marker_run(body) == str(HELD_ROW["run_id"]), body[:400])
        check("the annotation names the fix PR and the guard",
              "#1101" in body and GUARD in body, body[:400])
        check("the annotation says WHY the automatic pass could not reach it",
              "stamp pass could not reach" in body, body[:400])


def test_the_attribution_is_idempotent_and_marker_deduplicated() -> None:
    print("\nattribution: a second claim on the same fix is a no-op, and a threaded row is not re-commented")
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        env = scene(tmp, dict(BASE_CANNED))
        ledger = write_ledger(tmp, [dict(HELD_ROW)])
        first = run_attr(env, ledger, "--attribute", "--run", str(HELD_ROW["run_id"]),
                         "--fix-pr", "1101", "--guard", GUARD, "--evidence", EVIDENCE)
        check("first claim raises", first.returncode == 0, first.stderr)
        after_first = ledger.read_text()
        second = run_attr(env, ledger, "--attribute", "--run", str(HELD_ROW["run_id"]),
                          "--fix-pr", "1101", "--guard", GUARD, "--evidence", EVIDENCE)
        check("second claim exits 0 as a no-op", second.returncode == 0, second.stderr)
        check("second claim says no-op", "no-op" in second.stdout, second.stdout)
        check("the ledger is byte-identical after the no-op",
              ledger.read_text() == after_first, "the row was rewritten")
        check("no second comment on the thread", len(comments_written(tmp)) == 1,
              f"{len(comments_written(tmp))} comments")


def test_the_stamp_pass_still_skips_an_open_row_and_the_report_names_it() -> None:
    print("\nattribution: the stamp pass does NOT stamp an open row; the report pass makes it loud")
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        env = scene(tmp, dict(BASE_CANNED))
        ledger = write_ledger(tmp, [dict(HELD_ROW)])
        before = ledger.read_text()
        sweep = run_attr(env, ledger)  # the filer sweep: no runs canned, nothing to file
        check("sweep exits 0", sweep.returncode == 0, sweep.stderr)
        check("the sweep filed nothing", not (tmp / "canned" / "create-count").exists(), "")
        check("the open row is NOT stamped by the sweep",
              not rows_of(ledger)[0].get("fix_pr"), str(rows_of(ledger)[0]))
        check("the open row is reported as a fix in flight",
              "826" in sweep.stdout and "open" in sweep.stdout.lower(), sweep.stdout)
        report = run_attr(env, ledger, "--attribute-report")
        check("report exits 0", report.returncode == 0, report.stderr)
        check("report names the unattributed row",
              "UNATTRIBUTED run 42976201014" in report.stdout, report.stdout)
        check("report reads the issue state for the reason",
              "issue #826 is OPEN" in report.stdout, report.stdout)
        check("report prints the exact remedy command",
              "make pipeline-failure-attribute REPO=octo/repo RUN=42976201014" in report.stdout,
              report.stdout)
        check("report writes nothing", ledger.read_text() == before, "the ledger changed")
        check("report writes no comment", not comments_written(tmp), "")


def test_report_mode_excludes_stamped_expired_and_undiagnosed_rows() -> None:
    print("\nattribution: the report set is diagnosed-and-unattributed rows only")
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        canned = dict(BASE_CANNED)
        canned["issue-view-900.json"] = ISSUE_OPEN
        env = scene(tmp, canned)
        stamped = dict(HELD_ROW, run_id=800, issue_number=800, fix_pr=1057, guard=GUARD)
        expired = dict(HELD_ROW, run_id=801, issue_number=801, log_expired="log still unreadable")
        undiagnosed = dict(HELD_ROW, run_id=802, issue_number=802, undiagnosed="log fetch failed")
        del undiagnosed["error_excerpt"]
        open_row = dict(HELD_ROW, run_id=900, issue_number=900)
        ledger = write_ledger(tmp, [stamped, expired, undiagnosed, open_row])
        before = ledger.read_text()
        proc = run_attr(env, ledger, "--attribute-report")
        check("exit 0", proc.returncode == 0, proc.stderr)
        check("the open unattributed row is named", "UNATTRIBUTED run 900" in proc.stdout, proc.stdout)
        check("the stamped row is not named", "UNATTRIBUTED run 800" not in proc.stdout, proc.stdout)
        check("the log_expired drain is not named", "UNATTRIBUTED run 801" not in proc.stdout, proc.stdout)
        check("the undiagnosed row is not named (re-diagnosis owns it)",
              "UNATTRIBUTED run 802" not in proc.stdout, proc.stdout)
        check("the count line names exactly one row",
              "unattributed_diagnosed_rows=1" in proc.stdout, proc.stdout)
        check("no ledger write", ledger.read_text() == before, "changed")


def test_a_closed_issue_with_no_closing_pr_reports_the_manual_close_shape() -> None:
    print("\nattribution: a CLOSED issue with no closing PR reads as a manual close, not a stamped fix")
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        canned = dict(BASE_CANNED)
        canned["issue-view-905.json"] = ISSUE_CLOSED_NO_PR
        env = scene(tmp, canned)
        row = dict(HELD_ROW, run_id=905, issue_number=905)
        ledger = write_ledger(tmp, [row])
        proc = run_attr(env, ledger, "--attribute-report")
        check("exit 0", proc.returncode == 0, proc.stderr)
        check("names the manual close", "no closing PR" in proc.stdout or "manual close" in proc.stdout,
              proc.stdout)
        check("still no fix_pr written", not rows_of(ledger)[0].get("fix_pr"), str(rows_of(ledger)[0]))


# ---------------------------------------------------------------------------
# the refusals — each exits 2 and writes NOTHING
# ---------------------------------------------------------------------------

def refused(name: str, tmp: Path, ledger: Path, claim: list[str], needle: str,
            canned: dict | None = None) -> None:
    env = scene(tmp, canned or dict(BASE_CANNED))
    before = ledger.read_text()
    proc = run_attr(env, ledger, "--attribute", *claim)
    check(f"{name}: exit 2", proc.returncode == 2, f"rc={proc.returncode} out={proc.stdout}")
    check(f"{name}: refuses loudly", needle in proc.stderr, proc.stderr[:400])
    check(f"{name}: writes no ledger change", ledger.read_text() == before, "ledger changed")
    check(f"{name}: writes no comment", not comments_written(tmp), "")
    row = rows_of(ledger)[0]
    check(f"{name}: the row keeps no fix_pr/guard", not row.get("fix_pr") and not row.get("guard"),
          str(row))


def test_an_unmerged_fix_pr_refuses_the_attribution() -> None:
    print("\nrefusal: an unmerged PR is a fix in flight, never an attribution")
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        ledger = write_ledger(tmp, [dict(HELD_ROW)])
        refused("unmerged PR", tmp, ledger,
                ["--run", str(HELD_ROW["run_id"]), "--fix-pr", "1103", "--guard", GUARD,
                 "--evidence", EVIDENCE], "NOT merged")


def test_a_guard_make_test_does_not_collect_refuses_the_attribution() -> None:
    print("\nrefusal: a guard that is not a collected tests/test_*.py module is refused")
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        ledger = write_ledger(tmp, [dict(HELD_ROW)])
        refused("uncollected guard", tmp, ledger,
                ["--run", str(HELD_ROW["run_id"]), "--fix-pr", "1101",
                 "--guard", "tests/test_a_guard_that_does_not_exist.py", "--evidence", EVIDENCE],
                "not a `tests/test_*.py` module")


def test_a_named_guard_test_that_the_module_does_not_define_refuses() -> None:
    print("\nrefusal: a guard naming a ::test the module does not define is refused")
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        ledger = write_ledger(tmp, [dict(HELD_ROW)])
        refused("invented test name", tmp, ledger,
                ["--run", str(HELD_ROW["run_id"]), "--fix-pr", "1101",
                 "--guard", f"{GUARD}::test_a_test_nobody_wrote", "--evidence", EVIDENCE],
                "does not define")


def test_a_guard_the_fix_pr_diff_never_names_refuses_the_attribution() -> None:
    print("\nrefusal: a guard the claimed fix PR's own diff does not touch is not tied to the fix")
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        ledger = write_ledger(tmp, [dict(HELD_ROW)])
        # tests/test_workflows.py IS a collected module in this tree, but PR #1101 never touched it.
        refused("guard not in the fix diff", tmp, ledger,
                ["--run", str(HELD_ROW["run_id"]), "--fix-pr", "1101",
                 "--guard", "tests/test_workflows.py",
                 "--evidence", "scripts/pipeline_failure_issue.py stamps a merged fix PR"],
                "not in the fix PR's own diff")


def test_evidence_that_names_nothing_the_fix_touched_refuses() -> None:
    print("\nrefusal: evidence must name something the fix PR touched (or the guard module)")
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        ledger = write_ledger(tmp, [dict(HELD_ROW)])
        refused("untied evidence", tmp, ledger,
                ["--run", str(HELD_ROW["run_id"]), "--fix-pr", "1101", "--guard", GUARD,
                 "--evidence", "make lint is green on master today"],
                "names nothing this fix PR touched")


def test_prose_only_evidence_refuses_the_attribution() -> None:
    print("\nrefusal: EVIDENCE that cites no path, file or command is prose, not proof")
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        ledger = write_ledger(tmp, [dict(HELD_ROW)])
        refused("prose evidence", tmp, ledger,
                ["--run", str(HELD_ROW["run_id"]), "--fix-pr", "1101", "--guard", GUARD,
                 "--evidence", "I reviewed the run logs and this error class looks fixed"],
                "names nothing checkable")


def test_evidence_citing_a_path_that_does_not_exist_refuses() -> None:
    print("\nrefusal: evidence may not cite a repo path that is not in the tree")
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        ledger = write_ledger(tmp, [dict(HELD_ROW)])
        refused("phantom path", tmp, ledger,
                ["--run", str(HELD_ROW["run_id"]), "--fix-pr", "1101", "--guard", GUARD,
                 "--evidence", "scripts/a_script_that_was_never_written.py:12 proves it"],
                "does not exist in the tree")


def test_evidence_citing_the_ledger_itself_is_refused_as_circular() -> None:
    print("\nrefusal: evidence may not cite the ledger this pass writes (the #993 circularity)")
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        ledger = write_ledger(tmp, [dict(HELD_ROW)])
        refused("circular evidence", tmp, ledger,
                ["--run", str(HELD_ROW["run_id"]), "--fix-pr", "1101", "--guard", GUARD,
                 "--evidence", "data/pipeline_failures.json run=42976201014 shows the fix landed"],
                "circular")


def test_an_undiagnosed_row_refuses_an_attribution_claim() -> None:
    print("\nrefusal: an UNDIAGNOSED row belongs to re-diagnosis, not to an attribution")
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        row = dict(HELD_ROW)
        del row["error_excerpt"]
        row["undiagnosed"] = "log fetch for job 900 failed twice"
        ledger = write_ledger(tmp, [row])
        refused("undiagnosed row", tmp, ledger,
                ["--run", str(HELD_ROW["run_id"]), "--fix-pr", "1101", "--guard", GUARD,
                 "--evidence", EVIDENCE], "still UNDIAGNOSED")


def test_the_terminal_log_expired_drain_refuses_an_attribution() -> None:
    print("\nrefusal: the terminal `log_expired` row (issue #986) has no known error class")
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        row = dict(HELD_ROW, log_expired="log still unreadable after 3 sweeps")
        ledger = write_ledger(tmp, [row])
        refused("log_expired row", tmp, ledger,
                ["--run", str(HELD_ROW["run_id"]), "--fix-pr", "1101", "--guard", GUARD,
                 "--evidence", EVIDENCE], "log_expired")


def test_a_row_that_already_names_a_different_fix_pr_refuses_replacing_it() -> None:
    print("\nrefusal: a row carries ONE landed fix — an attribution may not replace it (rule 3b)")
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        row = dict(HELD_ROW, fix_pr=1057, guard=GUARD)
        ledger = write_ledger(tmp, [row])
        before = ledger.read_text()
        proc = run_attr(scene(tmp, dict(BASE_CANNED)), ledger, "--attribute",
                        "--run", str(HELD_ROW["run_id"]), "--fix-pr", "1101", "--guard", GUARD,
                        "--evidence", EVIDENCE)
        check("replace attempt exits 2", proc.returncode == 2, f"rc={proc.returncode}")
        check("names the recorded fix", "already names fix PR #1057" in proc.stderr, proc.stderr[:400])
        check("the ledger is untouched", ledger.read_text() == before, "changed")
        check("the recorded fix survives", rows_of(ledger)[0].get("fix_pr") == 1057,
              str(rows_of(ledger)[0]))


def test_a_claim_missing_a_part_is_refused_before_anything_is_read() -> None:
    print("\nrefusal: a claim missing RUN/FIX_PR/GUARD/EVIDENCE is never applied")
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        ledger = write_ledger(tmp, [dict(HELD_ROW)])
        before = ledger.read_text()
        for label, parts in [
            ("no evidence", ["--run", "42976201014", "--fix-pr", "1101", "--guard", GUARD]),
            ("no guard", ["--run", "42976201014", "--fix-pr", "1101", "--evidence", EVIDENCE]),
            ("no run", ["--fix-pr", "1101", "--guard", GUARD, "--evidence", EVIDENCE]),
            ("no PR", ["--run", "42976201014", "--guard", GUARD, "--evidence", EVIDENCE]),
        ]:
            proc = run_attr(scene(tmp, dict(BASE_CANNED)), ledger, "--attribute", *parts)
            check(f"{label}: exit 2", proc.returncode == 2, f"rc={proc.returncode}")
            check(f"{label}: refuses with the missing part named",
                  "owes --run" in proc.stderr or "missing part" in proc.stderr, proc.stderr[:300])
        check("nothing written", ledger.read_text() == before, "changed")


def test_an_unknown_run_refuses_the_claim() -> None:
    print("\nrefusal: a claim on a run the ledger does not record is refused")
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        ledger = write_ledger(tmp, [dict(HELD_ROW)])
        env = scene(tmp, dict(BASE_CANNED))
        proc = run_attr(env, ledger, "--attribute", "--run", "999999", "--fix-pr", "1101",
                        "--guard", GUARD, "--evidence", EVIDENCE)
        check("exit 2", proc.returncode == 2, f"rc={proc.returncode}")
        check("names the missing row", "no ledger row for run 999999" in proc.stderr, proc.stderr[:300])
        check("no comment written", not comments_written(tmp), "")


def test_an_unreadable_ledger_is_exit_2_never_a_fake_clean() -> None:
    print("\nrefusal: a malformed ledger exits 2 on both attribution modes (rule 6r)")
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        env = scene(tmp, dict(BASE_CANNED))
        broken = tmp / "broken.json"
        broken.write_text('{"failures": [ {"run_id": 1,, }]', encoding="utf-8")
        for mode in ("--attribute-report", "--attribute"):
            proc = run_attr(env, broken, mode,
                            *(["--run", "1", "--fix-pr", "1", "--guard", GUARD,
                               "--evidence", EVIDENCE] if mode == "--attribute" else []))
            check(f"{mode}: exit 2", proc.returncode == 2, f"rc={proc.returncode}")
            check(f"{mode}: names the unreadable ledger", "unreadable" in proc.stderr,
                  proc.stderr[:300])


# ---------------------------------------------------------------------------
# the skeptic's closure: an attribution is made exactly once, by proof
# ---------------------------------------------------------------------------

def run_triage(tmp: Path, ledger: Path, triage: str) -> subprocess.CompletedProcess:
    path = tmp / "triage.md"
    path.write_text(triage, encoding="utf-8")
    return subprocess.run(
        [sys.executable, str(VERDICT), "--repo", REPO, "--issue", "826", "--file", str(path),
         "--ledger", str(ledger), "--now", NOW, "--dry-run"],
        capture_output=True, text=True, timeout=120)


CLOSE_TRIAGE = (
    "TRIAGE: close\n"
    "EVIDENCE: data/pipeline_failures.json run=42976201014 names a merged fix PR and its guard\n"
    "REASON: the sweep defect this issue reported landed in a merged fix PR; the row now names it\n"
)


def test_a_closed_row_with_a_landing_pr_still_needs_ledger_proof_to_close() -> None:
    print("\nskeptic closure: a CLOSE citing a ledger run needs a merged fix_pr + collected guard")
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        unattributed = write_ledger(tmp, [dict(HELD_ROW)])
        proc = run_triage(tmp, unattributed, CLOSE_TRIAGE)
        check("an unattributed row REFUSES the close", proc.returncode != 0,
              f"rc={proc.returncode} out={proc.stdout[:300]}")
        check("the refusal names the evidence rule", "REFUSED" in proc.stdout + proc.stderr,
              (proc.stdout + proc.stderr)[:400])

        att_dir = tmp / "att"
        att_dir.mkdir()
        attributed = write_ledger(att_dir, [dict(HELD_ROW, fix_pr=1101, guard=GUARD)])
        ok = run_triage(att_dir, attributed, CLOSE_TRIAGE)
        check("the attributed row closes green", ok.returncode == 0,
              f"rc={ok.returncode} err={ok.stderr[:400]}")
        check("the close cites the verdict-hold honesty", "close" in ok.stdout.lower(), ok.stdout[:300])


def test_the_registered_marker_has_its_writer_and_no_second_copy_of_the_literal() -> None:
    print("\nwiring (rule 6j): the attribution marker is registered, written, and never re-spelled")
    scripts = {p: p.read_text(encoding="utf-8") for p in sorted((ROOT / "scripts").glob("*.py"))}
    check("bot_markers registers pipeline-attribution",
          bm.marker_name("queued-alarm", "attribution") == "pipeline-attribution", "")
    writers = [p.name for p in sorted((ROOT / "scripts").glob("*.py"))
               if p.name != "bot_markers.py"
               and ("attribution_marker(" in p.read_text(encoding="utf-8")
                    or "attribution_marker_runs(" in p.read_text(encoding="utf-8"))]
    check("a writer in scripts/ uses the ONE shape",
          "pipeline_failure_issue.py" in writers, str(writers))
    # A SECOND copy of the marker STRING (rule 6j): only a construction of the shape counts —
    # prose that NAMES the marker (a comment explaining the registry) is not a second copy.
    # Built, never written literally: this file is scanned by tests/test_bot_markers.py too, so a
    # literal comment opener here would read as a stray marker in the tree (the #588 trap).
    opener = "<" + "!-- pipeline-attribution"
    copies = sorted(str(name) for name, text in scripts.items()
                    if name.name != "bot_markers.py" and opener in text)
    check("no script re-spells the marker literal", not copies, str(copies))
    round_trip = bm.attribution_marker_run(bm.attribution_marker(
        __import__("datetime").datetime(2026, 11, 19, tzinfo=__import__("datetime").timezone.utc),
        42976201014))
    check("the shape round-trips its parser", round_trip == "42976201014", str(round_trip))


def test_the_makefile_target_and_the_queued_alarm_step_are_wired() -> None:
    print("\nwiring (rules 6d/6m): the target exists, the pipeline calls it through make, in order")
    make = MAKEFILE.read_text(encoding="utf-8")
    wf = QUEUE_WF.read_text(encoding="utf-8")
    check("Makefile defines pipeline-failure-attribute",
          "\npipeline-failure-attribute:" in make, "")
    check("the target is .PHONY", ".PHONY: pipeline-failure-attribute" in make, "")
    check("the target reaches the script only through python3 scripts/… in its own recipe",
          "scripts/pipeline_failure_issue.py --repo" in make, "")
    check("queued-alarm calls it through make",
          "make pipeline-failure-attribute" in wf, "")
    check("queued-alarm never reaches the script past the Makefile (rule 6m)",
          "python3 scripts/pipeline_failure_issue.py" not in wf, "")
    check("the attribution step runs BEFORE the ledger-landing step",
          wf.index("make pipeline-failure-attribute") < wf.index("pipeline-failure-ledger"),
          "ordering")
    check("the sweep's filer step runs BEFORE the attribution report",
          wf.index("make pipeline-failure-issue") < wf.index("make pipeline-failure-attribute"),
          "ordering")
    check("the step is read-only apart from the annotation (default token)",
          _attribution_step(wf).lstrip().startswith("- name: Report unattributed diagnosed rows")
          and "GH_TOKEN: ${{ github.token }}" in _attribution_step(wf)
          and "gh_pat" not in _attribution_step(wf),
          _attribution_step(wf)[:200])
    check("the dispatch inputs declare the attestation",
          all(k in wf for k in ("attribute_run", "attribute_fix_pr", "attribute_guard",
                                "attribute_evidence")), "")
    check("queued-alarm carries no schedule (rule 6t)", "on:\n  schedule:" not in wf
          and "  schedule:\n" not in wf, "")


def test_the_rulebook_names_the_attribution_seam_and_the_measured_rows() -> None:
    print("\nwiring (rules 3c/6r): AGENTS.md names the seam, the three measured rows and this guard")
    agents = AGENTS.read_text(encoding="utf-8")
    check("rule 6r names make pipeline-failure-attribute",
          "make pipeline-failure-attribute" in agents, "")
    check("rule 6r names the measured verdict-held rows",
          "#826" in agents and "#827" in agents and "#828" in agents, "")
    check("§8 names this test as the guard row",
          "tests/test_pipeline_failure_attribution.py" in agents, "")
    check("§6j names the attribution marker on the queued-alarm row",
          "pipeline-attribution" in agents, "")


def main() -> int:
    test_an_open_verdict_held_row_raises_from_a_merged_guard_carrying_fix()
    test_the_attribution_is_idempotent_and_marker_deduplicated()
    test_the_stamp_pass_still_skips_an_open_row_and_the_report_names_it()
    test_report_mode_excludes_stamped_expired_and_undiagnosed_rows()
    test_a_closed_issue_with_no_closing_pr_reports_the_manual_close_shape()
    test_an_unmerged_fix_pr_refuses_the_attribution()
    test_a_guard_make_test_does_not_collect_refuses_the_attribution()
    test_a_named_guard_test_that_the_module_does_not_define_refuses()
    test_a_guard_the_fix_pr_diff_never_names_refuses_the_attribution()
    test_evidence_that_names_nothing_the_fix_touched_refuses()
    test_prose_only_evidence_refuses_the_attribution()
    test_evidence_citing_a_path_that_does_not_exist_refuses()
    test_evidence_citing_the_ledger_itself_is_refused_as_circular()
    test_an_undiagnosed_row_refuses_an_attribution_claim()
    test_the_terminal_log_expired_drain_refuses_an_attribution()
    test_a_row_that_already_names_a_different_fix_pr_refuses_replacing_it()
    test_a_claim_missing_a_part_is_refused_before_anything_is_read()
    test_an_unknown_run_refuses_the_claim()
    test_an_unreadable_ledger_is_exit_2_never_a_fake_clean()
    test_a_closed_row_with_a_landing_pr_still_needs_ledger_proof_to_close()
    test_the_registered_marker_has_its_writer_and_no_second_copy_of_the_literal()
    test_the_makefile_target_and_the_queued_alarm_step_are_wired()
    test_the_rulebook_names_the_attribution_seam_and_the_measured_rows()
    print(f"\nPASSED {_checks_passed} | FAILED {_checks_failed}")
    return 0 if _checks_failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
