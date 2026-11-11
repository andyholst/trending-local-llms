# Proposal: section-boundary-anchors

Issue: #509 (tech-debt, "A guard that reads the wrong section boundary passes silently")

## Why

`scripts/architecture_check.py` locates the parts of `ARCHITECTURE.md` and
`AGENTS.md` it is allowed to read by **heading text**:

```python
def section(text: str, heading: str) -> str:
    m = re.search(rf"^## {heading}\.?", text, re.M)
    if not m:
        return ""
    nxt = re.search(r"^## ", text[m.end():], re.M)
    return text[m.end(): m.end() + (nxt.start() if nxt else len(text) - m.end())]
```

so `scripts_readable = bool(section(doc, "6"))` and the §3 target tables are the
text between `## 3.` and `## 4.`. A heading is renumberable prose: issue #479
added §10 and renumbered sections, and nothing noticed. When a document
renumbers, the guard silently reads a different region — the target tables stop
being checked, a script's §6 role is no longer looked for, and the finding that
then appears ("every script has no row in §6") is loud but for the wrong reason.
The guard's boundary is therefore a guess about a document it is actually
describing.

Measured on `origin/master` before this change:

```
$ grep -n '^## ' ARCHITECTURE.md
8:## 1. The product  …  108:## 10. The pipelines, end to end (generated)
$ python3 -c "…section(doc,'6')…"      # the §6 slice is whatever sits between
                                        # "## 6." and the NEXT "## " — not §6's table
```

## What Changes

- **`ARCHITECTURE.md`** gains one HTML-comment anchor beside each section the
  guard reads: `<!-- arch:targets -->`, `<!-- arch:pipelines -->`,
  `<!-- arch:scripts -->`, `<!-- arch:guards -->`.
- **`AGENTS.md`** gains the two anchors its rulebook sections need:
  `<!-- agents:rulebook -->` beside §6b and `<!-- agents:style -->` beside §7.
`scripts/architecture_check.py` replaces heading matching with an anchor
  registry (`_REQUIRED_ANCHORS`) and a `section(text, start, end)` helper that
  reads from the anchor to the next anchor (or the end of the file), plus an
  `anchor_findings()` pass that reports, as findings, a document that **loses an
  anchor** or holds an anchor **with no section heading beside it** (an anchor
  moved away from its section is exactly the drift #509 is about). The section
  *number* is now irrelevant to the guard; the anchor is the boundary.
- **`tests/test_architecture.py`** carries the anchor list in one constant shared
  with the fixture builder, and four new cases: a document missing an anchor is
  reported; restoring it turns that finding green; an anchor stranded away from
  any heading is reported; and a fixture whose sections are **renumbered** stays
  green — the guard reads the right region regardless of the numbers.

## Impact

- `make architecture-check` (and therefore `make test`, the fix loop and
  `qa-validate`'s `validate` job) fails when either document loses a boundary
  anchor, so a renumbering can no longer repoint a check unnoticed.
- No data, contract, README table, make target, workflow or image changes.
- The `AGENTS.md` diff is anchor comments plus a §8 guard-table row — the
  review-required half under rule 3c.

## Not covered

- The guard still does not verify the *prose* of §6's role text or §4's per-pipeline
  description — that boundary is unchanged and documented in those sections.
- `OPENSPEC.md` and `ARCHITECTURE.md` §10 are generated; their sections keep their
  own anchors in the generator's output, and `scripts/architecture_bot.py` is not
  changed by this work.
