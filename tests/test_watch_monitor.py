#!/usr/bin/env python3
"""Guard the repo-owned watch monitor (issue #1266).

The diffing code is the real product: tests feed it the same JSON shapes `gh` returns and
assert the exact markers. The external CLI itself is never replaced.
"""
from __future__ import annotations

import sys
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


def main() -> int:
    test_quiet_tick_emits_nothing()
    test_new_comment_marker()
    test_ci_state_marker()
    test_master_merge_marker_and_rulebook_duty()
    test_rulebook_carries_two_job_watch_protocol()
    test_heartbeat_marker_is_deterministic()
    test_heartbeat_coexists_with_failure_marker()
    test_r_marker_carries_workflow_name()
    test_offline_check_mode()
    test_the_rulebook_names_the_claim_settle_window()
    test_the_offline_contract_pins_the_settle_floor()
    print(f"\nPASSED {_passed} | FAILED {_failed}")
    return 0 if _failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
