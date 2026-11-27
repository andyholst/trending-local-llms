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
        # issue #1820: a producer that stays alive a moment, prints NOTHING and exits 0. On the
        # pre-fix seam this reads as a clean green leg (`stream: 0 line(s)`, rc 0).
        + "\nquiet:\n\t$(call scrubbed_run,sleep 0.05)\n"
        # Three real lines, one carrying the fake secret — the talking-stream control that must
        # stay byte-for-byte green beside the new refusal.
        + "\ntalking:\n\t$(call scrubbed_run,echo first; echo \"the key is $$NOUS_API_KEY\"; echo third)\n"
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


#: A stand-in for the EXTERNAL docker CLI (rule 6m): it emulates the one behaviour that matters
#: here — a `docker run` WITHOUT `-i` closes the container's stdin (the scrubber reads EOF and
#: exits), while `docker run -i` forwards it. Everything else is ignored; the real seam and the
#: real scripts/scrub_log.py still run.
_STUB_DOCKER = """#!/usr/bin/env bash
set -u
img="python:slim"
args=("$@")
attach=0
idx=-1
for a in "${args[@]}"; do [ "$a" = "-i" ] && attach=1; done
for ((i=0; i<${#args[@]}; i++)); do [ "${args[i]}" = "$img" ] && idx=$i; done
cmd=("${args[@]:idx+1}")
if [ "$attach" = 1 ]; then
  exec "${cmd[@]}"
else
  exec "${cmd[@]}" </dev/null
fi
"""


def _python_run_block() -> str:
    """The SHIPPED `PYTHON_RUN` definition, extracted from the Makefile (no copy lives here)."""
    lines = (ROOT / "Makefile").read_text().splitlines()
    for i, ln in enumerate(lines):
        if ln.startswith("PYTHON_RUN := "):
            block = [ln]
            while block[-1].rstrip().endswith("\\"):
                block.append(lines[i + len(block)])
            return "\n".join(block) + "\n"
    raise AssertionError("PYTHON_RUN definition not found in the Makefile")


def _stream_fixture(tmp: Path) -> Path:
    """A fixture using the REAL seam + REAL PYTHON_RUN, with a stand-in docker on PATH."""
    (tmp / "scripts").mkdir(exist_ok=True)
    for f in ("scrub_log.py", "check_secret_output.py"):
        shutil.copy(ROOT / "scripts" / f, tmp / "scripts" / f)
    stub = tmp / "stubbin"
    stub.mkdir(exist_ok=True)
    docker = stub / "docker"
    docker.write_text(_STUB_DOCKER)
    docker.chmod(0o755)
    (tmp / "Makefile").write_text(
        "HERMES_LOG      := hermes-run.log\n"
        "HERMES_LOG_SCRUBBED := hermes-run.scrubbed.log\n"
        "PYTHON_IMAGE    := python:slim\n\n"
        + _python_run_block()
        + "\n"
        + _seam()
        + "\nstream:\n\t$(call scrubbed_run,sh -c 'sleep 0.4; printf \"alpha\\nbeta\\n\"')\n"
        + "\nquiet:\n\t$(call scrubbed_run,sh -c 'sleep 0.4')\n"
    )
    return tmp


def _make_env(tmp: Path) -> dict:
    stub = str(tmp / "stubbin")
    return dict(os.environ, PATH=stub + os.pathsep + os.environ.get("PATH", ""))


def test_the_redactor_attaches_stdin_so_the_agent_stream_is_captured():
    """Issue #1808: PYTHON_RUN is a `docker run` at the redactor end of the scrubbed_run pipe.
    Without `-i` the container's stdin is closed, scrub_log.py --stream reads 0 lines and exits
    immediately, and the still-writing producer dies with SIGPIPE (141) — measured on refresh
    run 46000947806 (`stream: 0 line(s)` then `[scrub-log] FAIL … exit 141`). With `-i` the
    scrubber reads the live pipe, both lines reach the redacted log, and the producer's status
    is preserved. The anti-vacuous classification from #1747 must stay intact."""
    td = _stream_fixture(Path(tempfile.mkdtemp()))
    env = _make_env(td)

    r = subprocess.run(["make", "stream"], cwd=str(td), env=env, capture_output=True, text=True)
    console = r.stdout + r.stderr

    check("stdin: the agent's line reaches the redactor", "[agent] alpha" in console, console[-400:])
    check("stdin: both streamed lines are captured",
          "[agent] alpha" in console and "[agent] beta" in console, console[-400:])
    check("stdin: the scrubber reports a non-empty stream",
          re.search(r"stream: [1-9]\d* line\(s\)", console) is not None, console[-400:])
    check("stdin: no SIGPIPE classification on a live stream",
          "SIGPIPE" not in console and "exit 141" not in console, console[-400:])
    check("stdin: the producer keeps a success status", r.returncode == 0, str(r.returncode))

    # The shipped seam still carries the #1747 classification and the producer's exit status:
    # fixing the cause must not turn a genuinely dead agent into a skip or a retry-all.
    seam = _seam()
    check("anti-vacuous: the SIGPIPE classification is still present",
          "SIGPIPE (exit 141)" in seam, seam[:300])
    check("anti-vacuous: the seam still exits with the producer's status",
          'exit "$$st"' in seam, seam[:300])

    # A producer that emits nothing still yields a zero-line stream — no fabricated content,
    # and the fix did not turn an empty stream into a fake success with invented lines.
    q = subprocess.run(["make", "quiet"], cwd=str(td), env=env, capture_output=True, text=True)
    qconsole = q.stdout + q.stderr
    check("anti-vacuous: a silent producer yields no redacted lines",
          "[agent] " not in qconsole, qconsole[-300:])


def test_a_silent_producer_is_a_loud_classified_failure():
    """issue #1820/#1747: a 0-line stream from a successful producer must FAIL, not look green.

    RED on the pre-fix seam (`stream: 0 line(s)`, no `[agent]`, rc 0); GREEN once the redactor
    refuses the empty stream and the seam promotes its non-zero status. Only the external CLI is
    a stand-in — the shipped seam and the real `scrub_log.py` do all the work.
    """
    td = _fixture(Path(tempfile.mkdtemp()))
    r = subprocess.run(["make", "quiet"], cwd=str(td), capture_output=True, text=True)
    console = r.stdout + r.stderr
    fails = [ln for ln in console.splitlines() if "[scrub-log] FAIL:" in ln]
    # make turns ANY recipe failure into its own rc 2; the leg's exact exit 3 is pinned by make's
    # `Error 3` diagnostic. On the pre-fix seam make is green (rc 0) and there is no such line.
    check("quiet: a 0-line/0-status producer is refused with seam exit 3",
          r.returncode != 0 and "Error 3" in console,
          f"make rc={r.returncode}, console={console[-200:]!r}")
    check("quiet: exactly ONE classified FAIL line", len(fails) == 1, fails)
    check("quiet: the FAIL names quiet/agent-failed and both issues",
          bool(fails) and "quiet/agent-failed" in fails[0] and "#1820" in fails[0]
          and "#1747" in fails[0], fails[:1])
    check("quiet: no [agent] line is printed for an empty stream",
          "[agent]" not in console, console[:300])
    check("quiet: no green 'stream: 0 line(s)' summary survives",
          "stream: 0 line(s)" not in console, console[:300])


def test_a_talking_producer_still_redacts_every_line():
    """Control (#1820): a real 3-line stream must keep redacting, printing and staying green."""
    td = _fixture(Path(tempfile.mkdtemp()))
    env = dict(os.environ, NOUS_API_KEY=FAKE_VALUE)
    r = subprocess.run(["make", "talking"], cwd=str(td), env=env, capture_output=True, text=True)
    console = r.stdout + r.stderr
    agent_lines = [ln for ln in console.splitlines() if ln.startswith("[agent] ")]
    check("talking: all three lines reach the console", len(agent_lines) == 3, agent_lines)
    check("talking: the value is masked, never printed", FAKE_VALUE not in console, console[:200])
    scrubbed = td / "hermes-run.scrubbed.log"
    check("talking: the redacted artifact is non-empty",
          scrubbed.is_file() and scrubbed.stat().st_size > 0, str(scrubbed))
    check("talking: the leg stays green (rc 0)", r.returncode == 0, r.returncode)


def test_the_existing_seam_contract_survives_the_promotion():
    """#1820 is byte-additive to the shipped seam: runner, PIPESTATUS[0], 141 line unchanged."""
    seam = _seam()
    check("seam: the shipped redactor runner is still used", "$(PYTHON_RUN)" in seam,
          seam[:300])
    check("seam: PIPESTATUS[0] is still the producer status", "PIPESTATUS[0]" in seam, seam[:300])
    check("seam: the #1747 SIGPIPE(141) classification line is unchanged",
          "the agent stream closed with SIGPIPE (exit 141)" in seam and "issue #1747" in seam,
          seam[:400])
    check("seam: the producer's exit status is still the seam's verdict",
          'exit "$$st"' in seam, seam[:300])


def main() -> int:
    print("scrubbed_run seam: positional command, never a splice (issue #632); stdin attach (#1808)")
    test_a_command_with_single_quotes_survives_the_seam()
    test_the_seam_never_splices_the_command_into_the_script_text()
    test_redaction_still_wraps_the_positional_command()
    test_a_red_command_keeps_its_exit_status_through_eval()
    test_the_redactor_attaches_stdin_so_the_agent_stream_is_captured()
    test_a_silent_producer_is_a_loud_classified_failure()
    test_a_talking_producer_still_redacts_every_line()
    test_the_existing_seam_contract_survives_the_promotion()
    print(f"\nPASSED {_PASS} | FAILED {_FAIL}")
    return 1 if _FAIL else 0


if __name__ == "__main__":
    raise SystemExit(main())
