#!/usr/bin/env python3
"""The hard rules in AGENTS.md §2 are numbered, and the numbering is hand-maintained — so
nothing could notice a collision until issue #270 (issue #270).

`#262` renumbered its rule from `6l` to `6m` **because `6l` was already taken** (the
queued-alarm rule, #256). One merge later, `#265` picked `6m` for a different rule, and master
carried TWO `6m.` rules for weeks:

    250:6m. **ONE path: business logic goes through the Makefile, ...
    394:6m. **The searches must ask for the models we rank ...

The cost is not cosmetic: two tests cited "rule 6m" and meant **different rules**
(`tests/test_makefile_only.py` meant the ONE-path rule; `tests/test_query_coverage.py` pinned
the searches rule by its exact heading), so a reader following a citation lands on whichever
rule they scroll to first.

This guard makes the collision impossible to merge, and it checks the thing that actually
bites — that a citation RESOLVES:

  1. no two rules in §2 share an id, and the rule set is not empty (a vacuous guard is a
     defect);
  2. every `rule <id>` citation anywhere in the tree names an id that exists in §2.

It deliberately does NOT assert that the ids are contiguous or in order: the file is ordered by
TOPIC, not by number (on master `6m` sits before `6h`), and a missing `6a` makes no citation
ambiguous. Uniqueness and resolvability are the invariants.

Run: python3 tests/test_rule_numbers.py   (wired into `make _test`)
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
AGENTS = ROOT / "AGENTS.md"

#: A hard-rule heading: `6m.` / `3b.` / `1.` at column 0 inside the §2 block.
_RULE = re.compile(r"^([0-9]+[a-z]?)\.", re.M)

#: A citation: `rule 6m`, `rule 3e`, `rule 6f/6g` (each captured separately).
_CITE = re.compile(r"\brule ([0-9]+[a-z]?)\b")

#: Directories whose files are never citations of the rulebook.
_SKIP_DIRS = {".git", "node_modules", "__pycache__", ".venv", "data", "openspec"}

#: Text files that can carry a citation.
_TEXT_SUFFIXES = {".py", ".yml", ".yaml", ".md", ".sh", ".json", ".toml", ".cfg"}
_TEXT_NAMES = {"Makefile", "Dockerfile", "Dockerfile.test"}


def rules_block() -> str:
    """AGENTS.md §2 (Hard rules) — the rule numbers live only here, so the §5/§5b numbered
    LISTS (which also start `1. `) can never be mistaken for rules."""
    text = AGENTS.read_text(encoding="utf-8")
    m = re.search(r"^## 2\..*?(?=^## )", text, re.S | re.M)
    return m.group(0) if m else ""


def rule_ids() -> list[str]:
    """Every rule id in §2, in order of appearance."""
    return _RULE.findall(rules_block())


def text_files() -> list[Path]:
    """Every text file that could cite a rule (no `git ls-files`: this runs inside the test
    image with the repo mounted, where a worktree's `.git` is a file outside the mount)."""
    out: list[Path] = []
    for path in sorted(ROOT.rglob("*")):
        if not path.is_file():
            continue
        if any(part in _SKIP_DIRS for part in path.parts):
            continue
        if path.suffix in _TEXT_SUFFIXES or path.name in _TEXT_NAMES:
            out.append(path)
    return out


def test_every_rule_number_is_unique():
    """No two hard rules share an id (the #270 defect: two `6m.` rules)."""

    # Given the hard rules in AGENTS.md §2
    ids = rule_ids()

    # Then  the rulebook is not empty — a guard over nothing passes trivially
    assert ids, "AGENTS.md §2 carries no numbered hard rules — the guard is vacuous"

    # And no id is used twice
    seen: dict[str, int] = {}
    dupes: list[str] = []
    for rid in ids:
        seen[rid] = seen.get(rid, 0) + 1
        if seen[rid] == 2:  # report each colliding id once, with its real count
            dupes.append(f"rule {rid}: declared {ids.count(rid)} times")
    assert not dupes, "two hard rules share a number:\n  " + "\n  ".join(dupes)

    # And a rule id is never a strict prefix collision of another (6 and 6b are distinct)
    assert len(set(ids)) == len(ids)


def test_every_citation_resolves_to_a_rule():
    """Every `rule <id>` in the tree names a rule that exists in §2."""

    # Given the rule ids that exist
    known = set(rule_ids())
    assert known, "no rules found — the citation check would pass trivially"

    # When  every citation in the tree is collected
    unresolved: list[str] = []
    cited: set[str] = set()
    for path in text_files():
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for rid in _CITE.findall(text):
            cited.add(rid)
            if rid not in known:
                rel = path.relative_to(ROOT)
                unresolved.append(f"{rel}: cites rule {rid}, which §2 does not declare")

    # Then  every one resolves — a dangling citation is a reader sent to a rule that is not there
    assert not unresolved, "citations that do not resolve:\n  " + "\n  ".join(sorted(set(unresolved)))

    # And the scan is not vacuous: the tree really does cite rules
    assert cited, "no `rule <id>` citation found anywhere — the scan proves nothing"


def main() -> int:
    """Run every test in this file — a test defined but never called passes CI silently."""
    failures = 0
    for test in (test_every_rule_number_is_unique, test_every_citation_resolves_to_a_rule):
        try:
            test()
            print(f"  ok  {test.__name__}")
        except AssertionError as exc:
            failures += 1
            print(f"FAIL {test.__name__}  [{exc}]")
    print(f"\nPASSED {2 - failures} | FAILED {failures}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
