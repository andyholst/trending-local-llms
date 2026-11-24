#!/usr/bin/env python3
"""Classify and reconcile a divergent fleet host mirror against the fetched base (#1464).

`make fleet-host-sync-check` refuses byte divergence but names no direction and offers no
remedy, so every `M:` wake re-derives by hand whether a host file is BEHIND master (missing
a pinned needle) or FORWARD (extra experience notes) -- and a raw host copy into the tree
would delete master's bytes. This seam reuses the check's comparison inputs (`LANES`,
`MIRROR_RELS`, `_blob`, `_git` -- ONE definition of which files are compared and against
which base, rule 6d) and adds only NEW logic: a line-based classification
(`FORWARD` / `STALE` / `MIXED`), a LOSSLESS union, a timestamped backup before any overwrite,
and a destination that is either the host profile home (the section 7b refresh act) or a
worktree's `agents/<lane>/<rel>` (the reviewed delivery).

Scope: the TEXT mirrors only -- `SOUL.md` and `skills/<lane>/SKILL.md`. `config.yaml` stays
with `make agent-profile-provision`; a second drift verdict for it is forbidden (#1198/#1204).

Exit: 0 clean / every divergence written, 1 divergence remains (report-only, or an unwritten
file), 2 undecidable (bad base, missing home, unreadable blob, a violated lossless invariant).
"""
from __future__ import annotations

import argparse
import difflib
import shutil
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

try:  # the ONE lane set, mirror path list and base/blob seam (rule 6d)
    from fleet_host_sync_check import LANES, MIRROR_RELS, _blob, _git
except ImportError:  # run from the repo root
    from scripts.fleet_host_sync_check import LANES, MIRROR_RELS, _blob, _git


def _is_subsequence(needle: list[str], haystack: list[str]) -> bool:
    """True when every `needle` line appears in `haystack` IN ORDER (greedy)."""
    rest = iter(haystack)
    return all(line in rest for line in needle)


def classify(base_lines: list[str], host_lines: list[str]) -> str:
    """`SAME` / `FORWARD` (host deleted nothing) / `STALE` (host is behind) / `MIXED`."""
    if base_lines == host_lines:
        return "SAME"
    if _is_subsequence(base_lines, host_lines):
        return "FORWARD"
    if _is_subsequence(host_lines, base_lines):
        return "STALE"
    return "MIXED"


def _collapse_duplicate_blocks(lines: list[str]) -> list[str]:
    """Drop an exact-duplicate CONTIGUOUS RUN of >=2 lines, first occurrence wins.

    Nothing is lost: the earlier copy survives, so both inputs stay ordered subsequences of
    the result. This is the duplicate a hand-made union introduced on #1456 and an operator
    had to remove by hand (a bullet block copied twice with no blank line between the runs).
    """
    out = list(lines)
    while True:
        n = len(out)
        found: tuple[int, int, int] | None = None
        for length in range(min(512, n // 2), 1, -1):
            seen: dict[tuple[str, ...], int] = {}
            for i in range(0, n - length + 1):
                key = tuple(out[i:i + length])
                if key in seen:
                    found = (seen[key], i, length)
                    break
                seen[key] = i
            if found:
                break
        if not found:
            return out
        _, start, length = found
        print(f"[fleet-reconcile] union: dropped a duplicate block ({length} lines)")
        del out[start:start + length]


def union_lines(base_lines: list[str], host_lines: list[str]) -> list[str]:
    """A LOSSLESS merge: master's bytes are restored AND the host's forward notes survive."""
    matcher = difflib.SequenceMatcher(None, base_lines, host_lines, autojunk=False)
    raw: list[str] = []
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            raw.extend(base_lines[i1:i2])
        elif tag == "insert":
            raw.extend(host_lines[j1:j2])
        elif tag == "delete":
            raw.extend(base_lines[i1:i2])
        else:  # replace: keep BOTH sides -- a host note can sit where master changed a line
            raw.extend(base_lines[i1:i2])
            raw.extend(host_lines[j1:j2])
    # Lossless BEFORE normalisation: neither side may lose a line.
    if not _is_subsequence(base_lines, raw) or not _is_subsequence(host_lines, raw):
        raise AssertionError("the computed merge lost a line from one side")
    merged = _collapse_duplicate_blocks(raw)
    # Normalisation may drop a REPEATED run, never a line neither side still carries.
    lost = (set(base_lines) | set(host_lines)) - set(merged)
    if lost:
        raise AssertionError(f"the computed union lost {sorted(lost)!r}")
    return merged


def _backup(dest: Path) -> Path:
    """`<dest>.bak-<UTC>`, never clobbering an existing backup (rule 3b spirit)."""
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    candidate = dest.with_name(f"{dest.name}.bak-{stamp}")
    n = 2
    while candidate.exists():
        candidate = dest.with_name(f"{dest.name}.bak-{stamp}-{n}")
        n += 1
    shutil.copy2(dest, candidate)
    return candidate


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", required=True, help="resolved git ref, e.g. origin/master")
    parser.add_argument("--root", default=None, help="repository root")
    parser.add_argument("--profiles-home", default=None, help="profile home (default: ~/.hermes/profiles)")
    parser.add_argument("--expect-ref", default=None, help="refuse unless --base resolves to this ref")
    parser.add_argument("--dest", default=None, help="write the union under <dest>/agents/<lane>/<rel>")
    parser.add_argument("--write", action="store_true", help="back up + write the union (default: report only)")
    args = parser.parse_args(argv)

    root = Path(args.root).resolve() if args.root else Path(__file__).resolve().parent.parent
    resolved = _git(root, "rev-parse", "--verify", f"{args.base}^{{commit}}")
    if resolved.returncode:
        print(f"[fleet-reconcile] REFUSED: base {args.base!r} is not a commit in {root}")
        return 2
    base_sha = resolved.stdout.decode().strip()
    if args.expect_ref:
        expected = _git(root, "rev-parse", "--verify", f"{args.expect_ref}^{{commit}}")
        if expected.returncode or expected.stdout.decode().strip() != base_sha:
            print(
                f"[fleet-reconcile] REFUSED: base {base_sha} is not {args.expect_ref} "
                "-- fetch upstream before reconciling the fleet"
            )
            return 2

    dest_root: Path | None = None
    home: Path | None = None
    if args.dest:
        dest_root = Path(args.dest).expanduser().resolve()
    else:
        # Issue #1552: keep the caller's SPELLING -- absolute, but never symlink-resolved --
        # so every path this seam prints names the tree the operator pointed at. `resolve()`
        # rewrote `/var/folders/...` to `/private/var/folders/...` on macOS (`/var` is a
        # symlink there), so the printed BACKUP path disagreed with the handed spelling and
        # the guard reds on a healthy mac. The reads/writes below follow symlinks
        # transparently, so nothing else changes.
        home = (
            Path(args.profiles_home).expanduser().absolute()
            if args.profiles_home
            else (Path.home() / ".hermes" / "profiles")
        )
        if not home.is_dir():
            print(f"[fleet-reconcile] REFUSED: no profile home at {home}")
            return 2

    divergent = 0
    written = 0
    for lane in LANES:
        for rel in MIRROR_RELS:
            rel = rel.format(lane=lane)
            repo_path = f"agents/{lane}/{rel}"
            try:
                expected_bytes = _blob(root, base_sha, repo_path)
            except ValueError:
                print(f"[fleet-reconcile] REFUSED: {base_sha}:{repo_path} unreadable at base")
                return 2
            lane_dir = (dest_root / "agents" / lane) if dest_root else (home / lane)  # type: ignore[operator]
            actual = lane_dir / rel
            if not actual.is_file():
                print(f"[fleet-reconcile] FAIL {lane}/{rel} missing in {lane_dir}")
                divergent += 1
                continue
            base_lines = expected_bytes.decode("utf-8").splitlines()
            host_lines = actual.read_text(encoding="utf-8").splitlines()
            verdict = classify(base_lines, host_lines)
            if verdict == "SAME":
                continue
            try:
                merged = union_lines(base_lines, host_lines)
            except AssertionError as exc:
                print(f"[fleet-reconcile] REFUSED: {lane}/{rel}: {exc} -- nothing written")
                return 2
            plus = sum((Counter(host_lines) - Counter(base_lines)).values())
            minus = sum((Counter(base_lines) - Counter(host_lines)).values())
            print(f"[fleet-reconcile] CLASSIFY {lane}/{rel} {verdict} +{plus}/-{minus}")
            print(f"[fleet-reconcile] UNION {lane}/{rel} lines={len(merged)} -> {actual}")
            divergent += 1
            if args.write:
                backup = _backup(actual)
                print(f"[fleet-reconcile] BACKUP {backup}")
                actual.write_text("\n".join(merged) + ("\n" if merged else ""), encoding="utf-8")
                written += 1

    if not args.write and divergent:
        print(f"[fleet-reconcile] DIVERGENT {divergent} file(s) against {base_sha} -- rerun with WRITE=1")
        return 1
    if args.write and written != divergent:
        print(f"[fleet-reconcile] FAIL {divergent - written} file(s) left unwritten against {base_sha}")
        return 1
    print(f"[fleet-reconcile] OK: base {base_sha}, {len(LANES)} lane(s), every text mirror matches")
    return 0


if __name__ == "__main__":
    sys.exit(main())
