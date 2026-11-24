#!/usr/bin/env python3
"""The rebase lane's SOUL.md teaches push-and-verify, not a pre-push local gate (#1442).

Issue #1427 landed the SKILL.md half of owner directive #1423 but left
`agents/tll-pr-rebase/SOUL.md` untouched, so the file the lane reads FIRST still told it to run the
whole containerised gate locally before pushing. This module pins that one bullet, so a later edit
cannot regress it silently.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SOUL = ROOT / "agents" / "tll-pr-rebase" / "SOUL.md"


def _bullet() -> str:
    """The push-and-verify bullet of tll-pr-rebase/SOUL.md ('' when absent)."""
    if not SOUL.is_file():
        return ""
    return next(
        (ln for ln in SOUL.read_text(encoding="utf-8").splitlines() if "Change/rebase locally" in ln),
        "",
    )


def test_pr_rebase_soul_is_push_and_verify() -> None:
    bullet = _bullet()
    assert bullet, "tll-pr-rebase/SOUL.md dropped its push-and-verify bullet"
    for needle, why in (
        ("run only the FAST offline checks", "the fast-check-only instruction"),
        ("make lint", "the fast lint check"),
        ("PUSH", "the push"),
        ("gh pr checks <n>", "the per-PR CI confirmation"),
        ("gh run view <id> --json jobs", "the run-jobs CI confirmation"),
        ("CI red at your head means the rebase is not done", "the red-head rule as a CI verdict"),
    ):
        assert needle in bullet, f"tll-pr-rebase/SOUL.md push-and-verify bullet lacks {why}: {needle!r}"
    for needle, why in (
        ("make validate", "the full validate"),
        ("make test", "the whole test suite"),
        ("closure", "closure"),
        ("guard", "guard"),
    ):
        assert needle in bullet, f"tll-pr-rebase/SOUL.md push-and-verify bullet lacks {why} CI-ONLY: {needle!r}"
    assert "CI-ONLY" in bullet, "tll-pr-rebase/SOUL.md push-and-verify bullet does not name the heavy gates CI-ONLY"
    assert "Gate before push" not in SOUL.read_text(encoding="utf-8"), (
        "tll-pr-rebase/SOUL.md reintroduced the pre-push local-gate heading"
    )


def main() -> int:
    failed = 0
    for fn in (test_pr_rebase_soul_is_push_and_verify,):
        try:
            fn()
        except AssertionError as exc:
            print(f"FAIL {fn.__name__}: {exc}")
            failed += 1
        else:
            print(f"ok   {fn.__name__}")
    if failed:
        print(f"FAIL {failed}")
        return 1
    print("ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
