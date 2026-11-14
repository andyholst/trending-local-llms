"""Report the owed-row ledger: what open issues say AGENTS.md still owes (issue #523).

The ledger problem rule 3c produced: every run whose write to the protected `AGENTS.md` was
refused filed its own owed-row issue (#212 #314 #322 #324 #369 #380 #385 #405, each restating
the same mechanism), and "has the row landed yet?" was answerable only by re-reading a thread.
An issue now carries the answer in a machine-readable form — `owed-row` markers (registered in
`scripts/bot_markers.py`, the ONE marker definition, rule 6j) — and this tool reads them:

  * list the repo's OPEN issues (same `gh` seam as the other live alarms),
  * read each whole thread (body + every comment, paginated — issue #662's one-page bug must
    not be repeated by a new reader),
  * parse every `owed-row` declaration through the shared parser,
  * search the tree's `AGENTS.md` for the declared needle INSIDE the declared section, and
  * print one loud line per owed row: `landed AGENTS.md:<line>` or `outstanding`.

Exit codes: 0 = the report was produced (a landed row is news, not a failure; closing the issue
is a human's act, rule 6j). 2 = the ledger could not be read: `gh` failed, AGENTS.md is
unreadable, a named section does not exist, or a marker is malformed. Read-only — this tool
never edits an issue body, never writes a label, never closes anything.

The marker grammar (name, shape, parser) lives ONLY in `scripts/bot_markers.py` (rule 6j):
`owed_row_marker()` writes it, `parse_owed_rows()` reads it. This script restates neither.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import re
import subprocess
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from bot_markers import OWED_ROW, parse_owed_rows  # noqa: E402  (ONE marker definition, rule 6j)
from issue_queue import QUEUE_LABELS  # noqa: E402  (ONE queue label list, rule 6j)


def _gh(args: list[str]) -> str:
    """One gh call; failure raises (mirrors scripts/queued_run_alarm.py — no silent empty read)."""
    r = subprocess.run(["gh", *args], capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"gh {' '.join(args)} failed: {r.stderr.strip()}")
    return r.stdout


def open_issues(repo: str, limit: int) -> list[dict]:
    """The repo's open issues with their labels (oldest first)."""
    out = json.loads(_gh(["issue", "list", "--repo", repo, "--state", "open",
                          "--limit", str(limit),
                          "--json", "number,title,labels,createdAt"]) or "[]")
    return sorted(out, key=lambda i: i.get("createdAt") or "")


def thread(issue_json: dict, comments_json: list[dict]) -> str:
    """The WHOLE thread text: body first, every comment oldest-first (#522's rule for readers)."""
    parts = [issue_json.get("body") or ""]
    for c in sorted(comments_json, key=lambda c: c.get("created_at") or ""):
        parts.append(c.get("body") or "")
    return "\n".join(parts)


def read_thread(repo: str, number: int) -> str:
    issue = json.loads(_gh(["api", f"/repos/{repo}/issues/{number}"]))
    # --paginate --jq ".[]" emits ONE JSON object per line (the tested repo pattern,
    # scripts/issue_thread.py:106-108); a whole-output json.loads would break the moment a
    # thread spans a page — the #662-class defect this reader must not repeat.
    raw = _gh(["api", f"/repos/{repo}/issues/{number}/comments",
               "--paginate", "--jq", ".[]"])
    comments = [json.loads(line) for line in raw.splitlines() if line.strip()]
    return thread(issue, comments)


def sections(agents_text: str) -> dict[str, tuple[int, int]]:
    """`{section-id: (start_line, end_line)}` over `## <id>.`-headings, 1-indexed line spans.

    The id is the heading's own token (`6`, `6b`, `8`) — resolved from the heading TEXT, so a
    renumbering that renames a heading is visible as a missing section, never as a silent
    repoint (the defect filed as #509; this reader names what it looked for).
    """
    lines = agents_text.splitlines()
    heads: list[tuple[int, str]] = []
    for i, line in enumerate(lines, 1):
        m = re.match(r"## ([0-9]+[a-z]?)\.?\s", line + " ")
        if m:
            heads.append((i, m.group(1)))
    out: dict[str, tuple[int, int]] = {}
    for pos, (start, sid) in enumerate(heads):
        end = heads[pos + 1][0] - 1 if pos + 1 < len(heads) else len(lines)
        out.setdefault(sid, (start, end))
    return out


def row_states(parsed: dict, agents_lines: list[str],
               secs: dict[str, tuple[int, int]]) -> tuple[list[dict], int]:
    """The PURE half of the ledger: the landing state of every parsed owed-row.

    One dict per row: {section, needle, line, text, outside, missing_section}.
    `line` is the 1-indexed rulebook line where the needle appears INSIDE the declared
    section and `text` quotes that line; `outside` names a line where the needle appears
    but NOT in its section (#509's class); `missing_section` marks a row whose declared
    section heading does not exist. The problem count is missing-section rows + malformed
    markers — the same number the report gates on. Shared by the report (below) and by
    the close path (`owed_row_close_note`), so the two readers can never disagree
    (rule 6d: one implementation of the landing decision).
    """
    states: list[dict] = []
    problems = 0
    for row in parsed["rows"]:
        sid, needle = row["section"], row["needle"]
        if sid not in secs:
            states.append({"section": sid, "needle": needle, "line": None,
                           "text": None, "outside": None, "missing_section": True})
            problems += 1
            continue
        start, end = secs[sid]
        in_section = next((i for i in range(start, end + 1)
                           if needle in agents_lines[i - 1]), None)
        outside = None
        if in_section is None:
            outside = next((i for i, ln in enumerate(agents_lines, 1) if needle in ln), None)
        states.append({"section": sid, "needle": needle, "line": in_section,
                       "text": agents_lines[in_section - 1].strip() if in_section else None,
                       "outside": outside, "missing_section": False})
    problems += len(parsed["malformed"])
    return states, problems


def owed_row_close_note(repo: str, number: int | str, agents_path: pathlib.Path) -> list[str]:
    """Quote ONE issue's owed-row state for its close comment (issue #766).

    A closed owed-row issue must carry its row's fate on the thread, the way a `close`
    verdict already carries its EVIDENCE (issue #494): a LANDED row is quoted with its
    `AGENTS.md:<line>` proof; an OUTSTANDING row is named so the closer records what is
    still owed and the human who closes the row knows. Returns [] when the issue
    declares no owed row — the close comment then gains nothing.

    Raises (the caller refuses the close, exit 2 — never a silent skip): the thread or
    the rulebook cannot be read, a marker is malformed, or a marker names a section that
    does not exist. A close is a loud act; a broken ledger read must not launder one.
    """
    agents_text = agents_path.read_text(encoding="utf-8")
    text = read_thread(repo, int(number))
    parsed = parse_owed_rows(text)
    if parsed["malformed"]:
        raise RuntimeError(f"#{number} carries malformed owed-row marker(s): "
                           + "; ".join(repr(m) for m in parsed["malformed"]))
    states, _ = row_states(parsed, agents_text.splitlines(), sections(agents_text))
    missing = sorted({s["section"] for s in states if s["missing_section"]})
    if missing:
        raise RuntimeError(f"#{number} declares owed rows in section(s) that do not exist "
                           f"in {agents_path.name}: {', '.join(missing)}")
    notes: list[str] = []
    for st in states:
        if st["line"]:
            notes.append(f"- §{st['section']} **LANDED** at {agents_path.name}:{st['line']}: "
                         f"{st['text'][:300]}")
        else:
            hint = (f" (needle appears at {agents_path.name}:{st['outside']}, outside "
                    f"§{st['section']})" if st["outside"] else "")
            notes.append(f"- §{st['section']} **OUTSTANDING** needle={st['needle']!r}{hint}")
    return notes


def check_ledger(repo: str, agents_path: pathlib.Path, limit: int) -> tuple[list[str], int]:
    """Print the ledger. Returns (lines, problems) — problems > 0 means exit 2."""
    try:
        agents_text = agents_path.read_text(encoding="utf-8")
    except OSError as err:
        return ([f"[owed-rows] cannot read {agents_path}: {err}"], 1)
    secs = sections(agents_text)
    agents_lines = agents_text.splitlines()
    problems = 0
    lines: list[str] = []
    landed = outstanding = unmarked = 0

    for issue in open_issues(repo, limit):
        number, title = issue["number"], issue.get("title") or ""
        labels = {l.get("name") for l in issue.get("labels") or []}
        try:
            text = read_thread(repo, number)
        except (RuntimeError, ValueError) as err:
            lines.append(f"[owed-rows] #{number} UNREADABLE: {err}")
            problems += 1
            continue
        parsed = parse_owed_rows(text)
        states, issues = row_states(parsed, agents_lines, secs)
        for raw in parsed["malformed"]:
            lines.append(f"[owed-rows] #{number} MALFORMED marker: {raw!r}")
        for st in states:
            if st["missing_section"]:
                lines.append(f"[owed-rows] #{number} section={st['section']} "
                             f"NO SUCH SECTION in {agents_path.name} "
                             f"(known: {', '.join(sorted(secs))})")
                continue
            if st["line"]:
                landed += 1
                lines.append(f"[owed-rows] #{number} section={st['section']} "
                             f"needle={st['needle']!r} LANDED {agents_path.name}:{st['line']}")
            else:
                hint = (f" (needle appears at {agents_path.name}:{st['outside']}, outside "
                        f"section {st['section']})" if st["outside"] else "")
                outstanding += 1
                lines.append(f"[owed-rows] #{number} section={st['section']} "
                             f"needle={st['needle']!r} OUTSTANDING{hint}")
        problems += issues
        if not parsed["rows"] and not parsed["malformed"] and (labels & set(QUEUE_LABELS)):
            unmarked += 1
            lines.append(f"[owed-rows] #{number} NO MARKER (queue label "
                         f"{', '.join(sorted(labels & set(QUEUE_LABELS)))}; title: {title})")
    lines.append(f"[owed-rows] {repo}: landed={landed} outstanding={outstanding} "
                 f"no-marker={unmarked} problems={problems}")
    return lines, problems


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--repo", required=True, help="owner/name")
    ap.add_argument("--agents-file", default="AGENTS.md",
                    help="the rulebook to check rows against (default ./AGENTS.md)")
    ap.add_argument("--limit", type=int, default=300, help="how many open issues to read")
    a = ap.parse_args(argv)
    try:
        lines, problems = check_ledger(a.repo, pathlib.Path(a.agents_file), a.limit)
    except (RuntimeError, ValueError) as err:
        print(f"[owed-rows] {err}", file=sys.stderr, flush=True)
        return 2
    for line in lines:
        print(line, flush=True)
    if problems:
        print(f"[owed-rows] FAILED: {problems} unreadable/malformed item(s) — "
              f"the ledger is not trustworthy until they are fixed", file=sys.stderr, flush=True)
        return 2
    print(f"[owed-rows] OK: every owed row carries a parsed {OWED_ROW} declaration "
          "and was checked against the rulebook", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
