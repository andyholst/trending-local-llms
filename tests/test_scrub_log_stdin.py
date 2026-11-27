#!/usr/bin/env python3
"""#1810: the LIVE redactor must own the producer's stdin — real seam, real scrub_log.py.

The refresh legs pipe a talking agent into `scrub_log.py --stream` through `scrubbed_run`.
`PYTHON_RUN` had no `-i`, so the container's stdin was /dev/null: the redactor saw EOF at once,
captured zero lines, and the still-writing producer died of SIGPIPE (`PIPESTATUS[0]=141`).
The fix attaches stdin at the REDACTOR end only (`PYTHON_RUN_STDIN`, the same flags plus `-i`).

Everything product-shaped here is REAL: the shipped Makefile seam, `scripts/scrub_log.py`,
`scripts/check_no_bare_host_python.py`, `scripts/check_secret_output.py` and
`update_trending.zero_hit_verdict`. The ONLY stub is the container runtime: a fake `docker`
on PATH that reproduces the one behaviour in question (no `-i` => stdin /dev/null, `-i` =>
inherit the pipe) and then execs the real python3 with the real arguments. No business logic
is mocked; no retry, SKIP or classifier change is assumed.

secret-output: test value — the token below is a deliberate, non-live credential SHAPE fixture
used to prove the redactor masks before printing. It is built from two halves on purpose.

Wired into `make test` (rule 6d). Runs as a plain script (issue #176).
"""
from __future__ import annotations

import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

PASSED = FAILED = 0

FAKE_TOKEN = "ghp_" + "A1B2C3D4E5F6G7H8I9J0"
MASK = "***"

#: Stand-in for the external container runtime ONLY. It consumes the flags of
#: `docker run` and runs the real command; stdin is attached iff `-i` was passed.
DOCKER_STUB = """#!/usr/bin/env bash
set -u
if [ "${1:-}" != run ]; then
    echo "fake-docker: only 'run' is supported, got: $*" >&2
    exit 99
fi
shift
attached=0
while [ "$#" -gt 0 ]; do
    case "$1" in
        -i|--interactive) attached=1; shift ;;
        --rm|-t|--tty) shift ;;
        --user|-u|-v|--volume|-w|--workdir|-e|--env|--entrypoint|--name|--network) shift 2 ;;
        *) break ;;
    esac
done
while [ "$#" -gt 0 ] && [ "$1" != python3 ]; do shift; done
if [ "$#" -eq 0 ]; then
    echo "fake-docker: no python3 command in args" >&2
    exit 99
fi
if [ "$attached" = 1 ]; then
    exec "$@"
else
    exec "$@" </dev/null
fi
"""

#: The PRE-CHANGE harness, kept as the RED half of the proof: same seam, but the
#: container runtime is invoked WITHOUT -i, so the reader gets an immediate EOF.
DETACHED_SEAM = (
    "# RED half: the pre-#1810 redactor end, `docker run` without -i.\n"
    "define scrubbed_run\n"
    "\t@bash -o pipefail -c 'eval \"$$1\" 2>&1 | docker run --rm img python3 "
    "scripts/scrub_log.py --stream --append --raw \"$$2\" --out \"$$3\"; "
    "st=$${PIPESTATUS[0]}; if [ \"$$st\" = 141 ]; then printf \"%s\\n\" "
    "\"[scrub-log] FAIL: the agent stream closed with SIGPIPE (exit 141) and NO redacted "
    "line was captured — classified as quiet/agent-failed, not a source outage (issue #1747)\""
    " >&2; fi; exit \"$$st\"' _ '$(subst ','\\'',$(1))' "
    "'$(subst ','\\'',$(HERMES_LOG))' '$(subst ','\\'',$(HERMES_LOG_SCRUBBED))'\n"
    "endef\n"
)

TALKING = (
    'sleep 0.2; for i in 1 2 3 4; do '
    'if [ "$$i" = 2 ]; then printf \'agent says ' + FAKE_TOKEN + ' here\\n\'; '
    'else printf \'agent line %s\\n\' "$$i"; fi; sleep 0.08; done'
)
SILENT = "sleep 0.2; exit 0"
RED = "sleep 0.2; exit 7"


def check(name: str, ok: bool, detail: object = "") -> None:
    global PASSED, FAILED
    if ok:
        PASSED += 1
        print(f"  ok  {name}")
    else:
        FAILED += 1
        print(f"FAIL {name}  {detail}")


def _probe(producer: str) -> str:
    return (".PHONY: probe\nprobe:\n"
            "\t$(call scrubbed_run," + producer + ",$(HERMES_LOG),$(HERMES_LOG_SCRUBBED))\n")


def _run(producer: str, *, detached: bool = False):
    """Drive a Makefile seam with a fake container runtime; return (proc, raw, out)."""
    tmp = Path(tempfile.mkdtemp(prefix="tll-1810-"))
    bin_dir = tmp / "bin"
    bin_dir.mkdir()
    stub = bin_dir / "docker"
    stub.write_text(DOCKER_STUB, encoding="utf-8")
    stub.chmod(0o755)
    (tmp / "probe.mk").write_text(_probe(producer), encoding="utf-8")
    raw, out = tmp / "raw.log", tmp / "out.log"
    env = dict(os.environ)
    env["PATH"] = f"{bin_dir}{os.pathsep}{env.get('PATH', '')}"
    makefiles = [str(tmp / "detached.mk")] if detached else [str(ROOT / "Makefile"), str(tmp / "probe.mk")]
    if detached:
        (tmp / "detached.mk").write_text(DETACHED_SEAM + "\n" + _probe(producer), encoding="utf-8")
    cmd = ["make", "-s"]
    for makefile in makefiles:
        cmd += ["-f", makefile]
    cmd += ["probe", "IN_CONTAINER=", f"HERMES_LOG={raw}", f"HERMES_LOG_SCRUBBED={out}"]
    proc = subprocess.run(cmd, cwd=str(ROOT), env=env, capture_output=True, text=True, timeout=45)
    return proc, raw.read_text(encoding="utf-8"), out.read_text(encoding="utf-8")


def test_the_shipped_seam_captures_and_redacts_a_delayed_agent() -> None:
    """GIVEN the shipped seam and a delayed talking agent, WHEN it runs, THEN all lines land masked."""
    proc, raw, out = _run(TALKING)
    console = proc.stdout + proc.stderr
    check("attached: all four agent lines were streamed", console.count("[agent] ") == 4, console[-600:])
    check("attached: the summary counts 4 lines and 1 redaction",
          "stream: 4 line(s), 1 redaction(s)" in console, console[-400:])
    check("attached: the REDACTED artifact carries the mask, not the token",
          MASK in out and FAKE_TOKEN not in out, out[-300:])
    check("attached: the console never prints the token", FAKE_TOKEN not in console, console[-300:])
    check("attached: the RAW artifact keeps the honest transcript", FAKE_TOKEN in raw, raw[-200:])
    check("attached: the producer's rc survives the pipe", proc.returncode == 0, proc.returncode)
    check("attached: no SIGPIPE classification on a healthy stream",
          "quiet/agent-failed" not in console, console[-300:])


def test_the_pre_change_harness_loses_every_line() -> None:
    """RED half: the detached container stdin gives 0 lines, SIGPIPE 141 and no redacted line."""
    proc, raw, out = _run(TALKING, detached=True)
    console = proc.stdout + proc.stderr
    check("detached: the summary counts 0 lines and 0 redactions",
          "stream: 0 line(s), 0 redaction(s)" in console, console[-400:])
    check("detached: no agent line reached the console", "[agent]" not in console, console[-300:])
    check("detached: the #1747 SIGPIPE classification is printed",
          "quiet/agent-failed" in console and "141" in console, console[-400:])
    check("detached: make reports Error 141", "Error 141" in console, console[-300:])
    check("detached: the REDACTED artifact holds no agent content",
          not [line for line in out.splitlines() if not line.startswith("=====")], out[-200:])
    check("detached: the run is red", proc.returncode != 0, proc.returncode)


def test_a_silent_agent_is_not_retried_and_the_verdict_stays_put() -> None:
    """A genuinely quiet agent stays 0 lines / rc 0; no SKIP, no retry, unchanged classifier."""
    from update_trending import zero_hit_verdict

    proc, raw, out = _run(SILENT)
    console = proc.stdout + proc.stderr
    check("silent: 0 lines streamed and the leg stays green",
          "stream: 0 line(s)" in console and proc.returncode == 0, console[-300:])
    check("silent: no retry and no SKIP was introduced",
          re.search(r"\bretry\b", console, re.I) is None
          and re.search(r"\bskip\b", console, re.I) is None, console[-300:])
    quiet = zero_hit_verdict({"queries": 4, "with_hits": 0, "outage": 0,
                             "refused": 0, "failed": 0, "timeouts": 0})
    check("classifier: a quiet reachable mirror is still red (quiet/1)",
          quiet[:2] == ("quiet", 1), quiet[:2])
    outage = zero_hit_verdict({"queries": 4, "with_hits": 0, "outage": 4,
                              "refused": 0, "failed": 0, "timeouts": 0})
    check("classifier: a total outage is still excused (outage/0)",
          outage[:2] == ("outage", 0), outage[:2])


def test_a_red_producer_keeps_its_own_status_through_the_attached_pipe() -> None:
    """pipefail + PIPESTATUS[0] still report the PRODUCER, not the redactor."""
    proc, _raw, _out = _run(RED)
    console = proc.stdout + proc.stderr
    check("status: a red agent stays red", proc.returncode != 0, proc.returncode)
    check("status: the producer's own 141-free status is named", "Error 7" in console, console[-300:])


def test_the_two_harnesses_carry_the_same_flags() -> None:
    """PYTHON_RUN stays literal-identical to base; the scoped sibling differs only by -i."""
    makefile = (ROOT / "Makefile").read_text(encoding="utf-8")

    def definition(name: str) -> str:
        match = re.search(rf"^{name} := (.*?)(?=\n[^\s]|\Z)", makefile, re.M | re.S)
        return match.group(1) if match else ""

    shared = definition("PYTHON_RUN").replace("\n\t", " ").strip()
    attached = definition("PYTHON_RUN_STDIN").replace("\n\t", " ").strip()
    check("harness: both definitions exist", bool(shared) and bool(attached),
          (shared[:120], attached[:120]))
    check("harness: the scoped sibling differs only by -i",
          attached.replace(" -i ", " ", 1) == shared,
          (shared[:300], attached[:300]))
    check("harness: the shared seam keeps the #1496 literal flags",
          '-v "$(GIT_COMMON_DIR):$(GIT_COMMON_DIR)"' in shared
          and "-e SELF_ARCHIVE_BASELINE" in shared
          and "-e SELF_ARCHIVE_REF" in shared, shared[:300])


def test_the_guard_detectors_accept_the_scoped_redactor_only() -> None:
    """The real no-bare-host and secret-output guards still see the live seam."""
    import check_no_bare_host_python as detector
    import check_secret_output as cso

    makefile = (ROOT / "Makefile").read_text(encoding="utf-8")
    findings, _count = detector.violations(makefile)
    check("guard: the real tree has no bare-host finding", not findings, findings)
    check("guard: the scoped harness is a recognised container seam",
          "$(PYTHON_RUN_STDIN)" in detector.HARNESS_TOKENS, detector.HARNESS_TOKENS)
    check("secret-scan: the live stream seam is still detected",
          cso.seam_redacts(makefile) and cso.seam_streams(makefile), "")
    check("secret-scan: no bare host redactor was left behind",
          not re.search(r"\|\s*python3 scripts/scrub_log\.py", makefile), "")


def main() -> int:
    print("scrub-log stdin attach: real seam, real redactor (issue #1810)")
    test_the_shipped_seam_captures_and_redacts_a_delayed_agent()
    test_the_pre_change_harness_loses_every_line()
    test_a_silent_agent_is_not_retried_and_the_verdict_stays_put()
    test_a_red_producer_keeps_its_own_status_through_the_attached_pipe()
    test_the_two_harnesses_carry_the_same_flags()
    test_the_guard_detectors_accept_the_scoped_redactor_only()
    print(f"\nPASSED {PASSED} | FAILED {FAILED}")
    return 1 if FAILED else 0


if __name__ == "__main__":
    sys.exit(main())
