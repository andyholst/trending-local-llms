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
  8. a macOS-shaped home (reached through a symlinked ancestor, `/var` -> `/private/var`)
     still prints the BACKUP path in the SPELLING THE CALLER HANDED, never a rewritten one
     (#1552) -- RED on the pre-fix seam on any host, because the symlink reproduces the shape;
  9. the Linux-shaped plain tree agrees: handed and resolved spellings coincide there.
"""
from __future__ import annotations

import os
import re
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


def build(tmp: Path, base_text: str, host_text: str, lane: str = "tll-tester",
          rulebook_base: str | None = None, rulebook_host: str | None = None) -> tuple[Path, Path]:
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
    # Issue #1860: the host rulebook is a SINGLE file at the home root, compared against
    # the repo-root AGENTS.md. `rulebook_base`/`rulebook_host` default to identical bytes
    # so the existing nine guards stay green; the new four override them.
    (repo / "AGENTS.md").write_text(rulebook_base or "rule alpha\nrule beta\n", encoding="utf-8")
    (home / "AGENTS.md").write_text(rulebook_host or "rule alpha\nrule beta\n", encoding="utf-8")
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


def _printed_backup(stdout: str) -> str | None:
    """The path token on the seam's `[fleet-reconcile] BACKUP <path>` line, if any."""
    match = re.search(r"\[fleet-reconcile\] BACKUP (\S+)", stdout)
    return match.group(1) if match else None


def _check_backup_spelling(home: Path, written: subprocess.CompletedProcess[str], before: bytes) -> int:
    """One backup exists, holds the pre-write bytes, and is printed in the handed spelling."""
    failed = check(written.returncode == 0, "WRITE=1 lands the union")
    backups = sorted(home.glob("tll-tester/SOUL.md.bak-*"))
    failed += check(len(backups) == 1, "exactly one timestamped backup was written")
    if not backups:
        return failed
    failed += check(backups[0].read_bytes() == before, "the backup is the pre-write bytes")
    failed += check(f"BACKUP {backups[0]}" in written.stdout,
                    "the printed path keeps the caller's spelling, never a rewritten one")
    printed = _printed_backup(written.stdout)
    failed += check(printed is not None and Path(printed).resolve() == backups[0].resolve(),
                    "the printed path resolves to the backup that exists")
    return failed


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


def test_backup_path_keeps_the_handed_spelling_on_a_symlinked_macos_shaped_home() -> int:
    """macOS shape (#1552): `/var` is a symlink to `/private/var`, so a home under
    `/var/folders/...` resolves to a DIFFERENT spelling. The seam must print the path it was
    handed. A symlink reproduces that shape on ANY host, so this is RED against the pre-fix
    seam in Linux CI too -- not just on a mac."""
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp).resolve()
        repo, home = build(root, "alpha\nbeta\n", "alpha\nNOTE forward\nbeta\n")
        link = root / "homed"
        link.symlink_to(home, target_is_directory=True)
        before = (link / "tll-tester" / "SOUL.md").read_bytes()
        written = run_seam(repo, link, "--write")
        return _check_backup_spelling(link, written, before)


def test_backup_path_keeps_the_handed_spelling_on_a_plain_linux_shaped_home() -> int:
    """Linux shape: no symlinked ancestor, so handed and resolved spellings coincide. Pin
    that the seam still prints the handed path rather than inventing a canonical one."""
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp).resolve()
        repo, home = build(root, "alpha\nbeta\n", "alpha\nNOTE forward\nbeta\n")
        before = (home / "tll-tester" / "SOUL.md").read_bytes()
        written = run_seam(repo, home, "--write")
        return _check_backup_spelling(home, written, before)


def test_stale_host_rulebook_and_soul_converge_to_base() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        base_soul = "alpha\nbeta\ngamma\n"
        rule_base = "rule alpha\nrule beta\nrule gamma\n"
        repo, home = build(
            Path(tmp), base_soul, "alpha\nbeta\n",
            rulebook_base=rule_base, rulebook_host="rule alpha\nrule beta\n",
        )
        got = run_seam(repo, home, "--write", "--attended-signoff")
        failed = check(got.returncode == 0, "attended WRITE=1 repairs a stale host")
        failed += check("CLASSIFY AGENTS.md STALE +0/-1" in got.stdout,
                        "the host AGENTS.md is classified STALE against the fetched base")
        failed += check((home / "AGENTS.md").read_text(encoding="utf-8") == rule_base,
                        "the host rulebook converges to the repo-authoritative bytes")
        failed += check((home / "tll-tester" / "SOUL.md").read_text(encoding="utf-8") == base_soul,
                        "the stale SOUL mirror converges in the same run")
        failed += check(bool(list(home.glob("AGENTS.md.bak-*"))),
                        "the rulebook is backed up before it is overwritten")
        return failed


def test_forward_host_rulebook_note_is_preserved() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        rule_host = "rule alpha\nNOTE learned on this host\nrule beta\n"
        repo, home = build(
            Path(tmp), "alpha\nbeta\n", "alpha\nbeta\n",
            rulebook_base="rule alpha\nrule beta\n", rulebook_host=rule_host,
        )
        got = run_seam(repo, home, "--write", "--attended-signoff")
        failed = check("CLASSIFY AGENTS.md FORWARD +1/-0" in got.stdout,
                       "a host-ahead rulebook is classified FORWARD")
        failed += check((home / "AGENTS.md").read_text(encoding="utf-8") == rule_host,
                        "the lossless union preserves the host's forward note")
        return failed


def test_protected_rulebook_write_fails_closed_without_signoff() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        repo, home = build(
            Path(tmp), "alpha\nbeta\ngamma\n", "alpha\nbeta\n",
            rulebook_base="rule alpha\nrule beta\nrule gamma\n",
            rulebook_host="rule alpha\nrule beta\n",
        )
        rule_before = (home / "AGENTS.md").read_bytes()
        soul_before = (home / "tll-tester" / "SOUL.md").read_bytes()
        got = run_seam(repo, home, "--write")
        failed = check(got.returncode == 2, "an unattended protected write exits 2")
        failed += check("REFUSED" in got.stdout and "rule 3c" in got.stdout,
                        "the refusal names rule 3c")
        failed += check((home / "AGENTS.md").read_bytes() == rule_before,
                        "the protected rulebook bytes are untouched")
        failed += check((home / "tll-tester" / "SOUL.md").read_bytes() == soul_before,
                        "fail-closed means NO file is written, not just the protected one")
        failed += check(not list(home.glob("*.bak-*"))
                        and not list(home.glob("tll-tester/*.bak-*")),
                        "no backup is left by a refused write")
        return failed


def test_config_yaml_is_untouched() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        repo, home = build(Path(tmp), "alpha\nbeta\ngamma\n", "alpha\nbeta\n")
        cfg = home / "tll-tester" / "config.yaml"
        cfg.write_text("owned: stale\n", encoding="utf-8")
        before = cfg.read_bytes()
        got = run_seam(repo, home, "--write", "--attended-signoff")
        failed = check(got.returncode == 0, "the write path still lands the mirrors")
        failed += check(cfg.read_bytes() == before, "config.yaml is untouched by reconciliation")
        failed += check("config.yaml" not in got.stdout, "no second config.yaml drift verdict")
        failed += check(not list(home.glob("tll-tester/config.yaml.bak-*")),
                        "no config.yaml backup is written")
        return failed


def test_make_and_ci_wire_the_signoff_and_rulebook() -> int:
    root = Path(__file__).resolve().parent.parent
    makefile = (root / "Makefile").read_text(encoding="utf-8")
    workflow = (root / ".github" / "workflows" / "qa-validate.yml").read_text(encoding="utf-8")
    failed = check("$(if $(ATTESTED), --attended-signoff,)" in makefile,
                   "ATTESTED=1 is plumbed to the attended sign-off flag")
    failed += check("$(if $(RULEBOOK), --rulebook $(RULEBOOK),)" in makefile,
                    "RULEBOOK=... is plumbed to the rulebook override")
    failed += check("make fleet-host-reconcile BASE=HEAD PROFILES_HOME=agents RULEBOOK=AGENTS.md" in workflow,
                    "CI verifies the read-only rulebook comparison without a live host")
    failed += check("run: make test" in workflow,
                    "CI runs make test, which discovers the reconciliation guard module")
    failed += check("--write" not in [line.strip() for line in workflow.splitlines()
                                      if "fleet-host-reconcile" in line],
                    "no CI step turns the host write path on")
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
        test_backup_path_keeps_the_handed_spelling_on_a_symlinked_macos_shaped_home,
        test_backup_path_keeps_the_handed_spelling_on_a_plain_linux_shaped_home,
        test_stale_host_rulebook_and_soul_converge_to_base,
        test_forward_host_rulebook_note_is_preserved,
        test_protected_rulebook_write_fails_closed_without_signoff,
        test_config_yaml_is_untouched,
        test_make_and_ci_wire_the_signoff_and_rulebook,
    ))


if __name__ == "__main__":
    raise SystemExit(main())
