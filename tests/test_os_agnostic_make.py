#!/usr/bin/env python3
"""The no-bare-host-python guard (#712 Slice 5, #1496) against the REAL Makefile and the REAL detector.

Three properties, each locking a measured gap:

 1. **The tree is green.** No public target outside the documented host-only exceptions reaches a
    bare host `python3`/`pip`/`uv` — through a recipe line, a `$(call …)` macro body (the redaction
    filter lives in one), a `$(shell …)` parse-time exec, or one make hop into a private recipe
    in BOTH spellings (`$(MAKE) … _x` and plain `make _x`; #1596).
 2. **The exception list is mechanical, not hand-waved.** The names mirrored in the Makefile's
    `HOST-EXCEPTIONS-BEGIN/END` block are EXACTLY `check_no_bare_host_python.EXCEPTIONS`, and every
    one of them names a target that really exists — a typo'd or removed exception is loud.
 3. **The detector bites.** Fed the PRE-CHANGE seam shapes (a bare
    `python3 scripts/scrub_log.py` inside `scrubbed_run`, a bare `$(shell python3 …)`) it reports
    them. That is the RED half of "proven RED against the pre-change tree", so reverting either
    seam cannot pass silently while this module is green.
 4. **The pip-tools console scripts are tokens too (#1593).** A planted `pip-compile …` / bare
    `pip-tools …` in a NON-exception PUBLIC target is reported naming target + line, while the REAL
    private recipes that carry them (`_requirements`, `_generate-requirements`) stay GREEN because
    their only entry is a `$(DOCKER_RUN) make _x` hop — both polarities in one pair.
 5. **BOTH hop spellings are followed (#1596).** The reachability half of the same guard: a private
    recipe reached through a PUBLIC target's PLAIN `make _x` hop is walked exactly like one reached
    through `$(MAKE) … _x`. Pre-#1596 the matcher saw only the recursive spelling, so a bare host
    interpreter planted in such a private recipe exited 0 INVISIBLE — the failure mode #1496 set out
    to close, reintroduced by copying the file's own dominant idiom. The harnessed forms stay GREEN
    for the right reason: those hops run inside a container.

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


def test_the_detector_sees_the_pip_tools_console_scripts_and_keeps_them_harnessed() -> None:
    """Property 3b (#1593): the pip-tools console scripts are tokens, and their recipes stay green.

    RED half: a planted `pip-compile …` / bare `pip-tools …` in a NON-exception PUBLIC target is
    reported naming target + line. Pre-#1593 the alternation carried only `python3|pip|uv`, so the
    trailing `-` lookahead rejected `pip-compile` and the whole guard exited 0 INVISIBLE.
    GREEN half: the REAL repo recipes that carry those commands (`_requirements`,
    `_generate-requirements`) are private and reached only through a `$(DOCKER_RUN) make _x` hop,
    so `requirements`/`generate-requirements` walk to [] and the tree stays clean for the right
    reason (containerised), not because the token set cannot see them.
    """
    module = scanner()

    # The token set itself: each pip-tools console script is its OWN word, and the near-miss
    # spellings the old regex deliberately excluded still do NOT match.
    for token in ("pip-compile", "pip-sync", "pip-tools"):
        check(f"tokens: `{token}` is an interpreter token",
              module.INTERP_RE.search(token) is not None, module.INTERP_RE.pattern)
    for false_friend in ("python3.12", "my-python3", "scripts/pip"):
        check(f"tokens: `{false_friend}` is not an interpreter token",
              not module.INTERP_RE.search(false_friend), module.INTERP_RE.pattern)

    # RED: planted into a non-exception public target, named with target + line.
    planted = (
        ".PHONY: search-smoke\n"
        "search-smoke:\n"
        "\tpip-compile --quiet --output-file x.txt requirements.in\n"
        "\tpip-tools --version\n"
    )
    findings, _count = module.violations(planted)
    check("red(#1593): a planted bare `pip-compile` in a non-exception public target is reported",
          any(f.target == "search-smoke" and f.token == "pip-compile" for f in findings),
          [str(f) for f in findings])
    check("red(#1593): a planted bare `pip-tools` in a non-exception public target is reported",
          any(f.target == "search-smoke" and f.token == "pip-tools" for f in findings),
          [str(f) for f in findings])
    check("red(#1593): the finding names the offending line number",
          sorted({f.line for f in findings}) == [3, 4],
          [(f.target, f.line, f.token) for f in findings])

    # GREEN: the SAME idiom behind a harness seam is clean, on a synthetic pair.
    harnessed = (
        ".PHONY: requirements\n"
        "requirements:\n"
        "\t$(DOCKER_RUN) make _requirements\n"
        ".PHONY: _requirements\n"
        "_requirements:\n"
        "\tpip install --quiet pip-tools\n"
        "\tpip-compile --quiet --output-file requirements.txt requirements.in\n"
    )
    targets, macros = module.parse_makefile(harnessed)
    check("green(#1593): `requirements` (harnessed hop) walks to no finding",
          not module.walk("requirements", targets, macros),
          [str(f) for f in module.walk("requirements", targets, macros)])
    check("green(#1593): the containerised pair reports nothing at all",
          not module.violations(harnessed)[0], module.violations(harnessed)[0])

    # And the REAL tree's three recipes are private + harnessed exactly as documented, so the
    # widened token set does not red the current gate.
    real_targets, real_macros = module.parse_makefile(MAKEFILE_TEXT)
    for private in ("_requirements", "_generate-requirements", "_requirements-test"):
        check(f"green(#1593): `{private}` is a private target (not scanned as public)",
              private.startswith("_") and private not in module.public_targets(real_targets),
              private)
    for public in ("requirements", "generate-requirements"):
        check(f"green(#1593): `{public}` walks to no finding on the real tree",
              not module.walk(public, real_targets, real_macros),
              [str(f) for f in module.walk(public, real_targets, real_macros)])
        check(f"green(#1593): `{public}` carries its hop inside a container harness",
              "$(DOCKER_RUN) make _" in MAKEFILE_TEXT.split(f"\n{public}:", 1)[1].split("\n\n", 1)[0],
              "the public wrapper no longer routes the private recipe through $(DOCKER_RUN)")


def test_the_guard_follows_both_hop_spellings_into_private_recipes() -> None:
    """Property 3c (#1596): a plain `make _x` hop is walked, and its harnessed twin stays green.

    RED half: the exact live shape the reviewer measured on merged master — a bare
    `python3 scripts/query_vocab.py --print nvidia` planted in `_setup`, with the PUBLIC
    `search-smoke` target exposing it through ONE plain `make _setup` hop. Pre-#1596 `HOP_RE`
    matched only `$(MAKE) … _x`, so the whole plain-hop class (`_refresh`'s seven hops,
    `_setup`'s registers) was invisible and this exited 0.
    GREEN half: the same private recipe reached through `$(DOCKER_RUN) make _setup` is clean,
    because that hop already runs inside the container — the suppression the guard has always had,
    applied to BOTH spellings.
    """
    module = scanner()

    # The matcher itself: both spellings resolve to the private target name.
    for spelling, line in (
        ("plain", "\t@echo \"== _setup ==\"; make _setup || exit 1\n"),
        ("plain+flags", "\tmake --no-print-directory -j4 _search-nvidia\n"),
        ("recursive", "\t$(MAKE) --no-print-directory _setup\n"),
    ):
        hops = []
        for match in module.HOP_RE.finditer(line):
            groups = match.groups()
            if len(groups) > 1 and groups[-1]:
                hops.append(groups[-1])
        check(f"hop: the {spelling} spelling matches the private target", hops != [], line)

    # RED: the planted bare interpreter behind a PLAIN hop from a public target is DETECTED,
    # naming the public target and the private recipe's line.
    planted_plain = (
        ".PHONY: search-smoke\n"
        "search-smoke:\n"
        "\t@echo \"== _setup ==\"; make _setup || exit 1\n"
        ".PHONY: _setup\n"
        "_setup:\n"
        "\tpython3 scripts/query_vocab.py --print nvidia\n"
    )
    findings, _count = module.violations(planted_plain)
    check("red(#1596): a bare host python reached through a PLAIN `make _setup` hop is reported",
          any(f.target == "search-smoke" and f.token == "python3" for f in findings),
          [str(f) for f in findings])
    check("red(#1596): the finding names the private recipe's physical line",
          sorted({f.line for f in findings}) == [6],
          [(f.target, f.line, f.token) for f in findings])

    # The SAME tree with the recursive spelling is detected identically — one behaviour, two spellings.
    planted_recursive = planted_plain.replace("make _setup || exit 1", "$(MAKE) --no-print-directory _setup")
    recursive_findings, _ = module.violations(planted_recursive)
    check("red(#1596): the SAME private recipe reached through `$(MAKE) … _setup` is reported",
          any(f.target == "search-smoke" and f.token == "python3" for f in recursive_findings),
          [str(f) for f in recursive_findings])

    # GREEN: the harnessed twin of each spelling is suppressed for the right reason (container).
    for spelling, hop in (
        ("plain", "\t$(DOCKER_RUN) make _setup\n"),
        ("recursive", "\t$(DOCKER_RUN) sh -c \"make _setup\"\n"),
    ):
        harnessed = (
            ".PHONY: search-smoke\n"
            "search-smoke:\n"
            f"{hop}"
            ".PHONY: _setup\n"
            "_setup:\n"
            "\tpython3 scripts/query_vocab.py --print nvidia\n"
        )
        targets, macros = module.parse_makefile(harnessed)
        check(f"green(#1596): the harnessed {spelling} hop walks to no finding",
              not module.walk("search-smoke", targets, macros),
              [str(f) for f in module.walk("search-smoke", targets, macros)])

    # END-TO-END on the REAL tree, in the issue's exact shape: plant the bare command in the real
    # `_setup` recipe and expose it from the PUBLIC `search-smoke` through ONE plain `make _setup`
    # hop. Measured by the reviewer on merged master `c7fa437e`: the pre-change guard exits 0
    # INVISIBLE here; the fixed guard must exit 1. The copy is written to a temp Makefile so the
    # checkout is untouched (`--makefile`), which is the same seam `main()` uses.
    import tempfile
    planted_tree = MAKEFILE_TEXT.replace(
        ".PHONY: search-smoke\nsearch-smoke:\n\t$(DOCKER_RUN) make _search-smoke\n",
        ".PHONY: search-smoke\nsearch-smoke:\n\tmake _setup || exit 1\n", 1)
    marker = ".PHONY: _setup\n_setup:\n"
    head = planted_tree.index(marker) + len(marker)
    lines = planted_tree[head:].split("\n")
    skip = 0
    while skip < len(lines) and (not lines[skip].strip() or lines[skip].strip().startswith("@#")):
        skip += 1
    cut = head + sum(len(x) + 1 for x in lines[:skip])
    planted_tree = (planted_tree[:cut]
                    + "\tpython3 scripts/query_vocab.py --print nvidia\n"
                    + planted_tree[cut:])
    check("red(#1596): the planted tree really carries a plain public hop into `_setup`",
          "make _setup || exit 1" in planted_tree and "_setup:" in planted_tree, "")
    with tempfile.TemporaryDirectory() as tmp:
        planted_make = Path(tmp) / "Makefile"
        planted_make.write_text(planted_tree, encoding="utf-8")
        run = subprocess.run([sys.executable, str(ROOT / "scripts" / "check_no_bare_host_python.py"),
                              "--makefile", str(planted_make)],
                             capture_output=True, text=True)
    check("red(#1596): the CLI exits 1 on the real tree with a plain-hop-planted bare host python",
          run.returncode == 1, (run.returncode, run.stdout[-300:], run.stderr[-200:]))
    check("red(#1596): the CLI names the public target and the private line",
          "search-smoke" in run.stdout and "query_vocab" in run.stdout, run.stdout[-300:])

    # The SAME planted tree with the harnessed spelling stays green — suppression still holds.
    with tempfile.TemporaryDirectory() as tmp:
        harness_make = Path(tmp) / "Makefile"
        harness_make.write_text(
            planted_tree.replace("\tmake _setup || exit 1\n", "\t$(DOCKER_RUN) make _setup\n", 1),
            encoding="utf-8")
        run = subprocess.run([sys.executable, str(ROOT / "scripts" / "check_no_bare_host_python.py"),
                              "--makefile", str(harness_make)],
                             capture_output=True, text=True)
    check("green(#1596): the harnessed twin of the same planted tree exits 0",
          run.returncode == 0, (run.returncode, run.stdout[-300:]))

    # And the REAL tree: every one of the file's plain hops is now followed, while the 50 hops a
    # public target makes through a harness stay suppressed. Measured here so a future narrowing
    # of HOP_RE cannot quietly restore the hole. The walk starts at PUBLIC targets; a hop made by
    # a private recipe (`_refresh`'s own chain, `_setup`'s registers) is reachable only through a
    # PUBLIC wrapper (`refresh`/`setup`, both harnessed), so those lines are asserted through the
    # matcher rather than as direct findings.
    real_targets, _real_macros = module.parse_makefile(MAKEFILE_TEXT)
    plain_hops = []
    for target in sorted(real_targets):
        for lineno, raw in module.logical_lines(real_targets[target]):
            stripped = raw.strip()
            if not stripped or stripped.startswith("#"):
                continue
            if any(token in raw for token in module.HARNESS_TOKENS):
                continue
            for match in module.HOP_RE.finditer(raw.lstrip("@")):
                groups = match.groups()
                hop = groups[-1] if groups else None
                if not hop or raw.lstrip("@")[match.start():].startswith("$(MAKE"):
                    continue
                plain_hops.append((target, hop))
    check("real-tree(#1596): the Makefile's non-harnessed plain hops are present and walked",
          len(plain_hops) > 0, plain_hops)
    check("real-tree(#1596): the repo's own dominant idiom drives the private refresh chain",
          ("_refresh", "_setup") in plain_hops, sorted(plain_hops))
    # `_setup`'s two `$(MAKE) … _hermes-skills-*` registers are the SAME hop class with the
    # recursive spelling; the recursive matcher covers them (the guard walks `_setup` whenever a
    # public target reaches it), so this pins that both spellings resolve to the same name.
    for register in ("_hermes-skills-register", "_hermes-skills-check"):
        line = f"\t$(MAKE) --no-print-directory {register}\n"
        found = []
        for match in module.HOP_RE.finditer(line):
            groups = match.groups()
            if len(groups) > 1 and groups[-1]:
                found.append(groups[-1])
        check(f"real-tree(#1596): `{register}` is a reachable private target through the recursive hop",
              found == [register], line)
        check(f"real-tree(#1596): `{register}` really exists as a Makefile target",
              register in real_targets, sorted(t for t in real_targets if t.startswith("_hermes")))


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
    test_the_detector_sees_the_pip_tools_console_scripts_and_keeps_them_harnessed()
    test_the_guard_follows_both_hop_spellings_into_private_recipes()
    test_the_guard_is_wired_into_lint_and_reachable()
    print(f"\nPASSED {PASSED} | FAILED {FAILED}")
    return 1 if FAILED else 0


if __name__ == "__main__":
    sys.exit(main())
