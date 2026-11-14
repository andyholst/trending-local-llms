#!/usr/bin/env python3
"""Guard for issue #863: the generated README's bot-cadence prose must match
the pinned crons (weekly on Wednesday, tests/test_workflows.py). The REAL
scripts/validate.py::check_readme_bot_cadence runs against fixture README +
workflow trees (module globals repointed to temp files, like every validate
suite), and the fixture checks MUST go red — plus the real repo README and the
render template must be clean.

Run:  python3 tests/test_readme_bot_cadence.py   or   make test
"""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import validate as V  # noqa: E402

_PASS = 0
_FAIL = 0


def check(name, cond, detail: object = ""):
    global _PASS, _FAIL
    if cond:
        _PASS += 1
        print(f"  ok   {name}")
    else:
        _FAIL += 1
        print(f"  FAIL {name} {detail}")


def sandbox(readme_text: str, workflow_crons: dict[str, list[str]]):
    """A fixture repo root: README.md + .github/workflows/<name>.yml with the
    given crons; returns the temp root."""
    root = Path(tempfile.mkdtemp(prefix="cadence863"))
    (root / "README.md").write_text(readme_text, encoding="utf-8")
    wf = root / ".github" / "workflows"
    wf.mkdir(parents=True)
    for name, crons in workflow_crons.items():
        body = "on:\n  schedule:\n" + "".join(f'    - cron: "{c}"\n' for c in crons)
        (wf / name).write_text(body, encoding="utf-8")
    return root


def run_check(root: Path) -> list[str]:
    old_readme, old_root = V.README, V.ROOT
    V.README, V.ROOT = root / "README.md", root
    V.FAILURES.clear()
    try:
        V.check_readme_bot_cadence({})
        return list(V.FAILURES)
    finally:
        V.README, V.ROOT = old_readme, old_root
        V.FAILURES.clear()


REAL_CRONS = {
    "issue-bot.yml": ["19 * * * 3", "49 * * * 3"],
    "issue-review-bot.yml": ["41 * * * 3"],
    "queued-alarm.yml": ["37 * * * 3"],
    "code-review-bot.yml": ["7 6 * * 3"],
}


def test_hourly_claim_is_refused():
    root = sandbox(
        "`issue-bot` implements ONE open issue per hour and `issue-review-bot.yml` runs hourly at `41`.\n",
        REAL_CRONS,
    )
    fails = run_check(root)
    check("hourly claim refused", any("hourly cadence" in f and "issue-review-bot.yml" in f for f in fails), fails)


def test_per_hour_claim_is_refused():
    root = sandbox(
        "`queued-alarm.yml` (twice an hour at `:07`/`:37`, dispatch too) runs `make queued-alarm`.\n",
        REAL_CRONS,
    )
    fails = run_check(root)
    check("per-hour claim refused", any("hourly cadence" in f and "queued-alarm.yml" in f for f in fails), fails)


def test_wrong_weekday_is_refused():
    root = sandbox(
        "`code-review-bot.yml` (weekly Monday `7 6 * * 3`, dispatch too) runs `make code-review-scan`.\n",
        REAL_CRONS,
    )
    fails = run_check(root)
    check("wrong weekday refused", any("Monday" in f for f in fails), fails)


def test_quoted_cron_must_match_the_workflow():
    root = sandbox(
        "`issue-review-bot.yml` sweeps weekly on Wednesday at `41 * * * 4`.\n",
        REAL_CRONS,
    )
    fails = run_check(root)
    check("quoted cron cross-check refused", any("quotes cron" in f for f in fails), fails)


def test_a_true_weekly_line_passes():
    root = sandbox(
        "`issue-review-bot.yml` runs **weekly on Wednesday** at `41` and `issue-bot.yml` sweeps `19 * * * 3` with the `49 * * * 3` backup.\n",
        REAL_CRONS,
    )
    fails = run_check(root)
    check("true weekly line passes", fails == [], fails)


def test_cadence_refusal_is_not_vacuous():
    # a named pipeline with no workflow file: cadence words still refused,
    # quoted crons cannot be cross-checked (nothing asserts vacuously)
    root = sandbox(
        "`bot-health.yml` runs every hour.\n",
        REAL_CRONS,
    )
    fails = run_check(root)
    check("cadence refusal is not vacuous", any("hourly cadence" in f for f in fails), fails)


def test_real_repo_readme_is_clean():
    fails = run_check(ROOT)
    check("real README matches the pinned crons", fails == [], fails)


def test_render_template_no_longer_claims_hourly_queue():
    text = (ROOT / "scripts" / "update_trending.py").read_text(encoding="utf-8")
    check("template: no 'per hour' bot claim", "issue per hour" not in text)
    check("template: no 'twice an hour' alarm claim", "twice an hour" not in text)
    check("template: no 'weekly Monday' review claim", "weekly Monday `07:23`" not in text)


def main() -> int:
    test_a_true_weekly_line_passes()
    test_cadence_refusal_is_not_vacuous()
    test_hourly_claim_is_refused()
    test_per_hour_claim_is_refused()
    test_quoted_cron_must_match_the_workflow()
    test_real_repo_readme_is_clean()
    test_render_template_no_longer_claims_hourly_queue()
    test_wrong_weekday_is_refused()
    print(f"\ntest_readme_bot_cadence: {_PASS} passed, {_FAIL} failed")
    return 1 if _FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
