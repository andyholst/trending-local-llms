#!/usr/bin/env python3
"""Check a Hermes fleet profile home against the FETCHED upstream base (issue #1209).

The issue thread is the shared board across machines. That only works when every
host runs the SAME lane behaviour: a host one protocol behind follows different
rules and can claim the same issue as an updated host. This seam compares the real
`~/.hermes/profiles/<lane>/` bytes with the blobs in a resolved git base -- never
with the working tree, so local unmerged work cannot launder a stale host -- and
checks that the rulebook still carries the tll lifecycle shapes. A lane `config.yaml`
is compared by its OWNED blocks (`model`, `model_aliases`, `fallback_providers`), so
Hermes's runtime stamps are host state, not drift, while a stale owned byte still
reds (issue #1401).

Exit: 0 clean, 1 divergence found, 2 undecidable (bad base, missing tree/home).
"""
from __future__ import annotations

import argparse
import subprocess
import sys
import tempfile
from pathlib import Path

try:  # the ONE chain parser and the ONE drift verdict (rule 6d)
    from agent_model_chain import read_chain, render_text
    from agent_profile_provision import check_one as profile_drift
except ImportError:  # run from the repo root
    from scripts.agent_model_chain import read_chain, render_text
    from scripts.agent_profile_provision import check_one as profile_drift

LANES = (
    "tll-planner",
    "tll-architect",
    "tll-security",
    "tll-reviewer",
    "tll-implementer",
    "tll-tester",
    "tll-pr-rebase",
    "tll-docs",
)

# The TEXT mirrors compared byte-for-byte. `config.yaml` is deliberately absent: its OWNED
# blocks go through `agent_profile_provision.check_one` (issue #1401), so a second drift
# verdict for it is forbidden (#1198/#1204). `fleet_host_reconcile` imports this list --
# ONE definition of which files are compared (rule 6d).
# (issue #1860) The comparison set is MIRROR_RELS PLUS the ONE host rulebook. The rulebook is
# a single file at the PROFILES_HOME root (not per lane), compared against the repo-root
# AGENTS.md. `fleet_host_reconcile` imports all three names -- ONE definition of which files
# are compared, against which base, and which writes need an attended sign-off (rules 6d/3c).
RULEBOOK_REL = "AGENTS.md"
PROTECTED_RELS = (RULEBOOK_REL,)  # rule 3c: never silently overwrite a host instruction file
MIRROR_RELS = ("SOUL.md", "skills/{lane}/SKILL.md")

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

# Hermes stamps its own runtime metadata into every lane `config.yaml` on launch
# (`hermes_cli.config` writes `_config_version: <n>`, and the onboarding prompt writes
# `onboarding.seen.*`). Those keys are HOST RUNTIME STATE, not fleet drift, and they land
# on exactly the hosts that RUN their lanes -- so a plain byte compare reds a healthy host
# on every lane after one turn (issue #1389). Issue #1401: compare the lane config's OWNED
# blocks (`model`, `model_aliases`, `fallback_providers`) through the ONE drift verdict
# (`agent_profile_provision.check_one`, the same seam #1297 drives for the default profile),
# so ANY Hermes-written block -- the next stamp included -- is tolerated while a genuinely
# stale owned byte still reds. `SOUL.md` and the skill stay byte-exact.


def _git(root: Path, *argv: str) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(
        ["git", "-C", str(root), *argv], capture_output=True, check=False
    )


def _blob(root: Path, base: str, path: str) -> bytes:
    got = _git(root, "show", f"{base}:{path}")
    if got.returncode:
        raise ValueError(f"cannot read {base}:{path}")
    return got.stdout


def _default_profile_drift(root: Path, base_sha: str, home: Path) -> tuple[list[str], list[str]]:
    """(failures, skips) for the DEFAULT profile's owned blocks against the BASE chain.

    The default profile is a MERGE home (`~/.hermes/config.yaml`), so only its OWNED
    blocks are compared — through `agent_profile_provision.check_one`, the ONE drift
    verdict, never a second copy of the block rule (issue #1297, rule 6d). The chain is
    rendered from the BASE blobs in a scratch root, so local unmerged work cannot
    launder a stale host. An absent config is NAMED, never a silent pass; a stale block
    is a failure.
    """
    dest = home.parent / "config.yaml"
    if not dest.is_file():
        return [], [f"default profile {dest} is absent — no owned blocks to compare"]
    with tempfile.TemporaryDirectory() as tmp:
        scratch = Path(tmp) / "repo"
        (scratch / "agents").mkdir(parents=True)
        for rel in ("agents/model_chain.json", "Makefile"):
            try:
                blob = _blob(root, base_sha, rel)
            except ValueError:
                return [], [f"{base_sha}:{rel} is unreadable at base — the chain cannot be rendered"]
            (scratch / rel).write_bytes(blob)
        chain, fatal = read_chain(scratch)
        if chain is None:
            return [], [f"the chain at {base_sha[:12]} cannot be read: {fatal}"]
        rendered = render_text(chain)
    return profile_drift("profile=default", dest, rendered, whole_copy=False), []


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
        for rel in (*MIRROR_RELS, "config.yaml"):
            rel = rel.format(lane=lane)
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
                continue
            if rel == "config.yaml":
                # Issue #1401: only the OWNED blocks are compared, through the ONE drift
                # verdict -- Hermes's runtime stamps (`_config_version`, `onboarding.seen`,
                # the next one) are the host's own state, while a stale `model:` /
                # `model_aliases:` / `fallback_providers:` byte still reds, naming the file.
                for line in profile_drift(
                    f"{lane}/{rel}", actual, expected.decode("utf-8"), whole_copy=False
                ):
                    print(f"[fleet-sync] FAIL {line}")
                    failed += 1
                continue
            if actual.read_bytes() != expected:
                print(f"[fleet-sync] FAIL {lane}/{rel} diverges from {base_sha}")
                failed += 1

    try:
        rulebook = _blob(root, base_sha, RULEBOOK_REL).decode("utf-8")
    except ValueError:
        print(f"[fleet-sync] FAIL {base_sha}:{RULEBOOK_REL} missing at base")
        failed += 1
    else:
        for marker in RULEBOOK_MARKERS:
            if marker not in rulebook:
                print(f"[fleet-sync] FAIL AGENTS.md@{base_sha} dropped {marker!r}")
                failed += 1

    # Issue #1297: the DEFAULT profile's owned blocks are part of the same agreement. A host
    # running a retired provider shape answers HTTP 401 on inference while every lane byte
    # matches — so the lane loop alone reported OK on a host whose default profile was stale.
    drift, skips = _default_profile_drift(root, base_sha, home)
    for line in drift:
        print(f"[fleet-sync] FAIL {line}")
        failed += 1
    for line in skips:
        print(f"[fleet-sync] SKIP {line}")

    if failed:
        print(f"[fleet-sync] FAIL {failed} divergence(s) against {base_sha} ({base_sha[:12]})")
        return 1
    print(
        f"[fleet-sync] OK: base {base_sha}, {len(LANES)} lane(s), the default profile's "
        "owned blocks and the AGENTS.md lifecycle markers match upstream"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
