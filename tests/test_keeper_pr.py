#!/usr/bin/env python3
"""tests/test_keeper_pr.py — the ONE keeper-landing sequence (issues #869, #1081,
rules 6d/6m).

Drives the REAL scripts/keeper_pr.py through the REAL make keeper-pr target against
a REAL local git remote (rule 6m: external systems are real; `gh` is a stub CLI on
PATH — the sanctioned stand-in for the network). Pins the refusal/suppression
verdicts, single- and multi-file landing (#1081), the landed commit's identity and
shape, the body coming from the keeper's own target, and — the Done-when of #869
extended by #1081 — that no keeper job spells its own copy of the landing shell.
"""
from __future__ import annotations

import base64
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
KEEPER = ROOT / "scripts" / "keeper_pr.py"
MAKEFILE = ROOT / "Makefile"
QA_WF = ROOT / ".github" / "workflows" / "qa-validate.yml"
QUEUE_WF = ROOT / ".github" / "workflows" / "queued-alarm.yml"
ARCH_WF = ROOT / ".github" / "workflows" / "architecture-bot.yml"

FAILURES: list[str] = []


def check(label: str, ok: bool, detail: str = "") -> None:
    print(f"  {'PASS' if ok else 'FAIL'}  {label}")
    if not ok:
        FAILURES.append(f"{label}\n{detail[:600]}")


def git(*args: str, cwd: Path) -> str:
    proc = subprocess.run(["git"] + list(args), cwd=str(cwd),
                          capture_output=True, text=True, check=True)
    return proc.stdout.strip()


GH_STUB = """#!/bin/sh
if [ "$1" = "pr" ] && [ "$2" = "list" ]; then
    printf '%s\\n' "$KEEPER_GH_LIST"
    exit "${KEEPER_GH_LIST_RC:-0}"
fi
if [ "$1" = "pr" ] && [ "$2" = "create" ]; then
    { printf 'CREATE %s\\n' "$*"; printf 'BODY\\n'; cat; } >> "$KEEPER_GH_LOG"
    echo "https://github.com/o/r/pull/999"
    exit 0
fi
if [ "$1" = "pr" ] && [ "$2" = "comment" ]; then
    { printf 'COMMENT %s\\n' "$*"; } >> "$KEEPER_GH_LOG"
    exit 0
fi
if [ "$1" = "pr" ] && [ "$2" = "close" ]; then
    { printf 'CLOSE %s\\n' "$*"; } >> "$KEEPER_GH_LOG"
    exit 0
fi
if [ "$1" = "api" ]; then
    printf '%s' "$KEEPER_GH_API_CONTENT"
    exit 0
fi
exit 0
"""


def make_scene(tmp: Path) -> tuple[Path, dict]:
    """A clone with a real bare remote: one commit on master, a keeper body target."""
    remote = tmp / "remote.git"
    subprocess.run(["git", "init", "--bare", "-q", "-b", "master", str(remote)], check=True)
    work = tmp / "repo"
    subprocess.run(["git", "clone", "-q", str(remote), str(work)], check=True)
    git("config", "user.name", "Seed", cwd=work)
    git("config", "user.email", "seed@example.com", cwd=work)
    (work / "GENERATED.md").write_text("committed generation\n")
    (work / "README.md").write_text("product readme\n")
    (work / "Makefile").write_text(
        ".PHONY: keeper-body ORIGINAL_ARCHIVED=486\n"
        "keeper-body:\n"
        "\t@echo 'BODY MASTER_SHA=$(MASTER_SHA) RUN_URL=$(RUN_URL)'\n"
    )
    (work / "OPENSPEC.md").write_text(
        "# OpenSpec index\n\n"
        "Active changes: **0** · archived: **486**\n\n"
        "## Archived changes\n\n"
        "| Change | State | Issue | PR | Capability specs | Tasks | Proposal |\n"
        "|---|---|---|---|---|---|---|\n"
        "| `heartbeat-1282` | archived | #700 | #701 | [fleet-watch](openspec/changes/archive/heartbeat-1282/specs/fleet-watch/spec.md) | 20/20 | [proposal.md](openspec/changes/archive/heartbeat-1282/proposal.md) |\n",
        encoding="utf-8",
    )
    git("add", "-A", cwd=work)
    git("commit", "-q", "-m", "seed", cwd=work)
    git("push", "-q", "-u", "origin", "master", cwd=work)
    bin_dir = tmp / "bin"
    bin_dir.mkdir()
    gh = bin_dir / "gh"
    gh.write_text(GH_STUB)
    gh.chmod(0o755)
    env = dict(os.environ)
    env["PATH"] = f"{bin_dir}{os.pathsep}{env.get('PATH', '')}"
    env.setdefault("KEEPER_GH_LIST", "[]")
    env["KEEPER_GH_LOG"] = str(tmp / "gh_log.txt")
    env["KEEPER_GH_API_CONTENT"] = ""
    return work, env


def run_keeper(work: Path, env: dict, *extra: str) -> subprocess.CompletedProcess:
    cmd = [sys.executable, str(KEEPER), "--root", str(work)] + list(extra)
    return subprocess.run(cmd, capture_output=True, text=True, timeout=120, env=env)


BASE_ARGS = ("--file", "GENERATED.md", "--branch-prefix", "ci/test-keeper",
             "--commit-message", "chore(keeper): land the generated file",
             "--pr-title", "chore(keeper): land the generated file",
             "--body-target", "keeper-body",
             "--body-args", "MASTER_SHA=abc123 RUN_URL=https://example/run/1")


def test_no_change_exits_zero_without_a_branch_or_pr() -> None:
    print("\nnothing changed: exit 0, no branch, no commit, no PR")
    with tempfile.TemporaryDirectory() as td:
        work, env = make_scene(Path(td))
        proc = run_keeper(work, env, *BASE_ARGS)
        check("nothing-to-land exits 0", proc.returncode == 0, proc.stdout + proc.stderr)
        check("nothing-to-land names itself", "nothing to land" in proc.stdout, proc.stdout)
        refs = git("ls-remote", "--heads", "origin", cwd=work)
        check("no branch was pushed", refs == refs and "refs/heads/master" in refs
              and "test-keeper" not in refs, refs)
        check("no PR was opened", not Path(env["KEEPER_GH_LOG"]).exists(), "")


def test_extra_changes_refuse_exit_1_and_land_nothing() -> None:
    print("\nmore than the keeper file changed: exit 1 naming every file, nothing lands")
    with tempfile.TemporaryDirectory() as td:
        work, env = make_scene(Path(td))
        (work / "GENERATED.md").write_text("regenerated\n")
        (work / "README.md").write_text("collateral edit\n")
        proc = run_keeper(work, env, *BASE_ARGS)
        check("wider drift is refused with exit 1", proc.returncode == 1, proc.stdout)
        check("the refusal names the stray file", "README.md" in proc.stdout, proc.stdout)
        refs = git("ls-remote", "--heads", "origin", cwd=work)
        check("refusal pushes no branch", "test-keeper" not in refs, refs)
        check("refusal opens no PR", not Path(env["KEEPER_GH_LOG"]).exists(), "")


def keeper_row(name: str, state: str = "MERGEABLE", checks=(), number: int = 1248,
               head: str = "deadbeef") -> dict:
    """One `gh pr list` row as the real client answers it (the stub bypasses `--jq`)."""
    return {"number": number, "headRefName": name, "headRefOid": head,
            "mergeStateStatus": state,
            "statusCheckRollup": [{"name": n, "conclusion": c} for n, c in checks]}


GREEN = (("validate", "success"), ("live-smoke", "success"))


def test_mergeable_keeper_suppresses_and_dirty_keeper_does_not() -> None:
    print("\ndedupe #960/#1303: a LIVE open keeper suppresses; DIRTY/CONFLICTING keepers do not")
    with tempfile.TemporaryDirectory() as td:
        work, env = make_scene(Path(td))
        (work / "GENERATED.md").write_text("regenerated\n")
        env["KEEPER_GH_LIST"] = json.dumps(
            [keeper_row("ci/test-keeper-live", checks=GREEN)])
        proc = run_keeper(work, env, *BASE_ARGS, "--dedupe")
        check("a live open keeper suppresses the duplicate", proc.returncode == 0
              and "already open" in proc.stdout, proc.stdout)
        refs = git("ls-remote", "--heads", "origin", cwd=work)
        check("suppression pushes no branch", "test-keeper" not in refs, refs)
    with tempfile.TemporaryDirectory() as td:
        work, env = make_scene(Path(td))
        (work / "GENERATED.md").write_text("regenerated\n")
        env["KEEPER_GH_LIST"] = json.dumps(
            [keeper_row("ci/test-keeper-dirty", state="DIRTY"),
             keeper_row("ci/test-keeper-conflicting", state="CONFLICTING")])
        proc = run_keeper(work, env, *BASE_ARGS, "--dedupe")
        check("unmergeable keepers do NOT suppress (exit 0, fresh keeper lands)",
              proc.returncode == 0 and "UNMERGEABLE" in proc.stdout, proc.stdout)
        refs = git("ls-remote", "--heads", "origin", cwd=work)
        check("a fresh keeper is filed against the current tip",
              "refs/heads/ci/test-keeper-" in refs, refs)


def test_a_checkless_mergeable_keeper_does_not_suppress() -> None:
    print("\n#1303: a MERGEABLE keeper with NO check objects is a TOMBSTONE — a fresh keeper lands")
    with tempfile.TemporaryDirectory() as td:
        work, env = make_scene(Path(td))
        (work / "GENERATED.md").write_text("regenerated\n")
        env["KEEPER_GH_LIST"] = json.dumps(
            [keeper_row("ci/openspec-index-repair-20261122T041000Z", checks=())])
        proc = run_keeper(work, env, *BASE_ARGS, "--dedupe")
        check("a checkless mergeable keeper does NOT suppress", proc.returncode == 0
              and "TOMBSTONE" in proc.stdout, proc.stdout)
        check("the tombstone names the keeper shape", "never validated" in proc.stdout,
              proc.stdout)
        refs = git("ls-remote", "--heads", "origin", cwd=work)
        check("a fresh keeper is filed against the current tip",
              "refs/heads/ci/test-keeper-" in refs, refs)


def test_a_red_keeper_does_not_suppress() -> None:
    print("\n#1303: a keeper whose required check concluded red is a TOMBSTONE")
    with tempfile.TemporaryDirectory() as td:
        work, env = make_scene(Path(td))
        (work / "GENERATED.md").write_text("regenerated\n")
        env["KEEPER_GH_LIST"] = json.dumps(
            [keeper_row("ci/test-keeper-red",
                        checks=(("validate", "failure"), ("live-smoke", "success")))])
        proc = run_keeper(work, env, *BASE_ARGS, "--dedupe")
        check("a red keeper does NOT suppress", proc.returncode == 0
              and "TOMBSTONE" in proc.stdout, proc.stdout)
        refs = git("ls-remote", "--heads", "origin", cwd=work)
        check("a fresh keeper is filed against the current tip",
              "refs/heads/ci/test-keeper-" in refs, refs)


def test_an_in_flight_keeper_still_suppresses() -> None:
    print("\n#1303: a keeper whose checks are still running is LIVE — never duplicate it")
    with tempfile.TemporaryDirectory() as td:
        work, env = make_scene(Path(td))
        (work / "GENERATED.md").write_text("regenerated\n")
        env["KEEPER_GH_LIST"] = json.dumps([keeper_row(
            "ci/test-keeper-flight",
            checks=(("validate", None), ("live-smoke", None)))])
        proc = run_keeper(work, env, *BASE_ARGS, "--dedupe")
        check("an in-flight keeper suppresses", proc.returncode == 0
              and "already open" in proc.stdout and "TOMBSTONE" not in proc.stdout,
              proc.stdout)
        refs = git("ls-remote", "--heads", "origin", cwd=work)
        check("no duplicate branch is pushed", "refs/heads/ci/test-keeper-" not in refs, refs)


def test_keeper_lands_one_commit_touching_only_its_file() -> None:
    print("\nthe landed keeper: one agent-identity commit on a timestamped branch, "
          "body from the keeper's own target")
    sys.path.insert(0, str(ROOT / "scripts"))
    import agent_identity as AI
    with tempfile.TemporaryDirectory() as td:
        work, env = make_scene(Path(td))
        (work / "GENERATED.md").write_text("regenerated\n")
        (work / "untracked-scratch").write_text("ignored\n")
        proc = run_keeper(work, env, *BASE_ARGS)
        check("land exits 0 and names the branch", proc.returncode == 0
              and re.search(r"ci/test-keeper-\d{8}T\d{6}Z", proc.stdout) is not None,
              proc.stdout)
        branch = re.search(r"ci/test-keeper-\d{8}T\d{6}Z", proc.stdout).group(0)
        refs = git("ls-remote", "--heads", "origin", cwd=work)
        check("the branch is pushed to origin", f"refs/heads/{branch}" in refs, refs)
        check("the branch carries exactly one commit above master",
              git("rev-list", "--count", f"origin/master..{branch}", cwd=work) == "1", "")
        author = git("log", "-1", "--format=%an <%ae>", branch, cwd=work)
        check("the commit is authored by the repo agent identity",
              author == f"{AI.AGENT_NAME} <{AI.AGENT_EMAIL}>", author)
        touched = git("show", "--name-only", "--format=", branch, cwd=work).splitlines()
        check("the commit touches ONLY the keeper file (untracked scratch stays out)",
              touched == ["GENERATED.md"], str(touched))
        log = Path(env["KEEPER_GH_LOG"]).read_text()
        check("the PR body is the keeper target's own output with its BODY_ARGS",
              "BODY MASTER_SHA=abc123 RUN_URL=https://example/run/1" in log, log[:400])
        check("gh pr create carries the branch, base master and the title",
              f"--head {branch}" in log and "--base master" in log
              and "chore(keeper): land the generated file" in log, log[:400])


def test_multi_file_keeper_lands_one_commit_touching_both_files() -> None:
    """Issue #1081: the weekly architecture keeper regenerates ARCHITECTURE.md AND
    OPENSPEC.md; ONE seam invocation must land both files in one commit."""
    print("\nissue #1081: a multi-file keeper lands one commit carrying both owned files")
    with tempfile.TemporaryDirectory() as td:
        work, env = make_scene(Path(td))
        (work / "EXTRA.md").write_text("committed generation\n")
        git("add", "-A", cwd=work)
        git("commit", "-q", "-m", "seed extra", cwd=work)
        git("push", "-q", "origin", "master", cwd=work)
        (work / "GENERATED.md").write_text("regenerated\n")
        (work / "EXTRA.md").write_text("regenerated too\n")
        proc = run_keeper(work, env, "--file", "GENERATED.md EXTRA.md",
                          "--branch-prefix", "ci/test-keeper",
                          "--commit-message", "chore(keeper): land both generated files",
                          "--pr-title", "chore(keeper): land both generated files",
                          "--body-target", "keeper-body")
        check("multi-file land exits 0", proc.returncode == 0, proc.stdout + proc.stderr)
        check("the landing names BOTH files", "GENERATED.md EXTRA.md" in proc.stdout,
              proc.stdout)
        branch = re.search(r"ci/test-keeper-\d{8}T\d{6}Z", proc.stdout).group(0)
        touched = git("show", "--name-only", "--format=", branch, cwd=work).splitlines()
        check("ONE commit carries exactly both files",
              touched == ["EXTRA.md", "GENERATED.md"], str(touched))


def test_multi_file_keeper_lands_only_the_owned_file_that_changed() -> None:
    print("\nissue #1081: with a set of owned files, the one that changed still lands alone")
    with tempfile.TemporaryDirectory() as td:
        work, env = make_scene(Path(td))
        (work / "EXTRA.md").write_text("committed generation\n")
        git("add", "-A", cwd=work)
        git("commit", "-q", "-m", "seed extra", cwd=work)
        git("push", "-q", "origin", "master", cwd=work)
        (work / "GENERATED.md").write_text("regenerated\n")
        proc = run_keeper(work, env, "--file", "GENERATED.md EXTRA.md",
                          "--branch-prefix", "ci/test-keeper",
                          "--commit-message", "chore(keeper): land the changed file",
                          "--pr-title", "chore(keeper): land the changed file",
                          "--body-target", "keeper-body")
        check("partial-set drift lands exit 0", proc.returncode == 0,
              proc.stdout + proc.stderr)
        branch = re.search(r"ci/test-keeper-\d{8}T\d{6}Z", proc.stdout).group(0)
        touched = git("show", "--name-only", "--format=", branch, cwd=work).splitlines()
        check("the commit carries only the file that changed", touched == ["GENERATED.md"],
              str(touched))


def test_a_keeper_command_that_cannot_run_exits_two_loudly() -> None:
    print("\nloud failure: a failed gh read is exit 2, never a silent pass")
    with tempfile.TemporaryDirectory() as td:
        work, env = make_scene(Path(td))
        (work / "GENERATED.md").write_text("regenerated\n")
        env["KEEPER_GH_LIST_RC"] = "1"
        env["KEEPER_GH_LIST"] = "not json"
        proc = run_keeper(work, env, *BASE_ARGS, "--dedupe")
        check("unusable dedupe read exits 2 naming the failure", proc.returncode == 2
              and "UNAVAILABLE" in proc.stdout, proc.stdout + proc.stderr)
        refs = git("ls-remote", "--heads", "origin", cwd=work)
        check("a refused sequence lands no branch", "test-keeper" not in refs, refs)


def test_no_keeper_job_spells_the_landing_sequence_anymore() -> None:
    print("\nDone-when (#869, extended by #1081): the four keeper jobs land through "
          "make keeper-pr; no keeper step re-spells the landing shell")
    try:
        import yaml
    except ImportError:
        # the test image ships pyyaml; on hosts without it this check is skipped.
        print("  SKIP  pyyaml not installed (the test image has it)")
        return
    jobs = [("qa-validate.yml", QA_WF, "index-repair"),
            ("qa-validate.yml", QA_WF, "architecture-repair"),
            ("queued-alarm.yml", QUEUE_WF, "alarm"),
            # issue #1081: the weekly architecture keeper joined the seam.
            ("architecture-bot.yml", ARCH_WF, "refresh")]
    for wf_name, wf_path, job_name in jobs:
        wf = yaml.safe_load(wf_path.read_text())
        job = wf["jobs"][job_name]
        text = "\n".join(str(s.get("run", "")) for s in job["steps"])
        check(f"{wf_name}:{job_name} lands its keeper through the seam",
              "make keeper-pr" in text, text[:600])
        for spelled in ("git switch -c", 'git push origin "HEAD:refs/heads/',
                        "status --porcelain", 'startswith("ci/', "git config"):
            check(f"{wf_name}:{job_name} does not re-spell {spelled!r}",
                  spelled not in text, text[:600])
    # #962's invalid-change-repair keeper lands a MULTI-PATH drift (the archive
    # move + the regenerated index); keeper_pr lands its owned files only and
    # REFUSES wider drift, so that job keeps its own shell — pinned inline
    # by tests/test_workflows.py. The seam's no-second-copy guarantee covers the
    # keeper jobs the seam can actually land.
    qa_scoped = "\n".join(
        str(s.get("run", ""))
        for name, job in yaml.safe_load(QA_WF.read_text())["jobs"].items()
        if name != "invalid-change-repair"
        for s in job.get("steps", []))
    check("the landing shell lives ONLY in scripts/keeper_pr.py (no second copy in "
          "the seam's keeper jobs; #962's multi-path shell keeper is pinned "
          "separately by tests/test_workflows.py)",
          'git push origin "HEAD:refs/heads/' not in qa_scoped
          and "git switch -c" not in qa_scoped
          and "git switch -c" not in QUEUE_WF.read_text()
          and 'git push origin "HEAD:refs/heads/' not in ARCH_WF.read_text()
          and "git switch -c" not in ARCH_WF.read_text(), "")


def test_reaches_ci_through_the_makefile_only() -> None:
    """Rule 6m both directions: the script is reached only via make, and a CI job calls it."""
    print("\nwiring: no workflow reaches scripts/keeper_pr.py directly; a keeper job calls it")
    qa, queue = QA_WF.read_text(), QUEUE_WF.read_text()
    for name, text in (("qa-validate.yml", qa), ("queued-alarm.yml", queue)):
        check(f"{name} calls make keeper-pr (never executes the script itself)",
              "make keeper-pr" in text
              and "python3 scripts/keeper_pr.py" not in text
              and "python scripts/keeper_pr.py" not in text, "")
    wf_dir = ROOT / ".github" / "workflows"
    direct = [p.name for p in wf_dir.glob("*.yml")
              if ("python3 scripts/keeper_pr.py" in p.read_text()
                  or "python scripts/keeper_pr.py" in p.read_text())]
    check("no workflow executes scripts/keeper_pr.py directly anywhere", direct == [], str(direct))


def _set_and_read(work: Path, env: dict, keeper_count: int, master_count: int) -> None:
    """Put two different `archived:` counts into a fresh OPENSPEC.md, committed to master.

    The keeper's own count arrives through `KEEPER_GH_API_CONTENT`; the master count is
    written into the rendered index. The extra archived row keeps the write a REAL diff
    against `make_scene`'s seed (an identical tree would make `git commit` exit 1).
    """
    env["KEEPER_GH_API_CONTENT"] = base64.b64encode(
        "Active changes: **0** · archived: **{}**\n".format(keeper_count).encode("utf-8")
    ).decode("ascii")
    (work / "OPENSPEC.md").write_text(
        "# OpenSpec index\n\n"
        "Active changes: **0** · archived: **{}**\n\n"
        "## Archived changes\n\n"
        "| Change | State | Issue | PR | Capability specs | Tasks | Proposal |\n"
        "|---|---|---|---|---|---|---|\n"
        "| `heartbeat-1282` | archived | #700 | #701 | [fleet-watch](openspec/changes/archive/heartbeat-1282/specs/fleet-watch/spec.md) | 20/20 | [proposal.md](openspec/changes/archive/heartbeat-1282/proposal.md) |\n"
        "| `seed-row` | archived | #700 | #701 | [x](x.md) | 1/1 | [p.md](p.md) |\n".format(master_count),
        encoding="utf-8",
    )
    git("add", "-A", cwd=work)
    git("commit", "-q", "-m", "upstream index", cwd=work)
    git("push", "-q", "origin", "master", cwd=work)


def _github_remote(work: Path, bare: Path) -> None:
    """Give origin a github.com FETCH url (so `repo_slug` parses) while its PUSH url stays
    the real local bare remote — the fixture exercises the real push, not a fake URL."""
    git("remote", "set-url", "origin", "https://github.com/o/r.git", cwd=work)
    git("remote", "set-url", "--push", "origin", str(bare), cwd=work)


def test_a_stale_mergeable_index_repair_keeper_is_superseded_and_closed() -> None:
    print("\n#1438: a BELOW-count mergeable keeper is superseded: commented with both counts, "
          "closed, and a fresh keeper still lands")
    with tempfile.TemporaryDirectory() as td:
        work, env = make_scene(Path(td))
        _set_and_read(work, env, keeper_count=397, master_count=486)
        _github_remote(work, Path(td) / "remote.git")
        (work / "GENERATED.md").write_text("regenerated\n")
        env["KEEPER_GH_LIST"] = json.dumps(
            [keeper_row("ci/openspec-index-repair-2026-01-01T000000Z", checks=GREEN)])
        proc = run_keeper(work, env, *BASE_ARGS, "--dedupe")
        check("exit 0", proc.returncode == 0, proc.stdout + proc.stderr)
        check("classifies SUPERSEDED", "SUPERSEDED" in proc.stdout, proc.stdout)
        log = Path(env["KEEPER_GH_LOG"]).read_text()
        check("comments the count evidence", "archived: **397**" in log and "archived: **486**" in log, log)
        check("closes the stale keeper", "CLOSE pr close 1248" in log, log)
        refs = git("ls-remote", "--heads", str(Path(td) / "remote.git"), cwd=work)
        check("fresh keeper branch pushed", re.search(r"ci/test-keeper-\d{8}T\d{6}Z", refs) is not None, refs)


def test_a_current_mergeable_index_repair_keeper_is_live() -> None:
    print("\n#1438: a keeper AT the master count stays live and suppresses a duplicate")
    with tempfile.TemporaryDirectory() as td:
        work, env = make_scene(Path(td))
        _set_and_read(work, env, keeper_count=486, master_count=486)
        _github_remote(work, Path(td) / "remote.git")
        (work / "GENERATED.md").write_text("regenerated\n")
        env["KEEPER_GH_LIST"] = json.dumps(
            [keeper_row("ci/openspec-index-repair-2026-01-01T000000Z", checks=GREEN)])
        proc = run_keeper(work, env, *BASE_ARGS, "--dedupe")
        check("exit 0", proc.returncode == 0, proc.stdout + proc.stderr)
        check("classified live, not superseded", "SUPERSEDED" not in proc.stdout, proc.stdout)
        check("suppresses the duplicate", "already open" in proc.stdout, proc.stdout)
        log = Path(env["KEEPER_GH_LOG"])
        check("no comment, no close on a current keeper",
              not log.exists() or ("COMMENT" not in log.read_text() and "CLOSE" not in log.read_text()),
              log.read_text() if log.exists() else "<no gh write>")
        refs = git("ls-remote", "--heads", str(Path(td) / "remote.git"), cwd=work)
        check("no fresh branch pushed", "test-keeper-" not in refs, refs)


def test_the_supersede_guard_is_red_on_the_base_revision() -> None:
    print("\n#1438 Done-when: the pre-change keeper_pr.py has no supersede path; a guard "
          "failing against it proves the new shape is real")
    base_src = subprocess.run(
        ["git", "show", "origin/master:scripts/keeper_pr.py"], cwd=ROOT,
        capture_output=True, text=True, check=False)
    if base_src.returncode != 0 or not base_src.stdout.strip():
        check("base revision readable: source exists and is non-empty",
              False, base_src.stderr)
        return
    root = Path(tempfile.mkdtemp())
    try:
        (root / "scripts").mkdir()
        (root / "scripts" / "keeper_pr.py").write_text(base_src.stdout, encoding="utf-8")
        (root / "agent_identity.py").write_text(
            "AGENT_NAME = 'Seed'\nAGENT_EMAIL = 'seed@example.com'\n", encoding="utf-8")
        sys.path.insert(0, str(root / "scripts"))
        import importlib.util as ilu
        spec = ilu.spec_from_file_location("keeper_pr_base", root / "scripts" / "keeper_pr.py")
        base_mod = ilu.module_from_spec(spec)
        spec.loader.exec_module(base_mod)
        base_dedupe = base_mod.keeper_dedupe
        work, env = make_scene(Path(tempfile.mkdtemp()))
        _set_and_read(work, env, keeper_count=397, master_count=486)
        git("remote", "set-url", "origin", "https://github.com/o/r.git", cwd=work)
        (work / "GENERATED.md").write_text("regenerated\n")
        env["KEEPER_GH_LIST"] = json.dumps(
            [keeper_row("ci/openspec-index-repair-2026-01-01T000000Z", checks=GREEN)])
        # The base dedupe shells out to `gh` and inherits os.environ (it takes no env),
        # so drive it with the SAME stub PATH the real run uses.
        saved_path = os.environ.get("PATH", "")
        saved_list = os.environ.get("KEEPER_GH_LIST")
        os.environ["PATH"] = env["PATH"]
        os.environ["KEEPER_GH_LIST"] = env["KEEPER_GH_LIST"]
        try:
            out = base_dedupe("ci/openspec-index-repair-", work)
        finally:
            os.environ["PATH"] = saved_path
            if saved_list is None:
                os.environ.pop("KEEPER_GH_LIST", None)
            else:
                os.environ["KEEPER_GH_LIST"] = saved_list
        check("the BASE dedupe reports no superseded keepers (3-tuple shape)",
              len(out) == 3, repr(out))
        log = Path(env["KEEPER_GH_LOG"])
        check("the base dedupe never closed the stale keeper",
              not log.exists() or "CLOSE" not in log.read_text(),
              log.read_text() if log.exists() else "<no gh write>")
    finally:
        import shutil
        shutil.rmtree(root, ignore_errors=True)


def main() -> int:
    for t in (test_no_change_exits_zero_without_a_branch_or_pr,
              test_extra_changes_refuse_exit_1_and_land_nothing,
              test_mergeable_keeper_suppresses_and_dirty_keeper_does_not,
              test_a_checkless_mergeable_keeper_does_not_suppress,
              test_a_red_keeper_does_not_suppress,
              test_an_in_flight_keeper_still_suppresses,
              test_keeper_lands_one_commit_touching_only_its_file,
              test_multi_file_keeper_lands_one_commit_touching_both_files,
              test_multi_file_keeper_lands_only_the_owned_file_that_changed,
              test_a_keeper_command_that_cannot_run_exits_two_loudly,
              test_no_keeper_job_spells_the_landing_sequence_anymore,
              test_reaches_ci_through_the_makefile_only,
              test_a_stale_mergeable_index_repair_keeper_is_superseded_and_closed,
              test_a_current_mergeable_index_repair_keeper_is_live,
              test_the_supersede_guard_is_red_on_the_base_revision):
        t()
    if FAILURES:
        print(f"\n{len(FAILURES)} FAILURE(S):")
        for f in FAILURES:
            print(f"--- {f}")
        return 1
    print("\nkeeper_pr: all checks pass")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
