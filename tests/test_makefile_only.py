#!/usr/bin/env python3
"""ONE path: business logic goes through the Makefile, CI runs those targets, and tests do not
replace the system under test (AGENTS.md rule 6m).

Three properties, each with a real failure behind it:

 1. **A test never replaces the system under test.** A test that monkeypatches the function it
    claims to lock passes because the patch returned the wanted answer — it locks nothing. An
    EXTERNAL system may stand in (a local git remote, a local HTTP server, a stub `gh` on PATH);
    product code (anything defined under `scripts/`) may not.
 2. **Every workflow step goes through `make`.** A `run:` that reaches into `scripts/*.py` or calls
    `pytest` directly makes the command CI executed differ from the one you can run locally, and it
    bypasses the target that carries the repository's decisions.
 3. **A target a workflow calls exists, and the CI entry targets are actually called.** A `make`
    target nothing runs is green by never executing; a workflow calling a target that was renamed
    away fails only when that job happens to run.

Run: python3 tests/test_makefile_only.py   (wired into `make _test`)
"""
from __future__ import annotations

import ast
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MAKEFILE = (ROOT / "Makefile").read_text(encoding="utf-8")
WORKFLOWS = sorted((ROOT / ".github" / "workflows").glob("*.yml"))

PASSED = FAILED = 0


def check(name: str, ok: bool, detail: object = "") -> None:
    global PASSED, FAILED
    if ok:
        PASSED += 1
        print(f"  ok  {name}")
    else:
        FAILED += 1
        print(f"FAIL {name}  {detail}")


def make_targets() -> set[str]:
    """Every target the Makefile defines (the left side of `name:` at column 0)."""
    return set(re.findall(r"^([A-Za-z0-9_][A-Za-z0-9_.-]*):", MAKEFILE, re.M))


#: The targets that constitute the CI gate: every one MUST be called by a workflow, or the gate is
#: a promise the pipeline does not keep.
CI_ENTRY_TARGETS = ("test", "validate", "lint", "openspec-check", "architecture-check")


def product_symbols() -> dict[str, set[str]]:
    """`{module_stem: {top-level names}}` for every module under scripts/ — the product."""
    out: dict[str, set[str]] = {}
    for path in sorted((ROOT / "scripts").glob("*.py")):
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except SyntaxError:
            continue
        names = set()
        for node in tree.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                names.add(node.name)
            elif isinstance(node, ast.Assign):
                for t in node.targets:
                    if isinstance(t, ast.Name):
                        names.add(t.id)
        out[path.stem] = names
    return out


def test_a_test_does_not_replace_the_system_under_test() -> None:
    """No test patches, replaces or fakes a symbol the product defines."""

    # Given every module the product ships
    product = product_symbols()
    check("the product has modules worth protecting", bool(product), sorted(product)[:3])

    for path in sorted((ROOT / "tests").glob("test_*.py")):
        src = path.read_text(encoding="utf-8")

        # When  the file patches something by a `scripts.<module>.<symbol>` path
        for m in re.finditer(r"(?:patch|setattr)\s*\(\s*[\"']scripts\.([a-z_]+)\.([A-Za-z_][A-Za-z0-9_]*)",
                             src):
            module, symbol = m.group(1), m.group(2)
            # Then  it is a violation: that symbol IS the product
            check(f"{path.name}: does not patch scripts.{module}.{symbol}", False,
                  f"{path.name} replaces the system under test at scripts.{module}.{symbol}")

        # And a product symbol rebound to a mock is the same defect, spelled differently
        imported = set(re.findall(r"^from\s+scripts\.[a-z_]+\s+import\s+([A-Za-z_][A-Za-z0-9_]*)",
                                  src, re.M))
        imported |= set(re.findall(r"^import\s+scripts\.([a-z_]+)", src, re.M))
        for name in sorted(imported):
            if re.search(rf"^\s*{re.escape(name)}\s*=\s*(?:MagicMock|Mock|mock\.MagicMock)\s*\(",
                         src, re.M):
                check(f"{path.name}: does not rebind {name} to a mock", False, name)

    # And no test file even imports the mock machinery to patch the product this way
    check("no test patches a scripts.* symbol",
          not any(re.search(r"[\"']scripts\.[a-z_]+\.[A-Za-z_]", p.read_text(encoding="utf-8"))
                  and re.search(r"unittest\.mock|MagicMock", p.read_text(encoding="utf-8"))
                  for p in (ROOT / "tests").glob("test_*.py")),
          "a test replaces product code")


def test_every_workflow_step_goes_through_make() -> None:
    """A workflow `run:` may call `make`; it may not reach into the product itself."""

    # Given the workflow files
    check("there are workflows to check", bool(WORKFLOWS), [w.name for w in WORKFLOWS])

    #: A direct reach into the product from a `run:` block.
    direct = re.compile(r"(?:^|[\s;&|(])(?:python3?|bash|sh|\./)\s*[\"']?(?:\./)?"
                        r"(?:scripts|tests)/[A-Za-z0-9_./-]+"
                        r"|(?:^|[\s;&|(])(?:python3?\s+-m\s+)?pytest\b")

    for path in WORKFLOWS:
        hits = []
        for i, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            stripped = line.strip()
            if stripped.startswith("#") or "make " in stripped:
                continue
            if direct.search(stripped):
                hits.append(f"{path.name}:{i}: {stripped[:90]}")
        # Then  the workflow never bypasses the Makefile
        check(f"{path.name} reaches the product only through make", not hits, hits)


def test_workflows_only_call_targets_that_exist() -> None:
    """Every `make <target>` in a workflow names a target the Makefile defines."""

    # Given the Makefile's targets
    targets = make_targets()
    check("the Makefile defines targets", bool(targets), len(targets))

    #: A real target token: lowercase, hyphen-separated, no trailing hyphen (so the prose
    #: placeholder `make openspec-*` is not read as a target).
    target_token = re.compile(r"\bmake\s+(?:-C\s+\S+\s+)?([a-z][a-z0-9_]*(?:-[a-z0-9_]+)*)\b")

    called: set[str] = set()
    for path in WORKFLOWS:
        for line in path.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            # A comment or a printed message is prose about a target, not a call to one.
            if stripped.startswith("#") or "echo " in stripped:
                continue
            for m in target_token.finditer(stripped):
                called.add(m.group(1))

    # When  each called target is looked up
    missing = sorted(t for t in called if t not in targets)
    # Then  none is missing
    check("every target a workflow calls exists", not missing, missing)

    # And the CI gate itself is called by a workflow
    for target in CI_ENTRY_TARGETS:
        check(f"CI calls `make {target}`", target in called, sorted(called))


def test_every_target_the_ci_gate_calls_is_reachable_from_the_makefile() -> None:
    """The gate targets exist AND the workflows that run them are the ones CI triggers."""

    # Given the CI workflow (the PR pipeline)
    qa = ROOT / ".github" / "workflows" / "qa-validate.yml"
    check("qa-validate.yml exists", qa.exists(), qa)

    # When  its triggers are read
    text = qa.read_text(encoding="utf-8")
    # Then  it runs on pull_request and on push to master
    check("qa-validate runs on pull_request", "pull_request" in text)
    check("qa-validate runs on push", "push:" in text)
    # And it runs the gate through make, never a bare test runner
    check("qa-validate runs `make test`", "make test" in text)


def main() -> int:
    """Run every test in this file — a test defined but never called passes CI silently."""
    test_a_test_does_not_replace_the_system_under_test()
    test_every_workflow_step_goes_through_make()
    test_workflows_only_call_targets_that_exist()
    test_every_target_the_ci_gate_calls_is_reachable_from_the_makefile()
    print(f"\nPASSED {PASSED} | FAILED {FAILED}")
    return 1 if FAILED else 0


if __name__ == "__main__":
    sys.exit(main())
