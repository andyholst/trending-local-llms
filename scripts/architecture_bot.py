#!/usr/bin/env python3
"""Keep ARCHITECTURE.md's living inventory true to the tree (issue #479, rule 6h).

`ARCHITECTURE.md` describes the system — every pipeline, job, target, script and
the data flow between them. Its prose is hand-maintained, and the half that
answers *"which bot does what, and how does a model reach `README.md`?"* rots
silently between touches: `make architecture-check` (`scripts/architecture_check.py`)
notices a workflow or a script that is **missing from the description**, never a
description of a bot whose jobs, triggers or `make` targets have moved on.

This script owns the MECHANICAL half of that answer, between two markers:

    <!-- architecture-bot:begin -->
    ...
    <!-- architecture-bot:end -->

and derives every line of it from the tree, so it cannot invent a claim and
cannot drift from what it describes:

  * every workflow in `.github/workflows/` — its `name:`, its triggers and cron
    slots, its jobs in file order with their `needs`, and the `make` targets each
    job runs, each carrying the Makefile's own `##` description;
  * the end-to-end flow of the product (`FLOW`): the search legs → `data/raw/*`
    → `data/models.json` → the trend fields → `README.md` → the snapshot, with
    every named target, script and artifact VERIFIED to exist;
  * one line per script in `scripts/`, from that script's own module docstring;
  * the `##` section headings `README.md` carries — the surface a refresh
    rewrites.

`--write` replaces the block; `--check` fails when the block on disk is stale
(so `make architecture-check` — the rule-6h gate — catches a description that
stopped matching the code). `make architecture-refresh` is how a human or
`.github/workflows/architecture-bot.yml` runs the write; the daily bot opens a PR
only when the block actually changed.

Usage:
    python3 scripts/architecture_bot.py --write
    python3 scripts/architecture_bot.py --check
    python3 scripts/architecture_bot.py --write --root DIR   # a fixture tree
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

BEGIN = "<!-- architecture-bot:begin -->"
END = "<!-- architecture-bot:end -->"

WF_DIR = Path(".github") / "workflows"
SCRIPTS_DIR = Path("scripts")

#: The product, end to end. Each entry is (stage, command, reads, writes, note).
#: Every entry is VERIFIED against the tree (`_flow_problems`): the `make` target
#: must exist in the Makefile, the script must exist, and an artifact's directory
#: (or the artifact itself, when it is a single file) must exist. A flow line
#: that describes something the repository no longer has is a loud failure, never
#: a stale sentence.
FLOW: tuple[tuple[str, str, tuple[str, ...], tuple[str, ...], str], ...] = (
    ("1. Search",
     "make search",
     ("lightbrd.com mirror, via the Firecrawl scrape API",),
     ("data/raw/<backend>-<UTC>.json",),
     "One leg per backend (`SEARCH_LEGS`: nvidia, metal, cpu, amd — `search-<backend>` "
     "runs one); every call writes its own snapshot, so a later call never overwrites an "
     "earlier one."),
    ("2. Ingest",
     "make merge",
     ("data/raw/*.json",),
     ("data/models.json",),
     "`scripts/update_trending.py` folds the raw snapshots into the store "
     "(`ingest_raw_snapshots`): adds models and measurements, fills absent keys and never "
     "removes or shrinks one (rule 3b)."),
    ("3. Rank",
     "make merge",
     ("data/models.json",),
     ("trend_score / buzz_7d (derived fields in the store)",),
     "`recompute_7d_engagement` scores the last 7 days of real posts "
     "(`buzz`) plus the fastest in-scope measurement (`speed`), then `sort_models` orders "
     "trending → recent → stale (rule 4: engagement first, t/s as the tie-breaker)."),
    ("4. Render",
     "make merge (or make render-readme for a template-only change)",
     ("data/models.json",),
     ("README.md",),
     "`render_readme(store, as_of=generated_utc)` rewrites every table — most loved, "
     "pick-your-card, engine matrix, the four backend tables, the engine guide — so the "
     "README is never hand-edited."),
    ("5. Snap",
     "make merge",
     ("data/models.json",),
     ("data/snapshots/trending-<UTC>.json",),
     "The full store after each merge; it is what proves no model was ever removed "
     "(`check_no_removal`) or lost a value (`check_no_value_loss`)."),
)

_MAKE_CALL = re.compile(r"(?<![\w-])make\s+([a-z_][a-z0-9_-]*)")
_TARGET_DOC = re.compile(r"^([a-z][a-z0-9-]*):[^\n]*?##\s*(\S.*)$", re.MULTILINE)
_CRON = re.compile(r'-\s*cron:\s*["\']?([^"\'\n]+)')
_JOB = re.compile(r"^  ([A-Za-z0-9_-]+):\s*$", re.MULTILINE)
_NEEDS = re.compile(r"^    needs:\s*(.+)$", re.MULTILINE)
_WF_NAME = re.compile(r"^name:\s*(.+)$", re.MULTILINE)
#: The README's surface: its title, its `##` sections and its `#` backend tables.
#: The card tiers are `### 8 GB` … — one per tier, and a data value rather than a
#: section a refresh is judged by, so they are not listed.
_HEADING = re.compile(r"^#{1,2}\s+(.+?)\s*$", re.MULTILINE)
_DOC_FIRST = re.compile(r'^\s*(?:#!.*\n)?\s*(?:"""|\'\'\')\s*([^\n]+)')


class ArchitectureBotError(RuntimeError):
    """The tree cannot be described as it stands — a loud failure, never a guess."""


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.is_file() else ""


def make_descriptions(root: Path) -> dict[str, str]:
    """Every make target that carries a `## description`, from the Makefile."""
    out: dict[str, str] = {}
    for name, desc in _TARGET_DOC.findall(_read(root / "Makefile")):
        out.setdefault(name, desc.strip())
    return out


def make_targets(root: Path) -> set[str]:
    """Every public and internal make target the Makefile defines."""
    names = set(make_descriptions(root))
    for line in _read(root / "Makefile").splitlines():
        m = re.match(r"^([A-Za-z_][A-Za-z0-9_-]*):(?!=)", line)
        if m:
            names.add(m.group(1))
    return names


def _on_block(text: str) -> list[str]:
    """The lines of the workflow's top-level `on:` block."""
    lines = text.splitlines()
    for i, line in enumerate(lines):
        if line.rstrip() == "on:":
            body: list[str] = []
            for nxt in lines[i + 1:]:
                if nxt.strip() and not nxt.startswith((" ", "\t")):
                    break
                body.append(nxt)
            return body
    # the `on: [push]` inline shape
    return [line for line in lines if line.startswith("on:")]


def workflow_triggers(text: str) -> str:
    """A human summary of a workflow's triggers, crons included."""
    body = _on_block(text)
    crons = _CRON.findall(text)
    events: list[str] = []
    inline = next((l for l in body if l.startswith("on:")), "")
    if inline:
        events += [e.strip() for e in re.findall(r"[a-z_]+", inline.split(":", 1)[1])]
    for line in body:
        m = re.match(r"^  ([a-z_]+):", line)
        if m and m.group(1) not in ("types",):
            events.append(m.group(1))
    events = [e for e in dict.fromkeys(events) if e not in ("types",)]
    parts: list[str] = []
    if crons:
        parts.append("cron " + ", ".join(f"`{c}`" for c in crons))
    for e in events:
        if e == "schedule" and crons:
            continue
        parts.append(f"`{e}`")
    return ", ".join(parts) if parts else "not declared"


def _jobs_section(text: str) -> str:
    """The workflow's `jobs:` block — job ids only live there.

    The `on:` block is indented the same way (`  schedule:`, `  workflow_dispatch:`),
    so a job scan over the whole file would report the TRIGGERS as jobs.
    """
    lines = text.splitlines()
    for i, line in enumerate(lines):
        if line.rstrip() == "jobs:":
            return "\n".join(lines[i + 1:])
    return ""


def workflow_jobs(text: str) -> list[tuple[str, list[str]]]:
    """Every job of a workflow, in file order, with its `needs`."""
    section = _jobs_section(text)
    marks = [(m.start(), m.group(1)) for m in _JOB.finditer(section)]
    out: list[tuple[str, list[str]]] = []
    for i, (pos, name) in enumerate(marks):
        end = marks[i + 1][0] if i + 1 < len(marks) else len(section)
        block = section[pos:end]
        needs: list[str] = []
        m = _NEEDS.search(block)
        if m:
            needs = [n.strip("'\" ") for n in m.group(1).strip("[]").split(",") if n.strip()]
        out.append((name, needs))
    return out


def run_blocks(text: str) -> str:
    """The bodies of a workflow's `run:` steps, joined.

    Scanning the whole YAML would read the file's own COMMENTS as pipeline
    behaviour (`# ... make them ...` in a comment is not a call), and a
    description that reports a target nobody runs is worse than no line at all.
    Comments OUTSIDE a `run:` block are dropped; shell comments inside one are
    kept, because a `make` in a shell comment is still text a reader sees.
    """
    lines = text.splitlines()
    out: list[str] = []
    i = 0
    while i < len(lines):
        line = lines[i]
        m = re.match(r"^(\s*)(?:-\s+)?run:\s*(\||>|-)?\s*(.*)$", line)
        if not m:
            i += 1
            continue
        indent = len(m.group(1))
        inline = (m.group(3) or "").strip()
        if inline and not inline.startswith(("|", ">")):
            out.append(inline)
            i += 1
            continue
        i += 1
        while i < len(lines):
            nxt = lines[i]
            if nxt.strip() and (len(nxt) - len(nxt.lstrip())) <= indent:
                break
            out.append(nxt)
            i += 1
    return "\n".join(out)


_HEREDOC = re.compile(r"<<-?\s*(['\"]?)(?P<word>[A-Za-z_][A-Za-z0-9_]*)\1")
_QUOTED = re.compile(r"\"(?:[^\"\\]|\\.)*\"|'[^']*'")


def command_text(block: str) -> str:
    """The parts of a `run:` block a shell would EXECUTE (issue #544).

    Two shapes in a real `run:` block are TEXT, not commands, and both were being
    read as calls:

    * a HEREDOC body (`cat > f <<'EOF' … make validate … EOF`) — the lines are a
      file's content, and one of them happening to say `make validate` is prose;
    * a QUOTED string (`echo "this PR passes make openspec-check"`) — the shell
      never splits it into a command.

    A `make` inside either is dropped here, so the inventory cannot claim a target
    the pipeline never runs. Shell comments are left alone on purpose: a `make` a
    reader can SEE in a step is deliberately still reported.
    """
    out: list[str] = []
    pending: str | None = None
    for line in block.splitlines():
        if pending is not None:
            if line.strip() == pending:
                pending = None
            continue
        m = _HEREDOC.search(line)
        if m:
            pending = m.group("word")
        out.append(_QUOTED.sub(" ", line))
    return "\n".join(out)


def workflow_targets(text: str, targets: set[str]) -> list[str]:
    """The `make` targets a workflow's steps call, in first-use order.

    Only a target the Makefile really defines is reported — a word in prose that
    happens to follow `make` is not a call, and neither is one inside a heredoc body
    or a quoted string (`command_text`, issue #544) — and a dynamic call
    (`make search-${{ matrix.backend }}`) is rendered as its static prefix plus
    `*`, so the inventory never claims a target name that does not exist.
    """
    seen: list[str] = []
    for m in _MAKE_CALL.finditer(command_text(run_blocks(text))):
        raw = m.group(1)
        tail = m.string[m.end():]
        # `make search-${{ matrix.backend }}` captures `search-` (the class allows a
        # hyphen), so the trailing one is the CALL'S, not the target's.
        dynamic = raw.endswith("-") and tail.startswith("$")
        name = raw.rstrip("-") if dynamic else raw
        if dynamic:
            rendered = f"{name}-*" if name in targets else None
        elif tail.startswith("$"):
            # `make ${TARGET}` — a name that is not in the file at all; never guessed.
            rendered = None
        else:
            rendered = name if name in targets else None
        if rendered and rendered not in seen:
            seen.append(rendered)
    return seen


def script_lines(root: Path) -> list[str]:
    """One line per script, from the script's own docstring — no second prose."""
    out: list[str] = []
    for path in sorted(p for p in (root / SCRIPTS_DIR).glob("*") if p.is_file()):
        first = ""
        text = _read(path)
        m = _DOC_FIRST.search(text)
        if m:
            first = m.group(1).strip()
        elif path.suffix == ".sh":
            for line in text.splitlines():
                if line.startswith("#") and not line.startswith("#!"):
                    first = line.lstrip("# ").strip()
                    break
        out.append(f"`scripts/{path.name}` — {first or '(no docstring)'}")
    return out


def readme_sections(root: Path) -> list[str]:
    """The `##` headings of the generated README — the surface a refresh rewrites."""
    return [h for h in _HEADING.findall(_read(root / "README.md"))]


def _flow_problems(root: Path) -> list[str]:
    """Every FLOW reference the tree no longer backs."""
    problems: list[str] = []
    targets, have = make_targets(root), root
    for stage, command, reads, writes, _note in FLOW:
        for name in _MAKE_CALL.findall(command):
            if name not in targets:
                problems.append(f"flow step {stage!r} names `make {name}`, which is not a make target")
        for ref in (*reads, *writes):
            if ref.startswith("scripts/"):
                if not (have / ref).is_file():
                    problems.append(f"flow step {stage!r} names `{ref}`, which does not exist")
                continue
            if ref.startswith(("lightbrd", "trend_score", "buzz")):
                continue
            probe = ref.split("<", 1)[0].rstrip("/") or ref
            path = have / probe
            if not (path.exists() or path.parent.exists()):
                problems.append(f"flow step {stage!r} names `{ref}`, whose directory does not exist")
    return problems


def render(root: Path) -> str:
    """The generated block for this tree (deterministic: no dates, no SHAs)."""
    descs = make_descriptions(root)
    targets = make_targets(root)
    wfs = sorted(p for p in (root / WF_DIR).glob("*.yml"))
    if not wfs:
        raise ArchitectureBotError(f"no workflows under {WF_DIR}/ — nothing to describe")

    lines: list[str] = [
        "_Generated from the tree itself by `scripts/architecture_bot.py` "
        "(`make architecture-refresh`); `.github/workflows/architecture-bot.yml` "
        "regenerates it daily and opens a PR only when it changed. Do not edit this "
        "block by hand — change the code it describes and run the target._",
        "",
        f"### Bots in the tree ({len(wfs)} pipelines, {len(targets)} make targets, "
        f"{len([p for p in (root / SCRIPTS_DIR).glob('*') if p.is_file()])} files in "
        "`scripts/`)",
        "",
        "Every pipeline, what starts it, the jobs it runs and the `make` targets those "
        "jobs call (with the Makefile's own description of each target).",
        "",
    ]
    for path in wfs:
        text = _read(path)
        nm = _WF_NAME.search(text)
        label = nm.group(1).strip() if nm else path.name
        lines.append(f"#### `.github/workflows/{path.name}` — {label}")
        lines.append("")
        lines.append(f"- **when:** {workflow_triggers(text)}")
        jobs = workflow_jobs(text)
        if jobs:
            chain = ", ".join(
                f"`{j}`" + (f" (needs {', '.join('`%s`' % n for n in needs)})" if needs else "")
                for j, needs in jobs)
            lines.append(f"- **jobs:** {chain}")
        calls = workflow_targets(text, targets)
        if calls:
            described = []
            for c in calls:
                desc = descs.get(c)
                described.append(f"`make {c}`" if not desc else f"`make {c}` — {_shorten(desc)}")
            lines.append("- **calls:** " + "; ".join(described))
        lines.append("")

    lines += [
        "### The product, end to end",
        "",
        "How a model gets from an X post to a `README.md` row. Every step below is a real "
        "target and a real artifact (`make architecture-check` fails when one is gone).",
        "",
        "| Stage | Runs | Reads | Writes | Why it is that way |",
        "|---|---|---|---|---|",
    ]
    for stage, command, reads, writes, note in FLOW:
        lines.append("| {} | {} | {} | {} | {} |".format(
            stage, _cell(command), _cell(", ".join(reads)), _cell(", ".join(writes)), _cell(note)))

    lines += ["", "### `README.md` — the sections a refresh rewrites", ""]
    sections = readme_sections(root)
    if sections:
        lines += [f"- {_shorten(h, 120)}" for h in sections]
    else:
        lines.append("- (no `##` sections found — `README.md` is missing)")
    lines += [
        "",
        "`README.md` is generated, never hand-edited (`AGENTS.md` §5b): a change goes "
        "into the store or the renderer's template, then `make merge` or "
        "`make render-readme`.",
        "",
        "### Every script",
        "",
        "One line each, taken from the script's own docstring.",
        "",
    ]
    lines += [f"- {line}" for line in script_lines(root)]
    return "\n".join(lines).rstrip() + "\n"


def _shorten(text: str, limit: int = 190) -> str:
    text = " ".join(text.split())
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "…"


def _cell(text: str) -> str:
    """A markdown table cell: no raw pipe, no newline."""
    return " ".join(str(text).split()).replace("|", "\\|")


def block_on_disk(doc: str) -> str | None:
    """The block between the markers, or None when a marker is missing."""
    start = doc.find(BEGIN)
    end = doc.find(END)
    if start < 0 or end < start:
        return None
    return doc[start + len(BEGIN):end]


def write_block(doc: str, block: str) -> str:
    start = doc.find(BEGIN)
    end = doc.find(END)
    if start < 0 or end < start:
        raise ArchitectureBotError(
            f"ARCHITECTURE.md has no `{BEGIN}` / `{END}` pair — the generated block "
            "has nowhere to go; restore the markers (they are part of the document's shape)")
    return doc[: start + len(BEGIN)] + "\n" + block + doc[end:]


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Keep ARCHITECTURE.md's inventory true to the tree")
    ap.add_argument("--root", default=str(Path(__file__).resolve().parents[1]))
    mode = ap.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", action="store_true", help="regenerate the block in ARCHITECTURE.md")
    mode.add_argument("--check", action="store_true", help="fail when the block on disk is stale")
    a = ap.parse_args(argv)

    root = Path(a.root)
    doc_path = root / "ARCHITECTURE.md"
    if not doc_path.is_file():
        print(f"[architecture-bot] FAIL {doc_path.name} is missing (rule 6h)", file=sys.stderr)
        return 1
    doc = doc_path.read_text(encoding="utf-8")
    try:
        block = render(root)
    except ArchitectureBotError as exc:
        print(f"[architecture-bot] FAIL {exc}", file=sys.stderr)
        return 1

    if a.write:
        # A generator that writes a description of something that is not there is
        # worse than no generator: the flow is verified before it is written, and
        # the file is left untouched when it is not backed.
        problems = _flow_problems(root)
        if problems:
            print("[architecture-bot] FAIL the described flow is not backed by the tree "
                  "— ARCHITECTURE.md was NOT written:", file=sys.stderr)
            for p in problems:
                print(f"[architecture-bot]   - {p}", file=sys.stderr)
            return 1
        doc_path.write_text(write_block(doc, block), encoding="utf-8")
        print(f"[architecture-bot] wrote the inventory block in {doc_path.name} "
              f"({len(block.splitlines())} lines)")
        return 0

    problems = _flow_problems(root)
    if problems:
        print("[architecture-bot] FAIL the described flow is not backed by the tree:", file=sys.stderr)
        for p in problems:
            print(f"[architecture-bot]   - {p}", file=sys.stderr)
        return 1
    current = block_on_disk(doc)
    if current is None:
        print(f"[architecture-bot] FAIL {doc_path.name} carries no `{BEGIN}` / `{END}` block "
              "— the description is not generated any more (run `make architecture-refresh`)",
              file=sys.stderr)
        return 1
    if current.strip("\n") == block.strip("\n"):
        print("[architecture-bot] OK the inventory block matches the tree "
              f"({len(block.splitlines())} lines)")
        return 0
    print("[architecture-bot] FAIL the inventory block is STALE — the tree moved on and the "
          "description did not:", file=sys.stderr)
    for line in _first_differences(current.splitlines(), block.splitlines()):
        print(f"[architecture-bot]   {line}", file=sys.stderr)
    print("[architecture-bot] run `make architecture-refresh`, then commit ARCHITECTURE.md "
          "with the change that moved it (rule 6h)", file=sys.stderr)
    return 1


def _first_differences(have: list[str], want: list[str], limit: int = 8) -> list[str]:
    """A bounded, readable account of what changed — enough to act on, not a dump."""
    out: list[str] = []
    for i, (h, w) in enumerate(zip(have, want)):
        if h != w:
            out.append(f"line {i + 1}: on disk {h.strip()!r}")
            out.append(f"line {i + 1}: tree     {w.strip()!r}")
            if len(out) >= limit:
                return out
    if len(have) != len(want):
        out.append(f"the block has {len(have)} lines on disk and {len(want)} from the tree")
    return out or ["the block differs only in surrounding whitespace"]


if __name__ == "__main__":
    sys.exit(main())
