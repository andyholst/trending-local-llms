#!/usr/bin/env python3
"""Register the checkout's `.hermes/skills` with Hermes, so `hermes -s <name>` resolves (issue #549).

Every agent leg preloads its contract with `hermes -s <name>` instead of carrying 1000-2000
characters of rules inline (`.hermes/skills/<name>/SKILL.md`). Hermes looks for skills in its own
home and in `skills.external_dirs`, so the repository's skill directory has to be registered in the
agent container's Hermes home — once, at setup time, before any leg runs.

Why this goes THROUGH the CLI instead of editing `config.yaml`: the repo's Python has no PyYAML (its
`requirements.txt` is jsonschema only), so a hand-rolled writer would either need a new dependency in
the agent image or guess at YAML. `hermes config get` / `hermes config set` is the tool that owns the
file, it is already installed in every image that runs a leg, and the version pinned there
(`hermes-agent` 0.22.3) reads a JSON array back as a real list — verified by reading it back here,
which is the check this script performs either way.

Usage:
    python3 scripts/hermes_skills_register.py --home <hermes home> --dir <repo>/.hermes/skills
    python3 scripts/hermes_skills_register.py --home <hermes home> --dir <…> --check

Exit codes: 0 registered (or `--check` found it), 1 not registered (`--check` only),
2 no `hermes` CLI, an unreadable/unwritable config, or a directory that does not exist — never a
silent pass.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

KEY = "skills.external_dirs"


def _hermes(home: Path, *args: str) -> subprocess.CompletedProcess:
    env = dict(os.environ, HERMES_HOME=str(home))
    try:
        return subprocess.run(["hermes", *args], capture_output=True, text=True, env=env)
    except FileNotFoundError:
        print("[hermes-skills] the `hermes` CLI is not on PATH — the config cannot be read or "
              "written (run this inside the agent image)", file=sys.stderr)
        raise SystemExit(2) from None


def read_dirs(home: Path) -> list[str]:
    """`skills.external_dirs` as a plain list, read through the CLI that owns the config."""
    p = _hermes(home, "config", "get", KEY)
    if p.returncode != 0:
        print(f"[hermes-skills] `hermes config get {KEY}` failed: "
              f"{(p.stderr or p.stdout).strip()[:300]}", file=sys.stderr)
        raise SystemExit(2)
    out = p.stdout.strip()
    if out in ("", "[]"):
        return []
    dirs: list[str] = []
    for line in out.splitlines():
        line = line.strip()
        if line.startswith("- "):
            dirs.append(line[2:].strip().strip("'\""))
        elif line.startswith("["):
            # a one-line JSON array, from a version that prints it compactly
            try:
                parsed = json.loads(line)
            except ValueError:
                continue
            dirs.extend(str(d) for d in parsed if isinstance(d, str))
    return dirs


def write_dirs(home: Path, dirs: list[str]) -> None:
    p = _hermes(home, "config", "set", KEY, json.dumps(dirs))
    if p.returncode != 0:
        print(f"[hermes-skills] `hermes config set {KEY}` failed: "
              f"{(p.stderr or p.stdout).strip()[:300]}", file=sys.stderr)
        raise SystemExit(2)


def _same(a: str, b: str) -> bool:
    return Path(a).expanduser().resolve() == Path(b).expanduser().resolve()


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description="Register the checkout's .hermes/skills with Hermes so `hermes -s` resolves")
    ap.add_argument("--home", default=os.environ.get("HERMES_HOME") or str(Path.home() / ".hermes"),
                    help="the Hermes home (default: $HERMES_HOME or ~/.hermes)")
    ap.add_argument("--dir", required=True, help="the skills directory to register")
    ap.add_argument("--check", action="store_true", help="verify only; write nothing")
    args = ap.parse_args(argv)

    home = Path(args.home).expanduser()
    target = Path(args.dir).expanduser()
    if not target.is_dir():
        print(f"[hermes-skills] {target} is not a directory — the checkout carries no skills to "
              f"register", file=sys.stderr)
        return 2
    resolved = str(target.resolve())

    current = read_dirs(home)
    if any(_same(d, resolved) for d in current):
        print(f"[hermes-skills] ok: {resolved} is registered in {home} ({KEY})")
        return 0
    if args.check:
        print(f"[hermes-skills] FAIL: {resolved} is not in {KEY} of {home} "
              f"(have: {current or 'none'}) — `hermes -s <name>` would not resolve for any bot leg",
              file=sys.stderr)
        return 1
    write_dirs(home, current + [resolved])
    back = read_dirs(home)
    if not any(_same(d, resolved) for d in back):
        print(f"[hermes-skills] FAIL: wrote {home} but read back {back}", file=sys.stderr)
        return 2
    print(f"[hermes-skills] registered {resolved} in {home} ({KEY} = {back})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
