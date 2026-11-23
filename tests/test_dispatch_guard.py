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

Run:  python3 tests/test_dispatch_guard.py   or   make test
"""
from __future__ import annotations

import json
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


def main() -> int:
    test_open_issue_is_allowed()
    test_closed_issue_is_refused()
    test_merged_bound_pr_is_refused()
    test_concurrency_bound_is_one_constant()
    test_registry_is_caller_owned_and_lives_outside_the_repo()
    test_cli_exit_codes_over_recorded_fixtures()
    test_help_documents_the_registry_and_the_ceiling()
    test_make_dispatch_check_is_the_callers_single_seam()
    print(f"\nPASSED {_PASS} | FAILED {_FAIL}")
    return 1 if _FAIL else 0


if __name__ == "__main__":
    raise SystemExit(main())
