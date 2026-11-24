#!/usr/bin/env python3
"""The RED-first discipline is landed additively from a host forward note (issue #1497).

The host divergence was base + three added lines with zero deletions: a genuine
`RED-first` clause plus a duplicate `## This lane` heading. Only the new clause is
landed; the duplicate heading is not. This module reads the tracked skill and fails
when the clause, the renumbered step or the single heading is missing, and pins the
classify-before-copy rule so a future run cannot wipe forward work to force a gate.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKILL = ROOT / "agents" / "tll-implementer" / "skills" / "tll-implementer" / "SKILL.md"
NEEDLE = "RED-first: every acceptance criterion the change adds is locked by a test that FAILS on `git show origin/master:<product-file>` and PASSES on the fixed head."
OLD_STEP = "7. Post the result on the issue. The comment is the record."
NEW_STEP = "8. Post the result on the issue. The comment is the record."
HEADING = "## This lane"


def test_implementer_skill_states_red_first():
    text = SKILL.read_text()
    assert NEEDLE in text, "the RED-first clause must be present in the tracked implementer skill"
    assert NEW_STEP in text, "the following step must be renumbered to 8"
    assert OLD_STEP not in text, "the stale step-7 numbering must be gone"
    assert text.count(HEADING) == 1, "the duplicate host heading must NOT be landed"
    print("ok: tracked implementer skill carries one clean RED-first clause")


def _classify(base, host):
    """Diff shapes: a forward note adds lines; stale drift deletes owned bytes."""
    return ([line for line in host if line not in base],
            [line for line in base if line not in host])


def test_pure_addition_is_forward_work_not_staleness():
    # The measured host divergence was exactly: base + the RED-first clause +
    # a duplicate heading, with every base line still present (zero deletions).
    base = ["step 1", "step 2", OLD_STEP]
    host_forward = base + [NEEDLE, HEADING]
    added, deleted = _classify(base, host_forward)
    assert added == [NEEDLE, HEADING], added
    assert deleted == [], "a pure-addition divergence has zero deletions"

    # A host missing an owned base line is staleness and MUST be classified as such.
    host_stale = [line for line in base if line != OLD_STEP]
    added, deleted = _classify(base, host_stale)
    assert added == [], added
    assert deleted == [OLD_STEP], deleted
    print("ok: pure addition is forward work; a lost owned byte is staleness")


def main() -> int:
    for test in (test_implementer_skill_states_red_first, test_pure_addition_is_forward_work_not_staleness):
        test()
    return 0


if __name__ == "__main__":
    sys.exit(main())
