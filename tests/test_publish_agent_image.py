#!/usr/bin/env python3
"""Publishing the agent image is a deliberate, guarded act (issue #206).

The base image IS the agent image — it bakes the Hermes CLI and the pinned nerve
plugin, and every bot job runs inside it — so publishing it must not be a side
effect of a data refresh, and the credential must be proven BEFORE the ten-minute
build that re-downloads Hermes.

Two halves are locked here:

1. `scripts/ensure_image.py`'s publish modes, run for real with the `docker` CLI
   faked (the harness `tests/test_ensure_image.py` already uses) and, for the push
   probe, a LOCAL HTTP SERVER — a stand-in for the registry, never a mock of the
   code under test:
     - `ref` prints this revision's hash tag and the consumer `:latest` ref;
     - `publish` is a NO-OP when that tag is already published (re-runs cost
       seconds, not minutes) and pushes BOTH refs when it is not;
     - `--force` rebuilds the same inputs on demand;
     - `push-check` fails loudly with no credential, and reports the registry's OWN
       refusal (llgenie's measured `permission_denied: create_package`) instead of
       starting a build that cannot push.
2. `.github/workflows/publish-agent-image.yml`'s shape: dispatch-only, the
   owner/collaborator guard FIRST and before any secret, the default token (not a
   PAT), the push check before the build, and no merge anywhere.

Run:  python3 tests/test_publish_agent_image.py   or   make test
"""
from __future__ import annotations

import json
import re
import sys
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WF = ROOT / ".github" / "workflows" / "publish-agent-image.yml"
MAKEFILE = ROOT / "Makefile"

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_ensure_image import _run  # the real-script + fake-docker harness  # noqa: E402

_PASS = 0
_FAIL = 0


def check(name, cond, detail: object = ""):
    global _PASS, _FAIL
    if cond:
        _PASS += 1
        print(f"  ok  {name}")
    else:
        _FAIL += 1
        print(f"  FAIL {name}" + (f"  [{detail}]" if detail else ""))


# ------------------------------------------------------- the script's modes ---

def test_ref_prints_the_hash_tag_and_the_consumer_tag():
    """The two refs the fleet reads, from the one script that owns the tags."""

    # Given the script
    # When  `ref` runs
    rc, _, out = _run(["ref"])

    # Then  it prints this revision's hash tag and `:latest`, matching `tags`
    rc_tags, _, out_tags = _run(["tags"])
    base = dict(l.split("=", 1) for l in out_tags.splitlines() if "=" in l).get("BASE_TAG")

    check("ref: exit 0", rc == 0, out)
    check("ref: it prints the same BASE_TAG as `tags` (one definition)",
          base is not None and base in out, f"{base} / {out}")
    check("ref: it prints the consumer :latest ref the bots pull",
          re.search(r"ghcr\.io/[^:\s]+:latest", out) is not None, out)


def test_publish_is_a_noop_when_this_revision_is_already_published():
    """A re-run must cost seconds — the tag already names these inputs."""

    # Given the hash tag is on the registry
    rc_tags, _, out_tags = _run(["tags"])
    base = dict(l.split("=", 1) for l in out_tags.splitlines() if "=" in l)["BASE_TAG"]

    # When  publish runs
    rc, calls, out = _run(["publish"], available=[base])

    # Then  it builds nothing and pushes nothing
    check("publish(no-op): exit 0", rc == 0, out)
    check("publish(no-op): it says the tag is already published",
          "already published" in out, out)
    check("publish(no-op): no docker build ran",
          not any(c[:1] == ["build"] for c in calls), calls)
    check("publish(no-op): nothing was pushed",
          not any(c[:1] == ["push"] for c in calls), calls)


def test_publish_builds_and_pushes_both_refs_when_absent():
    """The hash tag is what `ensure` decides on; `:latest` is what jobs pull."""

    # Given this revision's tag is NOT on the registry
    # When  publish runs
    rc, calls, out = _run(["publish"], available=[])

    # Then  it builds once, tags both refs and pushes both
    builds = [c for c in calls if c[:1] == ["build"]]
    pushes = [c for c in calls if c[:1] == ["push"]]
    rc_tags, _, out_tags = _run(["tags"])
    base = dict(l.split("=", 1) for l in out_tags.splitlines() if "=" in l)["BASE_TAG"]

    check("publish: exit 0", rc == 0, out)
    check("publish: exactly one build", len(builds) == 1, calls)
    check("publish: the build carries the hash tag",
          builds and base in builds[0], builds)
    check("publish: it pushes the hash tag",
          any(base in " ".join(c) for c in pushes), pushes)
    check("publish: it pushes the consumer :latest ref too",
          any(c[-1].endswith(":latest") for c in pushes), pushes)
    check("publish: it says what it pushed", "pushed" in out, out)


def test_force_rebuilds_the_same_inputs_on_demand():
    """FORCE=1 is the one way to republish an unchanged revision."""

    # Given the tag IS published
    rc_tags, _, out_tags = _run(["tags"])
    base = dict(l.split("=", 1) for l in out_tags.splitlines() if "=" in l)["BASE_TAG"]

    # When  publish --force runs
    rc, calls, out = _run(["publish", "--force"], available=[base])

    # Then  it builds and pushes anyway
    check("publish --force: exit 0", rc == 0, out)
    check("publish --force: it built", any(c[:1] == ["build"] for c in calls), calls)
    check("publish --force: it pushed", any(c[:1] == ["push"] for c in calls), calls)


# --------------------------------------------------------- the push probe -----

class _Registry(BaseHTTPRequestHandler):
    """A local stand-in for the registry's blob-upload endpoint."""

    status = 202
    body = b'{"errors":[{"code":"DENIED","message":"permission_denied: create_package"}]}'
    seen: list[tuple[str, str]] = []

    def do_POST(self):  # noqa: N802 (BaseHTTPRequestHandler's name)
        type(self).seen.append((self.path, self.headers.get("Authorization", "")))
        self.send_response(type(self).status)
        self.send_header("Content-Type", "application/json")
        payload = b"" if type(self).status < 400 else type(self).body
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, *a):  # keep the test output clean
        pass


def _serve(status):
    _Registry.status = status
    _Registry.seen = []
    httpd = HTTPServer(("127.0.0.1", 0), _Registry)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    return httpd, f"127.0.0.1:{httpd.server_address[1]}"


def test_push_check_proves_the_credential_before_the_build():
    """The probe: the cheapest real write, and the registry's own refusal."""

    # Given no credential at all
    rc, _, out = _run(["push-check"], env_extra={"GITHUB_TOKEN": "", "GH_TOKEN": ""})

    # When/Then  it fails loudly and names what is missing, without touching a registry
    check("push-check(no token): non-zero", rc != 0, out)
    check("push-check(no token): it names the credential",
          "GITHUB_TOKEN" in out, out)
    check("push-check(no token): it says the build was not started",
          "build was NOT started" in out or "was NOT started" in out, out)

    # Given a credential the registry accepts
    httpd, host = _serve(202)

    # When  the probe runs against it
    rc, _, out = _run(["push-check"], env_extra={
        "GITHUB_TOKEN": "stub-token",
        "IMAGE_REGISTRY_HOST": host,
        "IMAGE_REGISTRY_SCHEME": "http",
    })

    # Then  it starts an upload session for the package and says the build may proceed
    path, auth = _Registry.seen[0] if _Registry.seen else ("", "")
    httpd.shutdown()
    check("push-check(accepted): exit 0", rc == 0, out)
    check("push-check(accepted): it POSTs the blob-upload endpoint",
          path == "/v2/andyholst/trending-local-llms/blobs/uploads/", path)
    check("push-check(accepted): it carries the ambient credential",
          auth == "Bearer stub-token", auth)
    check("push-check(accepted): it says the build may proceed",
          "may proceed" in out, out)

    # Given a credential the registry REFUSES (llgenie's measured failure)
    httpd, host = _serve(403)

    # When  the probe runs
    rc, _, out = _run(["push-check"], env_extra={
        "GITHUB_TOKEN": "stub-token",
        "IMAGE_REGISTRY_HOST": host,
        "IMAGE_REGISTRY_SCHEME": "http",
    })
    httpd.shutdown()

    # Then  it fails and repeats the registry's own words
    check("push-check(refused): non-zero", rc != 0, out)
    check("push-check(refused): the registry's message is shown verbatim",
          "permission_denied: create_package" in out, out)
    check("push-check(refused): it says the build was NOT started",
          "build was NOT started" in out, out)


# ----------------------------------------------------- the workflow's shape ---

def _wf() -> str:
    """The workflow's text, or "" when the file is missing.

    Empty rather than raising: one missing file must fail the CHECKS that depend on
    it (each naming what it wanted), not abort the whole file with a traceback that
    hides every other result — a suite that stops at the first absent artifact
    reports less than a suite that reports each absence.
    """
    return WF.read_text() if WF.is_file() else ""


def test_the_pipeline_is_dispatch_only():
    """No schedule, no PR, no push, no workflow_run may publish the toolchain."""

    # Given the workflow
    text = _wf()

    # When  its triggers are read
    # Then  only workflow_dispatch is there
    check("wf: `workflow_dispatch` is present", "workflow_dispatch:" in text, "")
    for forbidden in ("schedule:", "pull_request:", "push:", "workflow_run:"):
        check(f"wf: no `{forbidden}` trigger", forbidden not in text, forbidden)


def test_the_guard_runs_first_and_before_any_secret():
    """A stranger must die at step one, not after the build."""

    # Given the workflow
    text = _wf()

    # When  the job order and the guard are read
    jobs = re.findall(r"^  ([a-z][a-z0-9-]*):$", text, re.M)
    guard_at = text.find("  guard:")
    publish_at = text.find("  publish:")

    # Then  guard is the FIRST job, publish needs it, and the guard reads both actors
    check("wf: `guard` is the first job", jobs and jobs[0] == "guard", jobs)
    check("wf: `publish` runs after the guard", 0 <= guard_at < publish_at,
          f"{guard_at} {publish_at}")
    check("wf: publish needs the guard", "needs: guard" in text, "")
    check("wf: the guard checks the actor", "ACTOR: ${{ github.actor }}" in text, "")
    check("wf: the guard checks the TRIGGERING actor too",
          "TRIGGER: ${{ github.triggering_actor }}" in text, "")
    check("wf: only admin|maintain|write passes",
          "admin|maintain|write" in text, "")
    check("wf: the guard refuses everyone else",
          "exit 1" in text.split("publish:", 1)[0], "")


def test_publishing_uses_the_default_token_not_a_pat():
    """Measured upstream: a PAT that is not an org member cannot create the package."""

    # Given the workflow
    text = _wf()

    # When  its credential use is read
    # Then  the login is the default token as the triggering actor, and no PAT appears
    check("wf: GHCR login uses the default token",
          'echo "${{ github.token }}" | docker login ghcr.io -u "${{ github.actor }}"' in text,
          "")
    check("wf: no PAT secret is referenced",
          "secrets." not in text, "")
    check("wf: it asks for packages: write", "packages: write" in text, "")
    check("wf: it asks only for contents: read", "contents: read" in text, "")


def test_the_push_check_runs_before_the_build():
    """The whole point: fail in seconds, not after ten minutes of building."""

    # Given the workflow's publish job (empty when there is no publish job at all,
    # so each check below fails on its own instead of raising)
    text = _wf()
    parts = text.split("publish:", 1)
    publish_job = parts[1] if len(parts) > 1 else ""

    # When  its steps are read in order
    check_at = publish_job.find("make agent-image-push-check")
    build_at = publish_job.find("make publish-agent-image")

    # Then  the probe comes first and the build is after it
    check("wf: `make agent-image-push-check` is present", check_at != -1, "")
    check("wf: `make publish-agent-image` is present", build_at != -1, "")
    check("wf: the push check runs BEFORE the build", 0 <= check_at < build_at,
          f"{check_at} {build_at}")
    check("wf: force is opt-in only",
          'FORCE_INPUT' in publish_job and 'FORCE=1' in publish_job, "")
    check("wf: it prints the refs it published",
          publish_job.count("make agent-image-ref") >= 1, "")


def test_the_pipeline_never_merges_and_never_pushes_a_branch():
    """It publishes an image; it does not land changes."""

    # Given the workflow
    text = _wf()

    # When  it is read for git writes
    # Then  there are none beyond the checkout
    check("wf: no `gh pr merge`", "pr merge" not in text, "")
    check("wf: no push of a branch", not re.search(r"git push", text), "")
    check("wf: no checkout of a PR head", "ref: $" not in text, "")


def test_everything_is_wired_where_ci_and_the_suite_look():
    """Rule 6d: the targets exist, this file runs, and the pipeline is fetchable."""

    # Given the Makefile and the workflow
    make = MAKEFILE.read_text()

    # When  the wiring is read
    # Then  the three targets exist, this test runs in the suite, and the workflow
    #       is a real file the repo tracks
    for target in ("agent-image-ref:", "agent-image-push-check:", "publish-agent-image:"):
        check(f"wiring: `{target.rstrip(':')}` exists", re.search(rf"^{target}", make, re.M) is not None, "")
    check("wiring: this test runs in `make test`",
          "python3 tests/test_publish_agent_image.py" in make, "")
    check("wiring: push-check and publish go through the one script",
          "ensure_image.py push-check" in make and "ensure_image.py publish" in make, "")
    check("wiring: the workflow file exists", WF.is_file(), "")


def main() -> int:
    print("publishing the agent image: dispatch-only, guarded, proven before the build")
    test_ref_prints_the_hash_tag_and_the_consumer_tag()
    test_publish_is_a_noop_when_this_revision_is_already_published()
    test_publish_builds_and_pushes_both_refs_when_absent()
    test_force_rebuilds_the_same_inputs_on_demand()
    test_push_check_proves_the_credential_before_the_build()
    test_the_pipeline_is_dispatch_only()
    test_the_guard_runs_first_and_before_any_secret()
    test_publishing_uses_the_default_token_not_a_pat()
    test_the_push_check_runs_before_the_build()
    test_the_pipeline_never_merges_and_never_pushes_a_branch()
    test_everything_is_wired_where_ci_and_the_suite_look()
    print(f"\nPASSED {_PASS} | FAILED {_FAIL}")
    return 1 if _FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
