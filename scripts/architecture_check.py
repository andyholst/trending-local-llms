#!/usr/bin/env python3
"""Keep ARCHITECTURE.md true to the repository (rule 6h, issue #178).

`ARCHITECTURE.md` describes how this repo works — every public `make` target,
every pipeline, every image, every script. Prose rots silently, so this check is
what makes the description part of the change. It fails when

  * a public make target in the Makefile is not named in the description's §3
    tables (the target list),
  * a target the §3 tables name is not a make target any more,
  * a workflow under `.github/workflows/` is not described,
  * a script under `scripts/` is not described,
  * the description references a workflow/script path that does not exist.

Wired into `make architecture-check`, which `qa-validate`'s `validate` job and
`make test` run, and required of every implementation run by the prompt (rule 6h)
— so an agent that adds a target either documents it or turns CI red.

Usage:
    python3 scripts/architecture_check.py              # the real repository
    python3 scripts/architecture_check.py --root DIR   # a fixture tree
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

DOC_NAME = "ARCHITECTURE.md"
TARGET_SECTION = "## 3."
NEXT_SECTION = "## 4."

# A public target: `name:` at column 0. `.PHONY`, comments, `:=` assignments,
# `%`-patterns and `_`-prefixed internals are not public targets.
_TARGET_LINE = re.compile(r"^([a-z][a-z0-9-]*):(?!=)", re.MULTILINE)
_SKIP_PREFIX = ("\t", "#", ".PHONY", "include", "export", "SHELL", "if", "else", "endif")
# A markdown table row, and the backticked tokens in its FIRST cell.
_TABLE_ROW = re.compile(r"^\|\s*([^|]*)\|", re.MULTILINE)
_TICKED = re.compile(r"`([^`]+)`")
_NAME = re.compile(r"^[a-z][a-z0-9-]*$")
_WF_REF = re.compile(r"\.github/workflows/([A-Za-z0-9_.-]+\.yml)")
_SCRIPT_REF = re.compile(r"scripts/([A-Za-z0-9_.-]+\.(?:py|sh))")


def public_targets(makefile: Path) -> list[str]:
    """Every public make target in the Makefile, sorted."""
    if not makefile.is_file():
        return []
    names = set()
    for line in makefile.read_text(encoding="utf-8").splitlines():
        if line.startswith(_SKIP_PREFIX):
            continue
        m = _TARGET_LINE.match(line)
        if m:
            names.add(m.group(1))
    return sorted(names)


def described_targets(doc: Path) -> list[str]:
    """The target names the description's §3 tables claim exist."""
    if not doc.is_file():
        return []
    text = doc.read_text(encoding="utf-8")
    start = text.find(TARGET_SECTION)
    end = text.find(NEXT_SECTION, start + 1)
    section = text[start:end] if start >= 0 and end > start else ""
    names = set()
    for cell in _TABLE_ROW.findall(section):
        for token in _TICKED.findall(cell):
            if _NAME.match(token):
                names.add(token)
    return sorted(names)


def described_text(doc: Path) -> str:
    return doc.read_text(encoding="utf-8") if doc.is_file() else ""


def findings(root: Path) -> list[str]:
    """Every way the description and the repository disagree."""
    doc = root / DOC_NAME
    if not doc.is_file():
        return [f"{DOC_NAME} is missing — it is part of the change (rule 6h)"]
    text = described_text(doc)

    make_targets = set(public_targets(root / "Makefile"))
    doc_targets = set(described_targets(doc))

    out = [f"make target `{t}` is not described in {DOC_NAME}'s target tables"
           for t in sorted(make_targets - doc_targets)]
    out += [f"{DOC_NAME} describes `{t}`, which is no longer a make target"
            for t in sorted(doc_targets - make_targets)]

    workflows = sorted(p.name for p in (root / ".github" / "workflows").glob("*.yml"))
    out += [f"workflow `{w}` is not described in {DOC_NAME}" for w in workflows if w not in text]
    out += [f"{DOC_NAME} references `.github/workflows/{r}`, which does not exist"
            for r in sorted(set(_WF_REF.findall(text))) if r not in workflows]

    scripts = sorted(p.name for p in (root / "scripts").glob("*") if p.is_file())
    out += [f"script `scripts/{s}` is not described in {DOC_NAME}" for s in scripts if s not in text]
    out += [f"{DOC_NAME} references `scripts/{r}`, which does not exist"
            for r in sorted(set(_SCRIPT_REF.findall(text))) if r not in scripts]
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Keep ARCHITECTURE.md true to the repo")
    ap.add_argument("--root", default=str(Path(__file__).resolve().parents[1]))
    a = ap.parse_args(argv)

    root = Path(a.root)
    problems = findings(root)
    if problems:
        print(f"[architecture] FAIL {DOC_NAME} is out of step with the repository:", file=sys.stderr)
        for p in problems:
            print(f"[architecture]   - {p}", file=sys.stderr)
        print("[architecture] update it in the same change (rule 6h), then run "
              "`make architecture-check`", file=sys.stderr)
        return 1
    print(f"[architecture] OK {DOC_NAME} describes every make target "
          f"({len(public_targets(root / 'Makefile'))}), workflow and script")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
