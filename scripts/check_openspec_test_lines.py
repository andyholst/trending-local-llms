#!/usr/bin/env python3
"""Resolve every active change spec's `- **Test:** <path>::<test>` reference against the tree and fail when it does not (issue #621).

`openspec validate` proves a change's STRUCTURE and `openspec-tasks-check`
proves its checklist is ticked, but neither resolves the `- **Test:**` line
that rule 6f says LOCKS a scenario's behaviour — so a change can cite a file and
a test that were never written and the gate stays green. This script is that
resolution half of the gate.

For every ACTIVE (non-archived) change it reads every capability spec, extracts
each `- **Test:** <path>::<test>` reference and resolves it against the tree:

  * the `<path>` must exist under the repository; and
  * when `<path>` is a tracked Python module, the `<test>` name must be defined
    top-level in it (a `def`/`class`, or a module-level assignment) — so the
    measured failure (a spec citing `tests/test_agents_rows.py::test_the_footprint_sentence_names_every_dimension`
    in all four scenarios while neither the file nor the def existed) is RED,
    not satisfied by a same-named file with a different body.

A reference that does not resolve FAILS the gate, naming the change, the spec
file:line (scenario) and the missing target.

A `- **Test:**` line that names no `path::test` — prose, or a bare path with no
`::symbol` — is NOT a resolvable reference: it is REPORTED as a note, never
counted as resolved, so the scan cannot read as verified while its references
are prose. A change whose specs carry no `- **Test:**` lines at all is likewise
reported as having nothing to resolve. Archived changes are excluded (they keep
the shape they were reviewed with).

Wired into `make openspec-spec-tests-check`, which `make openspec-check` runs
and `qa-validate` calls on every PR (rule 6d: reachable from a make target CI
runs).

Usage:
    python3 scripts/check_openspec_test_lines.py            # all active changes
    python3 scripts/check_openspec_test_lines.py <name>     # just <name>
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
CHANGES_DIR = REPO_ROOT / "openspec" / "changes"

# A `- **Test:**` line. Anchored to the START of a list item (the tree's
# convention), so an inline prose mention ("read every `- **Test:**` line")
# inside a Requirement paragraph is never read as a scenario's citation. The
# reference token is EITHER a backtick-wrapped span right after the marker
# (`tests/x.py::test_x` — common when the line carries trailing prose after a
# `—`) OR the first whitespace-delimited word.
_MARKER = re.compile(r"^\s*-\s*\*\*Test:\*\*\s*")
_TOKEN = re.compile(r"`([^`]+)`|(\S+)")
# A `path::symbol` where `symbol` is a plain Python identifier.
_SYMBOL = re.compile(r"^[A-Za-z_]\w*$")


def _spec_files(change: Path) -> list[Path]:
    """The change's capability specs, sorted ([] when it has none)."""
    base = change / "specs"
    if not base.is_dir():
        return []
    return sorted(base.glob("*/spec.md"))


def _reference(line: str) -> str | None:
    """The `<path>::<symbol>` token on a `- **Test:**` line, else None.

    `- **Test:** `tests/x.py::test_x`` -> `tests/x.py::test_x`.
    `- **Test:** tests/x.py::test_x` -> `tests/x.py::test_x`.
    `- **Test:** tests/x.py (the ...`  -> None (no `::symbol`).
    `- **Test:** `scripts/self_test.py`` -> None (no `::symbol`).
    """
    m = _MARKER.search(line)
    if not m:
        return None
    tok = _TOKEN.search(line, m.end())
    if not tok:
        return None
    token = (tok.group(1) or tok.group(2)).strip()
    # A backticked span may carry a trailing `-` LITERALLY; drop a stray tail
    # backtick and any trailing colon so `...::test_x` parses cleanly.
    if token.endswith("`"):
        token = token[:-1]
    path, _, sym = token.partition("::")
    if not path or not sym:
        return None
    if not _SYMBOL.match(sym):
        return None
    return f"{path}::{sym}"


def _definition_names(module: Path) -> set[str]:
    """Every name defined top-level in *module* (`def`/`class`/`x = ...`)."""
    try:
        text = module.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return set()
    names: set[str] = set()
    for m in re.finditer(
        r"^(?:def|class)\s+([A-Za-z_]\w*)(?=\s*[\(:]|$)|^([A-Za-z_]\w*)\s*=\s*",
        text,
        re.M,
    ):
        names.add(m.group(1) or m.group(2))
    return names


def _resolve(ref: str, root: Path) -> str | None:
    """None when the reference resolves; else a short reason (missing file / symbol)."""
    path, _, sym = ref.partition("::")
    target = root / path
    if not target.is_file():
        return f"no such file `{path}`"
    if target.suffix != ".py":
        return None
    if sym in _definition_names(target):
        return None
    return f"`{path}` defines no top-level `{sym}`"


def _scan_change(
    name: str, change: Path, root: Path
) -> tuple[list[str], list[str]]:
    """(failures, notes) for one ACTIVE change's specs.

    A failure is a resolvable-reference-shaped citation that does not resolve.
    A note is a `- **Test:**` line that names no `path::symbol`, or a change
    whose specs carry no Test line at all — reported so the scan is never
    vacuous, never a failure.
    """
    failures: list[str] = []
    notes: list[str] = []
    saw_test_line = False
    for spec in _spec_files(change):
        rel = spec.relative_to(root)
        try:
            lines = spec.read_text(encoding="utf-8").splitlines()
        except OSError:
            failures.append(f"[openspec-test-lines] {name}: cannot read {rel}")
            continue
        for i, line in enumerate(lines, 1):
            if not _MARKER.search(line):
                continue
            saw_test_line = True
            ref = _reference(line)
            if ref is None:
                notes.append(
                    f"[openspec-test-lines] NOTE {name}:{rel}:{i} a `- **Test:**` "
                    f"line names no `<path>::<test>` reference — not resolved"
                )
                continue
            reason = _resolve(ref, root)
            if reason is not None:
                failures.append(
                    f"[openspec-test-lines] FAIL {name}: scenario at {rel}:{i} cites "
                    f"`{ref}` — {reason}"
                )
    if not saw_test_line:
        notes.append(
            f"[openspec-test-lines] NOTE {name}: no `- **Test:**` reference in any "
            f"active spec — nothing to resolve (vacuous)"
        )
    return failures, notes


def active_change_names(base: Path = CHANGES_DIR) -> list[str]:
    """All ACTIVE (non-archived) change names that have a proposal."""
    if not base.is_dir():
        return []
    out = []
    for p in sorted(base.iterdir()):
        if not p.is_dir() or p.name == "archive":
            continue
        if (p / "proposal.md").is_file():
            out.append(p.name)
    return out


def change_for(name: str, base: Path = CHANGES_DIR) -> Path | None:
    """The ACTIVE change dir for *name*; None if archived or missing."""
    if (base / "archive" / name).exists():
        return None
    p = base / name
    return p if p.is_dir() else None


def check_all(
    only: str | None = None,
    base: Path = CHANGES_DIR,
    root: Path | None = None,
    verbose: bool = True,
) -> int:
    """Check ACTIVE changes (all, or just *only*). Returns the # of failing changes.

    `base` is the `openspec/changes` directory; `root` is the repository root the
    referenced `<path>`s resolve against (defaults to this checkout — the tests
    pass a fixture tree for both).
    """
    if root is None:
        root = REPO_ROOT
    targets = [only] if only else active_change_names(base)
    if only is None and not targets:
        if verbose:
            print("[openspec-test-lines] no active changes — nothing to resolve", flush=True)
        return 0
    failures = 0
    for name in targets:
        change = change_for(name, base)
        if change is None:
            if verbose:
                print(f"[openspec-test-lines] FAIL {name}: no active change (archived/missing)")
            failures += 1
            continue
        bad, notes = _scan_change(name, change, root)
        failures += 1 if bad else 0
        for line in bad:
            print(line, file=sys.stderr, flush=True)
        for line in notes:
            print(line, flush=True)
    if verbose and failures == 0 and (only is None or targets):
        print(
            f"[openspec-test-lines] OK: every active change's `- **Test:** <path>::<test>` "
            f"resolves in the tree",
            flush=True,
        )
    return failures


if __name__ == "__main__":
    _target = sys.argv[1] if len(sys.argv) > 1 else None
    raise SystemExit(1 if check_all(_target) > 0 else 0)