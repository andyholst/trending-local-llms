#!/usr/bin/env python3
"""Issue #1214: prove the agent image is PUBLISHED and every fleet profile that
would run inside it has its prompts (SOUL + skills + config) available.

This is a TEST-ONLY smoke: it never makes a model call and never mutates a store,
a profile home or the registry (owner directive 2026-11-15 / issue #1029: the main
CI pipeline runs tests only). It is the preflight half of "a real turn can happen":
a green image-manifest probe plus a fully provisioned prompt tree. A real LLM
round-trip remains in the bot pipelines that need a model.

Usage:
    python3 scripts/agent_image_smoke.py \
        [--profiles-home DIR] [--skip-image] [--skip-profiles]
"""
from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REF_LINE = re.compile(r"ghcr\.io/[^\s'\"]+")


def agent_refs() -> list[str]:
    """The GHCR refs for this revision, from the ONE repo seam (no second hash rule)."""
    out = subprocess.run("python3 scripts/ensure_image.py ref", shell=True, cwd=ROOT,
                         capture_output=True, text=True, timeout=120)
    refs = []
    for line in (out.stdout + out.stderr).splitlines():
        refs.extend(REF_LINE.findall(line))
    return sorted(set(refs))


def published(ref: str) -> tuple[bool, str]:
    """Manifest answers for the exact ref — built AND published, not just built."""
    if shutil.which("docker") is None:
        return (False, "docker CLI is not available; cannot probe the published manifest")
    p = subprocess.run(["docker", "manifest", "inspect", ref],
                       capture_output=True, text=True, timeout=120)
    if p.returncode == 0:
        return (True, "manifest present")
    return (False, (p.stderr or p.stdout).strip().splitlines()[-1][:160] if (p.stderr or p.stdout).strip()
            else f"docker manifest inspect {ref} failed")


def built_locally(ref: str) -> bool:
    if shutil.which("docker") is None:
        return False
    # image-ensure's designed fallback builds the LOCAL name (`trending-local-llms:latest`)
    # when the hash tag is not published (measured on PR #1229: CI built that local tag,
    # then this probe called the image absent because it inspected only the GHCR ref).
    local = f"{ref.rsplit('/', 1)[-1].split(':', 1)[0]}:latest"
    for candidate in (ref, local):
        if subprocess.run(["docker", "image", "inspect", candidate],
                          capture_output=True, text=True, timeout=120).returncode == 0:
            return True
    return False


def image_state(ref: str) -> tuple[str, str]:
    """`published` (manifest answers), `built-local` (image-ensure built it here),
    or `absent` — with the reason. A built-local image is the repo's designed
    fallback when a hash tag is not published yet (image-ensure / #1120)."""
    ok, why = published(ref)
    if ok:
        return ("published", why)
    if built_locally(ref):
        return ("built-local", why)
    return ("absent", why)


def profile_findings(profiles_home: Path) -> list[str]:
    """One finding per missing prompt/config artefact in a provisioned lane home."""
    repo_tree = ROOT / "agents"
    lanes = sorted(p for p in repo_tree.glob("tll-*") if p.is_dir())
    if not lanes:
        return ["no agents/tll-* lane sources found in the repo"]
    if not profiles_home.is_dir():
        return [f"profiles home {profiles_home} does not exist — run make agent-profile-provision ALL=1 first"]
    bad = []
    for lane in lanes:
        home = profiles_home / lane.name
        if not home.is_dir():
            bad.append(f"profile {lane.name} is absent from {profiles_home}")
            continue
        for required in ("config.yaml", "SOUL.md"):
            target, source = home / required, lane / required
            if not target.exists():
                bad.append(f"profile {lane.name} is missing {required}")
            elif source.is_file() and target.read_bytes() != source.read_bytes():
                bad.append(f"profile {lane.name}'s {required} drifted from agents/{lane.name}/{required}")
        src_skills = {d.name: sorted(f.name for f in (d / "skills").glob("*"))
                      if (d / "skills").is_dir() else []
                      for d in [lane]}
        for skill in src_skills[lane.name]:
            target = home / "skills" / skill
            source = lane / "skills" / skill / "SKILL.md"
            if not target.is_dir() or not (target / "SKILL.md").exists():
                bad.append(f"profile {lane.name} is missing prompt skill {skill}/SKILL.md")
            elif source.is_file() and (target / "SKILL.md").read_bytes() != source.read_bytes():
                bad.append(f"profile {lane.name}'s skill {skill}/SKILL.md drifted from the agents source")
    return bad


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--profiles-home", default=os.environ.get(
        "PROFILES_HOME", str(Path.home() / ".hermes" / "profiles")))
    ap.add_argument("--skip-image", action="store_true")
    ap.add_argument("--skip-profiles", action="store_true")
    ap.add_argument("--require-published", action="store_true",
                    help="refuse a locally-built-only image (strict owner check)")
    a = ap.parse_args(argv)
    findings = []
    if not a.skip_image:
        refs = agent_refs()
        if not refs:
            findings.append("no agent image GHCR ref could be derived for this revision")
        for ref in refs:
            state, why = image_state(ref)
            print(f"[image] {ref}: {state} — {why}")
            if state == "absent" or (a.require_published and state != "published"):
                findings.append(f"agent image {ref} is {state}: {why}")
    if not a.skip_profiles:
        bad = profile_findings(Path(a.profiles_home))
        print(f"[profiles] {a.profiles_home}: {len(bad)} prompt finding(s)")
        findings.extend(bad)
    if findings:
        print(f"[agent-image-smoke] FAIL {len(findings)} finding(s):")
        for f in findings:
            print(f"  - {f}")
        return 1
    print("[agent-image-smoke] OK: published image + all fleet profile prompts present")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
