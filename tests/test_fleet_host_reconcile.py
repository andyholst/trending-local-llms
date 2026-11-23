#!/usr/bin/env python3
"""tests/test_fleet_host_reconcile.py — issue #1464: classify + losslessly reconcile a diverged mirror.

`make fleet-host-sync-check` refuses byte divergence but cannot say whether a host file is
BEHIND master (a pinned needle is missing) or FORWARD (extra experience notes), so every
`M:` wake re-derives that by hand and risks either destroying forward notes or wiping them to
go green. This suite drives the REAL `scripts/fleet_host_reconcile.py` end to end over a
scratch git repo + a scratch profile home (rule 6m: no stand-in replaces the seam; the only
external system is the filesystem, which is real):

  1. a FORWARD host (base lines all present, in order) classifies FORWARD and its union IS the
     host -- `WRITE=1` lands it and keeps the pre-existing file as `.bak-<UTC>`;
  2. a STALE host (host lines all present in base) classifies STALE and the union restores
     master's missing bytes and nothing else;
  3. a MIXED host yields a union that is a SUPERSET of both inputs, once each, order-preserving;
  4. an exact-duplicate non-blank BLOCK is dropped and REPORTED (the #1456 shape);
  5. report-only writes NOTHING (bytes and mtime unchanged);
  6. an unresolvable base exits 2 writing nothing;
  7. the target is wired to the Makefile, qa-validate and ARCHITECTURE.md (rules 6d/6h/6m).
"""
from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SEAM = ROOT / "scripts" / "fleet_host_reconcile.py"
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "tests"))

from wiring import wired  # noqa: E402  (a test must be discovered by `make test`, rule 6d)

import fleet_host_sync_check as fsc  # noqa: E402  (the ONE lane set / mirror list, rule 6d)

LANES = fsc.LANES

#: The module's own failure counter (issue #1301: plain pytest must agree with `make test`).
FAILED = 0


def check(cond: bool, msg: str) -> int:
    global FAILED
    if cond:
        print(f"ok   {msg}")
        return 0
    FAILED += 1
    print(f"FAIL {msg}")
    return 1


def build(tmp: Path, base_text: str, host_text: str, lane: str = "tll-tester") -> tuple[Path, Path]:
    """A REAL git repo at `repo` (base) and a profile home at `profiles` (host)."""
    repo = tmp / "repo"
    home = tmp / "profiles"
    home.mkdir(parents=True)
    for name in LANES:
        skill = repo / "agents" / name / "skills" / name
        skill.mkdir(parents=True)
        (repo / "agents" / name / "SOUL.md").write_text(
            base_text if name == lane else "base soul\n", encoding="utf-8"
        )
        (skill / "SKILL.md").write_text("base skill\n", encoding="utf-8")
        hskill = home / name / "skills" / name
        hskill.mkdir(parents=True)
        (home / name / "SOUL.md").write_text(
            host_text if name == lane else "base soul\n", encoding="utf-8"
        )
        (hskill / "SKILL.md").write_text("base skill\n", encoding="utf-8")
    for argv in (
        ["git", "init", "-q"],
        ["git", "add", "-A"],
        ["git", "-c", "user.name=fleet-test", "-c", "user.email=fleet@example.invalid",
         "commit", "-q", "-m", "base"],
    ):
        subprocess.run(argv, cwd=repo, check=True, capture_output=True)
    return repo, home


def run_seam(repo: Path, home: Path, *extra: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SEAM), "--base", "HEAD", "--root", str(repo),
         "--profiles-home", str(home), *extra],
        cwd=ROOT, capture_output=True, text=True, check=False,
    )


def test_forward_host_classifies_and_write_keeps_a_backup() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        base = "alpha\nbeta\n"
        host = "alpha\nNOTE forward\nbeta\n"
        repo, home = build(Path(tmp), base, host)
        victim = home / "tll-tester" / "SOUL.md"
        got = run_seam(repo, home)
        failed = check(got.returncode == 1, "report-only exit is 1 on a divergence")
        failed += check("CLASSIFY tll-tester/SOUL.md FORWARD +1/-0" in got.stdout,
                        "the verdict names FORWARD and the delta")
        before = victim.read_bytes()
        written = run_seam(repo, home, "--write")
        failed += check(written.returncode == 0, "WRITE=1 lands the union and exits 0")
        failed += check(victim.read_text(encoding="utf-8") == host,
                        "a pure FORWARD union equals the host bytes (no pinned line lost)")
        backups = sorted(home.glob("tll-tester/SOUL.md.bak-*"))
        failed += check(len(backups) == 1, "exactly one timestamped backup was written")
        if backups:
            failed += check(backups[0].read_bytes() == before, "the backup is the pre-write bytes")
            failed += check(f"BACKUP {backups[0]}" in written.stdout, "the backup path is printed")
        return failed


def test_stale_host_restores_master_bytes() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        base = "alpha\nbeta\ngamma\n"
        repo, home = build(Path(tmp), base, "alpha\nbeta\n")
        got = run_seam(repo, home, "--write")
        victim = home / "tll-tester" / "SOUL.md"
        failed = check("CLASSIFY tll-tester/SOUL.md STALE +0/-1" in got.stdout,
                       "the verdict names STALE and the deleted line")
        failed += check(got.returncode == 0, "the stale mirror is repaired")
        failed += check(victim.read_text(encoding="utf-8") == base,
                        "the union restores master's missing line and nothing else")
        return failed


def test_mixed_host_union_is_a_lossless_superset() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        base = "alpha\nbeta\ngamma\n"
        host = "alpha\nNEW\ngamma\nEXTRA\n"
        repo, home = build(Path(tmp), base, host)
        got = run_seam(repo, home, "--write")
        merged = (home / "tll-tester" / "SOUL.md").read_text(encoding="utf-8").splitlines()
        failed = check("CLASSIFY tll-tester/SOUL.md MIXED +2/-1" in got.stdout,
                       "the verdict names MIXED and both deltas")
        for line in ("alpha", "beta", "gamma", "NEW", "EXTRA"):
            failed += check(merged.count(line) == 1, f"the union carries {line!r} exactly once")
        failed += check(merged.index("alpha") < merged.index("beta") < merged.index("gamma"),
                        "master's order survives")
        failed += check(merged.index("alpha") < merged.index("NEW") < merged.index("gamma"),
                        "the host's inserted line keeps its place")
        return failed


def test_duplicate_block_is_dropped_and_reported() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        base = "a1\na2\nb1\n"
        host = "a1\na2\nb1\na1\na2\n"
        repo, home = build(Path(tmp), base, host)
        got = run_seam(repo, home, "--write")
        merged = (home / "tll-tester" / "SOUL.md").read_text(encoding="utf-8").splitlines()
        failed = check("dropped a duplicate block (2 lines)" in got.stdout,
                       "the duplicate block is reported, not silently absorbed")
        failed += check(merged == ["a1", "a2", "b1"], "the second copy is gone and nothing else moved")
        return failed


def test_report_only_leaves_bytes_and_mtime_untouched() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        repo, home = build(Path(tmp), "alpha\nbeta\n", "alpha\nNOTE\nbeta\n")
        victim = home / "tll-tester" / "SOUL.md"
        before = victim.read_bytes()
        mtime = victim.stat().st_mtime_ns
        got = run_seam(repo, home)
        failed = check(got.returncode == 1, "report-only still reports the divergence")
        failed += check(victim.read_bytes() == before, "the bytes are untouched")
        failed += check(victim.stat().st_mtime_ns == mtime, "the mtime is untouched")
        failed += check(not list(home.glob("tll-tester/*.bak-*")), "no backup is written report-only")
        return failed


def test_unresolvable_base_exits_two_writing_nothing() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        repo, home = build(Path(tmp), "alpha\nbeta\n", "alpha\nNOTE\nbeta\n")
        victim = home / "tll-tester" / "SOUL.md"
        before = victim.read_bytes()
        got = subprocess.run(
            [sys.executable, str(SEAM), "--base", "no-such-ref", "--root", str(repo),
             "--profiles-home", str(home), "--write"],
            cwd=ROOT, capture_output=True, text=True, check=False,
        )
        failed = check(got.returncode == 2, "an unresolvable base is exit 2")
        failed += check("REFUSED" in got.stdout, "the refusal is loud")
        failed += check(victim.read_bytes() == before, "nothing was written")
        return failed


def test_the_target_is_wired_to_make_ci_and_the_description() -> int:
    makefile = (ROOT / "Makefile").read_text(encoding="utf-8")
    workflow = (ROOT / ".github" / "workflows" / "qa-validate.yml").read_text(encoding="utf-8")
    arch = (ROOT / "ARCHITECTURE.md").read_text(encoding="utf-8")
    failed = check("fleet-host-reconcile:" in makefile, "the Makefile owns the target")
    failed += check("make fleet-host-reconcile BASE=HEAD PROFILES_HOME=agents" in workflow,
                    "qa-validate calls the read-only half")
    failed += check("`fleet-host-reconcile`" in arch, "ARCHITECTURE.md documents the target")
    failed += check("`scripts/fleet_host_reconcile.py`" in arch,
                    "ARCHITECTURE.md documents the script")
    failed += check(wired(__file__), "this suite is discovered by `make test`")
    return failed


def main() -> int:
    return sum(fn() for fn in (
        test_forward_host_classifies_and_write_keeps_a_backup,
        test_stale_host_restores_master_bytes,
        test_mixed_host_union_is_a_lossless_superset,
        test_duplicate_block_is_dropped_and_reported,
        test_report_only_leaves_bytes_and_mtime_untouched,
        test_unresolvable_base_exits_two_writing_nothing,
        test_the_target_is_wired_to_make_ci_and_the_description,
    ))


if __name__ == "__main__":
    raise SystemExit(main())
