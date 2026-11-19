#!/usr/bin/env python3
"""ONE teardown for a temp Hermes home (issue #1145, found by raising the pin to Hermes 0.23.2).

Hermes does not stop writing when its CLI exits. Measured on the host with the pinned 0.23.2: a
single `hermes config set` against a temp HERMES_HOME seeded `cache/uv/**`, `installs/<hash>` and
`cache/default-plugins.rerun` -> `cache/default-plugins.settled` into that home 4 s AFTER the CLI
call had returned. `tempfile.TemporaryDirectory`'s cleanup then races that seeding pass and dies

    OSError: [Errno 39] Directory not empty: '/tmp/tmpw_nr72tu/hermes/cache'

which made `make test` RED in CI's own qa-validate job (run 44537216542, module
`tests/test_agent_skills.py`) and on the host, with every assertion in the module already green:
the check proved nothing because the teardown failed on the agent's own bookkeeping.

The seam therefore removes a Hermes home through a BOUNDED retry, and a tree that never becomes
removable is a LOUD failure (AssertionError), never an ignored one — `ignore_errors=True` would
launder a real defect. Used by every test that points Hermes at a temp home
(`tests/test_agent_skills.py`, `tests/test_agent_shell_keys.py` — one implementation, rule 6d).
"""
from __future__ import annotations

import contextlib
import shutil
import tempfile
import time
from pathlib import Path

# 40 x 0.25 s = 10 s of grace: the measured seeding pass settles in well under a second, and a
# bounded wait is what keeps a genuinely stuck tree a failure instead of a hang.
SEED_SETTLE_ATTEMPTS = 40
SEED_SETTLE_DELAY_S = 0.25


def remove_hermes_home(path: Path, attempts: int = SEED_SETTLE_ATTEMPTS,
                       delay: float = SEED_SETTLE_DELAY_S) -> None:
    """Remove a temp Hermes home, tolerating the agent's background seeding.

    Loud if it never becomes removable: the retry is for the agent's own late writes, not an
    excuse to swallow a real undeletable tree.
    """
    last: OSError | None = None
    for _ in range(attempts):
        try:
            shutil.rmtree(path)
            return
        except OSError as exc:
            last = exc
            time.sleep(delay)
    raise AssertionError(f"temp Hermes home {path} never became removable: {last}")


@contextlib.contextmanager
def temp_hermes_home():
    """A temp dir used as HERMES_HOME, removed through the agent's late-write window."""
    td = Path(tempfile.mkdtemp())
    try:
        yield td
    finally:
        remove_hermes_home(td)
