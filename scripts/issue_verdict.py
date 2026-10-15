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
_FIELD = {name: re.compile(rf"^{name}:\s*(?P<v>.+?)\s*$", re.MULTILINE)
          for name in ("TRIAGE", "REFINED", "EVIDENCE", "REASON")}


def _gh(*args: str, check: bool = True, stdin: str | None = None) -> subprocess.CompletedProcess:
    out = subprocess.run(["gh", *args], input=stdin, text=True, capture_output=True)
    if check and out.returncode != 0:
        raise SystemExit(f"[verdict] gh {' '.join(args)} failed: {out.stderr.strip()}")
    return out


def parse(text: str) -> dict:
    """The verdict as data. Raises SystemExit(2) on anything unreadable."""
    found = _FIELD["TRIAGE"].search(text)
    kind = found.group("v").strip().lower() if found else ""
    if not kind:
        raise SystemExit("[verdict] REFUSED: triage.md carries no `TRIAGE:` line "
                         f"(expected one of {', '.join(KINDS)})")
    if kind not in KINDS:
        raise SystemExit(f"[verdict] REFUSED: unknown TRIAGE '{kind}' "
                         f"(expected one of {', '.join(KINDS)})")

    def field(name: str) -> str:
        found = _FIELD[name].search(text)
        return found.group("v").strip() if found else ""

    verdict = {"triage": kind, "refined": field("REFINED"), "evidence": field("EVIDENCE"),
               "reason": field("REASON")}
    if kind == "refine" and not verdict["refined"]:
        raise SystemExit("[verdict] REFUSED: `TRIAGE: refine` without a `REFINED:` "
                         "restatement — the comment IS the deliverable")
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
    args = ap.parse_args(argv)

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
