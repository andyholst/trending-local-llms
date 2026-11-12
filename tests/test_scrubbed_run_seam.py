#!/usr/bin/env python3
"""Does the `scrubbed_run` seam hand the COMMAND to `bash -c` as a positional argument? (issue #632)

The seam used to interpolate `$(1)` INSIDE a single-quoted script:
`bash -o pipefail -c '$(1) 2>&1 | python3 scripts/scrub_log.py …'`. AGENTS.md §4 tells every
prompt to put prose in single quotes inside the `-z "…"` body, so a caller that follows the rule
closes the `-c` string early: bash parses the remaining prose as a command and the leg dies with
a syntax error far from its cause (measured against the old seam with a probe command carrying
single quotes: `unexpected EOF while looking for matching '`, exit 2). The seam now shell-escapes
the value with `$(subst ','\\'',…)` and runs it through `eval "$$1"` as a positional argument —
same parsing, same pipefail status, same redaction.

NO-SKIP POLICY: a missing prerequisite is a LOUD FAILURE, never a skip.

Wired into `make test` (rule 6d). Runs as a plain script — the runner is scripts/run_tests.sh,
the test image carries no test runner at all (issue #176).
"""
from __future__ import annotations

import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

_PASS = 0
_FAIL = 0

#: A fake credential VALUE, never printed by the assertions themselves — the redactor needs
#: something real to redact.
FAKE_VALUE = "NEVER-PRINT-THIS-0123456789"


def check(name, cond, detail=""):
    global _PASS, _FAIL
    if cond:
        _PASS += 1
        print(f"  ok  {name}")
    else:
        _FAIL += 1
        print(f"  FAIL {name}" + (f"  [{detail}]" if detail else ""))


def _seam() -> str:
    """The SHIPPED seam, extracted from the repository Makefile — no copy of it lives here."""
    mk = (ROOT / "Makefile").read_text()
    return re.search(r"^define scrubbed_run\n.*?^endef\n", mk, re.M | re.S).group(0)


def _fixture(tmp: Path) -> Path:
    """A minimal workspace: the shipped seam + the scripts it invokes + probe targets."""
    (tmp / "scripts").mkdir(exist_ok=True)
    for f in ("scrub_log.py", "check_secret_output.py"):
        shutil.copy(ROOT / "scripts" / f, tmp / "scripts" / f)
    (tmp / "Makefile").write_text(
        "HERMES_LOG      := hermes-run.log\n"
        "HERMES_LOG_SCRUBBED := hermes-run.scrubbed.log\n\n"
        + _seam()
        + "\nprose:\n\t$(call scrubbed_run,echo \"prose with 'single quotes' inside\")\n"
        + "\nleaky:\n\t$(call scrubbed_run,echo \"the key is $$NOUS_API_KEY\")\n"
        + "\nfailing:\n\t$(call scrubbed_run,exit 3)\n"
    )
    return tmp


def test_a_command_with_single_quotes_survives_the_seam():
    """issue #632, the exact shape §4 prompts produce: double-quoted prose carrying single quotes.

    With the old splice this target died with a bash syntax error before the command ran; the
    positional seam must run it and print its own output.
    """
    td = _fixture(Path(tempfile.mkdtemp()))
    r = subprocess.run(["make", "prose"], cwd=str(td), capture_output=True, text=True)
    console = r.stdout + r.stderr
    check("seam: a command carrying single quotes runs (rc 0)", r.returncode == 0, console[:300])
    check("seam: the quoted prose reaches the console intact",
          "prose with 'single quotes' inside" in console, console[:300])
    check("seam: bash never reported a splice syntax error",
          "unexpected EOF" not in console and "syntax error" not in console, console[:300])


def test_the_seam_never_splices_the_command_into_the_script_text():
    """The regression guard: the shipped seam passes $1 positionally; the old splice shape is refused."""
    seam = _seam()
    check("seam: runs the command as the positional $1 via eval", 'eval "$$1"' in seam, seam[:200])
    check("seam: passes the value after a positional terminator (`_`)",
          re.search(r"^define scrubbed_run\n\t@bash -o pipefail -c '.*' _ ", seam) is not None,
          seam[:200])
    check("seam: shell-escapes every single quote of the value ($(subst ','\\'',…))",
          "$(subst ','\\'',$(1))" in seam, seam[:200])
    check("seam: the old splice `-c '$(1) …'` never returns",
          "-c '$(1)" not in seam, seam[:200])


def test_redaction_still_wraps_the_positional_command():
    """Passing the command positionally must not weaken the redactor (rule 3d): the value never
    reaches the console, the mask does, and BOTH capture files are still written."""
    td = _fixture(Path(tempfile.mkdtemp()))
    env = dict(os.environ, NOUS_API_KEY=FAKE_VALUE)
    r = subprocess.run(["make", "leaky"], cwd=str(td), env=env, capture_output=True, text=True)
    console = r.stdout + r.stderr
    check("seam: the value never reaches make's console", FAKE_VALUE not in console, console[:200])
    check("seam: the redacted line IS printed", "the key is ***" in console, console[:300])
    check("seam: the raw capture is written", (td / "hermes-run.log").is_file(), "")
    check("seam: the redacted capture is written", (td / "hermes-run.scrubbed.log").is_file(), "")


def test_a_red_command_keeps_its_exit_status_through_eval():
    """`eval "$1"` must preserve the pipefail contract: a failing command keeps the leg red."""
    td = _fixture(Path(tempfile.mkdtemp()))
    r = subprocess.run(["make", "failing"], cwd=str(td), capture_output=True, text=True)
    check("seam: a failing command keeps its exit status (a red leg stays red)",
          r.returncode != 0, r.returncode)


def main() -> int:
    print("scrubbed_run seam: positional command, never a splice (issue #632)")
    test_a_command_with_single_quotes_survives_the_seam()
    test_the_seam_never_splices_the_command_into_the_script_text()
    test_redaction_still_wraps_the_positional_command()
    test_a_red_command_keeps_its_exit_status_through_eval()
    print(f"\nPASSED {_PASS} | FAILED {_FAIL}")
    return 1 if _FAIL else 0


if __name__ == "__main__":
    raise SystemExit(main())
