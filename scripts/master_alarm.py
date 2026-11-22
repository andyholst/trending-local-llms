#!/usr/bin/env python3
"""The red-master alarm (issue #527): a deterministic gate on a `push` to master has no repairer.

`qa-validate`'s `validate` job runs on a `push` to master as well as on PRs, and every repair
path in this repo needs a PR: the implementer's own monitored fix loop (`issue-bot.yml` +
`scripts/fix_loop.sh`) repairs the PRs it opens, `pr-health` sweeps open PRs and REPORTS them
(the fix-bot pipeline was retired by issue #814), and `architecture-bot` repairs exactly two generated files (`ARCHITECTURE.md`, `OPENSPEC.md`
via #526). So when a deterministic gate goes red AFTER `auto-merge` — a stale generated file, a
data invariant broken, a table malformed (measured: run 39625708799, red at the `OpenSpec gate`
with the unit tests never reached) — nothing in the repo opens an edit: master stays red until a
human pastes a run URL into a thread.

This tool is the ALARM half. It reads `qa-validate`'s newest `push`-to-master run and, when it
concluded in failure, exits 1 naming the run URL and the failing job — so the scheduled sweep
that calls it goes RED in the Actions tab instead of staying quiet (the `queued-alarm` /
`bot-health` model: a red state must produce a signal, not a page nobody opens). It never writes
anything; the KEEPER half for the one repair path that exists (architecture-bot regenerates
`ARCHITECTURE.md` and `OPENSPEC.md`) is documented beside the registry below.

The KEEPER/ALARM registry is the TABLE the issue demands, and `tests/test_master_alarm.py` fails
when a new gate is added to the `validate` job without landing on one of the two lists.

Usage:
    python3 scripts/master_alarm.py --repo OWNER/NAME [--limit N]

Exit: 0 = the newest push-to-master run is green (or pending) and no alarm is owed; 1 = it is
red, naming the run URL and the failing jobs; 2 = the GitHub read failed (a tool that cannot read
must not report a pass).
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

WORKFLOW = "qa-validate.yml"
HEAD_BRANCH = "master"
#: A conclusion that means the run did not do its job (mirrors scripts/bot_health.py::BAD).
BAD = frozenset({"failure", "timed_out", "cancelled", "startup_failure", "action_required"})

# ---------------------------------------------------------------------------
# The KEEPER / ALARM table (issue #527) — every deterministic gate in
# qa-validate's `validate` job, with the thing that stops a red master from
# being silent. A gate is either KEEP (a bot in this repo regenerates the file
# that gate checks) or ALARM (the master-alarm above makes it visible). This is
# the single list; tests/test_master_alarm.py reads it to fail when a gate in
# the validate job is on NEITHER list. Additive only, never a deletion.
# ---------------------------------------------------------------------------
GATES: dict[str, tuple[str, str]] = {
    # -- KEEP — a bot in this repo regenerates the artifact the gate checks, so a
    #    merge that leaves the file stale is repaired on the pipeline that just saw it.
    # ARCHITECTURE.md has TWO keepers, mirroring OPENSPEC.md (issue #861, the #304
    # sibling): qa-validate's `architecture-repair` job runs on the very
    # push-to-master run whose `validate` went red, classifies the drift through
    # scripts/architecture_block_repair.py, and lands the regenerated block as a
    # keeper PR when the drift is block-only — event driven, minutes after the
    # merge. A Wednesday-only keeper left auto-merge red for days (measured after
    # merge `91eb093`: '201 make targets, 71 files' vs on disk '199…70…').
    "architecture-check": ("keeper", "qa-validate architecture-repair + architecture-bot"),
    # OPENSPEC.md has TWO keepers (issue #304): qa-validate's `index-repair` job
    # runs on the very push-to-master run whose `validate` went red, classifies
    # the drift through scripts/openspec_index_repair.py, and lands the
    # regenerated index as a keeper PR when the drift is index-only — event
    # driven, minutes after the merge. architecture-bot's weekly regeneration is
    # the backstop. A Wednesday-only keeper left auto-merge red for days (measured
    # 2026-11-12, pushes 28f2cd3 and ce57e9b).
    # Issue #962 names the THIRD repairer for this gate's other shape: an ACTIVE
    # change that shipped incomplete (proposal only, no spec, no tasks) reds
    # `openspec validate --changes` with the index perfectly current, so
    # `index-repair` answers `DRIFT=none` and owns nothing — the shape belongs to
    # qa-validate's `invalid-change-repair` job (`SHAPES` below, then the alarm
    # prints it per shape).
    "openspec-check": ("keeper", "qa-validate index-repair + architecture-bot"),
    # -- ALARM — the master-alarm makes a red push-to-master run visible.
    "fleet-host-sync-check": ("alarm", "master-alarm"),
    # The comment/CI/merge monitor is deterministic repo-owned code (issue #1266).
    # No keeper regenerates its protocol, so a red master goes to the alarm.
    "watch-monitor": ("alarm", "master-alarm"),
    "lint": ("alarm", "master-alarm"),
    "check-commit-authorship": ("alarm", "master-alarm"),
    "pr-closure": ("alarm", "master-alarm"),
    "image-ensure": ("alarm", "master-alarm"),
    # The corrupt-tag fallback ANNOUNCER (issue #1120): not a verifier — it posts the
    # PR comment when image-ensure/openspec-check rebuilt an image without a pull. It
    # is registered here because master_alarm derives "what the validate job runs"
    # from the pipeline itself, and a make target the job runs that GATES does not
    # name is the #527 defect; the master-alarm list covers it even though the step
    # is pull_request-only and can never red a push.
    "announce-image-fallback": ("alarm", "master-alarm"),
    "secret-scan": ("alarm", "master-alarm"),
    "secret-scan-self-test": ("alarm", "master-alarm"),
    "check-secret-output": ("alarm", "master-alarm"),
    "action-pin-check": ("alarm", "master-alarm"),
    "nerve-check": ("alarm", "master-alarm"),
    "validate": ("alarm", "master-alarm"),
    "validate-search": ("alarm", "master-alarm"),
    "validate-mapped": ("alarm", "master-alarm"),
    "openspec-archive-check": ("alarm", "master-alarm"),
    # The reintroduction gate (issue #802): a red on master here means a diagnosed pipeline
    # failure was closed without its fix PR + guard test; master-alarm makes it loud.
    "pipeline-failure-guard-check": ("alarm", "master-alarm"),
    "test": ("alarm", "master-alarm"),
}

#: The gates the keeper family (architecture-bot) repairs, by name.
KEEPERS = {g for g, (kind, _) in GATES.items() if kind == "keeper"}
#: The make targets the master-alarm covers (explicit, so a NEW gate that is
#: neither kept nor alarm-covered fails tests/test_master_alarm.py immediately).
ALARMED = {g for g, (kind, _) in GATES.items() if kind == "alarm"}

#: --------------------------------------------------------------------------
#: The per-SHAPE routing of a keeper gate (issue #962). `GATES` answers "which
#: list is this gate on"; this table answers "which repairer owns which shape of
#: its red", because one gate can go red for more than one reason and a keeper
#: that can only repair one of them leaves the other shape unnamed. Measured:
#: run 43610043055 — `openspec-check` red on master for an INCOMPLETE ACTIVE
#: change while the index was current, so the index keeper answered `DRIFT=none`
#: and named nothing. `verdict()` renders these pathways into the alarm text, so
#: a reader of the red run sees the repairer for the shape it actually hit.
#: --------------------------------------------------------------------------
SHAPES: dict[str, tuple[tuple[str, str], ...]] = {
    "openspec-check": (
        ("index-drift", "qa-validate index-repair + architecture-bot"),
        ("invalid-change", "qa-validate invalid-change-repair"),
    ),
    "architecture-check": (
        ("generated-block-stale", "qa-validate architecture-repair + architecture-bot"),
    ),
}


def keeper_pathways(job: str) -> str:
    """The named repairer(s) for one keeper gate, rendered for the alarm text.

    A keeper gate with no shape routing falls back to its `GATES` action, so the
    alarm never prints an empty pathway list.
    """
    shapes = SHAPES.get(job)
    if shapes:
        return "; ".join(f"{shape} -> {keeper}" for shape, keeper in shapes)
    return GATES[job][1]


#: The pipeline file the alarm reads its routing from (the same workflow gh reports).
WORKFLOW_PATH = Path(__file__).resolve().parent.parent / ".github" / "workflows" / WORKFLOW


def job_gate_map(wf_text: str | None = None) -> dict[str, list[str]]:
    """job name -> the registry gates that job runs, read from the pipeline itself.

    `gh run view --json jobs` reports JOB names; `GATES` registers `make <target>`
    gates (issue #962). Without this map the alarm could name a keeper only when a
    job happened to be spelled like a gate — it never is — so the routing is derived
    from the workflow (rule 6d: one source, no hand-kept second copy of which job
    runs which gate).
    """
    text = wf_text if wf_text is not None else WORKFLOW_PATH.read_text(encoding="utf-8")
    lines = text.splitlines()
    start = next((i for i, line in enumerate(lines) if line == "jobs:"), len(lines))
    out: dict[str, list[str]] = {}
    current: str | None = None
    for line in lines[start + 1:]:
        if line and not line.startswith(" "):
            break  # the next top-level key ends the jobs block
        key = re.match(r"^  ([a-z0-9_-]+):\s*(#.*)?$", line)
        name = key.group(1) if key else None
        if name:
            current = name
            out.setdefault(current, [])
            continue
        if current is None:
            continue
        for gate in re.findall(r"make\s+([a-z0-9_-]+)(?=[\"'\s]|$)", line):
            if gate in GATES and gate not in out[current]:
                out[current].append(gate)
    return out


def gates_of_failing_jobs(jfails: list[str]) -> list[str]:
    """The registry gates a run's failing JOB(s) actually run (issue #962)."""
    by_job = job_gate_map()
    found: list[str] = []
    for job in jfails:
        for gate in by_job.get(job, []):
            if gate not in found:
                found.append(gate)
    return sorted(found)


def _gh(args: list[str]) -> str:
    out = subprocess.run(["gh", *args], capture_output=True, text=True)
    if out.returncode != 0:
        raise RuntimeError(f"gh {' '.join(args)} failed: {out.stderr.strip() or 'non-zero exit'}")
    return out.stdout


#: A `make <target>` at a COMMAND position, terminated by a SHELL operator as well
#: as the quote/space/EOL the first version admitted (issue #1281): `make X;`,
#: `make X | …`, `make X && …`, `make X)`, `` `make X` `` and `make X` at EOL are
#: all gates. The terminator set is what makes a `run: |` continuation written
#: `make X;` visible instead of silence.
_MAKE_GATE = re.compile(r"make\s+([a-z0-9_-]+)(?=[\"'`\s;&|)]|$)")

#: A quoted span. A `make <target>` inside one is PROSE — an `echo`/`printf`
#: argument or a doc string — never a command the job runs (issue #1281).
_QUOTED = re.compile(r'"[^"]*"|\'[^\']*\'')

#: A line whose COMMAND WORD only reports text. Such a line runs no gate, so a
#: `make <target>` on it is prose even when it is not quoted.
_PROSE_CMD = re.compile(r"^\s*(?:@|-)?\s*(?:echo|printf|say|warn|annotate)\b")


def validate_gates_from_trees(wf_text: str) -> list[str]:
    """The `make <target>` gates the given `validate` job runs, in order.

    Used by tests to compare the tree against the registry: a `make X` the validate job
    runs that `GATES` does not name is caught as "a gate in validate on neither list".
    Both shapes count (issue #527): the inline `run: make X` step AND the bare
    `make X` continuation line of a multi-line `run:` block — the first version matched
    only the continuation lines and read the three gates of ONE block as the whole job.

    Issue #1281: the match is LINE-ORIENTED and reads a SHELL terminator, not only a
    quote/space. A gate written `make X;` (the normal shell shape, and the shape of a
    `run: |` continuation) was invisible, so a NEW gate could ship unregistered with
    this guard green; and a `make X` inside a quoted argument (`echo "Run 'make X'
    and rebase"`) manufactured a PHANTOM gate that reds the guard on prose. So a
    comment line, a line whose command word is echo/printf, and quoted spans all
    contribute nothing.
    """
    gates: list[str] = []
    for line in wf_text.splitlines():
        stripped = line.strip()
        if stripped.startswith("#") or _PROSE_CMD.match(line):
            continue
        gates += _MAKE_GATE.findall(_QUOTED.sub(" ", line))
    return gates


def unchecked_gates(wf_text: str) -> list[str]:
    """Gates the validate job runs that `GATES` does not cover (the defect, if any)."""
    return sorted(set(validate_gates_from_trees(wf_text)) - set(GATES))


def newest_push_run(repo: str, limit: int = 10) -> dict | None:
    """The newest `push`-to-`master` `qa-validate` run, or None when none exists."""
    raw = _gh(["run", "list", "--workflow", WORKFLOW, "--event", "push",
               "--limit", str(limit), "--json",
               "databaseId,createdAt,conclusion,status,url,headBranch,displayTitle",
               "--repo", repo])
    runs = [r for r in json.loads(raw or "[]") if r.get("headBranch") == HEAD_BRANCH]
    if not runs:
        return None
    runs.sort(key=lambda r: r.get("createdAt") or "", reverse=True)
    return runs[0]


def failing_jobs(repo: str, run_id: int) -> list[str]:
    """Names of the jobs that concluded in failure on the given run (best effort)."""
    try:
        raw = _gh(["run", "view", str(run_id), "--json", "jobs", "--repo", repo])
        jobs = json.loads(raw).get("jobs", [])
        return [j.get("name") or "?" for j in jobs
                if (j.get("conclusion") or "") in BAD]
    except (RuntimeError, ValueError):
        return []


def verdict(repo: str, limit: int = 10) -> tuple[int, str]:
    """The alarm's decision as (exit, message). Pure wrapper over the reads."""
    try:
        run = newest_push_run(repo, limit)
    except (RuntimeError, ValueError) as exc:
        return 2, f"[master-alarm] FAIL: {exc}"
    if run is None:
        return 0, f"[master-alarm] OK: no `push`-to-`{HEAD_BRANCH}` {WORKFLOW} run exists."
    conclusion = (run.get("conclusion") or run.get("status") or "unknown").lower()
    if conclusion == "success":
        at = (run.get("createdAt") or "?").replace("T", " ").replace("Z", "")
        return 0, (f"[master-alarm] OK: newest push-to-master qa-validate run "
                   f"{run.get('databaseId')} is green ({at}).")
    if conclusion in BAD:
        run_id = run.get("databaseId")
        lines = [f"[master-alarm] FAIL: newest push-to-master {WORKFLOW} run {run_id} "
                 f"concluded '{conclusion}'."]
        jfails = failing_jobs(repo, run_id) if run_id is not None else []
        if jfails:
            lines.append("  failing job(s): " + ", ".join(jfails))
        else:
            lines.append("  (the run's failing job could not be read)")
        url = run.get("url") or ""
        if url:
            lines.append(f"  run: {url}")
        # Name the repairer for the shape that reded the run (issue #962): a keeper
        # gate can fail for more than one reason, and the keeper that owns one shape
        # (index drift) is not the repairer for the other (an incomplete ACTIVE
        # change). The failing JOB is mapped to the registry gates it runs (one map,
        # read from the pipeline), so a red master names the repairer for the shape it
        # actually hit instead of being read as "the index keeper will handle it".
        gates = gates_of_failing_jobs(jfails)
        if gates:
            lines.append("  failing gate(s) of that job: " + ", ".join(gates))
        keepers = [g for g in gates if g in KEEPERS]
        if keepers:
            lines.append("  named repairer(s), by shape:")
            for gate in keepers:
                lines.append(f"    - {gate}: {keeper_pathways(gate)}")
        alarmed = [g for g in gates if g in ALARMED]
        if alarmed:
            lines.append("  alarm-covered gate(s) (no keeper regenerates them): "
                         + ", ".join(alarmed))
        lines.append("  master is red and no PR exists to repair it — this is the alarm that "
                     "makes it visible (issue #527).")
        return 1, "\n".join(lines)
    # pending / in_progress / skipped: not a verdict yet, not an alarm.
    return 0, (f"[master-alarm] OK: newest push-to-master run {run.get('databaseId')} is "
               f"{conclusion} — not a failure, nothing to alarm.")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description="Fail when the newest push-to-master qa-validate run is red (issue #527)")
    ap.add_argument("--repo", required=True, help="owner/name")
    ap.add_argument("--limit", type=int, default=10, help="how many push runs to read")
    args = ap.parse_args(argv)
    rc, msg = verdict(args.repo, args.limit)
    print(msg)
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
