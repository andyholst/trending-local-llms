#!/usr/bin/env python3
"""Apply the implementer's TRIAGE verdict (issue #210).

The comment thread IS part of the specification: an issue whose fifth comment
narrows the request, or which a merged PR has already satisfied, must not be
implemented from its body alone. So the implementer now reads the whole thread
(`issue.md` = body + every comment, with author and timestamp, + a decision
instruction) and writes its verdict to `triage.md`:

    TRIAGE: implement | refine | close
    REFINED: <the restatement>                              (refine only)
    EVIDENCE: <file:line / a command / a measured behaviour> (close only)
    REASON: <why it is obsolete / a duplicate / already fixed> (close only)

This module is DETERMINISTIC — no model — and it is the only thing that acts on
the verdict:

    implement  nothing at all. The run continues to commit, push and open its PR.
    refine     ONE comment carrying the restatement, plus the ``agent:refined``
               label. No PR, no code change.
    close      the REASON with its cited EVIDENCE, the issue closed, plus the
               ``agent:closed`` label.

Refusals, loudly (exit 2): a `close` with no EVIDENCE block, a `refine` with no
restatement, a missing/unknown TRIAGE, unreadable file. "It is done" without
proof is how a real gap gets buried, and a verdict nobody understands must not
be guessed at.

The grammar is answered by a MODEL, so the reader takes the DECORATION a model
puts around it (issue #245): leading markdown, a bold/backticked/spaced key and
colon, a case-different key, emphasis or quotes around the value, and a trailing
reason after the verdict word all still read. That is formatting tolerance, not
guessing — an unknown verdict (`TRIAGE: maybe`), a file with no TRIAGE-shaped
line, and a copied grammar line (`implement | refine | close`) are still refused.

Exit codes: 0 = the verdict was applied (or `implement`, which applies nothing),
2 = refused / misconfigured, so the workflow can tell the two apart.

Env: REPO, ISSUE (or --repo/--issue), TRIAGE_FILE (default triage.md), GH_TOKEN
for the gh calls — the DEFAULT token, because the owner PAT cannot comment on an
issue (measured on #124: `Resource not accessible by personal access token`).
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import subprocess
import sys
from pathlib import Path

TRIAGE_FILE = os.environ.get("TRIAGE_FILE", "triage.md")

# The labels a verdict leaves behind: the sweep skips an issue carrying one (see
# the shared queue rule, `scripts/issue_queue.py`), so a verdict is decided ONCE
# instead of being re-litigated every hour.
LABELS = {"refine": "agent:refined", "close": "agent:closed"}
LABEL_COLORS = {"agent:refined": "fbca04", "agent:closed": "0e8a16"}

KINDS = ("implement", "refine", "close")

# The grammar is answered by a MODEL, so the parser reads the formatting a model
# actually produces instead of only a bare line (issue #245). A near-miss used to
# fail the whole run AFTER the implementation: `**TRIAGE: implement**`, a `##`
# heading, a `- ` bullet, an indented line, a backticked key, `**TRIAGE:**`,
# `TRIAGE : implement`, `triage: implement`, or a trailing reason
# (`TRIAGE: implement — the thread matches the body`) were all "unknown TRIAGE"
# or "no TRIAGE: line". The cost is asymmetric and invisible in the run summary:
# 20 minutes of work thrown away over decoration.
#
# Tolerance is DECORATION, not guessing: the key still has to start a line (after
# leading markdown), the value's FIRST word is the verdict and must be one of
# KINDS, and a line that names an unknown verdict still REFUSES — "TRIAGE: maybe"
# remains unreadable. A verdict buried in prose is not read.
_DECOR = r"(?:[#>*+\-_`~]+\s*|\d+[.)]\s*)*"          # ## , - , > , 1. , ** , `
_EMPH = r"(?:\*+|_+|`+)?"                            # **bold**, *italic*, `code`
_FIELD = {name: re.compile(
    rf"^\s*{_DECOR}{_EMPH}{name}\s*{_EMPH}\s*:\s*{_EMPH}\s*(?P<v>.+?)\s*$",
    re.MULTILINE | re.IGNORECASE)
    for name in ("TRIAGE", "REFINED", "EVIDENCE", "REASON")}
#: The decoration a model puts around a VALUE: emphasis, backticks, quotes, a
#: trailing full stop. Stripped so `**implement**`, `implement.` and `implement`
#: are the same word — while the word itself is still what decides.
_VALUE_DECOR = " \t*_`\"'.,;:"

#: A copied GRAMMAR line is not a decision: `TRIAGE: implement | refine | close`
#: (or `… / …`) names every verdict, so it is skipped instead of read as the first
#: one. A model that pastes the instruction block and answers below it still
#: decides, and a model that pastes ONLY the block is refused (no decision at all).
_CHOICE_LIST = re.compile(r"\b(?:implement|refine|close)\b\s*[|/]\s*\b(?:implement|refine|close)\b",
                          re.IGNORECASE)


def _word(value: str) -> str:
    """The first word of a decorated value: the verdict, or an evidence token."""
    return value.strip(_VALUE_DECOR).split()[0].strip(_VALUE_DECOR) if value.strip() else ""


def _gh(*args: str, check: bool = True, stdin: str | None = None) -> subprocess.CompletedProcess:
    out = subprocess.run(["gh", *args], input=stdin, text=True, capture_output=True)
    if check and out.returncode != 0:
        raise SystemExit(f"[verdict] gh {' '.join(args)} failed: {out.stderr.strip()}")
    return out


#: What a "close" or "refine" EVIDENCE block has to look like (issue #494): the decision is now
#: taken against the CURRENT tree, so the proof must point INTO that tree — a `file:line`, a path
#: with an extension, or a `make <target>` / `python3 scripts/…` command. "It is obsolete" is not
#: evidence: a lazy close buries a real gap, and a lazy refine wastes a round.
_EVIDENCE_SHAPES = (
    re.compile(r"[A-Za-z0-9_./-]+\.[A-Za-z0-9]+:\d+"),            # path/to/file.py:1412
    re.compile(r"\b[\w.-]+/[\w./-]+\.[A-Za-z0-9]{1,6}\b"),         # scripts/update_trending.py
    re.compile(r"\bmake\s+[a-z][\w-]*"),                            # make validate
    re.compile(r"\bpython3?\s+[\w./-]+\.py"),                       # python3 scripts/x.py
    re.compile(r"\bgh\s+(?:api|pr|issue)\b"),                       # a gh read that was run
)


#: `--state` exit codes (issue #520): the caller branches on these, so they are a contract.
STATE_OPEN, STATE_CLOSED, STATE_UNREADABLE = 0, 4, 2


def issue_state(repo: str, number: str) -> str:
    """The issue's state as GitHub reports it: 'OPEN', 'CLOSED', or '' when unreadable.

    Used by the implementer's final step: an issue that got CLOSED while the run was in flight
    (its PR merged) is a finished outcome, not a failed implementation — and a state we cannot
    read is never a guess (issue #520).
    """
    proc = _gh("issue", "view", number, "--repo", repo, "--json", "state", check=False)
    if proc.returncode != 0:
        return ""
    try:
        return str(json.loads(proc.stdout or "{}").get("state") or "").upper()
    except ValueError:
        return ""


def evidence_is_checkable(text: str) -> bool:
    """Does this EVIDENCE block point at something in the tree a reviewer can re-run or re-read?"""
    return any(p.search(text or "") for p in _EVIDENCE_SHAPES)


def parse(text: str) -> dict:
    """The verdict as data. Raises SystemExit(2) on anything unreadable."""
    # Every TRIAGE-shaped line is a candidate; the first one whose FIRST word is a
    # real verdict wins (a decorated `**TRIAGE: implement**` still reads), and a
    # thread where the only TRIAGE line names nothing usable still REFUSES. A line
    # that lists the whole grammar (`implement | refine | close`) is a copy of the
    # instruction, not a decision, so it is not a candidate at all.
    matches = list(_FIELD["TRIAGE"].finditer(text))
    candidates = [_word(m.group("v")).lower() for m in matches
                  if not _CHOICE_LIST.search(m.group("v"))]
    kind = next((c for c in candidates if c in KINDS), "")
    if not kind:
        if not matches:
            raise SystemExit("[verdict] REFUSED: triage.md carries no `TRIAGE:` line "
                             f"(expected one of {', '.join(KINDS)})")
        if not candidates:
            raise SystemExit("[verdict] REFUSED: every `TRIAGE:` line names the whole grammar "
                             f"({' | '.join(KINDS)}) — that is the instruction copied back, "
                             f"not a decision; answer with ONE of {', '.join(KINDS)}")
        raise SystemExit(f"[verdict] REFUSED: unknown TRIAGE '{candidates[0]}' "
                         f"(expected one of {', '.join(KINDS)})")

    def field(name: str) -> str:
        found = _FIELD[name].search(text)
        if not found:
            return ""
        value = found.group("v").strip()
        # A trailing markdown wrapper is decoration, not content: `**implement**`
        # and "`scripts/x.py:12`" keep their word/path without the backticks.
        return value.strip().strip("*").strip()

    verdict = {"triage": kind, "refined": field("REFINED"), "evidence": field("EVIDENCE"),
               "reason": field("REASON")}
    if kind == "refine" and not verdict["refined"]:
        raise SystemExit("[verdict] REFUSED: `TRIAGE: refine` without a `REFINED:` "
                         "restatement — the comment IS the deliverable")
    # A fix/refine verdict is a judgement about the CURRENT tree (issue #494): the proof has to
    # name something in it. An evidence block that is only prose is REFUSED, so the sweep cannot
    # close a live issue — or park one — on the strength of the issue's own words.
    if verdict["evidence"] and not evidence_is_checkable(verdict["evidence"]):
        raise SystemExit("[verdict] REFUSED: `EVIDENCE:` points at nothing in the tree — give a "
                         "`path:line`, a checkable path, or the `make`/`python3`/`gh` command you "
                         "ran. The verdict is judged against the fetched base, so the proof has "
                         "to come from it.")
    if kind == "close":
        if not verdict["evidence"]:
            raise SystemExit("[verdict] REFUSED: `TRIAGE: close` without an "
                             "`EVIDENCE:` block — closing without proof buries a "
                             "real gap; give a file:line, a command or a measurement")
        if not verdict["reason"]:
            raise SystemExit("[verdict] REFUSED: `TRIAGE: close` without a `REASON:`")
    return verdict


def _labels_of(number: str) -> set[str]:
    out = _gh("issue", "view", number, "--json", "labels", check=False)
    try:
        return {str(x.get("name")) for x in json.loads(out.stdout or "{}").get("labels", [])}
    except json.JSONDecodeError:
        return set()


def ensure_label(repo: str, number: str, label: str) -> None:
    """The issue MUST end up carrying LABEL, or this fails loudly.

    Measured on this repo (#161): `gh issue create/edit --add-label` can exit 0
    having applied nothing, and here the label is what the sweep reads to skip a
    decided issue — an unlabelled verdict would be re-implemented within the hour.
    """
    if label in _labels_of(number):
        return
    _gh("label", "create", label, "--repo", repo, "--color", LABEL_COLORS.get(label, "ededed"),
        "--description", "The implementer triaged this issue (scripts/issue_verdict.py, #210)",
        check=False)
    _gh("issue", "edit", number, "--repo", repo, "--add-label", label, check=False)
    if label not in _labels_of(number):
        raise SystemExit(f"[verdict] FAIL: could not apply the {label} label to #{number} "
                         "— the sweep would re-implement a decided issue")


def _stamp(now: dt.datetime) -> str:
    return now.strftime("%Y-%m-%dT%H:%M:%SZ")


def apply_verdict(repo: str, number: str, verdict: dict, now: dt.datetime,
                  dry_run: bool = False) -> int:
    kind = verdict["triage"]
    marker = f"<!-- issue-bot-verdict: {kind} {_stamp(now)} -->"

    if kind == "implement":
        print("verdict=implement")
        print("[verdict] implement: nothing applied — the run continues to commit, "
              "push and open its PR")
        return 0

    if kind == "refine":
        body = "\n".join([
            marker,
            "**The implementer triaged this issue as *needs refinement* — no implementation.**",
            "",
            verdict["refined"],
            "",
            f"The sweep skips an issue carrying `{LABELS['refine']}`: refine the text above",
            "into this issue if it is right, clear the label, and the next sweep takes it.",
        ])
        if not dry_run:
            _gh("issue", "comment", number, "--repo", repo, "--body", body)
            ensure_label(repo, number, LABELS["refine"])
        print("verdict=refine")
        print(f"[verdict] refine: commented on #{number} with the restatement and applied "
              f"{LABELS['refine']} (no PR, no code change)")
        return 0

    body = "\n".join([
        marker,
        "**The implementer triaged this issue as *closed* — with evidence.**",
        "",
        f"**Reason:** {verdict['reason']}",
        "",
        "**Evidence:**",
        "",
        verdict["evidence"],
        "",
        "Reopen with a comment if the evidence does not hold; the sweep skips an issue "
        f"carrying `{LABELS['close']}`.",
    ])
    if not dry_run:
        _gh("issue", "comment", number, "--repo", repo, "--body", body)
        _gh("issue", "close", number, "--repo", repo)
        ensure_label(repo, number, LABELS["close"])
    print("verdict=close")
    print(f"[verdict] close: posted the reason with its evidence, closed #{number} and "
          f"applied {LABELS['close']} (no PR)")
    return 0


def resolve_repo(arg: str | None) -> str:
    if arg:
        return arg
    if os.environ.get("REPO"):
        return os.environ["REPO"]
    out = _gh("repo", "view", "--json", "nameWithOwner", "--jq", ".nameWithOwner")
    return out.stdout.strip()


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Apply the implementer's TRIAGE verdict (#210)")
    ap.add_argument("--repo", default=None)
    ap.add_argument("--issue", default=None)
    ap.add_argument("--file", default=TRIAGE_FILE)
    ap.add_argument("--now", default=None)
    ap.add_argument("--dry-run", action="store_true",
                    help="parse and validate, print what WOULD happen, touch nothing")
    ap.add_argument("--state", action="store_true",
                    help="print the issue's state and exit 0 (open) / 4 (closed) / 2 (unreadable)")
    args = ap.parse_args(argv)

    if args.state:
        # The FINAL check, after the implementation: an issue closed mid-run is a finished
        # outcome (issue #520), and an unreadable state is never a pass.
        number = (args.issue or os.environ.get("ISSUE", "")).strip()
        if not number:
            raise SystemExit("[state] REFUSED: no issue number (--issue or ISSUE=...)")
        repo = resolve_repo(args.repo)
        state = issue_state(repo, number)
        print(f"state={state.lower() or 'unknown'}")
        if state == "OPEN":
            return STATE_OPEN
        if state == "CLOSED":
            return STATE_CLOSED
        print(f"[state] could not read #{number}'s state from {repo} — silence is not evidence",
              file=sys.stderr)
        return STATE_UNREADABLE

    path = Path(args.file)
    if not path.is_file():
        raise SystemExit(f"[verdict] REFUSED: {path} does not exist — the implementer must "
                         "write its verdict there (TRIAGE/REFINED/EVIDENCE/REASON)")
    verdict = parse(path.read_text())
    now = (dt.datetime.strptime(args.now, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=dt.timezone.utc)
           if args.now else dt.datetime.now(dt.timezone.utc))
    number = (args.issue or os.environ.get("ISSUE", "")).strip()
    if not number and not args.dry_run:
        raise SystemExit("[verdict] REFUSED: no issue number (--issue or ISSUE=...)")
    repo = resolve_repo(args.repo) if not args.dry_run else (args.repo or "OWNER/REPO")
    print(f"[verdict] {verdict['triage']} on #{number or '<none>'} ({repo})")
    return apply_verdict(repo, number or "0", verdict, now, dry_run=args.dry_run)


if __name__ == "__main__":
    raise SystemExit(main())
