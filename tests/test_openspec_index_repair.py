#!/usr/bin/env python3
"""Behavioural tests for scripts/openspec_index_repair.py — the #304 keeper decision (issue #304).

A merged PR archives its OpenSpec change, so `master`'s tree no longer matches the
committed, generated `OPENSPEC.md`, and `make openspec-check` reds the
push-to-master `validate` run with NO PR-side repairer (rule 6q) — measured
2026-11-12: pushes `28f2cd3` and `ce57e9b`, both red at the OpenSpec gate,
auto-merge blocked repo-wide while the Wednesday-only architecture-bot keeper sat
idle. qa-validate's `index-repair` job now classifies the drift against the exact
post-merge tree and lands the regenerated index as a keeper PR — but ONLY under a
verdict this suite pins.

These tests drive the REAL repair script (imported by path) against a fixture tree
whose ROOT the loaded module is patched to (the accepted fixture shape of
`tests/test_openspec_index.py`), and the REAL closing parser against its PR body.

Wired into `make test` (rule 6d).
"""
from __future__ import annotations

import contextlib
import importlib.util
import io
import subprocess
import sys
import tempfile
from pathlib import Path

from wiring import wired  # noqa: E402  (issues #176/#192)

ROOT = Path(__file__).resolve().parent.parent
INDEX_SCRIPT = ROOT / "scripts" / "openspec_index.py"
REPAIR_SCRIPT = ROOT / "scripts" / "openspec_index_repair.py"
MAKEFILE = (ROOT / "Makefile").read_text(encoding="utf-8")
WF = ROOT / ".github" / "workflows"

_PASS = 0
_FAIL = 0


def check(name, cond, detail=""):
    global _PASS, _FAIL
    if cond:
        _PASS += 1
        print(f"  ok  {name}")
    else:
        _FAIL += 1
        print(f"  FAIL {name}" + (f"  [{detail}]" if detail else ""))


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader, path
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _patched_index(td: Path):
    """The REAL generator, its tree/INDEX globals patched to a fixture directory."""
    mod = _load("openspec_index", INDEX_SCRIPT)
    setattr(mod, "ROOT", td)
    setattr(mod, "CHANGES", td / "openspec" / "changes")
    setattr(mod, "INDEX", td / "OPENSPEC.md")
    return mod


def _repair_with(td: Path):
    """The REAL repair script, rewired to the patched generator (no fakes: the
    generator's own write/check is what the verdict is built from)."""
    rp = _load("openspec_index_repair", REPAIR_SCRIPT)
    setattr(rp, "oi", _patched_index(td))
    return rp


def _fixture_change(where: Path, name: str, issue: str = "", done: int = 1, todo: int = 0):
    (where / "specs" / "capability").mkdir(parents=True, exist_ok=True)
    (where / "specs" / "capability" / "spec.md").write_text("# capability\n", encoding="utf-8")
    boxes = "\n".join(f"- [x] step {i} done" for i in range(done))
    boxes += "\n" + "\n".join(f"- [ ] step {i} open" for i in range(todo)) if todo else ""
    (where / "tasks.md").write_text(f"# Tasks\n\n{boxes}\n", encoding="utf-8")
    header = f"# Proposal: {name}\n\n" + (f"Issue: {issue}\n\n" if issue else "")
    (where / "proposal.md").write_text(header + "## Why\n\nBecause. (evidence: a command)\n",
                                       encoding="utf-8")


def _run(mod, argv):
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        rc = mod.main(argv)
    return rc, out.getvalue() + err.getvalue()


def test_stale_index_after_a_merge_classifies_index_only_and_rewrites():
    """Given the exact shape of a merge that archived one change and landed another,
    the repair classifies DRIFT=index-only and the rewritten index is current by the
    generator's OWN check — the pre-change tree had no such verdict at all."""

    # Given a committed index that predates a merge: change `alpha` was ACTIVE when
    # the index was written; the merge ARCHIVED alpha and landed a new change `beta`.
    with tempfile.TemporaryDirectory() as td:
        tdp = Path(td)
        rp = _repair_with(tdp)
        oi = rp.oi
        changes = oi.CHANGES
        _fixture_change(changes / "alpha", "alpha", issue="#101")
        oi.INDEX.write_text(oi.render(), encoding="utf-8")  # committed index: alpha active
        (changes / "archive").mkdir()
        (changes / "alpha").rename(changes / "archive" / "alpha")  # the merge archived it
        _fixture_change(changes / "beta", "beta", issue="#202")  # the merge landed it

        # When the repair classifies this exact post-merge tree
        rc, out = _run(rp, ["--classify-and-write"])

        # Then the verdict is index-only, and the rewrite is current by the check itself
        check("index-only: exit 0", rc == 0, out)
        check("index-only: prints the DRIFT=index-only verdict",
              "DRIFT=index-only" in out, out)
        check("index-only: names the staleness it found (archived row + missing row)",
              "alpha" in out and "beta" in out, out)
        rc2, out2 = _run(oi, ["--check"])
        check("index-only: the rewritten index passes openspec_index.py --check",
              rc2 == 0, out2)

        # And a second run against the same tree reports none — idempotent, never a
        # second keeper PR for drift that is already repaired.
        rc3, out3 = _run(_repair_with(tdp), ["--classify-and-write"])
        check("index-only: a second classify on the repaired tree says DRIFT=none",
              rc3 == 0 and "DRIFT=none" in out3, out3)


def test_current_index_classifies_none_and_writes_nothing():
    """When the index IS current, the red was another cause: DRIFT=none, nothing is
    written — the workflow's land step then lands nothing."""
    with tempfile.TemporaryDirectory() as td:
        tdp = Path(td)
        rp = _repair_with(tdp)
        oi = rp.oi
        _fixture_change(oi.CHANGES / "alpha", "alpha", issue="#101")
        oi.INDEX.write_text(oi.render(), encoding="utf-8")
        before = oi.INDEX.read_bytes()

        rc, out = _run(rp, ["--classify-and-write"])

        check("none: exit 0 with DRIFT=none", rc == 0 and "DRIFT=none" in out, out)
        check("none: the index bytes are untouched", oi.INDEX.read_bytes() == before, out)


def test_a_tolerated_drift_is_still_classified_and_repaired():
    """Issue #1415: `--check` only WARNs at or under MAX_OPENSPEC_INDEX_DRIFT, but
    the keeper still measures that SAME drift by the generator's ONE function and
    rewrites it — a tolerated drift must not accumulate silently."""

    # Given one changed row (the shape a merge leaves behind): small, so the gate
    # would only warn about it.
    with tempfile.TemporaryDirectory() as td:
        tdp = Path(td)
        rp = _repair_with(tdp)
        oi = rp.oi
        _fixture_change(oi.CHANGES / "alpha", "alpha", issue="#101")
        oi.INDEX.write_text(oi.render(), encoding="utf-8")
        tasks = oi.CHANGES / "alpha" / "tasks.md"
        tasks.write_text(tasks.read_text(encoding="utf-8") + "- [ ] extra\n", encoding="utf-8")

        rc_warn, warn_out = _run(oi, ["--check"])
        rc, out = _run(rp, ["--classify-and-write"])
        rc2, out2 = _run(oi, ["--check"])

    check("tolerated: the gate warns and exits 0", rc_warn == 0 and "WARN" in warn_out, warn_out)
    check("tolerated: the keeper still repairs it (DRIFT=index-only)",
          rc == 0 and "DRIFT=index-only" in out, out)
    check("tolerated: the keeper names the count and the shared threshold",
          "1 differing change(s)" in out and "MAX_OPENSPEC_INDEX_DRIFT=25" in out, out)
    check("tolerated: the rewritten index passes --check", rc2 == 0, out2)

    src = REPAIR_SCRIPT.read_text(encoding="utf-8")
    check("tolerated: the keeper shares the generator's measure (no second counter)",
          "oi.index_drift(" in src and "def index_drift" not in src, "")


def test_missing_generated_file_is_index_only_drift():
    """A deleted OPENSPEC.md is exactly this guard's failure shape (issue #304 began
    with one): the repair writes it and the verdict is index-only."""
    with tempfile.TemporaryDirectory() as td:
        tdp = Path(td)
        rp = _repair_with(tdp)
        oi = rp.oi
        _fixture_change(oi.CHANGES / "alpha", "alpha", issue="#101")
        # index deliberately absent — only the changes exist on disk

        rc, out = _run(rp, ["--classify-and-write"])
        rc2, out2 = _run(oi, ["--check"])
        check("missing index: classified index-only and rewritten",
              rc == 0 and "DRIFT=index-only" in out and oi.INDEX.is_file(), out)
        check("missing index: the rewrite passes --check", rc2 == 0, out2)


def test_unreadable_index_is_loud_never_a_silent_clean():
    """An index that cannot be read must exit 2 naming the refusal — a scan that
    silently reports clean is the defect every rule in this repo exists to prevent."""
    with tempfile.TemporaryDirectory() as td:
        tdp = Path(td)
        rp = _repair_with(tdp)
        oi = rp.oi
        _fixture_change(oi.CHANGES / "alpha", "alpha", issue="#101")
        # NOT a chmod-000 trick: the container suite may run as root, and root
        # reads a 000 file happily. Undecodable bytes are unreadable for EVERY
        # uid — that is the shape this check must prove loud.
        oi.INDEX.write_bytes(b"\xff\xfe\x00\x01 not a real index")
        rc, out = _run(rp, ["--classify-and-write"])
        check("unreadable: exit 2, not 0", rc == 2, out)
        check("unreadable: names the refusal loudly", "ERROR" in out and "could not be read" in out, out)


def test_keeper_pr_body_implements_no_issue_and_closes_none():
    """The keeper PR body records drift (refs #304) and must not close anything —
    proven with the REAL closing parser against the REAL branch shape."""
    rp = _load("openspec_index_repair", REPAIR_SCRIPT)
    rc, body = _run(rp, ["--print-pr-body",
                         "--master-sha", "28f2cd3f8d5c4a1e9b0f112233445566778899aa",
                         "--run-url", "https://github.com/andyholst/trending-local-llms/actions/runs/1"])
    check("body: exit 0", rc == 0, body)
    check("body: references the tracking issue without closing it",
          "refs #304" in body and "Closes" not in body, body)

    pr_closure = _load("pr_closure", ROOT / "scripts" / "pr_closure.py")
    branch = "ci/openspec-index-repair-20261112T120000Z"
    check("body: the real parser sees NO implemented issue on this branch",
          pr_closure.implemented_issue(branch) is None, branch)
    problems = pr_closure.check(body, branch)
    check("body: the real closure gate accepts it", problems == [], problems)

    # The keeper branch shape itself carries no trailing number (rule 6e/#852): a
    # timestamped branch must never look like an implementation branch.
    check("body: branch shape has no issue number",
          pr_closure.implemented_issue(branch) is None, branch)

    # A body printed without naming the red run is a refusal, not an empty body.
    rc2, out2 = _run(rp, ["--print-pr-body"])
    check("body: missing --master-sha/--run-url exits 2 loudly",
          rc2 == 2 and "needs --master-sha" in out2, out2)


def test_the_keeper_body_names_the_green_drift_run_it_repairs():
    """Issue #1651: the body must say what the cited run ACTUALLY concluded.

    Measured on the shipped tree: post-merge push run 4546683307 concluded
    `completed/success`, yet the body printed by `make
    openspec-index-repair-pr-body` claimed it "went red at the OpenSpec gate"
    and the job's checkout step was named "...that went red". This drives the
    REAL composer with that green-with-drift run through the REAL CLI seam, and
    pins the workflow step name, so neither can lie again (rules 2/6g).
    """
    rp = _load("openspec_index_repair", REPAIR_SCRIPT)
    run_url = ("https://github.com/andyholst/trending-local-llms/actions/runs/4546683307")
    master_sha = "a0f9adc5b74f1a34e4886b3d9126397c2ebe81b9"
    rc, body = _run(rp, ["--print-pr-body", "--master-sha", master_sha,
                         "--run-url", run_url, "--run-green", "--index-drift", "1"])
    check("green drift: exit 0", rc == 0, body)
    check("green drift: names the exact run and tree",
          "4546683307" in body and "a0f9adc5" in body, body[:240])
    check("green drift: NEVER claims the run went red", "went red" not in body, body[:300])
    check("green drift: names the real conclusion",
          "stayed GREEN" in body and "REPORTED index drift" in body, body[:300])
    check("green drift: reports the drift count the gate published",
          "drift=1" in body, body[:300])

    # A red run keeps the ORIGINAL wording — this is a non-breaking additive fix.
    rc2, red_body = _run(rp, ["--print-pr-body", "--master-sha", master_sha,
                              "--run-url", run_url])
    check("red: exit 0", rc2 == 0, red_body)
    check("red: still names the red honestly", "went red at the OpenSpec gate" in red_body,
          red_body[:300])
    check("red: does not claim GREEN", "stayed GREEN" not in red_body, red_body[:300])

    # The step a human reads while diagnosing must be true for both triggers.
    wf = (ROOT / ".github" / "workflows" / "qa-validate.yml").read_text(encoding="utf-8")
    job = wf.split("  index-repair:\n", 1)[1].split("\n  invalid-change-repair:\n", 1)[0]
    checkout = next((ln for ln in job.splitlines() if "Checkout the exact master commit" in ln), "")
    check("qa: index-repair's checkout step no longer claims a red",
          "went red" not in checkout and "the run validated" in checkout, checkout)
    # The TWO sibling keepers still fire on failure() only, so their step names stay.
    check("qa: the sibling keepers' step names are left byte-identical",
          wf.count("- name: Checkout the exact master commit that went red") == 2, "")


def test_the_repair_is_wired_through_make_and_qa_validate():
    """Rule 6m/6d: the script is reachable ONLY through the Makefile, and qa-validate
    calls those targets — a workflow that reaches the script directly, or a target no
    pipeline runs, is the defect this test exists for."""
    check("makefile: openspec-index-repair is a target",
          "\nopenspec-index-repair:" in MAKEFILE, "")
    check("makefile: openspec-index-repair-pr-body is a target",
          "\nopenspec-index-repair-pr-body:" in MAKEFILE, "")
    check("makefile: both .PHONY",
          "openspec-index-repair openspec-index-repair-pr-body" in MAKEFILE, "")

    wf = (WF / "qa-validate.yml").read_text(encoding="utf-8")
    check("qa-validate: calls make openspec-index-repair and propagates its refusal (exit 2)",
          "if ! make openspec-index-repair; then" in wf and "exit 2" in wf, "")
    check("qa-validate: composes the body through make openspec-index-repair-pr-body "
          "(inline, or delegated to the keeper seam as its body target — issue #869)",
          "make openspec-index-repair-pr-body MASTER_SHA=" in wf
          or ("BODY_TARGET=openspec-index-repair-pr-body" in wf
              and 'BODY_ARGS="MASTER_SHA=' in wf), "")
    check("qa-validate: never runs the repair script directly (rule 6m)",
          "python3 scripts/openspec_index_repair.py" not in wf, "")


def test_the_suite_is_wired():
    check("wired into `make test` via scripts/run_tests.sh", wired(__file__), "")


def _subprocess_compile():
    proc = subprocess.run([sys.executable, "-m", "py_compile", str(REPAIR_SCRIPT)],
                          capture_output=True, text=True)
    return proc.returncode == 0


def main() -> int:
    assert _subprocess_compile(), "scripts/openspec_index_repair.py does not compile"
    test_stale_index_after_a_merge_classifies_index_only_and_rewrites()
    test_current_index_classifies_none_and_writes_nothing()
    test_a_tolerated_drift_is_still_classified_and_repaired()
    test_missing_generated_file_is_index_only_drift()
    test_unreadable_index_is_loud_never_a_silent_clean()
    test_keeper_pr_body_implements_no_issue_and_closes_none()
    test_the_keeper_body_names_the_green_drift_run_it_repairs()
    test_the_repair_is_wired_through_make_and_qa_validate()
    test_the_suite_is_wired()
    print(f"[test_openspec_index_repair] {_PASS} passed, {_FAIL} failed")
    return 1 if _FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
