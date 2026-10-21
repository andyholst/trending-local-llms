#!/usr/bin/env python3
"""Behavioural tests for the OpenSpec archive lifecycle guard (issue #183).

Rule 6f said how a change is CREATED and validated, never when it ENDS: on
`master` when this guard was written, `OPENSPEC.md` reported 115 active changes
and 0 archived, `openspec/changes/archive/` was empty, and six active changes
named a `PR:` that GitHub reported as merged (#173, #180, #189, #374, #379,
#384). `scripts/openspec_archive_check.py` is the guard that closes the loop: an
active change whose PR merged must be archived.

These tests drive the REAL script as a subprocess against a real fixture tree and
a stub `gh` on PATH (the permitted stand-in: an EXTERNAL system, never the code
under test — rule 6m). Its only job is to answer "is this PR merged?" the way
GitHub would; everything that decides a violation is the production code.

Wired into `make test` (rule 6d).
"""
from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from pathlib import Path

from wiring import wired  # noqa: E402  (issues #176/#192)

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "scripts" / "openspec_archive_check.py"
ARCHITECTURE = ROOT / "ARCHITECTURE.md"
MAKEFILE = ROOT / "Makefile"
QA_VALIDATE = ROOT / ".github" / "workflows" / "qa-validate.yml"

_PASS = 0
_FAIL = 0

#: A stub `gh`: answers `api repos/<repo>/pulls/<n> --jq .merged` from
#: `$FAKE_PR_<n>` (default false), resolves the repo, and can be told to FAIL.
#: It stands in for github.com ONLY; the script builds the request and reads the
#: answer itself.
STUB = r"""#!/usr/bin/env bash
set -u
if [ "${FAKE_GH_FAIL:-0}" = "1" ]; then
  echo "gh: HTTP 403 (stubbed refusal)" >&2
  exit 1
fi
if [ "${1:-}" = "api" ]; then
  url="${2:-}"
  n="${url##*/pulls/}"
  var="FAKE_PR_${n}"
  val="${!var-}"
  echo "${val:-false}"
  exit 0
fi
if [ "${1:-}" = "repo" ]; then
  echo "andyholst/trending-local-llms"
  exit 0
fi
echo "gh: unsupported invocation: $*" >&2
exit 1
"""


def check(name, cond, detail=""):
    global _PASS, _FAIL
    if cond:
        _PASS += 1
        print(f"  ok  {name}")
    else:
        _FAIL += 1
        print(f"  FAIL {name}" + (f"  [{detail}]" if detail else ""))


def _change(root: Path, name: str, pr: str = "", archived: bool = False) -> Path:
    """A change directory with a proposal (and the `PR:` line) and its spec/tasks."""
    where = (root / "openspec" / "changes" / "archive" / name) if archived else (
        root / "openspec" / "changes" / name
    )
    (where / "specs" / "capability").mkdir(parents=True, exist_ok=True)
    (where / "specs" / "capability" / "spec.md").write_text("# capability\n", encoding="utf-8")
    (where / "tasks.md").write_text("# Tasks\n\n- [x] 1. done\n", encoding="utf-8")
    header = f"# Proposal: {name}\n\n"
    if pr:
        header += f"PR: {pr}\n\n"
    (where / "proposal.md").write_text(header + "## Why\n\nBecause.\n", encoding="utf-8")
    return where


def _stub_gh(td: Path) -> Path:
    bindir = td / "bin"
    bindir.mkdir(parents=True, exist_ok=True)
    stub = bindir / "gh"
    stub.write_text(STUB, encoding="utf-8")
    stub.chmod(0o755)
    return bindir


def _run(root: Path, bindir: Path | None, extra: dict | None = None):
    """Run the REAL script against `root` with the stub `gh` first on PATH."""
    env = {**os.environ}
    if bindir is not None:
        env["PATH"] = f"{bindir}:{env['PATH']}"
    env.pop("GITHUB_REPOSITORY", None)
    env.update(extra or {})
    r = subprocess.run(
        [sys.executable, str(SCRIPT), "--root", str(root), "--repo", "andyholst/trending-local-llms"],
        capture_output=True, text=True, env=env,
    )
    return r.returncode, r.stdout + r.stderr


def test_a_merged_pr_left_an_active_change_behind():
    """An active change naming a merged PR fails, naming the change and the fix."""

    # Given an active change whose PR #42 is merged
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        _change(root, "old-thing", pr="#42")
        bindir = _stub_gh(root)

        # When  the guard runs
        rc, out = _run(root, bindir, {"FAKE_PR_42": "true"})

    # Then  it fails, and says which change, which PR and what to run
    check("merged active change: exits 1", rc == 1, str(rc))
    check("merged active change: names the change", "old-thing" in out, out)
    check("merged active change: names the PR", "#42" in out, out)
    check("merged active change: names the archive command",
          "make openspec-archive NAME=old-thing" in out, out)


def test_an_unmerged_pr_is_not_a_violation():
    """An active change whose PR is still open is in flight, not a defect."""

    # Given an active change whose PR #7 is NOT merged
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        _change(root, "in-flight", pr="#7")
        bindir = _stub_gh(root)

        # When  the guard runs
        rc, out = _run(root, bindir, {"FAKE_PR_7": "false"})

    # Then  it passes and reports what it asserted
    check("unmerged PR: exits 0", rc == 0, out)
    check("unmerged PR: the check reports it looked", "none of them merged" in out, out)


def test_an_archived_change_is_left_alone():
    """A merged PR on an ARCHIVED change is the expected state."""

    # Given an archived change whose PR #9 is merged
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        _change(root, "done-thing", pr="#9", archived=True)
        bindir = _stub_gh(root)

        # When  the guard runs
        rc, out = _run(root, bindir, {"FAKE_PR_9": "true"})

    # Then  it passes: the lifecycle is complete
    check("archived change: exits 0", rc == 0, out)
    check("archived change: reported as archived", "1 archived" in out, out)


def test_a_change_without_a_pr_line_is_skipped():
    """Nothing is asserted about a change that names no PR (we do not guess)."""
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        _change(root, "no-pr-yet")
        bindir = _stub_gh(root)

        rc, out = _run(root, bindir)

    check("no PR line: exits 0", rc == 0, out)
    check("no PR line: says there is nothing to assert", "nothing to assert" in out, out)


def test_a_gh_failure_is_loud():
    """A GitHub read that fails exits 2 — never a silent pass."""

    # Given a change naming a PR and a gh that refuses
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        _change(root, "some-change", pr="#11")
        bindir = _stub_gh(root)

        # When  the guard runs
        rc, out = _run(root, bindir, {"FAKE_GH_FAIL": "1"})

    # Then  it fails loudly with gh's own message, not as a pass
    check("gh failure: exits 2", rc == 2, str(rc))
    check("gh failure: prints what gh said", "HTTP 403" in out, out)


def test_a_missing_gh_is_loud():
    """No gh on PATH is exit 2, naming what could not be checked."""
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        _change(root, "some-change", pr="#12")
        empty = root / "empty-path"
        empty.mkdir()

        rc, out = _run(root, empty)

    check("missing gh: exits 2", rc == 2, str(rc))
    check("missing gh: names the tool", "gh` is not installed" in out, out)


def test_the_repository_itself_has_no_merged_change_left_active():
    """This tree is conformant: its archived table is populated, actives are not merged.

    The stub answers `false` for every PR, so this asserts the SHAPE the guard
    needs (an archived change whose PR line survived the move, and the index
    listing it) rather than re-reading GitHub from a unit test.
    """
    with tempfile.TemporaryDirectory() as td:
        bindir = _stub_gh(Path(td))
        rc, out = _run(ROOT, bindir)

    index = (ROOT / "OPENSPEC.md").read_text(encoding="utf-8")
    archived = list((ROOT / "openspec" / "changes" / "archive").glob("*/proposal.md"))
    check("repo tree: the guard passes", rc == 0, out)
    check("repo tree: archived changes exist", len(archived) >= 6, str(len(archived)))
    check("repo tree: an archived change keeps its PR line",
          any("PR:" in p.read_text(encoding="utf-8") for p in archived), "")
    check("repo tree: the index lists them as archived",
          "| archived |" in index, index[:200])


def test_the_description_documents_when_a_change_is_archived():
    """ARCHITECTURE.md §8 names the archive step, its timing, the index and the guard."""
    text = ARCHITECTURE.read_text(encoding="utf-8")
    life = text.split("## 8. The life of a change", 1)[-1].split("## 9.", 1)[0]
    check("life of a change: names the archive target",
          "make openspec-archive NAME=<change>" in life, life[:400])
    check("life of a change: says WHEN (the PR that completes it)",
          "PR that completes" in life, "")
    check("life of a change: requires the index in the same PR",
          "make openspec-index" in life, "")
    check("life of a change: names the guard", "openspec-archive-check" in life, "")


def test_the_guard_is_wired_to_a_target_a_workflow_and_the_gate():
    """The target exists, qa-validate calls it with a PR-read token, and its test runs."""
    mk = MAKEFILE.read_text(encoding="utf-8")
    wf = QA_VALIDATE.read_text(encoding="utf-8")
    check("makefile: the target exists", "\nopenspec-archive-check:" in mk, "")
    check("makefile: it runs the script", "scripts/openspec_archive_check.py" in mk, "")
    check("workflow: qa-validate calls the target", "make openspec-archive-check" in wf, "")
    check("workflow: it passes a token", "GH_TOKEN: ${{ github.token }}" in wf, "")
    check("workflow: the validate job may read pull requests",
          "pull-requests: read" in wf, "")
    check("tests: this module is run by the suite", wired(__file__), "")

    stubbed = subprocess.run(["bash", str(ROOT / "scripts" / "run_tests.sh"), "--list"],
                             capture_output=True, text=True)
    check("tests: the runner discovers this module",
          "test_openspec_archive_check.py" in stubbed.stdout, stubbed.stdout[-300:])


def main() -> int:
    for fn in (
        test_a_merged_pr_left_an_active_change_behind,
        test_an_unmerged_pr_is_not_a_violation,
        test_an_archived_change_is_left_alone,
        test_a_change_without_a_pr_line_is_skipped,
        test_a_gh_failure_is_loud,
        test_a_missing_gh_is_loud,
        test_the_repository_itself_has_no_merged_change_left_active,
        test_the_description_documents_when_a_change_is_archived,
        test_the_guard_is_wired_to_a_target_a_workflow_and_the_gate,
    ):
        print(f"-- {fn.__name__}")
        fn()
    print(f"\n{_PASS} passed, {_FAIL} failed")
    return 1 if _FAIL else 0


if __name__ == "__main__":
    raise SystemExit(main())
