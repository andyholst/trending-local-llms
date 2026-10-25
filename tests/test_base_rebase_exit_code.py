#!/usr/bin/env python3
"""`make base-rebase` must not lose a documented exit code (issue #586).

`scripts/worktree_base.py rebase` exits **3** when the rebase conflicts, because a conflicted
rebase KEEPS every commit and the push must still happen (AGENTS.md #475/#500). The issue-bot
commit step compared `make`'s status to 3 — but **make returns 2 for ANY failing recipe** and
prints the child's code only in its own message (`make: *** [Makefile:403: base-rebase] Error
3`). The exit-3 branch was therefore dead code, and every conflicted rebase was read as a hard
failure: measured on run 40205472559, where the run implemented for ~20 minutes, committed
(`6 files changed, 213 insertions(+)`) and then refused to push.

The fix lives in the TARGET: it normalises 3 into success (`base_rebase=conflict`) so the caller
does not have to interpret a code an intermediary rewrites. These tests run the recipe's REAL
text out of the Makefile against a stub `scripts/worktree_base.py`, so what is proved is what
the bot runs.

Run:  python3 tests/test_base_rebase_exit_code.py    or   make test
"""
from __future__ import annotations

import re
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MAKEFILE = ROOT / "Makefile"

_PASS = 0
_FAIL = 0


def check(name, cond, detail=None):
    global _PASS, _FAIL
    if cond:
        _PASS += 1
        print(f"  ok  {name}")
    else:
        _FAIL += 1
        shown = "" if detail is None or detail == "" else f"  [{detail}]"
        print(f"  FAIL {name}{shown}")


def recipe_text(target: str) -> str:
    """The recipe bodies of `target` in the Makefile, tabs stripped, as one shell script."""
    lines = MAKEFILE.read_text().splitlines()
    out: list[str] = []
    inside = False
    for line in lines:
        if re.match(rf"^{re.escape(target)}\s*:", line):
            inside = True
            continue
        if inside:
            if line.startswith("\t"):
                body = line[1:]
                if body.startswith("@"):     # make's silencer, not shell
                    body = body[1:]
                out.append(body)
            elif line.strip() == "" or line.startswith("#"):
                continue
            else:
                break
    if not out:
        raise AssertionError(f"no recipe for {target} in {MAKEFILE}")
    return "\n".join(out)


def run_recipe(stub_rc: int) -> subprocess.CompletedProcess:
    """Run the REAL `base-rebase` recipe with a stub script that exits `stub_rc`."""
    with tempfile.TemporaryDirectory() as td:
        d = Path(td)
        (d / "scripts").mkdir()
        (d / "scripts" / "worktree_base.py").write_text(
            "import sys\n"
            f"print('rebase=conflict' if {stub_rc} == 3 else 'mode=rebase')\n"
            f"raise SystemExit({stub_rc})\n")
        script = recipe_text("base-rebase")
        # `$(BRANCH)` / `$(if $(BASE),$(BASE),master)` are make functions: spell the values the
        # caller passes, which is what make would substitute.
        script = script.replace('"$(BRANCH)"', '"ci/x"').replace(
            '"$(if $(BASE),$(BASE),master)"', '"master"')
        script = script.replace("$(BRANCH)", "ci/x").replace("$$", "$")
        return subprocess.run(["bash", "-e", "-c", script], cwd=td,
                              capture_output=True, text=True)


def test_a_conflicted_rebase_succeeds():
    """Exit 3 means "the work is kept and the push goes ahead" — never a failure."""
    p = run_recipe(3)
    check("base-rebase: a conflicted rebase exits 0 (the push must go ahead)",
          p.returncode == 0, (p.returncode, p.stdout, p.stderr))
    check("base-rebase: it says so on stdout, so a caller can report it",
          "base_rebase=conflict" in p.stdout, p.stdout)
    check("base-rebase: the script's own output is not swallowed",
          "rebase=conflict" in p.stdout, p.stdout)


def test_a_real_failure_still_fails():
    """A branch that does not exist, an unreachable base: still a failure."""
    for rc in (1, 2, 4):
        p = run_recipe(rc)
        check(f"base-rebase: a genuine failure (exit {rc}) still exits non-zero",
              p.returncode != 0, (rc, p.returncode, p.stdout))
        check(f"base-rebase: exit {rc} is NOT reported as a conflict",
              "base_rebase=conflict" not in p.stdout, p.stdout)


def test_a_clean_rebase_is_silent_about_conflicts():
    p = run_recipe(0)
    check("base-rebase: a clean rebase exits 0", p.returncode == 0, p.returncode)
    check("base-rebase: it does not claim a conflict",
          "base_rebase=conflict" not in p.stdout, p.stdout)


def test_the_workflow_does_not_compare_makes_exit_code():
    """The dead contract: `make` returns 2 for any failing recipe, so `= 3` never matched."""
    wf = (ROOT / ".github/workflows/issue-bot.yml").read_text()
    check("workflow: the step calls the target",
          "make base-rebase BRANCH=\"$BRANCH\"" in wf, "")
    check("workflow: no `REBASE_RC` comparison survives (it read make's 2, never 3)",
          "REBASE_RC" not in wf, [l for l in wf.splitlines() if "REBASE_RC" in l][:3])
    check("workflow: the target is no longer wrapped in `|| …=$?`",
          "make base-rebase BRANCH=\"$BRANCH\" ||" not in wf, "")


def main() -> int:
    print("base-rebase exit code: unit tests")
    test_a_conflicted_rebase_succeeds()
    test_a_real_failure_still_fails()
    test_a_clean_rebase_is_silent_about_conflicts()
    test_the_workflow_does_not_compare_makes_exit_code()
    print(f"PASSED {_PASS} | FAILED {_FAIL}")
    return 0 if _FAIL == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
