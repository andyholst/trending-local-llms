#!/usr/bin/env python3
"""The tll lifecycle lives on the ISSUE thread and a host must match fetched master (issue #1209).

Every lane comments on the issue BEFORE it works; the planner reads those comments to
delegate; an implementer's PR hands over to the reviewer on the issue, not on the PR.
This module locks those shapes AND drives the real host-sync seam over a scratch home:
green on a synced tree, red on a planted byte-loss or a bad base. No stand-in for the
system under test -- the guard itself is executed.
"""
from __future__ import annotations

import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SEAM = ROOT / "scripts" / "fleet_host_sync_check.py"
LANES = (
    "tll-planner",
    "tll-architect",
    "tll-security",
    "tll-reviewer",
    "tll-implementer",
    "tll-tester",
    "tll-pr-rebase",
    "tll-docs",
)
BEFORE = "Comment on the issue BEFORE you do the work."
PR_SHAPE = "· pr #<id> · PR #<n> · base <sha> · handover tll-reviewer"
REVIEW_SHAPE = "· reviewing #<id> · PR #<n>"
PLANNER_READS = "The planner reads the issue comments to delegate accordingly."
AGENTS_SECTION = "TLL fleet — lifecycle, delegation and divergence gate"
FOLLOW_UP = "Always follow up on the issue"
#: Issue #1418: the host-ahead pitfall notes are LANDED, reconciled, in both mirrors.
HOST_AHEAD_HEADER = "## Host notes ahead of master"
HOST_TIMESTAMP = "20261123T140611Z"
HOST_NAME = "asimov@mac"
LANDED_HOST_AHEAD_NOTES = {
    "tll-planner": (
        "agents/tll-planner/skills/tll-planner/SKILL.md",
        (
            ("Bound lane concurrency", "#1416"),
            ('A PR with "no checks reported"', "#1115"),
            ("wiping Hermes runtime stamps", "#1401"),
            ("SUPERSEDE a filed `validate`/`openspec-index` failure", "#1412/#1413"),
            ("Verify a landed change against `origin/master`", "git rev-parse HEAD"),
            ("Lanes change locally and PUSH", "#1423"),
            ("separate WALL-CLOCK from CPU and count the containers", "docker ps"),
        ),
    ),
    "tll-implementer": (
        "agents/tll-implementer/skills/tll-implementer/SKILL.md",
        (
            ("`## Technical Solution` is a fast red in the `closure` job", "scripts/pr_body.py"),
            ("an OpenSpec index check on the MERGE TREE", "#1239"),
            ("force-push YOUR branch between your push and the merge", "#1398"),
            ("master-alarm routing sees only a BARE `make <target>` LINE", "master_alarm.py"),
            ("re-read the PR's live state", "state,mergedAt,mergeCommit"),
            ("OpenSpec LIFECYCLE gate", "#1434"),
            ("is RED in a local test-image run WITHOUT `GH_TOKEN`", "#972"),
        ),
    ),
}


def check(cond: bool, msg: str) -> int:
    if cond:
        print(f"ok   {msg}")
        return 0
    print(f"FAIL {msg}")
    return 1


def run_seam(*argv: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SEAM), *argv],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )


def scratch_home(dest: Path, repo: Path) -> None:
    for lane in LANES:
        src = ROOT / "agents" / lane
        (dest / lane / "skills" / lane).mkdir(parents=True)
        shutil.copyfile(src / "SOUL.md", dest / lane / "SOUL.md")
        shutil.copyfile(src / "config.yaml", dest / lane / "config.yaml")
        shutil.copyfile(
            src / "skills" / lane / "SKILL.md",
            dest / lane / "skills" / lane / "SKILL.md",
        )
    # The DEFAULT profile is a MERGE home at the profile home's PARENT (`~/.hermes/config.yaml`).
    # Plant the chain the BASE renders, so the seam has a synced default to accept.
    sys.path.insert(0, str(ROOT / "scripts"))
    import agent_model_chain as AMC

    chain, fatal = AMC.read_chain(repo)
    assert chain is not None, fatal
    (dest.parent / "config.yaml").write_text(AMC.render_text(chain), encoding="utf-8")


def test_every_lane_carries_the_pr_handover_shapes() -> int:
    failed = 0
    for lane in LANES:
        path = ROOT / "agents" / lane / "SOUL.md"
        text = path.read_text(encoding="utf-8") if path.is_file() else ""
        for needle, why in (
            (BEFORE, "comment-before-work"),
            (PR_SHAPE, "the PR-to-reviewer issue comment"),
            (REVIEW_SHAPE, "the reviewer's issue comment"),
            (PLANNER_READS, "the planner reads comments to delegate"),
            (FOLLOW_UP, "always follow up on the issue"),
        ):
            failed += check(needle in text, f"{lane}/SOUL.md carries {why}")
    return failed


def test_planner_skill_reads_the_comments() -> int:
    skill = ROOT / "agents" / "tll-planner" / "skills" / "tll-planner" / "SKILL.md"
    text = skill.read_text(encoding="utf-8")
    failed = check(BEFORE in text, "planner skill: comment before work")
    for needle, why in (
        ("Read before you dispatch.", "planner re-reads the thread"),
        ("answering <comment-id>", "dispatch names the comment it answers"),
        ("A PR is never the handover.", "PR is not the handover"),
        ("Always follow up on the issue.", "follow-up rule"),
    ):
        failed += check(needle in text, f"planner skill carries {why}")
    return failed


def test_the_lane_set_is_derived_and_the_new_lane_is_wired() -> int:
    """Issue #1396: a lane is DERIVED from `agents/tll-*/SOUL.md`, never a hand-kept list.

    The seam's `LANES`, the three guard lists and the fleet description must all carry the
    same set the tree derives — a lane added to the tree but missing from any of them is a
    lane the host-sync gate never compares, so its bytes can drift silently.
    """
    import sys as _sys

    _sys.path.insert(0, str(ROOT / "scripts"))
    import agent_model_chain as AMC

    failed = 0
    derived = set(AMC.fleet_lanes(ROOT))
    failed += check("tll-docs" in derived, "the tree derives the eighth lane `tll-docs`")
    failed += check(set(LANES) == derived, f"the guard's LANES equals the derived set ({sorted(derived)})")
    seam = (ROOT / "scripts" / "fleet_host_sync_check.py").read_text(encoding="utf-8")
    block = seam.split("LANES = (", 1)[1].split(")", 1)[0]
    failed += check(
        set(re.findall(r'"(tll-[a-z-]+)"', block)) == derived,
        "the seam's LANES tuple equals the derived set",
    )
    for rel in ("tests/test_fleet_handover_protocol.py", "tests/test_host_fleet_souls.py"):
        text = (ROOT / rel).read_text(encoding="utf-8")
        # A lane name also appears in prose (`handover tll-reviewer`), so read the
        # quoted spellings only: every derived lane must be a quoted list member.
        listed = set(re.findall(r'"(tll-[a-z-]+)"', text))
        # `tests/test_host_fleet_souls.py` asserts the forbidden-schedule shape on the
        # profiles it names; the lanes it must share with the other two lists are the
        # planner/architect/security/reviewer/implementer set, not the whole derived set.
        required = set(LANES) - {"tll-pr-rebase", "tll-tester"}
        missing = required - listed
        failed += check(
            not missing,
            f"{rel} lists every derived lane (missing {sorted(missing)})",
        )
    return failed


def test_reviewer_shapes_are_in_the_rulebook() -> int:
    text = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
    failed = check(AGENTS_SECTION in text, "AGENTS.md carries the tll fleet section")
    for needle, why in (
        (BEFORE, "comment-before-work"),
        (PR_SHAPE, "PR-to-reviewer shape"),
        (REVIEW_SHAPE, "reviewer shape"),
        (PLANNER_READS, "planner reads comments"),
        ("fleet-host-sync-check", "the host divergence gate"),
        ("tests/test_fleet_lifecycle.py", "the §8 guard row"),
    ):
        failed += check(needle in text, f"AGENTS.md carries {why}")
    return failed


def test_pr_rebase_skill_is_push_and_verify() -> int:
    """Issue #1427: the rebase skill's step 10 is push-and-verify, not a pre-push local gate.

    PR #1424 landed the owner directive (#1423) in the implementer/planner mirrors; this pins the
    same rule in the tll-pr-rebase mirror so no lane can regress to running the whole containerised
    suite on the host before pushing.
    """
    path = ROOT / "agents" / "tll-pr-rebase" / "skills" / "tll-pr-rebase" / "SKILL.md"
    text = path.read_text(encoding="utf-8") if path.is_file() else ""
    lines = [ln for ln in text.splitlines() if ln.strip().startswith("10.")]
    step = lines[0] if lines else ""
    failed = 0
    for needle, why in (
        ("make lint", "the fast offline check"),
        ("PUSH", "the push"),
        ("gh pr checks <n>", "the per-PR CI confirmation"),
        ("gh run view <id> --json jobs", "the run-jobs CI confirmation"),
        ("CI red at your head means the rebase is not done", "the red-head rule as a CI verdict"),
    ):
        failed += check(needle in step, f"pr-rebase skill step 10 carries {why}")
    for needle, why in (
        ("make validate", "the full validate"),
        ("make test", "the whole test suite"),
        ("closure", "closure"),
        ("guard", "guard"),
    ):
        failed += check(
            needle in step and "CI-ONLY" in step,
            f"pr-rebase skill step 10 names {why} CI-ONLY",
        )
    old = "**Gates before push**"
    failed += check(old not in step, "pr-rebase skill step 10 drops the pre-push local-gate heading")
    return failed


def scratch_repo(dest: Path) -> Path:
    """A REAL local git repo built from the tree — CI's checkout has no git objects."""
    repo = dest / "repo"
    repo.mkdir(parents=True)
    for lane in LANES:
        src = ROOT / "agents" / lane
        (repo / "agents" / lane / "skills" / lane).mkdir(parents=True)
        shutil.copyfile(src / "SOUL.md", repo / "agents" / lane / "SOUL.md")
        shutil.copyfile(src / "config.yaml", repo / "agents" / lane / "config.yaml")
        shutil.copyfile(
            src / "skills" / lane / "SKILL.md",
            repo / "agents" / lane / "skills" / lane / "SKILL.md",
        )
    shutil.copyfile(ROOT / "AGENTS.md", repo / "AGENTS.md")
    shutil.copyfile(ROOT / "agents" / "model_chain.json", repo / "agents" / "model_chain.json")
    shutil.copyfile(ROOT / "Makefile", repo / "Makefile")
    for argv in (
        ["git", "init", "-q"],
        ["git", "add", "-A"],
        ["git", "-c", "user.name=fleet-test", "-c", "user.email=fleet@example.invalid",
         "commit", "-q", "-m", "base"],
    ):
        subprocess.run(argv, cwd=repo, check=True, capture_output=True)
    return repo


def test_real_seam_accepts_a_synced_home() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        root = scratch_repo(Path(tmp))
        home = Path(tmp) / "profiles"
        home.mkdir()
        scratch_home(home, root)
        got = run_seam("--base", "HEAD", "--root", str(root), "--profiles-home", str(home))
        ok = check(got.returncode == 0, "real seam accepts a home synced at HEAD")
        ok += check(
            "the default profile's owned blocks" in got.stdout,
            "the acceptance line names the default profile's owned blocks",
        )
        print("      " + (got.stdout or got.stderr).strip().splitlines()[-1])
        return ok


def test_real_seam_refuses_a_diverged_default_profile() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        root = scratch_repo(Path(tmp))
        home = Path(tmp) / "profiles"
        home.mkdir()
        scratch_home(home, root)
        victim = home.parent / "config.yaml"
        text = victim.read_text(encoding="utf-8")
        # a retired provider shape: the exact drift issue #1297 measured on the host
        victim.write_text(
            text.replace("provider: nous", "provider: custom", 1)
            + "\nbase_url: http://127.0.0.1:8080/v1\n",
            encoding="utf-8",
        )
        got = run_seam("--base", "HEAD", "--root", str(root), "--profiles-home", str(home))
        failed = check(got.returncode == 1, "a drifted default profile is refused")
        failed += check(
            "profile=default" in got.stdout and "drifted from the rendered chain" in got.stdout,
            "the refusal names profile=default and the drifted block",
        )
        return failed


def test_real_seam_names_an_absent_default_profile() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        root = scratch_repo(Path(tmp))
        home = Path(tmp) / "profiles"
        home.mkdir()
        scratch_home(home, root)
        (home.parent / "config.yaml").unlink()
        got = run_seam("--base", "HEAD", "--root", str(root), "--profiles-home", str(home))
        failed = check(got.returncode == 0, "an absent default profile is not a divergence")
        failed += check(
            "SKIP" in got.stdout and "default profile" in got.stdout,
            "the absent default profile is NAMED, never a silent pass",
        )
        return failed


def test_real_seam_refuses_a_diverged_soul() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        root = scratch_repo(Path(tmp))
        home = Path(tmp) / "profiles"
        home.mkdir()
        scratch_home(home, root)
        victim = home / "tll-tester" / "SOUL.md"
        victim.write_bytes(victim.read_bytes()[:-1])  # one byte short
        got = run_seam("--base", "HEAD", "--root", str(root), "--profiles-home", str(home))
        failed = check(got.returncode == 1, "a one-byte drift is refused")
        failed += check(
            "tll-tester/SOUL.md" in got.stdout and "diverges from" in got.stdout,
            "the refusal names the lane and the file",
        )
        return failed


def test_real_seam_tolerates_hermes_runtime_stamps() -> int:
    """Issue #1401: Hermes's runtime stamps are host state, not fleet drift.

    The lane config's OWNED blocks are compared through the ONE drift verdict, so
    `_config_version`, `onboarding.seen` and a NOVEL stamp the fix never saw are all
    tolerated -- while a stale owned byte still reds, naming the lane's config.yaml, and
    `SOUL.md` / the lane skill stay byte-exact.
    """
    with tempfile.TemporaryDirectory() as tmp:
        root = scratch_repo(Path(tmp))
        home = Path(tmp) / "profiles"
        home.mkdir()
        scratch_home(home, root)
        victim = home / "tll-implementer" / "config.yaml"
        base = victim.read_bytes()

        failed = 0
        # Every Hermes-written block is host runtime state: the two measured stamps and a
        # NOVEL one (the whole point of owned-block comparison -- the next stamp is covered).
        for stamp in (
            b"_config_version: 54\n",
            b"onboarding:\n  seen:\n    tool_progress_prompt: true\n",
            b"some_future_stamp:\n  seen: true\n",
        ):
            victim.write_bytes(base + stamp)
            got = run_seam("--base", "HEAD", "--root", str(root), "--profiles-home", str(home))
            failed += check(
                got.returncode == 0,
                f"a planted {stamp.split(b':', 1)[0].decode()} stamp is tolerated",
            )
        print("      " + (got.stdout or got.stderr).strip().splitlines()[-1])

        # The teeth: a stale OWNED byte still reds, naming the lane's config.yaml.
        for block in (b"model", b"model_aliases", b"fallback_providers"):
            victim.write_bytes(base.replace(b"\n" + block + b":\n", b"\n" + block + b": stale\n", 1))
            got = run_seam("--base", "HEAD", "--root", str(root), "--profiles-home", str(home))
            failed += check(got.returncode == 1, f"a stale {block.decode()}: byte still reds")
            failed += check(
                "tll-implementer/config.yaml" in got.stdout and f"`{block.decode()}:`" in got.stdout,
                f"the refusal names tll-implementer/config.yaml and the {block.decode()}: block",
            )

        # The tolerance is config.yaml ONLY: the same blocks planted in SOUL.md are refused.
        soul = home / "tll-implementer" / "SOUL.md"
        soul_base = soul.read_bytes()
        for stamp in (
            b"\n_config_version: 54\n",
            b"\nonboarding:\n  seen:\n    tool_progress_prompt: true\n",
        ):
            soul.write_bytes(soul_base + stamp)
            got = run_seam("--base", "HEAD", "--root", str(root), "--profiles-home", str(home))
            failed += check(
                got.returncode == 1,
                f"a {stamp.strip().splitlines()[0].decode()} planted in SOUL.md is still refused",
            )
            failed += check(
                "tll-implementer/SOUL.md" in got.stdout and "diverges from" in got.stdout,
                "the SOUL.md refusal names the lane and the file",
            )

        # The lane skill stays byte-exact too.
        skill = home / "tll-implementer" / "skills" / "tll-implementer" / "SKILL.md"
        skill.write_bytes(skill.read_bytes()[:-1])  # one byte short
        got = run_seam("--base", "HEAD", "--root", str(root), "--profiles-home", str(home))
        failed += check(got.returncode == 1, "a one-byte lane-skill drift is refused")
        failed += check(
            "tll-implementer/skills/tll-implementer/SKILL.md" in got.stdout,
            "the skill refusal names the lane's SKILL.md",
        )
        return failed


def test_real_seam_refuses_a_bad_base() -> int:
    got = run_seam("--base", "no-such-ref-1209", "--root", str(ROOT))
    failed = check(got.returncode == 2, "an unresolvable base exits 2 (undecidable)")
    failed += check("REFUSED" in got.stdout, "the refusal is loud, not a silent clean")
    return failed


def test_ci_wires_the_guard_on_pr_and_push() -> int:
    workflow = (ROOT / ".github" / "workflows" / "qa-validate.yml").read_text(encoding="utf-8")
    makefile = (ROOT / "Makefile").read_text(encoding="utf-8")
    failed = check("pull_request:" in workflow, "qa-validate has a pull_request trigger")
    failed += check("\n  push:" in workflow, "qa-validate has a push trigger")
    failed += check("run: make test" in workflow, "qa-validate runs make test")
    failed += check(
        "run: make fleet-host-sync-check" in workflow,
        "qa-validate calls make fleet-host-sync-check",
    )
    failed += check(
        "fleet_host_sync_check.py" not in workflow,
        "no workflow reaches the script past the Makefile (rule 6m)",
    )
    failed += check("_fleet-host-sync-check:" in makefile, "Makefile defines the internal recipe")
    failed += check("fleet-host-sync-check: ##" in makefile, "Makefile defines the public target")
    runner = subprocess.run(
        ["bash", str(ROOT / "scripts" / "run_tests.sh"), "--list"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    failed += check(
        "test_fleet_lifecycle.py" in runner.stdout,
        "the ONE runner discovers this module (make test)",
    )
    return failed


def test_lane_skill_mirrors_carry_landed_host_ahead_notes() -> int:
    """Issue #1418: both lane mirrors carry the reconciled host-ahead pitfall notes.

    The host copies ran ahead of master with a `## Host notes ahead of master` section.
    They are landed here MERGED into each skill's own Pitfalls list — no timestamp
    header, no machine name — and every rule keeps its issue reference.
    """
    failed = 0
    for lane, (rel, notes) in LANDED_HOST_AHEAD_NOTES.items():
        text = (ROOT / rel).read_text(encoding="utf-8")
        pitfalls = text.split("## Pitfalls", 1)[-1].split("\n## ", 1)[0]
        for phrase, reference in notes:
            failed += check(phrase in pitfalls, f"{lane} skill's Pitfalls carry {phrase!r}")
            failed += check(reference in text, f"{lane} skill keeps the reference {reference!r}")
        failed += check(
            HOST_AHEAD_HEADER not in text, f"{lane} skill dropped the host timestamp header"
        )
        failed += check(HOST_TIMESTAMP not in text, f"{lane} skill dropped the host timestamp")
        failed += check(HOST_NAME not in text, f"{lane} skill dropped the machine name")
    return failed


def test_reviewer_skill_carries_landed_host_ahead_notes() -> int:
    """Issue #1432: the reviewer mirror carries the two reconciled host-ahead notes.

    The OpenSpec-lifecycle note is a numbered review step, not a pitfall bullet, so the
    whole-file check is deliberate: the reconciled notes keep their issue references and
    carry no host timestamp header, timestamp or machine name.
    """
    failed = 0
    text = (ROOT / "agents/tll-reviewer/skills/tll-reviewer/SKILL.md").read_text(encoding="utf-8")
    for phrase, reference in (
        ("A PR that closes an issue whose OpenSpec change is still ACTIVE", "#866"),
        ("a `test_*` listed TWICE in `main()`", "test_workflows.py"),
    ):
        failed += check(phrase in text, f"reviewer skill carries {phrase!r}")
        failed += check(reference in text, f"reviewer skill keeps the reference {reference!r}")
    failed += check(HOST_AHEAD_HEADER not in text, "reviewer skill dropped the host timestamp header")
    failed += check(HOST_TIMESTAMP not in text, "reviewer skill dropped the host timestamp")
    failed += check(HOST_NAME not in text, "reviewer skill dropped the machine name")
    return failed


def main() -> int:
    failed = 0
    for fn in (
        test_every_lane_carries_the_pr_handover_shapes,
        test_planner_skill_reads_the_comments,
        test_lane_skill_mirrors_carry_landed_host_ahead_notes,
        test_pr_rebase_skill_is_push_and_verify,
        test_reviewer_skill_carries_landed_host_ahead_notes,
        test_reviewer_shapes_are_in_the_rulebook,
        test_real_seam_accepts_a_synced_home,
        test_real_seam_refuses_a_diverged_soul,
        test_real_seam_tolerates_hermes_runtime_stamps,
        test_real_seam_refuses_a_diverged_default_profile,
        test_real_seam_names_an_absent_default_profile,
        test_real_seam_refuses_a_bad_base,
        test_ci_wires_the_guard_on_pr_and_push,
        test_the_lane_set_is_derived_and_the_new_lane_is_wired,
    ):
        failed += fn()
    if failed:
        print(f"FAIL {failed}")
        return 1
    print("ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
