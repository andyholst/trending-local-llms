#!/usr/bin/env python3
"""Fail when a Makefile knob (`NAME ?= …`) is declared and read by nothing (issue #630).

A `?=` knob is the shape an OPERATOR sets: `NAME=200 make <target>`. When nothing in the tree
reads it, the operator's act changes nothing and says nothing — measured with `HERMES_LOG_TAIL`:
the seam went LIVE (`--stream`, issue #591) and stopped passing `--tail`, yet the knob stayed
declared, so `HERMES_LOG_TAIL=200` silently changed nothing for months while looking like the
bound on what a round printed. A knob that looks live and is not is worse than no knob, and
nothing in the suite noticed, because the only tests mentioning it defined their OWN copy inside
a fixture.

The refused shape: any top-level `NAME ?=` in the Makefile whose name appears NOWHERE else in
the runner's own tree — the Makefile recipes, `scripts/`, `.github/workflows/`, the Dockerfiles,
`skills/` and `.hermes/skills/`. Deliberate exclusions:

  * the definition line itself;
  * comment-only lines (a knob documented to death is still unread);
  * `tests/**` — a test that re-declares the knob in a fixture tree proves nothing about the
    real Makefile (that is exactly the cover the old knob had);
  * `openspec/**` — change records are history, not readers.

Usage:
    python3 scripts/check_makefile_knobs.py [--makefile PATH] [--root DIR]

Exit: 0 = every declared knob has a reader, 1 = at least one DEAD KNOB (file:line named),
2 = the Makefile is missing or unreadable (never a silent clean).
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

#: Top-level override knobs: `NAME ?= …` at column 0 (a Makefile `?=` assignment).
KNOB_RE = re.compile(r"^([A-Z][A-Z0-9_]{2,}) \?=", re.M)

#: Only these parts of the tree can READ a knob (the runner's own code paths).
READER_GLOBS = (
    "Makefile",
    "Makefile.*",
    "scripts/**/*.py",
    "scripts/**/*.sh",
    ".github/workflows/*.yml",
    ".github/workflows/*.yaml",
    "Dockerfile",
    "Dockerfile.*",
    "skills/**/*.md",
    ".hermes/skills/**/*.md",
)

#: Never readers: fixtures (tests/) and history (openspec/).
EXCLUDED_PREFIXES = ("tests/", "openspec/", "data/")


def knob_definitions(makefile_text: str) -> list[tuple[str, int]]:
    out: list[tuple[str, int]] = []
    for m in KNOB_RE.finditer(makefile_text):
        line = makefile_text[: m.start()].count("\n") + 1
        out.append((m.group(1), line))
    return out


def _is_comment(line: str) -> bool:
    return line.lstrip().startswith("#")


def use_patterns(name: str) -> list[re.Pattern[str]]:
    """The spellings that are actual USES of a knob, not prose that mentions it.

    A bare word in a docstring or a comment is not a read — that is exactly the false cover
    `HERMES_LOG_TAIL` had. Only these shapes move a value: the make expansions `$(NAME)` /
    `${NAME}`, the shell forms `$NAME` / `${NAME}`, a real environment read in a Python
    script (`os.environ["NAME"]`, `os.environ.get("NAME"…)`, `getenv("NAME"…`), a YAML `NAME:`
    key (a workflow env entry), and a Dockerfile `ARG NAME`.
    """
    return [
        re.compile(rf"\$\({re.escape(name)}\)"),
        re.compile(rf"\$\{{{re.escape(name)}\}}"),
        re.compile(rf"\${re.escape(name)}\b"),
        re.compile(rf"\benviron\.get\(\s*[\"']{re.escape(name)}"),
        re.compile(rf"\benviron\[\s*[\"']{re.escape(name)}[\"']\s*\]"),
        re.compile(rf"\bgetenv\(\s*[\"']{re.escape(name)}"),
        re.compile(rf"^[ \t]*{re.escape(name)}:", re.M),
        re.compile(rf"\bARG\s+{re.escape(name)}\b"),
    ]


def reader_files(root: Path) -> list[Path]:
    files: list[Path] = []
    for pattern in READER_GLOBS:
        for path in root.glob(pattern):
            if not path.is_file():
                continue
            rel = path.relative_to(root).as_posix()
            if rel.startswith(EXCLUDED_PREFIXES):
                continue
            files.append(path)
    return files


def check(makefile_path: Path, root: Path) -> int:
    if not makefile_path.is_file():
        print(f"[makefile-knobs] FATAL: no Makefile to scan at {makefile_path} — "
              "a gate that cannot read its input must fail loudly, never clean.",
              file=sys.stderr)
        return 2
    try:
        text = makefile_path.read_text()
    except OSError as exc:
        print(f"[makefile-knobs] FATAL: cannot read {makefile_path}: {exc}", file=sys.stderr)
        return 2

    knobs = knob_definitions(text)
    if not knobs:
        print("[makefile-knobs] OK: the Makefile declares no override knobs.")
        return 0

    files = reader_files(root)
    # A guard may not cite the knob it guards: prose in its own docstring is not a reader.
    files = [p for p in files if p.name != Path(__file__).name]
    dead: list[tuple[str, int]] = []
    for name, lineno in knobs:
        patterns = use_patterns(name)
        read = 0
        for path in files:
            try:
                text = path.read_text(errors="replace")
            except OSError:
                continue
            lines = text.splitlines()
            for i, line in enumerate(lines, 1):
                if _is_comment(line):
                    continue
                # the knob's own definition line in the Makefile is not a read
                if path == makefile_path and i == lineno:
                    continue
                if any(p.search(line) for p in patterns):
                    read += 1
                    break
            if read:
                break
        if read == 0:
            dead.append((name, lineno))

    if dead:
        for name, lineno in dead:
            print(f"DEAD KNOB: {makefile_path.name}:{lineno} declares `{name} ?=` and nothing in "
                  f"the runner's tree reads it — an operator setting {name}=… changes nothing, "
                  "silently. Wire it into a recipe or remove the definition (issue #630).")
        print(f"[makefile-knobs] FAIL: {len(dead)} declared knob(s) with no reader "
              f"(scanned {len(files)} reader files under {root}).", file=sys.stderr)
        return 1

    print(f"[makefile-knobs] OK: {len(knobs)} declared knob(s), every one read by the tree "
          f"(scanned {len(files)} reader files).")
    return 0


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    parser.add_argument("--makefile", default=None, help="the Makefile to scan (default: <root>/Makefile)")
    parser.add_argument("--root", default=None, help="the tree to search for readers (default: repo root)")
    args = parser.parse_args(argv)
    root = Path(args.root) if args.root else ROOT
    makefile = Path(args.makefile) if args.makefile else root / "Makefile"
    return check(makefile, root)


if __name__ == "__main__":
    sys.exit(main())
