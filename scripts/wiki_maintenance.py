#!/usr/bin/env python3
"""Offline, deterministic wiki/doc freshness checker (issue #1773).

The board needs the written documentation to stay true to the fetched tree. Two
failure modes matter, and they need DIFFERENT remedies:

  * a false claim in a doc that is otherwise current -> UPDATE the doc
    (e.g. the README's generated render stamp lags ``data/models.json``, or a
    model that is in the store has no rendered row);
  * an obsolete doc whose subject no longer exists -> ARCHIVE the doc/row
    (e.g. a rendered model row naming a model the store no longer holds, or an
    ``ARCHITECTURE.md`` inventory line naming a script that was deleted).

Truth is DERIVED from the tree — never invented, never fetched, never produced
by a model:

  * ``data/models.json``   -> the canonical model names + ``generated_utc``;
  * ``README.md``          -> the generated render (its ``[**name**](url)`` rows
                              and its ``Last generated: … UTC`` stamp);
  * ``ARCHITECTURE.md``    -> the generated inventory block (``architecture-bot:
                              begin/end``), whose ``- `path` —`` items and
                              ``#### `.github/workflows/x.yml``` headings must
                              name files that exist.

Every finding carries the exact FILE and NEEDLE (the matched claim text), so a
reader can edit or archive it without guessing, and the evidence names the tree
fact it contradicts.

Usage:
    python3 scripts/wiki_maintenance.py --check            # gate: 0 clean, 1 findings, 2 unreadable
    python3 scripts/wiki_maintenance.py --apply             # print a keeper PR body; NEVER writes docs
    python3 scripts/wiki_maintenance.py --root DIR --check  # fixture seam for the tests

``--check`` and ``--apply`` are entirely offline and stdlib-only: no ``gh``, no
network, no model call, no mutation of any doc. The optional ``--apply`` writes
only to stdout (the keeper PR body a human reviews); it never edits a doc.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# --------------------------------------------------------------------------- patterns
# A generated README model row: [**Display Name**](https://huggingface.co/…).
_MODEL_ROW = re.compile(r"\[\*\*(?P<name>[^\]]+)\*\*\]\((?P<url>[^)]+)\)")
# The generated render stamp (minute precision): "> Last generated: YYYY-MM-DD HH:MM UTC".
_STAMP = re.compile(
    r"^>\s*Last generated:\s*(?P<stamp>\d{4}-\d{2}-\d{2} \d{2}:\d{2})\s*UTC", re.MULTILINE)
# ``data/models.json`` generated_utc -> the minute the README render must carry.
_GEN_MINUTE = re.compile(r"^(\d{4}-\d{2}-\d{2})T(\d{2}:\d{2})")
# ARCHITECTURE.md's generated inventory block and its two path spellings.
_BLOCK_BEGIN = "<!-- architecture-bot:begin -->"
_BLOCK_END = "<!-- architecture-bot:end -->"
_INV_ITEM = re.compile(r"^\s*-\s+`(?P<path>[^`]+)`\s+—", re.MULTILINE)
_INV_WORKFLOW = re.compile(r"^####\s+`(?P<path>\.github/workflows/[^`]+\.yml)`", re.MULTILINE)

# The two action classes, named so a report can be counted without a second parser.
UPDATE = "update"
ARCHIVE = "archive"
FALSE_CLAIM = "false-claim"
OBSOLETE_DOC = "obsolete-doc"


class Unreadable(RuntimeError):
    """A truth source could not be read — a loud exit 2, never a silent clean."""


class Empty(Exception):
    """``--apply`` with no findings has no keeper body to compose."""


@dataclass(frozen=True)
class Facts:
    names: frozenset[str]
    stamp: str
    generated_utc: str


@dataclass(frozen=True)
class Finding:
    kind: str      # FALSE_CLAIM | OBSOLETE_DOC
    action: str    # UPDATE | ARCHIVE
    file: str
    needle: str
    evidence: str

    def render(self) -> str:
        return (f"FINDING kind={self.kind} action={self.action} file={self.file} "
                f"needle={self.needle!r} evidence={self.evidence!r}")


def _read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except OSError as exc:
        raise Unreadable(f"cannot read {path}: {exc}") from exc


def data_facts(root: Path) -> Facts:
    """Canonical model names + render stamp, derived from ``data/models.json``."""
    store = root / "data" / "models.json"
    if not store.is_file():
        raise Unreadable(f"missing truth source {store}")
    try:
        payload = json.loads(_read(store))
    except json.JSONDecodeError as exc:
        raise Unreadable(f"unparseable {store}: {exc}") from exc
    names = frozenset(
        str(row["name"]) for row in (payload.get("models") or [])
        if isinstance(row, dict) and row.get("name"))
    generated = str(payload.get("generated_utc") or "")
    match = _GEN_MINUTE.match(generated)
    stamp = f"{match.group(1)} {match.group(2)}" if match else ""
    return Facts(names=names, stamp=stamp, generated_utc=generated)


def readme_rows(root: Path) -> list[str]:
    """Every model name the generated README render claims a row for."""
    return [m.group("name") for m in _MODEL_ROW.finditer(_read(root / "README.md"))]


def readme_stamp(root: Path) -> str:
    """The README's rendered ``Last generated`` minute (empty when absent)."""
    match = _STAMP.search(_read(root / "README.md"))
    return match.group("stamp") if match else ""


def inventory_paths(root: Path) -> list[str]:
    """Every path the generated ARCHITECTURE.md inventory block claims exists."""
    doc = _read(root / "ARCHITECTURE.md")
    if _BLOCK_BEGIN not in doc or _BLOCK_END not in doc:
        raise Unreadable("ARCHITECTURE.md has no architecture-bot begin/end block")
    block = doc[doc.index(_BLOCK_BEGIN):doc.index(_BLOCK_END)]
    items = [m.group("path") for m in _INV_ITEM.finditer(block)]
    workflows = [m.group("path") for m in _INV_WORKFLOW.finditer(block)]
    return items + workflows


def findings(root: Path) -> list[Finding]:
    """Every stale/false claim and obsolete doc in the tree, never empty by accident."""
    facts = data_facts(root)
    rendered = readme_rows(root)
    found: list[Finding] = []

    # Obsolete docs: a rendered row whose subject is gone from the store.
    for name in sorted(set(rendered) - facts.names):
        found.append(Finding(
            OBSOLETE_DOC, ARCHIVE, "README.md", f"[**{name}**]",
            f"rendered row names {name!r}, absent from data/models.json models[]"))

    # False claims: a store model the render failed to include (a stale render).
    for name in sorted(facts.names - set(rendered)):
        found.append(Finding(
            FALSE_CLAIM, UPDATE, "README.md", f"[**{name}**]",
            f"data/models.json models[] carries {name!r}, no README row renders it"))

    # False claim: the generated stamp disagrees with the store's generated_utc.
    stamp = readme_stamp(root)
    if facts.stamp and stamp != facts.stamp:
        found.append(Finding(
            FALSE_CLAIM, UPDATE, "README.md", f"Last generated: {stamp} UTC",
            f"README stamp {stamp!r} != data/models.json generated_utc "
            f"{facts.generated_utc!r} (expected {facts.stamp!r})"))

    # Obsolete docs: an inventory line naming a file that no longer exists.
    for path in sorted(set(inventory_paths(root))):
        if not (root / path).exists():
            found.append(Finding(
                OBSOLETE_DOC, ARCHIVE, "ARCHITECTURE.md", path,
                f"inventory names {path!r}, which is absent from the tree"))
    return found


def check(root: Path) -> int:
    """Report every finding with exact file+needle; 0 clean, 1 findings, 2 unreadable."""
    try:
        found = findings(root)
    except Unreadable as exc:
        print(f"[wiki-maintenance] READ FAILED: {exc}", file=sys.stderr)
        return 2
    for finding in found:
        print(finding.render())
    if found:
        updates = sum(1 for f in found if f.action == UPDATE)
        archives = sum(1 for f in found if f.action == ARCHIVE)
        print(f"[wiki-maintenance] {len(found)} finding(s): "
              f"{updates} update / {archives} archive (issue #1773)")
        return 1
    print("[wiki-maintenance] OK: no stale claim or obsolete doc; "
          "README render and ARCHITECTURE.md inventory match the tree")
    return 0


def keeper_body(found: list[Finding], root: Path) -> str:
    """Compose the keeper PR body from the findings. Writes NOTHING to the tree.

    A keeper implements no issue, so by rule 6e it carries NO closing keyword —
    ``pr_closure.check(body, 'ci/keeper-wiki-maintenance-…')`` stays empty. The
    body tells the human exactly which claims to update and which docs to
    archive, each with the exact file+needle the checker reported.
    """
    if not found:
        raise Empty("no findings — there is no keeper PR body to compose")
    updates = [f for f in found if f.action == UPDATE]
    archives = [f for f in found if f.action == ARCHIVE]
    lines = [
        "A daily wiki-maintenance read found documentation that no longer matches the "
        "fetched tree. This keeper records the findings; it does NOT edit any doc — "
        "a human updates the false claims and archives the obsolete docs.",
        "",
        f"Truth sources: data/models.json, README.md render, ARCHITECTURE.md inventory "
        f"(findings={len(found)}, update={len(updates)}, archive={len(archives)}).",
        "",
        "## False claims to update",
        "",
    ]
    lines += [f"- `{f.file}` :: `{f.needle}` — {f.evidence}" for f in updates] or ["- none"]
    lines += ["", "## Obsolete docs to archive", ""]
    lines += [f"- `{f.file}` :: `{f.needle}` — {f.evidence}" for f in archives] or ["- none"]
    lines += [
        "",
        "The checker is offline and deterministic (no network, no model call) and "
        "`make wiki-maintenance-check` is green once the recorded claims are fixed. "
        "Tracking issue: #1773 (referenced, never closed: this keeper implements no issue).",
    ]
    return "\n".join(lines) + "\n"


def apply(root: Path) -> int:
    """Print the keeper PR body to stdout; never mutate a doc."""
    try:
        found = findings(root)
    except Unreadable as exc:
        print(f"[wiki-maintenance] READ FAILED: {exc}", file=sys.stderr)
        return 2
    try:
        sys.stdout.write(keeper_body(found, root))
    except Empty as exc:
        print(f"[wiki-maintenance] {exc}", file=sys.stderr)
        return 2
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root", default=str(ROOT), help="repository root (default: this checkout)")
    mode = ap.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true", help="offline gate (0 clean, 1 findings, 2 unreadable)")
    mode.add_argument("--apply", action="store_true", help="print the keeper PR body; never edit a doc")
    args = ap.parse_args(argv)
    return check(Path(args.root)) if args.check else apply(Path(args.root))


if __name__ == "__main__":
    raise SystemExit(main())
