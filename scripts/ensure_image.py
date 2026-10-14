#!/usr/bin/env python3
"""Prepare the runner images for THIS revision — one code path, CI and local.

Both images are published to GHCR with a tag naming the inputs they were built
from (issue #141; the base image rule came with issue #135):

    base  ghcr.io/<owner>/trending-local-llms:dockerfile-<sha12>
    test  ghcr.io/<owner>/trending-local-llms-test:test-<sha12>

`ensure` views those tags as the source of truth: when the tag for this revision
is published the image is PULLED (byte-identical to what CI runs, no rebuild);
when it is not, the image is BUILT here — the base from this `Dockerfile`, the
test image on that base. Nothing else decides, so a workflow never needs an
inline `docker pull`/`docker build` and a stale local pull cannot stand in for
the revision's own base (measured: a cached GHCR base without the pinned nerve
plugin produced a test image the credential guard could only fail on).

`tags` prints the tags it expects, for the publisher's rebuild decision:

    BASE_TAG=ghcr.io/.../trending-local-llms:dockerfile-abcdef123456
    TEST_TAG=ghcr.io/.../trending-local-llms-test:test-abcdef123456

Usage:  ensure_image.py [ensure|ensure-base|ensure-test|tags]
"""

from __future__ import annotations

import hashlib
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# Files whose CONTENTS define each image, in a fixed order. A change to any of
# them changes the hash, which is what makes the published tag stale.
BASE_FILES = ("Dockerfile", "Dockerfile.test")
TEST_FILES = ("Dockerfile.test", "requirements-test.txt")

IMAGE_REPO = os.environ.get("IMAGE_REPO", "ghcr.io/andyholst/trending-local-llms")
IMAGE = os.environ.get("IMAGE", "trending-local-llms:latest")
TEST_IMAGE = os.environ.get("TEST_IMAGE", "trending-local-llms-test:latest")


def _digest(parts: tuple[str, ...]) -> str:
    # The CONTENTS concatenated in order, then sha256 — byte-identical to
    # `cat <files> | sha256sum | cut -c1-12`, which is how the tags already
    # published for the current revision were computed. Do not add separators:
    # a different recipe would invalidate every published tag on upgrade.
    return hashlib.sha256(b"".join(Path(ROOT, n).read_bytes() for n in parts)).hexdigest()[:12]


def base_hash() -> str:
    return _digest(BASE_FILES)


def test_hash() -> str:
    # The test image is layered on the base, so the base hash is an input too:
    # a base rebuild must rebuild the test image rather than serve a stale layer.
    blob = b"".join(Path(ROOT, n).read_bytes() for n in TEST_FILES)
    return hashlib.sha256(blob + f"base={base_hash()}".encode()).hexdigest()[:12]


def base_tag() -> str:
    return f"{IMAGE_REPO}:dockerfile-{base_hash()}"


def test_tag() -> str:
    return f"{IMAGE_REPO}-test:test-{test_hash()}"


def _run(*cmd: str) -> None:
    print(f"  $ {' '.join(cmd)}", flush=True)
    subprocess.run(list(cmd), cwd=ROOT, check=True)


def published(ref: str) -> bool:
    """True when the registry can serve the tag (public packages: no login)."""
    return subprocess.run(
        ["docker", "manifest", "inspect", ref],
        cwd=ROOT, capture_output=True, text=True,
    ).returncode == 0


def ensure_base() -> str:
    if published(base_tag()):
        _run("docker", "pull", base_tag())
        _run("docker", "tag", base_tag(), IMAGE)
        return f"base: pulled {base_tag()} -> {IMAGE}"
    _run("docker", "build", "-t", IMAGE, ".")
    return f"base: {base_tag()} is not published; built {IMAGE} from this revision's Dockerfile"


def base_ready() -> bool:
    return subprocess.run(
        ["docker", "image", "inspect", IMAGE], capture_output=True
    ).returncode == 0


def ensure_test() -> str:
    if published(test_tag()):
        _run("docker", "pull", test_tag())
        _run("docker", "tag", test_tag(), TEST_IMAGE)
        return f"test: pulled {test_tag()} -> {TEST_IMAGE}"
    if not base_ready():
        note = ensure_base()
        print(f"  ({note})")
    _run("docker", "build", "-f", "Dockerfile.test",
         "--build-arg", f"BASE_IMAGE={IMAGE}", "-t", TEST_IMAGE, ".")
    return f"test: {test_tag()} is not published; built {TEST_IMAGE} on {IMAGE}"


def main(argv: list[str]) -> int:
    action = argv[1] if len(argv) > 1 else "ensure"
    if action == "tags":
        print(f"BASE_TAG={base_tag()}")
        print(f"TEST_TAG={test_tag()}")
        return 0
    if action == "ensure-base":
        print(ensure_base())
        return 0
    if action == "ensure-test":
        print(ensure_test())
        return 0
    if action == "ensure":
        print(ensure_base())
        print(ensure_test())
        return 0
    print("usage: ensure_image.py [ensure|ensure-base|ensure-test|tags]", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
