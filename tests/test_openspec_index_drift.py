#!/usr/bin/env python3
"""Behavioural tests for the drift REPORT beside `--check` (issue #1634).

`OPENSPEC.md` is generated, and `make openspec-index-check` only WARNs inside
`MAX_OPENSPEC_INDEX_DRIFT` (issue #1415) while exiting 0. That tolerance is
deliberate housekeeping slack, but it means a drifted index keeps qa-validate's
`validate` job GREEN — so the event-driven `index-repair` keeper, gated on a RED
validate, never woke and the drift compounded merge over merge (measured on
master `cb139e7c`: `archived: **520**` vs 522 dirs, rc 0; the #1625 regeneration
was superseded within an hour).

The additive half is a REPORT: `scripts/openspec_index.py --drift` prints the SAME
`index_drift()` count as one line (`drift=<n>`) and exits 0 for any drift, and
qa-validate surfaces it as an allowlisted output key that wakes `index-repair` on
a green push. These tests drive the REAL CLI (a byte-identical copy of the script
inside a tempdir fixture — its ROOT comes from `__file__`) and the REAL workflow,
Makefile and registry text. No mocks (rule 6m).

Run standalone: python3 tests/test_openspec_index_drift.py   or   make test
"""
from __future__ import annotations

import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "scripts" / "openspec_index.py"
WF = ROOT / ".github" / "workflows" / "qa-validate.yml"

sys.path.insert(0, str(ROOT / "scripts"))
import master_alarm as a  # noqa: E402  the ONE gate registry (issue #527)
from wiring import wired  # noqa: E402  (issues #176/#192)

_PASS = 0
_FAIL = 0


def check(name: str, cond: bool, detail: str = "") -> None:
    global _PASS, _FAIL
    if cond:
        _PASS += 1
        print(f"  ok  {name}")
    else:
        _FAIL += 1
        print(f"  FAIL {name}" + (f"  [{detail}]" if detail else ""))


# --------------------------------------------------------------------------
# The fixture: a byte-identical copy of the REAL generator in a tempdir.
# --------------------------------------------------------------------------
def _fixture_script(td: Path) -> Path:
    """Copy the real generator + its one sibling import into `td/scripts/`.

    `openspec_index.py` derives `ROOT`/`CHANGES`/`INDEX` from `__file__`, so the
    only way to run the REAL CLI against a tempdir tree is to execute the
    byte-identical file from inside it.
    """
    scripts = td / "scripts"
    scripts.mkdir(parents=True, exist_ok=True)
    shutil.copy2(SCRIPT, scripts / "openspec_index.py")
    shutil.copy2(ROOT / "scripts" / "task_boxes.py", scripts / "task_boxes.py")
    return scripts / "openspec_index.py"


def _change(changes: Path, name: str, *, archived: bool = False, issue: str = "#1634") -> Path:
    where = changes / "archive" / name if archived else changes / name
    (where / "specs" / "capability").mkdir(parents=True, exist_ok=True)
    (where / "specs" / "capability" / "spec.md").write_text("# capability\n", encoding="utf-8")
    (where / "tasks.md").write_text("# Tasks\n\n- [x] 1. done\n", encoding="utf-8")
    (where / "proposal.md").write_text(
        f"# Proposal: {name}\n\nIssue: {issue}\n\n## Why\n\nBecause.\n", encoding="utf-8"
    )
    return where


def _run_cli(script: Path, *argv: str) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(script), *argv],
                          capture_output=True, text=True)


def _build_like_cb139e7c(td: Path) -> Path:
    """The measured shape: rows complete, count line one behind (master cb139e7c).

    One active + two archived changes, `--write`, then the summary line rewritten
    to lag by one archive — every row still present and identical, exactly what
    the issue measured (`archived: **520**` vs 522 dirs).
    """
    script = _fixture_script(td)
    changes = td / "openspec" / "changes"
    _change(changes, "agent-active")
    _change(changes, "agent-archived-a", archived=True)
    _change(changes, "agent-archived-b", archived=True)
    rc = _run_cli(script, "--write")
    assert rc.returncode == 0, rc.stderr
    index = td / "OPENSPEC.md"
    good = index.read_text(encoding="utf-8")
    index.write_text(
        re.sub(r"^Active changes: \*\*(\d+)\*\* · archived: \*\*(\d+)\*\*$",
               lambda m: (f"Active changes: **{m.group(1)}** · "
                          f"archived: **{int(m.group(2)) - 1}**"),
               good, flags=re.MULTILINE),
        encoding="utf-8",
    )
    return script


# --------------------------------------------------------------------------
# 1. The report itself.
# --------------------------------------------------------------------------
def test_drift_report_exits_0_and_prints_the_one_measure():
    """Given the cb139e7c shape, `--drift` prints exactly `drift=1` and exits 0.

    RED on the old code: `--drift` does not exist, argparse exits 2 with nothing
    on stdout.
    """
    with tempfile.TemporaryDirectory() as raw:
        script = _build_like_cb139e7c(Path(raw))
        proc = _run_cli(script, "--drift")
        check("drift: rc 0 on a tolerated drift", proc.returncode == 0,
              f"rc={proc.returncode} err={proc.stderr.strip()}")
        check("drift: stdout is exactly `drift=1\\n`", proc.stdout == "drift=1\n",
              repr(proc.stdout))

    # A clean tree reports 0 — the report is not blind to the no-drift case
    # (`index_drift()` alone would answer 1, because its "outside the rows" branch
    # fires on an empty reason list).
    with tempfile.TemporaryDirectory() as raw:
        td = Path(raw)
        script = _fixture_script(td)
        _change(td / "openspec" / "changes", "agent-active")
        _run_cli(script, "--write")
        proc = _run_cli(script, "--drift")
        check("drift: a current index reports 0", proc.returncode == 0 and proc.stdout == "drift=0\n",
              f"rc={proc.returncode} out={proc.stdout!r}")

    # A missing row too: the report is not blind to ROW drift — missing row (1) +
    # count line (1) = 2.
    with tempfile.TemporaryDirectory() as raw:
        td = Path(raw)
        script = _build_like_cb139e7c(td)
        index = td / "OPENSPEC.md"
        kept = [ln for ln in index.read_text(encoding="utf-8").splitlines()
                if "`agent-archived-b`" not in ln]
        index.write_text("\n".join(kept) + "\n", encoding="utf-8")
        proc = _run_cli(script, "--drift")
        check("drift: a missing row plus the count line reports 2",
              proc.returncode == 0 and proc.stdout == "drift=2\n",
              f"rc={proc.returncode} out={proc.stdout!r}")

    # The gate is untouched: the same cb139e7c tree still WARNs and exits 0.
    with tempfile.TemporaryDirectory() as raw:
        script = _build_like_cb139e7c(Path(raw))
        proc = _run_cli(script, "--check")
        check("drift: --check is unchanged (WARN, rc 0)",
              proc.returncode == 0 and "WARN" in proc.stdout,
              f"rc={proc.returncode} out={proc.stdout!r}")


def test_a_missing_index_is_loud_in_the_report_mode():
    """A missing/unreadable index has nothing to report: stderr + exit 2, no stdout."""

    with tempfile.TemporaryDirectory() as raw:
        td = Path(raw)
        script = _fixture_script(td)
        _change(td / "openspec" / "changes", "agent-active")
        proc = _run_cli(script, "--drift")
        check("drift: a missing index exits 2 with no stdout",
              proc.returncode == 2 and proc.stdout == "",
              f"rc={proc.returncode} out={proc.stdout!r}")
        check("drift: the failure names the remedy on stderr", "make openspec-index" in proc.stderr,
              proc.stderr.strip())

    # `--check` keeps its own exit code (1) on the same tree — the report's exit 2
    # is new behaviour, not a change to the gate.
    with tempfile.TemporaryDirectory() as raw:
        td = Path(raw)
        script = _fixture_script(td)
        _change(td / "openspec" / "changes", "agent-active")
        proc = _run_cli(script, "--check")
        check("drift: --check still exits 1 on a missing index", proc.returncode == 1,
              f"rc={proc.returncode}")


# --------------------------------------------------------------------------
# 2. The keeper wakes on a GREEN push with drift.
# --------------------------------------------------------------------------
def _validate_job_text() -> str:
    text = WF.read_text(encoding="utf-8")
    return text.split("  validate:\n")[1].split("  live-smoke:\n")[0]


def _job_block(name: str) -> str:
    """The YAML text of one job — from its `  <name>:` key to the next top-level key.

    Deliberately text-shaped, not a YAML parse: the assertion is about the exact
    `if:` clause the fleet reads, and this keeps the module runnable on a host with
    no PyYAML (rule 6m — no stand-in for the workflow, only a narrower read).
    """
    block = WF.read_text(encoding="utf-8").split(f"  {name}:\n", 1)[1]
    out: list[str] = []
    for ln in block.splitlines():
        if out and ln and not ln.startswith(" "):
            break
        out.append(ln)
    return "\n".join(out)


def _index_repair_gate() -> str:
    m = re.search(r"^    if: >[-+]?\n((?:      .*\n)+)", _job_block("index-repair"), re.MULTILINE)
    return m.group(1) if m else ""


def test_a_green_push_with_drift_wakes_the_index_repair_keeper():
    """The keeper's `if:` carries the drift clause beside `failure()`.

    RED on the old workflow: the token is absent, so a green push whose index
    drifted leaves the keeper asleep.
    """
    gate = _index_repair_gate()
    check("qa: the index-repair keeper still carries an `if:` clause", bool(gate), "")
    check("qa: index-repair also wakes on reported drift (issue #1634)",
          "needs.validate.outputs.index_drift != '0'" in gate, gate)
    check("qa: failure() stays, so a red validate with no drift step behaves as before",
          "failure()" in gate, gate)
    check("qa: the trigger is still push-to-master only",
          "github.event_name == 'push'" in gate and "refs/heads/master" in gate, gate)
    check("qa: the keeper still never lands on a PR event",
          "pull_request" not in gate, gate)

    validate_text = _validate_job_text()
    m = re.search(r"^      index_drift: (.+)$", validate_text, re.MULTILINE)
    check("qa: validate publishes the drift output key",
          m is not None and "steps.index-drift.outputs.drift" in m.group(1),
          m.group(0) if m else "no index_drift output")
    check("qa: the drift step runs through make and writes the allowlisted key (rule 3d)",
          "make openspec-index-drift" in validate_text
          and "printf 'drift=%s\\n' \"${DRIFT:-0}\" >> \"$GITHUB_OUTPUT\"" in validate_text,
          validate_text[:900])


# --------------------------------------------------------------------------
# 3. Wiring: target, .PHONY, registry.
# --------------------------------------------------------------------------
def test_the_drift_target_is_registered_and_called_through_make():
    """The target exists, is PHONY, is called by validate, and is on a GATES list."""
    mk = (ROOT / "Makefile").read_text(encoding="utf-8")

    def recipe(target: str) -> str:
        m = re.search(rf"^{target}:[^\n]*\n((?:\t[^\n]*\n)+)", mk, re.MULTILINE)
        return m.group(1) if m else ""

    check("make: the openspec-index-drift target exists", bool(recipe("openspec-index-drift")),
          "no recipe")
    check("make: its recipe runs the real script through PYTHON_RUN (rules 6m/6d)",
          "$(PYTHON_RUN) python3 scripts/openspec_index.py --drift" in recipe("openspec-index-drift"),
          recipe("openspec-index-drift"))
    phony = " ".join(ln for ln in mk.splitlines() if ln.startswith(".PHONY:"))
    check("make: the target is declared .PHONY", "openspec-index-drift" in phony, phony[:160])

    validate_text = _validate_job_text()
    check("qa: the validate job really calls `make openspec-index-drift`",
          "make openspec-index-drift" in validate_text, "")
    check("registry: master_alarm leaves no validate gate uncovered",
          not a.unchecked_gates(validate_text), str(a.unchecked_gates(validate_text)))
    check("registry: the report is ALARM-backed (it regenerates nothing, never gates)",
          a.GATES.get("openspec-index-drift") == ("alarm", "master-alarm")
          and "openspec-index-drift" in a.ALARMED
          and "openspec-index-drift" not in a.KEEPERS,
          str(a.GATES.get("openspec-index-drift")))


def test_the_tolerance_is_unchanged():
    """Blast-radius pin: the tolerance constant and the WARN threshold survive.

    The whole point of repair C is that NOTHING newly reds, so the shared constant
    and the boundary it drives are pinned here rather than trusted.
    """
    src = SCRIPT.read_text(encoding="utf-8")
    mod = _module()
    check("gate: MAX_OPENSPEC_INDEX_DRIFT is still the shared constant",
          mod.MAX_OPENSPEC_INDEX_DRIFT == 25
          and "MAX_OPENSPEC_INDEX_DRIFT = 25" in src, str(mod.MAX_OPENSPEC_INDEX_DRIFT))
    check("gate: `--drift` never compares against the tolerance",
          "--drift" in src and "drift <= MAX_OPENSPEC_INDEX_DRIFT" in src, "")


def _module():
    import importlib.util  # noqa: PLC0415
    spec = importlib.util.spec_from_file_location("openspec_index", SCRIPT)
    assert spec and spec.loader, SCRIPT
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main() -> int:
    print("OpenSpec index drift report (scripts/openspec_index.py --drift, issue #1634)")
    test_drift_report_exits_0_and_prints_the_one_measure()
    test_a_missing_index_is_loud_in_the_report_mode()
    test_a_green_push_with_drift_wakes_the_index_repair_keeper()
    test_the_drift_target_is_registered_and_called_through_make()
    test_the_tolerance_is_unchanged()
    check("wired: this module runs in `make test`", wired(__file__), "")
    print(f"\nPASSED {_PASS} | FAILED {_FAIL}")
    return 1 if _FAIL else 0


if __name__ == "__main__":
    raise SystemExit(main())
