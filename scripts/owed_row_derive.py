"""Derive owed-row declarations from the text a filer files (issue #765).

`scripts/bot_markers.py` renders and parses the owed-row marker, and
`scripts/owed_rows_check.py` reads the ledger — but until #765 NOTHING stamped a
marker at FILING time unless a findings.md carried an explicit `- **Owed-row:**`
field, so 23 open issues named their owed AGENTS.md row only in prose and
`make owed-rows-check` could only answer `NO MARKER`.

This module is the ONE derivation both filers use (rule 6d): given the Done-when
text (findings) or the composed body (data gaps) plus the live AGENTS.md, it
answers which owed-row declarations the text actually states. It never invents
one:

  * a section is only derived from a `§<id>`, `AGENTS.md section <id>` or
    `rule <id>` mention, AND the id must exist as a `## <id>.` heading in
    AGENTS.md — the SAME heading parser `owed_rows_check.sections()` uses, so a
    filer can never stamp a marker the ledger would refuse as
    `NO SUCH SECTION` (which turns `owed-rows-check` exit 2);
  * a needle is only derived from an identifier the text itself names — a
    `make <target>`, a `tests/test_*.py`, a `scripts/*.py`, or a `check_*`
    name — because a landed guard row names exactly those things;
  * if either half is not stated, the answer is `[]`: the filed issue then shows
    as `NO MARKER` in the ledger, which is honest, never a fabricated claim.

"""
from __future__ import annotations

import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

# The ONE heading parser (rule 6d): the ledger's definition of "a section that
# exists" is owed_rows_check's, and the filer must stamp only what the ledger
# can read — importing it is the disagreement-proof seam.
from owed_rows_check import sections  # noqa: E402

# Section mentions the filers accept. `rule <id>` is included because AGENTS.md
# cross-references its own numbered rules ("rule 6b"); ids that are NOT headings
# (rule 3b lives inside §2) are filtered by the heading check, never stamped.
_SECTION_REF = re.compile(
    r"§\s*([0-9]+[a-z]?)"
    r"|AGENTS\.md\s+section\s+([0-9]+[a-z]?)"
    r"|\brule\s+([0-9]+[a-z]?)",
    re.IGNORECASE,
)

# Candidate needles, first match wins. A landed §8 guard row names the make
# target, the test file, the script or the check_* it locks — the same shapes a
# Done-when sentence names. A free quoted phrase is NOT derived (an explicit
# `- **Owed-row:**` field may use one; a derivation may not — a phantom needle
# would file a false ledger row).
_NEEDLE_PATTERNS = (
    re.compile(r"\bmake\s+([a-z][a-z0-9-]+)"),
    re.compile(r"\btests/test_[a-z0-9_]+\.py"),
    re.compile(r"\bscripts/[a-z_0-9]+\.py"),
    re.compile(r"\bcheck_[a-z0-9_]+\b"),
)


def derive_rows(text: str, agents_text: str) -> list[dict]:
    """The owed-row declarations THIS text states, ready for bot_markers.owed_row_marker.

    -> [{"section": "<id>", "needle": "<n>", "derived": True}, ...] (possibly []).
    A `derived: True` row is always re-rendered through the ONE marker writer,
    exactly like an explicit `- **Owed-row:**` field.
    """
    if not text:
        return []
    ids: list[str] = []
    for m in _SECTION_REF.finditer(text):
        sid = m.group(1) or m.group(2) or m.group(3)
        if sid not in ids:
            ids.append(sid)
    if not ids:
        return []
    needle = ""
    for pat in _NEEDLE_PATTERNS:
        m = pat.search(text)
        if m:
            needle = m.group(1) if m.groups() else m.group(0)
            break
    if not needle:
        return []
    known = sections(agents_text or "")
    return [{"section": sid, "needle": needle, "derived": True}
            for sid in ids if sid in known]


if __name__ == "__main__":  # a tiny manual probe: derive from a sentence
    agents = pathlib.Path("AGENTS.md").read_text(encoding="utf-8")
    print(derive_rows(sys.argv[1], agents))
