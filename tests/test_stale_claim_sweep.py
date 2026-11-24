#!/usr/bin/env python3
"""Guard the report-only stale-claim sweep seam (issue #1610, #1265 design section 5 Child 1).

The DECISION is the real product: every test drives `stale_claim_sweep.sweep_thread` /
`sweep_threads` against gh-shaped payloads and asserts the exact marker lines. The external
`gh` CLI is stubbed only where a test must prove the REQUEST layer itself (`rule 6m`).

RED half: the wiring checks read the REAL tree, so they fail on the base revision (no target,
no workflow step, no ARCHITECTURE.md row, no `master_alarm.GATES` entry).
"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import stale_claim_sweep as S  # noqa: E402

PASSED = FAILED = 0
LANES = ("tll-planner", "tll-architect", "tll-security", "tll-reviewer",
         "tll-implementer", "tll-tester", "tll-pr-rebase", "tll-docs")

NOW = datetime(2026, 11, 24, 12, 0, 0, tzinfo=timezone.utc)


def check(label: str, ok: bool, detail: object = "") -> None:
    global PASSED, FAILED
    if ok:
        PASSED += 1
        print(f"  ok   {label}")
    else:
        FAILED += 1
        print(f"  FAIL {label}" + (f"\n       {detail}" if detail != "" else ""))


def comment(cid: int, minutes_ago: float, body: str, author: str = "andyholst") -> S.Comment:
    return S.Comment(id=cid, author=author, created_at=NOW - timedelta(minutes=minutes_ago), body=body)


def thread(number: int, comments: list[S.Comment], state: str = "open") -> S.Thread:
    return S.Thread(number=number, state=state, comments=tuple(comments))


CLAIM = ("BOT tll-implementer · working on #{n} · branch stale-claim-sweep-{n} · "
         "blocked on none · next land the seam")


def claim_thread(number: int = 1610, minutes_ago: float = 200, body: str | None = None,
                 state: str = "open", author: str = "andyholst") -> S.Thread:
    text = body if body is not None else CLAIM.format(n=number)
    return thread(number, [comment(9000 + number, minutes_ago, text, author)], state)


def markers(threads, **kwargs) -> list[str]:
    kwargs.setdefault("now", NOW)
    kwargs.setdefault("lanes", LANES)
    return [v.marker() for v in S.sweep_threads(threads, **kwargs)]


def test_a_silent_claim_under_the_threshold_is_not_reported() -> None:
    print("\nSilent claim under threshold: a fresh claim crosses nothing")
    check("a 60-minute silent claim is not reported", markers([claim_thread(minutes_ago=60)]) == [],
          markers([claim_thread(minutes_ago=60)]))
    check("the boundary is exclusive at the stale bound",
          markers([claim_thread(minutes_ago=89.9)]) == [], "")
    check("exactly the stale bound is stale",
          markers([claim_thread(minutes_ago=90)]) == [f"S:1610:{_id(claim_thread(1610, 90))}:stale"],
          markers([claim_thread(minutes_ago=90)]))


def _id(th: S.Thread) -> str:
    """The claim id of a one-comment fixture (recomputed through the SAME seam)."""
    c = th.comments[-1]
    return S.claim_token(c.author, c.created_at.isoformat(), th.number, c.body)


def test_a_silent_claim_over_the_threshold_reports_stale_then_released() -> None:
    print("\nSilent claim over threshold: PING at 90 min, release at 180 min")
    stale_line = f"S:1610:{_id(claim_thread(1610, 120))}:stale"
    released_line = f"S:1610:{_id(claim_thread(1610, 181))}:released"
    check("a 120-minute silent claim is stale", markers([claim_thread(minutes_ago=120)]) == [stale_line],
          markers([claim_thread(minutes_ago=120)]))
    check("an 181-minute silent claim is released",
          markers([claim_thread(minutes_ago=181)]) == [released_line],
          markers([claim_thread(minutes_ago=181)]))
    check("the release bound outranks the stale bound",
          "released" in markers([claim_thread(minutes_ago=180)])[0], markers([claim_thread(minutes_ago=180)]))


def test_a_run_bearing_claim_gets_the_doubled_bound() -> None:
    print("\nRun-bearing claim: CI consumes wall clock, so both bounds double (#1265 2a)")
    with_run = CLAIM.format(n=1610) + " — CI run R:45123456789"
    check("a 120-minute claim WITH a run id is still fresh (< 180)",
          markers([claim_thread(minutes_ago=120, body=with_run)]) == [],
          markers([claim_thread(minutes_ago=120, body=with_run)]))
    check("a 200-minute claim with a run id is stale (>= 180)",
          markers([claim_thread(minutes_ago=200, body=with_run)])
          == [f"S:1610:{_id(claim_thread(1610, 200, with_run))}:stale"],
          markers([claim_thread(minutes_ago=200, body=with_run)]))
    pr_run = CLAIM.format(n=1610) + " — opened PR #1611"
    check("a PR number counts as run evidence too",
          markers([claim_thread(minutes_ago=120, body=pr_run)]) == [],
          markers([claim_thread(minutes_ago=120, body=pr_run)]))
    check("a bare claim at the same age IS stale (the discriminator)",
          markers([claim_thread(minutes_ago=120)]) != [], "")


def test_a_human_claim_is_never_swept() -> None:
    print("\nHuman claim: the owner's claim is never stale (#1265 3A)")
    human = claim_thread(minutes_ago=500, body="asimov@omarchy · working on #1610 · branch x · next y")
    check("a host-signed note is not a BOT claim", markers([human]) == [], markers([human]))
    stranger = claim_thread(minutes_ago=500,
                            body="BOT contractor · working on #1610 · branch x · blocked on none · next y")
    check("a BOT line whose lane is not one of the eight is refused",
          markers([stranger]) == [], markers([stranger]))
    misnumbered = claim_thread(minutes_ago=500, body=CLAIM.format(n=9999))
    check("a claim naming a DIFFERENT issue is not this thread's claim",
          markers([misnumbered]) == [], markers([misnumbered]))
    stamped = claim_thread(minutes_ago=500,
                           body="BOT tll-implementer (host asimov@omarchy) · working on #1610 · branch b")
    check("the real host-suffixed claim shape is recognised",
          markers([stamped]) == [f"S:1610:{_id(stamped)}:released"], markers([stamped]))
    prefixed = claim_thread(minutes_ago=500,
                            body="asimov@omarchy · BOT tll-implementer · working on #1610 · branch b")
    check("the older machine-stamp-first claim shape is recognised",
          markers([prefixed]) == [f"S:1610:{_id(prefixed)}:released"], markers([prefixed]))


def test_a_terminal_thread_is_never_swept() -> None:
    print("\nTerminal thread: closed issue or a newer signed work comment (#1265 3C)")
    closed = claim_thread(minutes_ago=500, state="closed")
    check("a CLOSED issue yields nothing", markers([closed]) == [], markers([closed]))
    done = claim_thread(minutes_ago=500,
                        body="BOT tll-implementer · done #1610 · handover tll-reviewer · landed")
    check("a thread whose newest comment is done/handover is terminal", markers([done]) == [], markers([done]))
    pr = claim_thread(minutes_ago=500,
                      body="BOT tll-implementer · pr #1610 · PR #1612 · base abc · handover tll-reviewer")
    check("a thread whose newest comment is a pr handover is terminal", markers([pr]) == [], markers([pr]))
    status = claim_thread(minutes_ago=500,
                          body="BOT tll-implementer · status #1610 · asimov@omarchy · waiting on CI")
    check("a thread whose newest comment is a status note is not a live claim",
          markers([status]) == [], markers([status]))


def test_a_second_tick_does_not_re_report_the_same_claim() -> None:
    print("\nSecond tick: dedup is the caller's announced set, stable across ticks")
    th = claim_thread(minutes_ago=200)
    first = markers([th])
    check("the first tick reports the crossing", len(first) == 1, first)
    again = markers([th], announced=[S.claim_token(th.comments[-1].author,
                                                   th.comments[-1].created_at.isoformat(),
                                                   th.number, th.comments[-1].body)])
    check("the second tick with that claim id announced reports nothing", again == [], again)
    check("the claim id is stable across ticks",
          S.claim_token("andyholst", "2026-11-24T10:00:00+00:00", 1610, CLAIM.format(n=1610))
          == S.claim_token("andyholst", "2026-11-24T10:00:00+00:00", 1610, CLAIM.format(n=1610)),
          "")
    check("a different body changes the claim id",
          S.claim_token("a", "t", 1, "x") != S.claim_token("a", "t", 1, "y"), "")


def test_output_is_newest_last_and_one_line_per_claim() -> None:
    print("\nOutput contract: one line per claim, newest last")
    older = claim_thread(number=1001, minutes_ago=400)
    newer = claim_thread(number=1002, minutes_ago=100)
    lines = markers([newer, older])
    check("two crossings produce two lines", len(lines) == 2, lines)
    check("the oldest claim is printed first (newest-last)", lines[0].startswith("S:1001:")
          and lines[1].startswith("S:1002:"), lines)
    check("every line carries the S: prefix and a known verdict",
          all(line.startswith("S:") and line.rsplit(":", 1)[-1] in {"stale", "released"}
              for line in lines), lines)


def _stub_gh(tmp: Path, fail: str = "") -> Path:
    """A stub `gh` CLI — the only permitted stand-in (the external system), rule 6m."""
    source = '''#!/usr/bin/env python3
import json, sys
args = sys.argv[1:]
if "issue" in args[:2] and "list" in args[:3]:
    print(json.dumps([{"number": 1610}]))
elif "issue" in args[:2] and "view" in args[:3]:
    if __FAIL__:
        sys.exit(1)
    print(json.dumps({"number": 1610, "state": "OPEN", "comments": [{
        "id": 90001610, "author": {"login": "andyholst"},
        "createdAt": "2026-11-24T09:30:00Z",
        "body": "BOT tll-implementer · working on #1610 · branch b · blocked on none · next y"}]}))
else:
    sys.exit(1)
'''.replace("__FAIL__", repr(fail))
    stub = tmp / "gh-stub"
    stub.write_text(source, encoding="utf-8")
    stub.chmod(0o755)
    return stub


def test_the_real_request_layer_reads_a_thread_end_to_end() -> None:
    print("\ngh layer: the real fetch builds the request and parses the answer (stub gh only)")
    with tempfile.TemporaryDirectory() as td:
        stub = _stub_gh(Path(td))
        threads = S.fetch_open_threads("o/r", str(stub))
        check("one open issue was walked", len(threads) == 1, threads)
        check("the claim parsed out of the real row shape",
              S.parse_working_claim(threads[0].comments[-1].body) == ("tll-implementer", 1610),
              threads[0].comments[-1].body)
        now = datetime(2026, 11, 24, 12, 0, 0, tzinfo=timezone.utc)
        lines = [v.marker() for v in S.sweep_threads(threads, now=now, lanes=LANES)]
        check("a 150-minute claim is stale through the whole path", lines == [
            f"S:1610:{S.claim_token('andyholst', '2026-11-24T09:30:00+00:00', 1610, threads[0].comments[-1].body)}:stale"],
            lines)


def test_an_unreadable_thread_exits_2_loudly() -> None:
    print("\nUnreadable thread: a partial report would read as 'nothing is stale'")
    with tempfile.TemporaryDirectory() as td:
        stub = _stub_gh(Path(td), fail="view")
        proc = subprocess.run([sys.executable, str(ROOT / "scripts" / "stale_claim_sweep.py"),
                               "--repo", "o/r", "--gh", str(stub)],
                              capture_output=True, text=True)
        check("the CLI exits 2", proc.returncode == 2, (proc.returncode, proc.stdout, proc.stderr))
        check("the failure is named, never a silent clean", "READ FAILED" in proc.stderr, proc.stderr)
        check("nothing was printed as a verdict", "S:" not in proc.stdout, proc.stdout)


def test_the_offline_contract_needs_no_network() -> None:
    print("\nOffline contract: CHECK=1 proves the grammar and the grace pair")
    check("--check exits 0", S.main(["--check"]) == 0, "")
    out = _stdout_of(["--check"])
    check("--check writes no verdict line", not any(line.startswith("S:") for line in out.splitlines()), out)
    check("a disordered grace pair is refused", S.main(["--check", "--stale-after", "200",
                                                       "--release-after", "100"]) == 2, "")
    check("a zero grace is refused", S.main(["--check", "--stale-after", "0"]) == 2, "")


def _stdout_of(argv: list[str]) -> str:
    import io
    import contextlib
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        S.main(argv)
    return buf.getvalue()


def test_the_tree_wiring_is_complete() -> None:
    print("\nWiring: the target, its CI caller, the description rows and the alarm registry")
    makefile = (ROOT / "Makefile").read_text(encoding="utf-8")
    check("make stale-claim-sweep is a target", "stale-claim-sweep:" in makefile, "")
    check("the internal recipe runs the script",
          "python3 scripts/stale_claim_sweep.py" in makefile, "")
    workflow = (ROOT / ".github" / "workflows" / "qa-validate.yml").read_text(encoding="utf-8")
    check("qa-validate runs the offline contract beside watch-monitor",
          "make watch-monitor CHECK=1" in workflow and "make stale-claim-sweep CHECK=1" in workflow, "")
    doc = (ROOT / "ARCHITECTURE.md").read_text(encoding="utf-8")
    check("ARCHITECTURE.md describes the target", "`stale-claim-sweep`" in doc, "")
    check("ARCHITECTURE.md carries a §6 script row",
          "`scripts/stale_claim_sweep.py`" in doc, "")
    sys.path.insert(0, str(ROOT / "scripts"))
    import master_alarm
    check("master_alarm.GATES names the new validate gate",
          master_alarm.GATES.get("stale-claim-sweep", ("", ""))[1] == "master-alarm",
          master_alarm.GATES.get("stale-claim-sweep"))
    exceptions = (ROOT / "scripts" / "check_no_bare_host_python.py").read_text(encoding="utf-8")
    check("the host-side exception list carries the target (bare python3 recipe)",
          '"stale-claim-sweep":' in exceptions, "")


def main() -> int:
    test_a_silent_claim_under_the_threshold_is_not_reported()
    test_a_silent_claim_over_the_threshold_reports_stale_then_released()
    test_a_run_bearing_claim_gets_the_doubled_bound()
    test_a_human_claim_is_never_swept()
    test_a_terminal_thread_is_never_swept()
    test_a_second_tick_does_not_re_report_the_same_claim()
    test_output_is_newest_last_and_one_line_per_claim()
    test_the_real_request_layer_reads_a_thread_end_to_end()
    test_an_unreadable_thread_exits_2_loudly()
    test_the_offline_contract_needs_no_network()
    test_the_tree_wiring_is_complete()
    print(f"\nPASSED {PASSED} | FAILED {FAILED}")
    return 1 if FAILED else 0


if __name__ == "__main__":
    sys.exit(main())
