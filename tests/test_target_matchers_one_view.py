#!/usr/bin/env python3
"""One target-line matcher: every consumer reads the shared scan (issue #752).

`architecture_bot` owns THE Makefile target-line parser (#512 unified the two
counting parsers that had drifted 126 vs 178). But line-level copies of the
same matcher survived #513's own finding — and this suite measured a third the
finding never named:

  - `architecture_check._ANY_TARGET`      — byte-identical copy, hand-synced forever
  - `test_architecture_bot._makefile_targets` — looser copy: counts 145 `.PHONY:`
    lines in the real Makefile as targets the shared scan skips
  - `test_workflows._makefile_commands`   — the same looser copy attributing
    recipe commands

Every copy is a drift waiting to happen. This suite refuses a target-line
matcher literal outside `scripts/architecture_bot.py`, pins that
`architecture_check` carries no private matcher, and pins the test helpers to
the generator's parser. RED on the old tree (three copies, no `target_at_line`).

Wired into `make test` (rule 6d).
"""
from __future__ import annotations

import importlib.util
import subprocess
import sys
import tempfile
from pathlib import Path

from wiring import wired  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent

_PASS = 0
_FAIL = 0


def check(name, cond, detail=""):
    global _PASS, _FAIL
    if cond:
        _PASS += 1
        print(f"  ok  {name}")
    else:
        _FAIL += 1
        print(f"  FAIL {name}" + (f" — {detail}" if detail else ""))


def _load(script: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, script)
    assert spec and spec.loader, script
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# The signature of a target-line matcher regex, built so THIS file never
# contains the literal it scans for.
_SIGNATURE = ":" + "(?!=" + ")"


def _tracked_py() -> list[Path]:
    out = subprocess.run(["git", "ls-files", "scripts/*.py", "tests/*.py"],
                         cwd=str(ROOT), capture_output=True, text=True)
    return [ROOT / line for line in out.stdout.split("\n") if line.strip()]


def test_no_target_line_matcher_lives_outside_architecture_bot():
    """Every `name:(?!=…)` matcher in the tree is the shared parser's."""
    shared = ROOT / "scripts" / "architecture_bot.py"
    offenders = []
    for path in _tracked_py():
        if path == shared or not path.is_file():
            continue
        text = path.read_text(encoding="utf-8")
        if _SIGNATURE in text:
            offenders.append(str(path.relative_to(ROOT)))
    check("no target-line matcher lives outside scripts/architecture_bot.py",
          not offenders, f"copies: {offenders}")

    # The bot module itself still carries the one parser.
    bot = _load(shared, "architecture_bot")
    check("the shared parser is present and named",
          hasattr(bot, "_TARGET_LINE") and hasattr(bot, "make_targets"))
    check("the shared line-level view exists for consumers",
          hasattr(bot, "target_at_line"),
          "architecture_bot.target_at_line missing — consumers keep private copies")


def test_stage_lists_attributes_through_the_shared_view():
    """architecture_check tracks the current target with the shared view, not a copy."""
    check_mod = _load(ROOT / "scripts" / "architecture_check.py", "architecture_check")
    check("architecture_check carries no private target matcher",
          not hasattr(check_mod, "_ANY_TARGET"),
          "_ANY_TARGET is a byte-identical copy of architecture_bot._TARGET_LINE (#752)")

    with tempfile.TemporaryDirectory() as td:
        mk = Path(td) / "Makefile"
        mk.write_text(
            ".PHONY: _validate-x\n"
            "_validate-x: ## run the validator stages\n"
            "\tpython3 scripts/validate.py --only links,tables --data data/models.json\n",
            encoding="utf-8",
        )
        pairs = check_mod.stage_lists(mk)
        check("the --only list is attributed to its target",
              pairs == [("_validate-x", ["links", "tables"])],
              f"got {pairs}")


def test_the_test_helper_is_the_shared_parser_not_a_copy():
    """test_architecture_bot._makefile_targets answers with make_targets, `.PHONY` in neither."""
    bot = _load(ROOT / "scripts" / "architecture_bot.py", "architecture_bot")
    helper_mod = _load(ROOT / "tests" / "test_architecture_bot.py", "test_architecture_bot")
    helper = helper_mod._makefile_targets()
    shared = bot.make_targets(ROOT)
    diff = helper ^ shared
    check("_makefile_targets equals the generator's make_targets on the real Makefile",
          helper == shared,
          f"drift {sorted(diff)} — the copy counts {len([n for n in diff if n.startswith('.')])} pseudo-targets the scan skips")


def test_recipe_attribution_uses_the_shared_view():
    """test_workflows._makefile_commands attributes recipes through target_at_line."""
    wf = _load(ROOT / "tests" / "test_workflows.py", "test_workflows")
    src = (ROOT / "tests" / "test_workflows.py").read_text(encoding="utf-8")
    check("test_workflows has no private target matcher", _SIGNATURE not in src,
          "_makefile_commands carries its own name:(?!…=) regex — a third view of the one parser")

    # The attribution on the REAL Makefile must equal the shared view's.
    bot = _load(ROOT / "scripts" / "architecture_bot.py", "architecture_bot")
    shared_cmds: dict[str, list[str]] = {}
    target = None
    for line in (ROOT / "Makefile").read_text().splitlines():
        if line.startswith("\t"):
            body = line.strip()
            if target and body and not body.startswith("#"):
                shared_cmds.setdefault(target, []).append(body)
            continue
        target = bot.target_at_line(line)
    helper_cmds = wf._makefile_commands()
    check("_makefile_commands attributes exactly what the shared view attributes",
          helper_cmds == shared_cmds,
          f"drift keys {sorted(set(helper_cmds) ^ set(shared_cmds))}")

    # And the shared view never names a pseudo-target as a recipe owner.
    with tempfile.TemporaryDirectory() as td:
        mk = Path(td) / "Makefile"
        mk.write_text(
            ".helper: ## a dot-prefixed pseudo-target\n"
            "\techo attributed-to-pseudo\n"
            "real: ## a real target\n"
            "\tmake lint\n",
            encoding="utf-8",
        )
        attributed: dict[str, list[str]] = {}
        target = None
        for line in mk.read_text().splitlines():
            if line.startswith("\t"):
                if target:
                    attributed.setdefault(target, []).append(line.strip())
                continue
            target = bot.target_at_line(line)
        check("the shared view never names a pseudo-target as a recipe owner",
              ".helper" not in attributed, f"attributed keys {sorted(attributed)}")
        check("the shared view attributes a real target's recipe",
              attributed.get("real") == ["make lint"], f"got {attributed}")


def main() -> int:
    print("One target-line matcher, every consumer the shared view (scripts/architecture_bot.py)")
    test_no_target_line_matcher_lives_outside_architecture_bot()
    test_stage_lists_attributes_through_the_shared_view()
    test_the_test_helper_is_the_shared_parser_not_a_copy()
    test_recipe_attribution_uses_the_shared_view()
    check("wiring: this module is discovered by the ONE test runner", wired(__file__))
    print(f"\nPASSED {_PASS} | FAILED {_FAIL}")
    return 1 if _FAIL else 0


if __name__ == "__main__":
    raise SystemExit(main())
