#!/usr/bin/env python3
"""Unit tests for the hermes -z prompt shell-string validation.

Ensures no make-recipe hermes -z "..." prompt carries an unescaped quote (which
would close the -z string early, turn the rest of the prompt into stray args,
and make hermes error: '... is not a hermes command' — killing every search).

  - test_makefile_prompts_valid     dry-run against the REAL Makefile
  - test_prompt_permutations        data-driven matrix of broken/correct prompts

Run:  python3 tests/test_hermes_prompts.py   or   make test
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import validate as V  # noqa: E402

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


def test_makefile_prompts_valid():
    """Dry-run: every `hermes -z "..."` line in the real Makefile (4 search +
    fix-bot) must be a valid shell string (no unescaped quote in the body)."""
    bad = []
    count = 0
    for line in (ROOT / "Makefile").read_text().splitlines():
        if line.lstrip().startswith("hermes -z"):
            count += 1
            ok, why = V._hermes_prompt_ok(line)
            if not ok:
                bad.append(f"{why}: {line.strip()[:50]}")
    check("prompts: Makefile has hermes -z prompts to check", count >= 4, f"count={count}")
    check("prompts: all Makefile hermes -z prompts are valid shell strings", len(bad) == 0, str(bad))


def test_prompt_permutations():
    """DATA-DRIVEN: correct prompt bodies pass; every broken form (unescaped
    quote, malformed -z, missing quotes) is rejected."""
    good = [
        'hermes -z "Load AGENTS.md. Search. Write the payload. Never remove a model. Do not merge or push." \\',
        "hermes -z \"Fetch posts. Move context like 'DFlash spec-decode' into quant. Write data/raw/x.json.\" \\",
        "hermes -z \"JSON body {control:\\\"url\\\":\\\"v\\\"}. Rank by likes/comments/reshares. Write to data/raw/x.json.\" \\",
    ]
    bad = [
        # unescaped double-quote inside the -z body (the PR #38 bug)
        "hermes -z \"move context like \"DFlash spec-decode\" into quant. Write data/raw/x.json.\" \\",
        # unescaped quote mid-body
        "hermes -z \"Record engine \"+ model. Write.\" \\",
        # malformed: no closing quote / missing -z
        "hermes -z \"unclosed",
        "hermes fetch posts write data",
    ]
    for s in good:
        ok, _ = V._hermes_prompt_ok(s)
        check(f"prompt-perm: GOOD passes: {s[:38]!r}", ok, s)
    for s in bad:
        ok, why = V._hermes_prompt_ok(s)
        check(f"prompt-perm: BAD rejected: {s[:38]!r}", not ok, why)


def main() -> int:
    print("hermes -z prompt shell-string validation")
    test_makefile_prompts_valid()
    test_prompt_permutations()
    print(f"\nPASSED {_PASS} | FAILED {_FAIL}")
    return 1 if _FAIL else 0


if __name__ == "__main__":
    raise SystemExit(main())
