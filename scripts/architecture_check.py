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
#: inventory already uses (rule 6d: never a second copy of the same rule). So does
#: "what is a make target": `public_targets` (the projection this guard checks) and
#: `make_targets` (the full set the generator renders) are BOTH views of the one
#: scan in `architecture_bot`, imported here — issue #512's two parsers became one.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from architecture_bot import (public_targets, makefile_lanes, target_at_line, workflow_crons,
                              workflow_jobs, workflow_trigger_events)  # noqa: E402
import check_agent_skills as agent_skills  # noqa: E402  (SKILLS_DIR — the one skill home, issue #904)

DOC_NAME = "ARCHITECTURE.md"
VALIDATOR = "scripts/validate.py"
#: Section boundaries are STABLE HTML-comment ANCHORS, never prose headings
#: (this issue): a heading like `## 6.` is re-numberable prose — #479 added §10
#: and pushed every heading that followed — and a plain-text match against the
#: heading silently repoints a check when the numbers move. Each boundary is a
#: comment placed in the document beside its section, so a renumber moves the
#: anchor nowhere and the guard keeps reading the section it means. The anchor's
#: presence is itself a structural claim (rule 6h), so `findings()` fails LOUDLY
#: naming the missing anchor instead of reading an empty or shifted section for
#: the wrong reason.
TARGET_SECTION = "<!-- arch:targets -->"
NEXT_SECTION = "<!-- arch:pipelines -->"
#: The RULEBOOK's own pipeline list — the section a contributor reads first, and
#: the fourth place a workflow has to be named (issue `agents-md-6b-enumerates…`).
#: `ARCHITECTURE.md` §4 is canonical for a pipeline's SHAPE (its §4 section and job
#: list are checked below); §6b is where the rule that governs it lives.
AGENTS_DOC = "AGENTS.md"
RULEBOOK_SECTION = "<!-- agents:rulebook -->"
RULEBOOK_NEXT_SECTION = "<!-- agents:style -->"
#: The human-readable SCRIPT inventory. §10's generated block names every script
#: too, so "the name appears somewhere" (the old rule) was satisfied by the block
#: while §6 — the table a reader actually uses to learn what a script does — lost
#: 9 of 46 entries (issue #506).
SCRIPT_SECTION = "<!-- arch:scripts -->"
SCRIPT_NEXT_SECTION = "<!-- arch:guards -->"

#: Every boundary anchor this guard reads, per document. A section's REGION is a
#: structural claim, so a missing anchor is a finding that NAMES the anchor — never
#: the wrong-reason cascade (a silent empty read reporting "every script has no
#: row") of a heading the check stopped matching.
_REQUIRED_ANCHORS: tuple[tuple[str, str, str], ...] = (
    (DOC_NAME, "make-target tables", TARGET_SECTION),
    (DOC_NAME, "pipelines", NEXT_SECTION),
    (DOC_NAME, "script inventory", SCRIPT_SECTION),
    (DOC_NAME, "guards", SCRIPT_NEXT_SECTION),
    (AGENTS_DOC, "rulebook pipeline list", RULEBOOK_SECTION),
    (AGENTS_DOC, "style", RULEBOOK_NEXT_SECTION),
)


def anchor_findings(docs: dict[str, str]) -> list[str]:
    """Every boundary anchor a present document lost, or stranded from its section.

    Two failures, one rule: the anchor IS the boundary the guard reads, so a
    document that dropped one silently repoints a check (the wrong-reason cascade),
    and an anchor that slid away from the section it bounds bounds the wrong one —
    both are reported, never read as an empty section.
    """
    out: list[str] = []
    for doc_name, role, anchor in _REQUIRED_ANCHORS:
        text = docs.get(doc_name, "")
        if not text:
            continue
        if anchor not in text:
            out.append(f"{doc_name} is missing the section-boundary anchor `{anchor}` "
                       f"that marks its {role} — restore it with the section, or a "
                       f"renumbered heading silently repoints this check (rule 6h)")
            continue
        # The anchor sits beside the heading it bounds: the next non-blank line
        # after it is that heading. An anchor inside a table is a stranded one.
        following = text[text.index(anchor) + len(anchor):].lstrip("\n")
        if not following.startswith("#"):
            out.append(f"{doc_name} has `{anchor}` with no section heading beside it "
                       f"— an anchor stranded from its {role} bounds the wrong section "
                       f"(rule 6h)")
    return out

# A markdown table row, and the backticked tokens in its FIRST cell.
_TABLE_ROW = re.compile(r"^\|\s*([^|]*)\|", re.MULTILINE)
_TICKED = re.compile(r"`([^`]+)`")
_NAME = re.compile(r"^[a-z][a-z0-9-]*$")
_WF_REF = re.compile(r"\.github/workflows/([A-Za-z0-9_.-]+\.yml)")
_SCRIPT_REF = re.compile(r"scripts/([A-Za-z0-9_.-]+\.(?:py|sh))")
#: A `validate.py --only <stages>` call, and the stage list it carries.
_ONLY_CALL = re.compile(r"scripts/validate\.py\s+--only\s+([\w,-]+)")
#: A §4 subsection that describes ONE workflow, and a job written as a bold
#: bullet (`- **`guard`** — …`, the shape the two-job pipelines use).
_WF_HEADING = re.compile(r"^###\s+.*\.github/workflows/([A-Za-z0-9_.-]+\.yml)")
_JOB_BULLET = re.compile(r"^\s*[-*]\s+\*\*`([A-Za-z0-9_-]+)`\*\*")



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
    """The script paths §6's table claims a role for (its FIRST cell only).

    This is a PRESENCE check, never a role-verification: a row's role TEXT is
    human review prose the guard cannot and does not read (issue #508) — the
    same deliberate boundary as `#182`. A row whose role has rotted next to an
    unchanged path passes here; keeping the role true is a reviewer's (or the
    change's) job. `ARCHITECTURE.md` §6 states the same boundary.
    """
    if not doc.is_file():
        return set()
    body = section(doc.read_text(encoding="utf-8"), SCRIPT_SECTION, SCRIPT_NEXT_SECTION)
    names = set()
    for cell in _TABLE_ROW.findall(body):
        for token in _TICKED.findall(cell):
            if token.startswith("scripts/"):
                names.add(token)
    return names


_RULEBOOK_PIPELINE_CLAIM = re.compile(r"^- \*\*`([A-Za-z0-9_.\-]+\.yml)`\*\*", re.M)


def rulebook_pipelines(agents: Path) -> set[str]:
    """The workflow names `AGENTS.md` §6b lists (its pipeline BULLET lines).

    The section is the one a contributor reads first, and it is hand-maintained:
    it named 6 of the 12 workflows in the tree while every one of them was
    described in `ARCHITECTURE.md` §4 — so "is it in the description?" could never
    notice. The pipeline's SHAPE stays §4's job (canonical, generated, and checked
    above); this list is the rulebook entry, so it must name every pipeline.

    A claim is the bullet shape §6b requires — a line starting
    ``- **`<name>.yml`** ``. A backticked `.yml` in a PROSE sentence is the
    section explaining its own failure mode, never a pipeline claim: read as one
    it turned the guard red the moment the paragraph documenting the rule existed
    (issue #660).
    """
    if not agents.is_file():
        return set()
    body = section(agents.read_text(encoding="utf-8"), RULEBOOK_SECTION,
                   RULEBOOK_NEXT_SECTION)
    return set(_RULEBOOK_PIPELINE_CLAIM.findall(body))


def rulebook_pipeline_claims(text: str) -> list[tuple[int, str, str]]:
    """Each `AGENTS.md` §6b pipeline BULLET with its FULL paragraph (issue #1032).

    `rulebook_pipelines` answers WHICH pipelines the rulebook names; this is the same
    reader's second view — what the bullet CLAIMS about how that pipeline STARTS. A
    bullet is one paragraph that wraps across lines, so a line-by-line scan misses the
    claim on a wrapped line (measured: `- **`code-review-bot.yml`**` hid
    "weekly (Monday `23 7`)" on the line AFTER its name). One line, one claim, with the
    line number of the bullet's first line.
    """
    body = section(text, RULEBOOK_SECTION, RULEBOOK_NEXT_SECTION)
    if not body:
        return []
    first_line = text[: text.find(body)].count("\n")
    lines = body.splitlines()
    out: list[tuple[int, str, str]] = []
    i = 0
    while i < len(lines):
        m = _RULEBOOK_PIPELINE_CLAIM.match(lines[i])
        if not m:
            i += 1
            continue
        # The CLAIM is the bullet's INTRO — the first two lines, which is where the
        # sentence naming how the pipeline starts lives (measured: the cadence wrapped
        # onto line 2). The rest of a bullet describes what the pipeline DOES, where
        # ARCHITECTURE.md §4 is canonical (rule 6h) and where narrative words like
        # "a scheduled refresh" are prose about history, not a cadence claim.
        block = [lines[i], *([lines[i + 1]] if i + 1 < len(lines) else [])]
        out.append((first_line + i + 1, m.group(1), " ".join(block)))
        j = i + 1
        while j < len(lines) and lines[j].strip() and not _RULEBOOK_PIPELINE_CLAIM.match(lines[j]):
            j += 1
        i = j
    return out


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
        # issue #752: the current target is tracked through the generator's
        # line view (architecture_bot.target_at_line), not a private matcher.
        opened = target_at_line(line)
        if opened:
            target = opened
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


#: A cron expression quoted in prose (`37 * * * 3`) — the shape of a schedule claim
#: that can be checked against the workflow it names (issue #1032).
_CRON_SLOT = re.compile(r"\b\d{1,2} \d{1,2} \* \* \d{1,2}\b|\b\d{1,2} \* \* \* \d{1,2}\b")
#: A line that says the cadence was TAKEN AWAY is history, not a claim. Without this
#: exemption the guard would red the sentence that documents its own removal.
_CADENCE_RETIRED = re.compile(r"removed|retired|no longer|no cron|no schedule|dispatch-only|dispatch only", re.I)
#: A cadence word is a claim ONLY where it is attached to one pipeline: a §4 heading's
#: parenthetical or a §6b bullet (issue #1032). General prose is out of scope — this
#: guard reads STRUCTURE, never prose (rule 6h's own boundary).
_CADENCE_WORD = re.compile(r"weekly|daily|hourly|twice-an-hour|cron|schedule", re.I)
_DISPATCH_WORD = re.compile(r"dispatch", re.I)
#: `### \`.github/workflows/x.yml\` — label (weekly, \`13\` + dispatch)` — §4's heading
#: IS the trigger claim for that pipeline.
_WF_HEADING_CLAIM = re.compile(r"^###.*?\.github/workflows/([A-Za-z0-9_.\-]+\.yml)`?\s*[—–-]\s*(.+)$", re.M)
#: "`Eight have a cron`" — a COUNT of scheduled pipelines, checkable against the tree.
_CRON_COUNT = re.compile(r"\b([A-Za-z]+|\d+)\s+have a cron\b")
_COUNT_WORDS = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7,
                "eight": 8, "nine": 9, "ten": 10, "eleven": 11, "twelve": 12, "thirteen": 13}


def cadence_findings(root: Path, workflows: list[str] | None = None,
                     docs: dict[str, str] | None = None) -> list[str]:
    """Every cadence CLAIM the documents make that the tree does not declare (issue #1032).

    Owner directive 2026-11-15 (rule 6t, issue #1029) left `refresh-bot.yml` as the ONLY
    scheduled pipeline; `queued-alarm`, `pr-health`, `bot-health`, `architecture-bot`,
    `issue-bot` and `issue-review-bot` lost their crons in the same change, and the ALARM
    prose kept saying "the weekly `queued-alarm` sweep", "the dispatched run of a
    twice-an-hour sweep" and "Eight have a cron". An alarm that waits for an owner dispatch
    is not a scheduled sweep, and a reader who believes the text waits for a cron that
    never fires — the same "silent because nobody looks" class the alarms exist to catch.

    `workflows` / `docs` default to the tree's own workflows and its two rulebook
    documents, so a caller (or a test) can ask the question about a root alone.
    """
    if workflows is None:
        workflows = sorted(p.name for p in (root / ".github" / "workflows").glob("*.yml"))
    if docs is None:
        docs = {}
        for name in (DOC_NAME, AGENTS_DOC):
            path = root / name
            if path.is_file():
                docs[name] = path.read_text(encoding="utf-8")
    crons = {w: workflow_crons((root / ".github" / "workflows" / w).read_text(encoding="utf-8"))
             for w in workflows}
    events = {w: workflow_trigger_events((root / ".github" / "workflows" / w)
                                         .read_text(encoding="utf-8"))
              for w in workflows}
    out: list[str] = []

    # (1) A quoted cron slot must be a cron the pipeline it NAMES actually declares.
    for doc_name, text in docs.items():
        for i, line in enumerate(text.splitlines(), 1):
            slots = _CRON_SLOT.findall(line)
            if not slots or _CADENCE_RETIRED.search(line):
                continue
            named = {f"{m.group(1)}.yml" for m in _WF_REF.finditer(line)} & set(crons)
            if not named:
                continue
            owned = {s for w in named for s in crons[w]}
            for slot in slots:
                if slot not in owned:
                    out.append(f"{doc_name}:{i} quotes cron `{slot}` for "
                               f"{'/'.join(sorted(named))}, which declares no such cron "
                               f"(its own crons: "
                               f"{', '.join(cron for w in sorted(named) for cron in crons[w]) or 'none'})")

    # (2) A cadence word attached to ONE pipeline — §4's heading parenthetical or a
    #     §6b rulebook bullet — requires the workflow to declare a schedule.
    for doc_name, text in docs.items():
        claims: list[tuple[int, str, str]] = []
        for m in _WF_HEADING_CLAIM.finditer(text):
            claims.append((text[:m.start()].count("\n") + 1, m.group(1), m.group(2)))
        claims += rulebook_pipeline_claims(text)
        for line_no, wf, claim in claims:
            if wf not in crons:
                continue
            if _CADENCE_RETIRED.search(claim):
                continue
            if _CADENCE_WORD.search(claim) and not crons[wf]:
                out.append(f"{doc_name}:{line_no} claims a cadence for `{wf}` "
                           f"(\"{claim.strip()[:70]}…\") while that workflow declares no "
                           f"`schedule:` — it is dispatch/event-only (rule 6t)")
            # A §6b bullet names its pipeline as `` `x.yml` ``, not as a
            # `.github/workflows/x.yml` path, so prong (1) cannot see a cron slot quoted
            # INSIDE a bullet — the claim's own workflow is the subject here.
            for slot in _CRON_SLOT.findall(claim):
                if slot not in crons[wf]:
                    out.append(f"{doc_name}:{line_no} attributes `{wf}` the cron slot "
                               f"`{slot}`; that workflow declares "
                               f"{', '.join(crons[wf]) or 'no `schedule:`'}")
            if _DISPATCH_WORD.search(claim) and "workflow_dispatch" not in events[wf]:
                out.append(f"{doc_name}:{line_no} claims a dispatch trigger for `{wf}`, "
                           f"which declares {', '.join(events[wf]) or 'no `on:` events'}")

    # (3) A counted claim about scheduling must match the tree's count.
    scheduled = sorted(w for w in crons if crons[w])
    for doc_name, text in docs.items():
        for i, line in enumerate(text.splitlines(), 1):
            m = _CRON_COUNT.search(line)
            if not m:
                continue
            # A phrase inside a quotation is a REFERENCE to a claim (the §8 guard row
            # quotes the wrong wording it exists to catch); only an unquoted sentence is
            # the description's own claim.
            if line[: m.start()].rfind('"') != -1 and '"' in line[m.end():]:
                continue
            raw = m.group(1).lower()
            claimed = int(raw) if raw.isdigit() else _COUNT_WORDS.get(raw)
            if claimed is not None and claimed != len(scheduled):
                out.append(f"{doc_name}:{i} says {claimed} workflows have a cron; the tree "
                           f"has {len(scheduled)} scheduled pipeline(s): "
                           f"{', '.join(scheduled) or 'none'}")
    return out



def findings(root: Path) -> list[str]:
    """Every way the description and the repository disagree."""
    doc = root / DOC_NAME
    if not doc.is_file():
        return [f"{DOC_NAME} is missing — it is part of the change (rule 6h)"]
    text = described_text(doc)
    agents = root / AGENTS_DOC
    agents_text = described_text(agents)

    # The boundary anchors are the FIRST claim: a document that lost one is
    # broken structurally, and reading a section the anchor no longer bounds
    # would report the wrong thing (the "#479 every script has no row" cascade).
    out = anchor_findings({DOC_NAME: text, AGENTS_DOC: agents_text})
    targets_readable = TARGET_SECTION in text and NEXT_SECTION in text
    scripts_readable = SCRIPT_SECTION in text and SCRIPT_NEXT_SECTION in text
    rulebook_readable = RULEBOOK_SECTION in agents_text and RULEBOOK_NEXT_SECTION in agents_text

    make_targets = set(public_targets(root))
    doc_targets = set(described_targets(doc)) if targets_readable else set()

    out += [f"make target `{t}` is not described in {DOC_NAME}'s target tables"
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
    if not agents.is_file():
        out.append(f"{AGENTS_DOC} is missing — its §6b pipeline list is the rulebook's "
                   f"statement of which pipelines exist (rule 6h)")
    elif rulebook_readable:
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
    if scripts_readable:
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

    # The agent lanes (issue #935, rule 6h): every project skill on disk and every skill
    # name a Makefile leg preloads must be NAMED in the description. Today a preload name
    # appears in ARCHITECTURE.md only by prose accident — a leg whose `-s` pointer is
    # dropped, renamed, or orphaned reads green. This makes the generated block's agent
    # lane the contract it has to be.
    lanes = makefile_lanes((root / "Makefile").read_text(encoding="utf-8"))
    lane_names = {s for skills in lanes.values() for s in skills}
    skill_home = root / agent_skills.SKILLS_DIR
    on_disk = {p.name for p in skill_home.iterdir()
               if p.is_dir() and (p / agent_skills.SKILL_FILE).is_file()} \
        if skill_home.is_dir() else set()
    out += [f"agent skill `{s}` is not named in {DOC_NAME}'s description "
            f"(issue #935: the block must name every skill contract)"
            for s in sorted(on_disk) if s not in text]
    out += [f"Makefile leg preload `{s}` is not named in {DOC_NAME}'s description "
            f"(issue #935: a dropped `-s` pointer must fail the gate)"
            for s in sorted(lane_names) if s not in text]

    # Cadence claims (issue #1032): what the documents SAY starts a pipeline must be
    # what the workflow declares. Rule 6t (owner directive 2026-11-15) left ONE cron in
    # the tree; the alarm prose still said "weekly"/"scheduled"/"twice-an-hour", so a
    # reader waited for a cadence that no longer fires.
    out += cadence_findings(root, workflows, {DOC_NAME: text, AGENTS_DOC: agents_text})
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
          f"({len(public_targets(root))}), workflow and script — and its "
          f"`--only` stage lists and §4 job names match the tree")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
