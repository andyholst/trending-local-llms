#!/usr/bin/env python3
"""`make render-readme`: regenerate the README from the store, and NOTHING else (issue #195).

A template or docs change used to need `make merge`, which bumped
`data/models.json:generated_utc` and wrote a brand-new snapshot containing no new data —
store churn a review PR should not carry, indistinguishable from a real ingest.

These tests drive the REAL script against a copy of the real store in a temp directory
(`TRENDING_DATA_DIR` / `TRENDING_README`, the script's own seams) and assert what it does
and does not touch.

Run:  python3 tests/test_render_only.py   or   make test
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "scripts" / "update_trending.py"
MAKEFILE = ROOT / "Makefile"

_PASS = 0
_FAIL = 0


def check(name, cond, detail: object = ""):
    global _PASS, _FAIL
    if cond:
        _PASS += 1
        print(f"  ok  {name}")
    else:
        _FAIL += 1
        print(f"  FAIL {name}" + (f"  [{detail}]" if detail else ""))


def _fixture(td: Path) -> dict:
    """A copy of the real store + README, addressed through the script's own env seams."""
    data = td / "data"
    (data / "snapshots").mkdir(parents=True)
    shutil.copy(ROOT / "data" / "models.json", data / "models.json")
    shutil.copy(ROOT / "README.md", td / "README.md")
    return {**os.environ, "TRENDING_DATA_DIR": str(data), "TRENDING_README": str(td / "README.md")}


def _render(env: dict, *args: str):
    return subprocess.run([sys.executable, str(SCRIPT), "--render-only", *args],
                          cwd=ROOT, env=env, capture_output=True, text=True)


def test_render_only_touches_the_readme_and_nothing_else():
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        env = _fixture(td)
        store_before = (td / "data" / "models.json").read_bytes()
        readme_before = (td / "README.md").read_text()

        proc = _render(env)

        store_after = (td / "data" / "models.json").read_bytes()
        readme_after = (td / "README.md").read_text()
        snapshots = sorted((td / "data" / "snapshots").iterdir())

    check("render-only: exit 0", proc.returncode == 0, proc.stdout + proc.stderr)
    check("render-only: the store is NOT rewritten", store_before == store_after, "models.json changed")
    check("render-only: no snapshot is written", snapshots == [], [p.name for p in snapshots])
    check("render-only: it says what it did",
          "no store write, no snapshot" in proc.stdout, proc.stdout[-300:])
    # A re-run must be a NO-OP: the wall-clock "Last generated" line is kept, so a template
    # change does not churn the README either.
    check("render-only: re-running the same store changes nothing",
          readme_before == readme_after, "README differs")


def test_render_only_regenerates_a_stale_readme():
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        env = _fixture(td)
        original = (td / "README.md").read_text()
        # A hand-edited README (the case the gate refuses) is repaired from the store…
        (td / "README.md").write_text(original.replace("| Model |", "| Hand |", 1))

        proc = _render(env)
        repaired = (td / "README.md").read_text()

    check("render-only: a stale README exits 0", proc.returncode == 0, proc.stderr[-300:])
    check("render-only: … and is regenerated from the store", repaired == original,
          repaired[:200])


def test_render_only_keeps_the_last_generated_line():
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        env = _fixture(td)
        before = (td / "README.md").read_text()
        stamp = next(ln for ln in before.splitlines() if ln.startswith("> Last generated:"))

        _render(env)
        after = (td / "README.md").read_text()

    check("render-only: the README keeps its own 'Last generated' line",
          stamp in after.splitlines(), after.splitlines()[:12])


def test_the_target_is_wired_as_a_makefile_pair():
    mk = MAKEFILE.read_text()
    check("make: `_render-readme` runs the script's --render-only",
          "_render-readme:\n\tpython3 scripts/update_trending.py --render-only" in mk, "")
    check("make: `render-readme` is the docker wrapper of that recipe",
          "render-readme:\n\t$(DOCKER_RUN) make _render-readme" in mk, "")
    check("make: the target is documented in ARCHITECTURE.md",
          "render-readme" in (ROOT / "ARCHITECTURE.md").read_text(), "")


def main() -> int:
    print("render-only README (issue #195)")
    test_render_only_touches_the_readme_and_nothing_else()
    test_render_only_regenerates_a_stale_readme()
    test_render_only_keeps_the_last_generated_line()
    test_the_target_is_wired_as_a_makefile_pair()
    print(f"\nPASSED {_PASS} | FAILED {_FAIL}")
    return 1 if _FAIL else 0


if __name__ == "__main__":
    raise SystemExit(main())
