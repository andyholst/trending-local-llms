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
import re
import subprocess
import sys
import tempfile
from pathlib import Path

from wiring import wired  # noqa: E402  (issues #176/#192)

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "scripts" / "file_findings.py"

_PASS = 0
_FAIL = 0

# The gh stub: records every call, answers the reads the script makes, and captures the
# issue body written through `--body-file -` (stdin). It is PYTHON because it models
# GitHub's eventually-consistent issue list (issue #185): an issue created by `issue create`
# is PENDING and becomes visible to `issue list` only once it is older than FAKE_GH_LAG
# seconds. The default lag is 0 — visible immediately, the already-indexed case.
_GH_STUB = '''#!/usr/bin/env python3
import json
import os
import sys
import time

args = sys.argv[1:]
with open(os.environ["FAKE_GH_LOG"], "a", encoding="utf-8") as fh:
    fh.write(" ".join(args) + "\\n")


def read(path, default):
    return open(path, encoding="utf-8").read() if os.path.exists(path) else default


def publish_if_due():
    pending = os.environ["FAKE_GH_PENDING"]
    stamp = os.environ["FAKE_GH_PENDING_TS"]
    visible = os.environ["FAKE_GH_VISIBLE"]
    if not (os.path.exists(pending) and os.path.exists(stamp)):
        return
    age = time.time() - float(read(stamp, "0") or 0)
    if age < float(os.environ.get("FAKE_GH_LAG", "0") or 0):
        return
    items = json.loads(read(visible, "[]") or "[]")
    items.append({
        "number": 999,
        "url": "https://github.com/andyholst/trending-local-llms/issues/999",
        "body": read(pending, ""),
    })
    with open(visible, "w", encoding="utf-8") as fh:
        json.dump(items, fh)
    os.remove(pending)
    os.remove(stamp)


if args[:2] == ["issue", "list"]:
    publish_if_due()
    sys.stdout.write(read(os.environ["FAKE_GH_VISIBLE"], "[]"))
elif args[:2] == ["issue", "create"]:
    body_text = sys.stdin.read()
    with open(os.environ["FAKE_GH_BODY"], "w", encoding="utf-8") as fh:
        fh.write(body_text)
    with open(os.environ["FAKE_GH_PENDING"], "w", encoding="utf-8") as fh:
        fh.write(body_text)
    with open(os.environ["FAKE_GH_PENDING_TS"], "w", encoding="utf-8") as fh:
        fh.write(str(time.time()))
    sys.stdout.write("https://github.com/andyholst/trending-local-llms/issues/999\\n")
elif args[:2] == ["label", "list"]:
    sys.stdout.write(read(os.environ["FAKE_GH_LABELS"], "[]"))
elif args[:2] == ["issue", "view"]:
    sys.stdout.write(read(os.environ["FAKE_GH_LABELS_ON"], "{}"))
'''

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


def _stub_env(td: Path, *, issues: str = "[]", label_on: str = '{"labels":[{"name":"tech-debt"}]}',
              lag: float = 0.0):
    """A PATH with the gh stub in front, plus the control files it reads.

    `lag` is how many seconds a created issue stays invisible to `issue list` — the
    eventually-consistent index of issue #185 (0 = visible immediately).
    """
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
        "FAKE_GH_VISIBLE": str(td / "issues.json"),
        "FAKE_GH_LABELS_ON": str(td / "label_on.json"),
        "FAKE_GH_BODY": str(body),
        "FAKE_GH_PENDING": str(td / "pending.json"),
        "FAKE_GH_PENDING_TS": str(td / "pending-ts.txt"),
        "FAKE_GH_LAG": str(lag),
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


def test_a_mixed_finding_and_none_file_is_refused():
    """Issue #1662: a section AND a `- none` line is self-contradicting and is refused.

    The old order short-circuited on `- none` first, so this exact shape read as
    `([], None)` — "found nothing" — and the recorded finding was silently dropped.
    """

    # Given a complete finding followed by a stray template `- none` line
    text = ("# Findings\n\n## A real gap\n\n- **Evidence:** measured it\n"
            "- **Why:** it rots\n- **Done when:** fixed\n\n- none\n")
    mod = _module()
    with tempfile.TemporaryDirectory() as td:
        path = Path(td) / "findings.md"
        path.write_text(text, encoding="utf-8")

        # When  the REAL check runs
        proc = subprocess.run([sys.executable, str(SCRIPT), "--check", "--path", str(path)],
                              cwd=ROOT, capture_output=True, text=True)

    # Then  the parser refuses the MIXED shape instead of reading it as empty
    got, err = mod.parse(text)
    check("mixed: parse() returns no findings", got == [], str(got))
    check("mixed: parse() names BOTH conflicting shapes",
          bool(err) and "## <title>" in err and "`- none`" in err and "silently dropped" in err,
          err or "<no error>")
    # And   --check exits non-zero and names the file
    check("mixed: --check exits non-zero", proc.returncode != 0, str(proc.returncode))
    check("mixed: --check names the file", "findings.md" in proc.stderr, proc.stderr)


def test_a_sections_only_file_still_parses():
    """A sections-only file is byte-identical to the old behaviour (issue #1662)."""

    # Given one complete finding and NO `- none` line
    text = ("# Findings\n\n## Only a finding\n\n- **Evidence:** seen it\n"
            "- **Why:** it matters\n- **Done when:** fixed\n")
    with tempfile.TemporaryDirectory() as td:
        path = Path(td) / "findings.md"
        path.write_text(text, encoding="utf-8")

        # When  the REAL check runs
        proc = subprocess.run([sys.executable, str(SCRIPT), "--check", "--path", str(path)],
                              cwd=ROOT, capture_output=True, text=True)

    # Then  it is green and reports exactly one finding
    check("sections-only: exit 0", proc.returncode == 0, proc.stdout + proc.stderr)
    check("sections-only: one finding reported", "1 finding(s)" in proc.stdout, proc.stdout)


def test_the_shipped_findings_files_are_not_mixed():
    """Issue #1662: the two shipped mixed files now report their real findings.

    `findings/1586.md` (three) and `findings/1612.md` (one) carried a stray
    `- none` line beside their sections; after the change each parses its own
    findings instead of answering `0 finding(s)`.
    """

    mod = _module()
    for name, expected in (("1586.md", 3), ("1612.md", 1)):
        path = ROOT / "findings" / name
        if not path.is_file():
            check(f"shipped {name}: present", False, str(path))
            continue
        text = path.read_text(encoding="utf-8")
        got, err = mod.parse(text)
        check(f"shipped {name}: parses its {expected} finding(s)",
              err is None and len(got) == expected, err or f"got {len(got)}")


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


def test_two_immediate_invocations_file_exactly_one_issue():
    """Issue #185: a second `make file-findings` ~10 s after the first filed #184 as a
    duplicate of #182 — the first run exited before GitHub's list index caught up with its
    own create.

    Given a gh whose `issue list` lags a create by LAG seconds, when the tool runs TWICE in
    immediate succession, then exactly ONE issue is created: the first run waits for its
    issue to become discoverable before exiting, so the second run's pre-check finds it.
    """

    # Given the lagging stub and one finding
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        path = td / "findings.md"
        path.write_text(_ONE_FINDING, encoding="utf-8")
        env, log, _ = _stub_env(td, lag=1.0)

        # When  the findings are filed twice in immediate succession
        proc = None
        for _ in range(2):
            proc = subprocess.run(
                [sys.executable, str(SCRIPT), "--file", "--path", str(path), "--issue", "185"],
                cwd=ROOT, capture_output=True, text=True, env=env,
            )
        calls = [ln for ln in log.read_text().splitlines() if ln.strip()]
        created = [c for c in calls if c.startswith("issue create")]
        lists = [c for c in calls if c.startswith("issue list")]

    # Then  both runs are green and exactly one issue exists
    check("dedup: the second invocation exits 0", proc.returncode == 0, proc.stdout + proc.stderr)
    check("dedup: exactly one `issue create` across two invocations",
          len(created) == 1, str(calls))
    check("dedup: the first run re-read the list until its issue was discoverable",
          len(lists) >= 3, str(calls))


def test_a_create_that_never_becomes_discoverable_fails_loudly():
    """Issue #185: the discoverability wait must not report a false success — a create that
    never appears in the label list is a loud failure, not a green run."""

    # Given a gh whose index never catches up inside the window
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        path = td / "findings.md"
        path.write_text(_ONE_FINDING, encoding="utf-8")
        env, log, _ = _stub_env(td, lag=3600.0)

        # When  the findings are filed
        proc = subprocess.run(
            [sys.executable, str(SCRIPT), "--file", "--path", str(path), "--issue", "185"],
            cwd=ROOT, capture_output=True, text=True, env=env,
        )
        calls = [ln for ln in log.read_text().splitlines() if ln.strip()]

    # Then  the run refuses to report success and names the duplicate risk
    check("loud: the run exits non-zero", proc.returncode != 0, str(proc.returncode))
    check("loud: the failure names the duplicate risk",
          "NOT discoverable" in proc.stderr and "duplicate" in proc.stderr, proc.stderr)
    check("loud: the issue was still created exactly once",
          len([c for c in calls if c.startswith("issue create")]) == 1, str(calls))


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


_OWED_ROW_FINDING = """# Findings

## The §8 guard row for the new check is owed to a protected AGENTS.md

- **Signature:** owed-row-protected-rulebook
- **Evidence:** a new guard check ships under `make lint`, rule 6c owes the `AGENTS.md` §8 row,
  and the headless implement leg is REFUSED the write (protected agent-instruction file,
  measured on #654–657: the change died on the bare `- [ ]` the refusal left behind)
- **Why:** an undeclared owed row vanishes — the PR goes red on the unticked box, or the rulebook
  silently describes the pre-guard behaviour (rule 3c starvation)
- **Done when:** an attended run lands the row from the ledger issue
- **Owed-row:** <!-- owed-row: section=8 needle="owed rulebook row" -->
"""


def test_an_owed_row_finding_files_the_registered_marker():
    """Issue #659: a finding that owes an AGENTS.md row carries it into the ledger.

    Given a finding with a valid `- **Owed-row:**` declaration, --check parses it and
    --file's issue body carries the marker RE-RENDERED through
    scripts/bot_markers.owed_row_marker (the ONE writer, rule 6j) — the exact
    declaration `make owed-rows-check` reads — beside the dedup signature."""

    # Given the owed-row finding
    mod = _module()
    got, err = mod.parse(_OWED_ROW_FINDING)
    check("owed-row: --check parses the finding", bool(got) and err is None, err or "")
    check("owed-row: the declaration parses through bot_markers' grammar",
          got and got[0]["owed_rows"] == [{"section": "8", "needle": "owed rulebook row"}],
          str(got[0]) if got else "")

    # When  it is filed through the real script (gh stubbed on PATH)
    with tempfile.TemporaryDirectory() as td:
        tdp = Path(td)
        path = tdp / "findings.md"
        path.write_text(_OWED_ROW_FINDING, encoding="utf-8")
        env, log, body = _stub_env(tdp)
        proc = subprocess.run([sys.executable, str(SCRIPT), "--file", "--path", str(path)],
                              cwd=ROOT, capture_output=True, text=True, env=env)
        filed = body.read_text(encoding="utf-8") if body.exists() else ""
        calls = log.read_text(encoding="utf-8") if log.exists() else ""

    # Then  exactly one issue, carrying BOTH markers in the registered shape
    check("owed-row: one issue filed", proc.returncode == 0 and calls.count("issue create") == 1,
          proc.stdout + proc.stderr)
    check("owed-row: the filed body carries the registered owed-row marker",
          '<!-- owed-row: section=8 needle="owed rulebook row" -->' in filed, filed[:600])
    check("owed-row: the filed body keeps the dedup signature",
          "tech-debt-signature: owed-row-protected-rulebook" in filed, filed[:600])


def test_an_owed_row_field_that_declares_nothing_fails_loudly():
    """Issue #659: a half-written Owed-row field is a defect, never a silent field."""

    # Given  a findings file whose Owed-row field carries NO registered declaration
    prose = _OWED_ROW_FINDING.replace(
        '- **Owed-row:** <!-- owed-row: section=8 needle="owed rulebook row" -->',
        "- **Owed-row:** section 8, needle owed rulebook row (plain prose, no marker)")
    # And    one whose marker is malformed (no needle=)
    malformed = _OWED_ROW_FINDING.replace(
        'section=8 needle="owed rulebook row"', 'section=8')

    for name, text in (("no-marker prose", prose), ("malformed marker", malformed)):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "findings.md"
            path.write_text(text, encoding="utf-8")
            proc = subprocess.run([sys.executable, str(SCRIPT), "--check", "--path", str(path)],
                                  cwd=ROOT, capture_output=True, text=True)
        check(f"owed-row {name}: exit non-zero", proc.returncode != 0, str(proc.returncode))
        check(f"owed-row {name}: names the finding and the grammar",
              "§8 guard row" in proc.stderr and "owed-row:" in proc.stderr, proc.stderr)
    # And    a findings file with NO Owed-row field at all is still valid (optional field)
    mod = _module()
    got, err = mod.parse(_ONE_FINDING)
    check("owed-row: findings without the field still parse (optional)",
          bool(got) and err is None and got[0]["owed_rows"] == [], err or "")


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
          wired(__file__), "")
    check("loop: an implementation run demands findings-check (REQUIRE_FINDINGS)",
          "REQUIRE_FINDINGS" in loop and "findings-check" in loop, "")
    check("bot: the findings are filed with the issue and PR context",
          "make file-findings" in bot and "make findings-check" in bot, "")


# --------------------------------------------------------------------------------------
# Issue #1454: the gate is SHAPE-AWARE, and wired where CI decides
# --------------------------------------------------------------------------------------

_EXEMPT_SHAPES = (
    "ci/trending-refresh-20261114-1138",
    "ci/free-model-refresh-20261120-1",
    "ci/keeper-index-20261122t145402z",
    "ci/openspec-index-repair-20261123T091623Z",
    "ci/architecture-block-repair-20261123T091623Z",
    "ci/openspec-invalid-change-repair-20261123T091623Z",
    "ci/pipeline-failure-ledger-20261123T205600Z",
    "docs/contract-prose-sync-1394",
    "rule/reviewer-skill-notes-1432",
)


def _check_cli(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(SCRIPT), "--check", *args],
                          cwd=ROOT, capture_output=True, text=True)


def test_an_implementation_shaped_head_without_findings_goes_red():
    """The RED-first scenario: rule 6g's analysis is MANDATORY on an implementation PR.

    Given an implementation-shaped head with no findings.md, when the shape-aware check
    runs, then it exits non-zero naming the file — the old wiring never ran here at all.
    """

    with tempfile.TemporaryDirectory() as td:
        missing = Path(td) / "findings.md"
        proc = _check_cli("--path", str(missing), "--branch", "ci/data-gap-12-x")

    check("red: exit non-zero", proc.returncode != 0, str(proc.returncode))
    check("red: names findings.md", "findings.md" in proc.stderr, proc.stderr)
    check("red: it does not print a SKIP line", "SKIP" not in proc.stdout, proc.stdout)


def test_exempt_shapes_are_skipped():
    """A bare wiring would red EVERY keeper/refresh/docs PR; the declared exemption
    keeps each of them green and names the prefix it matched."""

    with tempfile.TemporaryDirectory() as td:
        missing = Path(td) / "findings.md"
        for branch in _EXEMPT_SHAPES:
            proc = _check_cli("--path", str(missing), "--branch", branch)
            check(f"exempt: {branch} exits 0", proc.returncode == 0, proc.stdout + proc.stderr)
            check(f"exempt: {branch} names its prefix",
                  "SKIP" in proc.stdout and "exempt shape" in proc.stdout, proc.stdout)


def test_a_push_event_is_a_green_noop():
    """A push to master / a dispatch carries no `pull_request`: nothing to require."""

    with tempfile.TemporaryDirectory() as td:
        missing = Path(td) / "findings.md"
        event = Path(td) / "push.json"
        event.write_text(json.dumps({"ref": "refs/heads/master", "commits": []}), encoding="utf-8")
        proc = _check_cli("--path", str(missing), "--event", str(event))

    check("push: exit 0", proc.returncode == 0, proc.stdout + proc.stderr)
    check("push: it says SKIP, never FAIL", "SKIP" in proc.stdout and "FAIL" not in proc.stderr,
          proc.stdout + proc.stderr)


def test_a_closing_claim_alone_makes_it_implementation():
    """A shapeless branch whose body claims an issue IS an implementation."""

    with tempfile.TemporaryDirectory() as td:
        missing = Path(td) / "findings.md"
        body = Path(td) / "body.md"
        body.write_text("Implements the seam.\n\nCloses #12\n", encoding="utf-8")
        proc = _check_cli("--path", str(missing), "--branch", "shapeless-branch",
                          "--body-file", str(body))

    check("claim: exit non-zero", proc.returncode != 0, proc.stdout + proc.stderr)
    check("claim: names findings.md", "findings.md" in proc.stderr, proc.stderr)


def test_a_quoted_claim_is_not_a_claim():
    """`visible_text` strips code FIRST, so a quoted example is prose, not a claim."""

    with tempfile.TemporaryDirectory() as td:
        missing = Path(td) / "findings.md"
        body = Path(td) / "body.md"
        body.write_text("The rule is `Closes #12`, quoted from the docs.\n", encoding="utf-8")
        proc = _check_cli("--path", str(missing), "--branch", "shapeless-branch",
                          "--body-file", str(body))

    check("quoted: exit 0", proc.returncode == 0, proc.stdout + proc.stderr)
    check("quoted: it reports SKIP", "SKIP" in proc.stdout, proc.stdout)


def test_the_shape_gate_is_wired_to_ci_and_the_fix_loop():
    """Rule 6d/6m: the target exists, CI runs it, the fix loop lists it, the description
    documents it — otherwise the gate is green because nothing executes it."""

    mk = (ROOT / "Makefile").read_text(encoding="utf-8")
    qa = (ROOT / ".github" / "workflows" / "qa-validate.yml").read_text(encoding="utf-8")
    loop = (ROOT / "scripts" / "fix_loop.sh").read_text(encoding="utf-8")
    arch = (ROOT / "ARCHITECTURE.md").read_text(encoding="utf-8")

    check("wiring: the Makefile defines findings-check-for-pr",
          "\nfindings-check-for-pr:" in mk, "")
    block = re.search(r"^findings-check-for-pr:.*\n(?:\t.*\n)+", mk, re.M)
    check("wiring: the target is HOST-SIDE (it reads the runner's $GITHUB_EVENT_PATH)",
          block is not None and "$(PYTHON_RUN)" not in block.group(0),
          "the container does not mount the event payload (measured: PR #1480 run 45288434759)")
    check("wiring: qa-validate's validate job calls it", "make findings-check-for-pr" in qa, "")
    check("wiring: the fix loop carries it", "findings-check-for-pr" in loop, "")
    check("wiring: ARCHITECTURE.md documents the target", "findings-check-for-pr" in arch, "")
    check("wiring: the plain findings-check is unchanged",
          "\nfindings-check:" in mk and "python3 scripts/file_findings.py --check" in mk, "")
    check("wiring: this suite is in the `_test` chain", wired(__file__), "")


def main() -> int:
    print("findings -> issues (scripts/file_findings.py)")
    test_a_multiline_field_keeps_its_continuation_lines()
    test_missing_findings_file_is_a_loud_failure()
    test_finding_without_why_is_rejected()
    test_none_is_a_valid_empty_analysis()
    test_a_mixed_finding_and_none_file_is_refused()
    test_a_sections_only_file_still_parses()
    test_the_shipped_findings_files_are_not_mixed()
    test_finding_is_filed_once_with_evidence_and_origin()
    test_already_filed_finding_is_skipped()
    test_two_immediate_invocations_file_exactly_one_issue()
    test_a_create_that_never_becomes_discoverable_fails_loudly()
    test_parse_helpers_are_the_scripts_own()
    test_an_owed_row_finding_files_the_registered_marker()
    test_an_owed_row_field_that_declares_nothing_fails_loudly()
    test_wired_into_make_test_and_the_bot()
    test_an_implementation_shaped_head_without_findings_goes_red()
    test_exempt_shapes_are_skipped()
    test_a_push_event_is_a_green_noop()
    test_a_closing_claim_alone_makes_it_implementation()
    test_a_quoted_claim_is_not_a_claim()
    test_the_shape_gate_is_wired_to_ci_and_the_fix_loop()
    print(f"\nPASSED {_PASS} | FAILED {_FAIL}")
    return 1 if _FAIL else 0


if __name__ == "__main__":
    raise SystemExit(main())
