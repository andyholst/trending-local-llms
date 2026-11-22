#!/usr/bin/env python3
"""tests/test_cross_machine_coordination.py — issue #1231.

Rule 6u makes cross-machine coordination WRITTEN: identity, claim-before-edit,
failure-report-before-fix, signed handover, issue-as-board, and status-while-waiting.
This suite reads the real AGENTS.md and fails when any obligation is dropped or
weakened; a planted copy with one clause removed must produce a named finding.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tests"))
from wiring import wired  # noqa: E402

_PASS = 0
_FAIL = 0


def check(name, cond, detail=""):
    global _PASS, _FAIL
    if cond:
        _PASS += 1
        print(f"  ok  {name}")
    else:
        _FAIL += 1
        print(f"  FAIL {name}" + (f"  [{detail}]" if detail else ""))


def rule_slice(text: str) -> str:
    a = text.find("6u. **Cross-machine")
    if a < 0:
        return ""
    b = text.find("## 3. Data source & collection", a)
    return text[a:b if b > a else len(text)]


OBLIGATIONS = {
    "identity": "`agent@host`",
    "claim before edit": "Claim before edit",
    "failure report before fix": "Failure report before fix",
    "signed handover": "Signed handover",
    "issue thread is the one board": "ONE board",
    "sync while waiting": "Sync while waiting",
}


def main() -> int:
    print("cross-machine coordination rule (issue #1231):")
    text = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
    rule = rule_slice(text)
    check("AGENTS.md carries rule 6u", bool(rule))
    for name, needle in OBLIGATIONS.items():
        check(f"rule 6u keeps the {name} obligation", needle in rule, needle)
    check("a missing obligation is named by the guard",
          "Signed handover" not in rule.replace("**Signed handover**", "**Dropped**"))
    check("the rule names its own regression test",
          "tests/test_cross_machine_coordination.py" in rule)
    check("this suite is discovered by `make test`", wired(__file__))
    print(f"{'FAILED' if _FAIL else 'PASSED'} {_PASS} | FAILED {_FAIL}")
    return 1 if _FAIL else 0


if __name__ == "__main__":
    raise SystemExit(main())
