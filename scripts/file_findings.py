#!/usr/bin/env python3
"""File ONE GitHub issue per finding an implementation run recorded.

Every implementation run must ALSO analyse what it touched and file what it
found — real gaps and technical debt, as their own issues, never folded into the
change it is implementing (AGENTS.md "Analysis ships issues, not code"). The
implementer writes those findings to `findings.md` at the repo root; this script
turns each one into a tracked issue.

    make findings-check     # parse findings.md, no network: fail loudly if it is
                            # missing or a finding lacks evidence / why / done-when
    make file-findings      # file one issue per finding (gh, host-side)

Findings are filed once: each issue body carries an invisible
`<!-- tech-debt-signature: <slug> -->` marker, and a finding whose marker already
exists (open or closed) is skipped — the same dedup rule the data-gap analysis
uses (issue #157). A run that found nothing writes `- none` and files nothing;
that is a valid, green outcome, not a missing analysis — `findings-check` is what
makes "I forgot to analyse" loud instead of silent.

Format (strict enough to parse, loose enough to write):

    # Findings

    ## <short title>
    - **Signature:** <stable-slug>          (optional; defaults to the title slug)
    - **Evidence:** <file:line / command output / data point>
    - **Why:** <what breaks or rots without it>
    - **Done when:** <what the fix looks like>

    - none                                   (a run that found nothing)

Usage:
    python3 scripts/file_findings.py --check
    python3 scripts/file_findings.py --file [--pr 171] [--issue 170]
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FINDINGS = ROOT / "findings.md"
LABEL = "tech-debt"
LABEL_DESCRIPTION = "Real gap / technical debt surfaced by an implementation run"

_SECTION = re.compile(r"^##\s+(?P<title>.+?)\s*$", re.MULTILINE)
_FIELD = {
    "Signature": re.compile(r"^\s*[-*]\s+\*\*Signature:\*\*\s*(?P<v>.+?)\s*$", re.MULTILINE),
    "Evidence": re.compile(r"^\s*[-*]\s+\*\*Evidence:\*\*\s*(?P<v>.+?)\s*$", re.MULTILINE),
    "Why": re.compile(r"^\s*[-*]\s+\*\*Why:\*\*\s*(?P<v>.+?)\s*$", re.MULTILINE),
    "Done when": re.compile(r"^\s*[-*]\s+\*\*Done when:\*\*\s*(?P<v>.+?)\s*$", re.MULTILINE),
}
_REQUIRED = ("Evidence", "Why", "Done when")


def slug(text: str) -> str:
    """A stable, URL-safe signature for a finding title."""
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:60]


def render_finding(f: dict, pr: str | None, issue: str | None) -> str:
    """The issue body for one finding: the four fields + the dedup marker."""
    origin = []
    if issue:
        origin.append(f"Filed while implementing #{issue}.")
    if pr:
        origin.append(f"Surfaced by PR #{pr}.")
    body = [
        "## Finding",
        "",
        f"- **Evidence:** {f['Evidence']}",
        f"- **Why:** {f['Why']}",
        f"- **Done when:** {f['Done when']}",
        "",
        "## Origin",
        "",
        " ".join(origin) or "Surfaced by an implementation run.",
        "",
        "This is its own work item: analysis ships issues, never implementation in",
        "the change that found it (AGENTS.md).",
        "",
        f"<!-- tech-debt-signature: {f['signature']} -->",
        "",
    ]
    return "\n".join(body)


def parse(text: str) -> tuple[list[dict], str | None]:
    """(findings, error). `- none` with no sections is a valid empty result."""
    if not text.strip():
        return [], "findings.md is empty — write `- none` or the findings"
    if re.search(r"^\s*[-*]\s+none\s*$", text, re.MULTILINE | re.IGNORECASE):
        return [], None
    sections = list(_SECTION.finditer(text))
    if not sections:
        return [], "findings.md has no `## <title>` section and no `- none` line"
    findings = []
    for i, m in enumerate(sections):
        end = sections[i + 1].start() if i + 1 < len(sections) else len(text)
        chunk = text[m.end():end]
        title = m.group("title").strip()
        f = {"title": title}
        for name, rx in _FIELD.items():
            hit = rx.search(chunk)
            f[name] = hit.group("v").strip() if hit else ""
        missing = [k for k in _REQUIRED if not f[k]]
        if missing:
            return [], f"finding {title!r} is missing {', '.join(missing)}"
        f["signature"] = slug(f["Signature"]) if f["Signature"] else slug(title)
        findings.append(f)
    return findings, None


def _gh(*args: str, check: bool = True, stdin: str | None = None) -> subprocess.CompletedProcess:
    out = subprocess.run(["gh", *args], input=stdin, text=True, capture_output=True)
    if check and out.returncode != 0:
        raise SystemExit(f"[findings] gh {' '.join(args)} failed: {out.stderr.strip()}")
    return out


def _labels_of(number: str) -> set[str]:
    out = _gh("issue", "view", number, "--json", "labels", check=False)
    try:
        return {str(x.get("name")) for x in json.loads(out.stdout or "{}").get("labels", [])}
    except json.JSONDecodeError:
        return set()


def ensure_label_on(issue: str) -> None:
    """The issue MUST carry LABEL, or fail loudly.

    Measured on this repo (issue #161): `gh issue create --label X` exits 0 while
    applying NO label, and the label is the trigger of the whole downstream chain
    — an unlabelled issue is invisible to every bot. Re-apply it and fail when it
    still is not there, instead of reporting success for an orphan.
    """
    number = issue.rstrip("/").split("/")[-1]
    if LABEL in _labels_of(number):
        return
    _gh("issue", "edit", number, "--add-label", LABEL, check=False)
    if LABEL not in _labels_of(number):
        raise SystemExit(
            f"[findings] {issue} does not carry `{LABEL}` after re-applying it — the bot "
            f"chain triggers on that label, so this filing would be invisible; failing "
            f"instead of reporting it"
        )


def already_filed(signature: str) -> str | None:
    """The URL of the existing issue with this marker, if any (open or closed)."""
    out = _gh(
        "issue", "list", "--state", "all", "--label", LABEL, "--limit", "200",
        "--json", "number,body,url", check=False,
    )
    if out.returncode != 0:
        return None
    try:
        items = json.loads(out.stdout or "[]")
    except json.JSONDecodeError:
        return None
    marker = f"tech-debt-signature: {signature} -->"
    for item in items:
        if marker in (item.get("body") or ""):
            return str(item.get("url") or item.get("number"))
    return None


def ensure_label() -> None:
    """The chain triggers on the label: create it when the repo has none."""
    existing = _gh("label", "list", "--limit", "100", "--json", "name", check=False)
    try:
        names = {str(x.get("name")) for x in json.loads(existing.stdout or "[]")}
    except json.JSONDecodeError:
        names = set()
    if LABEL not in names:
        _gh("label", "create", LABEL, "--description", LABEL_DESCRIPTION)


def file_findings(findings: list[dict], pr: str | None, issue: str | None) -> int:
    """File one issue per finding; returns the number filed."""
    if not findings:
        print("[findings] no findings — nothing filed")
        return 0
    ensure_label()
    filed = 0
    for f in findings:
        existing = already_filed(f["signature"])
        if existing:
            print(f"[findings] {f['signature']} is already filed: {existing} — no duplicate")
            continue
        out = _gh(
            "issue", "create",
            "--title", f"tech-debt: {f['title']}",
            "--body-file", "-",
            "--label", LABEL,
            stdin=render_finding(f, pr, issue),
        )
        url = out.stdout.strip()
        # `--label` can exit 0 having applied nothing (#161): verify, re-apply, or
        # fail loudly — an unlabelled issue is invisible to the bot chain.
        ensure_label_on(url)
        print(f"[findings] filed {url}")
        filed += 1
    return filed


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="File one issue per implementation finding")
    ap.add_argument("--file", action="store_true", help="file the findings in findings.md")
    ap.add_argument("--check", action="store_true", help="parse only: fail loudly if the analysis is missing")
    ap.add_argument("--path", default=str(FINDINGS), help="the findings file (default findings.md)")
    ap.add_argument("--pr", default=None, help="PR number the findings came from")
    ap.add_argument("--issue", default=None, help="issue number the run implemented")
    a = ap.parse_args(argv)

    path = Path(a.path)
    if not path.is_file():
        print(
            f"[findings] FAIL {path.name} is missing — every implementation run must analyse "
            f"what it touched (write `- none` when it found nothing)",
            file=sys.stderr,
        )
        return 1
    findings, error = parse(path.read_text(encoding="utf-8"))
    if error:
        print(f"[findings] FAIL {path.name}: {error}", file=sys.stderr)
        return 1
    for f in findings:
        print(f"[findings] {f['signature']}: {f['title']}")

    if a.check:
        print(f"[findings] OK {path.name}: {len(findings)} finding(s), all well-formed")
        return 0
    if a.file:
        file_findings(findings, a.pr, a.issue)
        return 0
    ap.error("choose --check or --file")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
