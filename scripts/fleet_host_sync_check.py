#!/usr/bin/env python3
"""Check a Hermes fleet profile home against the FETCHED upstream base (issue #1209).

The issue thread is the shared board across machines. That only works when every
host runs the SAME lane behaviour: a host one protocol behind follows different
rules and can claim the same issue as an updated host. This seam compares the real
`~/.hermes/profiles/<lane>/` bytes with the blobs in a resolved git base -- never
with the working tree, so local unmerged work cannot launder a stale host -- and
checks that the rulebook still carries the tll lifecycle shapes.

Exit: 0 clean, 1 divergence found, 2 undecidable (bad base, missing tree/home).
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

LANES = (
    "tll-planner",
    "tll-architect",
    "tll-security",
    "tll-reviewer",
    "tll-implementer",
    "tll-tester",
    "tll-pr-rebase",
)

# The rulebook markers the fleet's behaviour hangs on. Every one must be present in
# AGENTS.md AT THE BASE -- a rule dropped from the rulebook is a divergence too.
RULEBOOK_MARKERS = (
    "TLL fleet — lifecycle, delegation and divergence gate",
    "Comment on the issue BEFORE you do the work.",
    "working on #<id>",
    "done #<id> · handover",
    "· reviewing #<id>",
    "fleet-host-sync-check",
    "tests/test_fleet_lifecycle.py",
)


def _git(root: Path, *argv: str) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(
        ["git", "-C", str(root), *argv], capture_output=True, check=False
    )


def _blob(root: Path, base: str, path: str) -> bytes:
    got = _git(root, "show", f"{base}:{path}")
    if got.returncode:
        raise ValueError(f"cannot read {base}:{path}")
    return got.stdout


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", required=True, help="resolved git ref, e.g. origin/master")
    parser.add_argument("--root", default=None, help="repository root")
    parser.add_argument("--profiles-home", default=None, help="profile home (default: ~/.hermes/profiles)")
    parser.add_argument("--expect-ref", default=None, help="refuse unless --base resolves to this ref")
    args = parser.parse_args(argv)

    root = Path(args.root).resolve() if args.root else Path(__file__).resolve().parent.parent
    home = (
        Path(args.profiles_home).expanduser().resolve()
        if args.profiles_home
        else (Path.home() / ".hermes" / "profiles").resolve()
    )
    resolved = _git(root, "rev-parse", "--verify", f"{args.base}^{{commit}}")
    if resolved.returncode:
        print(f"[fleet-sync] REFUSED: base {args.base!r} is not a commit in {root}")
        return 2
    base_sha = resolved.stdout.decode().strip()
    if args.expect_ref:
        expected = _git(root, "rev-parse", "--verify", f"{args.expect_ref}^{{commit}}")
        if expected.returncode or expected.stdout.decode().strip() != base_sha:
            print(
                f"[fleet-sync] REFUSED: base {base_sha} is not {args.expect_ref} "
                "-- fetch upstream before checking the fleet"
            )
            return 2
    if not home.is_dir():
        print(f"[fleet-sync] REFUSED: no profile home at {home}")
        return 2

    failed = 0
    for lane in LANES:
        for rel in ("SOUL.md", f"skills/{lane}/SKILL.md", "config.yaml"):
            repo_path = f"agents/{lane}/{rel}"
            try:
                expected = _blob(root, base_sha, repo_path)
            except ValueError:
                print(f"[fleet-sync] FAIL {base_sha}:{repo_path} missing at base")
                failed += 1
                continue
            actual = home / lane / rel
            if not actual.is_file():
                print(f"[fleet-sync] FAIL {lane}/{rel} missing in {home}")
                failed += 1
            elif actual.read_bytes() != expected:
                print(f"[fleet-sync] FAIL {lane}/{rel} diverges from {base_sha}")
                failed += 1

    try:
        rulebook = _blob(root, base_sha, "AGENTS.md").decode("utf-8")
    except ValueError:
        print(f"[fleet-sync] FAIL {base_sha}:AGENTS.md missing at base")
        failed += 1
    else:
        for marker in RULEBOOK_MARKERS:
            if marker not in rulebook:
                print(f"[fleet-sync] FAIL AGENTS.md@{base_sha} dropped {marker!r}")
                failed += 1

    if failed:
        print(f"[fleet-sync] FAIL {failed} divergence(s) against {base_sha} ({base_sha[:12]})")
        return 1
    print(
        f"[fleet-sync] OK: base {base_sha}, {len(LANES)} lane(s) and the AGENTS.md "
        "lifecycle markers match upstream"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
