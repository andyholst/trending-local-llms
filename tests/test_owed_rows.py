"""The owed-row ledger check (issue #523).

The REAL `scripts/owed_rows_check.py` runs in every test; only GitHub is stood in for — a stub
`gh` on PATH serving recorded JSON fixtures (AGENTS.md rule 6m: an external system may be
recorded, the product itself is never patched). The rulebook is a fixture file passed via
`--agents-file`, so the tests never depend on the live AGENTS.md text.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "owed_rows_check.py"

sys.path.insert(0, str(ROOT / "scripts"))
import bot_markers  # noqa: E402  (the product's own marker definition — imported, not patched)

REPO = "octo/repo"

# A rulebook fixture: §8 has the landed needle; §6b exists but carries nothing; the misplaced
# needle is in §3, not §6b.
AGENTS_FIXTURE = """# Rulebook

## 3. Something else

- `make make-tea`

## 6b. The pipelines

- refresh-bot.yml runs searches.

## 8. Regression guards

| test | catches |
| tests/test_refresh_base.py | the refresh base assertion |

## 9. Style
"""


def _stub_gh(tmp_path: Path, fixtures: dict) -> Path:
    """A `gh` stand-in on PATH: it maps the exact calls the product makes to recorded JSON."""
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir(exist_ok=True)
    fixture_file = tmp_path / "fixtures.json"
    fixture_file.write_text(json.dumps(fixtures), encoding="utf-8")
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
        "    value = fx.get(f'{key}:{num}')\n"
        "    if value is None:\n"
        "        sys.stderr.write(f'no fixture for {path}\\n'); sys.exit(1)\n"
        "    if key == 'comments':\n"
        "        # mimic `gh api --paginate --jq .[]`: one JSON object per line\n"
        "        for c in value:\n"
        "            print(json.dumps(c))\n"
        "    else:\n"
        "        print(json.dumps(value))\n"
        "else:\n"
        "    sys.stderr.write('unexpected gh call: ' + ' '.join(args)); sys.exit(2)\n",
        encoding="utf-8",
    )
    stub.chmod(0o755)
    return bin_dir


def _run(tmp_path: Path, fixtures: dict, agents_text: str = AGENTS_FIXTURE):
    bin_dir = _stub_gh(tmp_path, fixtures)
    agents = tmp_path / "AGENTS.md"
    agents.write_text(agents_text, encoding="utf-8")
    env = dict(os.environ,
               PATH=f"{bin_dir}{os.pathsep}{os.environ['PATH']}",
               OWED_ROWS_FIXTURES=str(tmp_path / "fixtures.json"))
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), "--repo", REPO, "--agents-file", str(agents)],
        capture_output=True, text=True, env=env, cwd=tmp_path)
    return proc


def _fixtures(marker_text: str, labels=("tech-debt",)) -> dict:
    return {
        "issues": [{"number": 7, "title": "owed row ledger",
                    "labels": [{"name": l} for l in labels],
                    "createdAt": "2026-10-21T15:06:58Z"}],
        "issue:7": {"number": 7, "body": "## Finding\n\nAn owed row.\n\n" + marker_text},
        "comments:7": [{"created_at": "2026-10-22T00:00:00Z", "body": "(no markers here)"}],
    }


def test_the_owed_row_marker_is_registered_and_parses():
    """The marker's name+shape exist once, in scripts/bot_markers.py, and round-trip."""
    written = bot_markers.owed_row_marker("8", "tests/test_refresh_base.py")
    assert written == '<!-- owed-row: section=8 needle=tests/test_refresh_base.py -->'
    quoted = bot_markers.owed_row_marker("6b", "make refresh-sync")
    assert quoted == '<!-- owed-row: section=6b needle="make refresh-sync" -->'
    parsed = bot_markers.parse_owed_rows(f"body {written} ... {quoted}")
    assert parsed["malformed"] == []
    assert parsed["rows"] == [{"section": "8", "needle": "tests/test_refresh_base.py"},
                              {"section": "6b", "needle": "make refresh-sync"}]


def test_a_landed_owed_row_is_reported_with_evidence(tmp_path=None):
    if tmp_path is None:  # the standalone runner passes no pytest fixture
        tmp_path = Path(tempfile.mkdtemp())
    marker = bot_markers.owed_row_marker("8", "tests/test_refresh_base.py")
    proc = _run(tmp_path, _fixtures(marker))
    assert proc.returncode == 0, proc.stderr
    assert "LANDED AGENTS.md:14" in proc.stdout
    assert "landed=1 outstanding=0" in proc.stdout


def test_an_outstanding_owed_row_is_reported(tmp_path=None):
    if tmp_path is None:  # the standalone runner passes no pytest fixture
        tmp_path = Path(tempfile.mkdtemp())
    marker = bot_markers.owed_row_marker("6b", "make refresh-sync")
    proc = _run(tmp_path, _fixtures(marker))
    assert proc.returncode == 0, proc.stderr
    assert "OUTSTANDING" in proc.stdout
    assert "landed=0 outstanding=1" in proc.stdout


def test_a_needle_landed_in_the_wrong_section_is_not_landed(tmp_path=None):
    if tmp_path is None:  # the standalone runner passes no pytest fixture
        tmp_path = Path(tempfile.mkdtemp())
    # #509's class: a reader must not claim a row landed by matching text ANYWHERE; the
    # declared section is part of the contract, and the misplaced hit is named.
    marker = bot_markers.owed_row_marker("6b", "make make-tea")
    proc = _run(tmp_path, _fixtures(marker))
    assert proc.returncode == 0, proc.stderr
    assert "OUTSTANDING" in proc.stdout
    assert "outside section 6b" in proc.stdout


def test_a_marker_on_a_comment_counts_like_one_on_the_body(tmp_path=None):
    if tmp_path is None:  # the standalone runner passes no pytest fixture
        tmp_path = Path(tempfile.mkdtemp())
    fix = _fixtures("(the body carries no marker)")
    fix["comments:7"] = [{"created_at": "2026-10-23T00:00:00Z",
                          "body": "Ledger row: " + bot_markers.owed_row_marker(
                              "8", "tests/test_refresh_base.py")}]
    proc = _run(tmp_path, fix)
    assert proc.returncode == 0, proc.stderr
    assert "LANDED AGENTS.md:14" in proc.stdout


def test_a_malformed_owed_row_marker_is_loud(tmp_path=None):
    if tmp_path is None:  # the standalone runner passes no pytest fixture
        tmp_path = Path(tempfile.mkdtemp())
    proc = _run(tmp_path, _fixtures("<!-- owed-row: section=8 -->"))
    assert proc.returncode == 2
    assert "MALFORMED" in proc.stdout or "MALFORMED" in proc.stderr
    assert "problems=1" in proc.stdout
    assert "FAILED" in proc.stderr


def test_an_unknown_section_is_loud(tmp_path=None):
    if tmp_path is None:  # the standalone runner passes no pytest fixture
        tmp_path = Path(tempfile.mkdtemp())
    marker = bot_markers.owed_row_marker("17", "tests/test_anything.py")
    proc = _run(tmp_path, _fixtures(marker))
    assert proc.returncode == 2
    assert "NO SUCH SECTION" in proc.stdout


def test_a_queue_issue_without_a_marker_is_reported_as_unmarked(tmp_path=None):
    if tmp_path is None:  # the standalone runner passes no pytest fixture
        tmp_path = Path(tempfile.mkdtemp())
    proc = _run(tmp_path, _fixtures("(nothing declared here)"))
    assert proc.returncode == 0, proc.stderr
    assert "NO MARKER" in proc.stdout
    assert "no-marker=1" in proc.stdout


def test_an_unreadable_issue_is_a_problem(tmp_path=None):
    if tmp_path is None:  # the standalone runner passes no pytest fixture
        tmp_path = Path(tempfile.mkdtemp())
    fix = _fixtures("<!-- owed-row: section=8 needle=x -->")
    del fix["comments:7"]  # the stub will fail this read (no fixture)
    proc = _run(tmp_path, fix)
    assert proc.returncode == 2
    assert "UNREADABLE" in proc.stdout


def test_the_pipeline_calls_the_ledger_target():
    """`make owed-rows-check` is wired through the Makefile AND called by queued-alarm (rule 6m)."""
    makefile = (ROOT / "Makefile").read_text(encoding="utf-8")
    assert "owed-rows-check:" in makefile
    assert "scripts/owed_rows_check.py" in makefile
    workflow = (ROOT / ".github" / "workflows" / "queued-alarm.yml").read_text(encoding="utf-8")
    assert "make owed-rows-check REPO=" in workflow


def test_the_ledger_script_is_the_only_reacher_for_the_marker():
    """No second copy of the marker shape exists in the tree outside scripts/bot_markers.py."""
    hits = subprocess.run(
        ["grep", "-rn", "owed-row:", str(ROOT / "scripts"), str(ROOT / ".github")],
        capture_output=True, text=True).stdout.splitlines()
    offenders = [h for h in hits if "scripts/bot_markers.py" not in h]
    assert offenders == [], f"marker shape re-spelled outside bot_markers.py: {offenders}"


def main() -> int:
    tests = [
        test_the_owed_row_marker_is_registered_and_parses,
        test_a_landed_owed_row_is_reported_with_evidence,
        test_an_outstanding_owed_row_is_reported,
        test_a_needle_landed_in_the_wrong_section_is_not_landed,
        test_a_marker_on_a_comment_counts_like_one_on_the_body,
        test_a_malformed_owed_row_marker_is_loud,
        test_an_unknown_section_is_loud,
        test_a_queue_issue_without_a_marker_is_reported_as_unmarked,
        test_an_unreadable_issue_is_a_problem,
        test_the_pipeline_calls_the_ledger_target,
        test_the_ledger_script_is_the_only_reacher_for_the_marker,
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
