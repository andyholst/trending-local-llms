#!/usr/bin/env python3
"""Behavioural tests for scripts/image_manifest_check.py (issue #958).

The Hermes base image and the test image were published amd64-only while
ensure_image's published() answers "pull it" on ANY host — so a fresh arm64
checkout died at `docker pull` with "no matching manifest for
linux/arm64/v8" (the #767 failure shape, re-measured for base/test on
2026-11-14). The fix is the #919 pattern applied to BOTH publishers:
platforms declared, the manifest verified UNGATED on both refresh paths, and
the arm64 variant proven to RUN. The manifest verdict is ONE implementation
shared with the OpenSpec seam — a second copy is the drift this suite refuses.

The DOCKER CLI is the faked external system (a stub on PATH; rule 6m); the
script itself runs for real. The real refresh-bot.yml and Makefile are pinned.
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
SCRIPT = ROOT / "scripts" / "image_manifest_check.py"
OPENSPEC_SCRIPT = ROOT / "scripts" / "openspec_manifest_check.py"
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
                docker_fail: str = "",
                tag: str | None = "ghcr.io/o/r:trending-local-llms:dockerfile-abc123",
                label: str = "base",
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
            argv += ["--tag", tag, "--label", label]
        if extra:
            argv += extra
        return subprocess.run(argv, capture_output=True, text=True, env=env)


# --- the verdict --------------------------------------------------------------

def test_an_amd64_only_manifest_is_refused():
    out = run_stubbed(_index([("linux", "amd64")]))
    check("an amd64-only base manifest goes red (exit 1)",
          out.returncode == 1, out.returncode)
    check("the refusal names the missing arm64", "arm64" in out.stdout, out.stdout)
    check("the refusal points at the publisher fix", "platforms" in out.stdout,
          out.stdout)
    check("the report carries the seam's label", "[base]" in out.stdout,
          out.stdout)


def test_a_multi_arch_manifest_passes():
    out = run_stubbed(_index([("linux", "amd64"), ("linux", "arm64")]))
    check("a multi-arch manifest passes (exit 0)", out.returncode == 0, out.stdout)
    check("it reports both answered platforms",
          "amd64" in out.stdout and "arm64" in out.stdout, out.stdout)


def test_a_single_image_manifest_is_refused():
    out = run_stubbed(json.dumps({"mediaType": "application/vnd.docker.distribution.manifest.v2+json",
                                  "schemaVersion": 2}))
    check("a manifest with no manifest list is refused (exit 1)",
          out.returncode == 1, out.returncode)
    check("it says the tag is a single-architecture publication",
          "single-architecture" in out.stdout, out.stdout)


def test_an_unreadable_manifest_exits_two():
    out = run_stubbed(docker_fail="errors:: manifest unknown: the tag was never pushed")
    check("a failing `docker manifest inspect` is a loud exit 2", out.returncode == 2,
          out.returncode)
    check("the report says it is undecidable", "undecidable" in out.stdout, out.stdout)


def test_a_missing_tag_is_loud():
    out = run_stubbed(_index([("linux", "amd64"), ("linux", "arm64")]), tag=None)
    check("no --tag is a loud exit 2 — the check verifies ONE exact tag",
          out.returncode == 2 and "--tag is required" in out.stdout, out.stdout)


# --- the real publishers and wiring -------------------------------------------

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


def _assert_after(steps, verify_part: str, must_follow: list[str]) -> int:
    names = [name for name, _ in steps]
    def _at(part: str) -> int:
        for i, n in enumerate(names):
            if part in n:
                return i
        raise AssertionError(f"no step named like {part!r} in {names}")
    i = _at(verify_part)
    for part in must_follow:
        j = _at(part)
        if not i > j:
            return j
    return i


def test_both_publishers_declare_both_platforms():
    wf = WORKFLOW.read_text(encoding="utf-8")
    for job_name in ("build", "test-image"):
        job = _job(wf, job_name)
        check(f"the {job_name} build-push step declares both platforms",
              "platforms: linux/amd64,linux/arm64" in job, job[:400])
        check(f"the {job_name} job has headroom for QEMU arm64 layers",
              "timeout-minutes: 45" in job, job[:200])


def test_both_paths_verify_base_and_test_manifests():
    wf = WORKFLOW.read_text(encoding="utf-8")
    cases = {
        "build": ("Build + push image", "Image already current",
                  "Verify the base manifest", "make image-manifest-check TAG=\"${{ steps.decide.outputs.base_tag }}\""),
        "test-image": ("Build + push the test image", "already current",
                       "Verify the test manifest", "make image-manifest-check TAG=\"${{ needs.build.outputs.test_tag }}\""),
    }
    for job_name, (push_part, skip_part, verify_part, tag_call) in cases.items():
        job = _job(wf, job_name)
        steps = _steps(job)
        names = [name for name, _ in steps]
        def _at(part: str) -> int:
            for i, n in enumerate(names):
                if part in n:
                    return i
            raise AssertionError(f"no step named like {part!r} in {job_name}: {names}")
        push_i, skip_i, verify_i = _at(push_part), _at(skip_part), _at(verify_part)
        check(f"{job_name}: the verify step runs after BOTH the publish and skip branches, ungated",
              verify_i > push_i and verify_i > skip_i and not steps[verify_i][1],
              str(names))
        check(f"{job_name}: the verify names the exact tag of this revision",
              tag_call in job, job[-600:])
        check(f"{job_name}: no step reaches the script past the Makefile",
              "scripts/image_manifest_check.py" not in job, "workflow direct call")


def test_the_arm64_run_proof_steps_exist():
    wf = WORKFLOW.read_text(encoding="utf-8")
    check("the base job runs hermes --version from the arm64 variant of the verified tag",
          "docker run --rm --platform linux/arm64 \"${{ steps.decide.outputs.base_tag }}\" hermes --version"
          in _job(wf, "build"), "")
    check("the test-image job runs the arm64 run-proof through make (rule 6m — a raw "
          "python3 -c in a workflow step is the defect test_makefile_only refuses on #1114)",
          "make test-image-smoke" in _job(wf, "test-image"), _job(wf, "test-image")[:200])
    check("the arm64 docker run lives in the Makefile target, not the workflow",
          "docker run --rm --platform linux/arm64 \"$(TAG)\"" in MAKEFILE.read_text(encoding="utf-8")
          and "import pytest" in MAKEFILE.read_text(encoding="utf-8")
          and "python3 -c" not in _job(wf, "test-image"), "")
    for job_name, verify_part, proof_part in (("build", "Verify the base manifest", "Prove the arm64 base"),
                                              ("test-image", "Verify the test manifest", "Prove the arm64 test")):
        steps = _steps(_job(wf, job_name))
        names = [n for n, _ in steps]
        vi = next(i for i, n in enumerate(names) if verify_part in n)
        pi = next(i for i, n in enumerate(names) if proof_part in n)
        check(f"{job_name}: the arm64 run proof runs after the manifest check (never before it)",
              pi > vi, str(names))


def test_the_verdict_is_one_implementation():
    openspec_src = OPENSPEC_SCRIPT.read_text(encoding="utf-8")
    check("the OpenSpec seam delegates to the shared unit",
          "from image_manifest_check import" in openspec_src, openspec_src[:200])
    check("it carries no second copy of the manifest-reading logic",
          "_read_manifest" not in openspec_src and "subprocess" not in openspec_src,
          "")
    copies = [p.relative_to(ROOT) for p in (ROOT / "scripts").glob("*.py")
              if p.name != "image_manifest_check.py" and "def _read_manifest" in p.read_text(encoding="utf-8")]
    check("no other script re-implements the manifest read", not copies, copies)


def test_the_target_is_makefile_only_and_wired():
    makefile = MAKEFILE.read_text(encoding="utf-8")
    phony_line = next(line for line in makefile.splitlines()
                      if line.startswith(".PHONY:") and "openspec-image " in line)
    check("image-manifest-check is a .PHONY target",
          "image-manifest-check" in phony_line, phony_line)
    check("test-image-smoke is a .PHONY target (the arm64 run-proof the workflow calls)",
          "test-image-smoke" in phony_line, phony_line)
    check("its recipe reaches the product through python3 scripts/image_manifest_check.py --tag",
          "python3 scripts/image_manifest_check.py --tag" in makefile, "")
    wf = WORKFLOW.read_text(encoding="utf-8")
    check("the workflow calls the make target (a target CI runs — rule 6m)",
          "make image-manifest-check" in wf, "")


def main() -> int:
    for t in (test_an_amd64_only_manifest_is_refused,
              test_a_multi_arch_manifest_passes,
              test_a_single_image_manifest_is_refused,
              test_an_unreadable_manifest_exits_two,
              test_a_missing_tag_is_loud,
              test_both_publishers_declare_both_platforms,
              test_both_paths_verify_base_and_test_manifests,
              test_the_arm64_run_proof_steps_exist,
              test_the_verdict_is_one_implementation,
              test_the_target_is_makefile_only_and_wired):
        print(f"\n[{t.__name__}]")
        t()
    print(f"\n{_PASS} passed, {_FAIL} failed")
    return 1 if _FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
