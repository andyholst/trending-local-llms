#!/usr/bin/env python3
"""Sync the chain's local-tier model id into the host's AUXILIARY blocks (issue #1198).

The provision seam (issues #1142/#1192, `scripts/agent_profile_provision.py`) owns exactly three
top-level blocks — `model:`, `model_aliases:`, `fallback_providers:` — and keeps every other block
byte-for-byte. Two other blocks also name the local provider: the `custom_providers:` entry the
local tier routes through (`strata`) and the `moa:` presets (aggregator + reference models). The
chain's `local_fallback` model id therefore never reaches them. Measured 2026-11-21 across all 30
host homes (default + 29 profiles): the owned blocks carry the full ordered chain everywhere, but
23 homes still name the retired `qwen3.8-flash-next-q2_0` in `custom_providers[strata]` (model +
models map) and 10 of those also name it in every `moa.presets.default` entry — while the chain's
local tier names `qwen3.8-flash-next-iq3_xxs` (the box no longer serves q2_0). The MoA auxiliary
tool and the strata provider entry would call a retired id.

This seam propagates ONE id — the `local_fallback` entry's `model` in `agents/model_chain.json`,
the ONE source (rule 6d) — into those two surfaces, in named homes or every home including
`default` (the Hermes home's own config.yaml beside the profiles root):

- the `custom_providers:` entry whose `name` equals the tier's provider: its `model:` field and
  its `models:` map key + `context_length` (the tier's measured window);
- every `moa:` preset entry (aggregator or reference model) whose `provider:`/`base_url:` names
  the local tier: its `model:` field.

Contract (the provision seam's, narrowed to the auxiliary surface):

- ONLY the `custom_providers:` and `moa:` top-level blocks are touched, and within them only the
  local-tier model-id references; every other top-level block and the leading prose are kept
  byte-for-byte and VERIFIED after the write. A changed line that is not a model/models-key/
  context_length line is a refusal, never a silent rewrite.
- Rule 3b — additive only: the prior file is kept as `config.yaml.bak-<UTC>`; a home with no
  drift is not written at all (the sync is idempotent).
- Rule 3e — a credential is a NAME: this seam writes ONLY credential-less local-tier references
  and never touches a remote step, so it requires NO credential (unlike provision, which writes
  remote blocks and therefore demands the chain's `key_env` through `scripts/require_env.py`).
  No value is read, printed or measured.
- REFUSES (exit 2, writes NOTHING anywhere) when: the chain names no `local_fallback` tier (the
  state on master until issue #1192 / PR #1197 lands), the chain is unreadable or invalid, nothing
  was named, a named home does not exist, a stale moa id is ALSO named by a non-local entry
  (ambiguous), or the strata `models:` map carries more than one distinct stale key (a human
  decision). All homes are computed and verified BEFORE the first write.
- `--check` reports drift without writing (exit 1 on drift, 0 clean, 2 refusal) so the sync is
  gateable; `--dry-run` previews the writes and exits 0.

Usage:
    make agent-aux-local-sync PROFILE=developer,project-manager,default
    make agent-aux-local-sync ALL_PROFILES=1
    make agent-aux-local-sync ALL_PROFILES=1 CHECK=1
    python3 scripts/agent_aux_local_sync.py --profile default [--profiles-home DIR] [--root DIR]
"""
from __future__ import annotations

import argparse
import difflib
import os
import re
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import agent_model_chain as AMC  # noqa: E402  (ONE chain, ONE validator, rule 6d)
# ONE top-block splitter, ONE profiles-home resolver, ONE backup convention (rule 6d): the
# provision seam already owns them; this seam narrows the owned blocks, never re-implements them.
from agent_profile_provision import (  # noqa: E402
    BACKUP_SUFFIX,
    DEFAULT_PROFILE,
    _top_blocks,
    profiles_home,
    utc_stamp,
)

ROOT = AMC.ROOT
CONFIG_REL = AMC.CONFIG_REL
# The ONLY top-level blocks this seam touches (issue #1198); provision owns the other three.
OWNED_BLOCKS = ("custom_providers", "moa")
EXIT_OK, EXIT_DRIFT, EXIT_UNDECIDABLE = AMC.EXIT_OK, 1, AMC.EXIT_UNDECIDABLE

_MODEL_LINE = re.compile(r"(?m)^(\s*(?:- )?model:[ \t]*)(\S+)[ \t]*$")
_PROVIDER_LINE = re.compile(r"(?m)^\s*provider:[ \t]*(\S+)[ \t]*$")
_BASE_URL_LINE = re.compile(r"(?m)^\s*base_url:[ \t]*(\S+)[ \t]*$")
_NAME_LINE = re.compile(r"(?m)^\s*(?:- )?name:[ \t]*(\S+)[ \t]*$")
_ENTRY_START = re.compile(r"(?m)^  - ")
_MODELS_KEY = re.compile(r"(?m)^      ([^\s:]+):[ \t]*$")
_CTX_LINE = re.compile(r"(?m)^(\s*context_length:[ \t]*)\d+[ \t]*$")
# A changed line is legal ONLY if it is a model field, a models-map key, or a context_length.
_LEGAL_CHANGE = re.compile(r"^\s*(?:- )?(?:model:|[^\s:]+:|context_length:)")


def _id_token_re(old: str) -> re.Pattern:
    """Whole-token match for a model id (ids carry dots/dashes/underscores; never a substring)."""
    return re.compile(r"(?<![\w.\-])" + re.escape(old) + r"(?![\w.\-])")


def _cp_entries(block: str) -> list[tuple[int, int, str]]:
    """(start, end, chunk) for every `  - ` entry of a custom_providers block."""
    marks = [m.start() for m in _ENTRY_START.finditer(block)]
    out = []
    for i, pos in enumerate(marks):
        end = marks[i + 1] if i + 1 < len(marks) else len(block)
        out.append((pos, end, block[pos:end]))
    return out


def _moa_chunks(block: str) -> list[tuple[int, int, str]]:
    """(start, end, chunk) per model entry: each `model:` line starts a chunk that runs to the
    next `model:` line (its provider/base_url siblings follow it) or the block's end."""
    marks = [m.start() for m in _MODEL_LINE.finditer(block)]
    out = []
    for i, pos in enumerate(marks):
        end = marks[i + 1] if i + 1 < len(marks) else len(block)
        out.append((pos, end, block[pos:end]))
    return out


def _is_local(chunk: str, tier: AMC.Entry) -> bool:
    prov = _PROVIDER_LINE.search(chunk)
    url = _BASE_URL_LINE.search(chunk)
    return bool((prov and prov.group(1) == tier.provider) or (url and url.group(1) == tier.base_url))


def sync_blocks(existing: str, tier: AMC.Entry, _depth: int = 0) -> tuple[str, list[str], bool]:
    """Return (merged_text, problems, changed) for ONE home's config text.

    Only the strata custom_providers entry and the local-referencing moa entries are rewritten;
    every other top-level block stays byte-for-byte. Detection is conservative: an id shared
    with a non-local moa entry, or a models map with two distinct stale keys, is a REFUSAL.
    """
    problems: list[str] = []
    new_id = tier.model
    blocks = _top_blocks(existing)
    by_name = {n: c for n, c in blocks if n}
    new_cp = by_name.get("custom_providers")
    new_moa = by_name.get("moa")

    # --- custom_providers: the entry whose name is the tier's provider -------------------
    if new_cp is not None:
        entries = _cp_entries(new_cp)
        target = None
        for start, end, chunk in entries:
            nm = _NAME_LINE.search(chunk)
            if nm and nm.group(1) == tier.provider:
                target = (start, end, chunk)
                break
        if target is not None:
            start, end, chunk = target
            mm = _MODEL_LINE.search(chunk)
            old_model = mm.group(1) if mm else None
            # models-map keys live under the entry's `    models:` line (6-space keys).
            models_pos = re.search(r"(?m)^    models:[ \t]*$", chunk)
            stale_keys: list[str] = []
            if models_pos:
                tail = chunk[models_pos.end():]
                nxt = re.search(r"(?m)^    \S", tail)  # next 4-space field ends the map
                map_text = tail[: nxt.start()] if nxt else tail
                stale_keys = [k for k in _MODELS_KEY.findall(map_text) if k != new_id]
            distinct = sorted(set(stale_keys))
            if len(distinct) > 1:
                problems.append(
                    f"custom_providers[{tier.provider}].models carries {len(distinct)} distinct "
                    f"stale keys ({', '.join(distinct)}) — which one the box serves is a human decision")
            else:
                edits: list[str] = []
                if old_model and old_model != new_id:
                    edits.append(old_model)
                if distinct and distinct[0] not in edits:
                    edits.append(distinct[0])
                for old in edits:
                    chunk = _id_token_re(old).sub(new_id, chunk)
                if models_pos:
                    # the tier's measured window belongs to the (renamed) map entry
                    head, sep, tail = chunk.partition("    models:")
                    if sep:
                        nxt = re.search(r"(?m)^    \S", tail)
                        map_text = tail[: nxt.start()] if nxt else tail
                        rest = tail[nxt.start():] if nxt else ""
                        fixed = _CTX_LINE.sub(lambda m: m.group(1) + str(tier.context_window), map_text)
                        chunk = head + sep + fixed + rest
                new_cp = new_cp[:start] + chunk + new_cp[end:]

    # --- moa: every entry naming the tier's provider/base_url ----------------------------
    if new_moa is not None:
        chunks = _moa_chunks(new_moa)
        local_old: set[str] = set()
        other_ids: set[str] = set()
        for _, _, chunk in chunks:
            mm = _MODEL_LINE.search(chunk)
            if not mm:
                continue
            mid = mm.group(1)
            if _is_local(chunk, tier):
                if mid != new_id:
                    local_old.add(mid)
            else:
                other_ids.add(mid)
        ambiguous = sorted(local_old & other_ids)
        if ambiguous:
            problems.append(
                f"moa id(s) {', '.join(ambiguous)} are named by BOTH a local-tier entry and a "
                f"non-local entry — rewriting them would retarget a model this seam does not own")
        elif local_old:
            rebuilt = []
            for start, end, chunk in chunks:
                mm = _MODEL_LINE.search(chunk)
                if mm and _is_local(chunk, tier) and mm.group(1) != new_id:
                    chunk = _MODEL_LINE.sub(lambda m: m.group(1) + new_id, chunk, count=1)
                rebuilt.append((start, end, chunk))
            moa_out = new_moa
            for start, end, chunk in reversed(rebuilt):
                moa_out = moa_out[:start] + chunk + moa_out[end:]
            new_moa = moa_out

    if problems:
        return existing, problems, False

    # --- splice: replace ONLY the owned blocks; everything else stays byte-for-byte ------
    out: list[str] = []
    for name, chunk in blocks:
        if name == "custom_providers" and new_cp is not None:
            out.append(new_cp)
        elif name == "moa" and new_moa is not None:
            out.append(new_moa)
        else:
            out.append(chunk)
    merged = "".join(out)

    # --- verify: non-owned blocks byte-identical, in order; leading prose kept ------------
    before = [(n, c) for n, c in blocks if n and n not in OWNED_BLOCKS]
    after = [(n, c) for n, c in _top_blocks(merged) if n and n not in OWNED_BLOCKS]
    if before != after:
        problems.append("the sync changed a top-level block it does not own — refused")
    lead_before = blocks[0][1] if blocks and blocks[0][0] == "" else ""
    lead_after = _top_blocks(merged)[0][1] if _top_blocks(merged) and _top_blocks(merged)[0][0] == "" else ""
    if lead_before != lead_after:
        problems.append("the sync changed the home's leading prose — refused")
    # every changed line inside an owned block must be a model/models-key/context_length line
    for name, new_chunk in (("custom_providers", new_cp), ("moa", new_moa)):
        old_chunk = by_name.get(name)
        if old_chunk is None or new_chunk is None or old_chunk == new_chunk:
            continue
        diff = difflib.ndiff(old_chunk.splitlines(), new_chunk.splitlines())
        for line in diff:
            if line.startswith(("+ ", "- ")):
                body = line[2:]
                if body.strip() and not _LEGAL_CHANGE.match(body):
                    problems.append(f"the sync changed a line it does not own in `{name}:` — refused: {body!r}")
    if problems:
        return existing, problems, False
    if _depth == 0:
        # one-pass convergence: a second detection over the merge must find NOTHING left to do
        _, again_probs, again_changed = sync_blocks(merged, tier, _depth=1)
        if again_probs or again_changed:
            problems.append("the sync did not converge to the chain's local id in one pass — refused")
            return existing, problems, False
    return merged, [], merged != existing


def home_path(home: Path, name: str) -> Path:
    """`default` is the Hermes home's own config beside the profiles root (provision's convention)."""
    profile_dir = home.parent if name == DEFAULT_PROFILE else home / name
    return profile_dir / CONFIG_REL


def collect_targets(home: Path, names: list[str], all_profiles: bool) -> tuple[list[str], list[str]]:
    wanted = list(names)
    problems: list[str] = []
    if all_profiles:
        if home.is_dir():
            wanted += sorted(p.name for p in home.iterdir() if p.is_dir())
        if (home.parent / CONFIG_REL).is_file() and DEFAULT_PROFILE not in wanted:
            wanted.append(DEFAULT_PROFILE)
    bad = [p for p in wanted if not p or not re.match(r"^[A-Za-z0-9][A-Za-z0-9._-]*$", p)]
    if bad:
        problems.append(f"not a profile name: {', '.join(repr(p) for p in bad)}")
    missing = [p for p in wanted if p not in bad and not home_path(home, p).is_file()]
    if missing:
        problems.append(f"profile home(s) without a {CONFIG_REL}: {', '.join(missing)} — "
                        "the sync never creates a profile; name one that is there (or `default`)")
    seen: set[str] = set()
    deduped = [p for p in wanted if not (p in seen or seen.add(p))]
    return deduped, problems


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description="Sync the chain's local-tier model id into custom_providers[strata] + moa presets.")
    ap.add_argument("--profile", action="append", default=[],
                    help="a home to sync (repeatable; `default` names the Hermes home's own config.yaml)")
    ap.add_argument("--all-profiles", action="store_true",
                    help="sync every profile dir under the profiles home AND default")
    ap.add_argument("--profiles-home", default=None,
                    help="profile home root (default: $HERMES_PROFILES_HOME or ~/.hermes/profiles)")
    ap.add_argument("--root", default=str(ROOT), help="repository root to read (tests plant a scratch tree)")
    ap.add_argument("--check", action="store_true",
                    help="report drift without writing (exit 1 on drift, 0 clean, 2 refusal)")
    ap.add_argument("--dry-run", action="store_true", help="preview the writes, write nothing")
    args = ap.parse_args(argv)

    root = Path(args.root)
    chain, fatal = AMC.read_chain(root)
    if chain is None:
        lines = [fatal] if isinstance(fatal, str) else list(fatal)
        for line in lines:
            print(f"[aux-local-sync] UNDECIDABLE: {line}", file=sys.stderr)
        return EXIT_UNDECIDABLE
    pins, pin_problems = AMC.read_makefile_pins(root)
    problems = AMC.chain_problems(chain, pins) + pin_problems
    if problems:
        for line in problems:
            print(f"[aux-local-sync] UNDECIDABLE: {line}", file=sys.stderr)
        return EXIT_UNDECIDABLE
    tier = chain.local_fallback
    if tier is None:
        print("[aux-local-sync] REFUSED: the chain names no `local_fallback` tier — there is no "
              "local id to sync (the tier lands with issue #1192 / PR #1197); nothing was written",
              file=sys.stderr)
        return EXIT_UNDECIDABLE

    home = profiles_home(args.profiles_home)
    if not args.profile and not args.all_profiles:
        print("[aux-local-sync] REFUSED: name what you are syncing — `PROFILE=<name>[,<name>…]` "
              "(`default` for the Hermes home's own config) or `ALL_PROFILES=1`. Writing a live "
              "profile home is never a default.", file=sys.stderr)
        return EXIT_UNDECIDABLE
    targets, target_problems = collect_targets(home, args.profile, args.all_profiles)
    if target_problems:
        for p in target_problems:
            print(f"[aux-local-sync] REFUSED: {p}", file=sys.stderr)
        return EXIT_UNDECIDABLE

    # Compute EVERY home before the first write: one refusal writes nothing anywhere.
    planned: list[tuple[str, Path, str, str]] = []  # (name, dest, existing, merged)
    refusals: list[str] = []
    skipped: list[str] = []
    for name in targets:
        dest = home_path(home, name)
        existing = dest.read_text(encoding="utf-8")
        merged, probs, changed = sync_blocks(existing, tier)
        if probs:
            refusals.extend(f"profile={name}: {p}" for p in probs)
        elif changed:
            planned.append((name, dest, existing, merged))
        else:
            skipped.append(name)
    if refusals:
        for r in refusals:
            print(f"[aux-local-sync] REFUSED: {r}", file=sys.stderr)
        print(f"[aux-local-sync] nothing was written to {home} ({len(refusals)} refusal(s))",
              file=sys.stderr)
        return EXIT_UNDECIDABLE

    if args.check:
        for name, dest, _, _ in planned:
            print(f"[aux-local-sync] DRIFT profile={name} home={dest} — the local tier names "
                  f"{tier.model}; the auxiliary blocks name something else")
        for name in skipped:
            print(f"[aux-local-sync] clean profile={name}")
        print(f"[aux-local-sync] CHECK: {len(planned)} drifted, {len(skipped)} clean, "
              f"{len(targets)} home(s) examined; nothing written")
        return EXIT_DRIFT if planned else EXIT_OK

    if args.dry_run:
        for name, dest, _, _ in planned:
            print(f"[aux-local-sync] DRY RUN would sync profile={name} home={dest} -> {tier.model}")
        print(f"[aux-local-sync] DRY RUN: {len(planned)} home(s) would change, {len(skipped)} "
              f"already clean; nothing written")
        return EXIT_OK

    wrote = 0
    for name, dest, existing, merged in planned:
        backup = dest.parent / f"{CONFIG_REL}{BACKUP_SUFFIX}{utc_stamp()}"
        try:
            shutil.copy2(dest, backup)
            dest.write_text(merged, encoding="utf-8")
            if dest.read_text(encoding="utf-8") != merged:
                print(f"[aux-local-sync] FATAL: {dest} does not read back byte-identical to the sync",
                      file=sys.stderr)
                return EXIT_UNDECIDABLE
        except OSError as exc:
            print(f"[aux-local-sync] FATAL: cannot write {dest}: {exc}", file=sys.stderr)
            return EXIT_UNDECIDABLE
        print(f"[aux-local-sync] profile={name} home={dest} local_id={tier.model} backup={backup}")
        wrote += 1
    print(f"[aux-local-sync] OK: synced {wrote} home(s), {len(skipped)} already clean "
          f"({wrote} prior config(s) kept as {CONFIG_REL}{BACKUP_SUFFIX}<UTC> backups, rule 3b); "
          f"only custom_providers[{tier.provider}] + moa local entries touched, every other block "
          f"byte-for-byte; no credential required (local-tier references only)")
    return EXIT_OK


if __name__ == "__main__":
    raise SystemExit(main())