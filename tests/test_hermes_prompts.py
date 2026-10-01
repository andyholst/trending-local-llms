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


def test_makefile_prompts_cap_reasoning():
    """Every hermes call in the Makefile must pass an explicit --reasoning level.
    Without it the search model can spend its whole max_tokens budget on
    reasoning on every continuation ('No visible answer was produced'), write
    no raw snapshot, and fail the search leg with exit 2 (seen on search-cpu)."""
    import re
    lines = (ROOT / "Makefile").read_text().splitlines()
    calls = [l for l in lines if re.match(r"\t\t-m nous-deepseek\b", l)]
    check("reasoning: found hermes model-flag lines", len(calls) >= 4, f"count={len(calls)}")
    missing = [l.strip() for l in calls if "--reasoning " not in l]
    check("reasoning: every hermes call sets --reasoning", not missing, str(missing))
    levels = dict(re.findall(r"^(HERMES_(?:FIX_)?REASONING)\s*:=\s*(\S+)", "\n".join(lines), re.M))
    valid = {"none", "minimal", "low", "medium", "high"}
    check("reasoning: search level defined + valid", levels.get("HERMES_REASONING") in valid, str(levels))
    check("reasoning: fix level defined + valid", levels.get("HERMES_FIX_REASONING") in valid, str(levels))


HERMES_TARGETS = ("_search-nvidia", "_search-metal", "_search-cpu", "_fix")


def _logical_commands(text: str) -> list[str]:
    """Join make -n output lines continued with a trailing backslash."""
    out, cur = [], ""
    for line in text.splitlines():
        if line.rstrip().endswith("\\"):
            cur += line.rstrip()[:-1] + " "
        else:
            out.append(cur + line)
            cur = ""
    if cur:
        out.append(cur)
    return [c.strip() for c in out if c.strip()]


def test_make_dry_run_single_hermes_command():
    """`make -n <target>` must yield ONE shell command that carries the prompt
    AND `-m nous-deepseek --reasoning`. If the -z line loses its trailing
    backslash, make runs `-m nous-deepseek --yolo` as its OWN command (the
    leading '-' even becomes make's ignore-errors prefix) and hermes starts
    with NO alias — it auto-routed to Hugging Face via HF_TOKEN and 403'd on
    every fix-bot run. This checks what make actually executes."""
    import shutil
    import subprocess
    if not shutil.which("make"):
        print("  SKIP make dry-run: make not installed")
        return
    for t in HERMES_TARGETS:
        p = subprocess.run(["make", "-s", "-n", t], cwd=ROOT, capture_output=True, text=True)
        cmds = _logical_commands(p.stdout)
        hermes = [c for c in cmds if c.startswith("hermes -z")]
        stray = [c for c in cmds if "nous-deepseek" in c and not c.startswith("hermes -z")]
        check(f"make -n {t}: exactly one hermes -z command", len(hermes) == 1, f"rc={p.returncode} {len(hermes)}")
        check(f"make -n {t}: that command carries -m nous-deepseek --reasoning",
              bool(hermes) and "-m nous-deepseek --reasoning " in hermes[0], hermes[0][-80:] if hermes else "")
        check(f"make -n {t}: no detached model-flag command", not stray, [c[:60] for c in stray])


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
        # valid body but NO trailing backslash: make runs `-m <alias> --yolo` as a
        # separate command, so hermes starts without the model alias (the _fix bug)
        'hermes -z "Fix the data so validation passes. Then regenerate README.md."',
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
    test_makefile_prompts_cap_reasoning()
    test_make_dry_run_single_hermes_command()
    test_prompt_permutations()
    print(f"\nPASSED {_PASS} | FAILED {_FAIL}")
    return 1 if _FAIL else 0


if __name__ == "__main__":
    raise SystemExit(main())
