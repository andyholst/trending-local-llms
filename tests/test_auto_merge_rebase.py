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


def _run_seam(clone: Path, pr_obj: dict, extra_env: dict | None = None) -> tuple[subprocess.CompletedProcess, str]:
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        (td / "gh").write_text(STUB_GH)
        (td / "gh").chmod(0o755)
        (td / "pr.json").write_text(json.dumps(pr_obj))
        log = td / "gh.log"
        log.write_text("")
        env = {**GIT_ENV, "PATH": f"{td}:{os.environ['PATH']}",
               "FAKE_PR": str(td / "pr.json"), "GH_LOG": str(log)}
        env.update(extra_env or {})
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
    """The core #1049 proof: the merge-as-is squash tree carries a small index
    drift, and the seam lands a rebased head whose regenerated index is GREEN.

    Issue #1415 changed what "small" means: at or under MAX_OPENSPEC_INDEX_DRIFT
    differing changes the gate now WARNs and exits 0 instead of reddening on every
    merge, so the squash tree is no longer RED here — it is named and tolerated.
    The seam's rebase + regeneration below is unchanged.
    """
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        _, _, clone = _fixture(td)
        old = _head_oid(clone, HEAD_BRANCH)

        # The merge commit GitHub builds (squash tree) carries the branch's stale
        # OPENSPEC.md: the archived change has no matching row and the count moved.
        preview = td / "preview"
        _must(clone, "worktree", "add", "--detach", str(preview), f"refs/remotes/origin/{HEAD_BRANCH}")
        m = _git(preview, "-c", "user.name=Test Bot", "-c", "user.email=test-bot@example.com",
                 "merge", "-q", "--no-ff", "refs/remotes/origin/master", "-m", "preview squash tree")
        assert m.returncode == 0, m.stderr
        stale = _run_generator(preview, "--check")
        check("merge-as-is lands a SMALL tolerated drift: openspec-index-check WARNs, exit 0",
              stale.returncode == 0 and "WARN" in stale.stdout + stale.stderr,
              stale.stdout[-160:] + stale.stderr[-160:])
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
            status="BEHIND", behind: bool | None = True, author=None):
        pr = {"repository": {"nameWithOwner": "o/r"}, "number": 1, "state": state,
              "isDraft": draft, "headRefName": head, "headRefOid": "b" * 40,
              "mergeable": mergeable, "mergeStateStatus": status}
        if author is not None:
            pr["author"] = author
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
    bot = {"login": "asimov-agent", "is_bot": True}
    human = {"login": "andyholst", "is_bot": False}
    check("classify (#1295): bot-authored fix/feat/rule is behind-and-clean-bot",
          cls(head="fix/agent", author=bot) == "behind-and-clean-bot"
          and cls(head="feat/agent", author=bot) == "behind-and-clean-bot"
          and cls(head="rule/agent", author=bot) == "behind-and-clean-bot")
    check("classify (#1295): human-authored ci/tech-debt- is report-only",
          cls(head="ci/human", author=human) == "human-owned"
          and cls(head="tech-debt-human", author=human) == "human-owned")
    check("classify (#1295): PR_FIELDS requests author for the live merge gate",
          "author" in AMR.PR_FIELDS.split(","))


#: (issue #1115) a stub `gh` for the ghost-run alarm: `run list` answers from $FAKE_RUNS,
#: `run view <id>` answers from $FAKE_JOBS_DIR/<id>.json; a `run list` that fails ($GH_FAIL=1)
#: stands for a broken GitHub read. Every argv is recorded so the request construction is pinned.
#: (issue #1158) every `--json` REQUEST is validated through the REAL field contract
#: (scripts/gh_json_fields.py): the stub can no longer answer a query the real gh would refuse,
#: which is exactly how `htmlUrl` stayed green for the whole life of the alarm.
STUB_GH_RUNS = """#!/bin/sh
echo "gh $*" >> "$GH_LOG"
if [ -n "$GH_FAIL" ]; then echo "gh: could not read runs" >&2; exit 1; fi
for arg in "$@"; do
  case "$prev" in
    --json) "$PYTHON" "$GH_FIELD_CONTRACT" --check-argv "gh $*" >/dev/null || {
      echo "Unknown JSON field: $arg (stub gh refuses what the real gh refuses)" >&2
      exit 1
    } ;;
  esac
  prev="$arg"
done
case "$1 $2" in
  "run list") cat "$FAKE_RUNS" ;;
  "run view") cat "$FAKE_JOBS_DIR/$3.json" ;;
  *) echo "unexpected gh: $*" >&2; exit 3 ;;
esac
"""


GHOST_GH_LOGS: list[str] = []


def _run_ghost_alarm(runs: list[dict], jobs: dict, *, window_hours: int | None = None,
                     fail: bool = False) -> subprocess.CompletedProcess:
    """Drive the REAL scripts/ghost_run_alarm.py against the stub gh (external system only,
    rule 6m): planted run-list and per-run jobs payloads, no scripts/ symbol stubbed."""
    import datetime as dtm
    now = dtm.datetime.now(dtm.timezone.utc)

    def ts(hours_ago: int) -> str:
        return (now - dtm.timedelta(hours=hours_ago)).strftime("%Y-%m-%dT%H:%M:%SZ")

    for i, r in enumerate(runs):
        r.setdefault("workflowName", "qa-validate.yml")
        r.setdefault("name", "qa-validate")
        r.setdefault("createdAt", ts(1 + i))
        r.setdefault("url", f"https://github.com/o/r/actions/runs/{r['databaseId']}")
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        (td / "gh").write_text(STUB_GH_RUNS)
        (td / "gh").chmod(0o755)
        (td / "runs.json").write_text(json.dumps(runs))
        jobs_dir = td / "jobs"
        jobs_dir.mkdir()
        for rid, payload in jobs.items():
            (jobs_dir / f"{rid}.json").write_text(json.dumps(payload))
        env = {**GIT_ENV, "PATH": f"{td}:{os.environ['PATH']}",
               "FAKE_RUNS": str(td / "runs.json"), "FAKE_JOBS_DIR": str(jobs_dir),
               "GH_LOG": str(td / "gh.log"),
               # (issue #1158) the stub validates each --json request through the real seam.
               "PYTHON": sys.executable,
               "GH_FIELD_CONTRACT": str(ROOT / "scripts" / "gh_json_fields.py")}
        if fail:
            env["GH_FAIL"] = "1"
        cmd = [sys.executable, str(ROOT / "scripts" / "ghost_run_alarm.py"), "--repo", "o/r"]
        if window_hours is not None:
            cmd += ["--window-hours", str(window_hours)]
        proc = subprocess.run(cmd, capture_output=True, text=True, env=env)
        # (issue #1158) the argv the alarm ACTUALLY built is part of the evidence: every stub
        # call from this run is appended for the test to read (the temp dir is gone by then).
        try:
            GHOST_GH_LOGS.append((td / "gh.log").read_text())
        except OSError:
            GHOST_GH_LOGS.append("")
        return proc


def test_rebase_push_carries_the_owner_pat_identity_when_the_step_provides_it():
    """(issue #1115) The measured ghost runs followed a rebase push done under the job-token
    checkout credential: the PR's next `pull_request` runs arrived `action_required` with ZERO
    jobs. When the CI step provides GIT_PUSH_PAT, the shared rebaser pushes the github.com
    origin through the owner-PAT URL. The fixture clone's origin is re-pointed at a github-shaped
    URL and git's OWN `insteadOf` transport maps both URLs back to the local bare repo (rule 6m:
    the real git, a real remote — the network is what is stood in for)."""
    import pr_health as PH

    check("pat_push_url: a github.com https origin is rewritten with the PAT identity",
          PH.pat_push_url("https://github.com/o/r.git", "TESTPAT")
          == "https://oauth2:TESTPAT@github.com/o/r.git", "")
    check("pat_push_url: no PAT, no rewrite", PH.pat_push_url("https://github.com/o/r.git", "") is None, "")
    check("pat_push_url: a non-github origin is NEVER rewritten (fixture remotes stay honest)",
          PH.pat_push_url("https://example.com/o/r.git", "TESTPAT") is None, "")
    check("pat_push_url: an ssh origin is never rewritten",
          PH.pat_push_url("git@github.com:o/r.git", "TESTPAT") is None, "")

    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        origin_url, _seed, clone = _fixture(td)
        before = _git(origin_url, "rev-parse", f"refs/heads/{HEAD_BRANCH}").stdout.strip()
        gh_url = "https://github.com/o/r.git"
        _must(clone, "remote", "set-url", "origin", gh_url)
        _must(clone, "config", f"url.{origin_url}.insteadOf", gh_url)
        _must(clone, "config", "--add", f"url.{origin_url}.insteadOf",
              "https://oauth2:TESTPAT@github.com/o/r.git")
        proc, _log = _run_seam(clone, _pr_json(), extra_env={"GIT_PUSH_PAT": "TESTPAT"})
        out = proc.stdout + proc.stderr
        check("seam with GIT_PUSH_PAT lands the rebase and names the owner-pat push identity",
              proc.returncode == 0 and "push identity: owner-pat" in out, out[:240])
        check("rule 3d: the PAT value itself never reaches the printed output",
              "TESTPAT" not in out, out[:240])
        after = _git(origin_url, "rev-parse", f"refs/heads/{HEAD_BRANCH}").stdout.strip()
        check("the PAT-authenticated push LANDED: the origin branch moved",
              after and after != before, f"{before} -> {after}")
        anc = _git(origin_url, "merge-base", "--is-ancestor", "master", f"refs/heads/{HEAD_BRANCH}")
        check("the landed head carries the fetched master (a real rebase, not a stale push)",
              anc.returncode == 0, anc.stderr[:200])

        # Without GIT_PUSH_PAT the push stays on `origin` (host sweeps, local fixture remotes):
        # the identity line says checkout-credential and nothing is rewritten.
        with tempfile.TemporaryDirectory() as td2:
            origin_url2, _seed2, clone2 = _fixture(Path(td2), head="ci/data-gap-78-x")
            proc2, _log2 = _run_seam(clone2, _pr_json(head="ci/data-gap-78-x"))
            check("seam without GIT_PUSH_PAT still rebases and pushes via origin (checkout identity)",
                  proc2.returncode == 0 and "push identity: checkout-credential" in proc2.stdout,
                  (proc2.stdout + proc2.stderr)[:240])


def test_ghost_alarm_flags_completed_pr_runs_with_zero_jobs():
    """The planted ghost shapes (issue #1115): `action_required` with zero jobs, and `success`
    with zero jobs, both go RED; a run with real jobs, a concurrency `skipped`, an in-flight run
    (queued-alarm's own territory) and a ghost outside the window do NOT."""
    import datetime as dtm
    now = dtm.datetime.now(dtm.timezone.utc)
    old_ts = (now - dtm.timedelta(hours=400)).strftime("%Y-%m-%dT%H:%M:%SZ")

    runs = [
        {"databaseId": 1, "headBranch": "ci/a", "headSha": "a" * 40,
         "status": "completed", "conclusion": "action_required"},
        {"databaseId": 2, "headBranch": "ci/b", "headSha": "b" * 40,
         "status": "completed", "conclusion": "success"},
        {"databaseId": 3, "headBranch": "ci/c", "headSha": "c" * 40,
         "status": "completed", "conclusion": "success"},
        {"databaseId": 4, "headBranch": "ci/d", "headSha": "d" * 40,
         "status": "completed", "conclusion": "skipped"},
        {"databaseId": 5, "headBranch": "ci/e", "headSha": "e" * 40,
         "status": "in_progress", "conclusion": ""},
        {"databaseId": 6, "headBranch": "ci/f", "headSha": "f" * 40,
         "status": "completed", "conclusion": "action_required", "createdAt": old_ts},
    ]
    # (issue #1158) gh's OWN answer shapes are planted: `run list --json` is an ARRAY,
    # `run view --json jobs` is the OBJECT {"jobs": […]}. A seam that read either as `[]`
    # made every completed run look like a ghost (measured live: 50 false ghosts in 168h).
    jobs = {1: {"jobs": []},
            2: {"jobs": [{"id": 90, "status": "completed", "conclusion": "success"}]},
            3: {"jobs": []}, 4: {"jobs": []}, 5: {"jobs": []}}
    proc = _run_ghost_alarm([dict(r) for r in runs], jobs)
    out = proc.stdout + proc.stderr
    check("ghost alarm exits 1 (the sweep goes RED, not quiet)", proc.returncode == 1, out[:300])
    check("the action_required-with-zero-jobs ghost is flagged",
          "runs/1 " in out or "runs/1\n" in out or "/1 " in out, out[:300])
    check("the success-with-ZERO-jobs ghost is flagged (the pipeline never FAILED, it never RAN)",
          "runs/3" in out, out[:300])
    check("a run with real jobs is NOT a ghost", "runs/2" not in out, out[:300])
    check("a concurrency-skipped run is NOT a ghost", "runs/4" not in out, out[:300])
    check("an in-flight run belongs to queued-alarm, not here", "runs/5" not in out, out[:300])
    check("a ghost outside the window is named by the window, not silently forever",
          "runs/6" not in out, out[:300])
    check("the remedy is named (owner-PAT re-push), the alarm fixes nothing itself",
          "owner-PAT" in out or "owner PAT" in out or "REBASE=1" in out, out[-300:])
    asked = GHOST_GH_LOGS[-1] if GHOST_GH_LOGS else ""
    check("(issue #1158) the request the alarm ACTUALLY built asks for `url`, never `htmlUrl`",
          "--json databaseId,workflowName,name,headBranch,headSha,status,conclusion,createdAt,url"
          in asked and "htmlUrl" not in asked, asked[:300])
    check("(issue #1158) the ghost line prints the url gh answered",
          "https://github.com/o/r/actions/runs/1" in out, out[:300])

    clean = _run_ghost_alarm([dict(runs[1])], jobs)
    check("a green planted queue exits 0", clean.returncode == 0, clean.stdout[:200])
    broken = _run_ghost_alarm([dict(runs[1])], jobs, fail=True)
    check("a failed GitHub read is exit 2, never a silent clean",
          broken.returncode == 2 and "READ FAILED" in broken.stdout, broken.stdout[:200])

    check("ghost_verdict is pure (rule 6d): action_required + zero jobs is a ghost",
          __import__("pr_health") and _ghost_verdict_check(), "")


def test_the_ghost_alarm_refuses_a_gh_answer_of_the_wrong_shape():
    """(issue #1158, measured live) the jobs read is a CONTRACT, not a best-effort parse: gh
    answers `run view --json jobs` with the OBJECT {"jobs": […]}. A seam that answered `[]` for
    anything it did not recognise made EVERY completed run look like a ghost — the fixed alarm
    printed 50 false ghosts on this repository before its own answer-shape check landed. A wrong
    shape must be a loud exit 2, never a verdict."""
    ghost_run = {"databaseId": 11, "headBranch": "ci/g", "headSha": "g" * 40,
                 "status": "completed", "conclusion": "success"}
    no_jobs_key = _run_ghost_alarm([dict(ghost_run)], {11: {"workflows": []}})
    out1 = no_jobs_key.stdout + no_jobs_key.stderr
    check("a jobs answer with no 'jobs' array is a READ FAILED exit 2, not a ghost verdict",
          no_jobs_key.returncode == 2 and "READ FAILED" in out1 and "jobs" in out1, out1[:240])
    check("that run is NOT reported as a ghost", "runs/11 " not in out1, out1[:240])

    array_answer = _run_ghost_alarm([dict(ghost_run, databaseId=12)], {12: []})
    out2 = array_answer.stdout + array_answer.stderr
    check("an ARRAY where gh answers an OBJECT is also a loud exit 2",
          array_answer.returncode == 2 and "READ FAILED" in out2, out2[:240])

    honest = _run_ghost_alarm([dict(ghost_run, databaseId=13)], {13: {"jobs": []}})
    check("a REAL zero-jobs answer is still flagged as the ghost it is",
          honest.returncode == 1 and "runs/13" in honest.stdout and "jobs=0" in honest.stdout,
          honest.stdout[:240])


def test_a_missing_gh_is_a_loud_read_failure_not_a_traceback():
    """(issue #1158, measured on a host whose PATH lacked /opt/homebrew/bin) the alarm calls
    `gh` through subprocess; when gh is not runnable the sweep must get the loud
    `READ FAILED (exit 2)` line, not a Python traceback it cannot grade."""
    import shutil
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        bindir = td / "bin"
        bindir.mkdir()
        link = bindir / "python3"
        link.symlink_to(shutil.which("python3"))
        env = {**GIT_ENV, "PATH": str(bindir),
               "FAKE_RUNS": str(td / "runs.json"), "FAKE_JOBS_DIR": str(td),
               "GH_FIELD_CONTRACT": str(ROOT / "scripts" / "gh_json_fields.py"),
               "PYTHON": str(link)}
        (td / "runs.json").write_text("[]")
        proc = subprocess.run(
            [str(link), str(ROOT / "scripts" / "ghost_run_alarm.py"), "--repo", "o/r"],
            capture_output=True, text=True, env=env)
        out = proc.stdout + proc.stderr
        check("no gh on PATH -> exit 2 with the READ FAILED line (no traceback)",
              proc.returncode == 2 and "READ FAILED" in out and "Traceback" not in out,
              out[:300])


def _ghost_verdict_check() -> bool:
    import ghost_run_alarm as GA
    return (GA.ghost_verdict({"status": "completed", "conclusion": "action_required"}, []) is True
            and GA.ghost_verdict({"status": "completed", "conclusion": "success"}, []) is True
            and GA.ghost_verdict({"status": "completed", "conclusion": "success"}, [{"id": 1}]) is False
            and GA.ghost_verdict({"status": "completed", "conclusion": "skipped"}, []) is False
            and GA.ghost_verdict({"status": "in_progress", "conclusion": ""}, []) is False)


def test_ghost_run_and_push_identity_wiring():
    """Both halves are wired where CI runs them (rules 6d/6m): the qa-validate `auto-merge-rebase`
    step and the pr-health sweep step carry GIT_PUSH_PAT; queued-alarm calls
    `make ghost-run-alarm` with the DEFAULT token (a ghost is READ, not written); the Makefile
    defines the target; and the rebaser seam reads the env it is given."""
    qa = yaml.safe_load(WORKFLOW.read_text())
    am_steps = qa["jobs"]["auto-merge"]["steps"]
    rebase_step = next(s for s in am_steps if s.get("id") == "auto-merge-rebase")
    check("qa-validate: the auto-merge-rebase step provides GIT_PUSH_PAT (owner PAT)",
          "FIXBOT_DISPATCH_TOKEN" in str((rebase_step.get("env") or {}).get("GIT_PUSH_PAT", "")),
          str(rebase_step.get("env")))
    check("qa-validate: the rebase step keeps its READS on the default token",
          "github.token" in str((rebase_step.get("env") or {}).get("GH_TOKEN", "")), "")

    ph_wf = (ROOT / ".github" / "workflows" / "pr-health.yml").read_text()
    check("pr-health: the sweep step provides GIT_PUSH_PAT to the rebaser",
          "GIT_PUSH_PAT: ${{ secrets.FIXBOT_DISPATCH_TOKEN }}" in ph_wf, ph_wf[:200])

    qa_text = (ROOT / ".github" / "workflows" / "queued-alarm.yml").read_text()
    check("queued-alarm: the ghost sweep is called through the Makefile (rule 6m)",
          'make ghost-run-alarm REPO="${{ github.repository }}"' in qa_text, "")
    ghost_step = qa_text[qa_text.index("completed with zero jobs (issue #1115)"):]
    ghost_step = ghost_step[:ghost_step.index("A red main pipeline")]
    check("queued-alarm: the ghost step is read-only with the DEFAULT token (no owner PAT)",
          "GH_TOKEN: ${{ github.token }}" in ghost_step
          and "FIXBOT_DISPATCH_TOKEN" not in ghost_step, ghost_step[:200])

    mk = MAKEFILE.read_text()
    check("Makefile: `make ghost-run-alarm` is defined and dispatches the internal recipe",
          "ghost-run-alarm:" in mk and "_ghost-run-alarm:" in mk
          and "scripts/ghost_run_alarm.py" in mk, "")

    ph_src = PR_HEALTH.read_text()
    check("the ONE rebaser reads GIT_PUSH_PAT and names the push identity it used",
          "GIT_PUSH_PAT" in ph_src and "pat_push_url" in ph_src
          and "push identity" in ph_src, "")
    check("the ghost DECISION lives in the script, not in the workflow shell (rule 6d)",
          "ghost_verdict" in (ROOT / "scripts" / "ghost_run_alarm.py").read_text()
          and "ghost_verdict" not in qa_text, "")


def main():
    tests = [
        test_behind_clean_bot_branch_is_rebased_with_a_current_index,
        test_current_head_reports_current_and_pushes_nothing,
        test_human_owned_behind_branch_is_reported_and_untouched,
        test_conflicting_branches_are_never_rewritten,
        test_regeneration_failure_keeps_the_branch_untouched,
        test_the_auto_merge_wiring_refuses_the_merge_as_is_flow,
        test_classification_is_pure_and_partitions,
        # (issue #1115) the push-identity fix and the ghost-run alarm it pairs with.
        test_rebase_push_carries_the_owner_pat_identity_when_the_step_provides_it,
        test_ghost_alarm_flags_completed_pr_runs_with_zero_jobs,
        test_the_ghost_alarm_refuses_a_gh_answer_of_the_wrong_shape,
        test_a_missing_gh_is_a_loud_read_failure_not_a_traceback,
        test_ghost_run_and_push_identity_wiring,
    ]
    for t in tests:
        print(f"\n[{t.__name__}]")
        t()
    print(f"\n{os.path.basename(__file__)}: {_PASS} passed, {_FAIL} failed")
    return 1 if _FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
