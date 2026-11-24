#!/usr/bin/env python3
"""The planner's DEAD-lane RESUME rule is a landed forward note (issue #1501).

The host divergence was base + nine added lines with zero deletions. Only the
genuinely-new clause is landed; this module fails when it is missing or when a
duplicate section heading is introduced.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKILL = ROOT / "agents" / "tll-planner" / "skills" / "tll-planner" / "SKILL.md"
NEEDLE = "A pushed branch with NO PR is a DEAD lane — dispatch a RESUME, never a second implementation."
CHECKS = ("ps` for a live `hermes -p tll-* chat", "gh pr list --state all --head <branch>", "make dispatch-check ISSUE=<n>")
HEADING = "## This lane"


def test_planner_skill_states_dead_lane_resume():
    text = SKILL.read_text()
    assert NEEDLE in text, "the DEAD-lane RESUME clause must be in the tracked planner skill"
    for check in CHECKS:
        assert check in text, f"the RESUME three-check rule must name {check}"
    assert text.count(HEADING) == 1, "no duplicate section heading may be landed"
    print("ok: planner skill carries the DEAD-lane RESUME rule with all three checks")


def main() -> int:
    test_planner_skill_states_dead_lane_resume()
    return 0


if __name__ == "__main__":
    sys.exit(main())
