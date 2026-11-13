#!/usr/bin/env python3
"""Regression tests for scripts/self_archive_guard.py (issue #812).

The measured defect: a `make fix` round inside scripts/fix_loop.sh ran
`make openspec-archive` on its own change; the tree landed with the change moved
from openspec/changes/<name>/ into openspec/changes/archive/ while the PR was
still open — every gate green, and `make openspec-archive-check` (#779) blind
because it reads the ACTIVE changes.

These tests drive the REAL guard against real throwaway git repositories:
  - a clean tree is green;
  - a move into openspec/changes/archive/ mid-run is reported (and restored);
  - an archive already present at the baseline (the base merged it) is NOT a dismantle;
  - a committed mid-run move is restored too, and the index is re-staged;
  - a vanished change (no archive copy) is restored from the reference commit;
  - an unrecoverable loss is reported loudly, not silently;
  - a missing baseline is a loud exit 2, never a vacuous pass;
  - a change created AFTER the snapshot belongs to this run and is not guarded.

Run:  python3 tests/test_self_archive_guard.py   or   make test
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
GUARD = ROOT / "scripts" / "self_archive_guard.py"

_PASS = 0
_FAIL = 0


def check(name, cond, detail: object = ""):
    global _PASS, _FAIL
    if cond:
        _PASS += 1
        print(f"  ok  {name}")
    else:
        _FAIL += 1
        print(f"  FAIL {name}" + (f"  [{detail}]" if detail else ""))


def git(repo: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], cwd=str(repo), capture_output=True, text=True,
                          env=dict(os.environ,
                                   GIT_AUTHOR_NAME="guard-test",
                                   GIT_AUTHOR_EMAIL="guard@test.invalid",
                                   GIT_COMMITTER_NAME="guard-test",
                                   GIT_COMMITTER_EMAIL="guard@test.invalid"))


def run_guard(repo: Path, mode: str, baseline: Path, restore: bool = False,
              ref: str = "") -> subprocess.CompletedProcess:
    env = dict(os.environ, SELF_ARCHIVE_BASELINE=str(baseline))
    if restore:
        env["SELF_ARCHIVE_RESTORE"] = "1"
    if ref:
        env["SELF_ARCHIVE_REF"] = ref
    return subprocess.run([sys.executable or "python3", str(GUARD), mode],
                          cwd=str(repo), capture_output=True, text=True, env=env)


def fixture(active=(), archived=()) -> tuple[Path, Path]:
    """A real git repo with the given OpenSpec changes committed, plus a
    baseline file path OUTSIDE the repository."""
    repo = Path(tempfile.mkdtemp(prefix="sa-guard-repo."))
    for name in active:
        d = repo / "openspec" / "changes" / name
        d.mkdir(parents=True)
        (d / "proposal.md").write_text(f"# Proposal: {name}\n\nIssue: #1\n")
        (d / "tasks.md").write_text("- [x] done\n")
    for name in archived:
        d = repo / "openspec" / "changes" / "archive" / name
        d.mkdir(parents=True)
        (d / "proposal.md").write_text(f"# Proposal: {name} (merged)\n")
    (repo / "README.md").write_text("fixture\n")
    git(repo, "init", "-q", "-b", "main")
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", "fixture base")
    baseline = Path(tempfile.mkstemp(prefix="sa-guard-baseline.", text=True)[1])
    return repo, baseline


def test_snapshot_then_check_on_a_clean_tree_is_green():
    repo, baseline = fixture(active=("foo",), archived=("merged-old",))
    try:
        s = run_guard(repo, "snapshot", baseline)
        check("snapshot exits 0", s.returncode == 0, s.stderr)
        data = json.loads(baseline.read_text())
        check("snapshot records the active change", data["active"] == ["foo"], data)
        check("snapshot records the archive names", data["archive"] == ["merged-old"], data)
        c = run_guard(repo, "check", baseline)
        check("clean tree: check exits 0", c.returncode == 0, c.stdout + c.stderr)
        check("clean tree: says so", "no self-archive" in c.stdout, c.stdout)
    finally:
        shutil.rmtree(repo, ignore_errors=True)
        baseline.unlink(missing_ok=True)


def test_a_move_into_the_archive_is_reported_and_restored():
    repo, baseline = fixture(active=("foo",))
    try:
        run_guard(repo, "snapshot", baseline)
        (repo / "openspec" / "changes" / "archive").mkdir(exist_ok=True)
        shutil.move(str(repo / "openspec" / "changes" / "foo"),
                    str(repo / "openspec" / "changes" / "archive" / "foo"))
        c = run_guard(repo, "check", baseline)
        check("mid-run archive: check exits 1", c.returncode == 1, c.stdout)
        check("mid-run archive: names the change", "self-archive" in c.stdout and "foo" in c.stdout, c.stdout)

        r = run_guard(repo, "check", baseline, restore=True)
        check("restore run stays red (the round is reported)", r.returncode == 1, r.stdout)
        check("restore run says it restored", "restored" in r.stdout, r.stdout)
        foo = repo / "openspec" / "changes" / "foo"
        arch = repo / "openspec" / "changes" / "archive" / "foo"
        check("the change is back on disk", foo.is_dir() and (foo / "proposal.md").is_file(),
              sorted(str(p) for p in (repo / "openspec" / "changes").iterdir()))
        check("the fresh archive copy is gone", not arch.exists(), arch.exists())
        c2 = run_guard(repo, "check", baseline)
        check("after the restore the tree checks clean", c2.returncode == 0, c2.stdout)
    finally:
        shutil.rmtree(repo, ignore_errors=True)
        baseline.unlink(missing_ok=True)


def test_an_archive_already_at_the_baseline_is_not_a_dismantle():
    # The base merged an archive for another change BEFORE the loop's snapshot:
    # it is part of the baseline and must never be reported as a dismantle.
    repo, baseline = fixture(active=("foo",), archived=("base-archived",))
    try:
        s = run_guard(repo, "snapshot", baseline)
        check("snapshot sees the base-archived change", "base-archived" in json.loads(baseline.read_text())["archive"], s.stdout)
        c = run_guard(repo, "check", baseline)
        check("base-archived change is not reported", c.returncode == 0 and "base-archived" not in c.stdout, c.stdout)
    finally:
        shutil.rmtree(repo, ignore_errors=True)
        baseline.unlink(missing_ok=True)


def test_a_committed_mid_run_move_is_restored_and_the_index_restaged():
    repo, baseline = fixture(active=("foo",))
    try:
        run_guard(repo, "snapshot", baseline)
        # A round that commits its dismantling itself.
        (repo / "openspec" / "changes" / "archive").mkdir(exist_ok=True)
        shutil.move(str(repo / "openspec" / "changes" / "foo"),
                    str(repo / "openspec" / "changes" / "archive" / "foo"))
        git(repo, "add", "-A")
        git(repo, "commit", "-q", "-m", "round archived its own change")
        r = run_guard(repo, "check", baseline, restore=True)
        check("committed dismantle is still reported", r.returncode == 1, r.stdout)
        check("committed dismantle is restored",
              (repo / "openspec" / "changes" / "foo" / "tasks.md").is_file(), r.stdout)
        check("the committed archive copy is removed",
              not (repo / "openspec" / "changes" / "archive" / "foo").exists(), "")
        # The loop stages with `git add -A`; the guard must leave the INDEX matching
        # the repaired tree, not a half-moved one.
        staged = git(repo, "diff", "--cached", "--name-only").stdout.split()
        check("the index carries the restore (staged, not phantom-deleted)",
              any(p.startswith("openspec/changes/foo") for p in staged), staged)
        tracked_archived = git(repo, "ls-files", "openspec/changes/archive").stdout.split()
        check("the archive copy is staged out of the index", tracked_archived == [], tracked_archived)
    finally:
        shutil.rmtree(repo, ignore_errors=True)
        baseline.unlink(missing_ok=True)


def test_a_vanished_change_is_restored_from_the_reference():
    repo, baseline = fixture(active=("foo",))
    try:
        run_guard(repo, "snapshot", baseline)
        shutil.rmtree(repo / "openspec" / "changes" / "foo")
        c = run_guard(repo, "check", baseline)
        check("a deletion with no archive copy is a vanish", "vanish" in c.stdout and c.returncode == 1, c.stdout)
        r = run_guard(repo, "check", baseline, restore=True)
        check("vanish is restored from the reference commit",
              r.returncode == 1 and (repo / "openspec" / "changes" / "foo" / "proposal.md").is_file(),
              r.stdout)
    finally:
        shutil.rmtree(repo, ignore_errors=True)
        baseline.unlink(missing_ok=True)


def test_an_unrecoverable_loss_is_reported_loudly_not_silently():
    repo, baseline = fixture(active=("bar",))
    try:
        # An untracked (never committed) baseline-active change that is deleted
        # with no archive copy: nothing can restore it — the guard must say so.
        untracked = repo / "openspec" / "changes" / "fresh"
        untracked.mkdir(parents=True)
        (untracked / "proposal.md").write_text("# Proposal: fresh\n")
        run_guard(repo, "snapshot", baseline)
        check("the untracked change is in the baseline",
              "fresh" in json.loads(baseline.read_text())["active"], baseline.read_text())
        shutil.rmtree(untracked)
        r = run_guard(repo, "check", baseline, restore=True)
        check("unrecoverable loss exits 1", r.returncode == 1, r.stdout)
        check("unrecoverable loss names itself", "unrecoverable" in r.stdout, r.stdout)
    finally:
        shutil.rmtree(repo, ignore_errors=True)
        baseline.unlink(missing_ok=True)


def test_a_missing_baseline_is_a_loud_error():
    repo = Path(tempfile.mkdtemp(prefix="sa-guard-repo."))
    (repo / "README.md").write_text("fixture\n")
    git(repo, "init", "-q", "-b", "main")
    baseline = repo / "no-such-baseline.json"
    try:
        c = run_guard(repo, "check", baseline)
        check("no baseline: exit 2", c.returncode == 2, c.returncode)
        check("no baseline: names the remedy", "self-archive-snapshot" in c.stderr, c.stderr)
        s = run_guard(repo, "snapshot", baseline, )
        check("snapshot writes its baseline", baseline.is_file(), "")
        s2 = subprocess.run([sys.executable or "python3", str(GUARD), "snapshot"],
                            cwd=str(repo), capture_output=True, text=True,
                            env=dict(os.environ, SELF_ARCHIVE_BASELINE=""))
        check("snapshot with nowhere to write exits 2", s2.returncode == 2, s2.stderr)
    finally:
        shutil.rmtree(repo, ignore_errors=True)
        baseline.unlink(missing_ok=True)


def test_a_change_made_after_the_snapshot_is_this_runs_own_artifact():
    repo, baseline = fixture(active=("foo",))
    try:
        run_guard(repo, "snapshot", baseline)
        new = repo / "openspec" / "changes" / "made-by-this-run"
        new.mkdir(parents=True)
        (new / "proposal.md").write_text("# Proposal: made-by-this-run\n")
        git(repo, "add", "-A")
        git(repo, "commit", "-q", "-m", "this run's own new change")
        # A run may remove a scaffold IT created after the snapshot; it may not
        # delete history (baseline-active changes).
        shutil.rmtree(new)
        c = run_guard(repo, "check", baseline)
        check("post-snapshot changes are not guarded", c.returncode == 0, c.stdout)
    finally:
        shutil.rmtree(repo, ignore_errors=True)
        baseline.unlink(missing_ok=True)


def main() -> int:
    if not shutil.which("git"):
        print("SKIP: git not available")
        return 0
    print("self_archive_guard.py (issue #812)")
    test_snapshot_then_check_on_a_clean_tree_is_green()
    test_a_move_into_the_archive_is_reported_and_restored()
    test_an_archive_already_at_the_baseline_is_not_a_dismantle()
    test_a_committed_mid_run_move_is_restored_and_the_index_restaged()
    test_a_vanished_change_is_restored_from_the_reference()
    test_an_unrecoverable_loss_is_reported_loudly_not_silently()
    test_a_missing_baseline_is_a_loud_error()
    test_a_change_made_after_the_snapshot_is_this_runs_own_artifact()
    print(f"\nPASSED {_PASS} | FAILED {_FAIL}")
    return 1 if _FAIL else 0


if __name__ == "__main__":
    raise SystemExit(main())
