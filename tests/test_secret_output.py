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


def test_githubs_own_token_in_a_run_block_is_a_violation():
    """Issue #241: `${{ github.token }}` is a credential too, so the rule's claim is equally true of
    it. Every spelling GitHub accepts must be caught, and the failure must NAME the expression it
    found — a guard that says only "a secret" leaves the reader searching the file."""
    for spelling in ("${{ github.token }}", "${{ github['token'] }}", '${{ github["token"] }}'):
        for shape, body in (("block", "      - run: |\n"
                                       f"          echo \"{spelling}\" | docker login ghcr.io -u x --password-stdin\n"),
                            ("inline", f"      - run: echo \"{spelling}\" | docker login ghcr.io -u x --password-stdin\n")):
            with tempfile.TemporaryDirectory() as td:
                root = _tree(Path(td), {".github/workflows/a.yml":
                    "name: a\non:\n  workflow_dispatch:\njobs:\n  a:\n    steps:\n" + body})
                bad = cso.violations(root)
            check(f"secrets-in-run-block: `{spelling}` in a {shape} `run:` is a violation",
                  len(bad) == 1 and "secrets-in-run-block" in bad[0] and "github" in bad[0], str(bad))


def test_a_secret_in_an_inline_run_is_a_violation():
    """The inline shape (`- run: <cmd>`) is the most common one, and the collector used to skip it
    although its docstring promised "scalar or `|`": the sandbox test is the same secret, so it has
    to be the same rule."""
    with tempfile.TemporaryDirectory() as td:
        root = _tree(Path(td), {".github/workflows/a.yml":
            "name: a\non:\n  workflow_dispatch:\njobs:\n  a:\n    steps:\n"
            "      - run: curl -H \"Authorization: Bearer ${{ secrets.HF_TOKEN }}\" https://example.invalid\n"})
        bad = cso.violations(root)
    check("secrets-in-run-block: an inline `- run: <cmd>` is scanned too",
          len(bad) == 1 and "secrets-in-run-block" in bad[0], str(bad))


def test_githubs_own_token_through_env_is_not_a_violation():
    """The fix the rule asks for: the same token as a webhook/workflow `env:` entry is fine."""
    with tempfile.TemporaryDirectory() as td:
        root = _tree(Path(td), {".github/workflows/a.yml":
            "name: a\non:\n  workflow_dispatch:\njobs:\n  a:\n    steps:\n"
            "      - run: docker login ghcr.io -u x --password-stdin\n"
            "        env:\n          GHCR_TOKEN: ${{ github.token }}\n"})
        bad = cso.violations(root)
    check("secrets-in-run-block: `${{ github.token }}` passed through `env:` is not a violation",
          bad == [], str(bad))


def test_the_run_block_rule_only_applies_to_workflows():
    """A shell script that mentions the expression is not a `run:` block — the rule is about YAML
    interpolation, and a rule that fires outside its scope gets muted (measured for `key-shaped`)."""
    with tempfile.TemporaryDirectory() as td:
        root = _tree(Path(td), {"scripts/x.sh": "echo \"${{ github.token }}\" | docker login\n"})
        bad = cso.violations(root)
    check("secrets-in-run-block: a non-workflow file is out of scope", bad == [], str(bad))


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


def test_a_whole_stdout_piped_into_github_output_is_a_violation():
    """issue #346 — the measured line. `make` echoes its recipe line, so the output
    file gets a line that is not `key=value` and the whole step dies with
    `Invalid format`, after the implementation behind it was already done."""
    old = ("      - name: Apply the implementer's verdict (make issue-verdict)\n"
           "        run: |\n"
           "          set -o pipefail\n"
           '          make issue-verdict | tee /dev/stderr >> "$GITHUB_OUTPUT"\n')
    with tempfile.TemporaryDirectory() as td:
        root = _tree(Path(td), {".github/workflows/issue-bot.yml": old})
        rules = _rules(root)
        check("whole-stdout: the measured step shape is a violation",
              "whole-stdout-into-output-file" in rules, rules)
        check("whole-stdout: the log copy is caught too",
              "whole-stdout-into-log" in rules, rules)


def test_a_command_substitution_into_the_output_file_is_a_violation():
    sub = ("      - name: x\n"
           "        run: |\n"
           '          $(make rebuild-decision) >> "$GITHUB_OUTPUT"\n')
    with tempfile.TemporaryDirectory() as td:
        root = _tree(Path(td), {".github/workflows/refresh-bot.yml": sub})
        check("whole-stdout: a bare command substitution into the output file is a violation",
              "whole-stdout-into-output-file" in _rules(root), _rules(root))


def test_parsed_key_values_are_not_a_violation():
    """The fix's shape: capture the output, write ONLY `key=value`, print at most the
    parsed value. It must be clean, or the guard would forbid the fix it exists for."""
    fixed = ("      - name: Apply the implementer's verdict (make issue-verdict)\n"
             "        run: |\n"
             "          OUT=$(make issue-verdict)\n"
             "          for key in verdict; do\n"
             '            value=$(printf \'%s\\n\' "$OUT" | sed -n "s/^${key}=//p" | head -1)\n'
             '            printf \'%s=%s\\n\' "$key" "$value" >> "$GITHUB_OUTPUT"\n'
             "          done\n"
             "          printf '[verdict] %s\\n' \"$value\"\n")
    with tempfile.TemporaryDirectory() as td:
        root = _tree(Path(td), {".github/workflows/issue-bot.yml": fixed})
        check("whole-stdout: the parsed key=value shape is clean", _rules(root) == [], _rules(root))


def test_tee_into_the_log_alone_is_a_violation():
    """No output file needed: `| tee /dev/stderr` puts a whole stream in a public log."""
    with tempfile.TemporaryDirectory() as td:
        root = _tree(Path(td), {"s.sh": '#!/usr/bin/env bash\nmake thing | tee /dev/stderr\n'})
        check("whole-stdout: a bare tee to the log is a violation",
              "whole-stdout-into-log" in _rules(root), _rules(root))
        ok = _tree(Path(td) / "ok", {"s.sh": '#!/usr/bin/env bash\nmake thing | sed -n "/^a=/p"\n'})
        check("whole-stdout: a filtered pipeline is not a violation", _rules(ok) == [], _rules(ok))


def _verdict_step_snippet() -> str:
    """The REAL `run:` text of the verdict step, dedented — so the test locks the
    workflow as shipped, never a copy of it that could drift."""
    lines = (ROOT / ".github/workflows/issue-bot.yml").read_text().splitlines()
    start = next(i for i, l in enumerate(lines) if l.startswith("      - name: Apply the implementer's verdict"))
    run_at = next(i for i in range(start, len(lines)) if lines[i].strip() == "run: |")
    body: list[str] = []
    for l in lines[run_at + 1:]:
        if l.strip() and not l.startswith("          "):
            break
        body.append(l[10:])
    return "\n".join(body)


def test_the_verdict_step_writes_only_the_parsed_key_and_never_the_whole_stream():
    """Run the workflow's own step against a stub `make` whose output carries a recipe
    echo, a diagnostic line and a secret-shaped value: only `verdict=` may reach
    `$GITHUB_OUTPUT`, and the value may reach neither the file nor the log (issue #346)."""
    import os
    import subprocess

    snippet = _verdict_step_snippet()
    check("step: the shipped verdict step captures the output", "OUT=$(make issue-verdict)" in snippet, snippet)
    check("step: and never pipes it wholesale", "| tee" not in snippet and "| tee /dev/stderr" not in snippet)
    with tempfile.TemporaryDirectory() as td:
        bindir = Path(td) / "bin"
        bindir.mkdir()
        stub = bindir / "make"
        # a stub CLI on PATH stands in for the external command; the step's own logic runs.
        stub.write_text("#!/bin/sh\n"
                        "echo 'python3 scripts/issue_verdict.py --issue 346'\n"
                        "echo '[verdict] implement on #346 (o/r)'\n"
                        "echo 'verdict=implement'\n"
                        "echo 'LEAKED=NEVER-PRINT-THIS-0123456789'\n")
        stub.chmod(0o755)
        out = Path(td) / "out"
        out.write_text("")
        env = dict(os.environ, PATH=f"{bindir}:{os.environ['PATH']}", GITHUB_OUTPUT=str(out),
                   GH_TOKEN="token-name-only", REPO="o/r", ISSUE="346")
        r = subprocess.run(["bash", "-e", "-c", snippet], env=env, capture_output=True, text=True)
        check("step: it exits 0 on a normal verdict", r.returncode == 0, r.stderr[-300:])
        content = out.read_text()
        check("step: $GITHUB_OUTPUT holds the parsed key only", content.strip() == "verdict=implement", repr(content))
        check("step: the make echo never reaches the output file", "issue_verdict.py" not in content, repr(content))
        check("step: a value the target printed never reaches the output file", "LEAKED" not in content, repr(content))
        check("step: nor the log", "NEVER-PRINT-THIS-0123456789" not in (r.stdout + r.stderr), r.stdout[-300:])


def test_a_refused_verdict_still_fails_the_step():
    """`make` exiting 2 (a close with no EVIDENCE, an unreadable verdict) must abort the
    step: `bash -e` + a bare assignment are what makes that true now that pipefail is gone."""
    import os
    import subprocess

    snippet = _verdict_step_snippet()
    with tempfile.TemporaryDirectory() as td:
        bindir = Path(td) / "bin"
        bindir.mkdir()
        stub = bindir / "make"
        stub.write_text("#!/bin/sh\necho '[verdict] refused: a close with no EVIDENCE'\nexit 2\n")
        stub.chmod(0o755)
        out = Path(td) / "out"
        out.write_text("")
        env = dict(os.environ, PATH=f"{bindir}:{os.environ['PATH']}", GITHUB_OUTPUT=str(out),
                   GH_TOKEN="token-name-only", REPO="o/r", ISSUE="346")
        r = subprocess.run(["bash", "-e", "-c", snippet], env=env, capture_output=True, text=True)
        check("step: a refused verdict exits non-zero (never a green verdict)", r.returncode != 0, r.returncode)


def test_a_captured_stream_without_redaction_is_a_violation():
    """issue #351: capturing a stream to a file is only safe WITH the redactor in the same
    step. On its own it is a raw stream one edit away from the console."""
    body = ("jobs:\n  j:\n    steps:\n      - name: x\n        run: |\n"
            "          make implement-issue > implement.log 2>&1\n"
            "          echo \"done\"\n")
    with tempfile.TemporaryDirectory() as td:
        root = _tree(Path(td), {".github/workflows/w.yml": body})
        rules = _rules(root)
    check("raw-agent-log-captured: a capture with no redactor is a violation",
          "raw-agent-log-captured" in rules, str(rules))


def test_the_captured_and_redacted_shape_is_clean():
    """The shape the implement step uses: capture, then print only the redacted tail."""
    body = ("jobs:\n  j:\n    steps:\n      - name: x\n        run: |\n"
            "          make implement-issue > implement.log 2>&1\n"
            "          make scrub-log FILE=implement.log LOG_OUT=implement.scrubbed.log TAIL=60\n")
    with tempfile.TemporaryDirectory() as td:
        root = _tree(Path(td), {".github/workflows/w.yml": body})
        bad = cso.violations(root)
    check("raw-agent-log-captured: capture + `make scrub-log` is not a violation", bad == [], str(bad))


def test_printing_the_captured_log_is_a_violation():
    """`cat implement.log` puts the raw stream back on the console the capture existed to keep it off."""
    body = ("jobs:\n  j:\n    steps:\n      - name: x\n        run: |\n"
            "          make implement-issue > implement.log 2>&1\n"
            "          make scrub-log FILE=implement.log\n"
            "          cat implement.log\n")
    with tempfile.TemporaryDirectory() as td:
        root = _tree(Path(td), {".github/workflows/w.yml": body})
        rules = _rules(root)
    check("raw-agent-log-printed: printing the captured file is a violation",
          "raw-agent-log-printed" in rules, str(rules))


def test_a_python_script_that_prints_a_secret_value_is_a_violation():
    """The scripts wired to key values (issue #351): a value read from the environment and
    then printed is the same leak as `echo \"$KEY\"`, and no shell-shaped rule sees it."""
    src = ('import os\n'
           'key = os.environ["HF_TOKEN"]\n'
           'print(f"using {key} for the request")\n')
    with tempfile.TemporaryDirectory() as td:
        root = _tree(Path(td), {"s.py": src})
        rules = _rules(root)
    check("prints-secret-value: a python script printing a value it read is a violation",
          rules == ["prints-secret-value"], str(rules))


def test_a_python_script_that_prints_the_name_only_is_not_a_violation():
    src = ('import os\n'
           'token = os.environ.get("NOUS_API_KEY")\n'
           'if not token:\n'
           '    print("NOUS_API_KEY is not set")\n'
           'print(f"present: {bool(token)}")\n')
    with tempfile.TemporaryDirectory() as td:
        root = _tree(Path(td), {"s.py": src})
        bad = cso.violations(root)
    check("prints-secret-value: printing the NAME (never the value) is not a violation",
          bad == [], str(bad))


def test_a_python_script_that_prints_a_slice_of_the_value_is_a_violation():
    """A slice is the transformed value GitHub's mask does NOT cover (rule 3d) — still a leak."""
    src = ('import os\n'
           'key = os.environ.get("TYPESAFE_API_KEY")\n'
           'print(f"key starts with {key[:8]}")\n')
    with tempfile.TemporaryDirectory() as td:
        root = _tree(Path(td), {"s.py": src})
        rules = _rules(root)
    check("prints-secret-value: a slice of the value is a violation",
          rules == ["prints-secret-value"], str(rules))


def test_an_agent_stream_printed_raw_is_a_violation():
    """issue #351: a step that runs the agent with its whole stream going to the console log —
    the reviewer's two paths did exactly this (`run: make review-issue`)."""
    body = ("jobs:\n  j:\n    steps:\n      - name: x\n        run: make review-issue\n")
    with tempfile.TemporaryDirectory() as td:
        root = _tree(Path(td), {".github/workflows/w.yml": body})
        rules = _rules(root)
    check("agent-stream-printed-raw: an inline agent run is a violation",
          rules == ["agent-stream-printed-raw"], str(rules))


def test_a_captured_agent_run_is_clean():
    """The shipped shape: capture the agent's stream, print only the redacted tail."""
    body = ("jobs:\n  j:\n    steps:\n      - name: x\n        run: |\n"
            "          make review-issue > review.log 2>&1\n"
            "          make scrub-log FILE=review.log LOG_OUT=review.scrubbed.log TAIL=40\n")
    with tempfile.TemporaryDirectory() as td:
        root = _tree(Path(td), {".github/workflows/w.yml": body})
        bad = cso.violations(root)
    check("agent-stream-printed-raw: the captured+scrubbed agent run is clean", bad == [], str(bad))


def test_a_mention_of_an_agent_target_in_a_message_is_not_a_violation():
    """A step that only NAMES the target (an error message) does not run it."""
    body = ("jobs:\n  j:\n    steps:\n      - name: x\n        run: |\n"
            "          echo \"::error::produced no implementation (make implement-issue rc=2).\"\n")
    with tempfile.TemporaryDirectory() as td:
        root = _tree(Path(td), {".github/workflows/w.yml": body})
        bad = cso.violations(root)
    check("agent-stream-printed-raw: naming the target in output is not a violation", bad == [], str(bad))


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
    test_githubs_own_token_in_a_run_block_is_a_violation()
    test_a_secret_in_an_inline_run_is_a_violation()
    test_githubs_own_token_through_env_is_not_a_violation()
    test_the_run_block_rule_only_applies_to_workflows()
    test_python_reading_os_environ_is_not_a_violation()
    test_a_credential_shaped_literal_is_a_violation()
    test_a_fixture_name_that_merely_starts_like_a_token_is_not_a_violation()
    test_the_marker_declares_deliberate_test_values()
    test_a_whole_stdout_piped_into_github_output_is_a_violation()
    test_a_command_substitution_into_the_output_file_is_a_violation()
    test_parsed_key_values_are_not_a_violation()
    test_tee_into_the_log_alone_is_a_violation()
    test_the_verdict_step_writes_only_the_parsed_key_and_never_the_whole_stream()
    test_a_refused_verdict_still_fails_the_step()
    test_a_captured_stream_without_redaction_is_a_violation()
    test_the_captured_and_redacted_shape_is_clean()
    test_printing_the_captured_log_is_a_violation()
    test_a_python_script_that_prints_a_secret_value_is_a_violation()
    test_a_python_script_that_prints_the_name_only_is_not_a_violation()
    test_a_python_script_that_prints_a_slice_of_the_value_is_a_violation()
    test_an_agent_stream_printed_raw_is_a_violation()
    test_a_captured_agent_run_is_clean()
    test_a_mention_of_an_agent_target_in_a_message_is_not_a_violation()
    test_this_repository_never_prints_a_secret_value()
    test_the_report_lists_the_files_that_name_a_secret()
    test_check_exits_non_zero_on_a_violation()
    test_the_guard_is_wired_into_the_repo()
    print(f"\nPASSED {_PASS} | FAILED {_FAIL}")
    return 1 if _FAIL else 0


if __name__ == "__main__":
    raise SystemExit(main())
