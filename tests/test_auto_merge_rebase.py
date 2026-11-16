#!/usr/bin/env python3
"""Auto-merge must land a MERGE-TIME-CURRENT OPENSPEC.md (issue #1049).

Measured: auto-merge squashes a PR head whose `OPENSPEC.md` was generated at
branch-cut time. When the merge wave archives the change the PR closed, the
squash tree's index lists an archived change as active, `openspec-index-check`
goes red on the master push, and a keeper PR cycle burns — keepers
#1038/#1045/#1046/#1047 ping-ponged; re-measured 2026-11-16: rebased bot
branches 45fb245/5df9735/28bf765/9a5830a went red at `openspec-index-check`
because their regenerated count lines predated later archives.

The fix seam is `scripts/auto_merge_rebase.py` (reached through
`make auto-merge-rebase`, run by qa-validate's `auto-merge` job BEFORE the
squash): a behind-and-clean bot-owned branch is rebased onto the fetched base,
the index is regenerated on the rebased tree through the tree's OWN generator,
and the branch is pushed with `--force-with-lease`; the squash step then SKIPS
(this run lands nothing; CI on the new head will). Every other shape — a
current head, a human-owned branch, a conflicting branch — is reported and
left byte-identical.

These tests plant REAL git fixtures (a bare origin + clones) and drive the
REAL script with a stub `gh` answering `pr view` (an external system: the
GitHub API is what the script talks to — rule 6m). No scripts/ symbol is
stubbed. The first check is the OLD behavior made visible: the merge-as-is
squash tree goes red at the real index gate.

Run:  python3 tests/test_auto_merge_rebase.py   or   make test
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
SCRIPT = ROOT / "scripts" / "auto_merge_rebase.py"
INDEX_GEN = ROOT / "scripts" / "openspec_index.py"
TASK_BOXES = ROOT / "scripts" / "task_boxes.py"
WORKFLOW = ROOT / ".github" / "workflows" / "qa-validate.yml"
MAKEFILE = ROOT / "Makefile"
PR_HEALTH = ROOT / "scripts" / "pr_health.py"
sys.path.insert(0, str(ROOT / "scripts"))

import yaml  # noqa: E402

_PASS = 0
_FAIL = 0

#: A stub `gh`: `pr view` answers from $FAKE_PR; every `gh` argv is recorded in
#: $GH_LOG so the request construction is asserted, and any other subcommand is
#: loud (the seam may only read the PR through `gh pr view`).
STUB_GH = """#!/bin/sh
echo "gh $*" >> "$GH_LOG"
case "$1 $2" in
  "pr view") cat "$FAKE_PR" ;;
  *) echo "unexpected gh: $*" >&2; exit 3 ;;
esac
"""

GIT_ENV = {**os.environ, "GIT_CONFIG_NOSYSTEM": "1", "GIT_TERMINAL_PROMPT": "0"}

HEAD_BRANCH = "ci/data-gap-77-x"
ARCHIVE_SLUG = "2026-11-16-alpha"


def check(name, cond, detail: object = ""):
    global _PASS, _FAIL
    if cond:
        _PASS += 1
        print(f"  ok  {name}")
    else:
        _FAIL += 1
        print(f"  FAIL {name}" + (f"  [{detail}]" if detail else ""))


def _git(cwd, *args) -> subprocess.CompletedProcess:
    return subprocess.run(["git", "-C", str(cwd), *args],
                          capture_output=True, text=True, env=GIT_ENV)


def _git_commit(cwd, msg) -> subprocess.CompletedProcess:
    _git(cwd, "add", "-A")
    r = _git(cwd, "-c", "user.name=Test Bot", "-c", "user.email=test-bot@example.com",
             "commit", "-q", "-m", msg)
    assert r.returncode == 0, r.stderr
    return r


def _must(cwd, *args):
    r = _git(cwd, *args)
    assert r.returncode == 0, f"git {' '.join(args)}: {r.stderr}"
    return r


def _write(path: Path, text: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)


# ---------------------------------------------------------------- fixtures --

CHANGE_FILES = {
    "openspec/changes/change-alpha/proposal.md": (
        "# Change Alpha\n\nIssue: #77\n\n## Why\n\nAn active change for the fixture.\n"
    ),
    "openspec/changes/change-alpha/tasks.md": "# Tasks\n\n- [x] land alpha\n",
    "openspec/changes/change-alpha/specs/cap/spec.md": (
        "# Cap spec\n\n## Requirement: Alpha\n\nAlpha is listed in the index.\n\n"
        "#### Scenario: Alpha lands\n\nGiven a repo\nWhen alpha lands\nThen it is listed\n"
        "- **Test:** tests/test_auto_merge_rebase.py::test_behind_clean_bot_branch_is_rebased_with_a_current_index\n"
    ),
}


def _run_generator(tree: Path, *flag) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(tree / "scripts" / "openspec_index.py"), *flag],
                          capture_output=True, text=True, cwd=str(tree), env=GIT_ENV)


def _seed(td: Path) -> tuple[str, Path]:
    """A bare origin + a seeded clone: scripts/ generator + a valid openspec/ tree +
    a generated OPENSPEC.md that is CURRENT for this tree."""
    origin = td / "origin.git"
    origin.mkdir(parents=True)
    _must(origin, "init", "--bare", "-q", ".")
    seed = td / "seed"
    _must(td, "clone", "-q", str(origin), "seed")
    _must(seed, "config", "user.name", "Test Bot")
    _must(seed, "config", "user.email", "test-bot@example.com")
    (seed / "scripts").mkdir()
    shutil.copy(INDEX_GEN, seed / "scripts" / "openspec_index.py")
    shutil.copy(TASK_BOXES, seed / "scripts" / "task_boxes.py")
    _write(seed / "base.txt", "base\n")
    for rel, text in CHANGE_FILES.items():
        _write(seed / rel, text)
    gen = _run_generator(seed, "--write")
    assert gen.returncode == 0, gen.stderr
    chk = _run_generator(seed, "--check")
    assert chk.returncode == 0, f"seed index must be green: {chk.stdout}{chk.stderr}"
    _must(seed, "add", "-A")
    _must(seed, "branch", "-M", "master")
    _git_commit(seed, "seed: tree with an active change and a current index")
    _must(seed, "push", "-q", "origin", "master")
    return str(origin), seed


def _fixture(td: Path, *, head: str = HEAD_BRANCH, move_master: bool = True,
             archive: bool = True, clash: bool = False, broken_generator: bool = False):
    """origin + a PR-head branch from the base + master moved on (by default: the
    change gets ARCHIVED on master — the exact merge-wave shape that reds the index)."""
    origin_url, seed = _seed(td)
    _must(seed, "checkout", "-q", "-b", head)
    if broken_generator:
        _write(seed / "scripts" / "openspec_index.py", "raise SystemExit(3)\n")
        _must(seed, "add", "-A")
        _git_commit(seed, "feat: PR commit touching the generator")
    elif clash:
        _write(seed / "base.txt", "branch-side\n")
        _git_commit(seed, "feat: the branch edits base.txt")
    else:
        _write(seed / "feature.txt", "feat\n")
        _git_commit(seed, "feat: the PR's own commit")
    _must(seed, "push", "-q", "origin", head)
    _must(seed, "checkout", "-q", "master")
    if move_master:
        if clash:
            _write(seed / "base.txt", "master-side\n")
            _git_commit(seed, "master edits the same line")
        elif archive:
            (seed / "openspec" / "changes" / "archive").mkdir(parents=True, exist_ok=True)
            _must(seed, "mv", "openspec/changes/change-alpha",
                  f"openspec/changes/archive/{ARCHIVE_SLUG}")
            _git_commit(seed, "archive: the change closed by the merge wave")
        else:
            _write(seed / "other.txt", "other\n")
            _git_commit(seed, "master moves")
        _must(seed, "push", "-q", "origin", "master")
    clone = td / "clone"
    _must(td, "clone", "-q", origin_url, "clone")
    return origin_url, seed, clone


def _pr_json(*, head: str = HEAD_BRANCH, state: str = "open", draft: bool = False,
             mergeable: str = "MERGEABLE", state_status: str = "BEHIND") -> dict:
    return {"repository": {"nameWithOwner": "o/r"}, "number": 77, "state": state,
            "isDraft": draft, "headRefName": head, "headRefOid": "f" * 40,
            "mergeable": mergeable, "mergeStateStatus": state_status}


def _run_seam(clone: Path, pr_obj: dict) -> tuple[subprocess.CompletedProcess, str]:
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        (td / "gh").write_text(STUB_GH)
        (td / "gh").chmod(0o755)
        (td / "pr.json").write_text(json.dumps(pr_obj))
        log = td / "gh.log"
        log.write_text("")
        env = {**GIT_ENV, "PATH": f"{td}:{os.environ['PATH']}",
               "FAKE_PR": str(td / "pr.json"), "GH_LOG": str(log)}
        proc = subprocess.run(
            [sys.executable, str(SCRIPT), "--pr", "77", "--repo", "o/r", "--dir", str(clone)],
            capture_output=True, text=True, env=env, cwd=str(clone))
        return proc, log.read_text()


def _head_oid(clone: Path, branch: str) -> str:
    return _git(clone, "rev-parse", f"refs/remotes/origin/{branch}").stdout.strip()


def _show(clone: Path, branch: str, path: str) -> str:
    r = _git(clone, "show", f"refs/remotes/origin/{branch}:{path}")
    assert r.returncode == 0, r.stderr
    return r.stdout


def _worktree_check(clone: Path, ref: str, td: Path, tag: str) -> int:
    """Add a worktree at `ref` and run the tree's OWN `openspec_index.py --check` on it."""
    wt = td / f"wt-{tag}"
    _must(clone, "worktree", "add", "--detach", str(wt), ref)
    try:
        return _run_generator(wt, "--check").returncode
    finally:
        _must(clone, "worktree", "remove", "--force", str(wt))


# ------------------------------------------------------------------ tests --

def test_behind_clean_bot_branch_is_rebased_with_a_current_index():
    """The core #1049 proof: the merge-as-is squash tree is RED at the index gate,
    and the seam lands a rebased head whose regenerated index is GREEN."""
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        _, _, clone = _fixture(td)
        old = _head_oid(clone, HEAD_BRANCH)

        # OLD behavior, made visible: the merge commit GitHub builds (squash tree)
        # carries the branch's stale OPENSPEC.md — the REAL index gate goes red on it.
        preview = td / "preview"
        _must(clone, "worktree", "add", "--detach", str(preview), f"refs/remotes/origin/{HEAD_BRANCH}")
        m = _git(preview, "-c", "user.name=Test Bot", "-c", "user.email=test-bot@example.com",
                 "merge", "-q", "--no-ff", "refs/remotes/origin/master", "-m", "preview squash tree")
        assert m.returncode == 0, m.stderr
        stale = _run_generator(preview, "--check")
        check("merge-as-is lands a stale index: openspec-index-check is RED on the squash tree",
              stale.returncode != 0, stale.stdout[-160:])
        _must(clone, "worktree", "remove", "--force", str(preview))
        check("the branch tip's committed index claims the active change",
              "Active changes: **1**" in _show(clone, HEAD_BRANCH, "OPENSPEC.md"))

        # NEW behavior: the seam.
        proc, ghlog = _run_seam(clone, _pr_json())
        check("seam: exit 0 (report-only semantics even when it lands work)",
              proc.returncode == 0, proc.stdout + proc.stderr)
        check("seam: verdict=rebased", "verdict=rebased" in proc.stdout, proc.stdout)
        check("seam: rebased=true (the squash if-gate input)", "rebased=true" in proc.stdout,
              proc.stdout)
        check("seam: it names the regenerated index", "regenerated on the rebased tree" in proc.stdout,
              proc.stdout)
        check("seam: this run lands nothing, honestly",
              "will NOT merge" in proc.stdout, proc.stdout)
        check("seam: the request construction names the PR and repo",
              "gh pr view 77 --repo o/r --json" in ghlog, ghlog)

        _must(clone, "fetch", "-q", "origin", f"refs/heads/{HEAD_BRANCH}:refs/remotes/origin/{HEAD_BRANCH}")
        new = _head_oid(clone, HEAD_BRANCH)
        check("seam: the remote branch MOVED (rebased + regen commit)", new != old, (old, new))
        check("seam: origin/master is an ancestor of the new head",
              _git(clone, "merge-base", "--is-ancestor", "refs/remotes/origin/master",
                   f"refs/remotes/origin/{HEAD_BRANCH}").returncode == 0)
        log = _git(clone, "log", "--format=%s", f"refs/remotes/origin/{HEAD_BRANCH}").stdout
        check("seam: the PR's own commit survives the rebase", "feat: the PR's own commit" in log, log)
        check("seam: the regeneration commit landed", "regenerate the index on the rebased tree" in log, log)
        new_index = _show(clone, HEAD_BRANCH, "OPENSPEC.md")
        check("seam: the new head's index lists the ARCHIVE, not an active change",
              ARCHIVE_SLUG in new_index and "Active changes: **0**" in new_index, new_index[:200])
        check("seam: openspec-index-check is GREEN on the rebased head",
              _worktree_check(clone, f"refs/remotes/origin/{HEAD_BRANCH}", td, "green") == 0)


def test_current_head_reports_current_and_pushes_nothing():
    """A head that already carries the fetched base is CURRENT: no rebase, no push —
    the merge path today is unchanged."""
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        _, _, clone = _fixture(td, move_master=False)
        old = _head_oid(clone, HEAD_BRANCH)
        proc, _ = _run_seam(clone, _pr_json(state_status="CLEAN"))
        check("current: exit 0", proc.returncode == 0, proc.stdout + proc.stderr)
        check("current: verdict=current", "verdict=current" in proc.stdout, proc.stdout)
        check("current: rebased=false (the squash runs as today)", "rebased=false" in proc.stdout,
              proc.stdout)
        check("current: nothing was pushed", _head_oid(clone, HEAD_BRANCH) == old)
        check("current: the merge path is stated unchanged",
              "already carries the fetched master" in proc.stdout, proc.stdout)


def test_human_owned_behind_branch_is_reported_and_untouched():
    """A human-owned behind branch is NEVER rewritten (rule 6s): reported only."""
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        _, _, clone = _fixture(td, head="andy/human-feature")
        old = _head_oid(clone, "andy/human-feature")
        proc, _ = _run_seam(clone, _pr_json(head="andy/human-feature"))
        check("human: exit 0", proc.returncode == 0, proc.stdout + proc.stderr)
        check("human: verdict=human-owned", "verdict=human-owned" in proc.stdout, proc.stdout)
        check("human: rebased=false", "rebased=false" in proc.stdout, proc.stdout)
        check("human: the remote branch is byte-identical",
              _head_oid(clone, "andy/human-feature") == old)
        check("human: the report names the rule", "human-owned" in proc.stdout, proc.stdout)


def test_conflicting_branches_are_never_rewritten():
    """GitHub-known conflicts stay out of the rebaser; a conflict that only the
    rebase discovers ABORTS and leaves the remote branch byte-identical."""
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        # Shape A: GitHub already says CONFLICTING — the seam never attempts it.
        _, _, clone_a = _fixture(td / "a")
        old_a = _head_oid(clone_a, HEAD_BRANCH)
        proc_a, _ = _run_seam(clone_a, _pr_json(mergeable="CONFLICTING", state_status="DIRTY"))
        check("conflict-known: verdict=conflicting", "verdict=conflicting" in proc_a.stdout,
              proc_a.stdout)
        check("conflict-known: rebased=false", "rebased=false" in proc_a.stdout, proc_a.stdout)
        check("conflict-known: the branch is untouched",
              _head_oid(clone_a, HEAD_BRANCH) == old_a)
        check("conflict-known: it says GitHub refuses the merge commit",
              "CONFLICTING" in proc_a.stdout, proc_a.stdout)

        # Shape B: GitHub says MERGEABLE/BEHIND but the rebase itself conflicts.
        _, _, clone_b = _fixture(td / "b", clash=True)
        old_b = _head_oid(clone_b, HEAD_BRANCH)
        before = _show(clone_b, HEAD_BRANCH, "base.txt")
        proc_b, _ = _run_seam(clone_b, _pr_json())
        check("conflict-found: exit 0 (report-only, never a red step)",
              proc_b.returncode == 0, proc_b.stdout + proc_b.stderr)
        check("conflict-found: rebased=false", "rebased=false" in proc_b.stdout, proc_b.stdout)
        check("conflict-found: honest report — rebase aborted, branch untouched",
              "branch left untouched" in proc_b.stdout and "conflicted" in proc_b.stdout,
              proc_b.stdout)
        _must(clone_b, "fetch", "-q", "origin", f"+refs/heads/{HEAD_BRANCH}:refs/remotes/origin/{HEAD_BRANCH}")
        check("conflict-found: the remote branch is byte-identical",
              _head_oid(clone_b, HEAD_BRANCH) == old_b)
        check("conflict-found: the branch's own content survived",
              _show(clone_b, HEAD_BRANCH, "base.txt") == before)
        dirty = _git(clone_b, "status", "--porcelain").stdout.strip()
        check("conflict-found: the checkout stays clean", dirty == "", dirty)
        check("conflict-found: no rebase left half-applied in the checkout",
              not (clone_b / ".git" / "rebase-merge").exists()
              and not (clone_b / ".git" / "rebase-apply").exists())


def test_regeneration_failure_keeps_the_branch_untouched():
    """If the index regeneration fails on the rebased tree, NOTHING is pushed:
    the lease push never runs and the remote branch stays byte-identical."""
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        _, _, clone = _fixture(td, broken_generator=True)
        old = _head_oid(clone, HEAD_BRANCH)
        proc, _ = _run_seam(clone, _pr_json())
        check("regen-fail: exit 0 (report-only)", proc.returncode == 0, proc.stdout + proc.stderr)
        check("regen-fail: rebased=false", "rebased=false" in proc.stdout, proc.stdout)
        check("regen-fail: names the failed regeneration", "regeneration failed" in proc.stdout,
              proc.stdout)
        check("regen-fail: the branch was left untouched", "branch left untouched" in proc.stdout,
              proc.stdout)
        _must(clone, "fetch", "-q", "origin", f"refs/heads/{HEAD_BRANCH}:refs/remotes/origin/{HEAD_BRANCH}")
        check("regen-fail: the remote branch never moved", _head_oid(clone, HEAD_BRANCH) == old)


def test_the_auto_merge_wiring_refuses_the_merge_as_is_flow():
    """The job wiring is pinned: the rebase step runs BEFORE the squash, and the
    squash's `if:` refuses the merge when the seam rebased the head. The
    merge-as-is shape (no seam / the old `if:`) — what origin/master carried
    before #1049 — goes RED."""

    def job_steps(text: str) -> list[dict]:
        return yaml.safe_load(text)["jobs"]["auto-merge"]["steps"]

    def wiring_problems(steps: list[dict]) -> list[str]:
        names = [s.get("name") or "" for s in steps]
        rebase_at = next((i for i, n in enumerate(names)
                          if "Rebase a behind-and-clean bot branch" in n), -1)
        squash_at = next((i for i, n in enumerate(names) if "Squash-merge" in n), -1)
        problems: list[str] = []
        if rebase_at < 0:
            problems.append("auto-merge: no rebase-before-squash step (merge-as-is)")
        if squash_at >= 0 and 0 <= rebase_at >= squash_at:
            problems.append("auto-merge: the rebase step is not BEFORE the squash step")
        if rebase_at >= 0:
            run = steps[rebase_at].get("run", "")
            if "make auto-merge-rebase" not in run:
                problems.append("auto-merge: the rebase step reaches the script past the Makefile")
            if "rebased=" not in run:
                problems.append("auto-merge: the rebase step publishes no rebased= output")
        if squash_at >= 0:
            gate = str(steps[squash_at].get("if", ""))
            if "steps.auto-merge-rebase.outputs.rebased != 'true'" not in gate:
                problems.append("auto-merge: the squash merges a head the seam rebased (stale squash tree)")
            if "steps.dnm-check.outputs.hold != 'true'" not in gate:
                problems.append("auto-merge: the squash lost the do-not-merge gate")
        return problems

    shipped = wiring_problems(job_steps(WORKFLOW.read_text()))
    check("wiring: the shipped auto-merge job carries the pre-squash rebase seam",
          shipped == [], shipped)

    # The planted old flow: strip the seam, restore the pre-#1044-era squash if-gate.
    doc = yaml.safe_load(WORKFLOW.read_text())
    job = doc["jobs"]["auto-merge"]
    job["steps"] = [s for s in job["steps"]
                    if "Rebase a behind-and-clean bot branch" not in (s.get("name") or "")]
    for s in job["steps"]:
        if "Squash-merge" in (s.get("name") or ""):
            s["if"] = "steps.dnm-check.outputs.hold != 'true'"
    planted = wiring_problems(job["steps"])
    check("wiring: the merge-as-is job is refused (no seam + the old if-gate)",
          any("merge-as-is" in p for p in planted)
          and any("rebased" in p for p in planted), planted)

    # The guard is RED on the pre-change workflow (rule 6c).
    base = subprocess.run(["git", "-C", str(ROOT), "show", "origin/master:.github/workflows/qa-validate.yml"],
                          capture_output=True, text=True)
    if base.returncode == 0:
        problems = wiring_problems(job_steps(base.stdout))
        if "auto-merge-rebase" not in base.stdout:
            check("wiring: origin/master's merge-as-is job is refused by this guard",
                  bool(problems), problems)
        else:
            check("wiring: origin/master already carries the seam", problems == [], problems)

    # The seam is ONE verdict seam: the Makefile target exists, and the script
    # shares the sweep's rebaser (where the regeneration lives), pushing with a
    # lease pinned to the fetched remote tip (rule 6s).
    check("wiring: `make auto-merge-rebase` is defined in the Makefile",
          "auto-merge-rebase:" in MAKEFILE.read_text())
    seam_src = SCRIPT.read_text()
    check("wiring: the seam reuses pr_health's ONE rebaser (no second git flow)",
          "from pr_health import" in seam_src and "rebase_and_push" in seam_src, seam_src[:120])
    ph_src = PR_HEALTH.read_text()
    check("wiring: the shared rebaser pushes with --force-with-lease pinned to the fetched tip",
          "--force-with-lease=refs/heads/" in ph_src, ph_src[:120])


def test_classification_is_pure_and_partitions():
    """The verdict seam is a pure function: every PR shape lands on exactly one
    partition, and the git facts are inputs (rule 6d)."""
    import auto_merge_rebase as AMR

    def cls(*, head="ci/x", state="open", draft=False, mergeable="MERGEABLE",
            status="BEHIND", behind: bool | None = True):
        pr = {"repository": {"nameWithOwner": "o/r"}, "number": 1, "state": state,
              "isDraft": draft, "headRefName": head, "headRefOid": "b" * 40,
              "mergeable": mergeable, "mergeStateStatus": status}
        return AMR.classify(pr, behind)

    check("classify: a closed PR is not-open", cls(state="closed") == "not-open")
    check("classify: a draft is draft-only", cls(draft=True) == "draft")
    check("classify: GitHub-known CONFLICTING is conflicting",
          cls(mergeable="CONFLICTING", status="DIRTY") == "conflicting")
    check("classify: a human-owned branch is human-owned (never rewritten)",
          cls(head="andy/feature") == "human-owned")
    check("classify: a repo-owned prefix branch is human-owned", cls(head="o/feature") == "human-owned")
    check("classify: a head that is not behind is current", cls(behind=False) == "current")
    check("classify: unreadable git facts are reported, never guessed",
          cls(behind=None) == "refs-unreadable")
    check("classify: behind + bot prefix + clean mergeable is behind-and-clean-bot",
          cls() == "behind-and-clean-bot")
    check("classify: UNKNOWN mergeable still rebases safely (conflict abort keeps it honest)",
          cls(status="UNKNOWN") == "behind-and-clean-bot")


def main():
    tests = [
        test_behind_clean_bot_branch_is_rebased_with_a_current_index,
        test_current_head_reports_current_and_pushes_nothing,
        test_human_owned_behind_branch_is_reported_and_untouched,
        test_conflicting_branches_are_never_rewritten,
        test_regeneration_failure_keeps_the_branch_untouched,
        test_the_auto_merge_wiring_refuses_the_merge_as_is_flow,
        test_classification_is_pure_and_partitions,
    ]
    for t in tests:
        print(f"\n[{t.__name__}]")
        t()
    print(f"\n{os.path.basename(__file__)}: {_PASS} passed, {_FAIL} failed")
    return 1 if _FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
