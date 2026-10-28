#!/usr/bin/env python3
"""Keep ARCHITECTURE.md true to the repository (rule 6h, issue #178).

`ARCHITECTURE.md` describes how this repo works — every public `make` target,
every pipeline, every image, every script. Prose rots silently, so this check is
what makes the description part of the change. It fails when

  * a public make target in the Makefile is not named in the description's §3
    tables (the target list),
  * a target the §3 tables name is not a make target any more,
  * a workflow under `.github/workflows/` is not described,
  * a workflow under `.github/workflows/` is not named in `AGENTS.md` §6b, the
    rulebook's own pipeline list — the list a contributor reads FIRST, which was
    hand-maintained and named 6 of the 12 pipelines in the tree (the `tech-debt`
    issue `agents-md-6b-enumerates-five-of-the-eleven-pipelines`) — or §6b
    names a `.yml` that is not a workflow, and a missing `AGENTS.md`, which is
    a finding rather than a skip so deleting the file cannot silence it,
  * a script under `scripts/` is not described,
  * the description references a workflow/script path that does not exist,
  * a `--only` stage list of a Makefile target names a stage
    `scripts/validate.py` does not register, or a registered stage no `--only`
    list selects (issue #182),
  * §4's job tables/bullets name a job the workflow does not define, a real job
    no §4 section names, or a workflow has no §4 section at all (issue #182).

**The boundary is part of the contract** (issue #182): this guard proves PRESENCE
and these two STRUCTURAL cross-checks. It cannot read prose, so a sentence that
is wrong about a real target (`make merge` runs in the test image) passes.
`ARCHITECTURE.md` states the same boundary where the promise is made (rule 6h).

Wired into `make architecture-check`, which `qa-validate`'s `validate` job and
`make test` run, and required of every implementation run by the prompt (rule 6h)
— so an agent that adds a target either documents it or turns CI red.

Usage:
    python3 scripts/architecture_check.py              # the real repository
    python3 scripts/architecture_check.py --root DIR   # a fixture tree
"""

from __future__ import annotations

import argparse
import ast
import re
import sys
from pathlib import Path

#: The workflow's real `jobs:` keys have ONE parser — the one the generated
#: inventory already uses (rule 6d: never a second copy of the same rule).
sys.path.insert(0, str(Path(__file__).resolve().parent))
from architecture_bot import workflow_jobs  # noqa: E402

DOC_NAME = "ARCHITECTURE.md"
VALIDATOR = "scripts/validate.py"
TARGET_SECTION = "## 3."
NEXT_SECTION = "## 4."
#: The RULEBOOK's own pipeline list — the section a contributor reads first, and
#: the fourth place a workflow has to be named (issue `agents-md-6b-enumerates…`).
#: `ARCHITECTURE.md` §4 is canonical for a pipeline's SHAPE (its §4 section and job
#: list are checked below); §6b is where the rule that governs it lives.
AGENTS_DOC = "AGENTS.md"
RULEBOOK_SECTION = "## 6b."
RULEBOOK_NEXT_SECTION = "## 7."
#: The human-readable SCRIPT inventory. §10's generated block names every script
#: too, so "the name appears somewhere" (the old rule) was satisfied by the block
#: while §6 — the table a reader actually uses to learn what a script does — lost
#: 9 of 46 entries (issue #506).
SCRIPT_SECTION = "## 6."
SCRIPT_NEXT_SECTION = "## 7."

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
#: Any make target line (internal ones included) — only used to name the target
#: that carries a `--only` list in a failure message.
_ANY_TARGET = re.compile(r"^([A-Za-z_][A-Za-z0-9_-]*):(?!=)")
#: A `validate.py --only <stages>` call, and the stage list it carries.
_ONLY_CALL = re.compile(r"scripts/validate\.py\s+--only\s+([\w,-]+)")
#: A §4 subsection that describes ONE workflow, and a job written as a bold
#: bullet (`- **`guard`** — …`, the shape the two-job pipelines use).
_WF_HEADING = re.compile(r"^###\s+.*\.github/workflows/([A-Za-z0-9_.-]+\.yml)")
_JOB_BULLET = re.compile(r"^\s*[-*]\s+\*\*`([A-Za-z0-9_-]+)`\*\*")



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


def section(text: str, start_marker: str, end_marker: str) -> str:
    """The document's `start_marker` … `end_marker` section (empty when absent)."""
    start = text.find(start_marker)
    end = text.find(end_marker, start + 1)
    return text[start:end] if start >= 0 and end > start else ""


def described_scripts(doc: Path) -> set[str]:
    """The script paths §6's table claims a role for (its FIRST cell only)."""
    if not doc.is_file():
        return set()
    body = section(doc.read_text(encoding="utf-8"), SCRIPT_SECTION, SCRIPT_NEXT_SECTION)
    names = set()
    for cell in _TABLE_ROW.findall(body):
        for token in _TICKED.findall(cell):
            if token.startswith("scripts/"):
                names.add(token)
    return names


def rulebook_pipelines(agents: Path) -> set[str]:
    """The workflow names `AGENTS.md` §6b lists (its backticked `*.yml` tokens).

    The section is the one a contributor reads first, and it is hand-maintained:
    it named 6 of the 12 workflows in the tree while every one of them was
    described in `ARCHITECTURE.md` §4 — so "is it in the description?" could never
    notice. The pipeline's SHAPE stays §4's job (canonical, generated, and checked
    above); this list is the rulebook entry, so it must name every pipeline.
    """
    if not agents.is_file():
        return set()
    body = section(agents.read_text(encoding="utf-8"), RULEBOOK_SECTION,
                   RULEBOOK_NEXT_SECTION)
    return {t for t in _TICKED.findall(body) if t.endswith(".yml")}


def validate_stages(script: Path) -> set[str]:
    """Every stage `scripts/validate.py` registers, read from its own source.

    `main()` registers each check as `add(<label>, <stage>, <fn>)`; the map is read
    by AST, so the guard compares against the validator itself and never a copy
    of its stage list (issue #182).
    """
    if not script.is_file():
        return set()
    try:
        tree = ast.parse(script.read_text(encoding="utf-8"))
    except SyntaxError:
        return set()
    stages: set[str] = set()
    for node in ast.walk(tree):
        if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                and node.func.id == "add" and len(node.args) >= 2):
            continue
        label, stage = node.args[0], node.args[1]
        if (isinstance(label, ast.Constant) and isinstance(label.value, str)
                and isinstance(stage, ast.Constant) and isinstance(stage.value, str)):
            stages.add(stage.value)
    return stages


def stage_lists(makefile: Path) -> list[tuple[str, list[str]]]:
    """`(target, stages)` for every `validate.py --only …` list in the Makefile."""
    if not makefile.is_file():
        return []
    out: list[tuple[str, list[str]]] = []
    target = ""
    for line in makefile.read_text(encoding="utf-8").splitlines():
        if not line.lstrip().startswith("#"):
            m = _ANY_TARGET.match(line)
            if m:
                target = m.group(1)
            m = _ONLY_CALL.search(line)
            if m:
                out.append((target or "?", [s.strip() for s in m.group(1).split(",") if s.strip()]))
    return out


def described_jobs(doc: Path) -> dict[str, set[str]]:
    """The job names §4 claims, per workflow file (its `Job` tables + bold bullets).

    A §4 subsection is the one whose heading names `.github/workflows/<file>.yml`;
    it ends at the next `##`/`###` heading. Inside it, a table whose header cell is
    `Job` contributes the backticked names in its first cells, and a bold bullet
    (`- **`guard`** — …`) contributes its name (issue #182).
    """
    if not doc.is_file():
        return {}
    out: dict[str, set[str]] = {}
    current: str | None = None
    rows: list[str] = []

    def flush() -> None:
        if current is None:
            return
        names = out.setdefault(current, set())
        block: list[str] = []
        for row in rows:
            if row.lstrip().startswith("|"):
                block.append(row)
                continue
            _table_jobs(block, names)
            block = []
            m = _JOB_BULLET.match(row)
            if m:
                names.add(m.group(1))
        _table_jobs(block, names)

    for line in doc.read_text(encoding="utf-8").splitlines():
        m = _WF_HEADING.match(line)
        if m:
            flush()
            current, rows = m.group(1), []
            continue
        if re.match(r"^#{2,3}\s", line):
            flush()
            current, rows = None, []
            continue
        if current is not None:
            rows.append(line)
    flush()
    return out


def _table_jobs(block: list[str], names: set[str]) -> None:
    """Add the first-cell backticked names of a `| Job | Does |` table block."""
    if len(block) < 2:
        return
    cells = block[0].split("|")
    if len(cells) < 2 or "Job" not in cells[1]:
        return
    for row in block[2:]:
        parts = row.split("|")
        if len(parts) >= 2:
            names.update(_TICKED.findall(parts[1]))


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

    # The rulebook's OWN pipeline list, both directions — the one place a
    # contributor asks "which pipelines does this repo run?" and the one that was
    # never reconciled when the alarms were added (`AGENTS.md` §6b named 6 of 12).
    agents = root / AGENTS_DOC
    if not agents.is_file():
        out.append(f"{AGENTS_DOC} is missing — its §6b pipeline list is the rulebook's "
                   f"statement of which pipelines exist (rule 6h)")
    else:
        named = rulebook_pipelines(agents)
        out += [f"workflow `{w}` is not named in {AGENTS_DOC} §6b — every pipeline in the "
                f"tree belongs in the rulebook's list (its shape is described in "
                f"{DOC_NAME} §4)" for w in workflows if w not in named]
        out += [f"{AGENTS_DOC} §6b names `{n}`, which is not a workflow in "
                f"`.github/workflows/`" for n in sorted(named - set(workflows))]

    scripts = sorted(p.name for p in (root / "scripts").glob("*") if p.is_file())
    out += [f"script `scripts/{s}` is not described in {DOC_NAME}" for s in scripts if s not in text]
    out += [f"{DOC_NAME} references `scripts/{r}`, which does not exist"
            for r in sorted(set(_SCRIPT_REF.findall(text))) if r not in scripts]

    # §6 is the inventory a READER uses; naming a script in the generated §10
    # block does not give it a role (issue #506 — 9 of 46 scripts were in the
    # block and absent here, and the old check was satisfied by the block).
    roles = described_scripts(doc)
    out += [f"script `scripts/{s}` has no row in {DOC_NAME} §6 (the generated block "
            f"names it, but a reader has no role for it)" for s in scripts
            if f"scripts/{s}" not in roles]

    # The `--only` stage lists are a CLAIM about the validator's stage map, and a
    # closed one: an unknown stage, or a stage no list selects, is a description
    # that has rotted without any name disappearing (issue #182).
    stages = validate_stages(root / VALIDATOR)
    lists = stage_lists(root / "Makefile")
    if stages and lists:
        selected = {s for _, stages_in_list in lists for s in stages_in_list}
        out += [f"make target `{t}` runs `--only {s}`, which {VALIDATOR} does not register"
                for t, stages_in_list in lists for s in stages_in_list if s not in stages]
        out += [f"stage `{s}` of {VALIDATOR} is selected by no `--only` list in the Makefile"
                for s in sorted(stages - selected)]

    # §4's job lists are the same kind of claim about the workflows' real `jobs:`
    # keys — a renamed job, or one the table invented, is invisible to a
    # presence-only check (issue #182: §4 listed a `sweep` job for `queued-alarm`,
    # which defines `guard` and `alarm`).
    claimed = described_jobs(doc)
    for w in workflows:
        if w not in claimed:
            out.append(f"workflow `{w}` has no §4 section of its own in {DOC_NAME} "
                       f"(its job list cannot be checked)")
            continue
        real = {name for name, _ in workflow_jobs((root / ".github" / "workflows" / w)
                                                  .read_text(encoding="utf-8"))}
        out += [f"{DOC_NAME} §4 names job `{j}` in `{w}`, which that workflow does not define"
                for j in sorted(claimed[w] - real)]
        out += [f"workflow `{w}`'s job `{j}` is not named in its {DOC_NAME} §4 section"
                for j in sorted(real - claimed[w])]
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
          f"({len(public_targets(root / 'Makefile'))}), workflow and script — and its "
          f"`--only` stage lists and §4 job names match the tree")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
