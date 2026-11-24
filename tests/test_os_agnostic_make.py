#!/usr/bin/env python3
"""The no-bare-host-python guard (#712 Slice 5, #1496) against the REAL Makefile and the REAL detector.

Three properties, each locking a measured gap:

 1. **The tree is green.** No public target outside the documented host-only exceptions reaches a
    bare host `python3`/`pip`/`uv` — through a recipe line, a `$(call …)` macro body (the redaction
    filter lives in one), a `$(shell …)` parse-time exec, or one bare `$(MAKE) _x` hop.
 2. **The exception list is mechanical, not hand-waved.** The names mirrored in the Makefile's
    `HOST-EXCEPTIONS-BEGIN/END` block are EXACTLY `check_no_bare_host_python.EXCEPTIONS`, and every
    one of them names a target that really exists — a typo'd or removed exception is loud.
 3. **The detector bites.** Fed the PRE-CHANGE seam shapes (a bare
    `python3 scripts/scrub_log.py` inside `scrubbed_run`, a bare `$(shell python3 …)`) it reports
    them. That is the RED half of "proven RED against the pre-change tree", so reverting either
    seam cannot pass silently while this module is green.

Nothing here mocks product code: the suite imports the real `scripts/check_no_bare_host_python.py`
and reads the real `Makefile` (AGENTS.md rule 6m).

Run: python3 tests/test_os_agnostic_make.py   (wired into `make _test`)
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MAKEFILE = ROOT / "Makefile"
MAKEFILE_TEXT = MAKEFILE.read_text(encoding="utf-8")

PASSED = FAILED = 0


def check(name: str, ok: bool, detail: object = "") -> None:
    global PASSED, FAILED
    if ok:
        PASSED += 1
        print(f"  ok  {name}")
    else:
        FAILED += 1
        print(f"FAIL {name}  {detail}")


def scanner():
    """Import the REAL detector (one place, like every other test module)."""
    sys.path.insert(0, str(ROOT / "scripts"))
    import check_no_bare_host_python as module
    return module


def documented_exceptions(makefile_text: str) -> set[str]:
    """The names the Makefile mirrors between its HOST-EXCEPTIONS markers."""
    block = re.search(r"#\s*HOST-EXCEPTIONS-BEGIN\n(.*?)#\s*HOST-EXCEPTIONS-END",
                      makefile_text, re.S)
    if not block:
        return set()
    return set(re.findall(r"`([a-z0-9][a-z0-9-]*)`", block.group(1)))


def test_the_real_tree_has_no_bare_host_invocation_outside_the_exceptions() -> None:
    """Property 1: the guard is green on THIS tree, through its real CLI and its real functions."""
    module = scanner()

    findings, public_count = module.violations(MAKEFILE_TEXT)
    check("no-bare-host-python: the real Makefile is clean", not findings, findings)
    check("no-bare-host-python: the scan saw the public targets (non-vacuous)",
          public_count > 100, public_count)

    # End-to-end: the same script as `make check-no-bare-host-python` runs it.
    run = subprocess.run([sys.executable, str(ROOT / "scripts" / "check_no_bare_host_python.py"),
                          "--root", str(ROOT)], capture_output=True, text=True)
    check("no-bare-host-python: the CLI exits 0 on the real tree", run.returncode == 0,
          (run.returncode, run.stdout[-400:], run.stderr[-400:]))
    check("no-bare-host-python: the CLI prints its verdict",
          "[no-bare-host-python] OK" in run.stdout, run.stdout[-200:])


def test_the_documented_exception_list_agrees_with_the_scanner() -> None:
    """Property 2: the Makefile mirror and EXCEPTIONS are the SAME set, and each name is a target."""
    module = scanner()
    documented = documented_exceptions(MAKEFILE_TEXT)
    declared = set(module.EXCEPTIONS)

    check("exceptions: the Makefile mirror is present", bool(documented),
          "no HOST-EXCEPTIONS-BEGIN/END block in the Makefile")
    check("exceptions: the Makefile mirror and EXCEPTIONS agree exactly",
          documented == declared,
          f"only in Makefile: {sorted(documented - declared)[:8]} | "
          f"only in EXCEPTIONS: {sorted(declared - documented)[:8]}")

    targets, _macros = module.parse_makefile(MAKEFILE_TEXT)
    public = set(module.public_targets(targets))
    missing = sorted(n for n in declared if n not in public)
    check("exceptions: every documented exception names a real PUBLIC target", not missing, missing)


def test_the_two_cross_cutting_seams_run_through_the_container_seam() -> None:
    """Property 1b: the two #1496 seams are containerised, and their targets are NOT excepted."""
    module = scanner()

    # The redaction filter is a `python3` too: it runs at the redactor end of the pipeline through
    # the ONE python-env seam, never wrapped around the agent leg it filters.
    check("seam: scrubbed_run pipes through $(PYTHON_RUN)",
          "$(PYTHON_RUN) python3 scripts/scrub_log.py" in MAKEFILE_TEXT,
          "the redaction filter no longer runs through the python-env seam")
    check("seam: scrubbed_run has no bare host redactor left",
          not re.search(r"\|\s*python3 scripts/scrub_log\.py", MAKEFILE_TEXT),
          "a bare `| python3 scripts/scrub_log.py` is back in scrubbed_run")

    # The parse-time execs: all five go through the seam (recursive, so still lazy).
    shell_execs = re.findall(r"^\w+ = \$\(shell ([^\n]*)\)$", MAKEFILE_TEXT, re.M)
    query_shells = [s for s in shell_execs if "query_" in s]
    check("seam: the parse-time query execs exist and are the five expected",
          len(query_shells) == 5, query_shells)
    check("seam: every parse-time query exec goes through $(PYTHON_RUN)",
          all("$(PYTHON_RUN)" in s for s in query_shells), query_shells)

    # The search pre-flight proves the credential through the same seam (PYTHON_RUN forwards the
    # name), so `make search-*` starts no host interpreter before the agent container.
    check("seam: _search-preflight runs require_env through $(PYTHON_RUN)",
          "@$(PYTHON_RUN) python3 scripts/require_env.py FIRECRAWL_API_KEY" in MAKEFILE_TEXT,
          "the search credential pre-flight is back on the host interpreter")

    # And none of the nine targets those seams used to expose is hiding behind an exception.
    for target in ("fix", "implement-issue", "review-issue", "review-issue-window",
                   "search", "search-nvidia", "search-metal", "search-cpu", "search-amd"):
        check(f"seam: {target} is not in the exception list", target not in module.EXCEPTIONS,
              "a containerised target was added to the host-only exceptions")


def test_the_detector_is_red_on_the_pre_change_seam_shapes() -> None:
    """Property 3: the RED half — the pre-change shapes are reported, so a revert cannot pass."""
    module = scanner()

    pre_change = (
        "PYTHON_RUN := docker run --rm -v \"$PWD\":/workspace -w /workspace img\n"
        "MODEL_QUERIES = $(shell python3 scripts/query_coverage.py --queries 2>/dev/null)\n"
        "\n"
        "define scrubbed_run\n"
        "\t@bash -o pipefail -c 'eval \"$$1\" 2>&1 | python3 scripts/scrub_log.py --stream' _ '$(1)'\n"
        "endef\n"
        "\n"
        ".PHONY: fix\n"
        "fix:\n"
        "\t$(call scrubbed_run,$(DOCKER_RUN) sh -c \"make _fix\")\n"
    )
    findings, _count = module.violations(pre_change)
    check("red: the pre-change tree produces findings", bool(findings), findings)
    check("red: the bare redactor inside the macro is reported (not laundered by the caller's harness)",
          any(f.target == "fix" and "scrub_log" in f.text for f in findings),
          [str(f) for f in findings])
    check("red: the bare $(shell python3 …) parse-time exec is reported",
          any(f.target == "<$(shell)>" and "query_coverage" in f.text for f in findings),
          [str(f) for f in findings])

    # The SAME shapes, containerised, are clean — the GREEN half of the pair.
    fixed = pre_change.replace("| python3 scripts/scrub_log.py", "| $(PYTHON_RUN) python3 scripts/scrub_log.py")
    fixed = fixed.replace("$(shell python3 scripts/query_coverage.py",
                          "$(shell $(PYTHON_RUN) python3 scripts/query_coverage.py")
    fixed_findings, _ = module.violations(fixed)
    check("green: the containerised shapes are clean", not fixed_findings, fixed_findings)


def test_the_guard_is_wired_into_lint_and_reachable() -> None:
    """Property 1c: `make lint` actually runs the guard, and the public target exists."""
    lint_block = MAKEFILE_TEXT.split("\nlint:", 1)
    check("wiring: the lint target exists", len(lint_block) == 2, "no `lint:` target")
    if len(lint_block) == 2:
        block = lint_block[1].split("\n\n", 1)[0]
        check("wiring: make lint runs check-no-bare-host-python",
              "$(MAKE) --no-print-directory check-no-bare-host-python" in block, block)
    check("wiring: the public target exists",
          re.search(r"^check-no-bare-host-python:", MAKEFILE_TEXT, re.M) is not None,
          "no check-no-bare-host-python target")
    check("wiring: the guard script exists",
          (ROOT / "scripts" / "check_no_bare_host_python.py").is_file(), "")


def main() -> int:
    """Run every test in this file — a test defined but never called passes CI silently."""
    test_the_real_tree_has_no_bare_host_invocation_outside_the_exceptions()
    test_the_documented_exception_list_agrees_with_the_scanner()
    test_the_two_cross_cutting_seams_run_through_the_container_seam()
    test_the_detector_is_red_on_the_pre_change_seam_shapes()
    test_the_guard_is_wired_into_lint_and_reachable()
    print(f"\nPASSED {PASSED} | FAILED {FAILED}")
    return 1 if FAILED else 0


if __name__ == "__main__":
    sys.exit(main())
