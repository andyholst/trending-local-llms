#!/usr/bin/env python3
"""coverage_gap.py — ONE definition of the suite's identity line and its declared-gap seam (issue #1147).

Two facts this exists for, both measured in this repository's own CI:

1. `make test` claims "136 modules green", and the runner never said WHOSE uid it
   measured. `TEST_RUN` (Makefile) passes no `--user`, so the test container runs as the
   image's default user — measured `id -u` = 0 in `tll-test-3965-16821` — while the host
   `scripts/run_tests.sh` already assumes the invoking uid. Which identity produced a green
   verdict was invisible in the verdict.

2. The permission half of `tests/test_agent_skills.py`'s stuck-tree teardown guard prints
   `SKIP teardown: permission plant bypassed (uid 0 — DAC_OVERRIDE walks a mode-0o000 dir)`
   and returns, so the module exits 0 — measured in CI: qa-validate run 44551541279 removed
   the planted mode-0o000 tree (the container is uid 0) and the guard itself then died on its
   own cleanup `chmod`. An rc=0 green suite carried a half-covered guard and nothing in the
   verdict said so; the coverage gap was invisible to every reader of a green run.

So this module owns, ONCE (rule 6d — the runner, the plant guard and the tests all read these
strings here and never re-spell them):

* `IDENTITY_PREFIX` / `identity_line()` — the line `scripts/run_tests.sh` prints, naming the uid
  the suite actually measured and the uid that invoked `make test`.
* `GAP_PREFIX` — the line a guard prints when a filesystem state it planted is NOT honoured, so
  the verdict names the half that ran and the half that could not.
* `BYPASS_PHRASE` — the phrase the runner hunts for in a module's output: a bypass reported WITHOUT
  the `GAP_PREFIX` seam is a refusal, because a silent half-coverage is the defect.
"""
from __future__ import annotations

import os
import shutil
import sys
from collections.abc import Sequence

GAP_PREFIX = "[coverage-gap]"
IDENTITY_PREFIX = "[harness] suite identity:"
BYPASS_PHRASE = "permission plant bypassed"


def identity_line() -> str:
    """The line the suite prints about WHO measured it.

    `TLL_INVOKING_UID` is set by `scripts/docker_test_run.sh` (the seam that starts every
    TEST_RUN container) to the uid:gid of whoever ran `make test`, and the container's own
    `id -u` is read here — so one line states both halves: the invoker and the identity the
    assertions actually ran under.
    """
    uid, gid = os.getuid(), os.getgid()
    invoker = os.environ.get("TLL_INVOKING_UID", "unset")
    if invoker == "unset":
        # Nothing was forwarded: say exactly that, rather than claiming an identity nobody named.
        run_as = "unknown (no invoking uid forwarded)"
    elif invoker == f"{uid}:{gid}":
        run_as = "invoking uid"
    else:
        run_as = "image default user, NOT the invoking uid"
    return (f"{IDENTITY_PREFIX} container uid={uid} gid={gid} "
            f"invoking uid={invoker} run-as={run_as}")


def declare_gap(guard: str, reason: str) -> str:
    """Print the ONE declared-coverage-gap line and return it."""
    line = f"{GAP_PREFIX} {guard}: {reason}"
    print(line)
    return line


def declare_bypass_gap(guard: str, why: str) -> str:
    """A guard whose planted filesystem state was NOT honoured declares the gap.

    The `BYPASS_PHRASE` travels INSIDE the declared line on purpose: the runner can then tell a
    bypass that named its coverage gap (green, reported) from a bypass that only printed a SKIP
    (red), because the difference is the GAP_PREFIX on the line, not the wording.
    """
    return declare_gap(
        guard,
        f"uid {os.getuid()} — {why}; {BYPASS_PHRASE} by the OS privilege model, so this half "
        f"did not run in this identity (the always-checked half still locks its contract)",
    )


def external_binary_usable(binary: str) -> bool:
    """Is `binary` on PATH? Presence is PRESUMED usability (issue #1172) — the seam never runs it.

    The boundary this names: `external_binary_gap` declares a half ONLY when the binary is
    ABSENT. A binary that is PRESENT but broken — a stale install, a broken venv, a version
    mismatch — is NOT declared: the module runs its real half and goes red with the CLI's own
    error, which is the honest signal. A broken tool is a defect in the half that drives it, not
    a coverage gap the verdict should absorb, and a green suite must not be able to hide one.

    The probe deliberately does not EXECUTE the binary either: running an arbitrary CLI to decide
    coverage is a side effect at import time, and it would move a real failure into the gap class
    this seam exists to keep separate.
    """
    return shutil.which(binary) is not None


#: The boundary as a named constant, so a guard can pin it rather than restate it.
PRESENCE_IS_PRESUMED_USABLE = True


def external_binary_gap(guard: str, binary: str | Sequence[str], why: str) -> str:
    """A guard whose half needs an EXTERNAL binary this identity does not have (issue #1154).

    The owner directive of 2026-11-15 moved agent work onto the host, so a host `make test` is
    the only local verification an implementation run has — and a module that drives a real
    CLI (the `hermes` skills register, a smoke) went RED with the CLI's own "not on PATH"
    message, a failure the pipeline would never report and one an agent then spends its repair
    budget on. The half is declared here: the runner prints `[harness] coverage-gap N declared`
    naming the guard that did not run, the module stays green, and a module that merely prints
    "SKIP" without this seam is still a refusal (the `BYPASS_PHRASE` travels inside the line).

    `binary` is ONE name or a SEQUENCE of them (issue #1171): a module that drives several CLIs
    declares them in ONE line, naming only the ones THIS identity lacks. The seam probes, so a
    module may call it unconditionally — when every binary is present it prints nothing and
    returns `""`, and the guard's own half runs.

    PRESENCE is the only thing probed (issue #1172): a binary that IS on PATH but fails is a REAL
    failure of the half that drives it, never a declared gap. See `external_binary_usable`.
    """
    names = [binary] if isinstance(binary, str) else list(binary)
    missing = [b for b in names if not external_binary_usable(b)]
    if not missing:
        return ""
    listed = ", ".join(f"`{b}`" for b in missing)
    verb = "s are" if len(missing) > 1 else " is"
    return declare_gap(
        guard,
        f"the {listed} CLI{verb} not on PATH ({why}); {BYPASS_PHRASE}: this half did not run in "
        f"this identity, and the container run — where the binary exists — still locks it",
    )


def scan_module_output(lines) -> tuple[list[str], list[str]]:
    """Split one module's output into (declared gaps, undeclared bypass lines)."""
    declared: list[str] = []
    undeclared: list[str] = []
    for line in lines:
        line = line.rstrip("\n")
        if line.startswith(GAP_PREFIX + " "):
            declared.append(line[len(GAP_PREFIX) + 1:])
        elif BYPASS_PHRASE in line:
            undeclared.append(line)
    return declared, undeclared


def main(argv: list[str]) -> int:
    """Print one of the shared strings, so a shell reader never re-spells it (rule 6d)."""
    flags = {"--gap-prefix": GAP_PREFIX, "--phrase": BYPASS_PHRASE, "--identity-line": identity_line()}
    if len(argv) != 1 or argv[0] not in flags:
        print(f"usage: coverage_gap.py {{{'|'.join(flags)}}}", file=sys.stderr)
        return 2
    print(flags[argv[0]])
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
