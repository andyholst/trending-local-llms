#!/usr/bin/env python3
"""#1184: an auto-merge squash must never squash a head that moved after validation.

The seam is `scripts/auto_merge_head_check.py` (reached through
`make auto-merge-head-check`, run by qa-validate's `auto-merge` job IMMEDIATELY
before the squash). It re-reads the PR's `headRefOid` and compares it to the
event head the checks were green on:

  - same     -> `head_moved=false`, the merge proceeds;
  - moved    -> `head_moved=true`, names both SHAs, the workflow SKIPS the squash
                and the fresh pull_request run re-validates + merges the new head;
  - unreadable -> refuse too (never silently merge an unproven head).

Part 2 of #1184 (a 0-job `action_required` PR run reaching the alarm family) was
ALREADY landed by the #1115 fix (commit 92beb4d8, `ghost_verdict`), which predates
this issue; these tests do not duplicate that seam's coverage.

These tests drive the REAL script with a stub `gh` (the external GitHub API is
the only stand-in — rule 6m). No symbol under scripts/ is monkeypatched.

Run:  python3 tests/test_auto_merge_head_check.py   or   make test
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "scripts" / "auto_merge_head_check.py"
WORKFLOW = ROOT / ".github" / "workflows" / "qa-validate.yml"
MAKEFILE = ROOT / "Makefile"
sys.path.insert(0, str(ROOT / "scripts"))

import yaml  # noqa: E402

_PASS = 0
_FAIL = 0


def check(name: str, ok: bool, detail: str = "") -> None:
    global _PASS, _FAIL
    if ok:
        _PASS += 1
        print(f"ok - {name}")
    else:
        _FAIL += 1
        print(f"FAIL - {name}: {detail[:300]}")


#: A stub `gh` answering `pr view` from $FAKE_HEAD; every argv is recorded in
#: $GH_LOG so the request construction (field contract included) is asserted.
#: It emits the JSON OBJECT real `gh pr view --json headRefOid` emits — NOT a
#: --jq projection — so the seam's parse path is the production one (rule 6m).
STUB_GH = """#!/bin/sh
echo "gh $*" >> "$GH_LOG"
case "$1 $2" in
  "pr view") printf '{\"headRefOid\":\"%s\"}\\n' "$FAKE_HEAD" ;;
  *) echo "unexpected gh: $*" >&2; exit 3 ;;
esac
"""


def _stub_env(tmp: Path, head: str):
    d = tmp / "bin"
    d.mkdir(parents=True, exist_ok=True)
    gh = d / "gh"
    gh.write_text(STUB_GH)
    gh.chmod(0o755)
    log = tmp / "gh.log"
    env = dict(os.environ)
    env["PATH"] = f"{d}:{env['PATH']}"
    env["GH_LOG"] = str(log)
    env["FAKE_HEAD"] = head
    return env, log


def test_head_verdict_is_a_pure_case_insensitive_partition() -> None:
    import auto_merge_head_check as H
    check("the DECISION lives in the script, not the workflow shell (rule 6d)",
          callable(getattr(H, "head_verdict", None)), "")
    check("an identical head is same",
          H.head_verdict("abc123", "abc123") == "same", "")
    check("SHA comparison is case-insensitive",
          H.head_verdict("ABC123", "abc123") == "same", "")
    check("a moved head is moved",
          H.head_verdict("abc123", "def456") == "moved", "")
    check("an empty event or current SHA is unreadable, never same",
          H.head_verdict("", "abc") == "unreadable"
          and H.head_verdict("abc", "") == "unreadable", "")
    check("head_verdict never mutates its inputs (pure)",
          H.head_verdict("a", "b") in {"same", "moved", "unreadable"}, "")


def test_the_real_script_reads_the_head_through_the_field_contract() -> None:
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        env, log = _stub_env(tmp, "c9291dac4418d9ad519b3c46d75e3b20b3319f78")
        r = subprocess.run(
            [sys.executable, str(SCRIPT), "--pr", "1311", "--repo", "andyholst/trending-local-llms",
             "--event-head", "c9291dac4418d9ad519b3c46d75e3b20b3319f78"],
            capture_output=True, text=True, env=env, cwd=str(ROOT))
        calls = log.read_text() if log.exists() else ""
        check("same head -> head_moved=false and a clean pass",
              r.returncode == 0 and "head_moved=false" in r.stdout, r.stdout + r.stderr)
        check("the request is `gh pr view ... --json headRefOid` (contract, rule 6d)",
              "gh pr view 1311 --repo andyholst/trending-local-llms --json headRefOid" in calls,
              calls)


def test_a_moved_head_refuses_with_both_shas_and_skips_the_merge() -> None:
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        env, _ = _stub_env(tmp, "1111111111111111111111111111111111111111")
        r = subprocess.run(
            [sys.executable, str(SCRIPT), "--pr", "1311", "--repo", "andyholst/trending-local-llms",
             "--event-head", "2222222222222222222222222222222222222222"],
            capture_output=True, text=True, env=env, cwd=str(ROOT))
        check("moved head -> head_moved=true",
              r.returncode == 0 and "head_moved=true" in r.stdout, r.stdout + r.stderr)
        check("the refusal names BOTH the validated and current SHA",
              "2222222222222222" in r.stdout and "1111111111111111" in r.stdout, r.stdout)
        check("the refusal says the fresh run re-validates the new head",
              "re-validates" in r.stdout, r.stdout)


def test_an_unreadable_head_refuses_instead_of_a_silent_merge() -> None:
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        env, _ = _stub_env(tmp, "")
        r = subprocess.run(
            [sys.executable, str(SCRIPT), "--pr", "1311", "--repo", "andyholst/trending-local-llms",
             "--event-head", "2222222222222222222222222222222222222222"],
            capture_output=True, text=True, env=env, cwd=str(ROOT))
        check("unreadable head does not report head_moved=false",
              "head_moved=false" not in r.stdout, r.stdout)
        check("unreadable head names the refusal",
              "REFUSE" in r.stdout and "unreadable" in r.stdout, r.stdout)


def test_a_failed_gh_read_is_exit_2_not_a_silent_clean() -> None:
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        d = tmp / "bin"
        d.mkdir(parents=True, exist_ok=True)
        gh = d / "gh"
        gh.write_text("#!/bin/sh\necho 'gh failed' >&2\nexit 4\n")
        gh.chmod(0o755)
        env = dict(os.environ)
        env["PATH"] = f"{d}:{env['PATH']}"
        r = subprocess.run(
            [sys.executable, str(SCRIPT), "--pr", "1311",
             "--event-head", "2222222222222222222222222222222222222222"],
            capture_output=True, text=True, env=env, cwd=str(ROOT))
        check("failed read is exit 2 with READ FAILED (never a stale merge)",
              r.returncode == 2 and "READ FAILED" in r.stderr, r.stdout + r.stderr)


def test_read_head_parses_the_object_gh_really_emits() -> None:
    """The #1184 guard died in CI because `--jq` prints a BARE string and the
    seam json.loads'd it. Pin the object shape and the no---jq request."""
    import auto_merge_head_check as H

    class Obj:
        returncode = 0
        stdout = '{"headRefOid": "abc123def"}'
        stderr = ""

    seen = {}

    def fake(args, **kwargs):
        seen["args"] = list(args)
        return Obj()

    got = H.read_head("andyholst/trending-local-llms", "1311", gh=fake)
    check("a real gh --json object yields the bare SHA", got == "abc123def", got)
    check("the request asks for --json headRefOid with no --jq projection",
          "--json" in seen.get("args", []) and "--jq" not in seen.get("args", []),
          str(seen.get("args")))

    class Bare:
        returncode = 0
        stdout = "abc123def"  # what --jq used to print
        stderr = ""

    try:
        H.read_head("", "1311", gh=lambda args, **kwargs: Bare())
        check("a non-JSON (bare) answer is refused, never a green read", False,
              "no exception raised")
    except RuntimeError as exc:
        check("a non-JSON (bare) answer is refused, never a green read",
              "non-JSON" in str(exc), str(exc))


def test_the_workflow_guards_the_squash_on_a_moved_head() -> None:
    text = WORKFLOW.read_text()
    doc = yaml.safe_load(text)
    jobs = doc["jobs"]
    steps = jobs["auto-merge"]["steps"]
    head = [s for s in steps if s.get("id") == "head-check"]
    squash = [s for s in steps if s.get("name", "").startswith("Squash-merge")]
    check("qa-validate has a dedicated head-check step before the squash",
          len(head) == 1, "missing head-check step")
    check("the head-check calls the Makefile (rule 6m)",
          bool(head) and "make auto-merge-head-check" in head[0]["run"], "")
    check("the head-check passes the EVENT_HEAD the run validated",
          bool(head) and head[0].get("env", {}).get("EVENT_HEAD")
          == "${{ github.event.pull_request.head.sha }}", "")
    check("the head-check reads with the DEFAULT token, no owner PAT",
          bool(head) and head[0].get("env", {}).get("GH_TOKEN") == "${{ github.token }}", "")
    check("the squash step guards on head_moved (moved != true)",
          bool(squash) and "steps.head-check.outputs.moved != 'true'" in squash[0].get("if", ""),
          squash[0].get("if", "") if squash else "no squash step")
    check("the head-check step precedes the squash step",
          bool(head and squash) and steps.index(head[0]) < steps.index(squash[0]), "")


def test_the_target_is_wired_to_the_makefile() -> None:
    mk = MAKEFILE.read_text()
    check("make auto-merge-head-check is defined",
          "auto-merge-head-check:" in mk, "")
    check("its internal recipe calls the real script",
          "scripts/auto_merge_head_check.py" in mk, "")


def main() -> int:
    for t in [
        test_head_verdict_is_a_pure_case_insensitive_partition,
        test_the_real_script_reads_the_head_through_the_field_contract,
        test_a_moved_head_refuses_with_both_shas_and_skips_the_merge,
        test_an_unreadable_head_refuses_instead_of_a_silent_merge,
        test_a_failed_gh_read_is_exit_2_not_a_silent_clean,
        test_read_head_parses_the_object_gh_really_emits,
        test_the_workflow_guards_the_squash_on_a_moved_head,
        test_the_target_is_wired_to_the_makefile,
    ]:
        print(f"\n[{t.__name__}]")
        t()
    print(f"\n{os.path.basename(__file__)}: {_PASS} passed, {_FAIL} failed")
    return 1 if _FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
