#!/usr/bin/env python3
"""A refresh is published on the base as it is NOW, never on a stale one (issue #177).

A refresh PR is entirely GENERATED files — `data/models.json`, `README.md`,
`data/snapshots/*`, `data/gap_baseline.json` — that every other merge rewrites. PR #164
was rebased twice inside one hour (conflicts on `README.md`, `data/models.json`,
`data/gap_baseline.json`), and the second run's `auto-merge` had already failed with
`GraphQL: Pull Request has merge conflicts` while `validate` and `live-smoke` were green.
`refresh-bot` advances its clean checkout when `aggregate` starts (#448), but the search
legs ran before it and the merge/commit run after it, so `master` still moves under the
tree before the PR exists.

Every case below drives the REAL `scripts/refresh_base.py` against REAL git repositories
in a temp dir (a local file remote is the external system, never a stand-in):

  1. `sync` moves the generated tree onto the fetched tip, KEEPS the refresh's raw
     snapshots and the gap baseline, and reports the oldest snapshot's stamp so the
     caller can re-ingest exactly this run's data;
  2. `sync` is a no-op when the tree already is the fetched tip;
  3. `sync` refuses a dirty path a refresh does not generate, and a HEAD with commits of
     its own (it must never discard somebody's edit);
  4. `require-tip` FAILS on a branch behind the fetched base — the guard that stops a
     queued refresh from opening a PR `master` has already left — and passes after a
     sync;
  5. the two decisions are the Makefile seam `refresh-bot` calls, in the right order,
     before the push and before the PR.

Run standalone: python3 tests/test_refresh_base.py   or   make test
"""
from __future__ import annotations

import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from wiring import wired  # noqa: E402  (issues #176/#192)

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "scripts" / "refresh_base.py"
MAKEFILE = (ROOT / "Makefile").read_text(encoding="utf-8")
REFRESH_BOT = (ROOT / ".github" / "workflows" / "refresh-bot.yml").read_text(encoding="utf-8")

_PASS = 0
_FAIL = 0


def check(name: str, cond: bool, detail: object = "") -> None:
    global _PASS, _FAIL
    if cond:
        _PASS += 1
        print(f"  ok  {name}")
    else:
        _FAIL += 1
        print(f"FAIL {name}  {detail}")


def git(args: list[str], cwd: Path) -> subprocess.CompletedProcess:
    """The real git. `-c user.*` so a bare runner needs no global identity."""
    return subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@t",
                           "-c", "init.defaultBranch=master", *args],
                          cwd=str(cwd), capture_output=True, text=True)


def run_script(mode: str, cwd: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(SCRIPT), mode, *args],
                          cwd=str(cwd), capture_output=True, text=True)


def fixture(tmp: Path) -> dict:
    """A bare remote whose `master` carries the GENERATED files a refresh rewrites,
    plus a single-ref clone (`ref: master`, the shape `actions/checkout@v4` leaves)."""
    tmp.mkdir(parents=True, exist_ok=True)
    remote, seed, ci = tmp / "remote.git", tmp / "seed", tmp / "ci"
    git(["init", "-q", "--bare", str(remote)], tmp)
    git(["clone", "-q", str(remote), str(seed)], tmp)
    (seed / "data" / "raw").mkdir(parents=True)
    (seed / "data" / "snapshots").mkdir(parents=True)
    (seed / "README.md").write_text("# trending\n\nas of 2026-10-21T00:00:00Z\n")
    (seed / "data" / "models.json").write_text('{"models": ["a"]}\n')
    (seed / "data" / "gap_baseline.json").write_text('{"signature": "base"}\n')
    git(["add", "-A"], seed)
    git(["commit", "-qm", "base"], seed)
    git(["branch", "-m", "master"], seed)
    git(["push", "-q", "origin", "master"], seed)
    git(["clone", "-q", "--single-branch", "--branch", "master", str(remote), str(ci)], tmp)
    return {"remote": remote, "seed": seed, "ci": ci}


def advance(seed: Path, text: str) -> None:
    """Move the remote's master on — a merge that landed while the refresh searched."""
    (seed / "README.md").write_text((seed / "README.md").read_text() + text)
    (seed / "data" / "models.json").write_text('{"models": ["a", "b"]}\n')
    git(["commit", "-qam", text], seed)
    git(["push", "-q", "origin", "master"], seed)


def dirty_refresh_tree(ci: Path) -> Path:
    """What the aggregate's merge leaves behind on a base that has since moved."""
    (ci / "README.md").write_text("# trending (this run)\n")
    (ci / "data" / "models.json").write_text('{"models": ["a", "this-run"]}\n')
    (ci / "data" / "gap_baseline.json").write_text('{"signature": "this-run"}\n')
    raw = ci / "data" / "raw" / "cpu-20261021-120000.json"
    raw.parent.mkdir(parents=True, exist_ok=True)
    raw.write_text('{"backend": "cpu"}\n')
    # `make engine-meta-capture` (run before the commit step) records what it read
    # from GitHub for a newly registered engine — a reset must not drop it.
    meta = ci / "tests" / "fixtures" / "github_meta.json"
    meta.parent.mkdir(parents=True, exist_ok=True)
    meta.write_text('{"new-engine": {"full_name": "o/new-engine"}}\n')
    return raw


def test_sync_moves_the_generated_tree_onto_the_fetched_base(tmp: Path) -> None:
    fx = fixture(tmp)
    ci, seed = fx["ci"], fx["seed"]
    advance(seed, "merged while the legs searched\n")
    raw = dirty_refresh_tree(ci)
    proc = run_script("sync", ci)
    tip = git(["rev-parse", "origin/master"], ci).stdout.strip()
    check("sync: a tree behind the fetched base exits 0 after moving onto it",
          proc.returncode == 0, proc.stderr)
    check("sync: HEAD is the fetched tip (the base it reports)",
          git(["rev-parse", "HEAD"], ci).stdout.strip() == tip, proc.stdout)
    check("sync: it reports sync=reset and the base it reached",
          "sync=reset" in proc.stdout and f"base_sha={tip}" in proc.stdout, proc.stdout)
    check("sync: the generated README is the BASE's, re-derived not applied",
          (ci / "README.md").read_text() == "# trending\n\nas of 2026-10-21T00:00:00Z\n"
          + "merged while the legs searched\n", (ci / "README.md").read_text())
    check("sync: the refresh's raw snapshot SURVIVES the reset (the data is the input)",
          raw.exists() and raw.read_text() == '{"backend": "cpu"}\n', raw)
    check("sync: the gap baseline survives too (losing it re-files the same issue)",
          (ci / "data" / "gap_baseline.json").read_text() == '{"signature": "this-run"}\n',
          (ci / "data" / "gap_baseline.json").read_text())
    check("sync: the engine-metadata fixture survives (or the PR's `make test` goes red)",
          (ci / "tests" / "fixtures" / "github_meta.json").read_text()
          == '{"new-engine": {"full_name": "o/new-engine"}}\n',
          (ci / "tests" / "fixtures" / "github_meta.json").read_text())
    check("sync: it names the oldest snapshot so the caller re-ingests THIS run's data",
          "raw_floor=2026-10-21T12:00:00Z" in proc.stdout, proc.stdout)


def test_sync_is_a_no_op_on_the_fetched_tip(tmp: Path) -> None:
    fx = fixture(tmp)
    proc = run_script("sync", fx["ci"])
    check("sync: a tree already on the fetched tip is a green no-op",
          proc.returncode == 0 and "sync=current" in proc.stdout, proc.stdout)


def test_sync_refuses_a_dirty_path_a_refresh_does_not_generate(tmp: Path) -> None:
    fx = fixture(tmp)
    ci, seed = fx["ci"], fx["seed"]
    (ci / "scripts").mkdir()
    (ci / "scripts" / "some_guard.py").write_text("# a real edit\n")
    advance(seed, "moved\n")
    proc = run_script("sync", ci)
    check("sync: a non-generated dirty path is REFUSED (never silently reset)",
          proc.returncode == 1 and "REFUSED" in proc.stderr, (proc.returncode, proc.stderr))
    check("sync: it names the path it would have discarded",
          "scripts/some_guard.py" in proc.stderr, proc.stderr)
    check("sync: the refused edit is still in the tree",
          (ci / "scripts" / "some_guard.py").read_text() == "# a real edit\n", "")


def test_sync_refuses_a_head_with_its_own_commits(tmp: Path) -> None:
    fx = fixture(tmp)
    ci, seed = fx["ci"], fx["seed"]
    (ci / "README.md").write_text("# a committed branch\n")
    git(["commit", "-qam", "work"], ci)
    advance(seed, "moved\n")
    proc = run_script("sync", ci)
    check("sync: a HEAD carrying commits is REFUSED, not reset away",
          proc.returncode == 1 and "make base-rebase" in proc.stderr,
          (proc.returncode, proc.stderr))


def test_require_tip_fails_on_a_branch_behind_the_fetched_base(tmp: Path) -> None:
    fx = fixture(tmp)
    ci, seed = fx["ci"], fx["seed"]
    dirty_refresh_tree(ci)
    git(["checkout", "-qb", "ci/trending-refresh-1"], ci)
    git(["add", "-A"], ci)
    git(["commit", "-qm", "chore: refresh"], ci)
    advance(seed, "merged after this branch was cut\n")
    proc = run_script("require-tip", ci)
    check("require-tip: a branch behind the fetched base exits 1 (no PR from a stale base)",
          proc.returncode == 1, proc.stdout)
    check("require-tip: it says STALE and how far behind",
          "STALE" in proc.stderr and "behind_base=1" in proc.stdout, (proc.stdout, proc.stderr))
    check("require-tip: it names the repair (sync + re-derive), not a hand merge",
          "make refresh-sync && make merge" in proc.stderr, proc.stderr)


def test_require_tip_passes_after_the_tree_is_synced(tmp: Path) -> None:
    fx = fixture(tmp)
    ci, seed = fx["ci"], fx["seed"]
    advance(seed, "moved\n")
    dirty_refresh_tree(ci)
    sync = run_script("sync", ci)
    git(["checkout", "-qb", "ci/trending-refresh-2"], ci)
    git(["add", "-A"], ci)
    git(["commit", "-qm", "chore: refresh"], ci)
    proc = run_script("require-tip", ci)
    check("require-tip: after a sync the branch contains the fetched tip (exit 0)",
          sync.returncode == 0 and proc.returncode == 0, (sync.stderr, proc.stderr))
    check("require-tip: it reports the proof, machine-readably",
          "behind_base=0" in proc.stdout and "published_on_base=true" in proc.stdout, proc.stdout)


def test_require_tip_is_loud_when_the_base_cannot_be_fetched(tmp: Path) -> None:
    fx = fixture(tmp)
    proc = run_script("require-tip", fx["ci"], "--remote", "nosuchremote")
    check("require-tip: an unfetchable base FAILS (a stale base never passes for fresh)",
          proc.returncode == 1 and "REFUSED" in proc.stderr, (proc.returncode, proc.stderr))


def test_the_seam_is_wired_to_the_makefile_and_the_pipeline() -> None:
    targets = set(re.findall(r"^([A-Za-z0-9_][A-Za-z0-9_.-]*):", MAKEFILE, re.M))
    for target, mode in (("refresh-sync", "sync"), ("refresh-require-tip", "require-tip")):
        check(f"Makefile: `{target}` exists (the seam CI and a human share)",
              target in targets, sorted(t for t in targets if t.startswith("refresh-")))
        recipe = re.search(rf"^{re.escape(target)}:.*\n((?:\t.*\n)+)", MAKEFILE, re.M)
        check(f"Makefile: `{target}` calls scripts/refresh_base.py {mode}",
              bool(recipe) and f"refresh_base.py {mode}" in recipe.group(1), "")
    check("Makefile: `merge` forwards SINCE so a re-derivation can re-ingest this run's raws",
          'make _merge SINCE="$(SINCE)"' in MAKEFILE
          and '--since "$(SINCE)"' in MAKEFILE, "")
    check("Makefile: the test is in the `_test` chain (rule 6d — a guard nothing runs)",
          wired(__file__), "")

    # The pipeline: sync + re-derive BEFORE the branch is cut, and the guard BEFORE the
    # push/PR — a queued refresh cannot open a PR against a base it has already left.
    step = REFRESH_BOT[REFRESH_BOT.find("name: Commit + open PR if changed"):]
    check("refresh-bot: the commit step syncs the generated tree onto the fetched base",
          "make refresh-sync" in step, step[:400])
    check("refresh-bot: the container's root-owned generated files are chowned before the reset",
          0 <= step.find('sudo chown -R "$(id -u):$(id -g)" .') < step.find("make refresh-sync"), "")
    check("refresh-bot: the sync happens BEFORE the branch is cut",
          0 <= step.find("make refresh-sync") < step.find('git checkout -b "$BRANCH"'), "")
    check("refresh-bot: the merge is re-run on the synced base, bounded by this run's raws",
          0 <= step.find("make refresh-sync") < step.find("make merge SINCE="), "")
    check("refresh-bot: the re-derived tree is re-checked before it is published",
          0 <= step.find("make merge SINCE=") < step.find("make qa-report"), "")
    check("refresh-bot: the branch is proven to contain the fetched base BEFORE the push",
          0 <= step.find("make refresh-require-tip") < step.find('git push origin "$BRANCH"'),
          "")
    check("refresh-bot: and before the PR is opened",
          0 <= step.find("make refresh-require-tip") < step.find("gh pr create"), "")
    check("refresh-bot: a re-derivation that changed nothing opens no PR",
          "No data changes after the base sync" in step, "")

    # NOTE: the AGENTS.md §6b/§8 rows for this behaviour are tracked on their own issue —
    # AGENTS.md is a protected file in the implementation environment (rule 6g finding).
    check("the seam is reachable from the pipeline, not only from a human's terminal",
          "make refresh-sync" in step and "make refresh-require-tip" in step, "")


def main() -> int:
    print("a refresh is published on the base as it is NOW (issue #177)")
    tmp = Path(tempfile.mkdtemp(prefix="refresh-base-"))
    try:
        test_sync_moves_the_generated_tree_onto_the_fetched_base(tmp / "c1")
        test_sync_is_a_no_op_on_the_fetched_tip(tmp / "c2")
        test_sync_refuses_a_dirty_path_a_refresh_does_not_generate(tmp / "c3")
        test_sync_refuses_a_head_with_its_own_commits(tmp / "c4")
        test_require_tip_fails_on_a_branch_behind_the_fetched_base(tmp / "c5")
        test_require_tip_passes_after_the_tree_is_synced(tmp / "c6")
        test_require_tip_is_loud_when_the_base_cannot_be_fetched(tmp / "c7")
        test_the_seam_is_wired_to_the_makefile_and_the_pipeline()
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print(f"\nPASSED {_PASS} | FAILED {_FAIL}")
    return 1 if _FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
