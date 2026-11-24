#!/usr/bin/env python3
"""The dispatch guard's proof (issue #1416) — offline, fixture-driven, real logic.

The measured defect: 7 concurrent lanes on one host (load 7.08, one shared VM at 348% CPU),
including a 95-min lane on #1239 — already CLOSED, its PR #1242 already MERGED. Nothing
refused the dispatch and nothing bounded concurrency.

This suite runs the REAL guard (`scripts/dispatch_guard.py`) end to end over RECORDED
fixtures, through both its importable decisions and its CLI and the `make dispatch-check`
target — exactly what a planner consults before spawning a lane. The fixtures are local
JSON files with NO network and NO credential values (only an issue's state, a bound PR's
number/state, and a caller-owned active-lane count). No business logic is mocked: the
only stand-in is the EXTERNAL `gh` call, replaced by a recorded payload through the
guard's own documented `--from-file` seam (rule 6m).

The dispatch guard also serialises SHARED FILES (issue #1458): `--claim <repo-relative
path>` (repeatable, or `CLAIMS=`) refuses when another ACTIVE registry lane already claims
an overlapping path, naming the holder, while a FINISHED lane does not block and a claim-free
invocation behaves exactly as it did before.

Issue #1569 adds the CROSS-HOST half: `make dispatch-check` reads the ISSUE THREAD (the one
surface every host shares) and refuses when ANOTHER host holds a NEWER ACTIVE working-claim,
naming the holding host, lane and comment id. These tests run the REAL parser over RECORDED
threads through `--comments-file`/`--from-file` — offline, no network, no credential values.

Run:  python3 tests/test_dispatch_guard.py   or   make test
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import dispatch_guard as D  # noqa: E402  (the ONE implementation, rule 6d)

_PASS = 0
_FAIL = 0


def check(name: str, ok: bool, detail: str = "") -> None:
    global _PASS, _FAIL
    if ok:
        _PASS += 1
        print(f"  ok   {name}")
    else:
        _FAIL += 1
        print(f"  FAIL {name}" + (f"\n       {detail}" if detail else ""))


def state_file(tmp: Path, name: str, state: str, bound: list[dict]) -> Path:
    """The fixture seam: a recorded issue/PR payload (the shape gh-derived state has)."""
    path = tmp / name
    path.write_text(json.dumps({"state": state, "bound_prs": bound}), encoding="utf-8")
    return path


def registry(tmp: Path, name: str, count: int) -> Path:
    """A CALLER-OWNED registry outside the repository (tempdir sibling, never in-tree)."""
    path = tmp / name
    path.write_text(json.dumps({D.REGISTRY_COUNT_KEY: count}), encoding="utf-8")
    return path


def registry_with_lanes(tmp: Path, name: str, count: int, lanes) -> Path:
    """The #1458 registry shape: the count plus each lane's ACTIVE/FINISHED claims."""
    path = tmp / name
    payload = {D.REGISTRY_COUNT_KEY: count}
    if lanes is not None:
        payload[D.REGISTRY_LANES_KEY] = lanes
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


# ---------------------------------------------------------------------------- pure
def test_open_issue_is_allowed() -> None:
    print("\nOpen issue: allowed")
    v = D.evaluate({"issue": "1416", "state": "OPEN", "bound_prs": []}, 0, 3)
    check("open issue, no bound PR, no lanes -> ALLOW", v["verdict"] == "allow" and not v["reasons"], str(v))
    check("the count is always reported", v["active_lanes"] == 0 and v["ceiling"] == 3, str(v))


def test_closed_issue_is_refused() -> None:
    print("\nClosed issue: refused with a clear reason")
    v = D.evaluate({"issue": "1239", "state": "CLOSED", "bound_prs": []}, 0, 3)
    check("CLOSED -> REFUSE", v["verdict"] == "refuse", str(v))
    check("the reason says CLOSED", any("CLOSED" in r for r in v["reasons"]), str(v["reasons"]))


def test_merged_bound_pr_is_refused() -> None:
    print("\nMerged bound PR: refused even when the issue itself reads OPEN")
    v = D.evaluate({
        "issue": "1239", "state": "OPEN",
        "bound_prs": [{"number": 1242, "state": "MERGED", "mergedAt": "2026-11-23T13:19:42Z"}],
    }, 0, 3)
    check("MERGED bound PR -> REFUSE", v["verdict"] == "refuse", str(v))
    check("the reason names PR #1242 and its merge", any(
        "1242" in r and "MERGED" in r for r in v["reasons"]), str(v["reasons"]))


def test_concurrency_bound_is_one_constant() -> None:
    print("\nConcurrency: at the ceiling ok, over the ceiling refused")
    check("the ONE default ceiling is 3", D.ACTIVE_LANE_CEILING == 3, str(D.ACTIVE_LANE_CEILING))
    at = D.evaluate({"state": "OPEN", "bound_prs": []}, 3, D.ACTIVE_LANE_CEILING)
    check("3/3 (at the ceiling) -> ALLOW", at["verdict"] == "allow" and at["active_lanes"] == 3, str(at))
    under = D.evaluate({"state": "OPEN", "bound_prs": []}, 2, D.ACTIVE_LANE_CEILING)
    check("2/3 (under) -> ALLOW", under["verdict"] == "allow", str(under))
    over = D.evaluate({"state": "OPEN", "bound_prs": []}, 4, D.ACTIVE_LANE_CEILING)
    check("4/3 (over) -> REFUSE", over["verdict"] == "refuse", str(over))
    check("the reason reports BOTH the count and the ceiling",
          any("4" in r and "3" in r and "ABOVE" in r for r in over["reasons"]), str(over["reasons"]))
    check("the report prints the count for EVERY verdict",
          "active_lanes=4/3" in D.render(over) and "active_lanes=3/3" in D.render(at),
          D.render(over) + "\n" + D.render(at))


def test_registry_is_caller_owned_and_lives_outside_the_repo() -> None:
    print("\nRegistry: outside the repository, deterministic count")
    with tempfile.TemporaryDirectory(prefix="dispatch-reg-") as td:
        root = Path(td)
        reg = registry(root, "lanes.json", 4)
        check("a caller-owned registry counts its lanes", D.active_lane_count(reg) == 4)
        inside, why = D.resolve_registry("./lanes.json")
        check("an IN-REPO registry is refused", inside is None and "inside the repository" in why, why)
        outside, why = D.resolve_registry(str(reg))
        check("an outside registry resolves", outside == reg.resolve() and not why, str((outside, why)))
        absent = root / "absent.json"
        check("an absent registry means 0 lanes", D.active_lane_count(absent) == 0)


# ---------------------------------------------------------------------------- CLI
def _cli(tmp: Path, name: str, state: str, bound: list[dict], count: int) -> tuple[int, str]:
    fixture = state_file(tmp, name, state, bound)
    reg = registry(tmp, name + ".registry.json", count)
    proc = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "dispatch_guard.py"), "--issue", "1416",
         "--registry", str(reg), "--from-file", str(fixture)],
        capture_output=True, text=True, cwd=ROOT,
    )
    return proc.returncode, proc.stdout + proc.stderr


def test_cli_exit_codes_over_recorded_fixtures() -> None:
    print("\nCLI: real script, real recorded fixtures, no network")
    with tempfile.TemporaryDirectory(prefix="dispatch-cli-") as td:
        tmp = Path(td)
        rc, out = _cli(tmp, "open.json", "OPEN", [], 0)
        check("open issue: exit 0", rc == 0, out)
        check("open issue: reports ALLOW and the count", "ALLOW" in out and "active_lanes=0/3" in out, out)

        rc, out = _cli(tmp, "closed.json", "CLOSED", [], 0)
        check("closed issue: exit NON-ZERO", rc != 0, out)
        check("closed issue: the reason is on stdout", "REFUSE" in out and "CLOSED" in out, out)

        rc, out = _cli(tmp, "merged.json", "OPEN", [
            {"number": 1242, "state": "MERGED", "mergedAt": "2026-11-23T13:19:42Z"}], 0)
        check("merged bound PR: exit NON-ZERO", rc != 0, out)
        check("merged bound PR: names the PR and merge", "1242" in out and "MERGED" in out, out)

        rc, out = _cli(tmp, "at.json", "OPEN", [], 3)
        check("at the ceiling: exit 0", rc == 0, out)
        rc, out = _cli(tmp, "over.json", "OPEN", [], 4)
        check("over the ceiling: exit NON-ZERO", rc != 0, out)
        check("over: prints the count and ceiling", "active_lanes=4/3" in out, out)


def test_help_documents_the_registry_and_the_ceiling() -> None:
    print("\n--help: the registry path and the ceiling are documented")
    proc = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "dispatch_guard.py"), "--help"],
        capture_output=True, text=True, cwd=ROOT,
    )
    text = proc.stdout + proc.stderr
    check("--help: exit 0", proc.returncode == 0, text[-300:])
    check("--help: names --registry", "--registry" in text, text[-600:])
    check("--help: names the default ceiling 3", "ACTIVE_LANE_CEILING = 3" in text, text[-600:])
    check("--help: says the registry lives OUTSIDE the repository",
          "OUTSIDE the repository" in text, text[-600:])


# ---------------------------------------------------------------------------- make
def test_make_dispatch_check_is_the_callers_single_seam() -> None:
    print("\nmake dispatch-check: the planner's single seam, non-zero on refusal")
    mk = (ROOT / "Makefile").read_text(encoding="utf-8")
    check("Makefile: dispatch-check has a ## description and a recipe",
          "\ndispatch-check: ##" in mk and "scripts/dispatch_guard.py" in mk, "")
    check("Makefile: the recipe forwards ISSUE and REGISTRY",
          "--issue \"$(ISSUE)\"" in mk and "--registry " in mk, "")
    check("Makefile: no second ceiling constant (it is forwarded as --ceiling)",
          "--ceiling \"$(if $(CEILING),$(CEILING),3)\"" in mk, "")

    with tempfile.TemporaryDirectory(prefix="dispatch-make-") as td:
        tmp = Path(td)
        fixture = state_file(tmp, "state.json", "CLOSED", [])
        reg = registry(tmp, "lanes.json", 0)
        proc = subprocess.run(
            ["make", "dispatch-check", f"ISSUE=1239", f"REGISTRY={reg}",
             f"FROM_FILE={fixture}"],
            capture_output=True, text=True, cwd=ROOT,
        )
        out = proc.stdout + proc.stderr
        check("make dispatch-check: a CLOSED issue makes the target non-zero",
              proc.returncode != 0, out)
        check("make dispatch-check: the refusal reason reaches the caller",
              "REFUSE" in out and "CLOSED" in out, out)

        fixture2 = state_file(tmp, "open.json", "OPEN", [])
        proc = subprocess.run(
            ["make", "dispatch-check", "ISSUE=1416", f"REGISTRY={reg}",
             f"FROM_FILE={fixture2}"],
            capture_output=True, text=True, cwd=ROOT,
        )
        check("make dispatch-check: an open issue exits 0",
              proc.returncode == 0, proc.stdout + proc.stderr)


# ---------------------------------------------------------------------------- claims (#1458)
def test_claim_paths_and_registry_rows_are_normalized() -> None:
    print("\nClaims: repo-relative paths and registry rows normalize")
    check("a plain path is unchanged", D.normalize_repo_path("agents/x/SKILL.md") == ("agents/x/SKILL.md", ""))
    check("leading ./ and empty segments collapse",
          D.normalize_repo_path("./agents//x/./SKILL.md") == ("agents/x/SKILL.md", ""), "")
    for bad, why in [
        ("/Users/andy/repository/git/trending-local-llms/agents/x", "REPO-RELATIVE"),
        ("~/agents/x", "REPO-RELATIVE"),
        ("../outside", "escapes the repository"),
        ("", "empty"),
    ]:
        norm, refusal = D.normalize_repo_path(bad)
        check(f"an unusable claim ({bad!r}) is refused with a reason",
              norm == "" and why in refusal, str((norm, refusal)))
    check("exact paths overlap", D.paths_overlap("agents/x/SKILL.md", "agents/x/SKILL.md"))
    check("a directory overlaps the file under it",
          D.paths_overlap("agents/x", "agents/x/SKILL.md"))
    check("a sibling with a shared prefix does NOT overlap",
          not D.paths_overlap("agents/x", "agents/x2"), "")

    with tempfile.TemporaryDirectory(prefix="dispatch-lanes-") as td:
        root = Path(td)
        rows = registry_with_lanes(root, "lanes.json", 2, [
            {"lane": "tll-planner", "state": "active",
             "claims": ["agents/tll-planner/skills/tll-planner/SKILL.md"]},
            {"name": "tll-docs", "status": "finished", "claims": ["docs/README.md"]},
        ])
        entries = D.lane_entries(rows)
        check("the list shape normalizes lane/state/claims",
              entries == [
                  {"lane": "tll-planner", "state": "active",
                   "claims": ("agents/tll-planner/skills/tll-planner/SKILL.md",)},
                  {"lane": "tll-docs", "state": "finished", "claims": ("docs/README.md",)},
              ], str(entries))
        keyed = registry_with_lanes(root, "keyed.json", 1,
                                    {"tll-planner": {"claims": ["agents/tll-planner"]}})
        check("the lane-keyed object shape is accepted",
              D.lane_entries(keyed) == [{"lane": "tll-planner", "state": "",
                                         "claims": ("agents/tll-planner",)}], str(D.lane_entries(keyed)))
        legacy = registry(root, "legacy.json", 1)
        check("a pre-#1458 registry has no lane rows", D.lane_entries(legacy) == [])
        malformed = registry_with_lanes(root, "bad.json", 1,
                                        [{"lane": "x", "state": "active", "claims": "agents/x"}])
        try:
            D.lane_entries(malformed)
            check("a non-list `claims` is a loud exit 2", False, "no Unreadable raised")
        except D.Unreadable as exc:
            check("a non-list `claims` is a loud exit 2", "not a list" in str(exc), str(exc))


def test_claims_overlap_refuses_active_and_allows_finished() -> None:
    print("\nClaims: overlap with an ACTIVE lane refuses naming it; FINISHED allows")
    with tempfile.TemporaryDirectory(prefix="dispatch-overlap-") as td:
        tmp = Path(td)
        reg = registry_with_lanes(tmp, "lanes.json", 1, [
            {"lane": "tll-planner", "state": "active",
             "claims": ["agents/tll-planner/skills/tll-planner/SKILL.md"]},
            {"lane": "tll-docs", "state": "finished", "claims": ["docs/README.md"]},
        ])
        lanes = D.lane_entries(reg)

        allowed = D.evaluate({"issue": "1458", "state": "OPEN", "bound_prs": []}, 1, 3,
                             claims=["scripts/dispatch_guard.py"], lanes=lanes)
        check("no overlap -> ALLOW", allowed["verdict"] == "allow", str(allowed))

        refused = D.evaluate({"issue": "1458", "state": "OPEN", "bound_prs": []}, 1, 3,
                             claims=["agents/tll-planner/skills/tll-planner/SKILL.md"], lanes=lanes)
        check("overlap with an ACTIVE lane -> REFUSE", refused["verdict"] == "refuse", str(refused))
        check("the refusal names the HOLDING lane and the path",
              any("tll-planner" in r and "SKILL.md" in r for r in refused["reasons"]),
              str(refused["reasons"]))

        under_dir = D.evaluate({"issue": "1458", "state": "OPEN", "bound_prs": []}, 1, 3,
                               claims=["agents/tll-planner"], lanes=lanes)
        check("a held FILE also blocks a dispatch claiming its DIRECTORY",
              under_dir["verdict"] == "refuse", str(under_dir))

        finished = D.evaluate({"issue": "1458", "state": "OPEN", "bound_prs": []}, 1, 3,
                              claims=["docs/README.md"], lanes=lanes)
        check("overlap with a FINISHED lane -> ALLOW", finished["verdict"] == "allow", str(finished))

        no_claim = D.evaluate({"issue": "1458", "state": "OPEN", "bound_prs": []}, 1, 3, lanes=lanes)
        check("NO --claim behaves exactly as today (overlap ignored)",
              no_claim["verdict"] == "allow" and no_claim["claims"] == [], str(no_claim))


def test_cli_and_make_forward_claims_and_keep_existing_refusals() -> None:
    print("\nClaims: the real CLI/make seam, refusals intact, offline")
    with tempfile.TemporaryDirectory(prefix="dispatch-claims-cli-") as td:
        tmp = Path(td)
        fixture = state_file(tmp, "open.json", "OPEN", [])
        reg = registry_with_lanes(tmp, "lanes.json", 1, [
            {"lane": "tll-planner", "state": "active",
             "claims": ["agents/tll-planner/skills/tll-planner/SKILL.md"]},
        ])

        def run(*args: str) -> tuple[int, str]:
            proc = subprocess.run(
                [sys.executable, str(ROOT / "scripts" / "dispatch_guard.py"),
                 "--issue", "1458", "--registry", str(reg), "--from-file", str(fixture), *args],
                capture_output=True, text=True, cwd=ROOT,
            )
            return proc.returncode, proc.stdout + proc.stderr

        rc, out = run("--claim", "scripts/dispatch_guard.py")
        check("CLI: no overlap exits 0", rc == 0, out)
        check("CLI: the verdict carries the claims", "scripts/dispatch_guard.py" in out, out)
        rc, out = run("--claim", "agents/tll-planner/skills/tll-planner/SKILL.md")
        check("CLI: overlap exits NON-ZERO", rc != 0, out)
        check("CLI: the reason names the holding lane", "tll-planner" in out and "REFUSE" in out, out)
        rc, out = run("--claim", str(ROOT / "agents" / "tll-planner" / "skills" / "tll-planner" / "SKILL.md"))
        check("CLI: an in-repo (absolute) claim is refused", rc != 0 and "REPO-RELATIVE" in out, out)
        rc, out = run()
        check("CLI: no --claim exits 0 exactly as today", rc == 0 and "claims=" not in out, out)

        # The existing refusals still fire alongside the claims check.
        closed = state_file(tmp, "closed.json", "CLOSED", [])
        proc = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "dispatch_guard.py"), "--issue", "1239",
             "--registry", str(reg), "--from-file", str(closed),
             "--claim", "agents/tll-planner/skills/tll-planner/SKILL.md"],
            capture_output=True, text=True, cwd=ROOT,
        )
        out = proc.stdout + proc.stderr
        check("closed issue still refuses with its own reason",
              proc.returncode != 0 and "CLOSED" in out and "tll-planner" in out, out)

        # make: CLAIMS= is the make-side spelling of repeatable --claim.
        proc = subprocess.run(
            ["make", "dispatch-check", "ISSUE=1458", f"REGISTRY={reg}",
             f"FROM_FILE={fixture}", 'CLAIMS=agents/tll-planner/skills/tll-planner/SKILL.md'],
            capture_output=True, text=True, cwd=ROOT,
        )
        out = proc.stdout + proc.stderr
        check("make CLAIMS=: overlap exits NON-ZERO", proc.returncode != 0, out)
        check("make CLAIMS=: the refusal names the holding lane", "tll-planner" in out, out)
        proc = subprocess.run(
            ["make", "dispatch-check", "ISSUE=1458", f"REGISTRY={reg}", f"FROM_FILE={fixture}",
             'CLAIMS=scripts/dispatch_guard.py docs/README.md'],
            capture_output=True, text=True, cwd=ROOT,
        )
        check("make CLAIMS=: space-separated multiple claims allow on no overlap",
              proc.returncode == 0, proc.stdout + proc.stderr)


# ---------------------------------------------------------------------------- thread (#1569)
def comment(cid: int, created: str, body: str) -> dict:
    """One recorded comment (the REST shape: numeric id + `created_at`)."""
    return {"id": cid, "created_at": created, "body": body}


def thread_file(tmp: Path, name: str, comments: list[dict]) -> Path:
    path = tmp / name
    path.write_text(json.dumps(comments), encoding="utf-8")
    return path


def test_thread_markers_and_machine_lines_are_parsed() -> None:
    print("\nThread: signed markers and machine lines parse (issue #1569)")
    working = ("BOT tll-implementer (host asimov@omarchy) · working on #1495 · branch none · "
               "blocked on none · next cut the worktree")
    check("a working-on marker parses lane/kind/issue/host",
          D.comment_markers(working) == [{"lane": "tll-implementer", "kind": "working on",
                                          "issue": 1495, "host": "asimov@omarchy"}],
          str(D.comment_markers(working)))
    m = D.comment_markers("BOT tll-planner · dispatch #1569 · lane tll-implementer · base `abc`")[0]
    check("a dispatch marker parses with NO host",
          m["kind"] == "dispatch" and m["issue"] == 1569 and m["host"] is None, str(m))
    for kind in D.RELEASE_KINDS:
        got = D.comment_markers(f"BOT tll-reviewer · {kind} #1317 · handover owner")[0]
        check(f"the {kind!r} marker parses as a release",
              got["kind"] == kind and got["issue"] == 1317, str(got))
    check("(host …) is read", D.comment_machine("BOT x (host asimov@mac) · working on #1") == "asimov@mac")
    check("a leading machine line is read",
          D.comment_machine("asimov@mac · status #1 · head abc") == "asimov@mac")
    check("a · user@host · span (the STATUS marker shape) is read",
          D.comment_machine("BOT tll-implementer · status #1560 · andy@Andys-MacBook-Pro · branch b")
          == "andy@Andys-MacBook-Pro")
    check("prose that only MENTIONS a host is not read",
          D.comment_machine("BOT tll-planner · dispatch #1 · measured andy@Andys-MacBook-Pro elsewhere")
          is None)
    check("no identity -> None", D.comment_machine("BOT tll-planner · dispatch #1 · base abc") is None)
    rows = D.normalize_comments([
        {"id": 2, "created_at": "2026-11-24T08:02:00Z", "body": "b"},
        {"id": 1, "createdAt": "2026-11-24T08:01:00Z", "body": "a"},
    ])
    check("rows sort oldest-first across both API spellings",
          [row["id"] for row in rows] == [1, 2], str(rows))
    check("default_machine is user@host (first hostname label)",
          re.fullmatch(r"[^@\s]+@[^.\s]+", D.default_machine()) is not None, D.default_machine())
    check("machine labels/case compare equal",
          D.same_machine("asimov@omarchy.local", "Asimov@omarchy")
          and not D.same_machine("asimov@mac", "asimov@omarchy"))


def test_active_claim_replays_newest_wins_and_release_clears() -> None:
    print("\nThread: newest ACTIVE claim wins; a release clears")
    rows = D.normalize_comments([
        comment(10, "2026-11-23T17:12:45Z", "BOT tll-implementer · working on #1445 · branch fix/a"),
        comment(11, "2026-11-23T17:31:58Z", "BOT tll-implementer · working on #1445 · branch fix/b"),
        comment(12, "2026-11-23T18:00:00Z", "BOT tll-planner · dispatch #1445 · lane tll-reviewer"),
    ])
    holder = D.active_claim(rows, "1445")
    check("the newest claim holds",
          holder is not None and holder["comment_id"] == 12 and holder["lane"] == "tll-planner",
          str(holder))
    check("markers for another issue are ignored", D.active_claim(rows, "9999") is None)

    released = D.normalize_comments([
        comment(10, "2026-11-23T17:12:45Z", "BOT tll-implementer (host asimov@mac) · working on #1445"),
        comment(11, "2026-11-23T19:00:00Z", "BOT tll-implementer · done #1445 · handover tll-planner"),
    ])
    check("a later done releases the claim", D.active_claim(released, "1445") is None,
          str(D.active_claim(released, "1445")))

    delivered = D.normalize_comments([
        comment(10, "2026-11-23T17:12:45Z", "BOT tll-implementer (host asimov@mac) · working on #1445"),
        comment(11, "2026-11-23T19:00:00Z", "BOT tll-implementer · pr #1445 · PR #1448 · handover tll-reviewer"),
        comment(12, "2026-11-23T19:30:00Z", "BOT tll-reviewer · reviewing #1445 · handover tll-implementer"),
        comment(13, "2026-11-23T20:00:00Z", "BOT tll-planner · dispatch #1445 · lane tll-implementer"),
    ])
    held = D.active_claim(delivered, "1445")
    check("a review cycle ends with the newest dispatch holding",
          held is not None and held["comment_id"] == 13, str(held))


def test_cross_host_refusal_names_host_lane_and_comment() -> None:
    print("\nThread: another host's NEWER ACTIVE claim refuses, naming it (#1569)")
    holder = {"comment_id": 7125064315, "lane": "tll-implementer", "kind": "working on",
              "machine": "andy@Andys-MacBook-Pro", "created": "2026-11-24T07:30:20Z"}
    v = D.evaluate({"issue": "1569", "state": "OPEN", "bound_prs": []}, 0, 3,
                   holder=holder, machine="asimov@omarchy")
    check("different host -> REFUSE", v["verdict"] == "refuse", str(v))
    reason = " ".join(v["reasons"])
    check("names the holding host, lane and comment id",
          "andy@Andys-MacBook-Pro" in reason and "tll-implementer" in reason
          and "7125064315" in reason, reason)
    check("the refusal says ACTIVE and cross-host",
          "ACTIVE" in reason and "another host" in reason, reason)

    same = D.evaluate({"issue": "1569", "state": "OPEN", "bound_prs": []}, 0, 3,
                      holder=holder, machine="andy@Andys-MacBook-Pro")
    check("the SAME host re-dispatching an issue it holds -> ALLOW",
          same["verdict"] == "allow" and not same["reasons"], str(same))

    allow = D.evaluate({"issue": "1569", "state": "OPEN", "bound_prs": []}, 0, 3,
                       holder=dict(holder, machine=None), machine="asimov@omarchy")
    check("a claim whose host cannot be named does not block", allow["verdict"] == "allow", str(allow))


def test_cli_reads_a_recorded_thread_offline() -> None:
    print("\nThread: the real CLI over a recorded thread, no network")
    with tempfile.TemporaryDirectory(prefix="dispatch-thread-cli-") as td:
        tmp = Path(td)
        fixture = state_file(tmp, "open.json", "OPEN", [])
        reg = registry(tmp, "lanes.json", 0)
        thread = thread_file(tmp, "thread.json", [
            comment(1, "2026-11-24T07:29:43Z",
                    "BOT tll-planner · dispatch #1560 · lane tll-implementer · base `674bb36b`"),
            comment(2, "2026-11-24T07:30:20Z",
                    "BOT tll-implementer · working on #1560 · branch ci/workflow-concurrency-groups-1560"),
            comment(3, "2026-11-24T07:54:48Z",
                    "BOT tll-implementer · status #1560 · andy@Andys-MacBook-Pro · branch ci/workflow-concurrency-groups-1560 @ 340f0e7e"),
        ])

        def run(*args: str) -> tuple[int, str]:
            proc = subprocess.run(
                [sys.executable, str(ROOT / "scripts" / "dispatch_guard.py"),
                 "--issue", "1560", "--registry", str(reg), "--from-file", str(fixture),
                 "--comments-file", str(thread), *args],
                capture_output=True, text=True, cwd=ROOT,
            )
            return proc.returncode, proc.stdout + proc.stderr

        rc, out = run("--machine", "asimov@omarchy")
        check("CLI: the second host is refused", rc != 0, out)
        check("CLI: names the holding host, lane and comment",
              "andy@Andys-MacBook-Pro" in out and "tll-implementer" in out and "comment 2" in out, out)
        rc, out = run("--machine", "andy@Andys-MacBook-Pro")
        check("CLI: the holding host itself is allowed", rc == 0, out)
        check("CLI: the holder is reported", "thread_holder=andy@Andys-MacBook-Pro" in out, out)
        rc, out = run("--machine", "asimov@omarchy", "--json")
        data = json.loads(out)
        check("JSON: the holder is carried as data",
              data["thread_holder"]["comment_id"] == 2 and data["verdict"] == "refuse", out[:400])

        embedded = tmp / "embedded.json"
        embedded.write_text(json.dumps({"state": "OPEN", "bound_prs": [],
                                        "comments": json.loads(thread.read_text(encoding="utf-8"))}),
                            encoding="utf-8")
        proc = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "dispatch_guard.py"), "--issue", "1560",
             "--registry", str(reg), "--from-file", str(embedded), "--machine", "asimov@omarchy"],
            capture_output=True, text=True, cwd=ROOT,
        )
        check("CLI: a `comments` list inside --from-file is read offline",
              proc.returncode != 0 and "comment 2" in proc.stdout + proc.stderr,
              proc.stdout + proc.stderr)


def test_make_forwards_the_machine_and_the_recorded_thread() -> None:
    print("\nThread: make forwards MACHINE and COMMENTS_FILE (#1569)")
    mk = (ROOT / "Makefile").read_text(encoding="utf-8")
    check("Makefile: the recipe forwards --machine", '--machine "$(MACHINE)"' in mk, "")
    check("Makefile: the recipe forwards --comments-file", '--comments-file "$(COMMENTS_FILE)"' in mk, "")
    with tempfile.TemporaryDirectory(prefix="dispatch-thread-make-") as td:
        tmp = Path(td)
        fixture = state_file(tmp, "open.json", "OPEN", [])
        reg = registry(tmp, "lanes.json", 0)
        thread = thread_file(tmp, "thread.json", [
            comment(1, "2026-11-24T07:30:20Z",
                    "BOT tll-implementer (host asimov@omarchy) · working on #1560 · branch b"),
        ])
        base = ["make", "dispatch-check", "ISSUE=1560", f"REGISTRY={reg}",
                f"FROM_FILE={fixture}", f"COMMENTS_FILE={thread}"]

        proc = subprocess.run([*base, "MACHINE=andy@Andys-MacBook-Pro"],
                              capture_output=True, text=True, cwd=ROOT)
        out = proc.stdout + proc.stderr
        check("make: another host is refused", proc.returncode != 0, out)
        check("make: names the holding host", "asimov@omarchy" in out, out)
        proc = subprocess.run([*base, "MACHINE=asimov@omarchy"],
                              capture_output=True, text=True, cwd=ROOT)
        check("make: the holding host itself is allowed",
              proc.returncode == 0, proc.stdout + proc.stderr)


def test_existing_refusals_keep_firing_alongside_the_thread_check() -> None:
    print("\nThread: prior refusals unchanged with a thread present (#1569)")
    holder = {"comment_id": 2, "lane": "tll-implementer", "kind": "working on",
              "machine": "asimov@omarchy", "created": "2026-11-24T07:30:20Z"}
    closed = D.evaluate({"issue": "1", "state": "CLOSED", "bound_prs": []}, 0, 3,
                        holder=holder, machine="andy@Andys-MacBook-Pro")
    check("closed issue still refuses with its own reason",
          any("CLOSED" in r for r in closed["reasons"]), str(closed["reasons"]))
    check("and the cross-host reason is added",
          any("another host" in r for r in closed["reasons"]), str(closed["reasons"]))
    over = D.evaluate({"state": "OPEN", "bound_prs": []}, 9, 3,
                      holder=holder, machine="andy@Andys-MacBook-Pro")
    check("ceiling refusal intact", any("ABOVE" in r for r in over["reasons"]), str(over["reasons"]))
    merged = D.evaluate({"state": "OPEN", "bound_prs": [
        {"number": 7, "state": "MERGED", "mergedAt": "2026-11-24T00:00:00Z"}]}, 0, 3,
        holder=holder, machine="andy@Andys-MacBook-Pro")
    check("merged-PR refusal intact", any("MERGED" in r for r in merged["reasons"]),
          str(merged["reasons"]))
    with tempfile.TemporaryDirectory(prefix="dispatch-thread-claims-") as td:
        reg = registry_with_lanes(Path(td), "lanes.json", 1, [
            {"lane": "tll-planner", "state": "active", "claims": ["agents/tll-planner"]},
        ])
        both = D.evaluate({"state": "OPEN", "bound_prs": []}, 1, 3,
                          claims=["agents/tll-planner/SKILL.md"],
                          lanes=D.lane_entries(reg),
                          holder=holder, machine="andy@Andys-MacBook-Pro")
        check("--claim overlap refusal intact alongside the thread check",
              any("tll-planner" in r and "overlaps" in r for r in both["reasons"])
              and any("another host" in r for r in both["reasons"]), str(both["reasons"]))


def main() -> int:
    test_open_issue_is_allowed()
    test_closed_issue_is_refused()
    test_merged_bound_pr_is_refused()
    test_concurrency_bound_is_one_constant()
    test_registry_is_caller_owned_and_lives_outside_the_repo()
    test_claim_paths_and_registry_rows_are_normalized()
    test_claims_overlap_refuses_active_and_allows_finished()
    test_cli_exit_codes_over_recorded_fixtures()
    test_cli_and_make_forward_claims_and_keep_existing_refusals()
    test_help_documents_the_registry_and_the_ceiling()
    test_make_dispatch_check_is_the_callers_single_seam()
    test_thread_markers_and_machine_lines_are_parsed()
    test_active_claim_replays_newest_wins_and_release_clears()
    test_cross_host_refusal_names_host_lane_and_comment()
    test_cli_reads_a_recorded_thread_offline()
    test_make_forwards_the_machine_and_the_recorded_thread()
    test_existing_refusals_keep_firing_alongside_the_thread_check()
    print(f"\nPASSED {_PASS} | FAILED {_FAIL}")
    return 1 if _FAIL else 0


if __name__ == "__main__":
    raise SystemExit(main())
