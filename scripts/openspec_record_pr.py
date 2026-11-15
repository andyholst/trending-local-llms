#!/usr/bin/env python3
"""Record the PR that completed a change AND archive it, in the completing PR (issue #518) — and raise that issue's pipeline-failure ledger row (`fix_pr` + `guard`, issue #1068).

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
import json
import re
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import openspec_index  # noqa: E402  (the ONE index generator + the shared _refs, rule 6d)

ROOT = Path(__file__).resolve().parent.parent

#: A change's proposal already ends with a `PR:` header line? (either spelling)
_EXISTING_PR = re.compile(r"^\**\s*PR:\**\s*[^\n]*$", re.MULTILINE)

#: The append-only pipeline-failure ledger whose `fix_pr` this seam raises (issue #1068).
#: Rule 6r: "the fix PR raises its ledger row (append-only) with `fix_pr` + `guard`" —
#: this is the mechanical half: recording the completing PR and stamping the ledger row
#: are the SAME moment, so a merged pipeline-failure fix can never again leave its row
#: `fix_pr: null` for the gate to red on the next master push (measured: run 43761917321).
_LEDGER_REL = "data/pipeline_failures.json"

#: A spec scenario's locked test: `- **Test:** tests/test_x.py::test_y` — the module is
#: the ledger `guard` candidate (the same `tests/test_*.py` shape the gate requires).
_TEST_REF = re.compile(r"^\- \*\*Test:\*\* (tests/test_[A-Za-z0-9_]+\.py)(?:::[^\n]*)?", re.MULTILINE)


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


def _proposal_names_issue(path: Path, issue: int) -> bool:
    """Does this change's proposal reference `Issue: #<issue>` — through the ONE parser."""
    refs = openspec_index._refs(path / "proposal.md")
    m = re.search(r"#(\d+)", refs.get("Issue") or "")
    return m is not None and int(m.group(1)) == issue


def _spec_test_modules(change_dir: Path) -> list[str]:
    """The `tests/test_*.py` modules this change's scenarios lock (document order)."""
    mods: list[str] = []
    for spec in sorted(change_dir.glob("specs/*/spec.md")):
        for m in _TEST_REF.finditer(spec.read_text(encoding="utf-8")):
            if m.group(1) not in mods:
                mods.append(m.group(1))
    return mods


def _entry_window(text: str, run_id: int) -> tuple[int, int]:
    """(start, end) character span of the ledger entry whose `run_id` is this value."""
    m = re.search(rf'"run_id": {run_id},?\n', text)
    if m is None:
        raise ValueError(f'no "run_id": {run_id} entry in the ledger')
    start = text.rfind("{", 0, m.start())
    end = text.find('"run_id":', m.end())
    if end == -1:
        end = text.rfind("}")
    return start, end


def plan_ledger_stamp(root: Path, issue: int, pr: int, spec_mods: list[str]) -> dict:
    """Decide the ledger raise for issue #<issue> BEFORE any mutation (read-only).

    Additive only (rule 3b): a row whose `fix_pr` is already raised is never touched.
    A null `fix_pr` is raised to `pr`; its `guard` is KEPT when the row already names
    one, FILLED from the change's own `- **Test:**` modules when null, and if neither
    resolves to a module that exists under `tests/`, the whole recording is REFUSED
    (stamping `fix_pr` without a guard is exactly the shape the ledger gate reds on
    the next master push — refusing loudly is the fix, not a silent half-raise).

    Returns {"stamps": [(run_id, guard_or_None)], "text": str|None, "refusal": str|None}.
    """
    ledger = root / _LEDGER_REL
    if not ledger.exists():
        return {"stamps": [], "rows": 0, "text": None, "refusal": None}
    text = ledger.read_text(encoding="utf-8")
    data = json.loads(text)
    stamps: list[tuple[int, str | None]] = []
    rows_found = 0
    for e in data.get("failures", []):
        raw = e.get("issue_number")
        if raw is None or str(raw) != str(issue):
            continue
        run_id = e.get("run_id")
        if run_id is None:
            continue
        rows_found += 1
        if e.get("fix_pr") is not None:
            continue  # already raised — never rewritten (rule 3b)
        guard = e.get("guard")
        if guard:
            stamps.append((run_id, guard))
            continue
        resolved = next((mod for mod in spec_mods if (root / mod).is_file()), None)
        if resolved is None:
            return {"stamps": [], "rows": rows_found, "text": text, "refusal":
                    f"ledger row run {run_id} (issue #{issue}) has null fix_pr AND null guard, and "
                    f"the change names no test module that exists under tests/ — refusing to stamp "
                    f"fix_pr without a guard (the gate reds that shape on the next master push)"}
        stamps.append((run_id, resolved))
    return {"stamps": stamps, "rows": rows_found, "text": text, "refusal": None}


def apply_ledger_stamp(root: Path, plan: dict, pr: int) -> list[int]:
    """Apply the planned raise to the ledger: surgical fills inside each entry's own
    window, every other byte untouched (rule 3b: keys added, never removed)."""
    text = plan["text"]
    stamped: list[int] = []
    for run_id, guard in plan["stamps"]:
        start, end = _entry_window(text, run_id)
        seg = text[start:end]
        m = re.search(r'"fix_pr": null', seg)
        if m is None:
            continue  # raced or already raised — leave it alone
        seg = seg[: m.start()] + f'"fix_pr": {pr}' + seg[m.end():]
        if guard:
            m = re.search(r'"guard": null', seg)
            if m is not None:
                seg = seg[: m.start()] + f'"guard": "{guard}"' + seg[m.end():]
            elif '"guard"' not in seg:
                m = re.search(r'"issue_number": [^\n]*\n', seg)
                if m is None:
                    raise ValueError(f"entry run {run_id} has no issue_number line to insert guard after")
                seg = seg[: m.end()] + f'      "guard": "{guard}",\n' + seg[m.end():]
        text = text[: start] + seg + text[end:]
        stamped.append(run_id)
    if stamped:
        now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        m = re.search(r'"updated_utc": "([^"]*)"', text)
        if m is None:
            text = text.replace("{\n", '{\n  "updated_utc": "' + now + '",\n', 1)
        elif now >= m.group(1):  # a timestamp only moves FORWARD (rule 3b)
            text = text[: m.start()] + f'"updated_utc": "{now}"' + text[m.end():]
        ledger = root / _LEDGER_REL
        json.loads(text)  # never write a ledger this seam cannot itself parse
        ledger.write_text(text, encoding="utf-8")
    return stamped


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
        if not _proposal_names_issue(path, issue):
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
        if _proposal_names_issue(path, issue):
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

    # The ledger stamp is DECIDED before any mutation (issue #1068): a refusal must
    # leave the tree exactly as it found it — changes active, ledger untouched.
    spec_mods: list[str] = []
    for _name, path in _active_changes(root):
        if _proposal_names_issue(path, a.issue):
            spec_mods += _spec_test_modules(path)
    for _name, path in _archived_changes(root):
        if _proposal_names_issue(path, a.issue):
            spec_mods += _spec_test_modules(path)
    plan = plan_ledger_stamp(root, a.issue, a.pr, spec_mods)
    if plan["refusal"]:
        print(f"[openspec-record-pr] REFUSED: {plan['refusal']}", file=sys.stderr)
        return 2

    try:
        names = record(a.issue, a.pr, root)
    except AlreadyThere as exc:
        # A benign re-run — but the ledger raise is NOT benign to skip: the #833 shape
        # (change already archived, row still null) is repaired here too (issue #1068).
        re_stamped = apply_ledger_stamp(root, plan, a.pr) if plan["stamps"] else []
        if re_stamped:
            _regen_index(root)
        print(f"[openspec-record-pr] already recorded: {', '.join(exc.args[0])} "
              f"for issue #{a.issue} is already archived — nothing to do"
              + (f"; ledger raised for run(s) {', '.join(str(r) for r in re_stamped)}"
                 if re_stamped else ""))
        return 0
    except NoSuchChange as exc:
        print(f"[openspec-record-pr] REFUSED: {exc}", file=sys.stderr)
        return 2

    # The index is part of the change: a recorded/archived change without the
    # regenerated row would drift from `make openspec-index` next run.
    _regen_index(root)
    stamped = apply_ledger_stamp(root, plan, a.pr) if plan["stamps"] else []
    if stamped:
        stamp_note = f"; raised `fix_pr: {a.pr}` on ledger row(s) for run(s) " \
                     f"{', '.join(str(r) for r in stamped)}"
    elif plan["rows"]:
        stamp_note = f"; ledger row(s) for issue #{a.issue} are already raised — untouched"
    elif plan["text"] is not None:
        stamp_note = f"; no ledger row references issue #{a.issue}"
    else:
        stamp_note = "; no ledger file"
    print(f"[openspec-record-pr] recorded PR #{a.pr} and archived {len(names)} change(s) "
          f"for issue #{a.issue}: {', '.join(names)}{stamp_note}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
