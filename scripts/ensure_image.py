#!/usr/bin/env python3
"""Prepare the runner images for THIS revision — one code path, CI and local.

Both images are published to GHCR with a tag naming the inputs they were built
from (issue #141; the base image rule came with issue #135):

    base      ghcr.io/<owner>/trending-local-llms:dockerfile-<sha12>
    test      ghcr.io/<owner>/trending-local-llms-test:test-<sha12>
    openspec  ghcr.io/<owner>/trending-local-llms-openspec:openspec-<sha12>

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
    OPENSPEC_TAG=ghcr.io/.../trending-local-llms-openspec:openspec-abcdef123456

The base image IS the agent image (it bakes the Hermes CLI and the pinned nerve
plugin), so PUBLISHING it is a privileged act with its own pipeline (issue #206,
`.github/workflows/publish-agent-image.yml`) and three extra modes:

    ref          print the base hash tag + the consumer `:latest` ref
    push-check   prove the ambient credential can write the package, by starting an
                 empty blob upload — the registry's own refusal, seconds into the
                 run, instead of after the ten-minute build (llgenie measured
                 `permission_denied: create_package` here, PR #267)
    publish      build + push the base ONLY when its hash tag is absent
                 (`--force` rebuilds the same inputs); pushes BOTH the hash tag and
                 `:latest`, so this publisher and refresh-bot cannot disagree

Usage:  ensure_image.py
        [ensure|ensure-base|ensure-test|ensure-openspec|tags|ref|push-check|publish [--force]]
"""

from __future__ import annotations

import hashlib
import os
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# Files whose CONTENTS define each image, in a fixed order. A change to any of
# them changes the hash, which is what makes the published tag stale.
BASE_FILES = ("Dockerfile", "Dockerfile.test")
TEST_FILES = ("Dockerfile.test", "requirements-test.txt")
# The OpenSpec CLI image is independent of the base (Node, not Python), so its
# tag hashes only its own Dockerfile.
OPENSPEC_FILES = ("openspec/Dockerfile",)

IMAGE_REPO = os.environ.get("IMAGE_REPO", "ghcr.io/andyholst/trending-local-llms")
IMAGE = os.environ.get("IMAGE", "trending-local-llms:latest")
# The publish path (issue #206). `IMAGE_REPO` is `<host>/<owner>/<repo>`, so the
# consumer tag refresh-bot also pushes is IMAGE_REPO + ":latest"; the package path
# below is what the registry API takes. The host/scheme are overridable so the
# push probe can be exercised against a local server (the same allowance the tests
# already use for the `docker` CLI) — ghcr.io/https are the defaults.
REGISTRY_HOST = os.environ.get("IMAGE_REGISTRY_HOST", "ghcr.io")
REGISTRY_SCHEME = os.environ.get("IMAGE_REGISTRY_SCHEME", "https")
PUSH_TIMEOUT = int(os.environ.get("IMAGE_PUSH_TIMEOUT", "60"))
TEST_IMAGE = os.environ.get("TEST_IMAGE", "trending-local-llms-test:latest")
OPENSPEC_IMAGE = os.environ.get("OPENSPEC_IMAGE", "trending-local-llms-openspec:latest")


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


def openspec_hash() -> str:
    return _digest(OPENSPEC_FILES)


def openspec_tag() -> str:
    return f"{IMAGE_REPO}-openspec:openspec-{openspec_hash()}"


def ensure_openspec() -> str:
    """The OpenSpec CLI image: the one code path for `make openspec-*`."""
    if published(openspec_tag()):
        _run("docker", "pull", openspec_tag())
        _run("docker", "tag", openspec_tag(), OPENSPEC_IMAGE)
        return f"openspec: pulled {openspec_tag()} -> {OPENSPEC_IMAGE}"
    _run("docker", "build", "-f", "openspec/Dockerfile", "-t", OPENSPEC_IMAGE, "openspec")
    return (
        f"openspec: {openspec_tag()} is not published; built {OPENSPEC_IMAGE} "
        "from this revision's openspec/Dockerfile"
    )


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


def latest_tag() -> str:
    """The consumer tag every job pulls (`ghcr.io/<owner>/<repo>:latest`)."""
    return f"{IMAGE_REPO}:latest"


def package_path() -> str:
    """The registry package path (no host, no tag): `<owner>/<repo>`."""
    return IMAGE_REPO.split("/", 1)[1] if "/" in IMAGE_REPO else IMAGE_REPO


def push_check(host: str = "", scheme: str = "", token: str = "") -> str:
    """Prove the AMBIENT credential can create/write this package, before a build.

    Issue #206: publishing the agent image is a privileged act, and the failure it
    can hit is a CREDENTIAL one — `denied: permission_denied: The token provided
    does not match expected scopes` / `permission_denied: create_package` — which
    today only appears after the ten-minute build that re-downloads Hermes.
    llgenie measured exactly that on its own agent image (an owner PAT that is not
    an org member cannot create the package; the workflow's default
    `GITHUB_TOKEN` can).

    So this does the cheapest real write there is: it STARTS an empty blob upload
    (`POST /v2/<path>/blobs/uploads/`), which the registry authorises the same way
    it authorises a push, and reports the registry's own words when it refuses. No
    bytes are uploaded, nothing is created for a credential that may not create.
    """
    host = host or REGISTRY_HOST
    scheme = scheme or REGISTRY_SCHEME
    token = token or os.environ.get("GITHUB_TOKEN", "") or os.environ.get("GH_TOKEN", "")
    if not token:
        raise SystemExit(
            "[push-check] FAIL: no credential in the environment (GITHUB_TOKEN or GH_TOKEN).\n"
            f"  Publishing the agent image needs a token with `packages: write` for "
            f"{host}/{package_path()} — the workflow supplies the default GITHUB_TOKEN.\n"
            "  The image build was NOT started."
        )
    url = f"{scheme}://{host}/v2/{package_path()}/blobs/uploads/"
    req = urllib.request.Request(url, method="POST", data=b"",
                                headers={"Authorization": f"Bearer {token}"})
    try:
        with urllib.request.urlopen(req, timeout=PUSH_TIMEOUT) as resp:
            status = resp.status
    except urllib.error.HTTPError as e:  # the registry's own refusal, verbatim
        body = e.read().decode("utf-8", "replace").strip()[:300]
        raise SystemExit(
            f"[push-check] FAIL: the credential cannot push to {host}/{package_path()}: "
            f"HTTP {e.code} {body}\n"
            "  The image build was NOT started. Give the credential package-write, or "
            "publish with the workflow's default token (llgenie: a PAT that is not an "
            "org member is refused `permission_denied: create_package` here)."
        ) from None
    except urllib.error.URLError as e:
        raise SystemExit(f"[push-check] FAIL: {host} is unreachable: {e.reason}") from None
    if status not in (201, 202):
        raise SystemExit(f"[push-check] FAIL: unexpected HTTP {status} from {url}")
    return (f"[push-check] OK: the credential can write {host}/{package_path()} "
            f"(upload session accepted, HTTP {status}) — the build may proceed")


def publish(force: bool = False) -> str:
    """Build + push the agent (base) image, but ONLY when its tag is absent.

    The tag names this revision's inputs (`Dockerfile` + `Dockerfile.test`), so a
    re-run is a no-op unless the inputs changed — or unless `force` says so.
    Publishes BOTH refs the fleet reads: the hash tag (what `ensure` decides on)
    and `:latest` (what every bot job pulls), exactly as refresh-bot's build job
    does, so the two publishers cannot disagree about what is current.
    """
    tag = base_tag()
    if published(tag) and not force:
        return (f"publish: {tag} is already published — nothing to do "
                "(pass --force to rebuild the same inputs)")
    _run("docker", "build", "-t", IMAGE, "-t", tag, ".")
    _run("docker", "push", tag)
    _run("docker", "push", latest_tag())
    return f"publish: pushed {tag} and {latest_tag()}"


def main(argv: list[str]) -> int:
    action = argv[1] if len(argv) > 1 else "ensure"
    if action == "tags":
        print(f"BASE_TAG={base_tag()}")
        print(f"TEST_TAG={test_tag()}")
        print(f"OPENSPEC_TAG={openspec_tag()}")
        return 0
    if action == "ensure-openspec":
        print(ensure_openspec())
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
    # ---- the publish path (issue #206): a deliberate, guarded act ----
    if action == "ref":
        print(base_tag())
        print(latest_tag())
        return 0
    if action == "push-check":
        print(push_check())
        return 0
    if action == "publish":
        print(publish(force="--force" in argv[2:]))
        return 0
    print(
        "usage: ensure_image.py "
        "[ensure|ensure-base|ensure-test|ensure-openspec|tags|ref|push-check|publish [--force]]",
        file=sys.stderr,
    )
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
