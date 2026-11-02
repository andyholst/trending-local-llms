#!/usr/bin/env python3
"""The host fleet copy under agents/ adds no schedule (issues #682-#687)."""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PROFILES = (
    "tll-planner",
    "tll-architect",
    "tll-security",
    "tll-reviewer",
    "tll-implementer",
)
CRON = re.compile(r"(?m)^\s*-\s*cron:\s*|\b\d+\s+\d+\s+\*\s+\*\s+\S+")
LEAVE = "Existing GitHub Actions schedules stay as they are."


def main() -> int:
    failed = 0
    for profile in PROFILES:
        files = [
            ROOT / "agents" / profile / "SOUL.md",
            ROOT / "agents" / profile / "skills" / profile / "SKILL.md",
        ]
        for path in files:
            rel = path.relative_to(ROOT)
            if not path.is_file():
                print(f"FAIL {rel} missing")
                failed += 1
                continue
            text = path.read_text(encoding="utf-8")
            if LEAVE not in text and "Do not add a schedule" not in text and "do not edit a GitHub Actions" not in text and "No Hermes cron" not in text and "There is no Hermes cron" not in text:
                print(f"FAIL {rel} does not forbid a new schedule")
                failed += 1
            else:
                print(f"ok   {rel} forbids a new schedule")
            hit = CRON.search(text)
            if hit:
                print(f"FAIL {rel} contains a cron expression: {hit.group(0)!r}")
                failed += 1
            else:
                print(f"ok   {rel} has no cron expression")
        soul = (ROOT / "agents" / profile / "SOUL.md").read_text(encoding="utf-8")
        if LEAVE not in soul:
            print(f"FAIL agents/{profile}/SOUL.md dropped the leave-schedules-alone line")
            failed += 1
        else:
            print(f"ok   agents/{profile}/SOUL.md leaves existing schedules alone")
    if failed:
        print(f"FAIL {failed}")
        return 1
    print("ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
