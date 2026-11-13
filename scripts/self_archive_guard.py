#!/usr/bin/env python3
"""Refuse a fix round that dismantles its branch's own OpenSpec change (issue #812).

Measured defect (issue #812): a `make fix` round on a branch under
scripts/fix_loop.sh ran `make openspec-archive`, and the loop STAGED the result
(`git add -A`) and went green — then the commit/push steps landed the branch with
its OpenSpec change moved from `openspec/changes/<name>/` into
`openspec/changes/archive/<name>/` with the PR still open. The archive dirs hold
MERGED work (AGENTS.md rule 6f: "the change lifecycle closes AT THE PR"), and
`make openspec-archive-check` (issue #779) reads the ACTIVE changes to refuse a
merge that strands one — dismantling the change mid-run makes that gate blind:
every check passed while the trail was dismantled.

Two modes, both reached only through `make self-archive-snapshot` /
`make self-archive-guard` (AGENTS.md rules 6d/6m):

  snapshot  writes the OpenSpec changes active ON DISK right now (plus the
            archive names present) as JSON to $SELF_ARCHIVE_BASELINE.
            scripts/fix_loop.sh calls this once per run, after its base merge.

  check     every change active at the baseline that is no longer on disk is a
            dismantle:
              * it appeared in openspec/changes/archive/ and was not there at the
                baseline  -> self-archive (the #812 shape);
              * otherwise -> vanished.
            With SELF_ARCHIVE_RESTORE=1 the change is put back FIRST:
              * the fresh archive copy is moved back on the filesystem (this also
                covers a change the loop never committed), then
              * else the baseline files are restored from $SELF_ARCHIVE_REF
                (default HEAD; scripts/fix_loop.sh pins it at the post-merge tip),
              * else the loss is reported as unrecoverable.
            The verdict is printed either way and stays red (exit 1) so the
            round's report names what happened.

Changes created AFTER the snapshot are this run's own new artifacts: they are not
guarded (a run may remove a scaffold it just made; it may not delete history).

Exit codes: 0 clean, 1 dismantled (restored when asked), 2 unreadable inputs —
no baseline file, a snapshot that cannot read the tree, a bad git reference. A
guard that silently cannot run is the defect this script exists to prevent.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

CHANGES = Path("openspec/changes")
ARCHIVE = CHANGES / "archive"

_BASELINE = os.environ.get("SELF_ARCHIVE_BASELINE", "")
_REF = os.environ.get("SELF_ARCHIVE_REF", "HEAD")
_RESTORE = os.environ.get("SELF_ARCHIVE_RESTORE", "") == "1"


def _git(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], capture_output=True, text=True)


def active_names() -> list[str]:
    """Change directories currently active on disk (everything under
    openspec/changes/ except the archive/ subdir), sorted, deterministic."""
    if not CHANGES.is_dir():
        return []
    return sorted(
        p.name for p in CHANGES.iterdir()
        if p.is_dir() and p.name != "archive" and p.name != ".git"
    )


def archive_names() -> list[str]:
    if not ARCHIVE.is_dir():
        return []
    return sorted(p.name for p in ARCHIVE.iterdir() if p.is_dir())


def cmd_snapshot() -> int:
    if not _BASELINE:
        print("guard: SELF_ARCHIVE_BASELINE is not set — the snapshot has nowhere to write",
              file=sys.stderr)
        return 2
    data = {"active": active_names(), "archive": archive_names()}
    try:
        Path(_BASELINE).write_text(json.dumps(data) + "\n")
    except OSError as exc:
        print(f"guard: cannot write the baseline {_BASELINE}: {exc}", file=sys.stderr)
        return 2
    print(f"self-archive snapshot: {len(data['active'])} active changes, "
          f"{len(data['archive'])} archived (baseline {_BASELINE})")
    return 0


def _tracked_at_ref(name: str) -> bool:
    """Were files of openspec/changes/<name>/ tracked at the reference commit?"""
    res = _git("ls-tree", "-r", "--name-only", _REF, "--", str(CHANGES / name))
    if res.returncode != 0:
        return False
    return bool(res.stdout.strip())


def _restore(name: str, fresh_archive: bool) -> tuple[bool, str]:
    """Put the change back. Returns (restored, how)."""
    target = CHANGES / name
    moved_from = ARCHIVE / name
    if fresh_archive and moved_from.is_dir():
        # The round moved it (tracked or not): move the whole directory back,
        # then re-stage openspec/changes so an index staged by the loop's
        # `git add -A` matches the repaired tree.
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            if target.exists():
                shutil.rmtree(target)
            shutil.move(str(moved_from), str(target))
        except OSError as exc:
            return False, f"move-back failed: {exc}"
        if _git("rev-parse", "--git-dir").returncode == 0:
            _git("add", "-A", "--", str(CHANGES))
        return True, f"moved back from {moved_from}"
    if _tracked_at_ref(name):
        res = _git("checkout", _REF, "--", str(CHANGES / name))
        if res.returncode != 0:
            return False, f"git checkout {_REF} failed: {res.stderr.strip()}"
        return True, f"restored from {_REF}"
    return False, "unrecoverable: neither a fresh archive copy nor files tracked at the reference"


def cmd_check() -> int:
    if not _BASELINE:
        print("guard: SELF_ARCHIVE_BASELINE is not set — run `make self-archive-snapshot` first",
              file=sys.stderr)
        return 2
    try:
        baseline = json.loads(Path(_BASELINE).read_text())
    except (OSError, ValueError) as exc:
        print(f"guard: cannot read the baseline {_BASELINE}: {exc} — "
              "run `make self-archive-snapshot` first", file=sys.stderr)
        return 2
    baseline_active = set(baseline.get("active") or [])
    baseline_archive = set(baseline.get("archive") or [])
    if not baseline_active and not (CHANGES.is_dir() or ARCHIVE.is_dir()):
        # No OpenSpec changes existed at the snapshot: nothing can be dismantled.
        print("no self-archive (baseline carried no active changes)")
        return 0

    findings: list[str] = []
    for name in sorted(baseline_active):
        if (CHANGES / name).is_dir():
            continue
        fresh_archive = (ARCHIVE / name).is_dir() and name not in baseline_archive
        kind = "self-archive" if (ARCHIVE / name).is_dir() else "vanish"
        if _RESTORE:
            ok, how = _restore(name, fresh_archive)
            if ok:
                findings.append(f"{kind}: openspec/changes/{name} was dismantled mid-run — "
                                f"the guard restored it ({how})")
                continue
            findings.append(f"{kind}: openspec/changes/{name} was dismantled mid-run — "
                            f"NOT RESTORED ({how})")
        else:
            where = f"now at {ARCHIVE / name}" if (ARCHIVE / name).is_dir() else "no copy on disk"
            findings.append(f"{kind}: openspec/changes/{name} was active at the baseline, "
                            f"is gone from the tree ({where})")

    if not findings:
        print(f"no self-archive ({len(baseline_active)} baseline-active changes intact)")
        return 0
    for line in findings:
        print(line)
    print("AGENTS.md 3b/6f: a branch archives its OpenSpec change when its PR MERGES "
          "(openspec-record-pr), never mid-repair — a dismantled change blinds the "
          "#779 archive gate (issue #812).")
    return 1


def main(argv: list[str]) -> int:
    mode = argv[1] if len(argv) > 1 else "check"
    if mode == "snapshot":
        return cmd_snapshot()
    if mode == "check":
        return cmd_check()
    print(f"guard: unknown mode {mode!r} (expected snapshot or check)", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
