#!/usr/bin/env python3
"""The OpenSpec archive seam leaves no text file without a final newline.

Drives the REAL `scripts/openspec_archive_newline.py` against a planted archive
dir (no external system, no stand-in for the code under test) and pins that the
`openspec-archive` Makefile recipe calls it AFTER the CLI archive (issue #1782).
Wired into `make test` (rule 6d).
"""

from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "scripts" / "openspec_archive_newline.py"
MAKEFILE = ROOT / "Makefile"

_PASS = 0
_FAIL = 0


def check(name: str, cond: bool, detail: str = "") -> None:
    global _PASS, _FAIL
    if cond:
        _PASS += 1
        print(f"  ok  {name}")
    else:
        _FAIL += 1
        print(f"  FAIL {name}" + (f"  [{detail}]" if detail else ""))


def _run(root: Path, name: str = "demo") -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), "--name", name, "--root", str(root)],
        capture_output=True,
        text=True,
    )


def test_the_seam_repairs_a_planted_no_newline_archive() -> None:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        archive = root / "openspec" / "changes" / "archive" / "demo"
        archive.mkdir(parents=True)
        bad = archive / ".openspec.yaml"
        bad.write_bytes(b"schema: spec-driven\ncreated: 2026-11-26")
        good = archive / "proposal.md"
        good.write_bytes(b"# Proposal\n\nIssue: #1782\n")
        first = _run(root)
        check("seam exits 0 on a planted no-newline archive", first.returncode == 0, first.stderr)
        check("the .openspec.yaml gained exactly one 0x0a",
              bad.read_bytes() == b"schema: spec-driven\ncreated: 2026-11-26\n")
        check("an already-correct file is byte-identical",
              good.read_bytes() == b"# Proposal\n\nIssue: #1782\n")
        second = _run(root)
        check("second run is a no-op (idempotent)",
              second.returncode == 0 and bad.read_bytes().endswith(b"\n")
              and bad.read_bytes().count(b"\n") == 2, repr(bad.read_bytes()))


def test_binary_empty_and_nested_files_are_untouched() -> None:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        archive = root / "openspec" / "changes" / "archive" / "demo" / "nested"
        archive.mkdir(parents=True)
        binary = archive / "blob.bin"
        binary.write_bytes(b"\x00\x01no-newline")
        empty = archive / "empty.txt"
        empty.write_bytes(b"")
        nested_bad = archive / "note.md"
        nested_bad.write_bytes(b"note without newline")
        run = _run(root)
        check("binary file untouched", binary.read_bytes() == b"\x00\x01no-newline")
        check("empty file untouched", empty.read_bytes() == b"")
        check("nested text file repaired", nested_bad.read_bytes() == b"note without newline\n")
        check("nested repair is announced", "note.md" in run.stdout, run.stdout)


def test_a_date_prefixed_archive_dir_is_found() -> None:
    """The CLI date-prefixes the archive dir; the seam must still find it."""
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        archive = root / "openspec" / "changes" / "archive" / "2026-11-26-demo"
        archive.mkdir(parents=True)
        yaml = archive / ".openspec.yaml"
        yaml.write_bytes(b"schema: spec-driven\ncreated: 2026-11-26")
        run = _run(root)
        check("date-prefixed archive is resolved", run.returncode == 0, run.stderr)
        check("date-prefixed archive file repaired", yaml.read_bytes().endswith(b"\n"))
        check("date-prefixed repair is announced", "2026-11-26-demo" in run.stdout, run.stdout)


def test_a_missing_archive_dir_is_refused() -> None:
    with tempfile.TemporaryDirectory() as td:
        run = _run(Path(td), name="absent")
        check("missing archive dir exits non-zero", run.returncode != 0, str(run.returncode))
        check("refusal names the missing path", "REFUSED" in run.stderr and "absent" in run.stderr, run.stderr)


def test_the_archive_recipe_wires_the_seam() -> None:
    src = MAKEFILE.read_text(encoding="utf-8")
    lines = src.splitlines()
    start = next((i for i, line in enumerate(lines) if line.startswith("openspec-archive:")), None)
    check("openspec-archive recipe exists", start is not None)
    if start is None:
        return
    block: list[str] = []
    for line in lines[start + 1:]:
        if line and not line.startswith(("\t", " ")):
            break
        block.append(line)
    body = "\n".join(block)
    check("recipe invokes the newline seam", "scripts/openspec_archive_newline.py" in body, body)
    check("CLI archive is called before the seam",
          "openspec archive $(NAME) -y" in body
          and body.index("openspec archive $(NAME) -y") < body.index("scripts/openspec_archive_newline.py"), body)


if __name__ == "__main__":
    test_the_seam_repairs_a_planted_no_newline_archive()
    test_binary_empty_and_nested_files_are_untouched()
    test_a_date_prefixed_archive_dir_is_found()
    test_a_missing_archive_dir_is_refused()
    test_the_archive_recipe_wires_the_seam()
    print(f"PASSED {_PASS} | FAILED {_FAIL}")
    sys.exit(1 if _FAIL else 0)
