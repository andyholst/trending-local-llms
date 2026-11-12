#!/usr/bin/env python3
"""check_workflow_guards.py — the tree-wide identity-guard scan (AGENTS.md §6j, issue #816).

§6j: only the owner, a collaborator with write/maintain/admin, or `github-actions[bot]`
may start a pipeline; the guard is the FIRST job (every other job needs it) and touches
no secret. This stage makes that a property of the TREE: it scans EVERY
`.github/workflows/*.yml` — never a hand-kept list (a list is what rots) — and asserts,
for the triggers each workflow declares itself:

  * every workflow carries a guard job (derived by scanning, not remembered);
  * the guard job needs nothing, every other job needs the guard (transitively);
  * the guard job declares no secret and no guard step touches one;
  * the REAL guard script is executed for every caller class: owner, write/maintain/
    admin collaborator and the bot are ALLOWED; a read-only or triage collaborator, a
    non-collaborator, and a stranger re-running an owner's run are REFUSED;
  * a workflow with `on.schedule` carries the schedule bypass and passes a scheduled
    run with NO usable caller identity — a cron starts mechanically, from no human;
  * a repository event the workflow declares (`pull_request`, `push`, `issues`) is
    admitted regardless of actor — GitHub starts it for the repository itself, and a PR
    must be validated whatever its author (issue #771 extended this to `issues`);
  * NO job anywhere uses `environment:` — an approval-gated start is a human in the
    loop, and the owner's directive (2026-11-12) is that a pipeline never waits on a
    human to start.

The guard scripts are executed as written (bash), with a stub `gh` on PATH standing in
for the collaborator-permission API (an EXTERNAL system only — the production guard
script itself runs, rule 6m).

`make lint` is already the first gate of qa-validate's `validate` job and of
scripts/fix_loop.sh, so bundling this check into lint (rule 6m) makes every PR, every
bot round and every human run execute it.

Exit 0 = every workflow guarded for its triggers. Exit 1 = offenders named. Exit 2 =
the tree itself could not be read — never a silent clean.
"""
from __future__ import annotations

import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

WF_DIR = ".github/workflows"

#: Events GitHub starts for the repository itself (there is no caller to admit).
REPO_EVENTS = ("pull_request", "push", "issues")

#: The caller classes every guard must decide the same way (issue #238). The bot
#: itself is a bot-to-bot dispatch with the default token; it MUST be allowed.
#: This is the ONE table — tests import it instead of keeping a copy (rule 6d).
GUARD_CALLERS = (
    ("workflow_dispatch", "andyholst", "andyholst", 0, "owner dispatch"),
    ("workflow_dispatch", "alice", "alice", 0, "write collaborator"),
    ("workflow_dispatch", "bob", "bob", 0, "maintain collaborator"),
    ("workflow_dispatch", "carol", "andyholst", 0, "admin collaborator re-run of owner run"),
    ("workflow_dispatch", "github-actions[bot]", "github-actions[bot]", 0, "the bot itself"),
    ("workflow_dispatch", "eve", "eve", 1, "read-only collaborator"),
    ("workflow_dispatch", "mallory", "mallory", 1, "triage collaborator"),
    ("workflow_dispatch", "stranger", "stranger", 1, "non-collaborator (API 404)"),
    ("workflow_dispatch", "andyholst", "stranger", 1, "stranger re-running an owner run"),
)

GUARD_PERMS = {"alice": "write", "bob": "maintain", "carol": "admin", "eve": "read", "mallory": "triage"}


# ---------------------------------------------------------------- parsing

def _block_scalar(lines: list[str], i: int, parent_indent: int) -> tuple[str, int]:
    """Read a `|` block scalar starting after line i; return (text, next_index)."""
    out: list[str] = []
    common: int | None = None
    while i < len(lines):
        line = lines[i]
        if not line.strip():
            out.append("")
            i += 1
            continue
        indent = len(line) - len(line.lstrip(" "))
        if indent <= parent_indent:
            break
        if common is None:
            common = indent
        out.append(line[common:] if indent >= common else line.lstrip(" "))
        i += 1
    while out and not out[-1].strip():
        out.pop()
    return "\n".join(out), i


def parse_workflow(text: str) -> dict:
    """Parse the parts of a workflow this check needs, stdlib-only (the runner host
    has no PyYAML; `make lint` runs on that host). Returns:

      {"on": [events...], "jobs": {name: {"needs": [...], "body": str,
                                          "steps": [{"name","run"}...]}}}
    """
    lines = text.split("\n")
    on_events: list[str] = []
    jobs: dict[str, dict] = {}
    i = 0
    n = len(lines)
    top_re = re.compile(r"^([A-Za-z_][A-Za-z0-9_-]*):\s*(.*)$")

    def sub_block(start: int) -> tuple[int, int]:
        """Range of a block whose keys sit at exactly 2 spaces, from `start`."""
        j = start
        while j < n:
            line = lines[j]
            if not line.strip() or line.lstrip().startswith("#"):
                j += 1
                continue
            indent = len(line) - len(line.lstrip(" "))
            if indent == 0:
                break
            j += 1
        return start, j

    while i < n:
        m = top_re.match(lines[i])
        if not m:
            i += 1
            continue
        key, rest = m.group(1), m.group(2).strip()
        if key == "on" or key == "true":  # YAML 1.1 parses bare `on:` as True
            lo, hi = sub_block(i + 1)
            for k in range(lo, hi):
                mm = re.match(r"^\s+([A-Za-z_][A-Za-z0-9_-]*):", lines[k])
                if mm and (len(lines[k]) - len(lines[k].lstrip(" "))) == 2:
                    on_events.append(mm.group(1))
            if rest:  # inline form: `on: [push, pull_request]` or `on: push`
                for ev in re.findall(r"[A-Za-z_][A-Za-z0-9_-]*", rest):
                    on_events.append(ev)
            i = max(hi, i + 1)
            continue
        if key == "jobs":
            lo = i + 1
            while lo < n and (not lines[lo].strip() or lines[lo].lstrip().startswith("#")):
                lo += 1
            j = lo
            while j < n:
                line = lines[j]
                if not line.strip():
                    j += 1
                    continue
                indent = len(line) - len(line.lstrip(" "))
                if indent == 0:
                    break
                mm = re.match(r"^  ([A-Za-z_][A-Za-z0-9_-]*):\s*$", line)
                if indent == 2 and mm:
                    name = mm.group(1)
                    body_start = j + 1
                    k = body_start
                    while k < n:
                        bl = lines[k]
                        if not bl.strip():
                            k += 1
                            continue
                        bi = len(bl) - len(bl.lstrip(" "))
                        if bi <= 2:
                            break
                        k += 1
                    body = "\n".join(lines[body_start:k])
                    needs: list[str] = []
                    mn = re.search(r"^    needs:\s*(.+)$", body, re.M)
                    if mn:
                        needs = [x.strip().strip('"\'') for x in re.findall(r"[A-Za-z_][A-Za-z0-9_-]*", mn.group(1))]
                    elif re.match(r"^    needs:\s*$", body, re.M):
                        mn2 = re.search(r"^    needs:\s*\n((?:      .+\n?)+)", body, re.M)
                        if mn2:
                            needs = [x.strip().lstrip("- ").strip().strip('"\'')
                                     for x in mn2.group(1).splitlines() if x.strip()]
                    steps: list[dict] = []
                    si = body_start
                    cur: dict | None = None
                    while si < k:
                        sm = re.match(r"^      - (?:name:\s*(.+))?$", lines[si])
                        if sm:
                            if cur:
                                steps.append(cur)
                            cur = {"name": (sm.group(1) or "").strip(), "run": ""}
                            si += 1
                            continue
                        rm = re.match(r"^        run:\s*\|?\s*$", lines[si])
                        if rm and cur is not None:
                            cur["run"], si = _block_scalar(lines, si + 1, 8)
                            continue
                        nm = re.match(r"^        name:\s*(.+)$", lines[si])
                        if nm and cur is not None and not cur["name"]:
                            cur["name"] = nm.group(1).strip()
                        si += 1
                    if cur:
                        steps.append(cur)
                    jobs[name] = {"needs": needs, "body": body, "steps": steps}
                    j = k
                    continue
                j += 1
            i = max(j, i + 1)
            continue
        i += 1
    return {"on": on_events, "jobs": jobs}


# ---------------------------------------------------------------- execution

def guard_ok(run: str) -> bool:
    """The shape §6j's guard must have: actor AND triggering actor checked against
    the owner, the bot, and the collaborator-permission API with write+ required."""
    return ("$OWNER" in run and "$TRIGGER" in run and "$ACTOR" in run
            and "collaborators/$u/permission" in run and "admin|maintain|write)" in run)


def run_guard_script(run: str, event: str, actor: str, trigger: str,
                     perms: dict, owner: str = "andyholst",
                     repo: str = "andyholst/trending-local-llms") -> tuple[int, str]:
    """Execute the REAL guard script from the workflow with a stub `gh` that answers
    the collaborator-permission API from `perms` (unknown user -> API 404). The stub
    stands in for the EXTERNAL API only; the production guard shell runs unchanged."""
    td = Path(tempfile.mkdtemp())
    (td / "perms").write_text("\n".join(f"{u}={p}" for u, p in perms.items()) + "\n")
    gh = td / "gh"
    gh.write_text(f"""#!/usr/bin/env bash
u=$(echo "$2" | sed -E 's#.*/collaborators/([^/]+)/permission#\\1#')
p=$(grep -E "^$u=" "{td}/perms" | cut -d= -f2)
[ -z "$p" ] && {{ echo '{{"message":"Not Found"}}' >&2; exit 1; }}
echo "$p"
""")
    gh.chmod(0o755)
    env = dict(os.environ, PATH=f"{td}:{os.environ['PATH']}", EVENT=event, ACTOR=actor,
               TRIGGER=trigger, OWNER=owner, REPO=repo, GH_TOKEN="x")
    p = subprocess.run(["bash", "-e", "-c", run], env=env, capture_output=True, text=True, timeout=30)
    return p.returncode, p.stdout


def find_guard_step(wf: dict) -> tuple[str, dict] | None:
    """(job_name, step) of this workflow's trigger guard, derived from the tree."""
    for job_name, body in wf["jobs"].items():
        for st in body["steps"]:
            if "guard" in st["name"].lower():
                return job_name, st
    return None


def _deps(jobs: dict, name: str) -> set[str]:
    out, todo = set(), [name]
    while todo:
        for d in jobs.get(todo.pop(), {}).get("needs", []):
            if d not in out:
                out.add(d)
                todo.append(d)
    return out


# ---------------------------------------------------------------- scan

def scan_workflow(name: str, wf: dict) -> list[str]:
    """Every way this workflow fails §6j's guard rule, as problem strings."""
    problems: list[str] = []
    jobs = wf["jobs"]
    hit = find_guard_step(wf)
    if hit is None:
        return [f"{name}: no guard job found (every pipeline carries its guard as its own job)"]
    guard_job, step = hit
    body = jobs[guard_job]

    if body["needs"]:
        problems.append(f"{name}: guard job '{guard_job}' needs {body['needs']} — the guard needs nothing")
    if "secrets." in body["body"]:
        problems.append(f"{name}: guard job '{guard_job}' declares or touches a secret — the guard runs before any secret")
    if not guard_ok(step["run"]):
        problems.append(f"{name}: guard script does not decide owner / $TRIGGER / $ACTOR against the permission API with write+")
    for other in jobs:
        if other != guard_job and guard_job not in _deps(jobs, other):
            problems.append(f"{name}: job '{other}' does not need the guard — it can run before it")
    for other, ob in jobs.items():
        if re.search(r"^    environment:\s*\S", ob["body"], re.M):
            problems.append(f"{name}: job '{other}' uses environment: — an approval gate is a human gate (owner directive: no pipeline waits on a human to start)")

    has_cron = "schedule" in wf["on"]
    if has_cron:
        if '"schedule"' not in step["run"]:
            problems.append(f"{name}: a cron pipeline without the schedule bypass — a scheduled start would depend on who GitHub credits and can stall")
        rc, out = run_guard_script(step["run"], "schedule", "", "", GUARD_PERMS)
        if rc != 0:
            problems.append(f"{name}: schedule bypass refused a scheduled run with no caller identity (rc={rc}: {out.strip()[-120:]})")

    for event in wf["on"]:
        if event in REPO_EVENTS:
            rc, out = run_guard_script(step["run"], event, "stranger", "stranger", GUARD_PERMS)
            if rc != 0:
                problems.append(f"{name}: a guard must admit the repository event '{event}' whatever its actor (a PR is validated whatever its author) — refused (rc={rc}: {out.strip()[-120:]})")
        if event == "workflow_dispatch":
            for ev, actor, trigger, want, label in GUARD_CALLERS:
                rc, out = run_guard_script(step["run"], ev, actor, trigger, GUARD_PERMS)
                if (rc == 0) != (want == 0):
                    verdict = "allow" if want == 0 else "refuse"
                    problems.append(f"{name}: guard must {verdict} {label} (rc={rc}: {out.strip()[-120:]})")

    if "workflow_dispatch" not in wf["on"] and "schedule" not in wf["on"]:
        # A purely event-driven pipeline (no dispatch, no cron): the caller classes
        # still must be refused on its dispatchable surface if one appears later;
        # for now its declared events fully determine the decision surface.
        for event in wf["on"]:
            if event not in REPO_EVENTS:
                problems.append(f"{name}: trigger '{event}' is neither a repository event nor guarded by caller class")
    return problems


def scan_tree(root: Path) -> tuple[list[str], list[str]]:
    """(reports, problems) over EVERY workflow .yml in the tree."""
    wf_dir = root / WF_DIR
    if not wf_dir.is_dir():
        raise FileNotFoundError(f"{wf_dir} not found")
    reports: list[str] = []
    problems: list[str] = []
    files = sorted(wf_dir.glob("*.yml")) + sorted(wf_dir.glob("*.yaml"))
    if not files:
        raise FileNotFoundError(f"{wf_dir} holds no workflows")
    for f in files:
        try:
            wf = parse_workflow(f.read_text())
        except Exception as exc:  # an unreadable workflow is loud, never clean
            problems.append(f"{f.name}: cannot parse ({exc})")
            continue
        probs = scan_workflow(f.name, wf)
        problems.extend(probs)
        hit = find_guard_step(wf)
        guard = hit[0] if hit else "MISSING"
        events = ",".join(wf["on"]) or "-"
        reports.append(f"GUARD {f.name}: guard-job={guard} triggers={events} "
                       f"repo-events-admitted={any(e in REPO_EVENTS for e in wf['on'])} "
                       f"cron={'yes' if 'schedule' in wf['on'] else 'no'} "
                       f"{'OK' if not probs else 'RED'}")
    return reports, problems


def main(argv: list[str] | None = None) -> int:
    argv = argv if argv is not None else sys.argv[1:]
    root = Path(argv[0]) if argv else Path(__file__).resolve().parent.parent
    try:
        reports, problems = scan_tree(root)
    except FileNotFoundError as exc:
        print(f"workflow-guard-scan: cannot read the tree: {exc}", file=sys.stderr)
        return 2
    for r in reports:
        print(r)
    if problems:
        print(f"workflow-guard-scan: {len(problems)} problem(s):")
        for p in problems:
            print(f"  RED {p}")
        return 1
    print(f"workflow-guard-scan: OK — {len(reports)} workflows scanned, every guard in place "
          "for its triggers (no environment: gate, every cron admitted, every repository event admitted).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
