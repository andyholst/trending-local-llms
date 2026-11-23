#!/usr/bin/env python3
"""The ONE python-env seam forks inside a container (issue #1411).

#712 Slice 3 routes `pr-title`, `pr-body` and `architecture-pr-body` through
`python-env-image` + `$(PYTHON_RUN)`. A routed recipe cannot be exercised from inside
the docker-less test image while the seam names `docker run`, so the SAME assignment
carries an `$(if $(IN_CONTAINER),…)` fork: on a host it is the pinned harness plus the
image-ensure step; inside a container it is EMPTY and the ensure is skipped silently.

These probes drive the REAL `make` (no stand-ins): the dry-run expansion, the silent
escape, and the three `ARCHITECTURE.md` prose rows the routing leaves stale.

Run:  python3 tests/test_python_env_in_container.py   or   make test
"""
from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

_PASS = 0
_FAIL = 0


def check(name: str, ok: bool, detail: object = "") -> None:
    global _PASS, _FAIL
    if ok:
        _PASS += 1
        print(f"  ok  {name}")
    else:
        _FAIL += 1
        print(f"FAIL {name}  {detail}")


def _make(*args: str, in_container: bool | None = None) -> subprocess.CompletedProcess:
    """Run the REAL `make` in the repo root.

    `in_container` pins the seam's fork explicitly: True forces `IN_CONTAINER=1`,
    False forces it EMPTY (so a docker-less container cannot flip the default), and
    None leaves it to the Makefile's own `/.dockerenv` detection.
    """
    env = dict(os.environ, MAKEFLAGS="--no-print-directory")
    if in_container is None:
        env.pop("IN_CONTAINER", None)
    else:
        env["IN_CONTAINER"] = "1" if in_container else ""
    return subprocess.run(["make", *args], cwd=ROOT, capture_output=True, text=True, env=env)


def test_the_seam_expands_differently_inside_a_container() -> None:
    issue = "287"

    # Given  the HOST path (IN_CONTAINER forced empty)
    host = _make("-n", "pr-body", f"ISSUE={issue}", in_container=False)
    check("seam: the host dry-run keeps the docker harness",
          host.returncode == 0 and "docker run" in host.stdout,
          host.stdout[:400] + host.stderr[-200:])
    check("seam: the host dry-run keeps the image-ensure step",
          "ensure_image.py ensure-python" in host.stdout, host.stdout[:400])
    check("seam: the host dry-run still ends in the pure composer command",
          "python3 scripts/pr_body.py" in host.stdout, host.stdout[:400])

    # When   the same expansion runs INSIDE a container
    inner = _make("-n", "pr-body", f"ISSUE={issue}", in_container=True)
    # Then   no docker and no ensure appear, and the pure command remains
    check("seam: the in-container dry-run drops the docker harness",
          inner.returncode == 0 and "docker run" not in inner.stdout,
          inner.stdout[:400] + inner.stderr[-200:])
    check("seam: the in-container dry-run drops the image-ensure step",
          "ensure_image.py ensure-python" not in inner.stdout, inner.stdout[:400])
    check("seam: the in-container dry-run keeps the pure composer command",
          "python3 scripts/pr_body.py" in inner.stdout, inner.stdout[:400])


def test_the_escape_branch_is_silent() -> None:
    p = _make("python-env-image", in_container=True)
    check("escape: the in-container ensure exits 0", p.returncode == 0,
          p.stdout + p.stderr)
    check("escape: the in-container ensure writes NOTHING to stdout",
          p.stdout == "", repr(p.stdout))


def test_the_host_ensure_recipe_is_silent() -> None:
    """Issue #1457: on the HOST branch the ensure prerequisite must not reach fd 1.

    `make -n` prints the command text (it ignores `@`), so the dry-run proves the stdout
    REDIRECTION; the Makefile source proves the `@`. Both are required: `@` alone still
    lets `ensure_image.py`'s own print through to a redirected artifact.
    """
    issue = "287"
    host = _make("-n", "pr-body", f"ISSUE={issue}", in_container=False)
    lines = [l for l in host.stdout.splitlines() if "ensure_image.py ensure-python" in l]
    check("seam: the host dry-run keeps exactly one ensure step", len(lines) == 1,
          host.stdout[:400])
    check("seam: the host ensure step moves its stdout off fd 1",
          bool(lines) and re.search(r">&2|>/dev/null", lines[0]) is not None, lines)

    src = (ROOT / "Makefile").read_text(encoding="utf-8")
    block = src.split("python-env-image:", 1)[1].split("\nelse", 1)[0]
    recipe = next((l.strip() for l in block.splitlines()
                   if "ensure_image.py ensure-python" in l), "")
    check("seam: the host ensure recipe is @-prefixed (no make echo)",
          recipe.startswith("@"), recipe)


def test_the_description_no_longer_calls_the_composers_host_targets() -> None:
    doc = (ROOT / "ARCHITECTURE.md").read_text(encoding="utf-8")
    check("description: no row says pr-body runs on the runner's own python3",
          "Runs on the runner's own `python3`" not in doc, "")
    check("description: no keeper row calls architecture-pr-body a host target",
          "host target, like `architecture-pr-body`" not in doc, "")
    row = next((line for line in doc.splitlines() if line.startswith("| `pr-body`")), "")
    check("description: the pr-body row names the python-env seam",
          "python-env-image" in row, row)


def main() -> int:
    print("python-env seam in-container fork (issue #1411)")
    test_the_seam_expands_differently_inside_a_container()
    test_the_escape_branch_is_silent()
    test_the_host_ensure_recipe_is_silent()
    test_the_description_no_longer_calls_the_composers_host_targets()
    print(f"\nPASSED {_PASS} | FAILED {_FAIL}")
    return 1 if _FAIL else 0


if __name__ == "__main__":
    raise SystemExit(main())
