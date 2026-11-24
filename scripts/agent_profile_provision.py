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

Issue #1192 widens the seam to the WHOLE host: `--profile <name>` merges the rendered chain into a
NON-lane profile home (only the `model:`, `model_aliases:` and `fallback_providers:` top-level
blocks are replaced; every other block is kept byte-for-byte and verified after the write), and
`--profile default` names the Hermes home's own `config.yaml` beside the profiles root. The chain
itself gained the credential-less `local_fallback` tier between the free steps and the paid pin.

Three rules shape it (AGENTS.md):

- Rule 3e — a credential is a NAME. The chain names `key_env`; this seam reads only whether the
  named variable is SET (through `scripts/require_env.py`, the one pre-flight, issue #357) and
  REFUSES (exit 2, naming the variable) before it writes anything. A lane configured with a chain
  whose key is absent is a keyless lane that fails inside a model call, which is exactly the
  measured 401/403 story of §3e/§6k — so the gate speaks first. No value is read, printed or
  measured for length. The local tier is credential-less, but the remote steps still demand
  their key: a local step never makes provisioning keyless.
- Rule 3b — additive only. A home's existing `config.yaml` is never destroyed: it is copied to
  `config.yaml.bak-<UTC>` and the new file lands beside the backup. Restoring is a human act.
- Rule 6d — one implementation. Lanes come from `agent_model_chain.fleet_lanes` (the tree, never
  a hand-kept list), the bytes written are `agent_model_chain.render_lane`'s output — `render_text`'s
  byte-exact chain plus a lane's OPTIONAL declared `config.append.yaml` (issue #1618, so a whole-copy
  re-provision preserves owner-authorized settings such as #1591's flag) — and a lane
  whose on-disk config has drifted from the chain is REFUSED rather than copied: provisioning a
  config the gate would red is laundering the drift into a live profile.

Usage:
    make agent-profile-provision LANE=tll-architect
    make agent-profile-provision ALL=1
    make agent-profile-provision PROFILE=developer,project-manager,default
    make agent-profile-provision CHECK=1 ALL=1 PROFILE=developer,default   # drift report, writes nothing
    python3 scripts/agent_profile_provision.py --lane tll-architect [--profiles-home DIR]
    python3 scripts/agent_profile_provision.py --profile developer [--profiles-home DIR]
    python3 scripts/agent_profile_provision.py --check --all [--profiles-home DIR]

`--check` (issue #1204) is the read-only drift report: it names every home whose owned blocks (a
merge) or whole config (a lane) differ from the rendered chain, exits 1 on any drift and 0 when
all match, writes NOTHING and needs NO credential — the weekly free-tier refresh (issue #1195)
moves the repo's chain, and this is how a stale host is named instead of drifting in silence.
"""
from __future__ import annotations

import argparse
import datetime as dt
import os
import re
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
DEFAULT_PROFILE = "default"
# The ONLY top-level blocks a non-lane merge replaces (issue #1192); everything else is kept.
OWNED_BLOCKS = ("model", "model_aliases", "fallback_providers")
_TOP_BLOCK_RE = re.compile(r"(?m)^([A-Za-z_][A-Za-z0-9_]*):")

EXIT_OK, EXIT_PROBLEM, EXIT_UNDECIDABLE = AMC.EXIT_OK, AMC.EXIT_PROBLEM, AMC.EXIT_UNDECIDABLE


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


def _top_blocks(text: str) -> list[tuple[str, str]]:
    """Split a config into top-level blocks, preserving bytes; leading prose is an unnamed block."""
    marks = [(m.start(), m.group(1)) for m in _TOP_BLOCK_RE.finditer(text)]
    if not marks:
        return [("", text)] if text else []
    blocks: list[tuple[str, str]] = []
    if marks[0][0] > 0:
        blocks.append(("", text[:marks[0][0]]))
    for i, (pos, name) in enumerate(marks):
        end = marks[i + 1][0] if i + 1 < len(marks) else len(text)
        blocks.append((name, text[pos:end]))
    return blocks


def merge_rendered(existing: str, rendered: str) -> tuple[str, list[str]]:
    """Replace ONLY the owned blocks; every other top-level block stays byte-identical (issue #1192).

    The rendered chain's leading generated-header prose travels with its first owned block, so a
    merged home carries the same DO-NOT-HAND-EDIT notice a lane copy does. The merge is idempotent
    and VERIFIES itself: a non-owned block that changed, or an owned block that is not exactly the
    rendered one, is a problem — never a silent rewrite.
    """
    problems: list[str] = []
    rblocks = _top_blocks(rendered)
    lead = ""
    if rblocks and rblocks[0][0] == "":
        lead, rblocks = rblocks[0][1], rblocks[1:]
    new_owned: dict[str, str] = {}
    for name, chunk in rblocks:
        if name in OWNED_BLOCKS:
            new_owned[name] = chunk
    for name in OWNED_BLOCKS:
        if name not in new_owned:
            problems.append(f"the rendered chain carries no `{name}:` block to merge")

    existing_blocks = _top_blocks(existing)
    existing_lead = existing_blocks[0][1] if existing_blocks and existing_blocks[0][0] == "" else ""
    # The generated header goes to the FILE FRONT (never between blocks: a comment before a key
    # rides with the PREVIOUS block's bytes, which would change a block the merge does not own).
    # A second merge must not duplicate it: the merge is idempotent.
    attach_lead = bool(lead) and lead not in existing_lead

    out: list[str] = [lead] if attach_lead else []
    seen: set[str] = set()
    for name, chunk in existing_blocks:
        if name in OWNED_BLOCKS:
            if name in seen:
                continue  # a duplicate owned block collapses into the ONE rendered block
            if name in new_owned:
                out.append(new_owned[name])
                seen.add(name)
        else:
            out.append(chunk)
    for name in OWNED_BLOCKS:
        if name not in seen and name in new_owned:
            out.append(new_owned[name])
            seen.add(name)
    merged = "".join(out)

    # Verify: every NAMED non-owned block survives byte-for-byte in order, the home's leading
    # prose stays at the front (after the header, if one was attached), and each owned block IS
    # the rendered one.
    before = [(n, c) for n, c in existing_blocks if n and n not in OWNED_BLOCKS]
    after = [(n, c) for n, c in _top_blocks(merged) if n and n not in OWNED_BLOCKS]
    if before != after:
        problems.append("the merge changed a top-level block it does not own — refused")
    expected_prefix = (lead if attach_lead else "") + existing_lead
    if expected_prefix and not merged.startswith(expected_prefix):
        problems.append("the merge dropped the home's leading prose — refused")
    merged_owned = {n: c for n, c in _top_blocks(merged) if n in OWNED_BLOCKS}
    for name in OWNED_BLOCKS:
        if merged_owned.get(name) != new_owned.get(name):
            problems.append(f"the merged `{name}:` block is not byte-identical to the rendered chain")
    return merged, problems


def provision_one(root: Path, lane: str, home: Path, chain_or_rendered: AMC.Chain | str) -> tuple[int, Path | None]:
    """Copy ONE lane's rendered config into its profile home, backing up whatever was there."""
    src = root / "agents" / lane / CONFIG_REL
    if not src.is_file():
        print(f"[profile-provision] FATAL: agents/{lane}/{CONFIG_REL} does not exist — run "
              f"`make agent-profile-model-render` first (the chain renders it)", file=sys.stderr)
        return EXIT_UNDECIDABLE, None
    # A caller that already rendered the bytes (issue #1229's prompt probe) still works; a chain
    # caller gets the lane's declared append too (issue #1618). Additive, never a breaking switch.
    rendered = (chain_or_rendered if isinstance(chain_or_rendered, str)
                else AMC.render_lane(root, chain_or_rendered, lane))
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

    # Issue #1214: a lane whose home has only config.yaml cannot take a turn with its
    # prompts. Copy SOUL.md + skills/ from the SAME lane source (additive; CHECK mode
    # never reaches this function), so CI's freshly provisioned homes carry prompts.
    src_lane = src.parent
    soul = src_lane / "SOUL.md"
    if soul.is_file():
        shutil.copy2(soul, lane_home / "SOUL.md")
    src_skills = src_lane / "skills"
    if src_skills.is_dir():
        shutil.copytree(src_skills, lane_home / "skills", dirs_exist_ok=True)
    return EXIT_OK, backup


def provision_profile(name: str, home: Path, rendered: str) -> tuple[int, Path | None]:
    """Merge the rendered chain into ONE non-lane home (issue #1192); `default` is the Hermes home's own config."""
    if name == DEFAULT_PROFILE:
        profile_dir = home.parent
    else:
        profile_dir = home / name
    dest = profile_dir / CONFIG_REL
    if not profile_dir.is_dir():
        print(f"[profile-provision] REFUSED: profile home {profile_dir} does not exist — "
              f"provisioning never creates a profile; name one that is there (or `default`)",
              file=sys.stderr)
        return EXIT_UNDECIDABLE, None
    existing = dest.read_text(encoding="utf-8") if dest.is_file() else ""
    if existing:
        merged, problems = merge_rendered(existing, rendered)
        if problems:
            for p in problems:
                print(f"[profile-provision] REFUSED: profile={name}: {p}", file=sys.stderr)
            return EXIT_UNDECIDABLE, None
    else:
        merged = rendered
    try:
        backup: Path | None = None
        if dest.is_file():
            backup = profile_dir / f"{CONFIG_REL}{BACKUP_SUFFIX}{utc_stamp()}"
            shutil.copy2(dest, backup)
        dest.write_text(merged, encoding="utf-8")
        if dest.read_text(encoding="utf-8") != merged:
            print(f"[profile-provision] FATAL: {dest} does not read back byte-identical to the merge",
                  file=sys.stderr)
            return EXIT_UNDECIDABLE, None
    except OSError as exc:
        print(f"[profile-provision] FATAL: cannot write {dest}: {exc}", file=sys.stderr)
        return EXIT_UNDECIDABLE, None
    print(f"[profile-provision] profile={name} home={dest} bytes={len(merged)} "
          f"backup={backup if backup else 'none (no prior config)'}")
    return EXIT_OK, backup


def check_one(label: str, dest: Path, rendered: str, whole_copy: bool) -> list[str]:
    """The drift verdict for ONE home (issue #1204): which bytes differ from the rendered chain.

    A lane is a WHOLE copy, so its entire config must equal the render; a non-lane home is a
    MERGE, so only the owned blocks are compared — the home's other blocks are its own business.
    Read-only: nothing is written, no credential is needed (a drift report must work on a host
    whose key is absent — that is exactly the host that needs the report).
    """
    if not dest.is_file():
        return [f"{label}: {dest} is missing — the home was never provisioned"]
    try:
        text = dest.read_text(encoding="utf-8")
    except OSError as exc:
        return [f"{label}: {dest} could not be read: {exc}"]
    if whole_copy:
        if text != rendered:
            return [f"{label}: the lane config drifted from the rendered chain (a lane is a whole copy)"]
        return []
    blocks = {n: c for n, c in _top_blocks(text) if n in OWNED_BLOCKS}
    want = {n: c for n, c in _top_blocks(rendered) if n in OWNED_BLOCKS}
    return [f"{label}: `{n}:` drifted from the rendered chain"
            for n in OWNED_BLOCKS if blocks.get(n) != want.get(n)]


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Provision a fleet lane's rendered chain config into its Hermes profile home.")
    ap.add_argument("--lane", action="append", default=[],
                    help="a fleet lane to provision (repeatable; e.g. tll-architect)")
    ap.add_argument("--all", action="store_true", help="provision every fleet lane in the tree")
    ap.add_argument("--profile", action="append", default=[],
                    help="a NON-lane profile home to merge the chain into (repeatable; `default` "
                         "names the Hermes home's own config.yaml)")
    ap.add_argument("--profiles-home", default=None,
                    help=f"profile home root (default: ${PROFILES_ENV} or ~/.hermes/profiles)")
    ap.add_argument("--root", default=str(ROOT), help="repository root to read (tests plant a scratch tree)")
    ap.add_argument("--dry-run", action="store_true",
                    help="verify the chain, the credential and every lane config, write nothing")
    ap.add_argument("--check", action="store_true",
                    help="REPORT drift between the named homes and the rendered chain (issue #1204): "
                         "exit 1 naming every stale home/block, exit 0 when all match, writes nothing, "
                         "needs no credential")
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
    wanted_profiles = list(args.profile)
    if not wanted and not wanted_profiles:
        print("[profile-provision] REFUSED: name what you are provisioning — "
              f"`make agent-profile-provision LANE=<lane>` (one of: {', '.join(lanes)}), "
              "`ALL=1` (every lane), or `PROFILE=<name>[,<name>…]` (a non-lane home, `default` "
              "for the Hermes home's own config). Writing a live profile home is never a default.",
              file=sys.stderr)
        return EXIT_UNDECIDABLE

    unknown = [w for w in wanted if w not in lanes]
    if unknown:
        print(f"[profile-provision] REFUSED: unknown lane(s) {', '.join(unknown)}; the fleet is "
              f"{', '.join(lanes)}", file=sys.stderr)
        return EXIT_UNDECIDABLE
    lane_as_profile = [p for p in wanted_profiles if p in lanes]
    if lane_as_profile:
        print(f"[profile-provision] REFUSED: {', '.join(lane_as_profile)} is a fleet lane — "
              f"provision it with LANE=<lane> (a whole copy), never PROFILE= (a merge)",
              file=sys.stderr)
        return EXIT_UNDECIDABLE
    bad_profiles = [p for p in wanted_profiles if not p or not re.match(r"^[A-Za-z0-9][A-Za-z0-9._-]*$", p)]
    if bad_profiles:
        print(f"[profile-provision] REFUSED: not a profile name: {', '.join(repr(p) for p in bad_profiles)}",
              file=sys.stderr)
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

    home = profiles_home(args.profiles_home)
    rendered = AMC.render_text(chain)  # non-lane merge homes get the chain; lanes add their declared append
    drift = AMC.config_problems(root, chain)
    if drift:
        for line in drift:
            print(f"[profile-provision] REFUSED: {line}", file=sys.stderr)
        return EXIT_UNDECIDABLE

    if args.check:
        # Issue #1204: the read-only drift report. A merged weekly refresh (issue #1195) moves
        # the repo's chain while the host homes keep the old list until someone re-provisions;
        # this mode NAMES the stale homes loudly instead of letting the drift sit silent.
        stale: list[str] = []
        checked = 0
        for lane in wanted:
            dest = home / lane / CONFIG_REL
            if not (home / lane).is_dir():
                print(f"[profile-drift] UNDECIDABLE: profile home {home / lane} does not exist",
                      file=sys.stderr)
                return EXIT_UNDECIDABLE
            stale += check_one(f"lane={lane}", dest, AMC.render_lane(root, chain, lane), whole_copy=True)
            checked += 1
        for name in wanted_profiles:
            profile_dir = home.parent if name == DEFAULT_PROFILE else home / name
            if not profile_dir.is_dir():
                print(f"[profile-drift] UNDECIDABLE: profile home {profile_dir} does not exist",
                      file=sys.stderr)
                return EXIT_UNDECIDABLE
            stale += check_one(f"profile={name}", profile_dir / CONFIG_REL, rendered, whole_copy=False)
            checked += 1
        for s in stale:
            print(f"[profile-drift] STALE {s}")
        if stale:
            print(f"[profile-drift] {checked} home(s) checked, {len(stale)} drift finding(s) — "
                  f"re-provision with `make agent-profile-provision` (the same targets, without CHECK=1)")
            return EXIT_PROBLEM
        print(f"[profile-drift] CLEAN: {checked} home(s) match the rendered chain byte-for-byte "
              f"(owned blocks for merges, whole copy for lanes)")
        return EXIT_OK

    # Rule 3e / issue #357: the credential is checked BY NAME before anything is written. A chain
    # on the `nous` provider authenticates through the Portal session and names NO key_env (issue
    # #1203), so there is nothing to pre-flight and the check is skipped; a chain that DOES name a
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

    if args.dry_run:
        print(f"[profile-provision] DRY RUN: chain ok, {', '.join(names)} set (value never read), "
              f"{len(wanted)} lane config(s) match the chain; nothing written "
              f"(target home would be {home / wanted[0] / CONFIG_REL if wanted else home})"
              + (f"; profiles to merge: {', '.join(wanted_profiles)}" if wanted_profiles else ""))
        return EXIT_OK

    wrote = 0
    backups = 0
    for lane in wanted:
        rc, backup = provision_one(root, lane, home, chain)
        if rc != EXIT_OK:
            return rc
        wrote += 1
        if backup:
            backups += 1
    merged_count = 0
    for name in wanted_profiles:
        rc, backup = provision_profile(name, home, rendered)
        if rc != EXIT_OK:
            return rc
        merged_count += 1
        if backup:
            backups += 1
    print(f"[profile-provision] OK: provisioned {wrote} lane config(s) and merged {merged_count} "
          f"profile home(s) into {home} "
          f"({backups} prior config(s) kept as {CONFIG_REL}{BACKUP_SUFFIX}<UTC> backups, rule 3b); "
          f"credential NAMES required: {', '.join(names)} (values never read or printed)")
    return EXIT_OK


if __name__ == "__main__":
    raise SystemExit(main())
