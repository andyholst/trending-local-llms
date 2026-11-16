#!/usr/bin/env python3
"""An INVALID ACTIVE OpenSpec change goes red AND gets its named repairer (issue #962).

Drives the REAL `scripts/openspec_invalid_change_repair.py` (classifier + repairer),
the REAL verdict seam `scripts/openspec_index_repair.py`, the REAL generator
`scripts/openspec_index.py`, the REAL binding gate `scripts/openspec_binding_check.py`
and the REAL closure parser `scripts/pr_closure.py` against planted fixture trees
(external system only — a fixture directory, rule 6m).

The measured failure this suite locks out: push `aec1410` / run 43610043055 put an
active change on `master` as a bare `openspec/changes/<name>/proposal.md` — no
`specs/<capability>/spec.md`, no `tasks.md`. `openspec validate --changes` refused it,
`make openspec-check` went red on every open PR, and the ONLY keeper of that gate
answered `DRIFT=none` because the index really was current. Auto-merge stayed blocked
repo-wide with a named cause and no named repairer.

Planted shapes this suite refuses: an incomplete ACTIVE change that passes silently;
a verdict seam that launders it as `DRIFT=none` or as an index rewrite; a keeper that
COMPLETES a change it cannot know (invented spec/tasks — rule 2); a repair that moves
something the index cannot follow; a keeper body that closes an issue its branch does
not implement (rule 6e); an unreadable tree reported as a clean run.

Run:  python3 tests/test_openspec_invalid_change_repair.py   or   make test
"""
from __future__ import annotations

import contextlib
import importlib
import io
import re
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "scripts" / "openspec_invalid_change_repair.py"
sys.path.insert(0, str(ROOT / "scripts"))

import openspec_binding_check  # noqa: E402  (the REAL #952 gate, for the exemption shape)
import openspec_index  # noqa: E402  (the ONE generator)
import openspec_invalid_change_repair as repairer  # noqa: E402  (the classifier itself)
import openspec_index_repair as real_index_repair  # noqa: E402  (the ONE verdict seam)
import pr_closure  # noqa: E402  (the ONE closure parser)

_PASS = 0
_FAIL = 0


def check(name, cond, detail: object = ""):
    global _PASS, _FAIL
    if cond:
        _PASS += 1
        print(f"  ok  {name}")
    else:
        _FAIL += 1
        print(f"  FAIL {name}" + (f"  [{detail}]" if detail else ""))


def run(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(SCRIPT), *args],
                          text=True, capture_output=True, timeout=180)


# --- planted trees ----------------------------------------------------------

VALID_PROPOSAL = """# Proposal: {name}

Issue: #962

## Why

A change that shipped complete: it carries its proposal, its capability spec and its
task list (rule 6f).

## What Changes

- one honest change

## Impact

- the gate stays green
"""

VALID_SPEC = """## ADDED Requirements

### Requirement: A complete change names its requirement

It does, in the tree.

#### Scenario: the gate reads a complete change

- **Given** an active change with proposal.md, a capability spec and a task list
- **When** `make openspec-invalid-change-check` reads it
- **Then** it is not classified invalid
- **Test:** tests/test_openspec_invalid_change_repair.py::test_a_structurally_complete_change_is_never_archived
"""

VALID_TASKS = """# Tasks

- [x] 1. The change was implemented and verified
"""

BARE_PROPOSAL = """# Proposal: bare-invalid-change

Issue: #962

## Why

This change reached `master` as a proposal alone — the shape run 43610043055 shipped.

## What Changes

- (never written)
"""


def tree(root: Path, *, complete: bool = True, bare: bool = True,
         tasks_with_boxes: bool = True) -> Path:
    """Plant an `openspec/changes/` tree under `root`."""
    changes = root / "openspec" / "changes"
    if complete:
        spec_dir = changes / "complete-change" / "specs" / "capability"
        spec_dir.mkdir(parents=True)
        (changes / "complete-change" / "proposal.md").write_text(
            VALID_PROPOSAL.format(name="complete-change"), encoding="utf-8")
        (spec_dir / "spec.md").write_text(VALID_SPEC, encoding="utf-8")
        (changes / "complete-change" / "tasks.md").write_text(
            VALID_TASKS if tasks_with_boxes else "# Tasks\n\n(no boxes)\n", encoding="utf-8")
    if bare:
        bare_dir = changes / "bare-invalid-change"
        bare_dir.mkdir(parents=True)
        (bare_dir / "proposal.md").write_text(BARE_PROPOSAL, encoding="utf-8")
    return root


def write_current_index(root: Path) -> str:
    """Generate the index for `root` through the ONE generator; return its text."""
    openspec_index.ROOT = root
    openspec_index.CHANGES = root / "openspec" / "changes"
    openspec_index.INDEX = root / "OPENSPEC.md"
    openspec_index.main(["--write"])
    return (root / "OPENSPEC.md").read_text(encoding="utf-8")


def index_check(root: Path) -> int:
    openspec_index.ROOT = root
    openspec_index.CHANGES = root / "openspec" / "changes"
    openspec_index.INDEX = root / "OPENSPEC.md"
    return openspec_index.main(["--check"])


def index_repair_for(root: Path):
    """The REAL verdict seam pointed at `root` (the same harness
    tests/test_openspec_index_repair.py uses: the seam's own module globals, no stub
    of any product symbol)."""
    ir = importlib.reload(real_index_repair)
    ir.oi = importlib.reload(openspec_index)
    ir.oi.ROOT = root
    ir.oi.CHANGES = root / "openspec" / "changes"
    ir.oi.INDEX = root / "OPENSPEC.md"
    return ir


def seam_classify(root: Path) -> tuple[int, str]:
    ir = index_repair_for(root)
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
        rc = ir.main(["--classify-and-write"])
    return rc, buf.getvalue()


def job_block(yml: str, job: str) -> str:
    """One job's YAML block from a workflow file (its own lines, nothing else)."""
    out: list[str] = []
    inside = False
    for line in yml.splitlines():
        if re.match(rf"^  {re.escape(job)}:\s*$", line):
            inside = True
            out.append(line)
            continue
        if inside:
            if re.match(r"^  \S", line) or re.match(r"^\S", line):
                break
            out.append(line)
    return "\n".join(out)


def today() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


# --- 1. the classifier goes red, naming the change and the remedy -----------

def test_an_invalid_active_change_goes_red_naming_the_change_and_the_remedy():
    with tempfile.TemporaryDirectory() as tmp:
        root = tree(Path(tmp))
        r = run("--check", "--root", str(root))
        out = r.stdout + r.stderr
        check("--check exits 1 on a proposal-only ACTIVE change", r.returncode == 1,
              f"rc={r.returncode} {out[:120]}")
        check("the offender is named", "bare-invalid-change" in out, out[:160])
        check("the missing capability spec is named", "specs/<capability>/spec.md" in out)
        check("the missing task list is named", "tasks.md" in out)
        check("the exact archive remedy is printed",
              "make openspec-invalid-change-repair" in out)
        check("the named keeper job is printed", "invalid-change-repair" in out)
        check("the complete change is NOT named",
              "complete-change" not in out.replace("bare-invalid-change", ""), out[:200])
        # the classifier is also callable in-process: one shape, one definition
        found = repairer.invalid_active_changes(root / "openspec" / "changes")
        check("the classifier returns (name, problems) for the offender",
              [n for n, _ in found] == ["bare-invalid-change"], found)
        # a tasks.md with no `- [ ]` box is a missing checklist, not a checked one
        root2 = tree(Path(tmp) / "no-boxes", complete=False, bare=False)
        (root2 / "openspec/changes/complete-change").mkdir(parents=True)
        (root2 / "openspec/changes/complete-change/specs/capability").mkdir(parents=True)
        (root2 / "openspec/changes/complete-change/proposal.md").write_text(
            VALID_PROPOSAL.format(name="complete-change"), encoding="utf-8")
        (root2 / "openspec/changes/complete-change/specs/capability/spec.md").write_text(
            VALID_SPEC, encoding="utf-8")
        (root2 / "openspec/changes/complete-change/tasks.md").write_text(
            "# Tasks\n\n- the work, unboxed\n", encoding="utf-8")
        r2 = run("--check", "--root", str(root2))
        check("a tasks.md with no checklist box is invalid", r2.returncode == 1,
              f"rc={r2.returncode}")
        check("it is named as the missing checklist",
              "checklist" in r2.stdout + r2.stderr, r2.stderr[:160])
        # a change with a spec but no proposal is also invalid
        root3 = Path(tmp) / "no-proposal" / "openspec/changes" / "no-proposal"
        (root3 / "specs/capability").mkdir(parents=True)
        (root3 / "specs/capability/spec.md").write_text(VALID_SPEC, encoding="utf-8")
        (root3 / "tasks.md").write_text(VALID_TASKS, encoding="utf-8")
        r3 = run("--check", "--root", str(root3.parent.parent.parent))
        check("a change with no proposal.md is invalid", r3.returncode == 1,
              f"rc={r3.returncode}")
        check("the missing proposal is named", "proposal.md" in r3.stdout + r3.stderr)


# --- 2. the ONE verdict seam classifies the shape before touching the index --

def test_the_verdict_seam_classifies_the_invalid_change_before_the_index():
    with tempfile.TemporaryDirectory() as tmp:
        root = tree(Path(tmp))
        # the index is ALSO stale here: the invalid classification must win, and the
        # index must NOT be rewritten (a regenerated index would only catalogue the
        # incomplete change).
        (root / "OPENSPEC.md").write_text("# Index\n\n(stale: written before the change)\n",
                                          encoding="utf-8")
        stale = (root / "OPENSPEC.md").read_text(encoding="utf-8")
        rc, printed = seam_classify(root)
        check("the seam exits 0 with a verdict (the workflow branches on the line)",
              rc == 0, f"rc={rc}")
        check("the verdict is DRIFT=invalid-change", "DRIFT=invalid-change" in printed,
              printed[:200])
        check("the seam names the offender", "bare-invalid-change" in printed, printed[:200])
        check("the seam names the repairer",
              "make openspec-invalid-change-repair" in printed, printed[:240])
        check("the seam refuses to call this index staleness",
              "NOT index staleness" in printed, printed[:240])
        check("the seam does NOT claim an index-only repair beside an invalid change",
              "DRIFT=index-only" not in printed, printed[:240])
        check("the index is left exactly as it was",
              (root / "OPENSPEC.md").read_text(encoding="utf-8") == stale)
        check("the seam shares the classifier instead of re-spelling it",
              "invalid_active_changes" in
              (ROOT / "scripts" / "openspec_index_repair.py").read_text(encoding="utf-8"))
        seam_src = (ROOT / "scripts" / "openspec_index_repair.py").read_text(encoding="utf-8")
        check("the seam writes no spec or task content of its own",
              not re.search(r"(write_text|mkdir).*(spec\.md|tasks\.md)", seam_src),
              "the seam fabricates change content")


# --- 3. the seam still lands the index-only repair it always landed ----------

def test_the_seam_still_lands_an_index_only_repair_beside_valid_changes():
    with tempfile.TemporaryDirectory() as tmp:
        root = tree(Path(tmp), bare=False)
        (root / "OPENSPEC.md").write_text("# Index\n\n(stale)\n", encoding="utf-8")
        rc, printed = seam_classify(root)
        check("a complete tree with a stale index is still index-only",
              "DRIFT=index-only" in printed, f"rc={rc} {printed[:200]}")
        check("the verdict is not invalid-change for a complete tree",
              "DRIFT=invalid-change" not in printed, printed[:200])
        check("the regenerated index is current by the generator's own verdict",
              index_check(root) == 0)
        check("the regenerated index carries the change's row",
              bool(re.search(r"^\| `complete-change` \|",
                             (root / "OPENSPEC.md").read_text(encoding="utf-8"),
                             re.MULTILINE)),
              (root / "OPENSPEC.md").read_text(encoding="utf-8")[:400])
        # a green tree (index already current) is DRIFT=none — the existing answer
        write_current_index(root)
        rc2, printed2 = seam_classify(root)
        check("a current index beside complete changes stays DRIFT=none",
              "DRIFT=none" in printed2, f"rc={rc2} {printed2[:200]}")


# --- 4. the repair archives it and the index stays current ------------------

def test_the_repair_archives_the_invalid_change_and_the_index_stays_current():
    with tempfile.TemporaryDirectory() as tmp:
        root = tree(Path(tmp))
        write_current_index(root)
        check("the planted index is current before the repair", index_check(root) == 0)
        r = run("--classify-and-archive", "--root", str(root), "--run-id", "43610043055")
        out = r.stdout + r.stderr
        check("--classify-and-archive exits 0 after a landed archive", r.returncode == 0,
              f"rc={r.returncode} {out[:200]}")
        check("the verdict line names the landed archive",
              "REPAIR=archived" in out and "bare-invalid-change" in out, out[:240])
        active = root / "openspec/changes/bare-invalid-change"
        archived = root / "openspec/changes/archive" / f"{today()}-bare-invalid-change"
        check("the incomplete change is no longer ACTIVE", not active.exists())
        check("the archive name follows the archive convention (<UTC-date>-<name>)",
              archived.is_dir(), str(archived))
        check("the archive directory is the ONE the archive convention uses",
              (root / "openspec/changes/archive").is_dir())
        check("the regenerated index is current after the move", index_check(root) == 0,
              "openspec_index.py --check refused the rewritten index")
        check("the regenerated index lists the archived change",
              "bare-invalid-change" in (root / "OPENSPEC.md").read_text(encoding="utf-8"))
        check("the index reports it as archived",
              bool(re.search(r"bare-invalid-change.*archived",
                             (root / "OPENSPEC.md").read_text(encoding="utf-8"))))
        check("the classifier now reports nothing to repair",
              run("--check", "--root", str(root)).returncode == 0)
        # the REAL binding gate no longer sees the change as ACTIVE, and the tree it
        # does see is green
        rc_bind = openspec_binding_check.main(
            ["--changes-dir", str(root / "openspec/changes")])
        check("the real binding gate is green on the repaired tree", rc_bind == 0,
              f"rc={rc_bind}")


# --- 5. the archived proposal declares the exemption; nothing is invented ---

def test_the_archived_proposal_carries_the_keeper_exemption_and_no_fabricated_content():
    with tempfile.TemporaryDirectory() as tmp:
        root = tree(Path(tmp))
        write_current_index(root)
        r = run("--classify-and-archive", "--root", str(root), "--run-id", "43610043055")
        check("the repair landed", r.returncode == 0, f"rc={r.returncode}")
        archived = root / "openspec/changes/archive" / f"{today()}-bare-invalid-change"
        text = (archived / "proposal.md").read_text(encoding="utf-8")
        check("the archived proposal carries the #952 exemption line",
              "Binding-exempt: invalid active change repaired by keeper (43610043055)"
              in text, text[:200])
        m = openspec_binding_check.EXEMPT_RE.search(text)
        check("the exemption line is the shape the real binding gate parses",
              m is not None and m.group(1).strip()
              == "invalid active change repaired by keeper (43610043055)",
              m.group(0) if m else "no match")
        # prove the exemption shape is accepted BY THE GATE: an exempt ACTIVE change
        # (no Issue line) is green and reported
        exempt_tree = Path(tmp) / "exempt" / "openspec/changes" / "keeper-change"
        exempt_tree.mkdir(parents=True)
        (exempt_tree / "proposal.md").write_text(
            "# Proposal: keeper-change\n\n"
            "Binding-exempt: index keeper repair, implements no issue\n\n## Why\n\nx\n",
            encoding="utf-8")
        rc = openspec_binding_check.main(["--changes-dir", str(exempt_tree.parent)])
        check("the real gate accepts a declared exemption (issue #952 shape)", rc == 0,
              f"rc={rc}")
        # nothing was invented
        files = sorted(p.relative_to(archived).as_posix() for p in archived.rglob("*")
                       if p.is_file())
        check("the archive holds only the proposal it arrived with (no fabricated spec)",
              files == ["proposal.md"], files)
        check("no spec.md was fabricated anywhere under archive/",
              not list((root / "openspec/changes/archive").rglob("spec.md")))
        check("no tasks.md was fabricated anywhere under archive/",
              not list((root / "openspec/changes/archive").rglob("tasks.md")))
        check("the proposal's own words survived the move",
              "the shape run 43610043055 shipped" in text, text[:200])


# --- 6. a complete change is never archived, even with unticked boxes -------

def test_a_structurally_complete_change_is_never_archived():
    with tempfile.TemporaryDirectory() as tmp:
        root = tree(Path(tmp), bare=False)
        (root / "openspec/changes/complete-change/tasks.md").write_text(
            "# Tasks\n\n- [ ] 1. Not done yet\n- [x] 2. Done\n", encoding="utf-8")
        write_current_index(root)
        before = sorted(p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file())
        r = run("--classify-and-archive", "--root", str(root), "--run-id", "42")
        out = r.stdout + r.stderr
        check("--classify-and-archive exits 0 when nothing is invalid", r.returncode == 0,
              f"rc={r.returncode} {out[:200]}")
        check("the verdict is REPAIR=none", "REPAIR=none" in out, out[:200])
        after = sorted(p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file())
        check("no change moved", before == after, f"{before} -> {after}")
        check("no archive directory appeared",
              not (root / "openspec/changes/archive").exists())
        check("the index stayed current", index_check(root) == 0)
        # a spec without its capability dir is still invalid: 'complete' is structural
        r2 = run("--check", "--root", str(root))
        check("a change with unticked boxes is still structurally complete",
              r2.returncode == 0, r2.stderr[:200])


# --- 7. the gate + keeper wiring --------------------------------------------

def test_the_check_and_the_repair_are_wired_into_the_gate_and_the_keeper_job():
    makefile = (ROOT / "Makefile").read_text(encoding="utf-8")
    qa = (ROOT / ".github" / "workflows" / "qa-validate.yml").read_text(encoding="utf-8")
    script_src = (ROOT / "scripts" / "openspec_invalid_change_repair.py").read_text(
        encoding="utf-8")

    gate = re.search(r"^openspec-check:.*$", makefile, re.MULTILINE)
    check("openspec-check names the structural check as a prerequisite",
          gate is not None and "openspec-invalid-change-check" in gate.group(0),
          gate.group(0)[:160] if gate else "no openspec-check target")
    check("the three OpenSpec structural gates are prerequisites together",
          gate is not None and all(t in gate.group(0) for t in ("openspec-backlog-check",
                                                                "openspec-binding-check",
                                                                "openspec-invalid-change-check")),
          gate.group(0)[:240] if gate else "")
    check("every new target is .PHONY-registered",
          bool(re.search(r"^\.PHONY:.*openspec-invalid-change-check.*$", makefile,
                         re.MULTILINE))
          and bool(re.search(r"^\.PHONY:.*openspec-invalid-change-repair.*$", makefile,
                             re.MULTILINE)),
          re.findall(r"^\.PHONY:.*openspec-invalid.*$", makefile, re.MULTILINE))
    check_recipe = re.search(r"^openspec-invalid-change-check:.*\n(?:\t.*\n)+", makefile,
                             re.MULTILINE)
    check("the check target runs the real classifier host-side",
          check_recipe is not None
          and "scripts/openspec_invalid_change_repair.py --check" in check_recipe.group(0),
          check_recipe.group(0) if check_recipe else "no recipe")
    repair_recipe = re.search(r"^openspec-invalid-change-repair:.*\n(?:\t.*\n)+", makefile,
                              re.MULTILINE)
    check("the repair target runs the real repairer host-side",
          repair_recipe is not None
          and "scripts/openspec_invalid_change_repair.py --classify-and-archive"
          in repair_recipe.group(0),
          repair_recipe.group(0) if repair_recipe else "no recipe")
    body_recipe = re.search(r"^openspec-invalid-change-repair-pr-body:.*\n(?:\t.*\n)+",
                            makefile, re.MULTILINE)
    check("the keeper body target composes the body through the script seam",
          body_recipe is not None
          and "scripts/openspec_invalid_change_repair.py --print-pr-body"
          in body_recipe.group(0) and "--print-pr-body" in script_src,
          body_recipe.group(0) if body_recipe else "no recipe")

    job_text = job_block(qa, "invalid-change-repair")
    check("qa-validate carries the invalid-change-repair keeper job", bool(job_text),
          "job missing")
    check("the keeper job needs the guard (rule 6j)", "needs: [guard, validate]" in job_text,
          job_text[:120])
    check("the keeper job fires only on a failed push to master",
          "github.event_name == 'push'" in job_text and "refs/heads/master" in job_text
          and "failure()" in job_text, job_text[:240])
    steps = "\n".join(l for l in job_text.splitlines() if not l.strip().startswith("#"))
    check("the keeper job reaches the product only through make (rule 6m)",
          "make openspec-invalid-change-repair" in steps and "scripts/" not in steps,
          steps[:240])
    check("the keeper job lands nothing on REPAIR=none",
          "REPAIR=none" in steps, steps[:300])
    check("the keeper job refuses a drift wider than the archive + index",
          "refusing to land" in steps, steps[:400])
    check("the keeper job honours only a MERGEABLE open keeper (#960)",
          "mergeStateStatus" in steps and "UNMERGEABLE" in steps, steps[:600])
    check("the keeper job never merges", "gh pr merge" not in steps)
    check("the keeper job never pushes master", "git push origin master" not in steps)
    check("the keeper branch carries the keeper prefix",
          "ci/openspec-invalid-change-repair-" in steps)
    check("the keeper body is composed by make, not by the workflow",
          "make openspec-invalid-change-repair-pr-body" in steps)
    check("auto-merge still needs only validate + live-smoke (a keeper never joins it)",
          bool(re.search(r"auto-merge:\n(?:.*\n)*?    needs: \[validate, live-smoke\]",
                         qa)))
    check("the index keeper still classifies through the same seam",
          "make openspec-index-repair" in qa)
    check("no workflow step reaches the new script past the Makefile",
          "python3 scripts/openspec_invalid_change_repair.py" not in qa)
    check("the new target is called by a pipeline (rule 6m)",
          "make openspec-invalid-change-repair" in qa)


# --- 8. the keeper body records the drift and closes nothing ----------------

def test_the_keeper_body_records_the_drift_and_closes_nothing():
    with tempfile.TemporaryDirectory() as tmp:
        root = tree(Path(tmp))
        r = run("--print-pr-body", "--root", str(root),
                "--master-sha", "aec1410abcdeffe",
                "--run-url", "https://github.com/andyholst/trending-local-llms/actions/runs/43610043055",
                "--run-id", "43610043055")
        check("--print-pr-body exits 0", r.returncode == 0, f"rc={r.returncode}")
        body = r.stdout
        check("the body names the exact red run", "43610043055" in body)
        check("the body names the exact master commit", "aec1410" in body)
        check("the body names the gate that went red", "make openspec-check" in body)
        check("the body names the named repairer",
              "make openspec-invalid-change-repair" in body)
        check("the body declares the exemption it stamped",
              "Binding-exempt" in body and "43610043055" in body)
        check("the body tracks the keeper's own change shape", "#962" in body)
        branch = f"ci/openspec-invalid-change-repair-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"
        check("the body carries no closing keyword (a keeper records, never closes)",
              not any(line.strip().lower().startswith(("closes ", "close ", "fixes ",
                                                       "fix ", "resolves ", "resolve "))
                      for line in body.splitlines()),
              [l for l in body.splitlines() if l.lower().startswith("closes")])
        check("the closure parser finds no closing binding in the body",
              pr_closure.closing_bindings(body) == [], pr_closure.closing_bindings(body))
        check("the keeper branch implements no issue",
              pr_closure.implemented_issue(branch) is None,
              pr_closure.implemented_issue(branch))
        check("the real closure check accepts the keeper shape",
              pr_closure.check(body, branch) == [], pr_closure.check(body, branch))
        missing = run("--print-pr-body", "--root", str(root))
        check("--print-pr-body without the run refuses loudly", missing.returncode == 2,
              f"rc={missing.returncode}")


# --- 9. an unreadable tree / a collision is a loud exit 2 -------------------

def test_an_unreadable_tree_is_a_loud_exit_2_never_a_silent_clean():
    with tempfile.TemporaryDirectory() as tmp:
        missing = Path(tmp) / "no-such-tree"
        r = run("--check", "--root", str(missing))
        check("--check on a missing change tree exits 2", r.returncode == 2,
              f"rc={r.returncode}")
        check("--check names the path it could not read", str(missing) in r.stderr,
              r.stderr[:160])
        check("--check never reports OK for a tree it cannot read",
              "OK" not in r.stdout, r.stdout[:160])
        r2 = run("--classify-and-archive", "--root", str(missing))
        check("--classify-and-archive on a missing tree exits 2", r2.returncode == 2,
              f"rc={r2.returncode}")
        check("the refusal says a silent clean is refused",
              "silent" in r2.stderr, r2.stderr[:200])
        check("nothing was created by the refused repair", not missing.exists())

        # archive destination already exists: refuse, never overwrite or merge
        root = tree(Path(tmp) / "collision")
        dest = root / "openspec/changes" / "archive" / f"{today()}-bare-invalid-change"
        dest.mkdir(parents=True)
        (dest / "proposal.md").write_text("# already archived, untouched\n", encoding="utf-8")
        r3 = run("--classify-and-archive", "--root", str(root), "--run-id", "42")
        out3 = r3.stdout + r3.stderr
        check("a colliding archive destination is a loud exit 2", r3.returncode == 2,
              f"rc={r3.returncode} {out3[:200]}")
        check("the collision names the destination", "already exists" in out3, out3[:240])
        check("the active change was NOT moved out from under the collision",
              (root / "openspec/changes/bare-invalid-change").exists())
        check("the existing archive was NOT overwritten",
              (dest / "proposal.md").read_text(encoding="utf-8")
              == "# already archived, untouched\n")

        # no arguments asked: the seam refuses instead of defaulting to a repair
        r4 = run()
        check("a call that asks for nothing refuses (exit 2)", r4.returncode == 2,
              f"rc={r4.returncode}")


def main() -> int:
    for t in (test_an_invalid_active_change_goes_red_naming_the_change_and_the_remedy,
              test_the_verdict_seam_classifies_the_invalid_change_before_the_index,
              test_the_seam_still_lands_an_index_only_repair_beside_valid_changes,
              test_the_repair_archives_the_invalid_change_and_the_index_stays_current,
              test_the_archived_proposal_carries_the_keeper_exemption_and_no_fabricated_content,
              test_a_structurally_complete_change_is_never_archived,
              test_the_check_and_the_repair_are_wired_into_the_gate_and_the_keeper_job,
              test_the_keeper_body_records_the_drift_and_closes_nothing,
              test_an_unreadable_tree_is_a_loud_exit_2_never_a_silent_clean):
        print(f"\n[{t.__name__}]")
        t()
    print(f"\n{_PASS} passed, {_FAIL} failed")
    return 1 if _FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
