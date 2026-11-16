#!/usr/bin/env python3
"""Name and repair the OTHER way `make openspec-check` goes red: an INVALID ACTIVE CHANGE (issue #962).

qa-validate's `index-repair` keeper classifies a red OpenSpec gate through
`scripts/openspec_index_repair.py`, whose verdict could only ever be
`DRIFT=none|index-only`. Measured on run 43610043055 (push `aec1410`): an ACTIVE
change reached `master` as a bare `openspec/changes/<name>/proposal.md` — no
`specs/<capability>/spec.md`, no `tasks.md` — `openspec validate --changes`
refused it, every open PR's `validate` went red, and the keeper answered
`DRIFT=none` because the index really was current. A red the keeper cannot own
has no repairer: nothing landed until an unrelated keeper PR arrived.

`make openspec-tasks-check` cannot see this shape either — it walks only the
changes that HAVE a `tasks.md`, so a change that ships without one is skipped in
silence and only the container CLI notices. This script is the deterministic
Python half (it runs in the checkout and in CI, no image needed) and the honest
repairer.

  --check
      exit 0  every ACTIVE change carries proposal.md, at least one
              specs/<capability>/spec.md and a tasks.md with a checklist
      exit 1  an ACTIVE change does not: each is named with the artifact that is
              missing and the exact remedy (`make openspec-invalid-change-repair`)
      exit 2  the changes tree cannot be read — loud, never a vacuous clean

  --classify-and-archive
      REPAIR=none      nothing invalid — nothing is moved, nothing is written
      REPAIR=archived  every invalid ACTIVE change was MOVED to
                       `openspec/changes/archive/<UTC-date>-<name>/` (the archive
                       convention 41 of this repo's archived changes already use),
                       its proposal stamped
                       `Binding-exempt: invalid active change repaired by keeper (<run id>)`
                       — the #952 exemption shape — and the index regenerated
      exit 2  the tree cannot be read, or an archive destination already exists

      The repairer NEVER writes the missing spec or task list. Rule 2 forbids
      invented content, and a spec authored by a keeper would launder an
      unreviewed change into a validated one: the only honest end for a change
      nobody wrote is the archive, declaring what it was.

  --print-pr-body
      The keeper PR body: records the repair, `refs` #962, carries NO closing
      keyword (rule 6e — a keeper implements no issue).

Local equivalent:
  make openspec-invalid-change-check
  make openspec-invalid-change-repair [RUN_ID=<ci run id>]
  make openspec-invalid-change-repair-pr-body MASTER_SHA=<sha> RUN_URL=<url>

Usage:
    python3 scripts/openspec_invalid_change_repair.py --check
    python3 scripts/openspec_invalid_change_repair.py --classify-and-archive --run-id 43610043055
    python3 scripts/openspec_invalid_change_repair.py --check --root <tree>   # fixture seam
"""
from __future__ import annotations

import argparse
import datetime as dt
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import openspec_index  # noqa: E402  the ONE proposal parser + index generator (rule 6d)
import task_boxes  # noqa: E402      the ONE checkbox vocabulary (issue #636)
from openspec_binding_check import active_changes  # noqa: E402  the ONE ACTIVE-change reader

REPO_ROOT = Path(__file__).resolve().parent.parent

#: What rule 6f requires of an ACTIVE change before any of the other gates can
#: even read it. Each artifact names the gate it feeds, so the failure message
#: tells a reader WHICH rule the change broke, not just which file is absent.
MISSING_PROPOSAL = "no proposal.md (rule 6f: Why / What Changes / Impact / not covered)"
MISSING_SPEC = "no specs/<capability>/spec.md (rule 6f: at least one capability spec)"
MISSING_TASKS = "no tasks.md with a `- [ ]` checklist (rule 6f: one box per implemented step)"

#: The keeper's own declaration, written ON the archived proposal. It is the
#: #952 exemption shape (`Binding-exempt: <reason>`, scripts/openspec_binding_check.py),
#: so the archived change states in its own text that a keeper archived it and why.
EXEMPTION_PREFIX = "invalid active change repaired by keeper"


def exemption_line(run_id: str) -> str:
    """The declared keeper exemption (the ONE spelling; rule 6j/6d)."""
    return f"Binding-exempt: {EXEMPTION_PREFIX} ({run_id})"


def structural_problems(change: Path) -> list[str]:
    """Every rule-6f artifact this ACTIVE change is missing (empty == complete)."""
    problems: list[str] = []
    if not (change / "proposal.md").is_file():
        problems.append(MISSING_PROPOSAL)
    if not sorted(change.glob("specs/*/spec.md")):
        problems.append(MISSING_SPEC)
    tasks = change / "tasks.md"
    if not tasks.is_file():
        problems.append(MISSING_TASKS)
    elif not task_boxes.BOX_RE_MULTILINE.findall(tasks.read_text(encoding="utf-8")):
        problems.append(MISSING_TASKS)
    return problems


def invalid_active_changes(changes_dir: Path) -> list[tuple[str, list[str]]]:
    """`[(change name, [missing artifacts])]` for every invalid ACTIVE change."""
    out: list[tuple[str, list[str]]] = []
    for change in active_changes(changes_dir):
        problems = structural_problems(change)
        if problems:
            out.append((change.name, problems))
    return out


def remedy(name: str) -> str:
    """The one honest remedy for an invalid ACTIVE change (never 'write the rest')."""
    return (f"archive it: `make openspec-invalid-change-repair` moves "
            f"openspec/changes/{name}/ to openspec/changes/archive/<UTC-date>-{name}/ "
            f"and regenerates OPENSPEC.md — the missing spec/tasks are NEVER written "
            f"by a keeper (rule 2: no invented content)")


def run_check(root: Path) -> int:
    """The gate half: name every invalid ACTIVE change and its remedy."""
    changes_dir = root / "openspec" / "changes"
    if not changes_dir.is_dir():
        print(f"[openspec-invalid-change] FAIL: cannot read {changes_dir} (exit 2, "
              "never a vacuous clean)", file=sys.stderr)
        return 2
    try:
        active = active_changes(changes_dir)
        invalid = invalid_active_changes(changes_dir)
    except OSError as exc:
        print(f"[openspec-invalid-change] FAIL: cannot read {changes_dir}: {exc} "
              "(exit 2)", file=sys.stderr)
        return 2

    if not invalid:
        print(f"[openspec-invalid-change] OK: {len(active)} ACTIVE change(s) carry "
              "proposal.md + specs/<capability>/spec.md + tasks.md — nothing to repair")
        return 0

    print(f"[openspec-invalid-change] FAIL: {len(invalid)} ACTIVE change(s) are "
          f"structurally incomplete (of {len(active)} active):", file=sys.stderr)
    for name, problems in invalid:
        print(f"  - {name}: {', '.join(problems)}", file=sys.stderr)
        print(f"    remedy: {remedy(name)}", file=sys.stderr)
    print("[openspec-invalid-change] this is the shape `openspec validate --changes` "
          "refuses and `make openspec-index-repair` cannot own: the named repairer is "
          "`qa-validate invalid-change-repair` (`make openspec-invalid-change-repair`)",
          file=sys.stderr)
    return 1


def _stamp_exemption(proposal: Path, run_id: str) -> bool:
    """Add the keeper exemption to an archived proposal; False when there is none to stamp.

    A change that shipped with no proposal at all gets NO proposal written here —
    the repairer archives what exists and reports what it could not stamp.
    """
    if not proposal.is_file():
        return False
    text = proposal.read_text(encoding="utf-8")
    line = exemption_line(run_id)
    if line in text:
        return True
    lines = text.splitlines()
    at = 0
    for i, ln in enumerate(lines):
        if ln.startswith("# ") or ln.startswith("Issue:"):
            at = i + 1
    lines.insert(at, line)
    proposal.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return True


def _regen_index(root: Path) -> None:
    """Regenerate OPENSPEC.md for `root` through the ONE generator.

    `openspec_index` reads its module-global ROOT/CHANGES/INDEX (its own repo by
    default); point them at the target tree so a keeper repair — or a fixture tree —
    never rewrites this checkout's index by accident, and put them back afterwards
    so no later caller in the same process inherits the fixture's paths.
    """
    saved = (openspec_index.ROOT, openspec_index.CHANGES, openspec_index.INDEX)
    openspec_index.ROOT = root
    openspec_index.CHANGES = root / "openspec" / "changes"
    openspec_index.INDEX = root / "OPENSPEC.md"
    try:
        openspec_index.main(["--write"])
    finally:
        (openspec_index.ROOT, openspec_index.CHANGES, openspec_index.INDEX) = saved


def classify_and_archive(root: Path, run_id: str) -> int:
    """Land the repair for the invalid-change shape: archive, declare, re-index."""
    changes_dir = root / "openspec" / "changes"
    if not changes_dir.is_dir():
        print(f"[openspec-invalid-change] ERROR: cannot read {changes_dir} (exit 2, "
              "never a silent clean)", file=sys.stderr)
        return 2
    try:
        invalid = invalid_active_changes(changes_dir)
    except OSError as exc:
        print(f"[openspec-invalid-change] ERROR: cannot read {changes_dir}: {exc} "
              "(exit 2)", file=sys.stderr)
        return 2

    if not invalid:
        print("[openspec-invalid-change] REPAIR=none — no ACTIVE change is structurally "
              "invalid; nothing was moved and nothing was written")
        return 0

    archive_dir = changes_dir / "archive"
    archived: list[tuple[str, str]] = []
    for name, problems in invalid:
        src = changes_dir / name
        dest_name = f"{dt.datetime.now(dt.timezone.utc).strftime('%Y-%m-%d')}-{name}"
        dest = archive_dir / dest_name
        if dest.exists():
            # A second keeper on the same day for the same change, or a move that
            # would overwrite merged history: refused loudly, never silently merged.
            print(f"[openspec-invalid-change] ERROR: {dest} already exists — refusing to "
                  "move the change over it (exit 2)", file=sys.stderr)
            return 2
        archive_dir.mkdir(parents=True, exist_ok=True)
        shutil.move(str(src), str(dest))
        stamped = _stamp_exemption(dest / "proposal.md", run_id)
        archived.append((dest_name, ", ".join(problems)))
        print(f"[openspec-invalid-change] archived {name} -> openspec/changes/archive/{dest_name}/ "
              f"({', '.join(problems)})")
        if not stamped:
            print(f"[openspec-invalid-change] NOTE {dest_name}: the change shipped with no "
                  "proposal.md, so no exemption line could be stamped — the archive holds "
                  "exactly what landed, nothing was invented")

    try:
        _regen_index(root)
    except SystemExit as exc:  # the generator refuses the tree: loud, never a half-repair
        print(f"[openspec-invalid-change] ERROR: the index generator refused the tree after "
              f"the archive move (exit 2): {exc}", file=sys.stderr)
        return 2

    print(f"[openspec-invalid-change] REPAIR=archived {len(archived)} change(s): "
          f"{', '.join(name for name, _ in archived)} — OPENSPEC.md regenerated "
          f"(keeper run {run_id})")
    return 0


def archived_repairs(root: Path, run_id: str | None) -> list[str]:
    """Archive entries this keeper shape stamped (the body names what it actually moved)."""
    archive_dir = root / "openspec" / "changes" / "archive"
    if not archive_dir.is_dir():
        return []
    out: list[str] = []
    for entry in sorted(archive_dir.iterdir()):
        proposal = entry / "proposal.md"
        if not proposal.is_file():
            continue
        text = proposal.read_text(encoding="utf-8")
        if EXEMPTION_PREFIX not in text:
            continue
        if run_id and f"({run_id})" not in text:
            continue
        out.append(entry.name)
    return out


def compose_pr_body(master_sha: str, run_url: str, root: Path,
                    run_id: str | None = None) -> str:
    """Body for the invalid-change keeper PR. It implements no issue, so it carries
    NO closing keyword (rule 6e) — the tracking issue is referenced, never closed."""
    repairs = archived_repairs(root, run_id)
    parts = [
        "Generated invalid-active-change repair (issue #962).",
        "",
        f"A `push`-to-`master` `qa-validate` run ({run_url}) went red at `make openspec-check` "
        f"because `master` carries an ACTIVE change that shipped incomplete — a proposal with "
        f"no capability spec and no task checklist. `openspec validate --changes` refuses it, "
        f"and the index keeper's verdict (`DRIFT=none|index-only`) cannot own that red, so this "
        f"job is the named repairer for the shape.",
        "",
        f"This branch carries exactly the archive move `make openspec-invalid-change-repair` "
        f"made against the merged tree `{master_sha[:10]}`: the incomplete change moved to "
        f"`openspec/changes/archive/<UTC-date>-<name>/`, its proposal declaring "
        f"`Binding-exempt: {EXEMPTION_PREFIX} (<run id>)`, and `OPENSPEC.md` regenerated from the "
        f"resulting tree.",
        "",
        ("It names the change(s) it archived: " + ", ".join(f"`{n}`" for n in repairs) + ".")
        if repairs else
        "It archives nothing it did not find: the repairer writes no spec and no task list — an "
        "incomplete change is archived and declared, never completed by a keeper (rule 2).",
        "",
        "The job refuses to land unless the tree's drift is only the archive move plus "
        "`OPENSPEC.md`; a red with any other cause keeps this PR from opening at all.",
        "",
        "This PR records a keeper repair of an invalid change; it implements no issue, so it "
        "closes none (rule 6e). The repair path itself is tracked in refs #962.",
    ]
    return "\n".join(parts) + "\n"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description=(__doc__ or "openspec invalid change repair").splitlines()[0])
    ap.add_argument("--check", action="store_true",
                    help="exit 1 naming every structurally invalid ACTIVE change and its remedy")
    ap.add_argument("--classify-and-archive", action="store_true",
                    help="archive every invalid ACTIVE change and regenerate the index")
    ap.add_argument("--print-pr-body", action="store_true",
                    help="print the keeper PR body (no closing keyword)")
    ap.add_argument("--master-sha", default=None, help="required for --print-pr-body")
    ap.add_argument("--run-url", default=None, help="required for --print-pr-body")
    ap.add_argument("--run-id", default=None,
                    help="the CI run this keeper acts on (stamped on the archived proposal)")
    ap.add_argument("--root", default=None, help="target tree (default: this repository)")
    a = ap.parse_args(argv)

    root = Path(a.root).resolve() if a.root else REPO_ROOT
    run_id = a.run_id or "unattended-keeper"

    if a.print_pr_body:
        if not a.master_sha or not a.run_url:
            print("[openspec-invalid-change] --print-pr-body needs --master-sha AND --run-url "
                  "(the PR must name the exact red run it repairs)", file=sys.stderr)
            return 2
        sys.stdout.write(compose_pr_body(a.master_sha, a.run_url, root, a.run_id))
        return 0

    if a.check:
        return run_check(root)

    if a.classify_and_archive:
        return classify_and_archive(root, run_id)

    print("[openspec-invalid-change] nothing asked: pass --check, --classify-and-archive "
          "or --print-pr-body", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
