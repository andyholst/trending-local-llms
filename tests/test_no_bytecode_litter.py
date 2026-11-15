#!/usr/bin/env python3
"""issue #839 — `make test` must not litter the checkout with bytecode copies.

The measured source (issue #836): the host's `make test` left
`tests/__pycache__/test_secret_scan.cpython-312.pyc` — a BYTECODE COPY of a test
module that embeds planted FAKE credentials — and `make secret-scan` went red
re-reading a `.pyc` no commit could ever carry. The scan side classifies by what
git could commit; THIS guard locks the littering side: the ONE test runner
(`scripts/run_tests.sh`, reached from `make test` through `_test:`) runs with
`PYTHONDONTWRITEBYTECODE=1`, proven end to end by the real mechanism: a planted
probe module that IMPORTS a helper (the exact shape that wrote
`tests/__pycache__/wiring.cpython-312.pyc`).

Contract (rule 6m): the REAL runner is executed against a scratch tests dir —
no mocks. The control run proves the mechanism really produces `__pycache__`
bytecode without the flag (so this guard FAILS on the pre-fix runner), and the
runner run proves it produces none and stays green.
"""
from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RUNNER = ROOT / "scripts" / "run_tests.sh"

PASSED = 0
FAILED: list[str] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    global PASSED
    if ok:
        PASSED += 1
        print(f"  ok  {name}")
    else:
        FAILED.append(name)
        print(f"  FAIL {name}  {detail}")


def scratch_tree() -> Path:
    """A tests dir whose module IMPORTS a sibling helper — the real litter shape."""
    d = Path(tempfile.mkdtemp(prefix="no-bytecode-litter-"))
    (d / "planted_helper.py").write_text(
        '# imported by the probe; a credential SHAPE (fake) so its bytecode copy '
        'is exactly the junk issue #836 measured\nFAKE_TOKEN = "ghp_" + "x" * 36\n',
        encoding="utf-8",
    )
    (d / "test_planted_probe.py").write_text(
        "import os, sys\n"
        "sys.path.insert(0, os.path.dirname(__file__))\n"
        "import planted_helper  # the import that wrote tests/__pycache__/wiring.pyc\n"
        "print('ok planted probe', planted_helper.FAKE_TOKEN[:4])\n",
        encoding="utf-8",
    )
    return d


def run(cmd: list[str]) -> subprocess.CompletedProcess:
    e = dict(os.environ)
    # Never inherit a value set by THIS guard process; the runner must own it.
    e.pop("PYTHONDONTWRITEBYTECODE", None)
    return subprocess.run(cmd, capture_output=True, text=True, env=e, timeout=300)


def test_a_helper_import_under_bare_python3_does_litter():
    """Control: the planted mechanism is real — without the flag litter appears
    (this guard fails on the pre-fix runner)."""
    d = scratch_tree()
    try:
        r = run([sys.executable, str(d / "test_planted_probe.py")])
        littered = list(d.rglob("__pycache__"))
        check("control: importing a helper under bare python3 DOES litter __pycache__",
              r.returncode == 0 and bool(littered),
              f"rc={r.returncode} dirs={littered}")
    finally:
        subprocess.run(["rm", "-rf", str(d)])


def test_the_runner_is_green_and_leaves_no_pycache():
    """The REAL runner over the SAME tree: green, trace line present, zero litter."""
    d = scratch_tree()
    try:
        r = run(["bash", str(RUNNER), str(d)])
        littered = list(d.rglob("__pycache__"))
        check("runner: green suite over an importing probe module",
              r.returncode == 0,
              (r.stdout + r.stderr)[-400:])
        check("runner: the per-module trace still arrives (issue #911 contract intact)",
              "[test] ok test_planted_probe.py" in r.stdout, r.stdout[-300:])
        check("runner: leaves NO __pycache__ anywhere under the tests dir",
              not littered, str(littered))
    finally:
        subprocess.run(["rm", "-rf", str(d)])


def test_the_seam_owns_the_flag_and_the_only_path():
    """One export in the runner covers every caller (container `_test:`, host,
    direct invocation), and `make test` still reaches the suite ONLY through it
    (rule 6m)."""
    runner_text = RUNNER.read_text(encoding="utf-8")
    check("seam: run_tests.sh exports PYTHONDONTWRITEBYTECODE=1",
          "export PYTHONDONTWRITEBYTECODE=1" in runner_text, "")
    check("wiring: `make test` still reaches the suite ONLY through the runner (rule 6m)",
          "bash scripts/run_tests.sh" in (ROOT / "Makefile").read_text(encoding="utf-8"), "")


def main() -> int:
    test_a_helper_import_under_bare_python3_does_litter()
    test_the_runner_is_green_and_leaves_no_pycache()
    test_the_seam_owns_the_flag_and_the_only_path()
    print(f"PASSED {PASSED} | FAILED {len(FAILED)}")
    return 0 if not FAILED else 1


if __name__ == "__main__":
    sys.exit(main())
