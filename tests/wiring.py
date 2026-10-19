"""Is this module actually run by the suite? (issues #176 and #192)

`make test` used to carry a hand-maintained list of `python3 tests/test_*.py`
calls, so several suites asserted "my filename appears in the Makefile". That
made every new module a Makefile edit, and it is exactly the drift #192 records.

`scripts/run_tests.sh` DISCOVERS its modules, so the honest question is no longer
"is my name in the recipe" but "does the runner list me, and does `make test`
run the runner". `wired()` answers that by driving the real runner — no copy of
the discovery rule lives here.
"""
from __future__ import annotations

import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RUNNER = ROOT / "scripts" / "run_tests.sh"


def listed(path: str | Path | None = None) -> set[str]:
    """Every module the runner would run (basenames)."""
    out = subprocess.run(["bash", str(RUNNER), "--list"], cwd=str(ROOT),
                         capture_output=True, text=True)
    return {Path(line).name for line in out.stdout.split("\n") if line.strip()}


def wired(path: str | Path | None = None) -> bool:
    """The runner discovers this module AND `make test` runs the runner."""
    mk = (ROOT / "Makefile").read_text()
    name = Path(path).name if path else None
    return "_test:\n\tbash scripts/run_tests.sh" in mk and (name in listed(path) if name else True)
