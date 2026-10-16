#!/usr/bin/env python3
"""No tracked Python module raises a `SyntaxWarning` (issue #190).

`scripts/update_trending.py` carried a single unescaped backslash in its module
docstring — the text git prints for a file with no final newline — so importing
it raised ``SyntaxWarning: "\\ " is an invalid escape sequence`` on every run. The warning
was invisible: `make lint` checked only the final newline, `make validate` never
compiled a module, and the suite imported the module after the warning had
already scrolled past. PEP 686's warning path ends in an error in a future
Python, so this is a latent break, not a style nit — and a real warning in the
same stream is easy to miss.

    make lint-syntax          # fail closed: name every module that warns on compile
    python3 scripts/lint_syntax.py --root DIR   # check a fixture tree

The file set is what git tracks (`git ls-files '*.py'`), so a generated or
untracked file can never fail the lint and a new module is covered the moment it
is added. Each file is compiled from source with `SyntaxWarning` turned into an
error, so the check sees exactly the warning the interpreter would raise — it
never imports the module, so a module's import side effects cannot run here. A
file that fails to parse is reported too. Pure stdlib, so host and container
agree.

Wired into `make lint` (the first step of `qa-validate`'s `validate` job and the
first check in `scripts/fix_loop.sh`) and into `make test` through
`tests/test_lint_syntax.py` (rule 6d).

Usage:
    python3 scripts/lint_syntax.py               # check the repository (exit 1 on a finding)
    python3 scripts/lint_syntax.py --root DIR    # check a fixture tree
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import warnings
from pathlib import Path


def tracked_python_files(root: Path) -> list[str]:
    """The tracked ``*.py`` files of *root* (via git), sorted; [] when git cannot answer.

    ``-c safe.directory=*`` because the suite runs this inside a container as root
    over host-owned files: without it git refuses to answer ("detected dubious
    ownership") and a false red would be reported for a correct tree.
    """
    out = subprocess.run(
        ["git", "-c", "safe.directory=*", "-C", str(root), "ls-files", "*.py"],
        capture_output=True, text=True,
    )
    if out.returncode != 0:
        return []
    return sorted(line for line in out.stdout.splitlines() if line.strip())


def _compile_warnings(path: Path) -> list[str]:
    """Every `SyntaxWarning`/`SyntaxError` compiling *path*, as human strings."""
    try:
        src = path.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        return [f"could not read: {exc}"]
    findings: list[str] = []
    # A `SyntaxWarning` is shown once per (file, line) by default; when this very
    # script is the offender its warning was already emitted at import, so the
    # registry must be cleared or the re-compile would be silent.
    globals().pop("__warningregistry__", None)
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        try:
            compile(src, str(path), "exec")
        except SyntaxError as exc:
            findings.append(f"SyntaxError: {exc.msg} (line {exc.lineno})")
        except ValueError as exc:  # e.g. source with a NUL byte
            findings.append(f"ValueError: {exc}")
        for w in caught:
            if issubclass(w.category, SyntaxWarning):
                findings.append(f"SyntaxWarning: {w.message}")
    return findings


def offenders(root: Path) -> dict[str, list[str]]:
    """Map every tracked module that warns/fails on compile to its findings."""
    bad: dict[str, list[str]] = {}
    for name in tracked_python_files(root):
        findings = _compile_warnings(root / name)
        if findings:
            bad[name] = findings
    return bad


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="No tracked Python module raises a SyntaxWarning")
    ap.add_argument("--root", default=str(Path(__file__).resolve().parents[1]))
    a = ap.parse_args(argv)

    root = Path(a.root)
    files = tracked_python_files(root)
    if not files:
        print(f"[lint-syntax] no tracked .py files under {root} (not a git checkout?)", file=sys.stderr)
        return 1

    bad = offenders(root)
    if bad:
        print(f"[lint-syntax] FAIL {len(bad)} tracked module(s) do not compile cleanly:", file=sys.stderr)
        for name in sorted(bad):
            for finding in bad[name]:
                print(f"[lint-syntax]   - {name}: {finding}", file=sys.stderr)
        print("[lint-syntax] escape the sequence (a raw string or a doubled backslash) "
              "so the module imports without a SyntaxWarning", file=sys.stderr)
        return 1

    print(f"[lint-syntax] OK every one of {len(files)} tracked modules compiles without a SyntaxWarning")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
