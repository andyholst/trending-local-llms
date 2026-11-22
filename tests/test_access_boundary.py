#!/usr/bin/env python3
"""tests/test_access_boundary.py — issue #1238.

Rule 6v makes the access boundary WRITTEN: agents never hand out collaborator /
repository access; only the human owner does. This suite reads the REAL AGENTS.md
and fails if the rule loses its agent prohibition, the owner-only decision, or the
issue-thread escalation path. A planted omission must produce a named finding.
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
    # The rule is a column-0 hard rule (`6v. **Collaborator ...**`); accept the
    # unbolded spelling too so the anchor never silently misses the rule.
    a = text.find("6v. **Collaborator")
    if a < 0:
        a = text.find("6v. Collaborator")
    if a < 0:
        return ""
    b = text.find("## 3. Data source & collection", a)
    return text[a:b if b > a else len(text)]


CLAUSES = {
    "agent prohibition": "NEVER hands out collaborator access",
    "all access forms": "permission",
    "owner-only decision": "the human owner alone does that",
    "escalation path": "posts the need on the shared issue thread",
    "no workaround": "never\n   grants, requests on anyone's behalf, or works around the boundary",
    "regression test named": "tests/test_access_boundary.py",
}


def missing(rule: str) -> list[str]:
    return [name for name, needle in CLAUSES.items() if needle not in rule]


def main() -> int:
    print("access boundary rule (issue #1238):")
    text = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
    rule = rule_slice(text)
    check("AGENTS.md carries rule 6v", bool(rule))
    for name in CLAUSES:
        check(f"rule 6v keeps the {name} clause", name not in missing(rule), name)
    planted = rule.replace("the human owner alone does that", "the agent may decide")
    check("a planted owner-only omission is named by the guard",
          "owner-only decision" in missing(planted), str(missing(planted)))
    check("this suite is discovered by `make test`", wired(__file__))
    print(f"{'FAILED' if _FAIL else 'PASSED'} {_PASS} | FAILED {_FAIL}")
    return 1 if _FAIL else 0


if __name__ == "__main__":
    raise SystemExit(main())
