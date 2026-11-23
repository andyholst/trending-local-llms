#!/usr/bin/env python3
"""Guard the repo-owned watch monitor (issue #1266).

The diffing code is the real product: tests feed it the same JSON shapes `gh` returns and
assert the exact markers. The external CLI is replaced only where a test must prove the
request-building itself (`test_branch_resolution_is_capped_and_never_guesses`, a stub `gh`
on PATH standing in for the network — rule 6m).
"""
from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import watch_monitor as W  # noqa: E402

_passed = 0
_failed = 0


def check(label: str, ok: bool, detail: str = "") -> None:
    global _passed, _failed
    if ok:
        _passed += 1
        print(f"  ok   {label}")
    else:
        _failed += 1
        print(f"  FAIL {label}" + (f"\n       {detail}" if detail else ""))


def payload(comment_id: int = 100, run_status: str = "completed", sha: str = "aaa",
            conclusion: str = "success") -> dict:
    return {
        "comments": {"issues": [{"id": comment_id}], "pulls": []},
        "runs": [{"id": 7, "status": run_status, "conclusion": conclusion}],
        "master": {"sha": sha},
    }


def test_quiet_tick_emits_nothing() -> None:
    print("\nQuiet tick: an unchanged snapshot wakes nobody")
    first, state = W.marker_state({}, payload())
    check("first tick establishes a baseline", "BASELINE" in first, str(first))
    again, state2 = W.marker_state(state, payload())
    check("no markers on an unchanged tick", again == [], str(again))
    check("state does not drift on a quiet tick", state2 == state, str(state2))
    check("no timestamps in any marker", all(not line[:1].isdigit() for line in first + again), "")


def test_new_comment_marker() -> None:
    print("\nComment trigger: only the new ID is emitted")
    _, state = W.marker_state({}, payload(comment_id=100))
    lines, state2 = W.marker_state(state, payload(comment_id=101))
    check("one new C marker", lines == ["C:101"], str(lines))
    check("cursor advances", state2["comments"]["issues"] == 101, str(state2["comments"]))
    _, state3 = W.marker_state(state2, payload(comment_id=101))
    check("the same comment is not re-emitted", state3 == state2, str(state3))


def test_ci_state_marker() -> None:
    print("\nCI trigger: a run that changes state is emitted once")
    _, state = W.marker_state({}, payload(run_status="in_progress"))
    lines, state2 = W.marker_state(state, payload(run_status="completed"))
    check("one R marker with status and conclusion", lines == ["R:7:completed:success"], str(lines))
    later, _ = W.marker_state(state2, payload(run_status="completed"))
    check("the same state is silent", later == [], str(later))


def test_master_merge_marker_and_rulebook_duty() -> None:
    print("\nMerge trigger: a new master head wakes the fleet to fetch/pull and sync")
    _, state = W.marker_state({}, payload(sha="aaa"))
    lines, _ = W.marker_state(state, payload(sha="bbb"))
    check("one M marker", lines == ["M:bbb"], str(lines))
    rules = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
    for needle in ("fetch", "pull", "AGENTS.md", "skills"):
        check(f"rule 6w names {needle}", needle in rules, "")


def test_rulebook_carries_two_job_watch_protocol() -> None:
    print("\nRulebook guard: the two-job watch protocol and its §8 row are pinned")
    rules = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
    for needle in ("6w.", "no-LLM monitor", "monitor-gated", "C:<comment", "R:<run", "M:<master",
                   "H:<", "oldest unclaimed", "do not stop at diagnosis"):
        check(f"rulebook carries {needle}", needle in rules, "")
    check("§8 guard row names the module",
          "tests/test_watch_monitor.py" in rules, "")
    makefile = (ROOT / "Makefile").read_text(encoding="utf-8")
    check("Makefile owns watch-monitor", "watch-monitor:" in makefile, "")
    workflow = (ROOT / ".github/workflows/qa-validate.yml").read_text(encoding="utf-8")
    check("qa-validate runs the offline check", "make watch-monitor CHECK=1" in workflow, "")


def test_heartbeat_marker_is_deterministic() -> None:
    print("\nHeartbeat: opt-in bucket marker, stable inside a bucket")
    check("no heartbeat by default", W.heartbeat_marker(0, now=100) is None, "")
    a = W.heartbeat_marker(900, now=100)
    b = W.heartbeat_marker(900, now=899)
    c = W.heartbeat_marker(900, now=900)
    check("same bucket is identical", a == b == "H:0", f"{a} {b}")
    check("boundary changes the marker", c == "H:1", str(c))
    check("no wall-clock timestamp in the marker", a is not None and a[2:].isdigit(), str(a))


def test_heartbeat_coexists_with_failure_marker() -> None:
    print("\nHeartbeat + failure: a red run is never swallowed by the heartbeat")
    _, state = W.marker_state({}, payload(conclusion="success"))
    lines, _ = W.marker_state(state, payload(run_status="completed", conclusion="failure"),
                              heartbeat_seconds=900, now=100)
    check("failure R marker survives", "R:7:completed:failure" in lines, str(lines))
    check("H marker is added", "H:0" in lines, str(lines))
    check("both are sorted and unique", lines == sorted(set(lines)), str(lines))


def test_r_marker_carries_workflow_name() -> None:
    print("\nCI marker names its workflow: guard/closure success != full validation (#1288)")
    p = {
        "comments": {"issues": [], "pulls": []},
        "runs": [
            {"id": 1, "status": "completed", "conclusion": "success", "name": "pr-closure"},
            {"id": 2, "status": "completed", "conclusion": "success", "name": "qa-validate"},
            {"id": 3, "status": "completed", "conclusion": "success", "name": "a:b\nc"},
        ],
        "master": {"sha": "aaa"},
    }
    lines, _ = W.marker_state({}, p)
    check("guard/closure success names its workflow",
          "R:1:completed:success:pr-closure" in lines, str(lines))
    check("full validation names its workflow",
          "R:2:completed:success:qa-validate" in lines, str(lines))
    assert "R:1:completed:success:pr-closure" in lines, str(lines)
    assert "R:2:completed:success:qa-validate" in lines, str(lines)
    check("the two bare-success rows are distinguishable from the marker alone",
          "R:1:completed:success:pr-closure" != "R:2:completed:success:qa-validate"
          and "R:1:completed:success:pr-closure" in lines
          and "R:2:completed:success:qa-validate" in lines, str(lines))
    check("a colon/newline in a name cannot add a marker field",
          "R:3:completed:success:abc" in lines, str(lines))
    assert "R:3:completed:success:abc" in lines, str(lines)
    check("a missing or blank name contributes no field",
          W.workflow_token(None) == "" and W.workflow_token("") == "", "")
    assert W.workflow_token(None) == "" and W.workflow_token("") == ""
    _, state = W.marker_state({}, payload(run_status="in_progress"))
    nameless, _ = W.marker_state(state, payload(run_status="completed"))
    check("a nameless run still emits the three-field marker",
          nameless == ["R:7:completed:success"], str(nameless))
    assert nameless == ["R:7:completed:success"], str(nameless)


def test_offline_check_mode() -> None:
    print("\nOffline check: no network, no state file")
    check("H is a legal marker prefix", "H:" in W.MARKER_PREFIXES, "")
    check("--check passes", W.main(["--check"]) == 0, "")


def test_the_rulebook_names_the_claim_settle_window() -> None:
    """Issue #1312: the wait-and-re-read race guard has a FLOOR, named in §7b and pinned once."""
    print("\nClaim settle window: the race guard has a floor (#1312)")
    rules = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
    needle = "a minimum settle window between a wake-up and a claim"
    check("§7b names the claim settle window", needle in rules, "")
    check("the rulebook names the ONE seam that carries the number",
          "CLAIM_SETTLE_SECONDS" in rules, "")
    check("the rulebook carries the window's value",
          f"{W.CLAIM_SETTLE_SECONDS} seconds" in rules, "")
    seam = (ROOT / "scripts" / "watch_monitor.py").read_text(encoding="utf-8")
    check("the window lives in the monitor seam, not a second copy",
          "CLAIM_SETTLE_SECONDS = " in seam, "")
    check("the pinned window is at least the floor",
          W.CLAIM_SETTLE_SECONDS >= W.CLAIM_SETTLE_FLOOR_SECONDS, "")
    check("the offline contract reports the pinned window",
          W.main(["--check"]) == 0, "")


def test_the_offline_contract_pins_the_settle_floor() -> None:
    """The floor is a real contract, driven through the real CLI (no product symbol rebound)."""
    print("\nOffline contract: a settle window below the floor is refused")
    check("a caller asking for a 30s window is refused",
          W.main(["--check", "--claim-settle-seconds", "30"]) != 0, "")
    check("a caller asking for the floor itself is accepted",
          W.main(["--check", "--claim-settle-seconds", str(W.CLAIM_SETTLE_FLOOR_SECONDS)]) == 0, "")
    check("the default is the pinned window",
          W.main(["--check", "--claim-settle-seconds", str(W.CLAIM_SETTLE_SECONDS)]) == 0, "")
def test_r_marker_carries_its_pull_request() -> None:
    """Issue #1284: an R marker names its PR, so a woken lane reads the right thread."""
    print("\nCI marker names its PR: the run's own pull_requests is carried (#1284)")
    p = {
        "comments": {"issues": [], "pulls": []},
        "runs": [{"id": 11, "status": "completed", "conclusion": "failure",
                  "name": "qa-validate", "pull_requests": [{"number": 1289}]}],
        "master": {"sha": "aaa"},
    }
    lines, _ = W.marker_state({}, p)
    check("a PR run's marker carries its PR number",
          "R:11:completed:failure:qa-validate:1289" in lines, str(lines))
    assert "R:11:completed:failure:qa-validate:1289" in lines, str(lines)
    check("the PR field is the LAST field, after the workflow token",
          "R:11:completed:failure:qa-validate:1289".split(":")[-1] == "1289", str(lines))
    check("a run with no pull_requests keeps the run-only shape",
          W.pull_token({"pull_requests": []}) == "" and W.pull_token({}) == "", "")
    check("a non-int PR entry contributes no field",
          W.pull_token({"pull_requests": [{"number": "1289"}]}) == ""
          and W.pull_token({"pull_requests": [None]}) == "", "")
    check("the PR field is a second state, so a new PR re-emits",
          W.pull_token({"pull_requests": [{"number": 1}]}) == "1", "")


def test_r_marker_keeps_its_pr_after_the_merge_clears_the_association() -> None:
    """Issue #1355: GitHub clears `pull_requests` once the PR merges; the marker keeps the PR.

    Measured 2026-11-23 on run `45085274450` (merged PR #1350's old head): the run's
    `pull_requests` answered `[]` after the merge, so a marker emitted then lost the field
    the lane needs to find the thread. The caller-owned `run_prs` map records the PR while
    the association is live and reuses it afterwards.
    """
    print("\nCI marker after a merge: the recorded run->PR map survives (#1355)")
    open_run = {
        "comments": {"issues": [], "pulls": []},
        "runs": [{"id": 45085274450, "status": "in_progress", "conclusion": None,
                  "name": "qa-validate", "pull_requests": [{"number": 1350}]}],
        "master": {"sha": "aaa"},
    }
    _, state = W.marker_state({}, open_run)
    check("the PR is recorded while the run is seen with its association live",
          state.get("run_prs", {}).get("45085274450") == "1350", str(state.get("run_prs")))
    merged_run = {
        "comments": {"issues": [], "pulls": []},
        "runs": [{"id": 45085274450, "status": "completed", "conclusion": "failure",
                  "name": "qa-validate", "pull_requests": []}],
        "master": {"sha": "aaa"},
    }
    lines, state2 = W.marker_state(state, merged_run)
    check("a post-merge tick still emits the PR field",
          "R:45085274450:completed:failure:qa-validate:1350" in lines, str(lines))
    assert "R:45085274450:completed:failure:qa-validate:1350" in lines, str(lines)
    check("the run->PR map is carried forward unchanged",
          state2["run_prs"]["45085274450"] == "1350", str(state2["run_prs"]))
    push = {
        "comments": {"issues": [], "pulls": []},
        "runs": [{"id": 99, "status": "completed", "conclusion": "success",
                  "name": "qa-validate", "pull_requests": []}],
        "master": {"sha": "aaa"},
    }
    lines2, state3 = W.marker_state(state2, push)
    check("a push run with no recorded PR keeps the shorter shape",
          "R:99:completed:success:qa-validate" in lines2, str(lines2))
    check("a push run is not written into the run->PR map",
          "99" not in state3["run_prs"], str(state3["run_prs"]))


def _stub_gh(tmp: Path) -> Path:
    """A stub `gh` CLI — the only permitted stand-in (the external system), not a product symbol.

    It answers the two comment query shapes the way GitHub really does: an unqualified
    `per_page=100` returns the 100 OLDEST comments (the bug #1360 measured), while an
    explicit `sort=created&direction=desc` returns the NEWEST 100, including a comment
    far newer than the old frozen cursor. Every request path is recorded for assertion.
    """
    log = tmp / "requests.log"
    source = '''#!/usr/bin/env python3
import json, sys
args = sys.argv[1:]
path = args[args.index("api") + 1] if "api" in args else ""
with open(__LOG__, "a", encoding="utf-8") as fh:
    fh.write(path + "\\n")
if "/comments?" in path:
    if "sort=created" in path and "direction=desc" in path:
        rows = [{"id": 7090680909}, {"id": 7090000000}] + [
            {"id": i} for i in range(6242933574, 6242933674)]
    else:
        rows = [{"id": i} for i in range(5942946574, 5942946674)]
    print(json.dumps(rows))
elif path.startswith("actions/runs"):
    print(json.dumps({"workflow_runs": []}))
elif path.startswith("commits/"):
    print(json.dumps({"sha": "aaa"}))
else:
    print(json.dumps([]))
'''.replace("__LOG__", repr(str(log)))
    stub = tmp / "gh-stub"
    stub.write_text(source, encoding="utf-8")
    stub.chmod(0o755)
    return stub


def test_comment_fetch_requests_newest_first() -> None:
    """Issue #1360: the real fetch must ask GitHub for newest-first comments."""
    print("\nComment fetch: the detector asks GitHub for newest-first comments (#1360)")
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        payload = W.fetch_payload("o/r", str(_stub_gh(tmp)))
        requests = (tmp / "requests.log").read_text(encoding="utf-8")
        check("the issue comment request pins descending order",
              "issues/comments?per_page=100&sort=created&direction=desc" in requests, requests)
        check("the PR comment request pins descending order",
              "pulls/comments?per_page=100&sort=created&direction=desc" in requests, requests)
        check("the newest comment is actually in the response",
              any(r.get("id") == 7090680909 for r in payload["comments"]["issues"]),
              str(payload["comments"]["issues"][:3]))
        assert "sort=created" in requests, requests
        assert "direction=desc" in requests, requests


def test_comment_fetch_sees_a_new_comment_outside_the_oldest_100() -> None:
    """Issue #1360: a comment newer than the 100th-oldest produces a real C marker."""
    print("\nComment trigger: a comment newer than the 100th-oldest wakes the lane (#1360)")
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        payload = W.fetch_payload("o/r", str(_stub_gh(tmp)))
        previous = {"comments": {"issues": 6242933673, "pulls": 6242933673},
                    "comments_v2": True}
        lines, state = W.marker_state(previous, payload)
        check("the new comment wakes the lane", "C:7090680909" in lines, str(lines))
        check("the stale oldest-100 backlog is not re-emitted",
              not any(i.startswith("C:59429") for i in lines), str(lines[:5]))
        check("cursor advances to the newest comment",
              state["comments"]["issues"] == 7090680909, str(state["comments"]))
        assert "C:7090680909" in lines, str(lines)


def test_comment_cursor_migration_baselines_without_flood() -> None:
    """Issue #1360: the first repaired tick seeds the cursor, it does not flood C markers."""
    print("\nCursor migration: the repair baselines instead of flooding stale markers (#1360)")
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        payload = W.fetch_payload("o/r", str(_stub_gh(tmp)))
        previous = {"comments": {"issues": 6242933673, "pulls": 0}}
        lines, state = W.marker_state(previous, payload)
        check("no stale backlog flood on the first repaired tick",
              not any(i.startswith("C:") for i in lines), str(lines[:8]))
        check("cursor is seeded to the newest comment",
              state["comments"]["issues"] == 7090680909, str(state["comments"]))
        check("the v2 cursor marker is recorded",
              state.get("comments_v2") is True, str(state))
        newer = dict(payload)
        newer["comments"] = dict(payload["comments"])
        newer["comments"]["issues"] = payload["comments"]["issues"] + [{"id": 7090680910}]
        lines2, _ = W.marker_state(state, newer)
        check("the next genuinely-new comment wakes the lane",
              lines2 == ["C:7090680910"], str(lines2))
        assert lines2 == ["C:7090680910"], str(lines2)
def test_r_marker_resolves_a_pr_first_seen_after_the_merge() -> None:
    """Issue #1364: a PR run whose FIRST sight is post-merge still names its PR.

    Measured 2026-11-23: `R:45116060775:completed:failure:qa-validate` carried no PR field for
    PR #1362's old head, because #1355's `run_prs` memo only records a run SEEN while its PR was
    open and this run's first sight was after the merge. `inject_run_prs` is the pure half that
    puts the merge-surviving resolution back into the row before the diff.
    """
    print("\nCI marker first seen after the merge: the branch resolves its PR (#1364)")
    first_sight = {
        "id": 45116060775, "status": "completed", "conclusion": "failure",
        "name": "qa-validate", "event": "pull_request",
        "head_branch": "ci/tech-debt-pr-rebase-soul-1361", "pull_requests": [],
    }
    enriched = W.inject_run_prs([first_sight], {"ci/tech-debt-pr-rebase-soul-1361": 1362})
    check("the resolved PR re-enters the run row as a one-element pull_requests",
          enriched[0]["pull_requests"] == [{"number": 1362}], str(enriched[0]))
    payload = {"comments": {"issues": [], "pulls": []}, "runs": enriched,
               "master": {"sha": "aaa"}}
    lines, state = W.marker_state({}, payload)
    check("the marker names the PR on its first sight",
          "R:45116060775:completed:failure:qa-validate:1362" in lines, str(lines))
    check("the resolution is recorded in the run->PR map",
          state.get("run_prs", {}).get("45116060775") == "1362", str(state.get("run_prs")))

    push_run = {"id": 7, "status": "completed", "conclusion": "success", "name": "qa-validate",
                "event": "push", "head_branch": "master", "pull_requests": []}
    untouched = W.inject_run_prs([push_run], {"master": 1})
    check("a push run is never given a PR", untouched[0]["pull_requests"] == [], str(untouched[0]))
    unknown = {"id": 8, "status": "completed", "conclusion": "success", "name": "qa-validate",
               "event": "pull_request", "head_branch": "nobody/resolved-this", "pull_requests": []}
    guessed = W.inject_run_prs([unknown], {})
    check("an unresolved branch is left alone, never guessed",
          guessed[0]["pull_requests"] == [], str(guessed[0]))
    live = {"id": 9, "status": "completed", "conclusion": "success", "name": "qa-validate",
            "event": "pull_request", "head_branch": "b", "pull_requests": [{"number": 5}]}
    kept = W.inject_run_prs([live], {"b": 6})
    check("a live association is not overwritten", kept[0]["pull_requests"] == [{"number": 5}],
          str(kept[0]))


def test_branch_resolution_is_capped_and_never_guesses() -> None:
    """The network half: one `gh pr list --head` per branch, capped, unique-only.

    The stub `gh` on PATH is the only stand-in (the external CLI, rule 6m); the request this
    seam builds and the JSON it accepts are the real product.
    """
    print("\nBranch->PR resolution: capped, unique, no guess on a failed read (#1364)")
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        calls = tmp_path / "calls"
        stub = tmp_path / "gh"
        stub.write_text(
            "#!/usr/bin/env python3\n"
            "import json, sys\n"
            f"open({str(calls)!r}, 'a').write('x')\n"
            "args = sys.argv[1:]\n"
            "branch = args[args.index('--head') + 1] if '--head' in args else ''\n"
            "if branch == 'ambiguous':\n"
            "    print(json.dumps([{'number': 1}, {'number': 2}]))\n"
            "elif branch == 'empty':\n"
            "    print(json.dumps([]))\n"
            "elif branch == 'broken':\n"
            "    sys.exit(1)\n"
            "else:\n"
            "    print(json.dumps([{'number': 1362}]))\n", encoding="utf-8")
        stub.chmod(0o755)
        resolved = W.resolve_branch_prs("andyholst/trending-local-llms", str(stub),
                                        ["ambiguous", "empty", "broken", "good"])
        check("an ambiguous branch resolves to nothing", "ambiguous" not in resolved, str(resolved))
        check("an empty branch list resolves to nothing", "empty" not in resolved, str(resolved))
        check("a failed read resolves to nothing", "broken" not in resolved, str(resolved))
        check("a unique merged PR resolves", resolved.get("good") == 1362, str(resolved))
        many = [f"branch-{i}" for i in range(W.PR_RESOLVE_MAX + 15)]
        calls.write_text("", encoding="utf-8")
        W.resolve_branch_prs("andyholst/trending-local-llms", str(stub), many)
        count = calls.read_text(encoding="utf-8").count("x")
    check("the per-tick resolution budget is honoured",
          count == W.PR_RESOLVE_MAX, f"calls={count} cap={W.PR_RESOLVE_MAX}")


def test_fetch_payload_keeps_the_explicit_gh_client() -> None:
    """The --gh path pinned by a cron wrapper must serve EVERY detector leg, not just api."""
    print("\nExplicit gh client: resolution never swaps in a second gh")
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        log = tmp / "clients.log"
        source = '''#!/usr/bin/env python3
import json, sys
args = sys.argv[1:]
with open(__LOG__, "a", encoding="utf-8") as fh:
    fh.write(__NAME__ + " | " + " ".join(args[:2]) + "\\n")
if "pr" in args[:2] and "list" in args:
    print(json.dumps([{"number": 1362}]))
elif "api" in args[:2]:
    path = args[args.index("api") + 1]
    if "actions/runs" in path:
        print(json.dumps({"workflow_runs": [{
            "id": 45116060775, "name": "qa-validate", "event": "pull_request",
            "status": "completed", "conclusion": "failure",
            "head_branch": "ci/tech-debt-pr-rebase-soul-1361", "head_sha": "abc",
            "pull_requests": []
        }]}))
    elif path.startswith("commits/"):
        print(json.dumps({"sha": "aaa"}))
    else:
        print(json.dumps([]))
else:
    print(json.dumps([]))
'''
        primary = tmp / "primary-gh"
        primary.write_text(source.replace("__LOG__", repr(str(log))).replace("__NAME__", repr("primary")),
                           encoding="utf-8")
        primary.chmod(0o755)
        sentinel = tmp / "sentinel-gh"
        sentinel.write_text(source.replace("__LOG__", repr(str(log))).replace("__NAME__", repr("sentinel")),
                            encoding="utf-8")
        sentinel.chmod(0o755)
        saved_path, saved_tll = os.environ.get("PATH", ""), os.environ.get("TLL_GH")
        bin_dir = tmp / "bin"
        bin_dir.mkdir()
        (bin_dir / "python3").symlink_to(sys.executable)
        try:
            os.environ["PATH"] = str(bin_dir)      # python3 only, no gh on PATH
            os.environ["TLL_GH"] = str(sentinel)   # a second gh the buggy code would pick up
            payload = W.fetch_payload("o/r", str(primary))
        finally:
            os.environ["PATH"] = saved_path
            if saved_tll is None:
                os.environ.pop("TLL_GH", None)
            else:
                os.environ["TLL_GH"] = saved_tll
        calls = log.read_text(encoding="utf-8")
        check("resolution never swaps in a second gh", "sentinel" not in calls, calls)
        check("the resolution leg ran on the explicit client",
              any(line.startswith("primary | pr list") for line in calls.splitlines()), calls)
        check("the PR was injected back into the run",
              any(r.get("pull_requests") for r in payload["runs"]), str(payload["runs"]))
        assert "sentinel" not in calls, calls


def test_the_rulebook_requires_filing_a_red_pipeline() -> None:
    """Issue #1376: a concluded-bad run is FILED, not only diagnosed.

    Measured: the #1371 flake reddened `validate` on every open PR and no issue was filed —
    the filer's only caller is the owner-dispatched `queued-alarm` sweep and rule 6t forbids a
    cron, so the duty belongs to the lane the `R:` marker wakes.
    """
    print("\nRulebook guard: the R: duty files a red main/PR pipeline (#1376)")
    rules = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
    for needle in ("make pipeline-failure-issue", "tll-implementer",
                   "a concluded-bad run is FILED", "on a PR pipeline is filed"):
        check(f"§6w names {needle!r}", needle in rules, "")
    for pipeline in ("qa-validate", "refresh-bot", "issue-bot", "issue-review-bot",
                     "architecture-bot", "queued-alarm"):
        check(f"§6w names the main pipeline {pipeline}", pipeline in rules, "")
    makefile = (ROOT / "Makefile").read_text(encoding="utf-8")
    check("the filer seam is a make target", "pipeline-failure-issue:" in makefile, "")


def main() -> int:
    test_quiet_tick_emits_nothing()
    test_fetch_payload_keeps_the_explicit_gh_client()
    test_new_comment_marker()
    test_ci_state_marker()
    test_master_merge_marker_and_rulebook_duty()
    test_rulebook_carries_two_job_watch_protocol()
    test_the_rulebook_requires_filing_a_red_pipeline()
    test_heartbeat_marker_is_deterministic()
    test_heartbeat_coexists_with_failure_marker()
    test_r_marker_carries_workflow_name()
    test_r_marker_carries_its_pull_request()
    test_r_marker_keeps_its_pr_after_the_merge_clears_the_association()
    test_comment_fetch_requests_newest_first()
    test_comment_fetch_sees_a_new_comment_outside_the_oldest_100()
    test_comment_cursor_migration_baselines_without_flood()
    test_r_marker_resolves_a_pr_first_seen_after_the_merge()
    test_branch_resolution_is_capped_and_never_guesses()
    test_offline_check_mode()
    test_the_rulebook_names_the_claim_settle_window()
    test_the_offline_contract_pins_the_settle_floor()
    print(f"\nPASSED {_passed} | FAILED {_failed}")
    return 0 if _failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
