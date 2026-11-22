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


def pre_change_blob(sha: str, path: str) -> str | None:
    """The source at an IMMUTABLE `sha`, or None when it cannot be resolved.

    A regression guard proves itself RED on the pre-change code. Reading that code from
    a MOVING ref (`origin/master`) fails in BOTH directions (issue #1292): on a full
    clone the ref already carries the feature, so the negative assertion is a false red,
    and in a checkout with no such ref `git show` answers EMPTY, so the assertion passes
    vacuously and locks nothing. A pinned SHA is present in every clone whose history
    reaches the change (the guard's SHA is the parent of the feature commit).

    `None` is a LOUD failure at the call site — never an empty string that a negative
    assertion could pass on.

    `safe.directory` is passed on the COMMAND LINE (never written to a config file): the
    test container runs as the image's default user (uid 0, issue #1147) while the bind-mounted
    checkout is owned by the invoking uid, so a bare `git show` dies `detected dubious
    ownership` — which is a SECOND way the probe could answer nothing and read as a pass.
    """
    proc = subprocess.run(
        ["git", "-C", str(ROOT), "-c", f"safe.directory={ROOT}",
         "show", f"{sha}:{path}"],
        capture_output=True, text=True)
    return proc.stdout if proc.returncode == 0 else None
