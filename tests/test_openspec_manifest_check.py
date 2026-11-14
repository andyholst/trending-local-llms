#!/usr/bin/env python3
"""Behavioural tests for scripts/openspec_manifest_check.py (issue #919).

The OpenSpec CLI image must be PUBLISHED as a multi-architecture manifest or a
fresh arm64 checkout dies at `docker pull` ("no matching manifest for
linux/arm64/v8") — issue #767's failure, still reachable because
refresh-bot's openspec-image job published amd64-only. The check is the guard
that keeps the publisher and the seam's pull path in step.

The DOCKER CLI is the faked external system (a stub on PATH answering
`manifest inspect` from a control file); the script itself runs for real
(rule 6m). The real refresh-bot.yml and Makefile are pinned too: platforms
declared, verify steps on BOTH refresh paths, Makefile-only reach.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "scripts" / "openspec_manifest_check.py"
WORKFLOW = ROOT / ".github" / "workflows" / "refresh-bot.yml"
MAKEFILE = ROOT / "Makefile"

_PASS = 0
_FAIL = 0


def check(name: str, cond: bool, detail="") -> None:
    global _PASS, _FAIL
    if cond:
        _PASS += 1
        print(f"  ok  {name}")
    else:
        _FAIL += 1
        print(f"  FAIL {name}  [{str(detail)[:300]}]")


_DOCKER_STUB = """#!/bin/sh
case "$1 $2" in
  "manifest inspect")
    if [ -n "$FAKE_DOCKER_FAIL" ]; then echo "$FAKE_DOCKER_FAIL" >&2; exit 1; fi
    cat "$FAKE_MANIFEST"
    exit 0 ;;
esac
exit 0
"""


def _index(platforms: list[tuple[str, str]]) -> str:
    return json.dumps({
        "mediaType": "application/vnd.oci.image.index.v1+json",
        "manifests": [
            {"digest": f"sha256:{i:064x}", "platform": {"architecture": a, "os": o}}
            for i, (o, a) in enumerate(platforms)
        ],
    })


def run_stubbed(manifest_text: str | None = None,
                docker_fail: str = "", tag: str | None = "ghcr.io/o/r-openspec:openspec-abc123",
                extra: list[str] | None = None) -> subprocess.CompletedProcess:
    with tempfile.TemporaryDirectory() as tmp:
        stub_dir = Path(tmp) / "bin"
        stub_dir.mkdir()
        (stub_dir / "docker").write_text(_DOCKER_STUB)
        (stub_dir / "docker").chmod(0o755)
        env = dict(os.environ)
        env["PATH"] = f"{stub_dir}{os.pathsep}{env['PATH']}"
        if manifest_text is not None:
            manifest_file = Path(tmp) / "manifest.json"
            manifest_file.write_text(manifest_text)
            env["FAKE_MANIFEST"] = str(manifest_file)
        if docker_fail:
            env["FAKE_DOCKER_FAIL"] = docker_fail
        argv = [sys.executable, str(SCRIPT)]
        if tag is not None:
            argv += ["--tag", tag]
        if extra:
            argv += extra
        return subprocess.run(argv, capture_output=True, text=True, env=env)


# --- the verdict ------------------------------------------------------------

def test_an_amd64_only_manifest_is_refused():
    out = run_stubbed(_index([("linux", "amd64")]))
    check("an amd64-only published manifest goes red (exit 1)",
          out.returncode == 1, out.returncode)
    check("the refusal names the missing arm64", "arm64" in out.stdout, out.stdout)
    check("the refusal points at the publisher fix", "platforms" in out.stdout,
          out.stdout)


def test_a_multi_arch_manifest_passes():
    out = run_stubbed(_index([("linux", "amd64"), ("linux", "arm64")]))
    check("a multi-arch manifest passes (exit 0)", out.returncode == 0, out.stdout)
    check("it reports both answered platforms",
          "amd64" in out.stdout and "arm64" in out.stdout, out.stdout)


def test_a_single_image_manifest_is_refused():
    # Not an index at all — the exact one-architecture publication shape.
    out = run_stubbed(json.dumps({"mediaType": "application/vnd.docker.distribution.manifest.v2+json",
                                  "schemaVersion": 2}))
    check("a manifest list with no entries is refused (exit 1)",
          out.returncode == 1, out.returncode)
    check("it says the tag is a single-architecture publication",
          "single-architecture" in out.stdout, out.stdout)


def test_an_unreadable_manifest_exits_two():
    out = run_stubbed(docker_fail="errors:: manifest unknown: the tag was never pushed")
    check("a failing `docker manifest inspect` is a loud exit 2, never 1 or 0",
          out.returncode == 2, out.returncode)
    check("the report says it is undecidable", "undecidable" in out.stdout, out.stdout)

    out = run_stubbed("this is not json at all")
    check("non-JSON manifest output is a loud exit 2", out.returncode == 2, out.returncode)


def test_a_missing_tag_is_loud():
    out = run_stubbed(_index([("linux", "amd64"), ("linux", "arm64")]), tag=None)
    check("no --tag is a loud exit 2 — the check verifies ONE exact tag",
          out.returncode == 2 and "--tag is required" in out.stdout, out.stdout)


def test_extra_platforms_are_reported_but_not_required():
    out = run_stubbed(_index([("linux", "amd64"), ("linux", "arm64"), ("linux", "riscv64")]))
    check("extra answered platforms still pass", out.returncode == 0, out.stdout)


# --- the real publisher and wiring -------------------------------------------

def _job(wf: str, name: str) -> str:
    """One job block of refresh-bot.yml, from its 2-space key to the next."""
    m = re.search(rf"^  {name}:\n(.*?)(?=^  \S|\Z)", wf, re.M | re.S)
    if not m:
        raise AssertionError(f"job {name!r} not found in refresh-bot.yml")
    return m.group(1)


def _steps(job: str) -> list[tuple[str, bool]]:
    """(step name, has an `if:` gate) for every step of a job, in order."""
    steps: list[tuple[str, bool]] = []
    for part in re.split(r"^      - ", job, flags=re.M)[1:]:
        m = re.match(r"name: (.+)", part)
        name = m.group(1) if m else part.splitlines()[0]
        steps.append((name, bool(re.search(r"^        if:", part, re.M))))
    return steps


def test_the_publisher_declares_both_platforms():
    wf = WORKFLOW.read_text(encoding="utf-8")
    job = _job(wf, "openspec-image")
    check("the openspec-image build-push step declares both platforms",
          "platforms: linux/amd64,linux/arm64" in job, job[:400])


def test_both_refresh_paths_verify_the_manifest():
    wf = WORKFLOW.read_text(encoding="utf-8")
    job = _job(wf, "openspec-image")
    check("the job runs make openspec-manifest-check with the exact tag",
          "make openspec-manifest-check TAG=" in job, job[-500:])
    steps = _steps(job)
    names = [name for name, _ in steps]
    def _at(name_part: str) -> int:
        for i, n in enumerate(names):
            if name_part in n:
                return i
        raise AssertionError(f"no step named like {name_part!r} in {names}")
    push_i = _at("Build + push the OpenSpec image")
    skip_i = _at("already current")
    verify_i = _at("Verify the manifest answers both architectures")
    check("the verify step runs AFTER the publish and skip branches, ungated (so both paths hit it)",
          verify_i > push_i and verify_i > skip_i and not steps[verify_i][1],
          str(names))
    check("no step reaches the script past the Makefile",
          "scripts/openspec_manifest_check.py" not in job, "workflow direct call")


def test_the_target_is_makefile_only_and_wired():
    makefile = MAKEFILE.read_text(encoding="utf-8")
    phony_line = next(line for line in makefile.splitlines()
                      if line.startswith(".PHONY:") and "openspec-image " in line)
    check("openspec-manifest-check is a .PHONY target",
          "openspec-manifest-check" in phony_line, phony_line)
    check("its recipe reaches the product through python3 scripts/openspec_manifest_check.py",
          "python3 scripts/openspec_manifest_check.py --tag" in makefile, "")
    wf = WORKFLOW.read_text(encoding="utf-8")
    check("the workflow calls the make target (a target CI runs — rule 6m)",
          "make openspec-manifest-check" in wf, "")


def main() -> int:
    for t in (test_an_amd64_only_manifest_is_refused,
              test_a_multi_arch_manifest_passes,
              test_a_single_image_manifest_is_refused,
              test_an_unreadable_manifest_exits_two,
              test_a_missing_tag_is_loud,
              test_extra_platforms_are_reported_but_not_required,
              test_the_publisher_declares_both_platforms,
              test_both_refresh_paths_verify_the_manifest,
              test_the_target_is_makefile_only_and_wired):
        print(f"\n[{t.__name__}]")
        t()
    print(f"\n{_PASS} passed, {_FAIL} failed")
    return 1 if _FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
