#!/usr/bin/env python3
"""The architect's wiki-freshness duty is a SOURCE-LEVEL role change (issue #1773).

Three sibling lanes split #1773; this guard owns ONLY the architect role/mirror
slice. It reads the four role texts the owner directed us to amend (the two
in-tree mirrors and the two host profile copies) and refuses a tree where the
duty is missing from any of them.

RED-first: the duty heading and every needle below are ABSENT from the freshly
fetched base role text at the pinned sha (measured 2026-11-26:
37c6d88150fdb73fd0583a59099aee0b418d7927) and PRESENT on this head. The pinned
sha is a constant, not a moving `origin/master`, so the RED proof stays valid
after this change reaches master. `test_red_on_the_pinned_base` fails if a
future edit makes the guard unable to distinguish base from head.

Wired into `main()`; `scripts/run_tests.sh` discovers this module by filename.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BASE_SHA = "37c6d88150fdb73fd0583a59099aee0b418d7927"
HOST = Path.home() / ".hermes" / "profiles" / "tll-architect"

HEADING = "## Wiki / documentation freshness (issue #1773)"
NEEDLES = (
    "measure each wiki/doc claim against the fetched tree",
    "UPDATE a doc when its claim is false",
    "ARCHIVE an obsolete doc into `docs/archive/` with a dated marker and a pointer",
    "file one `enhancement` issue per change with measured evidence and the fetched sha",
    "never invent a value",
    "never hand-edit a generated artifact",
    "the former 'no cron / no workflow' prohibitions are amended ONLY for this duty",
    "The weekly cron reviews the daily CI findings",
)

TREE_ROLE_FILES = (
    "agents/tll-architect/SOUL.md",
    "agents/tll-architect/skills/tll-architect/SKILL.md",
)
HOST_ROLE_FILES = (
    ("SOUL.md", "agents/tll-architect/SOUL.md"),
    ("skills/tll-architect/SKILL.md",
     "agents/tll-architect/skills/tll-architect/SKILL.md"),
)


def _base_blob(rel: str) -> str:
    """The role text at the pinned base sha; raises when the object is unavailable.

    A shallow CI checkout may not carry the pinned object: the caller treats that
    as an honest SKIP of the RED proof, never as a green assertion over no data.
    """
    got = subprocess.run(
        ["git", "-C", str(ROOT), "show", f"{BASE_SHA}:{rel}"],
        capture_output=True, text=True, check=False,
    )
    if got.returncode != 0:
        raise RuntimeError(f"cannot read {BASE_SHA}:{rel}")
    return got.stdout


def _missing(text: str) -> list[str]:
    absent = [n for n in NEEDLES if n not in text]
    if HEADING not in text:
        absent.insert(0, HEADING)
    return absent


def test_tree_role_mirrors_carry_the_duty() -> None:
    for rel in TREE_ROLE_FILES:
        text = (ROOT / rel).read_text(encoding="utf-8")
        assert not _missing(text), f"{rel} lost the wiki-freshness duty: {_missing(text)}"


def test_host_profile_copies_carry_the_duty() -> None:
    for rel, _tree in HOST_ROLE_FILES:
        path = HOST / rel
        if not path.is_file():
            # The test image mounts the tree, not a real operator home; the tree
            # mirrors above are the CI-visible half of this four-file contract.
            print(f"ok   SKIP host copy not mounted: {path}")
            continue
        text = path.read_text(encoding="utf-8")
        assert not _missing(text), f"host {rel} lost the duty: {_missing(text)}"


def test_host_copy_matches_its_tree_mirror_duty_text() -> None:
    """Both halves of the contract carry the same amendment, not a chat-only note."""
    for rel, tree_rel in HOST_ROLE_FILES:
        host = HOST / rel
        if not host.is_file():
            print(f"ok   SKIP host mirror comparison (no host home): {rel}")
            continue
        tree = (ROOT / tree_rel).read_text(encoding="utf-8")
        host_text = host.read_text(encoding="utf-8")
        for needle in NEEDLES:
            assert (needle in tree) == (needle in host_text), (
                f"host/tree disagree on {needle!r} ({rel} vs {tree_rel})")


def test_red_on_the_pinned_base() -> None:
    """The guard must FAIL on the base role text and PASS on this head."""
    for rel in TREE_ROLE_FILES:
        try:
            base = _base_blob(rel)
        except RuntimeError as exc:
            print(f"ok   SKIP RED proof ({exc}) — shallow checkout")
            continue
        absent = _missing(base)
        assert HEADING in absent, f"base {rel} already carries the new duty heading"
        assert len(absent) >= 4, f"base {rel} is not convincingly RED: {absent}"


def main() -> int:
    failed = 0
    for fn in (
        test_tree_role_mirrors_carry_the_duty,
        test_host_profile_copies_carry_the_duty,
        test_host_copy_matches_its_tree_mirror_duty_text,
        test_red_on_the_pinned_base,
    ):
        try:
            fn()
        except AssertionError as exc:
            print(f"FAIL {fn.__name__}: {exc}")
            failed += 1
        else:
            print(f"ok   {fn.__name__}")
    if failed:
        print(f"FAIL {failed}")
        return 1
    print("ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
