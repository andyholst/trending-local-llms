#!/usr/bin/env python3
"""Guard the report-only stale-claim sweep seam (issue #1610, #1626, #1265 design section 5 Child 1-2).

The DECISION is the real product: every test drives `stale_claim_sweep.sweep_thread` /
`sweep_threads` against gh-shaped payloads and asserts the exact marker lines. The external
`gh` CLI is stubbed only where a test must prove the REQUEST layer itself (`rule 6m`).

Child 2 pins both grace pairs as module constants with `Makefile ?=` overrides and floors,
names the three authority limits, and locks them with the same-age proof assertion.

Issue #1635 adds the `#1265` §3B half: the thin `gh` layer resolves each `R:<id>` /
`PR #<n>` the claim carries, a STILL-LIVE one is exempt from sweeping at any age, and a
CONCLUDED one keeps the doubled pair — proved end-to-end against a stub `gh`, both directions,
with a RED pin against an authentic pre-#1635 script fixture. That fixture is pinned in the tree
(`tests/fixtures/stale_claim_sweep_base_1635.py`, recorded from `origin/master` = `cb139e7c`):
reading it through `git show` in the container goes empty on a worktree whose `.git` points at a
host path, which made the negative assertion pass on an empty module (#1292 lesson).

RED half: the wiring checks read the REAL tree, so they fail on the base revision (no target,
no workflow step, no ARCHITECTURE.md row, no `master_alarm.GATES` entry); the Child 2 guards
fail on `origin/master`'s script, which carries neither the pinned live pair nor the limits,
and the §3B guard fails there because the shipped seam cannot exempt a still-live run.
"""
from __future__ import annotations

import importlib.util
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


def test_the_threshold_pairs_are_pinned_with_floors_and_makefile_overrides() -> None:
    print("\nPinned thresholds: two pairs, floors, and the Makefile ?= overrides (#1265 2a)")
    check("the SILENT pair is pinned at 90/180 minutes",
          (S.STALE_AFTER_SECONDS, S.RELEASE_AFTER_SECONDS) == (90 * 60, 180 * 60),
          (S.STALE_AFTER_SECONDS, S.RELEASE_AFTER_SECONDS))
    check("the LIVE-RUN pair is pinned at the doubled 180/360 minutes",
          (S.LIVE_RUN_STALE_SECONDS, S.LIVE_RUN_RELEASE_SECONDS)
          == (S.STALE_AFTER_SECONDS * S.LIVE_RUN_MULTIPLIER,
              S.RELEASE_AFTER_SECONDS * S.LIVE_RUN_MULTIPLIER)
          == (180 * 60, 360 * 60),
          (S.LIVE_RUN_STALE_SECONDS, S.LIVE_RUN_RELEASE_SECONDS))
    for label, value, floor in (
        ("silent stale", S.STALE_AFTER_SECONDS, S.STALE_FLOOR_SECONDS),
        ("silent release", S.RELEASE_AFTER_SECONDS, S.RELEASE_FLOOR_SECONDS),
        ("live-run stale", S.LIVE_RUN_STALE_SECONDS, S.LIVE_RUN_STALE_FLOOR_SECONDS),
        ("live-run release", S.LIVE_RUN_RELEASE_SECONDS, S.LIVE_RUN_RELEASE_FLOOR_SECONDS),
    ):
        check(f"the pinned {label} bound sits at or above its floor", value >= floor, (value, floor))
    makefile = (ROOT / "Makefile").read_text(encoding="utf-8")
    for knob, value in (
        ("STALE_CLAIM_STALE_SECONDS", S.STALE_AFTER_SECONDS),
        ("STALE_CLAIM_RELEASE_SECONDS", S.RELEASE_AFTER_SECONDS),
        ("STALE_CLAIM_LIVE_STALE_SECONDS", S.LIVE_RUN_STALE_SECONDS),
        ("STALE_CLAIM_LIVE_RELEASE_SECONDS", S.LIVE_RUN_RELEASE_SECONDS),
    ):
        check(f"the Makefile pins {knob} at the same seconds", f"{knob} ?= {value}" in makefile, "")
    check("the recipe forwards every override to the script",
          all(flag in makefile for flag in ("--stale-after", "--release-after",
                                           "--live-stale-after", "--live-release-after")), "")
    check("--check refuses a silent bound below its floor",
          S.main(["--check", "--stale-after", str(S.STALE_FLOOR_SECONDS - 1)]) == 2, "")
    check("--check refuses a live-run bound below its floor",
          S.main(["--check", "--live-stale-after", str(S.LIVE_RUN_STALE_FLOOR_SECONDS - 1)]) == 2, "")
    check("--check accepts the floors themselves",
          S.main(["--check", "--stale-after", str(S.STALE_FLOOR_SECONDS),
                  "--release-after", str(S.RELEASE_FLOOR_SECONDS),
                  "--live-stale-after", str(S.LIVE_RUN_STALE_FLOOR_SECONDS),
                  "--live-release-after", str(S.LIVE_RUN_RELEASE_FLOOR_SECONDS)]) == 0, "")


def test_the_three_authority_limits_emit_nothing_at_the_same_age() -> None:
    print("\nAuthority limits: human and live-run emit NO line at 120 min; a silent one does (#1265 3)")
    check("the three limits are named in ONE place",
          S.AUTHORITY_LIMITS == (S.REFUSAL_HUMAN, S.REFUSAL_LIVE_RUN, S.REFUSAL_TERMINAL)
          == ("human", "live-run", "terminal"), S.AUTHORITY_LIMITS)
    age = 120  # past the 90 min silent bound, short of the 180 min live-run bound
    silent = markers([claim_thread(minutes_ago=age)])
    human = markers([claim_thread(minutes_ago=age,
                                  body="BOT contractor · working on #1610 · branch b")])
    live_run = markers([claim_thread(minutes_ago=age,
                                     body=CLAIM.format(n=1610) + " — CI run R:45123456789")])
    open_pr = markers([claim_thread(minutes_ago=age,
                                    body=CLAIM.format(n=1610) + " — opened PR #1611")])
    terminal = markers([claim_thread(minutes_ago=age, state="closed")])
    check("a HUMAN claim at 120 min emits NO line", human == [], human)
    check("a LIVE-RUN claim at 120 min emits NO line (never swept under the silent bound)",
          live_run == [], live_run)
    check("an OPEN-PR claim at 120 min emits NO line (never swept under the silent bound)",
          open_pr == [], open_pr)
    check("a TERMINAL thread at 120 min emits NO line", terminal == [], terminal)
    check("a SILENT claim past the threshold DOES emit one stale line",
          len(silent) == 1 and silent[0].endswith(":stale"), silent)


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


def _liveness_stub(tmp: Path, *, body: str, created_at: str,
                   runs: dict | None = None, prs: dict | None = None,
                   newest: dict | None = None) -> Path:
    """A stub `gh` answering the thread AND the liveness reads (the external system only).

    `runs` maps a run id to its `status`; `prs` maps a PR number to `{state, headRefName}`;
    `newest` maps a branch to its newest-first run rows. An id the payload does not name is a
    LOUD exit 1, so a seam that asks for an unplanted run cannot pass silently.
    """
    payload = {
        "body": body,
        "createdAt": created_at,
        "runs": {str(key): value for key, value in (runs or {}).items()},
        "prs": {str(key): value for key, value in (prs or {}).items()},
        "newest": newest or {},
    }
    source = '''#!/usr/bin/env python3
import json, sys
ARGS = sys.argv[1:]
DATA = __DATA__
if ARGS[:2] == ["issue", "list"]:
    print(json.dumps([{"number": 1610}]))
elif ARGS[:2] == ["issue", "view"]:
    print(json.dumps({"number": 1610, "state": "OPEN", "comments": [{
        "id": 90001610, "author": {"login": "andyholst"},
        "createdAt": DATA["createdAt"], "body": DATA["body"]}]}))
elif ARGS[:2] == ["run", "view"]:
    status = DATA["runs"].get(ARGS[2])
    if status is None:
        sys.stderr.write("unknown run %s\\n" % ARGS[2]); sys.exit(1)
    print(json.dumps({"status": status,
                      "conclusion": "success" if status == "completed" else None}))
elif ARGS[:2] == ["pr", "view"]:
    pr = DATA["prs"].get(ARGS[2])
    if pr is None:
        sys.stderr.write("unknown pr %s\\n" % ARGS[2]); sys.exit(1)
    print(json.dumps(pr))
elif ARGS[:2] == ["run", "list"]:
    branch = ARGS[ARGS.index("--branch") + 1]
    rows = DATA["newest"].get(branch)
    if rows is None:
        sys.stderr.write("unknown branch %s\\n" % branch); sys.exit(1)
    print(json.dumps(rows))
else:
    sys.stderr.write("unexpected gh call: %s\\n" % ARGS); sys.exit(1)
'''.replace("__DATA__", repr(payload))
    stub = tmp / "gh-liveness"
    stub.write_text(source, encoding="utf-8")
    stub.chmod(0o755)
    return stub


def _created(minutes_ago: float) -> str:
    return (NOW - timedelta(minutes=minutes_ago)).strftime("%Y-%m-%dT%H:%M:%SZ")


def test_the_pure_decision_exempts_live_evidence_at_any_age() -> None:
    print("\nPure decision (#1265 §3B): live evidence emits nothing at ANY age")
    body = CLAIM.format(n=1610) + " — CI run R:45123456789"
    check("the run id is extracted from the claim text", S.extract_run_ids(body) == (45123456789,),
          S.extract_run_ids(body))
    check("the PR number is extracted from the claim text",
          S.extract_pr_numbers(CLAIM.format(n=1610) + " — opened PR #1611") == (1611,),
          S.extract_pr_numbers(CLAIM.format(n=1610) + " — opened PR #1611"))
    check("a queued or in_progress status is live", S.run_is_live("in_progress")
          and S.run_is_live("queued") and not S.run_is_live("completed"), "")
    for age in (181, 200, 360, 600, 1440):
        th = claim_thread(minutes_ago=age, body=body)
        check(f"live_evidence=True exempts a {age}-minute run-bearing claim",
              S.sweep_thread(th, now=NOW, lanes=LANES, live_evidence=True) == [],
              S.sweep_thread(th, now=NOW, lanes=LANES, live_evidence=True))
    th = claim_thread(minutes_ago=600, body=body)
    check("live_evidence=False keeps the doubled pair (released)",
          [v.kind for v in S.sweep_thread(th, now=NOW, lanes=LANES, live_evidence=False)] == ["released"],
          [v.kind for v in S.sweep_thread(th, now=NOW, lanes=LANES, live_evidence=False)])
    check("live_evidence=None (unresolved) keeps the doubled pair — nothing is silently exempted",
          [v.kind for v in S.sweep_thread(th, now=NOW, lanes=LANES)] == ["released"],
          [v.kind for v in S.sweep_thread(th, now=NOW, lanes=LANES)])
    check("a SILENT claim ignores live_evidence entirely",
          [v.kind for v in S.sweep_thread(claim_thread(minutes_ago=600), now=NOW,
                                          lanes=LANES, live_evidence=True)] == ["released"],
          "")


def test_a_still_live_run_is_exempt_and_a_concluded_one_keeps_the_doubled_pair() -> None:
    print("\nLive-run evidence end-to-end (#1265 §3B): stub gh only, BOTH directions")
    base = CLAIM.format(n=1610)
    cases = (
        ("an in_progress run id", base + " — CI run R:111", {"runs": {111: "in_progress"}},
         {}, {}, True),
        ("a queued run id", base + " — CI run R:112", {"runs": {112: "queued"}},
         {}, {}, True),
        ("a completed run id", base + " — CI run R:113", {"runs": {113: "completed"}},
         {}, {}, False),
        ("an OPEN PR whose newest run is in_progress",
         base + " — opened PR #1611", {},
         {"prs": {1611: {"state": "OPEN", "headRefName": "fix/live"}}},
         {"newest": {"fix/live": [{"databaseId": 9001, "status": "in_progress",
                                   "conclusion": None}]}}, True),
        ("an OPEN PR whose newest run is completed",
         base + " — opened PR #1612", {},
         {"prs": {1612: {"state": "OPEN", "headRefName": "fix/done"}}},
         {"newest": {"fix/done": [{"databaseId": 9002, "status": "completed",
                                   "conclusion": "success"}]}}, False),
        ("a MERGED PR", base + " — opened PR #1613", {},
         {"prs": {1613: {"state": "MERGED", "headRefName": "fix/merged"}}}, {}, False),
        ("an OPEN PR with no run at all", base + " — opened PR #1614", {},
         {"prs": {1614: {"state": "OPEN", "headRefName": "fix/empty"}}},
         {"newest": {"fix/empty": []}}, False),
    )
    for label, body, runs, prs, newest, live in cases:
        for age in (200, 400):  # past the live STALE bound, and past the live RELEASE bound
            with tempfile.TemporaryDirectory() as td:
                stub = _liveness_stub(Path(td), body=body, created_at=_created(age),
                                      runs=runs.get("runs"), prs=prs.get("prs"),
                                      newest=newest.get("newest"))
                threads = S.fetch_open_threads("o/r", str(stub))
                got = [v.marker() for v in S.sweep_threads(
                    threads, now=NOW, lanes=LANES,
                    live_resolver=S.liveness_resolver(repo="o/r", client=str(stub)))]
                if live:
                    check(f"{label} at {age} min (still LIVE) emits NOTHING", got == [], got)
                else:
                    kind = "released" if age >= 400 else "stale"
                    check(f"{label} at {age} min (concluded) keeps the doubled pair ({kind})",
                          len(got) == 1 and got[0].endswith(f":{kind}"), got)


def test_the_live_exemption_guard_is_red_on_the_base_revision() -> None:
    print("\nRED on the base head: the shipped seam cannot exempt a still-live run "
          "(authentic fixture recorded from origin/master)")
    body = CLAIM.format(n=1610) + " — CI run R:111"
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        stub = _liveness_stub(tmp, body=body, created_at=_created(400), runs={111: "in_progress"})
        threads = S.fetch_open_threads("o/r", str(stub))
        fixed = [v.marker() for v in S.sweep_threads(
            threads, now=NOW, lanes=LANES,
            live_resolver=S.liveness_resolver(repo="o/r", client=str(stub)))]
        check("this head exempts the still-live claim", fixed == [], fixed)

        # An authentic pre-#1635 script fixture, pinned in the tree. `git show origin/master:…`
        # answers EMPTY inside the test container for a linked worktree (the worktree's `.git`
        # points at a host path the container does not mount), which used to make this negative
        # assertion pass on an empty module (#1292/#1438 lesson).
        base_src = (ROOT / "tests" / "fixtures" / "stale_claim_sweep_base_1635.py").read_text(
            encoding="utf-8")
        check("the pre-change script fixture is non-empty", bool(base_src.strip()), "")
        check("RED: the pre-change script carries NO liveness seam",
              "claim_evidence_is_live" not in base_src and "liveness_resolver" not in base_src,
              "the base already resolves run/PR liveness")
        mod_path = tmp / "stale_base_1635.py"
        mod_path.write_text(base_src, encoding="utf-8")
        spec = importlib.util.spec_from_file_location("stale_base_1635", mod_path)
        assert spec is not None and spec.loader is not None, "the base script could not be loaded"
        base = importlib.util.module_from_spec(spec)
        # dataclasses resolves `cls.__module__` through sys.modules, so the module must be
        # REGISTERED before it executes (a bare module_from_spec leaves it absent).
        sys.modules[spec.name] = base
        spec.loader.exec_module(base)
        base_threads = base.fetch_open_threads("o/r", str(stub))
        old = [v.marker() for v in base.sweep_threads(base_threads, now=NOW, lanes=LANES)]
        check("RED: the base head reports the still-live claim (no exemption exists there)",
              len(old) == 1 and old[0].endswith(":released"), old)


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
    test_the_threshold_pairs_are_pinned_with_floors_and_makefile_overrides()
    test_the_three_authority_limits_emit_nothing_at_the_same_age()
    test_the_pure_decision_exempts_live_evidence_at_any_age()
    test_a_still_live_run_is_exempt_and_a_concluded_one_keeps_the_doubled_pair()
    test_the_live_exemption_guard_is_red_on_the_base_revision()
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
