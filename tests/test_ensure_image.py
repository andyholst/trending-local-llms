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


def test_force_reaches_the_script_as_a_value_not_a_bare_flag():
    """Issue #227: `$(if $(FORCE),--force,)` kept only the fact that FORCE was
    non-empty, so `FORCE=0` reached `publish(force="--force" in argv)` as ON and
    a valueless flag crashed `decide` with IndexError."""
    tag = _base_tag()

    # Given every ref published and an OFF value in each spelling the make
    # variable can carry (`--force=<v>` is what the Makefile passes now)
    for off in ("0", "false", "no", "off"):
        rc, calls, out = _run(["publish", f"--force={off}"], available=[tag])

        # Then  nothing is rebuilt and the script says why
        check(f"publish: FORCE={off!r} does NOT rebuild", rc == 0
              and not any(c[:1] == ["build"] for c in calls), str(calls))
        check(f"publish: FORCE={off!r} reports nothing to do",
              "already published" in out, out)

    # Given the value as a separate argument (the `decide` shape)
    rc, calls, out = _run(["publish", "--force", "0"], available=[tag])
    check("publish: `--force 0` does NOT rebuild",
          not any(c[:1] == ["build"] for c in calls), str(calls))

    # Given a BARE --force (what `FORCE=1` used to become, and what a human types)
    for args in (["publish", "--force"], ["publish", "--force=1"], ["publish", "--force", "true"]):
        rc, calls, out = _run(args, available=[tag])
        check(f"publish: {' '.join(args[1:])} is ON",
              any(c[:1] == ["build"] for c in calls), str(calls))

    # Given `decide` with a bare --force — it used to die with IndexError
    rc, _, out = _run(["decide", "--force", "--dow", "1"], available=[])
    check("decide: a bare --force is ON and never an IndexError",
          rc == 0 and "built=yes" in out, out)

    # Given the Makefile target itself: the value is forwarded, not dropped
    mk = (ROOT / "Makefile").read_text()
    check("make: publish-agent-image forwards FORCE's VALUE",
          "--force=$(FORCE)" in mk, "")


def test_wired_into_make_test():
    """The suite runs under `make test` (rule 6d)."""
    mk = (ROOT / "Makefile").read_text()
    check("make: the ensure_image tests run in the suite",
          "python3 tests/test_ensure_image.py" in mk, "")
    check("make: `image-ensure` calls the script the tests exercise",
          "image-ensure:\n\tpython3 scripts/ensure_image.py ensure" in mk, "")



# ------------------------------------------------- the rebuild decision (#208) --

def _base_tag():
    rc, _, out = _run(["tags"])
    return dict(l.split("=", 1) for l in out.splitlines() if "=" in l)["BASE_TAG"]


def _test_tag():
    rc, _, out = _run(["tags"])
    return dict(l.split("=", 1) for l in out.splitlines() if "=" in l)["TEST_TAG"]


def _openspec_tag():
    rc, _, out = _run(["tags"])
    return dict(l.split("=", 1) for l in out.splitlines() if "=" in l)["OPENSPEC_TAG"]


def _decide(available, dow="1", force="false"):
    rc, _, out = _run(["decide", "--dow", str(dow), "--force", str(force)], available=available)
    return rc, dict(l.split("=", 1) for l in out.splitlines() if "=" in l), out


def test_the_rebuild_decision_is_data_not_workflow_shell():
    """Issue #208: every branch of "when do we rebuild" must be testable."""

    # Given every ref this revision publishes is on the registry, and it is not Sunday
    all_refs = [_base_tag(), _test_tag(), _openspec_tag(),
                f"{IMAGE_REPO}:latest"]

    # When  the decision runs
    rc, out, raw = _decide(all_refs, dow="1")

    # Then  nothing is rebuilt and each reason says why
    check("decide: exit 0", rc == 0, raw)
    check("decide: current -> built=no", out.get("built") == "no", raw)
    check("decide: current -> test_built=no", out.get("test_built") == "no", raw)
    check("decide: current -> publish_openspec=no", out.get("publish_openspec") == "no", raw)
    check("decide: current -> reason=current", out.get("reason") == "current", raw)
    check("decide: it reports the tags the workflow builds with",
          out.get("base_tag") == all_refs[0] and out.get("test_tag") == all_refs[1]
          and out.get("openspec_tag") == all_refs[2], raw)

    # Given this revision's tags are NOT published (a merged Dockerfile change)
    rc, out, raw = _decide([], dow="1")

    # Then  both images rebuild and the openspec image publishes, each naming the reason
    check("decide: missing tags -> built=yes", out.get("built") == "yes", raw)
    check("decide: missing tags -> the base reason names the tag",
          "base-tag-missing" in out.get("reason", ""), raw)
    check("decide: missing tags -> test_built=yes", out.get("test_built") == "yes", raw)
    check("decide: missing tags -> the test reason names the tag",
          "test-tag-missing" in out.get("test_reason", ""), raw)
    check("decide: missing tags -> the openspec image publishes",
          out.get("publish_openspec") == "yes"
          and "openspec-tag-missing" in out.get("openspec_reason", ""), raw)

    # Given only the consumer `:latest` ref is missing (#135's failure mode)
    rc, out, raw = _decide([_base_tag(), _test_tag(), _openspec_tag()], dow="1")

    # Then  the base rebuilds (a job would pull a stale `:latest`) and the test image does not
    check("decide: latest missing -> built=yes", out.get("built") == "yes", raw)
    check("decide: latest missing -> the reason names it",
          "latest-missing" in out.get("reason", ""), raw)
    check("decide: latest missing -> test_built=no", out.get("test_built") == "no", raw)

    # Given Sunday, with everything published (the weekly Hermes refresh)
    rc, out, raw = _decide(all_refs, dow="7")

    # Then  both images rebuild, reason=sunday, and the openspec image is untouched
    check("decide: Sunday -> built=yes", out.get("built") == "yes", raw)
    check("decide: Sunday -> the reason is sunday", out.get("reason") == "sunday", raw)
    check("decide: Sunday -> test_built=yes", out.get("test_built") == "yes", raw)
    check("decide: Sunday -> the openspec image is NOT rebuilt",
          out.get("publish_openspec") == "no", raw)

    # Given a forced rebuild with everything published
    rc, out, raw = _decide(all_refs, dow="1", force="true")

    # Then  the two code images rebuild, and the openspec image still does not
    check("decide: forced -> built=yes", out.get("built") == "yes", raw)
    check("decide: forced -> the reason is forced", "forced" in out.get("reason", ""), raw)
    check("decide: forced -> publish_openspec=no (unchanged behaviour)",
          out.get("publish_openspec") == "no", raw)


def test_force_is_parsed_strictly_so_zero_means_off():
    """Issue #227's class: an "off" value must not take the destructive branch."""

    # Given every ref is published and it is not Sunday
    all_refs = [_base_tag(), _test_tag(), _openspec_tag(), f"{IMAGE_REPO}:latest"]

    # When  FORCE is the string a caller writes to mean "off"
    for off in ("0", "false", "no", "", "off"):
        rc, out, raw = _decide(all_refs, dow="1", force=off)

        # Then  nothing is rebuilt
        check(f"decide: FORCE={off!r} means OFF", out.get("built") == "no", raw)

    # When  FORCE is an on value
    for on in ("1", "true", "yes"):
        rc, out, raw = _decide(all_refs, dow="1", force=on)

        # Then  the base rebuilds
        check(f"decide: FORCE={on!r} means ON", out.get("built") == "yes", raw)

    # When  FORCE is something that is neither
    rc, out, raw = _decide(all_refs, dow="1", force="maybe")

    # Then  it fails loudly instead of guessing
    check("decide: an unreadable FORCE fails", rc != 0, raw)
    check("decide: it says what it could not read",
          "cannot read" in raw and "boolean" in raw, raw)


def main() -> int:
    print("runner-image decision (scripts/ensure_image.py)")
    test_tags_are_the_hash_of_this_revisions_inputs()
    test_the_rebuild_decision_is_data_not_workflow_shell()
    test_force_is_parsed_strictly_so_zero_means_off()
    test_force_reaches_the_script_as_a_value_not_a_bare_flag()
    test_openspec_image_is_hash_tagged_and_pulled_or_built()
    test_ensure_base_builds_only_when_the_tag_is_not_published()
    test_ensure_test_pulls_or_builds_on_that_base()
    test_wired_into_make_test()
    print(f"\nPASSED {_PASS} | FAILED {_FAIL}")
    return 1 if _FAIL else 0


if __name__ == "__main__":
    raise SystemExit(main())
