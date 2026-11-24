#!/usr/bin/env python3
"""File ONE GitHub issue per finding an implementation run recorded.

Every implementation run must ALSO analyse what it touched and file what it
found — real gaps and technical debt, as their own issues, never folded into the
change it is implementing (AGENTS.md "Analysis ships issues, not code"). The
implementer writes those findings to `findings/<issue>.md` — ONE file per issue,
so two sibling PRs cannot collide on a shared append point (issue #1493); this
script turns each one into a tracked issue.

    make findings-check     # parse the analysis, no network: fail loudly if it is
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
    - **Owed-row:** the row declaration as bot_markers.owed_row_marker renders it
      (optional; a finding that OWES an AGENTS.md row (rule 3c). The declaration
      must parse through scripts/bot_markers.parse_owed_rows — the filed issue
      then carries the registered marker `make owed-rows-check` reads)

    - none                                   (a run that found nothing)

Usage:
    python3 scripts/file_findings.py --check [--issue <n>] [--branch <ref>]
    python3 scripts/file_findings.py --file [--pr 171] [--issue 170]
    python3 scripts/file_findings.py --check --path <file>   # an explicit file wins
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import bot_markers  # noqa: E402  # the ONE owed-row marker definition (rule 6j)
import owed_row_derive  # noqa: E402  # the ONE Done-when derivation (rule 6d, issue #765)
import owed_rows_check  # noqa: E402  # the ONE heading parser the ledger reads (issue #1642)
import pr_closure  # noqa: E402  # the ONE branch/body shape parser (rule 6d, issue #1454)

#: The per-issue analysis seam (issue #1493). The old root `findings.md` was ONE
#: shared append point: every implementation PR appended its own `## <title>`
#: section, so any two open PRs answered `CONFLICT (content): Merge conflict in
#: findings.md` and GitHub's auto-merge refused them both (measured on PR #1488,
#: which needed three rebase rounds to land a test-only change). Each run now owns
#: `findings/<issue>.md`; siblings touch different files and cannot collide.
FINDINGS_DIR = ROOT / "findings"
#: The pre-#1493 root file, kept ONLY as the fallback for a caller with neither an
#: issue nor a branch (a host still on the old skill). It is no longer tracked —
#: the historical sections live in `findings/history.md`.
LEGACY_FINDINGS = ROOT / "findings.md"
LABEL = "tech-debt"
LABEL_DESCRIPTION = "Real gap / technical debt surfaced by an implementation run"

#: GitHub's `issue list` is served from an eventually-consistent index: an issue created
#: seconds earlier can be ABSENT from the list. Measured on this repo (issue #185): a second
#: `make file-findings` ~10 s after the first filed #184 as a duplicate of #182, because the
#: first run exited before the index caught up. A read that may follow a create therefore
#: retries with a pause until the index catches up, so a run that exits green has left an
#: issue the NEXT run can find.
DISCOVER_ATTEMPTS = 5
DISCOVER_DELAY_S = 2.0

_SECTION = re.compile(r"^##\s+(?P<title>.+?)\s*$", re.MULTILINE)
# A FIELD is its marker line AND the lines under it, until the next marker, the next
# `## ` heading, or a blank line (issue #205: the single-line regex filed issue #202
# as "`- **Evidence:** \`.github/workflows/issue-bot.yml\`, the \`pick\` job's" and
# dropped the four lines of reasoning that made the finding worth filing).
_FIELD_START = re.compile(r"^\s*[-*]\s+\*\*(?P<name>[A-Za-z][A-Za-z -]*?):?\*\*\s*:?\s*(?P<first>.*)$")
_FIELD_NAMES = ("Signature", "Evidence", "Why", "Done when", "Owed-row")
_REQUIRED = ("Evidence", "Why", "Done when")


def slug(text: str) -> str:
    """A stable, URL-safe signature for a finding title."""
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:60]


def _agents_text() -> str:
    """The rulebook the derivation checks sections against (issue #765). An
    unreadable AGENTS.md derives NOTHING — a filed issue then reads NO MARKER,
    never a claim derived from an empty rulebook."""
    try:
        return (ROOT / "AGENTS.md").read_text(encoding="utf-8")
    except OSError:
        return ""


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
    ]
    for row in f.get("owed_rows") or []:
        # Re-rendered through the ONE writer (rule 6d/6j): the filed issue carries
        # the registered owed-row declaration, so `make owed-rows-check` reports the
        # owed AGENTS.md row as landed/outstanding without re-reading a thread.
        body.append(f"- **Owed-row:** {bot_markers.owed_row_marker(row['section'], row['needle'])}")
    body += [
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


def _fields(chunk: str) -> dict[str, str]:
    """Every `- **Name:** …` field in a section, with its CONTINUATION lines.

    A field runs from its marker to the next marker / `## ` heading / blank line, so
    the detail a finding was written with survives into the issue body (issue #205).
    Lines are joined with a space; the marker's own line is always the first.
    """
    found: dict[str, str] = {}
    lines = chunk.splitlines()
    i = 0
    while i < len(lines):
        m = _FIELD_START.match(lines[i])
        i += 1
        if not m:
            continue
        name = m.group("name").strip()
        if name not in _FIELD_NAMES or name in found:
            continue
        parts = [m.group("first").strip()]
        while i < len(lines):
            nxt = lines[i]
            if not nxt.strip() or _FIELD_START.match(nxt) or nxt.lstrip().startswith("## "):
                break
            parts.append(nxt.strip())
            i += 1
        found[name] = " ".join(p for p in parts if p).strip()
    return found


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
        f = {"title": title, **{n: "" for n in _FIELD_NAMES}}
        f.update(_fields(chunk))
        missing = [k for k in _REQUIRED if not f[k]]
        if missing:
            return [], f"finding {title!r} is missing {', '.join(missing)}"
        # An Owed-row field (rule 3c: the finding owes an AGENTS.md row) must parse
        # through the registered owed-row grammar — a half-written declaration is a
        # defect, never a silently-skipped line (rule 6d), and it is what
        # `make owed-rows-check` will read on the filed issue.
        f["owed_rows"] = []
        if f["Owed-row"]:
            parsed = bot_markers.parse_owed_rows(f["Owed-row"])
            if parsed["malformed"] or not parsed["rows"]:
                return [], (
                    f"finding {title!r} has an Owed-row field that declares nothing valid: "
                    f"{parsed['malformed'] or 'no owed-row marker found'} — write "
                    f"`{bot_markers.owed_row_marker('<id>', '<needle>')}` "
                    "(scripts/bot_markers.owed_row_marker is the ONE writer)"
                )
            f["owed_rows"] = parsed["rows"]
            # Issue #1642: a DERIVED row is filtered by `derive_rows`' heading check, but an
            # EXPLICIT `- **Owed-row:**` field bypasses it — so a hand-written `section=6r`
            # (a numbered RULE inside §2, not a `## <id>.` heading) reached the ledger as
            # `NO SUCH SECTION` and turned `make owed-rows-check` exit 2 repo-wide (measured
            # on #1581). Validate the declared section through the ONE heading parser the
            # ledger itself reads, never a second copy (rule 6d).
            known = owed_rows_check.sections(_agents_text())
            unknown = sorted({r["section"] for r in f["owed_rows"] if r["section"] not in known})
            if unknown:
                return [], (
                    f"finding {title!r} declares owed-row section(s) {', '.join(unknown)} "
                    f"that are NOT an AGENTS.md `## <id>.` heading "
                    f"(known: {', '.join(sorted(known))}) — `make owed-rows-check` would "
                    "answer `NO SUCH SECTION` and exit 2; name the section the row lives in"
                )
        else:
            # Issue #765: a Done-when that NAMES the owed row ("add the AGENTS.md §8
            # guard row for tests/test_x.py") stamps the registered marker on the
            # filed issue even without an explicit field — derived through
            # scripts/owed_row_derive (the ONE derivation, rule 6d), never invented:
            # only sections that exist as AGENTS.md headings and a needle the text
            # itself names. Nothing derivable -> no marker -> the ledger reports
            # NO MARKER, which is honest.
            f["owed_rows"] = owed_row_derive.derive_rows(
                f["Done when"], _agents_text())
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


def already_filed(signature: str, *, attempts: int = 1,
                  delay: float = DISCOVER_DELAY_S) -> str | None:
    """The URL of the existing issue with this marker, if any (open or closed).

    `attempts > 1` re-reads the list with a pause between tries. The label list is served
    from an eventually-consistent index, so an issue created moments ago can be missing on
    the first read (issue #185); a caller that has just created the issue passes
    `attempts=DISCOVER_ATTEMPTS` and the read waits for the index to catch up.
    """
    marker = f"tech-debt-signature: {signature} -->"
    for attempt in range(max(1, attempts)):
        if attempt:
            time.sleep(delay)
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
        # The create can return before the issue is discoverable in the label list (GitHub's
        # index is eventually consistent, issue #185). Wait for it before reporting success:
        # a run that exits green must have left an issue the NEXT run can find, or the next
        # run files a duplicate.
        if already_filed(f["signature"], attempts=DISCOVER_ATTEMPTS) is None:
            raise SystemExit(
                f"[findings] {url} was created but is NOT discoverable in the `{LABEL}` list "
                f"after {DISCOVER_ATTEMPTS} tries — GitHub's index has not caught up, so a "
                f"re-run would file a duplicate (issue #185); refusing to report success"
            )
        print(f"[findings] filed {url}")
        filed += 1
    return filed


def _shape_inputs(args: argparse.Namespace) -> tuple[str | None, str]:
    """(branch, body) for the shape decision — the event payload wins, as in pr_closure.

    A `pull_request` event carries BOTH the head ref and the body, so it is authoritative;
    an explicit `--branch`/`--body-file` is the local shape (the fix loop has no PR yet).
    A push or dispatch payload has no `pull_request`: `read_event` answers ("", None), so
    the gate has nothing to require and stays a green no-op (issue #1454).
    """
    if args.event:
        body, head = pr_closure.read_event(args.event)
        return (head or args.branch), body
    body = ""
    if args.body_file:
        body = Path(args.body_file).read_text(encoding="utf-8")
    return args.branch, body


def analysis_path(*, path: str | None = None, issue: str | None = None,
                  branch: str | None = None) -> Path:
    """The ONE resolution order for the analysis file (issue #1493).

    An explicit `--path` always wins (the tests and the shape fixtures name their own
    files). Otherwise the file is per issue: `--issue`, then the issue the BRANCH
    encodes (`ci/data-gap-<n>-…`, `ci/<slug>-<n>` — the ONE parser, rule 6d), so the
    shape-aware gate and the fix loop need no extra flag. With neither, the legacy root
    file is the fallback, so an old caller still reads what it wrote.
    """
    if path:
        return Path(path)
    if issue is None and branch:
        derived = pr_closure.implemented_issue(branch)
        issue = str(derived) if derived is not None else None
    if issue is not None:
        return FINDINGS_DIR / f"{int(str(issue).lstrip('#'))}.md"
    return LEGACY_FINDINGS


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="File one issue per implementation finding")
    ap.add_argument("--file", action="store_true", help="file the findings in the analysis file")
    ap.add_argument("--check", action="store_true", help="parse only: fail loudly if the analysis is missing")
    ap.add_argument("--path", default=None,
                    help="an explicit findings file (default: findings/<issue>.md, from --issue or the branch)")
    ap.add_argument("--pr", default=None, help="PR number the findings came from")
    ap.add_argument("--issue", default=None, help="issue number the run implemented")
    # (issue #1454) the SHAPE inputs: with none of them this is byte-identical to the
    # plain `findings-check`, so the bot paths are untouched; with any of them the check
    # first asks `pr_closure.implementation_shaped` whether this PR owes an analysis.
    ap.add_argument("--event", help="webhook payload ($GITHUB_EVENT_PATH): read the PR shape from it")
    ap.add_argument("--branch", help="the head branch, when there is no event payload")
    ap.add_argument("--body-file", help="the PR body on disk, when there is no event payload")
    a = ap.parse_args(argv)

    branch, body = _shape_inputs(a)
    path = analysis_path(path=a.path, issue=a.issue, branch=branch)
    if a.check and (a.event or a.body_file or a.branch):
        if not pr_closure.implementation_shaped(branch, body):
            prefix = pr_closure.non_implementation_prefix(branch)
            if prefix:
                print(f"[findings] SKIP {branch}: exempt shape ({prefix}) — "
                      f"no analysis file required")
            else:
                print(f"[findings] SKIP {branch or '(no branch)'}: no implementation claim "
                      f"in this PR — nothing here owes an analysis")
            return 0
    if not path.is_file():
        print(
            f"[findings] FAIL {path} is missing — every implementation run must analyse "
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
