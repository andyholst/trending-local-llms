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


def payload(comment_id: int = 100, run_status: str = "completed", sha: str = "aaa") -> dict:
    return {
        "comments": {"issues": [{"id": comment_id}], "pulls": []},
        "runs": [{"id": 7, "status": run_status, "conclusion": "success"}],
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
    for needle in ("6w.", "no-LLM monitor", "monitor-gated", "C:<comment", "R:<run", "M:<master"):
        check(f"rulebook carries {needle}", needle in rules, "")
    check("§8 guard row names the module",
          "tests/test_watch_monitor.py" in rules, "")
    makefile = (ROOT / "Makefile").read_text(encoding="utf-8")
    check("Makefile owns watch-monitor", "watch-monitor:" in makefile, "")
    workflow = (ROOT / ".github/workflows/qa-validate.yml").read_text(encoding="utf-8")
    check("qa-validate runs the offline check", "make watch-monitor CHECK=1" in workflow, "")


def test_offline_check_mode() -> None:
    print("\nOffline check: no network, no state file")
    check("--check passes", W.main(["--check"]) == 0, "")


def main() -> int:
    test_quiet_tick_emits_nothing()
    test_new_comment_marker()
    test_ci_state_marker()
    test_master_merge_marker_and_rulebook_duty()
    test_rulebook_carries_two_job_watch_protocol()
    test_offline_check_mode()
    print(f"\nPASSED {_passed} | FAILED {_failed}")
    return 0 if _failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
