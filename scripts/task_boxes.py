#!/usr/bin/env python3
"""The ONE task-box vocabulary every OpenSpec `tasks.md` reader shares (issue #636).

Two readers parse a change's checkboxes:

    scripts/check_openspec_tasks.py   the completion gate (fails unchecked boxes)
    scripts/openspec_index.py         the index generator (counts done/blocked)

Before this module each spelled the box regex itself — added side by side in the
same change that introduced `~` — and nothing made them agree about what a box
IS. A fourth state added to one reader was silently a non-task in the other,
which is exactly how `- [~]` once read as "all tasks checked" (issue #409). This
is rule 6j's marker rule for a vocabulary: one definition, no reader copies.

The vocabulary:

    BOX_STATES       every character allowed inside the brackets
    BOX_CORE         the line shape, COMPOSED from BOX_STATES (not spelled beside it)
    box_pattern()    compile the shape — a state added to BOX_STATES propagates
                     to every reader by construction
    BOX_RE / BOX_RE_MULTILINE   the ready patterns (gate matches per line; the
                     index findalls across a file)

The classification lives here too, so "what a state means" cannot diverge:

    open_box(state)  the failing unchecked state
    checked(state)   done
    blocked(state)   waiting on a human (the gate additionally demands a
                     `blocked:` annotation — that is gate semantics, not vocabulary)

Adding a state means: add the character to BOX_STATES, teach the helpers, and
tests/test_task_boxes.py proves BOTH readers see it — its mutation scenario
runs copies of this module and both readers with a new state added HERE and
nowhere else, so a reader that grew a private regex fails it.
"""

from __future__ import annotations

import re

# Every character allowed inside the brackets. One character per state; the
# classification helpers below must say what each one means.
BOX_STATES = " xX~"

# The line shape: a list marker (`-`, `*`, `+`) then a bracket holding exactly
# one state character, then the task text. Group 1 is the state character.
BOX_CORE = r"^\s*[-*+]\s+\[([" + BOX_STATES + r"])\]\s+"


def box_pattern(flags: int = 0) -> re.Pattern[str]:
    """The compiled box pattern, composed from BOX_STATES at call time.

    Compiling per call (these scripts run a handful of times per pipeline) is
    the seam: a state added to BOX_STATES is in every reader's next pattern.
    """
    return re.compile(BOX_CORE, flags)


BOX_RE = box_pattern()
BOX_RE_MULTILINE = box_pattern(re.MULTILINE)


def open_box(state: str) -> bool:
    """The unchecked state — the box nobody has ticked."""
    return state == " "


def checked(state: str) -> bool:
    """The done state (both `- [x]` and `- [X]` spellings)."""
    return state.lower() == "x"


def blocked(state: str) -> bool:
    """The blocked state — done as far as an agent may take it, waiting on a human."""
    return state == "~"
