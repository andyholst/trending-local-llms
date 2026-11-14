#!/usr/bin/env python3
"""Filers stamp the owed-row marker at FILING time (issue #765).

`scripts/bot_markers.py` renders/parses the owed-row marker and
`scripts/owed_rows_check.py` reads the ledger, but until #765 the marker was
written only when findings.md carried an explicit `- **Owed-row:**` field — so
23 open issues named their owed AGENTS.md row only in prose and the ledger
answered `NO MARKER`. These tests drive the REAL filers:

  * `scripts/owed_row_derive.py` derives a declaration ONLY from what the text
    states — a section that exists as an AGENTS.md heading AND a guard-row
    identifier the text names; anything else derives nothing;
  * `scripts/file_findings.py` stamps the derived marker on the issue it files
    (gh stubbed on PATH, the real product runs);
  * `scripts/data_gap_analysis.py` stamps it on the gap issue it composes;
  * a filed, derived marker is then read end-to-end by the REAL
    `scripts/owed_rows_check.py` against the REAL AGENTS.md: it parses and the
    row reports OUTSTANDING with problems=0 — never malformed, never a phantom
    section.

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

from wiring import wired  # noqa: E402  (issues #176/#192)

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import bot_markers  # noqa: E402  (the ONE marker definition — imported, not restated)

FF_SCRIPT = ROOT / "scripts" / "file_findings.py"
LEDGER_SCRIPT = ROOT / "scripts" / "owed_rows_check.py"
REPO = "andyholst/trending-local-llms"

_AGENTS_FIXTURE = """# Fixture rulebook

## 2. Hard rules

## 6b. The pipelines

## 8. Regression guards
| tests/test_refresh_base.py | the refresh base assertion |

## 9. Style
"""

_FF_GH_STUB = """#!/bin/sh
echo "$@" >> "$FAKE_GH_LOG"
case "$1 $2" in
  "label list")   cat "$FAKE_GH_LABELS" ;;
  "issue list")   echo "[]" ;;
  "issue view")   echo '{"labels": [{"name": "tech-debt"}]}' ;;
  "issue create") cat > "$FAKE_GH_BODY"; echo "https://github.com/o/r/issues/999" ;;
esac
exit 0
"""


def _load(name: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _stub_ff_env(tmp_path: Path) -> tuple[dict, Path, Path]:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir(exist_ok=True)
    gh = bin_dir / "gh"
    gh.write_text(_FF_GH_STUB, encoding="utf-8")
    gh.chmod(0o755)
    log = tmp_path / "gh.log"
    log.write_text("", encoding="utf-8")
    body = tmp_path / "body.md"
    env = dict(os.environ,
               PATH=f"{bin_dir}{os.pathsep}{os.environ['PATH']}",
               FAKE_GH_LOG=str(log), FAKE_GH_BODY=str(body),
               FAKE_GH_LABELS=str(tmp_path / "labels"))
    (tmp_path / "labels").write_text("", encoding="utf-8")
    return env, log, body


def _finding(done_when: str) -> str:
    return (
        "# Findings\n\n"
        "## Derivation probe finding\n\n"
        "- **Signature:** derivation-probe\n"
        "- **Evidence:** scripts/owed_row_derive.py derives nothing today\n"
        "- **Why:** filed issues answer NO MARKER in the owed-row ledger\n"
        f"- **Done when:** {done_when}\n"
    )


def test_the_derivation_states_only_what_the_text_names():
    d = _load("owed_row_derive")

    # A Done-when that names a real section AND an identifier -> one declaration
    rows = d.derive_rows(
        "add the AGENTS.md §8 guard row for tests/test_derived_probe.py",
        _AGENTS_FIXTURE)
    assert rows == [{"section": "8", "needle": "tests/test_derived_probe.py",
                     "derived": True}], rows

    # `rule <id>` cross-references count when the id IS a heading
    rows = d.derive_rows("document it in the rulebook (rule 6b) beside make owed-rows-check",
                         _AGENTS_FIXTURE)
    assert rows == [{"section": "6b", "needle": "owed-rows-check", "derived": True}], rows

    # No section stated -> nothing derived (no marker invented)
    assert d.derive_rows("land the fix in scripts/anything.py", _AGENTS_FIXTURE) == []

    # A section that does NOT exist as a heading -> nothing derived: a filer may
    # never stamp a marker the ledger would refuse as NO SUCH SECTION (exit 2).
    assert d.derive_rows("add the §99z guard row for make derived-probe",
                         _AGENTS_FIXTURE) == []

    # A section stated but no guard-row identifier named -> nothing derived.
    assert d.derive_rows("add the AGENTS.md §8 guard row (needle left unspoken)",
                         _AGENTS_FIXTURE) == []


def test_file_findings_stamps_a_derived_row_on_the_filed_issue():
    """A finding with NO explicit Owed-row field but a Done-when that names the
    owed row files an issue carrying the registered marker (gh stubbed; the real
    script runs against the real AGENTS.md, where §8 exists)."""
    text = _finding("add the AGENTS.md §8 guard row for tests/test_foo_derive.py")
    with tempfile.TemporaryDirectory() as td:
        tdp = Path(td)
        path = tdp / "findings.md"
        path.write_text(text, encoding="utf-8")
        env, log, body = _stub_ff_env(tdp)
        proc = subprocess.run([sys.executable, str(FF_SCRIPT), "--file", "--path", str(path)],
                              cwd=ROOT, capture_output=True, text=True, env=env)
        filed = body.read_text(encoding="utf-8") if body.exists() else ""
        calls = log.read_text(encoding="utf-8") if log.exists() else ""
    assert proc.returncode == 0 and calls.count("issue create") == 1, proc.stdout + proc.stderr
    assert "<!-- owed-row: section=8 needle=tests/test_foo_derive.py -->" in filed, filed[:800]
    parsed = bot_markers.parse_owed_rows(filed)
    assert parsed["rows"] == [{"section": "8", "needle": "tests/test_foo_derive.py"}] \
        and not parsed["malformed"], parsed
    # The explicit-field path is unchanged: no second marker appears.
    assert filed.count("owed-row:") == 1, filed[:800]


def test_file_findings_stamps_nothing_when_the_done_when_names_nothing():
    text = _finding("merge the fix and keep the suite green")
    with tempfile.TemporaryDirectory() as td:
        tdp = Path(td)
        path = tdp / "findings.md"
        path.write_text(text, encoding="utf-8")
        env, log, body = _stub_ff_env(tdp)
        proc = subprocess.run([sys.executable, str(FF_SCRIPT), "--file", "--path", str(path)],
                              cwd=ROOT, capture_output=True, text=True, env=env)
        filed = body.read_text(encoding="utf-8") if body.exists() else ""
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "owed-row:" not in filed, filed[:800]


def test_the_data_gap_filer_stamps_its_own_body():
    """`issue_body()` derives from the body it composes: a contract-gap sentence
    naming a real section and a make target lands a parseable marker, and an
    ordinary body lands none."""
    g = _load("data_gap_analysis")
    report = {
        "as_of": "2026-11-14T00:00:00Z",
        "baseline_as_of": "2026-11-13T00:00:00Z",
        "models": 1,
        "dimensions": {"context_tokens": {"label": "context_tokens", "why": "probe"}},
        "missing": {"context_tokens": ["model-a"]},
        "unstructured": {"context_tokens": []},
        "not_captured": {"context_tokens": ["model-a"]},
        "captured_prose": {"context_tokens": []},
        "not_applicable": {"context_tokens": []},
        "untraceable": {"context_tokens": []},
        "maintenance": {"stale": {}, "thin_measurements": {}, "estimated": {},
                        "empty_raw_legs": [], "starved_legs": []},
        "findings": [],
        "informational": [],
        "contract_gaps": {
            "model": "the contract prunes context_tokens; the fix owes the "
                     "AGENTS.md §8 guard row beside make owed-rows-check",
        },
        "signature": ["probe-sig"],
    }
    body, _title = g.issue_body(report, None)
    parsed = bot_markers.parse_owed_rows(body)
    assert parsed["rows"] == [{"section": "8", "needle": "owed-rows-check"}], parsed
    assert not parsed["malformed"], parsed
    assert "## Owed rulebook rows" in body, body[:600]

    plain = dict(report, contract_gaps={})
    body2, _ = g.issue_body(plain, None)
    assert "owed-row:" not in body2, body2[:600]


def test_a_filed_derived_marker_reads_in_the_real_ledger():
    """End-to-end (rule 6m): the marker a filer stamps is read by the REAL
    owed_rows_check against the REAL AGENTS.md — it parses, the row reports
    OUTSTANDING (the needle is not in §8 yet), and the run reports no problems."""
    marker = bot_markers.owed_row_marker("8", "tests/test_foo_derive.py")
    fixtures = {
        "issues": [{"number": 765, "title": "owed-row markers are never stamped at creation",
                    "labels": [{"name": "tech-debt"}],
                    "createdAt": "2026-11-13T00:00:00Z"}],
        "issue:765": {"number": 765,
                      "body": "## Finding\n\nThe filers stamp at filing.\n\n" + marker},
        "comments:765": [],
    }
    with tempfile.TemporaryDirectory() as td:
        tdp = Path(td)
        fixture_file = tdp / "fixtures.json"
        fixture_file.write_text(json.dumps(fixtures), encoding="utf-8")
        bin_dir = tdp / "bin"
        bin_dir.mkdir()
        stub = bin_dir / "gh"
        stub.write_text(
            "#!/usr/bin/env python3\n"
            "import json, os, sys\n"
            "fx = json.load(open(os.environ['OWED_ROWS_FIXTURES']))\n"
            "args = sys.argv[1:]\n"
            "if args[:2] == ['issue', 'list']:\n"
            "    print(json.dumps(fx['issues']))\n"
            "elif args[:1] == ['api']:\n"
            "    path = args[1]\n"
            "    num = path.split('/issues/')[1].split('/')[0]\n"
            "    key = 'comments' if path.endswith('/comments') else 'issue'\n"
            "    value = fx[f'{key}:{num}']\n"
            "    if key == 'comments':\n"
            "        for c in value:\n"
            "            print(json.dumps(c))\n"
            "    else:\n"
            "        print(json.dumps(value))\n"
            "else:\n"
            "    sys.exit(2)\n",
            encoding="utf-8")
        stub.chmod(0o755)
        env = dict(os.environ, PATH=f"{bin_dir}{os.pathsep}{os.environ['PATH']}",
                   OWED_ROWS_FIXTURES=str(fixture_file))
        proc = subprocess.run(
            [sys.executable, str(LEDGER_SCRIPT), "--repo", REPO,
             "--agents-file", str(ROOT / "AGENTS.md")],
            capture_output=True, text=True, env=env, cwd=tdp)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "section=8 needle='tests/test_foo_derive.py' OUTSTANDING" in proc.stdout, proc.stdout
    assert "problems=0" in proc.stdout, proc.stdout


def test_wired_into_make_test():
    assert wired(__file__), "runner/Makefile wiring"


def main() -> int:
    tests = [
        test_the_derivation_states_only_what_the_text_names,
        test_file_findings_stamps_a_derived_row_on_the_filed_issue,
        test_file_findings_stamps_nothing_when_the_done_when_names_nothing,
        test_the_data_gap_filer_stamps_its_own_body,
        test_a_filed_derived_marker_reads_in_the_real_ledger,
        test_wired_into_make_test,
    ]
    failed = 0
    for t in tests:
        try:
            t()
            print(f"PASS {t.__name__}")
        except AssertionError as exc:
            failed += 1
            print(f"FAIL {t.__name__}: {exc}")
    print(f"\nPASSED {len(tests) - failed} | FAILED {failed}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
