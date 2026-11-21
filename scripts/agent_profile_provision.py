#!/usr/bin/env python3
"""Provision a fleet lane's RENDERED chain config into the Hermes profile home that runs it.

The repository already carries the chain: `agents/model_chain.json` is the ONE source (issue
#1140) and `make agent-profile-model-render` renders each lane's `agents/tll-<lane>/config.yaml`
from it. Issue #1142 measured the other half and found it missing: nothing copied a rendered lane
config into `~/.hermes/profiles/tll-<lane>/config.yaml`, so the machine that actually runs the
lanes read something else entirely — `~/.hermes/profiles/tll-architect/config.yaml` said
`provider: strata` / `default: qwen3.8-flash-next-q2_0` / `base_url: http://127.0.0.1:8080/v1` in
all seven `tll-*` homes, `printenv | grep -c NOUS_API_KEY` printed `0`, and `make
agent-model-chain-check` enforced "free first, paid last" only inside the repository. "Green in
the repo, wrong on the machine" is the defect this seam closes.

Three rules shape it (AGENTS.md):

- Rule 3e — a credential is a NAME. When the chain names a `key_env`, this seam reads only whether the
  named variable is SET (through `scripts/require_env.py`, the one pre-flight, issue #357) and
  REFUSES (exit 2, naming the variable) before it writes anything. A lane configured with a chain
  whose key is absent is a keyless lane that fails inside a model call, which is exactly the
  measured 401/403 story of §3e/§6k — so the gate speaks first. No value is read, printed or
  measured for length. A chain on the `nous` provider names NO key_env (the Portal session
  authenticates it, issue #1199), so the pre-flight has nothing to check and is skipped.
- Rule 3b — additive only. A home's existing `config.yaml` is never destroyed: it is copied to
  `config.yaml.bak-<UTC>` and the new file lands beside the backup. Restoring is a human act.
- Rule 6d — one implementation. Lanes come from `agent_model_chain.fleet_lanes` (the tree, never
  a hand-kept list), the bytes written are `agent_model_chain.render_text`'s output, and a lane
  whose on-disk config has drifted from the chain is REFUSED rather than copied: provisioning a
  config the gate would red is laundering the drift into a live profile.

Usage:
    make agent-profile-provision LANE=tll-architect
    make agent-profile-provision ALL=1
    python3 scripts/agent_profile_provision.py --lane tll-architect [--profiles-home DIR]
"""
from __future__ import annotations

import argparse
import datetime as dt
import os
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import agent_model_chain as AMC  # noqa: E402  (ONE chain, ONE renderer, ONE lane list, rule 6d)
from require_env import main as require_env_main  # noqa: E402  (ONE credential pre-flight, #357)

ROOT = AMC.ROOT
CONFIG_REL = AMC.CONFIG_REL
BACKUP_SUFFIX = ".bak-"
PROFILES_ENV = "HERMES_PROFILES_HOME"

EXIT_OK, EXIT_UNDECIDABLE = AMC.EXIT_OK, AMC.EXIT_UNDECIDABLE


def profiles_home(cli_value: str | None) -> Path:
    """Where Hermes keeps profile homes: flag > HERMES_PROFILES_HOME > ~/.hermes/profiles."""
    if cli_value:
        return Path(cli_value).expanduser()
    env = os.environ.get(PROFILES_ENV)
    if env:
        return Path(env).expanduser()
    return Path.home() / ".hermes" / "profiles"


def utc_stamp() -> str:
    return dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def required_key_names(chain: AMC.Chain) -> list[str]:
    """Every credential NAME the chain's steps name — deduped, order-stable, VALUES never touched."""
    names: list[str] = []
    for entry in chain.entries:
        for name in (entry.key_env,):
            if name and name not in names:
                names.append(name)
    if chain.key_env and chain.key_env not in names:
        names.append(chain.key_env)
    return names


def provision_one(root: Path, lane: str, home: Path, rendered: str) -> tuple[int, Path | None]:
    """Copy ONE lane's rendered config into its profile home, backing up whatever was there."""
    src = root / "agents" / lane / CONFIG_REL
    if not src.is_file():
        print(f"[profile-provision] FATAL: agents/{lane}/{CONFIG_REL} does not exist — run "
              f"`make agent-profile-model-render` first (the chain renders it)", file=sys.stderr)
        return EXIT_UNDECIDABLE, None
    if src.read_text() != rendered:
        # The gate would red this lane; a live home must never receive what the gate refuses.
        print(f"[profile-provision] REFUSED: agents/{lane}/{CONFIG_REL} is not what the chain "
              f"renders — run `make agent-profile-model-render` (and fix the chain), never "
              f"provision a drifted config into a profile home", file=sys.stderr)
        return EXIT_UNDECIDABLE, None

    lane_home = home / lane
    dest = lane_home / CONFIG_REL
    try:
        lane_home.mkdir(parents=True, exist_ok=True)
        backup: Path | None = None
        if dest.is_file():
            backup = lane_home / f"{CONFIG_REL}{BACKUP_SUFFIX}{utc_stamp()}"
            shutil.copy2(dest, backup)
        dest.write_text(rendered)
        if dest.read_text() != rendered:
            print(f"[profile-provision] FATAL: {dest} does not read back byte-identical to what "
                  f"the chain renders", file=sys.stderr)
            return EXIT_UNDECIDABLE, None
    except OSError as exc:
        print(f"[profile-provision] FATAL: cannot write {dest}: {exc}", file=sys.stderr)
        return EXIT_UNDECIDABLE, None

    print(f"[profile-provision] lane={lane} home={dest} bytes={len(rendered)} "
          f"backup={backup if backup else 'none (no prior config)'}")
    return EXIT_OK, backup


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Provision a fleet lane's rendered chain config into its Hermes profile home.")
    ap.add_argument("--lane", action="append", default=[],
                    help="a fleet lane to provision (repeatable; e.g. tll-architect)")
    ap.add_argument("--all", action="store_true", help="provision every fleet lane in the tree")
    ap.add_argument("--profiles-home", default=None,
                    help=f"profile home root (default: ${PROFILES_ENV} or ~/.hermes/profiles)")
    ap.add_argument("--root", default=str(ROOT), help="repository root to read (tests plant a scratch tree)")
    ap.add_argument("--dry-run", action="store_true",
                    help="verify the chain, the credential and every lane config, write nothing")
    args = ap.parse_args(argv)

    root = Path(args.root)
    lanes = AMC.fleet_lanes(root)
    if not lanes:
        print("[profile-provision] UNDECIDABLE: no fleet lane found under agents/ "
              "(agents/tll-*/SOUL.md) — there is nothing to provision", file=sys.stderr)
        return EXIT_UNDECIDABLE

    wanted = list(args.lane)
    if args.all:
        wanted = list(lanes)
    if not wanted:
        print("[profile-provision] REFUSED: name what you are provisioning — "
              f"`make agent-profile-provision LANE=<lane>` (one of: {', '.join(lanes)}) or "
              "`ALL=1` (every lane). Writing a live profile home is never a default.",
              file=sys.stderr)
        return EXIT_UNDECIDABLE

    unknown = [w for w in wanted if w not in lanes]
    if unknown:
        print(f"[profile-provision] REFUSED: unknown lane(s) {', '.join(unknown)}; the fleet is "
              f"{', '.join(lanes)}", file=sys.stderr)
        return EXIT_UNDECIDABLE

    chain, fatal = AMC.read_chain(root)
    if chain is None:
        for line in fatal:
            print(f"[profile-provision] UNDECIDABLE: {line}", file=sys.stderr)
        return EXIT_UNDECIDABLE
    pins, pin_problems = AMC.read_makefile_pins(root)
    problems = AMC.chain_problems(chain, pins) + pin_problems
    if problems:
        for line in problems:
            print(f"[profile-provision] UNDECIDABLE: {line}", file=sys.stderr)
        return EXIT_UNDECIDABLE

    # Rule 3e / issue #357: the credential is checked BY NAME before anything is written. A chain
    # on the `nous` provider authenticates through the Portal session and names NO key_env (issue
    # #1199), so there is nothing to pre-flight and the check is skipped; a chain that DOES name a
    # key is checked before a byte is written.
    names = required_key_names(chain)
    if names:
        rc = require_env_main(names + ["--why",
                                       "a provisioned fleet lane must be able to authenticate the chain "
                                       "it names, or it will fail inside a model call instead of at this gate"])
        if rc != 0:
            print(f"[profile-provision] REFUSED: nothing was written to {profiles_home(args.profiles_home)} "
                  f"— the chain names {', '.join(names)} and that credential is absent", file=sys.stderr)
            return EXIT_UNDECIDABLE

    home = profiles_home(args.profiles_home)
    rendered = AMC.render_text(chain)
    drift = AMC.config_problems(root, chain, rendered)
    if drift:
        for line in drift:
            print(f"[profile-provision] REFUSED: {line}", file=sys.stderr)
        return EXIT_UNDECIDABLE

    if args.dry_run:
        print(f"[profile-provision] DRY RUN: chain ok, {', '.join(names)} set (value never read), "
              f"{len(wanted)} lane config(s) match the chain; nothing written "
              f"(target home would be {home / wanted[0] / CONFIG_REL})")
        return EXIT_OK

    wrote = 0
    backups = 0
    for lane in wanted:
        rc, backup = provision_one(root, lane, home, rendered)
        if rc != EXIT_OK:
            return rc
        wrote += 1
        if backup:
            backups += 1
    print(f"[profile-provision] OK: provisioned {wrote} lane config(s) into {home} "
          f"({backups} prior config(s) kept as {CONFIG_REL}{BACKUP_SUFFIX}<UTC> backups, rule 3b); "
          f"credential NAMES required: {', '.join(names)} (values never read or printed)")
    return EXIT_OK


if __name__ == "__main__":
    raise SystemExit(main())
