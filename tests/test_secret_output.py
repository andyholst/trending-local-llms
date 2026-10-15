#!/usr/bin/env python3
"""Do we have a test that no secret VALUE is printed? Yes — for every key, not just one.

`scripts/check_secret_output.py` is the guard; this file is its proof. Every rule is broken on a
fixture file (one violation, the right rule id), and the guard is then run over THIS repository,
because a rule the repo itself violates is not a rule.

secret-output: test value — the marker this fixture file carries: the credential-shaped strings
below are deliberate, non-live test values, which is exactly what the marker in the guard is for.

NO-SKIP POLICY: a missing prerequisite is a LOUD FAILURE, never a skip.

Wired into `make test` (rule 6d). Runs as a plain script (the test image's pytest path is dead,
issue #176) and under pytest.
"""
from __future__ import annotations

import contextlib
import io
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import check_secret_output as cso  # noqa: E402

_PASS = 0
_FAIL = 0


def check(name, cond, detail=""):
    global _PASS, _FAIL
    if cond:
        _PASS += 1
        print(f"  ok  {name}")
    else:
        _FAIL += 1
        print(f"  FAIL {name}" + (f"  [{detail}]" if detail else ""))


def _tree(td: Path, files: dict[str, str]) -> Path:
    root = td / "repo"
    root.mkdir(parents=True, exist_ok=True)
    for name, body in files.items():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(body)
    return root


def _rules(root: Path) -> list[str]:
    return [v.split(": ", 1)[1].split(" —")[0] for v in cso.violations(root)]


# ---------------------------------------------------------------------------
# rule: secrets-in-run-block
# ---------------------------------------------------------------------------
def test_a_secret_interpolated_into_a_run_block_is_a_violation():
    with tempfile.TemporaryDirectory() as td:
        root = _tree(Path(td), {".github/workflows/a.yml": """
name: a
on:
  workflow_dispatch:
jobs:
  a:
    steps:
      - run: |
          curl -H "Authorization: Bearer ${{ secrets.HF_TOKEN }}" https://example.invalid
"""})
        rules = _rules(root)
    check("secrets-in-run-block: a `${{ secrets.X }}` in a `run:` block is a violation",
          rules == ["secrets-in-run-block"], str(rules))


def test_a_secret_passed_through_env_is_not_a_violation():
    with tempfile.TemporaryDirectory() as td:
        root = _tree(Path(td), {".github/workflows/a.yml": """
name: a
on:
  workflow_dispatch:
jobs:
  a:
    steps:
      - run: make something
        env:
          HF_TOKEN: ${{ secrets.HF_TOKEN }}
"""})
        bad = cso.violations(root)
    check("secrets-in-run-block: a secret passed through `env:` is not a violation",
          bad == [], str(bad))


# ---------------------------------------------------------------------------
# rule: prints-secret-value
# ---------------------------------------------------------------------------
def test_echoing_a_secret_value_is_a_violation():
    with tempfile.TemporaryDirectory() as td:
        root = _tree(Path(td), {"s.sh": '#!/usr/bin/env bash\necho "token: $HF_TOKEN"\n'})
        rules = _rules(root)
    check("prints-secret-value: echoing a secret's value is a violation",
          rules == ["prints-secret-value"], str(rules))


def test_printing_the_name_and_guarding_on_it_is_not_a_violation():
    """The repo's own guard shape: it fails when the key is missing and prints only the NAME."""
    with tempfile.TemporaryDirectory() as td:
        root = _tree(Path(td), {"s.sh": '''#!/usr/bin/env bash
set -euo pipefail
test -n "$NOUS_API_KEY" || { echo "NOUS_API_KEY unset - refusing to spend time on a dead key"; exit 1; }
'''})
        bad = cso.violations(root)
    check("prints-secret-value: printing the NAME and guarding on it is not a violation",
          bad == [], str(bad))


def test_writing_a_secret_to_a_file_is_not_a_violation():
    """`>> "$HERMES_HOME/.env"` is where a key IS allowed to live (mode 600), not output."""
    with tempfile.TemporaryDirectory() as td:
        root = _tree(Path(td), {"s.sh": '''#!/usr/bin/env bash
printf '%s=%s\\n' "TYPESAFE_API_KEY" "$TYPESAFE_API_KEY" >> "${HERMES_HOME}/.env"
'''})
        bad = cso.violations(root)
    check("prints-secret-value: writing a key to a file (a redirect) is not a violation",
          bad == [], str(bad))


# ---------------------------------------------------------------------------
# rule: xtrace-with-secrets
# ---------------------------------------------------------------------------
def test_xtrace_in_a_file_that_reads_a_secret_is_a_violation():
    with tempfile.TemporaryDirectory() as td:
        root = _tree(Path(td), {"s.sh": '#!/usr/bin/env bash\nset -eux\nmake deploy TOKEN="$HF_TOKEN"\n'})
        rules = _rules(root)
    check("xtrace-with-secrets: `set -x` beside a key read is a violation",
          "xtrace-with-secrets" in rules, str(rules))


def test_no_xtrace_is_not_a_violation():
    with tempfile.TemporaryDirectory() as td:
        root = _tree(Path(td), {"s.sh": '#!/usr/bin/env bash\nset -euo pipefail\nmake deploy TOKEN="$HF_TOKEN"\n'})
        bad = cso.violations(root)
    check("xtrace-with-secrets: no `set -x` is not a violation", bad == [], str(bad))


# ---------------------------------------------------------------------------
# rule: value-in-argv
# ---------------------------------------------------------------------------
def test_a_secret_value_on_the_command_line_is_a_violation():
    with tempfile.TemporaryDirectory() as td:
        root = _tree(Path(td), {"s.sh": '#!/usr/bin/env bash\ndocker run -e HF_TOKEN=$HF_TOKEN img true\n'})
        rules = _rules(root)
    check("value-in-argv: `-e KEY=$KEY` is a violation", rules == ["value-in-argv"], str(rules))


def test_passing_the_name_only_is_not_a_violation():
    with tempfile.TemporaryDirectory() as td:
        root = _tree(Path(td), {"s.sh": '#!/usr/bin/env bash\ndocker run -e HF_TOKEN -e NOUS_API_KEY img true\n'})
        bad = cso.violations(root)
    check("value-in-argv: passing the NAME only is not a violation", bad == [], str(bad))


def test_a_secret_expression_on_the_command_line_is_a_violation():
    with tempfile.TemporaryDirectory() as td:
        root = _tree(Path(td), {"s.sh": '#!/usr/bin/env bash\ndocker run -e HF_TOKEN=${{ secrets.HF_TOKEN }} img true\n'})
        rules = _rules(root)
    check("value-in-argv: a `${{ secrets.X }}` on the command line is a violation",
          rules == ["value-in-argv"], str(rules))


# ---------------------------------------------------------------------------
# rule: env-dump
# ---------------------------------------------------------------------------
def test_a_bare_environment_dump_is_a_violation():
    with tempfile.TemporaryDirectory() as td:
        root = _tree(Path(td), {"s.sh": "#!/usr/bin/env bash\nenv\n"})
        rules = _rules(root)
    check("env-dump: a bare `env` is a violation", rules == ["env-dump"], str(rules))


def test_python_reading_os_environ_is_not_a_violation():
    with tempfile.TemporaryDirectory() as td:
        root = _tree(Path(td), {"s.py": "import os\nenv = os.environ if os.environ else {}\n"})
        bad = cso.violations(root)
    check("env-dump: python reading os.environ is not a violation", bad == [], str(bad))


# ---------------------------------------------------------------------------
# rule: key-shaped-literal
# ---------------------------------------------------------------------------
def test_a_credential_shaped_literal_is_a_violation():
    with tempfile.TemporaryDirectory() as td:
        root = _tree(Path(td), {"cfg.py": 'TOKEN = "hf_' + "A1b2C3d4E5f6G7h8I9j0K1l2M3" + '"\n'})
        rules = _rules(root)
    check("key-shaped-literal: a credential-shaped string is a violation",
          rules == ["key-shaped-literal"], str(rules))


def test_a_fixture_name_that_merely_starts_like_a_token_is_not_a_violation():
    """Measured: the loose pattern flags names like `hf_get_wrapped`, `hf_download_stall`."""
    with tempfile.TemporaryDirectory() as td:
        root = _tree(Path(td), {"t.py": 'NAME = "hf_download_stall"\nOTHER = "hf_get_wrapped"\n'})
        bad = cso.violations(root)
    check("key-shaped-literal: a fixture NAME that merely starts like a token is not a violation",
          bad == [], str(bad))


def test_the_marker_declares_deliberate_test_values():
    # this file itself carries the marker (see the module docstring), so use a copy of it
    body = (ROOT / "tests" / "test_secret_output.py").read_text()
    check("key-shaped-literal: this file carries the test-value marker",
          cso.TEST_VALUE_MARKER in body, "")
    with tempfile.TemporaryDirectory() as td:
        root = _tree(Path(td), {"t.py": 'TOKEN = "hf_' + "A1b2C3d4E5f6G7h8I9j0K1l2M3" + '"\n'})
        marked = _tree(Path(td) / "marked", {"t.py": f"# {cso.TEST_VALUE_MARKER}\n"
                                                      'TOKEN = "hf_' + "A1b2C3d4E5f6G7h8I9j0K1l2M3" + '"\n'})
        unmarked_rules = _rules(root)
        marked_bad = cso.violations(marked)
    check("key-shaped-literal: unmarked is a violation", unmarked_rules == ["key-shaped-literal"],
          str(unmarked_rules))
    check("key-shaped-literal: the marker declares deliberate test values", marked_bad == [],
          str(marked_bad))


# ---------------------------------------------------------------------------
# the guard over THIS repository, and the exit code CI gates on
# ---------------------------------------------------------------------------
def test_this_repository_never_prints_a_secret_value():
    bad = cso.violations(ROOT)
    check("this repo: no secret VALUE is printed/passed/xtraced/dumped/committed",
          bad == [], "\n".join(bad[:5]))
    check("this repo: `check` exits 0", cso.main(["check"]) == 0, "")


def test_the_report_lists_the_files_that_name_a_secret():
    rows = cso.report(ROOT)
    files = {r["file"] for r in rows}
    # the bot workflows and the image's install scripts are the ones that carry keys
    for name in (".github/workflows/issue-bot.yml", ".github/workflows/fix-bot.yml",
                 ".github/workflows/qa-validate.yml", ".github/workflows/refresh-bot.yml",
                 "scripts/nerve_key_check.py", "Makefile"):
        check(f"report: {name} names a secret variable", name in files, "")
    check("report: no file prints a secret value", all(not r["prints"] for r in rows),
          str([r for r in rows if r["prints"]]))
    check("report: no file xtraces a secret", all(not r["xtrace"] for r in rows),
          str([r for r in rows if r["xtrace"]]))


def test_check_exits_non_zero_on_a_violation():
    with tempfile.TemporaryDirectory() as td:
        root = _tree(Path(td), {"s.sh": '#!/usr/bin/env bash\necho "$HF_TOKEN"\n'})
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            rc = cso.main(["check", "--root", str(root)])
        check("check: a violation exits non-zero", rc == 1, str(rc))
        check("check: the rule id is named", "prints-secret-value" in err.getvalue(), err.getvalue())

        clean = _tree(Path(td) / "clean", {"s.sh": '#!/usr/bin/env bash\necho "HF_TOKEN unset"\n'})
        check("check: a clean tree exits 0", cso.main(["check", "--root", str(clean)]) == 0, "")


def test_the_guard_is_wired_into_the_repo():
    """A guard no target names runs nowhere: the make targets, .PHONY and the test chain."""
    mk = (ROOT / "Makefile").read_text()
    check("make: `check-secret-output` target exists", "check-secret-output:" in mk, "")
    check("make: `secret-output-report` target exists", "secret-output-report:" in mk, "")
    check("make: the targets are in .PHONY",
          ".PHONY: check-secret-output secret-output-report" in mk, "")
    check("make: the target runs the guard script", "check_secret_output.py check" in mk, "")
    check("make: the guard's test is in `make test`", "tests/test_secret_output.py" in mk, "")


def main() -> int:
    print("no-secret-VALUE guard (scripts/check_secret_output.py, issue #219)")
    test_a_secret_interpolated_into_a_run_block_is_a_violation()
    test_a_secret_passed_through_env_is_not_a_violation()
    test_echoing_a_secret_value_is_a_violation()
    test_printing_the_name_and_guarding_on_it_is_not_a_violation()
    test_writing_a_secret_to_a_file_is_not_a_violation()
    test_xtrace_in_a_file_that_reads_a_secret_is_a_violation()
    test_no_xtrace_is_not_a_violation()
    test_a_secret_value_on_the_command_line_is_a_violation()
    test_passing_the_name_only_is_not_a_violation()
    test_a_secret_expression_on_the_command_line_is_a_violation()
    test_a_bare_environment_dump_is_a_violation()
    test_python_reading_os_environ_is_not_a_violation()
    test_a_credential_shaped_literal_is_a_violation()
    test_a_fixture_name_that_merely_starts_like_a_token_is_not_a_violation()
    test_the_marker_declares_deliberate_test_values()
    test_this_repository_never_prints_a_secret_value()
    test_the_report_lists_the_files_that_name_a_secret()
    test_check_exits_non_zero_on_a_violation()
    test_the_guard_is_wired_into_the_repo()
    print(f"\nPASSED {_PASS} | FAILED {_FAIL}")
    return 1 if _FAIL else 0


if __name__ == "__main__":
    raise SystemExit(main())
