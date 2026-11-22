#!/usr/bin/env python3
"""tests/test_agent_image_smoke.py — issue #1214: the live smoke must prove the
agent image is available (published, or built by image-ensure's fallback) AND that
every provisioned fleet profile carries its prompts (SOUL + skills + config).

No model call: the repo's main CI pipeline runs tests only (owner directive
2026-11-15 / #1029). The guards call the REAL checker; the only external system is
the filesystem and the `docker`/`ensure_image` seams, which are replaced with fakes
where needed.
"""
from __future__ import annotations

import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "tests"))

import agent_image_smoke as AISM  # noqa: E402
from wiring import wired  # noqa: E402

_PASS = 0
_FAIL = 0


def check(name, cond, detail=""):
    global _PASS, _FAIL
    if cond:
        _PASS += 1
        print(f"  ok  {name}")
    else:
        _FAIL += 1
        print(f"  FAIL {name}" + (f"  [{detail}]" if detail else ""))


def test_profile_prompt_findings():
    with tempfile.TemporaryDirectory() as td:
        home = Path(td)
        lanes = sorted(p.name for p in (ROOT / "agents").glob("tll-*") if p.is_dir())
        check("the repo declares fleet lanes", len(lanes) >= 3, str(lanes))
        for name in lanes:
            lane = home / name
            lane.mkdir(parents=True)
            source = ROOT / "agents" / name
            # Byte-identical to the repo source: the checker now verifies identity, not just presence.
            for artefact in ("config.yaml", "SOUL.md"):
                shutil.copy2(source / artefact, lane / artefact)
            if (source / "skills").is_dir():
                shutil.copytree(source / "skills", lane / "skills", dirs_exist_ok=True)
        check("a complete planted profile tree has no findings",
              not AISM.profile_findings(home), str(AISM.profile_findings(home)[:3]))
        lane = home / lanes[0]
        (lane / "SOUL.md").unlink()
        missing = AISM.profile_findings(home)
        check("a missing SOUL is named", any("SOUL.md" in f for f in missing), str(missing))
        (lane / "SOUL.md").write_text("You are a planner.\n")
        (lane / "skills" / lanes[0] / "SKILL.md").unlink()
        missing = AISM.profile_findings(home)
        check("a missing prompt skill is named", any("SKILL.md" in f for f in missing), str(missing))
        # A stale-but-present prompt is a real #1190 failure mode: presence alone is not reachability.
        (lane / "SOUL.md").write_text("STALE PROMPT\n")
        drifted = AISM.profile_findings(home)
        check("stale SOUL bytes are named as drift",
              any("drifted" in f and "SOUL.md" in f for f in drifted), str(drifted[:3]))
    check("a missing profiles home is named",
          any("does not exist" in f for f in AISM.profile_findings(Path("/nonexistent/tll-smoke"))))


def test_image_states_and_refs():
    refs = AISM.agent_refs()
    check("the one ref seam yields an immutable hash tag",
          any(":dockerfile-" in r for r in refs), str(refs[:3]))
    saved = (AISM.published, AISM.built_locally)
    try:
        AISM.published = lambda ref: (True, "manifest present")
        AISM.built_locally = lambda ref: False
        check("a published manifest is reported as published",
              AISM.image_state("ref")[0] == "published")
        AISM.published = lambda ref: (False, "manifest unknown")
        AISM.built_locally = lambda ref: True
        check("image-ensure's local build is accepted as built-local",
              AISM.image_state("ref")[0] == "built-local")
        AISM.built_locally = lambda ref: False
        check("neither published nor built is absent",
              AISM.image_state("ref")[0] == "absent")
    finally:
        AISM.published, AISM.built_locally = saved


def test_local_fallback_image_name():
    """PR #1229: image-ensure builds `trending-local-llms:latest` locally when the
    hash tag is unpublished; the probe must accept that local name too."""
    saved = AISM.subprocess.run
    seen = []

    class Result:
        returncode = 0

    def fake_run(argv, **kwargs):
        seen.append(argv[-1])
        # The exact GHCR ref is absent in CI; only the locally built fallback answers.
        return Result() if argv[-1].endswith("trending-local-llms:latest") else type(
            "Result", (), {"returncode": 1})()

    try:
        AISM.subprocess.run = fake_run
        check("a locally built fallback image is accepted",
              AISM.built_locally("ghcr.io/andyholst/trending-local-llms:dockerfile-a106db319f32"))
        check("the local fallback is probed when the hash ref is absent",
              "trending-local-llms:latest" in seen, str(seen))
    finally:
        AISM.subprocess.run = saved


def test_provision_copies_prompts():
    """PR #1229: CI homes provisioned from the chain must carry SOUL + skills, not
    only config.yaml — otherwise the prompt smoke cannot pass in a fresh runner."""
    import agent_profile_provision as APP
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        lane_dir = root / "agents" / "tll-probe"
        (lane_dir / "skills" / "tll-probe").mkdir(parents=True)
        (lane_dir / "config.yaml").write_text("model:\n  provider: nous\n")
        (lane_dir / "SOUL.md").write_text("You are a probe.\n")
        (lane_dir / "skills" / "tll-probe" / "SKILL.md").write_text("# probe\n")
        home = root / "homes"
        code, _ = APP.provision_one(root, "tll-probe", home,
                                    (lane_dir / "config.yaml").read_text())
        planted = home / "tll-probe"
        check("provision succeeds on a planted lane", code == 0, str(code))
        check("the provisioned home gets SOUL.md", (planted / "SOUL.md").is_file())
        check("the provisioned home gets its skill prompt",
              (planted / "skills" / "tll-probe" / "SKILL.md").is_file())
        planted_findings = [f for f in AISM.profile_findings(home) if "tll-probe" in f]
        check("the planted tree has no findings for the provisioned lane",
              not planted_findings, str(planted_findings[:3]))


def test_wiring():
    mk = (ROOT / "Makefile").read_text()
    wf = (ROOT / ".github" / "workflows" / "qa-validate.yml").read_text()
    check("make agent-image-smoke target exists", "agent-image-smoke:" in mk)
    check("strict published-only target exists", "agent-image-published-check:" in mk)
    check("live-smoke runs the image/profile check", "make agent-image-smoke" in wf)
    check("the CI step uses the provisioned scratch home",
          "PROFILES_HOME: ${{ runner.temp }}/hermes-profiles" in wf)
    check("this suite is discovered by `make test`", wired(__file__), "")


def main() -> int:
    print("agent image + profile prompt smoke (#1214):")
    test_profile_prompt_findings()
    test_image_states_and_refs()
    test_local_fallback_image_name()
    test_provision_copies_prompts()
    test_wiring()
    print(f"{'FAILED' if _FAIL else 'PASSED'} {_PASS} | FAILED {_FAIL}")
    return 1 if _FAIL else 0


if __name__ == "__main__":
    raise SystemExit(main())
