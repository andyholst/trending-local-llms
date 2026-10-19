#!/usr/bin/env python3
"""Behavioural tests for scripts/file_findings.py (issue #172).

Every implementation run must analyse what it touched and file what it found —
as its OWN issues, never folded into the change. These tests drive the REAL
script: `--check` is loud when the analysis is missing or vague, `--file` opens
exactly one `tech-debt` issue per finding carrying its evidence and its origin,
and a finding that was already filed is never filed twice.

The `gh` CLI is the replaced EXTERNAL system (a stub on PATH that records its
arguments and answers `label list` / `issue list` / `issue view` from control
files); the script itself runs for real.

Wired into `make test` (rule 6d).
"""
from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "scripts" / "file_findings.py"

_PASS = 0
_FAIL = 0

# The gh stub: records every call, answers the reads the script makes, and
# captures the issue body written through `--body-file -` (stdin).
_GH_STUB = """#!/bin/sh
echo "$@" >> "$FAKE_GH_LOG"
case "$1 $2" in
  "label list")   cat "$FAKE_GH_LABELS" ;;
  "issue list")   cat "$FAKE_GH_ISSUES" ;;
  "issue view")   cat "$FAKE_GH_LABELS_ON" ;;
  "issue create") cat > "$FAKE_GH_BODY"; echo "https://github.com/andyholst/trending-local-llms/issues/999" ;;
esac
exit 0
"""

_ONE_FINDING = """# Findings

## The crawler re-scrapes every raw file on every merge

- **Signature:** full-raw-rescan
- **Evidence:** scripts/update_trending.py ingest_raw_snapshots walks RAW_DIR.glob("*.json") on every run
- **Why:** the merge cost grows with history and hides which file actually changed
- **Done when:** ingest reads only the files newer than the store's generated_utc
"""


def check(name, cond, detail=""):
    global _PASS, _FAIL
    if cond:
        _PASS += 1
        print(f"  ok  {name}")
    else:
        _FAIL += 1
        print(f"  FAIL {name}" + (f"  [{detail}]" if detail else ""))


def _module():
    spec = importlib.util.spec_from_file_location("file_findings", SCRIPT)
    assert spec and spec.loader, SCRIPT
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _stub_env(td: Path, *, issues: str = "[]", label_on: str = '{"labels":[{"name":"tech-debt"}]}'):
    """A PATH with the gh stub in front, plus the control files it reads."""
    (td / "bin").mkdir(exist_ok=True)
    gh = td / "bin" / "gh"
    gh.write_text(_GH_STUB, encoding="utf-8")
    gh.chmod(0o755)
    log = td / "calls.log"
    log.write_text("", encoding="utf-8")
    body = td / "created-body.txt"
    (td / "labels.json").write_text(json.dumps([{"name": "tech-debt"}]), encoding="utf-8")
    (td / "issues.json").write_text(issues, encoding="utf-8")
    (td / "label_on.json").write_text(label_on, encoding="utf-8")
    env = {
        **os.environ,
        "PATH": f"{td / 'bin'}{os.pathsep}{os.environ['PATH']}",
        "FAKE_GH_LOG": str(log),
        "FAKE_GH_LABELS": str(td / "labels.json"),
        "FAKE_GH_ISSUES": str(td / "issues.json"),
        "FAKE_GH_LABELS_ON": str(td / "label_on.json"),
        "FAKE_GH_BODY": str(body),
    }
    return env, log, body


_MULTILINE_FINDING = """# Findings

## A filed finding loses everything after its first line

- **Signature:** findings-continuation
- **Evidence:** `scripts/file_findings.py` extracts each section with a
  per-field regex anchored to `^`, so only the marker's own line reaches the
  issue body — the filed #202 carries the headline and stops.
- **Why:** rule 6g makes the issue the durable artifact, so a headline without
  its evidence forces a reviewer to re-derive the defect.
- **Done when:** the extractor captures each section until the next marker or
  `## ` heading, and the body keeps that text.
"""


def test_a_multiline_field_keeps_its_continuation_lines():
    """Issue #205: issue #202 was filed with `- **Evidence:** \\`.github/workflows/
    issue-bot.yml\\`, the \\`pick\\` job's` and nothing else — the four lines under it
    existed only in the gitignored findings.md."""
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        path = td / "findings.md"
        path.write_text(_MULTILINE_FINDING, encoding="utf-8")
        env, log, body = _stub_env(td)

        # Given a finding whose Evidence/Why/Done-when continue on later lines
        proc = subprocess.run([sys.executable, str(SCRIPT), "--file", "--path", str(path)],
                              cwd=ROOT, capture_output=True, text=True, env=env)
        filed = body.read_text(encoding="utf-8") if body.exists() else ""
        calls = log.read_text(encoding="utf-8") if log.exists() else ""

    check("multiline: --file exits 0", proc.returncode == 0, proc.stdout + proc.stderr)
    check("multiline: exactly one issue created", calls.count("issue create") == 1, calls)
    # Then  every continuation line is in the filed body
    for fragment in ("anchored to `^`", "the filed #202 carries the headline and stops",
                     "forces a reviewer to re-derive", "the extractor captures each section"):
        check(f"multiline: the body keeps {fragment!r}", fragment in filed, filed[:400])
    check("multiline: the body is not just the marker's line",
          len(filed.split("\n")) > 12, filed[:400])

    # And   prose inside a continuation that QUOTES another marker is not that field
    mod = _module()
    tricky = ("# Findings\n\n## Tricky\n\n- **Evidence:** first line\n"
              "  continuation that quotes `**Why:**` in its prose\n"
              "- **Why:** the real why\n- **Done when:** done\n")
    got, err = mod.parse(tricky)
    check("multiline: prose quoting another marker is not read as that field",
          bool(got) and got[0]["Why"] == "the real why" and "quotes" in got[0]["Evidence"],
          err or str(got))


def test_missing_findings_file_is_a_loud_failure():
    """A run that wrote no analysis fails the check instead of passing silently."""

    # Given a run that never wrote findings.md
    with tempfile.TemporaryDirectory() as td:
        missing = Path(td) / "findings.md"

        # When  the findings check runs
        proc = subprocess.run([sys.executable, str(SCRIPT), "--check", "--path", str(missing)],
                              cwd=ROOT, capture_output=True, text=True)

    # Then  it exits non-zero and says the run must analyse what it touched
    check("missing file: exit non-zero", proc.returncode != 0, str(proc.returncode))
    check("missing file: the message explains what to do",
          "findings.md" in proc.stderr and "- none" in proc.stderr, proc.stderr)


def test_finding_without_why_is_rejected():
    """A finding with a title but no Why fails, and is named."""

    # Given a finding missing its Why
    text = "# Findings\n\n## Something is off\n\n- **Evidence:** seen it\n- **Done when:** fixed\n"
    with tempfile.TemporaryDirectory() as td:
        path = Path(td) / "findings.md"
        path.write_text(text, encoding="utf-8")

        # When  the check runs
        proc = subprocess.run([sys.executable, str(SCRIPT), "--check", "--path", str(path)],
                              cwd=ROOT, capture_output=True, text=True)

    # Then  it fails and names the section and the missing field
    check("vague finding: exit non-zero", proc.returncode != 0, str(proc.returncode))
    check("vague finding: names the section", "Something is off" in proc.stderr, proc.stderr)
    check("vague finding: names the missing field", "Why" in proc.stderr, proc.stderr)


def test_none_is_a_valid_empty_analysis():
    """`- none` is a valid, green outcome for a run that found nothing."""

    # Given a findings file that says the run found nothing
    with tempfile.TemporaryDirectory() as td:
        path = Path(td) / "findings.md"
        path.write_text("# Findings\n\n- none\n", encoding="utf-8")

        # When  the check runs
        proc = subprocess.run([sys.executable, str(SCRIPT), "--check", "--path", str(path)],
                              cwd=ROOT, capture_output=True, text=True)

    # Then  it is green and reports zero findings
    check("none: exit 0", proc.returncode == 0, proc.stdout + proc.stderr)
    check("none: zero findings reported", "0 finding(s)" in proc.stdout, proc.stdout)


def test_finding_is_filed_once_with_evidence_and_origin():
    """One finding -> exactly one labelled issue carrying evidence + origin."""

    # Given a well-formed finding and a stub gh that has filed nothing yet
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        path = td / "findings.md"
        path.write_text(_ONE_FINDING, encoding="utf-8")
        env, log, body = _stub_env(td)

        # When  the findings are filed for issue #172 and PR #173
        proc = subprocess.run(
            [sys.executable, str(SCRIPT), "--file", "--path", str(path),
             "--issue", "172", "--pr", "173"],
            cwd=ROOT, capture_output=True, text=True, env=env,
        )
        calls = [ln for ln in log.read_text().splitlines() if ln.strip()]
        created = [c for c in calls if c.startswith("issue create")]
        written = body.read_text(encoding="utf-8")

    # Then  exactly one issue is created, labelled tech-debt, with its evidence and origin
    check("filing: exit 0", proc.returncode == 0, proc.stdout + proc.stderr)
    check("filing: exactly one `issue create`", len(created) == 1, str(calls))
    check("filing: created with the tech-debt label",
          bool(created) and "tech-debt" in created[0], str(created))
    check("filing: the title names the finding",
          bool(created) and "full-raw-rescan" not in created[0] and "re-scrapes" in created[0],
          str(created))
    check("filing: the body carries the evidence", "ingest_raw_snapshots" in written, written)
    check("filing: the body carries why + done-when",
          "**Why:**" in written and "**Done when:**" in written, written)
    check("filing: the body links the issue and the PR",
          "#172" in written and "#173" in written, written)
    check("filing: the body carries the dedup signature",
          "tech-debt-signature: full-raw-rescan -->" in written, written)


def test_already_filed_finding_is_skipped():
    """A finding whose signature is already filed opens nothing new."""

    # Given an existing issue that carries the finding's signature marker
    existing = json.dumps([{
        "number": 900,
        "url": "https://github.com/andyholst/trending-local-llms/issues/900",
        "body": "<!-- tech-debt-signature: full-raw-rescan -->",
    }])
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        path = td / "findings.md"
        path.write_text(_ONE_FINDING, encoding="utf-8")
        env, log, _ = _stub_env(td, issues=existing)

        # When  the findings are filed again
        proc = subprocess.run(
            [sys.executable, str(SCRIPT), "--file", "--path", str(path), "--issue", "172"],
            cwd=ROOT, capture_output=True, text=True, env=env,
        )
        calls = [ln for ln in log.read_text().splitlines() if ln.strip()]

    # Then  nothing is created and the existing issue is reported
    check("already filed: exit 0", proc.returncode == 0, proc.stdout + proc.stderr)
    check("already filed: no `issue create` call",
          not any(c.startswith("issue create") for c in calls), str(calls))
    check("already filed: the existing issue is named",
          "issues/900" in proc.stdout, proc.stdout)


def test_parse_helpers_are_the_scripts_own():
    """The parse keeps every field and defaults the signature to the title slug."""

    # Given the real module and two variants of a finding
    mod = _module()
    with_sig = _ONE_FINDING
    without = _ONE_FINDING.replace("- **Signature:** full-raw-rescan\n", "")

    # When  both are parsed
    a, err_a = mod.parse(with_sig)
    b, err_b = mod.parse(without)

    # Then  the explicit signature survives and a missing one falls back to the title
    check("parse: the explicit signature is kept", a and a[0]["signature"] == "full-raw-rescan",
          err_a or str(a))
    check("parse: a missing signature falls back to the title slug",
          b and b[0]["signature"].startswith("the-crawler-re-scrapes"), err_b or str(b))


def test_wired_into_make_test_and_the_bot():
    """The script is reachable from make targets the pipeline runs (rule 6d)."""

    # Given the Makefile, the fix loop and the implementer workflow
    mk = (ROOT / "Makefile").read_text()
    loop = (ROOT / "scripts" / "fix_loop.sh").read_text()
    bot = (ROOT / ".github" / "workflows" / "issue-bot.yml").read_text()

    # When  their wiring is read
    # Then  both targets exist, the loop demands the analysis, and the bot files it
    check("make: file-findings files them",
          "file-findings:" in mk and "python3 scripts/file_findings.py --file" in mk, "")
    check("make: findings-check is the analysis gate",
          "findings-check:" in mk and "python3 scripts/file_findings.py --check" in mk, "")
    check("make: the findings tests run in the suite",
          "python3 tests/test_file_findings.py" in mk, "")
    check("loop: an implementation run demands findings-check (REQUIRE_FINDINGS)",
          "REQUIRE_FINDINGS" in loop and "findings-check" in loop, "")
    check("bot: the findings are filed with the issue and PR context",
          "make file-findings" in bot and "make findings-check" in bot, "")


def main() -> int:
    print("findings -> issues (scripts/file_findings.py)")
    test_a_multiline_field_keeps_its_continuation_lines()
    test_missing_findings_file_is_a_loud_failure()
    test_finding_without_why_is_rejected()
    test_none_is_a_valid_empty_analysis()
    test_finding_is_filed_once_with_evidence_and_origin()
    test_already_filed_finding_is_skipped()
    test_parse_helpers_are_the_scripts_own()
    test_wired_into_make_test_and_the_bot()
    print(f"\nPASSED {_PASS} | FAILED {_FAIL}")
    return 1 if _FAIL else 0


if __name__ == "__main__":
    raise SystemExit(main())
