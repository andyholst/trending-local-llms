#!/usr/bin/env python3
"""Behavioural tests for scripts/ensure_image.py (issues #141, #155).

The script decides whether the base and test images are PULLED (the published tag
names this revision's inputs) or BUILT here — the one code path every workflow and
developer uses. Until now only its static shape was asserted, so a drifted hash
recipe or an inverted pull/build decision would have passed `make test`.

The DOCKER CLI is the faked external system (a script on PATH that records its
arguments and answers `manifest inspect` / `image inspect` from a control file);
the script itself runs for real, in the repo, against the real Dockerfile(s).
"""
from __future__ import annotations

import hashlib
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "scripts" / "ensure_image.py"
IMAGE_REPO = "ghcr.io/andyholst/trending-local-llms"

_PASS = 0
_FAIL = 0

# One `docker` stub per test run: records every call, answers `manifest
# inspect <ref>` / `image inspect <ref>` by looking <ref> up in a file of
# "published/available" refs. It ALSO records every tag a `build -t` / `tag`
# creates and REFUSES to `push` a ref that was never tagged — real docker prints
# `tag does not exist` for that (measured on run 38683713224), and a stub that
# accepted the push hid exactly that publish bug.
_DOCKER_STUB = """#!/bin/sh
echo "$@" >> "$FAKE_DOCKER_LOG"
case "$1" in
  build)
    prev=""
    for arg in "$@"; do
      [ "$prev" = "-t" ] && echo "$arg" >> "$FAKE_DOCKER_TAGS"
      prev="$arg"
    done ;;
  tag) echo "$3" >> "$FAKE_DOCKER_TAGS" ;;
  manifest|image)
    case "$2" in
      inspect)
        if grep -qxF "$3" "$FAKE_DOCKER_AVAILABLE"; then exit 0; else exit 1; fi ;;
    esac ;;
  push)
    if grep -qxF "$2" "$FAKE_DOCKER_TAGS" 2>/dev/null; then exit 0; else echo "tag does not exist: $2" >&2; exit 1; fi ;;
esac
exit 0
"""


def check(name, cond, detail=""):
    global _PASS, _FAIL
    if cond:
        _PASS += 1
        print(f"  ok  {name}")
    else:
        _FAIL += 1
        print(f"  FAIL {name}" + (f"  [{detail}]" if detail else ""))


def _run(args, available=(), env_extra=None):
    """Run the real script with the docker CLI faked; return (rc, calls, out).

    `env_extra` lets a caller add the seams a mode needs (issue #206's push probe
    points `IMAGE_REGISTRY_HOST` at a local server); everything else is unchanged.
    """
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        stub = td / "docker"
        stub.write_text(_DOCKER_STUB)
        stub.chmod(0o755)
        log = td / "calls.log"
        log.write_text("")
        avail = td / "available.txt"
        avail.write_text("\n".join(available) + "\n")
        tags = td / "tags.txt"
        tags.write_text("")
        env = {
            **os.environ,
            "PATH": f"{td}{os.pathsep}{os.environ['PATH']}",
            "FAKE_DOCKER_LOG": str(log),
            "FAKE_DOCKER_AVAILABLE": str(avail),
            "FAKE_DOCKER_TAGS": str(tags),
            "IMAGE_REPO": IMAGE_REPO,
            **(env_extra or {}),
        }
        proc = subprocess.run([sys.executable, str(SCRIPT), *args],
                              cwd=ROOT, capture_output=True, text=True, env=env)
        calls = [l.split() for l in log.read_text().splitlines() if l.strip()]
    return proc.returncode, calls, proc.stdout + proc.stderr


def _expected_hash(parts) -> str:
    """The recipe, computed independently: file contents concatenated, first 12."""
    blob = b"".join((ROOT / p).read_bytes() for p in parts)
    return hashlib.sha256(blob).hexdigest()[:12]


def test_tags_are_the_hash_of_this_revisions_inputs():
    """The tags must be the published ones for this revision, or a pipeline that
    could have pulled its own image rebuilds it (and vice versa)."""
    # Given the inputs each image is defined by
    base_hash = _expected_hash(["Dockerfile", "Dockerfile.test"])
    test_hash = hashlib.sha256(
        b"".join((ROOT / p).read_bytes() for p in ["Dockerfile.test", "requirements-test.txt"])
        + f"base={base_hash}".encode()
    ).hexdigest()[:12]

    # When  the script prints the tags it decides on
    proc = subprocess.run([sys.executable, str(SCRIPT), "tags"],
                          cwd=ROOT, capture_output=True, text=True)
    out = dict(l.split("=", 1) for l in proc.stdout.splitlines() if "=" in l)

    # Then  they are the independent hashes above
    check("tags: exit 0", proc.returncode == 0, proc.stdout + proc.stderr)
    check("tags: BASE_TAG is sha12(Dockerfile + Dockerfile.test)",
          out.get("BASE_TAG") == f"{IMAGE_REPO}:dockerfile-{base_hash}",
          f"{out.get('BASE_TAG')} vs {base_hash}")
    check("tags: TEST_TAG folds in Dockerfile.test, requirements-test.txt and the base",
          out.get("TEST_TAG") == f"{IMAGE_REPO}-test:test-{test_hash}",
          f"{out.get('TEST_TAG')} vs {test_hash}")


def test_openspec_image_is_hash_tagged_and_pulled_or_built():
    """The OpenSpec CLI image follows the SAME rule as the other two (issue #172).

    `make openspec-*` must pull the tag naming this revision's
    openspec/Dockerfile when it is published, and build it here when it is not —
    with no host `npm install` anywhere, so CI and a developer run the same CLI.
    """
    # Given the CLI image's own input (its Dockerfile alone — it is Node, not Python)
    ospec_hash = _expected_hash(["openspec/Dockerfile"])
    ospec_tag = f"{IMAGE_REPO}-openspec:openspec-{ospec_hash}"

    # When  the tags are printed
    proc = subprocess.run([sys.executable, str(SCRIPT), "tags"],
                          cwd=ROOT, capture_output=True, text=True)
    out = dict(l.split("=", 1) for l in proc.stdout.splitlines() if "=" in l)

    # Then  the tag names this revision's openspec/Dockerfile
    check("tags: OPENSPEC_TAG is sha12(openspec/Dockerfile)",
          out.get("OPENSPEC_TAG") == ospec_tag, f"{out.get('OPENSPEC_TAG')} vs {ospec_tag}")

    # Given a registry without that tag
    rc, calls, log = _run(["ensure-openspec"], available=[])

    # Then  the CLI image is built here from its own Dockerfile
    check("ensure-openspec (unpublished): exit 0", rc == 0, log)
    check("ensure-openspec (unpublished): builds from openspec/Dockerfile",
          ["build", "-f", "openspec/Dockerfile", "-t", "trending-local-llms-openspec:latest", "openspec"] in calls,
          str(calls))
    check("ensure-openspec (unpublished): never pulls", not any(c[:1] == ["pull"] for c in calls), str(calls))

    # Given the tag IS published
    rc, calls, log = _run(["ensure-openspec"], available=[ospec_tag])

    # Then  it is pulled and tagged locally, never rebuilt
    check("ensure-openspec (published): exit 0", rc == 0, log)
    check("ensure-openspec (published): pulls the published tag", ["pull", ospec_tag] in calls, str(calls))
    check("ensure-openspec (published): tags it locally",
          ["tag", ospec_tag, "trending-local-llms-openspec:latest"] in calls, str(calls))
    check("ensure-openspec (published): never rebuilds", not any(c[:1] == ["build"] for c in calls), str(calls))

    # And there is exactly ONE way to run the CLI: no host npm install anywhere.
    # Only places a COMMAND can run: the Makefile, the shell scripts, the
    # workflows. A markdown/docstring sentence that says "no host npm install"
    # (the README template lives in update_trending.py) is not a second path.
    npm_hits = []
    for p in (
        list(ROOT.glob("Makefile"))
        + [f for f in (ROOT / "scripts").glob("*.sh") if f.is_file()]
        + list((ROOT / ".github" / "workflows").glob("*.yml"))
    ):
        for line in p.read_text(errors="ignore").splitlines():
            # Comments (Makefile `#`, YAML `#`) may SAY "no host npm install";
            # only a line that would RUN it counts.
            if line.lstrip().startswith("#"):
                continue
            if "npm install" in line:
                npm_hits.append(f"{p.relative_to(ROOT)}: {line.strip()}")
    check("openspec: no host npm install for the CLI (the image is the one path)",
          not npm_hits, str(npm_hits))


def test_ensure_base_builds_only_when_the_tag_is_not_published():
    """Not published -> build from this revision's Dockerfile. Published -> pull."""
    base_tag = f"{IMAGE_REPO}:dockerfile-{_expected_hash(['Dockerfile', 'Dockerfile.test'])}"

    # Given a registry without the tag
    rc, calls, out = _run(["ensure-base"], available=[])

    # Then  the base is BUILT here (never a pull of something absent)
    check("ensure-base (unpublished): exit 0", rc == 0, out)
    check("ensure-base (unpublished): builds the base image",
          ["build", "-t", "trending-local-llms:latest", "."] in calls, str(calls))
    check("ensure-base (unpublished): never pulls",
          not any(c[:1] == ["pull"] for c in calls), str(calls))

    # Given the tag IS published
    rc, calls, out = _run(["ensure-base"], available=[base_tag])

    # Then  it is pulled and tagged locally — no rebuild
    check("ensure-base (published): exit 0", rc == 0, out)
    check("ensure-base (published): pulls the published tag",
          ["pull", base_tag] in calls, str(calls))
    check("ensure-base (published): tags it as the local base",
          ["tag", base_tag, "trending-local-llms:latest"] in calls, str(calls))
    check("ensure-base (published): does NOT build",
          not any(c[:1] == ["build"] for c in calls), str(calls))


def test_ensure_test_pulls_or_builds_on_that_base():
    """The test image's own tag decides; when it must be built and the base is
    missing, the base is ensured first (Dockerfile.test layers on `$(IMAGE)`)."""
    base_hash = _expected_hash(["Dockerfile", "Dockerfile.test"])
    base_tag = f"{IMAGE_REPO}:dockerfile-{base_hash}"
    test_hash = hashlib.sha256(
        b"".join((ROOT / p).read_bytes() for p in ["Dockerfile.test", "requirements-test.txt"])
        + f"base={base_hash}".encode()
    ).hexdigest()[:12]
    test_tag = f"{IMAGE_REPO}-test:test-{test_hash}"

    # Given the published test image
    rc, calls, out = _run(["ensure-test"], available=[test_tag])

    # Then  it is pulled and tagged, with no build at all
    check("ensure-test (published): exit 0", rc == 0, out)
    check("ensure-test (published): pulls the test tag",
          ["pull", test_tag] in calls, str(calls))
    check("ensure-test (published): does NOT build",
          not any(c[:1] == ["build"] for c in calls), str(calls))

    # Given NOTHING published and no local base either
    rc, calls, out = _run(["ensure-test"], available=[])

    # Then  the base is built first, then the test image on it
    check("ensure-test (fresh): exit 0", rc == 0, out)
    check("ensure-test (fresh): builds the base first",
          ["build", "-t", "trending-local-llms:latest", "."] in calls, str(calls))
    check("ensure-test (fresh): builds the test image on that base",
          ["build", "-f", "Dockerfile.test", "--build-arg",
           "BASE_IMAGE=trending-local-llms:latest", "-t", "trending-local-llms-test:latest", "."]
          in calls, str(calls))
    check("ensure-test (fresh): the base build comes first",
          calls.index(["build", "-t", "trending-local-llms:latest", "."]) <
          len(calls) - 1, str(calls))

    # Given a LOCAL base already present but nothing published
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        stub = td / "docker"
        stub.write_text(_DOCKER_STUB)
        stub.chmod(0o755)
        log = td / "calls.log"
        log.write_text("")
        avail = td / "available.txt"
        # `image inspect` answers from the same file: pretend the base is present.
        avail.write_text("trending-local-llms:latest\n")
        env = {**os.environ, "PATH": f"{td}{os.pathsep}{os.environ['PATH']}",
               "FAKE_DOCKER_LOG": str(log), "FAKE_DOCKER_AVAILABLE": str(avail),
               "IMAGE_REPO": IMAGE_REPO}
        proc = subprocess.run([sys.executable, str(SCRIPT), "ensure-test"],
                              cwd=ROOT, capture_output=True, text=True, env=env)
        calls = [l.split() for l in log.read_text().splitlines() if l.strip()]
    # Then  it is NOT rebuilt (a present base is reused)
    check("ensure-test (local base present): exit 0", proc.returncode == 0,
          proc.stdout + proc.stderr)
    check("ensure-test (local base present): reuses the base",
          not any(c[:2] == ["build", "-t"] for c in calls), str(calls))
    check("ensure-test (local base present): still builds the test image",
          any(c[:2] == ["build", "-f"] for c in calls), str(calls))


def test_wired_into_make_test():
    """The suite runs under `make test` (rule 6d)."""
    mk = (ROOT / "Makefile").read_text()
    check("make: the ensure_image tests run in the suite",
          "python3 tests/test_ensure_image.py" in mk, "")
    check("make: `image-ensure` calls the script the tests exercise",
          "image-ensure:\n\tpython3 scripts/ensure_image.py ensure" in mk, "")


def main() -> int:
    print("runner-image decision (scripts/ensure_image.py)")
    test_tags_are_the_hash_of_this_revisions_inputs()
    test_openspec_image_is_hash_tagged_and_pulled_or_built()
    test_ensure_base_builds_only_when_the_tag_is_not_published()
    test_ensure_test_pulls_or_builds_on_that_base()
    test_wired_into_make_test()
    print(f"\nPASSED {_PASS} | FAILED {_FAIL}")
    return 1 if _FAIL else 0


if __name__ == "__main__":
    raise SystemExit(main())
