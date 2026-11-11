#!/usr/bin/env python3
"""Record the PR that completed a change AND archive it, in the completing PR (issue #518).

Rule 6f gives every change a life that ENDS in the PR completing it: once its
`PR:` line is known, that PR writes `PR: #<n>` AND moves the change to
`openspec/changes/archive/`, regenerating the index — so a merged change never
sits "active" for which the guard's "none names a PR" was vacuous.

The gap measured on `master`: `scripts/openspec_archive_check.py` could only see
a change that CARRIED a `PR:` line, and 110 of 111 active changes had none — a
change written without a PR (every one created before #183, plus every one whose
author did not know its PR number at authoring time) was merged and forgotten
while the guard reported a vacuous OK.

This is the recording + archiving half, and it belongs to the WORKFLOW that opens
the PR, so no change can ever reach a merge without its completing-PR reference
exposed to the guard: the implementer bot, once `gh pr create` returns a number,
runs `openspec-record-pr ISSUE=<n> PR=<m>` to (1) write `PR: #<m>` into every
ACTIVE change whose proposal references `Issue: #<n>` and (2) move those changes
to `archive/`, then regenerate the index — host-side, deterministic, no model.

It finds the change by its `Issue:` ref through the SHARED parser
(`scripts/openspec_index.py::_refs`, rule 6d — one reader), so it can never
target a change that references a different issue. An ARCHIVED change for the
same issue is the state an earlier run already recorded (issue #754), so a re-run
is a benign no-op (exit 0) that names the change as already archived; it refuses
(exit 2) loudly only when NO change — active or archived — references that issue:
a step that silently matched nothing would leave the change unrecorded and the
guard vacuous again.

Usage:
    make openspec-record-pr ISSUE=518 PR=523
    python3 scripts/openspec_record_pr.py --issue 518 --pr 523
"""

from __future__ import annotations

import argparse
import re
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import openspec_index  # noqa: E402  (the ONE index generator + the shared _refs, rule 6d)

ROOT = Path(__file__).resolve().parent.parent

#: A change's proposal already ends with a `PR:` header line? (either spelling)
_EXISTING_PR = re.compile(r"^\**\s*PR:\**\s*[^\n]*$", re.MULTILINE)


class NoSuchChange(Exception):
    """No change — active OR archived — references the given issue: nothing recorded."""


class AlreadyThere(Exception):
    """Every change for the issue was already archived with a recorded PR (a benign re-run)."""



def _insert_pr(text: str, pr: int) -> str:
    """Place the `PR:` line immediately after the proposal's `Issue:` header.

    Keeps the two header lines adjacent (the shape an archived change's proposal
    ends with), whatever the surrounding prose; the shared parser reads it at line
    start regardless, and an existing PR line is replaced in place.
    """
    line = f"PR: #{pr}"
    existing = _EXISTING_PR.search(text)
    if existing:
        return _EXISTING_PR.sub(line, text, count=1)
    m = re.search(r"^\**\s*Issue:\**[^\n]*$", text, re.MULTILINE)
    if m:
        return text[: m.end()] + f"\n{line}" + text[m.end():]
    return text.rstrip("\n") + f"\n{line}\n"


def _active_changes(root: Path) -> list[tuple[str, Path]]:
    changes = root / "openspec" / "changes"
    return [c for c in openspec_index.discover(changes)[0]]


def _archived_changes(root: Path) -> list[tuple[str, Path]]:
    changes = root / "openspec" / "changes"
    return [c for c in openspec_index.discover(changes)[1]]


def record(issue: int, pr: int, root: Path = ROOT) -> list[str]:
    """Write `PR: #<pr>` into every ACTIVE change referencing issue #<issue> and
    move it to `archive/`.

    Returns the names of the changes it archived; raises `NoSuchChange` when no
    change (active OR archived) references the issue, and `AlreadyThere` when
    every matching change is already archived (a re-run of the same recording —
    a benign no-op that must not look like a failure).

    Additive only: an existing `PR:` line is replaced in place, never duplicated,
    and no other file is rewritten.
    """
    targeted: list[str] = []
    already: list[str] = []
    for name, path in _active_changes(root):
        refs = openspec_index._refs(path / "proposal.md")
        iss_ref = refs.get("Issue")
        m = re.search(r"#(\d+)", iss_ref or "")
        if m is None or int(m.group(1)) != issue:
            continue
        proposal = path / "proposal.md"
        text = proposal.read_text(encoding="utf-8")
        proposal.write_text(_insert_pr(text, pr), encoding="utf-8")
        archive_dir = root / "openspec" / "changes" / "archive"
        archive_dir.mkdir(parents=True, exist_ok=True)
        dest = archive_dir / name
        if dest.exists():
            shutil.rmtree(dest)
        shutil.move(str(path), str(dest))
        targeted.append(name)
    if targeted:
        return targeted
    # No ACTIVE change matched — the recording may already have happened. An
    # ARCHIVED change for this issue is that state (its completing PR was recorded
    # and it was moved in an earlier run), so a re-run is a benign no-op, never a
    # failure. Only when no archived change references the issue either is the
    # recording genuinely unmatched, and that is refused loudly.
    for name, path in _archived_changes(root):
        refs = openspec_index._refs(path / "proposal.md")
        iss_ref = refs.get("Issue")
        m = re.search(r"#(\d+)", iss_ref or "")
        if m is not None and int(m.group(1)) == issue:
            already.append(name)
    if already:
        raise AlreadyThere(already)
    raise NoSuchChange(f"no change — active or archived — references Issue: #{issue} — nothing recorded")



def _regen_index(root: Path) -> None:
    """Regenerate OPENSPEC.md for `root` through the ONE generator.

    `openspec_index` reads its module-global ROOT/CHANGES/INDEX (its own repo by
    default); point them at the target root so a test can record into a fixture
    tree without touching this checkout.
    """
    openspec_index.ROOT = root
    openspec_index.CHANGES = root / "openspec" / "changes"
    openspec_index.INDEX = root / "OPENSPEC.md"
    openspec_index.main(["--write"])


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Record the completing PR on a change and archive it (issue #518).")
    ap.add_argument("--issue", type=int, required=True, help="the issue this PR implements")
    ap.add_argument("--pr", type=int, required=True, help="the PR number to record")
    ap.add_argument("--root", default=str(ROOT), help="repository root (default: this checkout)")
    a = ap.parse_args(argv)

    root = Path(a.root)
    try:
        names = record(a.issue, a.pr, root)
    except AlreadyThere as exc:
        print(f"[openspec-record-pr] already recorded: {', '.join(exc.args[0])} "
              f"for issue #{a.issue} is already archived — nothing to do")
        return 0
    except NoSuchChange as exc:
        print(f"[openspec-record-pr] REFUSED: {exc}", file=sys.stderr)
        return 2

    # The index is part of the change: a recorded/archived change without the
    # regenerated row would drift from `make openspec-index` next run.
    _regen_index(root)
    print(f"[openspec-record-pr] recorded PR #{a.pr} and archived {len(names)} change(s) "
          f"for issue #{a.issue}: {', '.join(names)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
