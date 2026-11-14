#!/usr/bin/env python3
"""Fail when an ACTIVE OpenSpec change carries no Issue binding (issue #952).

The lifecycle rule (AGENTS.md §6f) closes a change THROUGH the PR that closes
its issue: `make openspec-record-pr ISSUE=<n>` finds the change by its
proposal's `Issue:` line. When an implementation run creates its change
WITHOUT that binding, nothing notices until the record step at the very END
of the run — measured on the 2026-11-12 weekly sweep (issue-bot run
43147959554, step 15): ~30 minutes of implementation, then
`[openspec-record-pr] REFUSED: no change — active or archived — references
Issue: #624 — nothing recorded`, a `failure` delivery, and `make sweep-alarm`
reds every queued-alarm until a newer schedule delivery replaces it.

This check moves the refusal EARLY, into the `make openspec-check` family the
run already passes BEFORE the PR, where the fix loop can still repair it. One
ACTIVE change may instead declare itself exempt — the keeper shape (rule 6e:
an archive move, an index regeneration) implements no issue, so it states
`Binding-exempt: <reason>` in its proposal instead of staying silent. An
unbound change that never declares is the defect; an unbound change that
declares why is a documented state (the archived keeper changes show silence
can never be the default).

Exit codes (the ledger-guard model):
  0  every active change is bound or declared exempt
  1  an active change is neither — each is named with its remedy
  2  the changes tree cannot be read — loud, never a vacuous clean

Wired into `make openspec-binding-check`, a prerequisite of `make
openspec-check` (rules 6d/6m: bundled into the stage the pipeline already
runs on every PR and push).

Usage:
    python3 scripts/openspec_binding_check.py
    python3 scripts/openspec_binding_check.py --changes-dir <dir>   # fixture seam
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import openspec_index  # the ONE `Issue:`/`PR:` proposal parser (rule 6d)

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CHANGES_DIR = REPO_ROOT / "openspec" / "changes"

#: The declared exemption shape (issue #952): a keeper change that genuinely
#: implements no issue states its reason on this line instead of omitting the
#: binding in silence. One spelling, parsed here only.
EXEMPT_RE = re.compile(r"^Binding-exempt:\s*(\S.*)$", re.MULTILINE)


def active_changes(changes_dir: Path) -> list[Path]:
    """ACTIVE change directories: everything except `archive/` and dot-dirs."""
    return sorted(p for p in changes_dir.iterdir()
                  if p.is_dir() and p.name != "archive" and not p.name.startswith("."))


def binding_state(change: Path) -> tuple[str, str]:
    """`('bound', '#650')`, `('exempt', <reason>)` or `('unbound', <detail>)`."""
    proposal = change / "proposal.md"
    if not proposal.is_file():
        return ("unbound", "no proposal.md at all")
    refs = openspec_index._refs(proposal)
    issue_ref = refs.get("Issue") or ""
    if re.search(r"#(\d+)", issue_ref):
        return ("bound", issue_ref)
    m = EXEMPT_RE.search(proposal.read_text(encoding="utf-8"))
    if m:
        return ("exempt", m.group(1).strip())
    if issue_ref:
        return ("unbound", f"its Issue line names no issue: {issue_ref!r}")
    return ("unbound", "no Issue line and no `Binding-exempt:` declaration")


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    changes_dir = DEFAULT_CHANGES_DIR
    if "--changes-dir" in argv:
        i = argv.index("--changes-dir")
        if i + 1 >= len(argv):
            print("[openspec-binding-check] FAIL: --changes-dir needs a path",
                  file=sys.stderr)
            return 2
        changes_dir = Path(argv[i + 1])
    if not changes_dir.is_dir():
        print(f"[openspec-binding-check] FAIL: cannot read {changes_dir} (exit 2, "
              "never a vacuous clean)", file=sys.stderr)
        return 2

    changes = active_changes(changes_dir)
    unbound: list[tuple[str, str]] = []
    exempt: list[tuple[str, str]] = []
    bound = 0
    for change in changes:
        state, detail = binding_state(change)
        if state == "bound":
            bound += 1
        elif state == "exempt":
            exempt.append((change.name, detail))
        else:
            unbound.append((change.name, detail))

    for name, reason in exempt:
        print(f"[openspec-binding-check] exempt: {name} — Binding-exempt: {reason}")
    if unbound:
        print(f"[openspec-binding-check] FAIL: {len(unbound)} ACTIVE change(s) bind "
              "no issue and declare no exemption:", file=sys.stderr)
        for name, detail in unbound:
            print(f"  - {name}: {detail}", file=sys.stderr)
        print("Remedy: add an `Issue: #<n>` line to openspec/changes/<name>/proposal.md "
              "(rule 6f — the binding `make openspec-record-pr` needs at the end of "
              "the run), or declare `Binding-exempt: <why this change implements no "
              "issue>` for a keeper change.", file=sys.stderr)
        return 1
    print(f"[openspec-binding-check] OK: bound={bound} exempt={len(exempt)} "
          f"of {len(changes)} active change(s) — every ACTIVE change names the "
          "issue its PR will close, or declares why it implements none")
    return 0


if __name__ == "__main__":
    sys.exit(main())
