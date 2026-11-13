#!/usr/bin/env python3
"""Tests for scripts/task_boxes.py — the ONE task-box vocabulary (issue #636).

`check_openspec_tasks` (the completion gate) and `openspec_index` (the index
generator) read the same `tasks.md` boxes. Before issue #636 each spelled the
box regex itself, so a fourth state added to one was silently a non-task in the
other — exactly how `- [~]` once read as "all tasks checked". These tests lock
the fix:

  * the vocabulary has exactly ONE home in scripts/, and both readers import it;
  * the compiled pattern is COMPOSED from BOX_STATES, not spelled beside it;
  * both REAL readers classify every state in the vocabulary the same way;
  * adding a state in the ONE place is seen by BOTH readers — proven by running
    copies of the real modules in a fresh subprocess, and proven to BITE by a
    planted reader copy that keeps a private regex (the pre-#636 code), which
    must NOT see the new state.

Wired into `make test` (rule 6d).
"""
from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import tempfile
import textwrap
from pathlib import Path

from wiring import wired  # noqa: E402  (issues #176/#192)

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "scripts"

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


def _load(name: str, path: Path):
    """The REAL script, imported by path (no copy of its logic in the test)."""
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader, path
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# The fixture: every state in the vocabulary, plus the things that are NOT boxes.
FIXTURE = """# Tasks — vocabulary fixture

- [ ] open box
- [x] checked box
- [X] capital checked box
- [~] blocked box — blocked: reviewer sign-off
- a plain bullet is not a task
* [x] star bullet checked
+ [ ] plus bullet open
  - [x] indented checked
mid-line [x] is not a task
- [z] a character outside the vocabulary is not a task
"""

# The gate skips fenced boxes; the index (pre-existing, documented asymmetry)
# counts them. Locked here so the readers' SHARED contract is the state, not
# the fence policy.
FENCED_FIXTURE = """# Tasks

- [x] real box

```
- [ ] fenced sample is not a task to the gate
```
"""


def test_the_box_vocabulary_has_exactly_one_home():
    """No script under scripts/ re-spells the box regex; both readers import it."""

    # Given every script in the repository
    spellers = sorted(
        p.name
        for p in SCRIPTS.glob("*.py")
        if r"[-*+]\s+\[" in p.read_text(encoding="utf-8")
    )

    # When  the vocabulary is looked for, it exists once — in task_boxes.py
    check("the box regex lives in exactly one script", spellers == ["task_boxes.py"], str(spellers))

    # Then  both readers import it and keep no private spelling
    gate = (SCRIPTS / "check_openspec_tasks.py").read_text(encoding="utf-8")
    index = (SCRIPTS / "openspec_index.py").read_text(encoding="utf-8")
    for name, src in (("check_openspec_tasks", gate), ("openspec_index", index)):
        check(f"{name} imports task_boxes", "import task_boxes" in src)
        check(f"{name} uses the shared pattern", "task_boxes.BOX_RE" in src)
        check(f"{name} keeps no private _CHECKBOX/_TASK_BOX regex",
              "_CHECKBOX = re.compile" not in src and "_TASK_BOX = re.compile" not in src)
        check(f"{name} keeps no private state vocabulary", "[ xX~]" not in src)


def test_the_pattern_is_composed_from_the_states_string():
    """BOX_CORE embeds BOX_STATES itself: adding a state there changes every pattern."""

    tb = _load("task_boxes", SCRIPTS / "task_boxes.py")

    # Given the module's own definitions
    core = r"^\s*[-*+]\s+\[([" + tb.BOX_STATES + r"])\]\s+"

    # Then  the pattern is the vocabulary composed into the shape — by construction
    check("BOX_CORE is BOX_STATES composed into the line shape", tb.BOX_CORE == core, tb.BOX_CORE)
    check("BOX_RE is exactly BOX_CORE", tb.BOX_RE.pattern == core)
    check("BOX_RE_MULTILINE is BOX_CORE with MULTILINE",
          tb.BOX_RE_MULTILINE.pattern == core
          and tb.BOX_RE_MULTILINE.flags & __import__("re").MULTILINE)

    # And  every state character in the vocabulary is a one-character class member
    for state in tb.BOX_STATES:
        check(f"BOX_RE matches a box with state {state!r}",
              tb.BOX_RE.match(f"- [{state}] text") is not None)
    check("BOX_RE refuses a state outside the vocabulary",
          tb.BOX_RE.match("- [z] text") is None)


def test_both_readers_classify_every_state_in_the_vocabulary_the_same_way():
    """The gate and the index, run for real on one fixture, agree state by state."""

    tb = _load("task_boxes", SCRIPTS / "task_boxes.py")
    gate = _load("check_openspec_tasks", SCRIPTS / "check_openspec_tasks.py")
    index = _load("openspec_index", SCRIPTS / "openspec_index.py")

    with tempfile.TemporaryDirectory() as td:
        fix = Path(td) / "tasks.md"
        fix.write_text(FIXTURE, encoding="utf-8")

        # When  both readers run on the same file
        boxes = gate._boxes(fix)
        seen = [state for _, state, _ in boxes]
        cell = index._tasks(fix)  # e.g. "4/7 · 1 blocked"
        total = int(cell.split(" · ")[0].split("/")[1])

        # Then  they see the SAME boxes
        check("both readers see the same box count", len(seen) == total, f"gate {len(seen)} vs index {total}")
        check("non-boxes are ignored by both", "- [z]" not in str(boxes) and "mid-line" not in str(boxes))

        # And  each state classifies exactly as the shared helpers say
        expect_done = sum(1 for s in seen if tb.checked(s))
        expect_blocked = sum(1 for s in seen if tb.blocked(s))
        expect_open = sum(1 for s in seen if tb.open_box(s))
        cell_done = int(cell.split(" · ")[0].split("/")[0])
        cell_blocked = int(cell.split(" · ")[1].split()[0]) if " · " in cell else 0
        gate_open = len(gate.unchecked_tasks(fix))
        gate_blocked = len(gate.blocked_tasks(fix))
        check("gate open-count == open_box()", gate_open == expect_open, f"{gate_open} vs {expect_open}")
        check("gate blocked-count == blocked()", gate_blocked == expect_blocked, f"{gate_blocked} vs {expect_blocked}")
        check("index done-count == checked()", cell_done == expect_done, f"{cell_done} vs {expect_done}")
        check("index blocked-count == blocked()", cell_blocked == expect_blocked, f"{cell_blocked} vs {expect_blocked}")
        check("index total counts every box once", total == len(seen))

        # And  the documented fence asymmetry holds (gate skips, index counts)
        fix2 = Path(td) / "fenced.md"
        fix2.write_text(FENCED_FIXTURE, encoding="utf-8")
        check("gate ignores a fenced box", len(gate._boxes(fix2)) == 1)
        check("index counts a fenced box (documented asymmetry)",
              int(index._tasks(fix2).split(" · ")[0].split("/")[1]) == 2)


def _mutation_tree(td: Path, private_regex_gate: bool = False) -> Path:
    """Copies of the vocabulary + both readers, with a NEW state 'b' added to
    BOX_STATES in the vocabulary copy and nowhere else. With private_regex_gate,
    the gate copy instead keeps its own old regex (the pre-#636 shape)."""
    scripts = td / "scripts"
    scripts.mkdir(parents=True, exist_ok=True)
    vocab = (SCRIPTS / "task_boxes.py").read_text(encoding="utf-8")
    assert 'BOX_STATES = " xX~"' in vocab
    (scripts / "task_boxes.py").write_text(
        vocab.replace('BOX_STATES = " xX~"', 'BOX_STATES = " xX~b"'), encoding="utf-8")
    for src_name in ("check_openspec_tasks.py", "openspec_index.py"):
        text = (SCRIPTS / src_name).read_text(encoding="utf-8")
        if private_regex_gate and src_name == "check_openspec_tasks.py":
            text = text.replace(
                "m = task_boxes.BOX_RE.match(ln)",
                'm = re.match(r"^\\s*[-*+]\\s+\\[([ xX~])\\]\\s+", ln)',
            )
        (scripts / src_name).write_text(text, encoding="utf-8")
    return scripts


def _run_mutation(scripts: Path) -> dict:
    """Run the COPIED readers for real, in a fresh process, on a fixture whose
    boxes cover the vocabulary including the added state 'b'."""
    fixture = scripts.parent / "tasks.md"
    fixture.write_text(
        "- [ ] open\n- [x] done\n- [X] capital\n- [~] blocked — blocked: reviewer\n"
        "- [b] brand-new state\n",
        encoding="utf-8",
    )
    prog = textwrap.dedent(
        f"""
        import json, sys
        from pathlib import Path
        sys.path.insert(0, {str(scripts)!r})
        import task_boxes as tb
        import check_openspec_tasks as gate
        import openspec_index as index
        fix = Path({str(fixture)!r})
        seen = [s for _, s, _ in gate._boxes(fix)]
        cell = index._tasks(fix)
        total = int(cell.split(" · ")[0].split("/")[1])
        done = int(cell.split(" · ")[0].split("/")[0])
        blocked = int(cell.split(" · ")[1].split()[0]) if " · " in cell else 0
        print(json.dumps({{
            "gate_seen": seen,
            "gate_open_lines": len(gate.unchecked_tasks(fix)),
            "gate_blocked_lines": len(gate.blocked_tasks(fix)),
            "index_total": total, "index_done": done, "index_blocked": blocked,
            "open_b": tb.open_box("b"), "checked_b": tb.checked("b"), "blocked_b": tb.blocked("b"),
        }}))
        """
    )
    out = subprocess.run([sys.executable, "-c", prog], capture_output=True, text=True)
    assert out.returncode == 0, out.stderr
    return json.loads(out.stdout)


def test_a_state_added_in_the_one_place_is_a_box_for_both_readers():
    """Add state 'b' to BOX_STATES in the ONE place: both copied readers see it."""

    # Given  copies with the new state declared in the vocabulary only
    with tempfile.TemporaryDirectory() as td:
        scripts = _mutation_tree(Path(td))

        # When  both copied readers run on a fixture using - [b]
        r = _run_mutation(scripts)

        # Then  the gate sees 'b' as a box, and classifies it like the index does
        check("gate sees the new state as a box", r["gate_seen"].count("b") == 1, str(r["gate_seen"]))
        check("index sees the new state in its total", r["index_total"] == 5, str(r))
        check("both totals agree", len(r["gate_seen"]) == r["index_total"])
        check("neither reader calls it open/done/blocked",
              r["open_b"] is False and r["checked_b"] is False and r["blocked_b"] is False)
        check("gate open-count unchanged by the new state", r["gate_open_lines"] == 1, str(r))
        check("gate blocked-count unchanged by the new state", r["gate_blocked_lines"] == 1, str(r))
        check("index done-count unchanged by the new state", r["index_done"] == 2, str(r))
        check("index blocked-count unchanged by the new state", r["index_blocked"] == 1, str(r))

    # And  the scenario BITES: a gate copy that re-grew its private regex (the
    # pre-#636 shape) silently misses the state the index counts.
    with tempfile.TemporaryDirectory() as td:
        drift = _mutation_tree(Path(td), private_regex_gate=True)
        r2 = _run_mutation(drift)
        check("a private-regex gate MISSES the new state (guard bites)",
              "b" not in r2["gate_seen"] and r2["index_total"] == 5, str(r2))
        check("the divergence shows up as disagreeing totals",
              len(r2["gate_seen"]) != r2["index_total"], str(r2))


def test_this_module_is_wired_into_make_test():
    check("wired into make test via the runner", wired(__file__))


def main():
    test_the_box_vocabulary_has_exactly_one_home()
    test_the_pattern_is_composed_from_the_states_string()
    test_both_readers_classify_every_state_in_the_vocabulary_the_same_way()
    test_a_state_added_in_the_one_place_is_a_box_for_both_readers()
    test_this_module_is_wired_into_make_test()
    print(f"\nPASSED {_PASS} | FAILED {_FAIL}")
    return 1 if _FAIL else 0


if __name__ == "__main__":
    raise SystemExit(main())
