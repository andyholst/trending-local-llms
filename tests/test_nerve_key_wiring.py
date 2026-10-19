#!/usr/bin/env python3
"""Nerve-plugin credential wiring guards (issue #120).

The issue asked for the nerve plugin's key to reach Hermes ONLY as a `-e` env var
— never baked into the image, never written into a file, never committed — while
explicitly leaving the *name* "to be confirmed against the plugin's expected env
var". Confirmed at the catalog-pinned revision: the plugin resolves
`TYPESAFE_API_KEY` (the provider PRODUCTION runs), `OPENROUTER_API_KEY` and
`OPENCODE_API_KEY` (the plugin's other providers)
from `hermes_nerve/client.py::PROVIDER_API_KEY_ENV`. There is no `JEV_KEY`
upstream, so wiring that name would register a variable nothing reads and the
plugin would keep reporting its key missing — silently, which is the failure the
issue exists to prevent.

  - test_detector_catches_every_forbidden_shape  the guard is not a no-op
  - test_pre_change_tree_fails_the_guards        it fails on the OLD files
  - test_real_tree_is_clean                      it passes on the current tree
  - test_credential_name_is_verified             the NAME is measured, not chosen
  - test_provider_names_match_the_pinned_plugin  provenance: plugin source == guard
  - test_wired_to_make_and_ci                    rule 6d: a make target CI runs

Wired into `_test` (so `make test`, which CI runs, executes it) and the check it
drives into qa-validate's `validate` job via `make nerve-check`.

Run:  python3 tests/test_nerve_key_wiring.py    or   make test
"""
from __future__ import annotations

import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import nerve_key_check as NK  # noqa: E402

from wiring import wired  # noqa: E402  (issues #176/#192)

_PASS = 0
_FAIL = 0

# A well-formed but FAKE credential, assembled from parts so this guard file
# never trips the secret scan it complements (same trick as the planted-key
# self-test in scripts/secret_scan_self_test.py).
_FAKE = "sk" + "-" + "Ab1".ljust(26, "x")


def check(name, cond, detail: object = "") -> None:
    global _PASS, _FAIL
    if cond:
        _PASS += 1
        print(f"  ok  {name}")
    else:
        _FAIL += 1
        print(f"  FAIL {name}" + (f"  [{detail}]" if detail else ""))


def wf(**exported) -> str:
    """A minimal workflow whose job env is `exported` (name -> secret name)."""
    lines = ["name: x", "jobs:", "  j:", "    runs-on: ubuntu-latest", "    env:"]
    lines += [f"      {k}: ${{{{ secrets.{v} }}}}" for k, v in exported.items()]
    lines += ["    steps:", "      - run: make validate"]
    return "\n".join(lines) + "\n"


ALL_WF = {n: wf(TYPESAFE_API_KEY="TYPESAFE_API_KEY") for n in NK.CONTAINER_WORKFLOWS}


def test_detector_catches_every_forbidden_shape():
    """Every shape the issue forbids must be a finding, or the guard is theatre."""

    # Given the forbidden Dockerfile shapes
    # Then  each is reported
    check("docker: `ENV <KEY>=<value>` is a finding",
          NK.check_dockerfile(f"ENV TYPESAFE_API_KEY={_FAKE}\n") != [])
    check("docker: `ENV JEV_KEY=<value>` is a finding",
          NK.check_dockerfile("ENV JEV_KEY=whatever\n") != [])
    check("docker: a COPYed config.yaml is a finding",
          NK.check_dockerfile("COPY config.yaml /root/.hermes/config.yaml\n") != [])
    check("docker: an unpinned plugin install is a finding",
          NK.check_dockerfile(f"RUN hermes plugins install {NK.PLUGIN_SOURCE}\n") != [])
    ok_docker = (f"ARG NERVE_PLUGIN_REF={NK.PLUGIN_REF}\n"
                 f'RUN hermes plugins install {NK.PLUGIN_SOURCE} --ref "$NERVE_PLUGIN_REF"\n')
    check("docker: the real shape passes", NK.check_dockerfile(ok_docker) == [],
          NK.check_dockerfile(ok_docker))

    # Given the forbidden Makefile shapes
    old_run = ("DOCKER_RUN := docker run --rm -v \"$$PWD\":/workspace -w /workspace \\\n"
               "\t-e NOUS_API_KEY -e FIRECRAWL_API_KEY -e HF_TOKEN $(IMAGE)\n"
               "TEST_RUN := docker run --rm $(TEST_IMAGE)\n"
               "NERVE_KEY_ENV  := JEV_KEY\n")
    check("make: a JEV_KEY name is a finding",
          any("resolves" in f for f in NK.check_makefile(old_run)), NK.check_makefile(old_run))
    check("make: `-e JEV_KEY` is a finding",
          any("never reads" in f for f in NK.check_makefile(
              _MAKE_WIRING + "NERVE_KEY_ENV  := OPENROUTER_API_KEY\n"
              "\t-e JEV_KEY $(IMAGE)\n")))
    check("make: a wrapper that forwards nothing is a finding",
          NK.check_makefile(
              "DOCKER_RUN := docker run --rm $(IMAGE)\nTEST_RUN := docker run --rm $(TEST_IMAGE)\n"
              "NERVE_KEY_ENV  := OPENROUTER_API_KEY\n") != [])

    # Given the real mistake this guard was written after: a SELF-CONSISTENT
    # provider/key pair that is the plugin's own default, not production's
    wrong_provider = (
        "NERVE_PROVIDER := openrouter\n"
        "NERVE_KEY_ENV  := OPENROUTER_API_KEY\n"
        "DOCKER_RUN := docker run --rm -e $(NERVE_KEY_ENV) $(IMAGE)\n"
        "TEST_RUN := docker run --rm -e $(NERVE_KEY_ENV) $(TEST_IMAGE)\n"
    )

    # When  the guard checks it
    findings = NK.check_makefile(wrong_provider)

    # Then  the wrong provider is a finding even though the pair is consistent
    check("make: a consistent pair on the wrong provider is a finding",
          any("is not the provider the setup runs" in f for f in findings), findings)
    check("make: the guard's provider is the one production runs",
          NK.DEFAULT_PROVIDER == "typesafe", NK.DEFAULT_PROVIDER)
    check("make: that provider's key name is the one production sets",
          NK.PROVIDER_KEY_ENV[NK.DEFAULT_PROVIDER] == "TYPESAFE_API_KEY",
          NK.PROVIDER_KEY_ENV[NK.DEFAULT_PROVIDER])
    check("make: a literal key in `config set` is a finding",
          any("literal credential" in f for f in NK.check_makefile(
              _MAKE_WIRING + "_setup:\n\thermes config set plugins.entries.nerve.settings.reflex_laya_token "
              f"{_FAKE}\n")))
    check("make: `config set …key_env NOUS_API_KEY` (a NAME) is NOT a finding",
          not any("literal credential" in f for f in NK.check_makefile(
              _MAKE_WIRING + "_setup:\n\thermes config set model.aliases.nous-deepseek.key_env NOUS_API_KEY\n")))
    check("make: `config set …max_tokens 65536` (not a credential path) is NOT a finding",
          not any("literal credential" in f for f in NK.check_makefile(
              _MAKE_WIRING + "_setup:\n\thermes config set model.aliases.nous-deepseek.max_tokens 65536\n")))

    # Given the forbidden workflow shapes
    check("workflow: a missing `env:` export is a finding",
          NK.check_workflows({n: wf(NOUS_API_KEY="NOUS_PORTAL_API_TOKEN") for n in NK.CONTAINER_WORKFLOWS}) != [])
    check("workflow: the secret exported under a DIFFERENT name is a finding",
          NK.check_workflows({n: wf(OTHER_KEY="OPENROUTER_API_KEY") for n in NK.CONTAINER_WORKFLOWS}) != [])
    check("workflow: echoing the credential is a finding",
          NK.check_workflows({**ALL_WF, "fix-bot.yml":
                              ALL_WF["fix-bot.yml"] + "      - run: echo $OPENROUTER_API_KEY\n"}) != [])
    check("workflow: the real shape passes", NK.check_workflows(ALL_WF) == [], NK.check_workflows(ALL_WF))

    # Given a credential literal anywhere in a tracked file
    check("scan: a key literal is a finding", NK.forbidden_shapes(f'KEY={_FAKE}', "x") != [])
    check("scan: an elided placeholder is NOT a finding",
          NK.forbidden_shapes("OPENROUTER_API_KEY=<value>", "AGENTS.md") == []
          and NK.forbidden_shapes("Authorization: Bearer ***", "Makefile") == [])


_MAKE_WIRING = (
    "NERVE_PROVIDER := typesafe\n"
    "NERVE_KEY_ENV  := TYPESAFE_API_KEY\n"
    "DOCKER_RUN := docker run --rm -e $(NERVE_KEY_ENV) $(IMAGE)\n"
    "TEST_RUN := docker run --rm -e $(NERVE_KEY_ENV) $(TEST_IMAGE)\n"
)


def test_scan_walks_the_tree_by_directory():
    """The shape scan is repo-wide and directory-driven, not a hand-kept file
    list: a credential planted in a NEW file of a scanned directory is found."""
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        (root / "scripts").mkdir()
        (root / "scripts" / "brand_new_thing.py").write_text(f'KEY = "{_FAKE}"\n')
        (root / "data").mkdir()
        (root / "data" / "captured.json").write_text(f'{{"text": "{_FAKE}"}}')
        saved, NK.ROOT = NK.ROOT, root
        try:
            hits = NK.scan_tree()
        finally:
            NK.ROOT = saved
    check("scan: a new file in a scanned directory is covered",
          any("brand_new_thing.py" in h for h in hits), hits)
    check("scan: captured data/ is excluded (scraped post text, never authored)",
          not any("captured.json" in h for h in hits), hits)


def test_pre_change_tree_fails_the_guards():
    """The guard must FAIL on the files as they were BEFORE issue #120 — a guard
    that only ever passes proves nothing (AGENTS.md rule 6c)."""
    old_dockerfile = "\n".join([
        "FROM python:3.12-slim",
        "ADD https://hermes-agent.nousresearch.com/install.sh /tmp/hermes-install.sh",
        "RUN bash /tmp/hermes-install.sh",
        "COPY . .",
    ])
    old_makefile = "\n".join([
        "IMAGE := trending-local-llms:latest",
        'DOCKER_RUN := docker run --rm -v "$$PWD":/workspace -w /workspace \\',
        "\t-e NOUS_API_KEY -e FIRECRAWL_API_KEY -e HF_TOKEN $(IMAGE)",
        "TEST_RUN := docker run --rm -e HF_TOKEN $(TEST_IMAGE)",
    ])
    old_workflows = {n: wf(NOUS_API_KEY="NOUS_PORTAL_API_TOKEN") for n in NK.CONTAINER_WORKFLOWS}
    check("pre-change Dockerfile: the guard fails", NK.check_dockerfile(old_dockerfile) != [])
    check("pre-change Makefile: the guard fails", NK.check_makefile(old_makefile) != [])
    check("pre-change workflows: the guard fails", NK.check_workflows(old_workflows) != [])


def test_real_tree_is_clean():
    """On the real tree the check reports nothing — and says so out loud."""
    findings, notes = NK.run_all()
    check("real tree: no finding", findings == [], findings)
    # The plugin is installed by the Dockerfile, so the image this runs in must
    # have it: a proof that could not run is a FAILURE, never a note in a PASSED
    # line (issue #135 — the image follows the Dockerfile or it is stale).
    check("real tree: the plugin proof RAN (never skipped)",
          any("loud without the key" in n for n in notes), notes)
    check("real tree: the script exits 0", NK.main(["--quiet"]) == 0)


def test_credential_name_is_verified():
    """The NAME is the one the plugin resolves, and explicitly NOT the
    unverifiable `JEV_KEY` the issue proposed."""
    mk = (ROOT / "Makefile").read_text()
    m = re.search(r"(?m)^NERVE_KEY_ENV\s*:?=\s*(\S+)\s*$", mk)
    check("make: NERVE_KEY_ENV is defined", m is not None)
    name = m.group(1) if m else ""
    check("make: the name is one the pinned plugin resolves", name in NK.PROVIDER_KEY_ENV.values(), name)
    check("make: the unverified JEV_KEY is NOT wired", name != "JEV_KEY")
    prov = re.search(r"(?m)^NERVE_PROVIDER\s*:?=\s*(\S+)\s*$", mk)
    check("make: NERVE_KEY_ENV matches the selected provider",
          prov is not None and NK.PROVIDER_KEY_ENV[prov.group(1)] == name,
          f"{prov.group(1) if prov else '?'} -> {name}")
    check("make: DOCKER_RUN and TEST_RUN both forward it by name",
          mk.count("-e $(NERVE_KEY_ENV)") >= 2, mk.count("-e $(NERVE_KEY_ENV)"))
    check("make: the config carries the provider, never the key",
          "hermes config set plugins.entries.nerve.settings.jev_provider $(NERVE_PROVIDER)" in mk
          and "plugins.entries.nerve.settings.key_env" not in mk)


def test_provider_names_match_the_pinned_plugin():
    """PROVENANCE. When the plugin is installed (the image, and any dev run that
    has it) its own client is the authority: the guard's name map must equal
    `PROVIDER_API_KEY_ENV` at the pinned revision, so the wiring cannot drift
    from what the plugin actually reads."""
    d = NK.plugin_dir()
    # Given the environment the guard runs in — the plugin ships in this image,
    # so an instance without it means the image predates the Dockerfile that
    # pins it: that is a failure, not a skip (issue #135).
    check("provenance: the pinned plugin is installed in this environment", d is not None,
          "run `make docker-build`/`make docker-test-build` — the base image is stale")
    if d is None:
        return
    src = ""
    for pkg in ("hermes_nerve", "hermes_jev"):
        f = d / pkg / "client.py"
        if f.exists():
            src = f.read_text()
            break
    check("provenance: the plugin client was found", bool(src), str(d))
    if not src:
        return
    found = dict(re.findall(r'"(\w+)":"([A-Z_]+)"', src))
    want = {k: v for k, v in found.items() if v.endswith("_API_KEY")}
    check("provenance: the guard's names == the plugin's PROVIDER_API_KEY_ENV",
          want == NK.PROVIDER_KEY_ENV, f"plugin={want} guard={NK.PROVIDER_KEY_ENV}")


def test_wired_to_make_and_ci():
    """Rule 6d: the check runs from a make target CI actually executes."""
    mk = (ROOT / "Makefile").read_text()
    check("make: `_nerve-check` exists", "\n_nerve-check:" in mk)
    check("make: `nerve-check` public wrapper exists", "\nnerve-check:" in mk)
    check("make: the public target runs the internal one in the container",
          "$(TEST_RUN) make _nerve-check" in mk)
    check("make: the check script is reachable", "scripts/nerve_key_check.py" in mk)
    check("make: this guard runs in `make test`",
          wired(__file__))
    qa = (ROOT / ".github" / "workflows" / "qa-validate.yml").read_text()
    check("ci: qa-validate runs `make nerve-check`", "run: make nerve-check" in qa)
    check("ci: it runs after the images are prepared",
          qa.index("make nerve-check") > qa.index("make image-ensure"))
    wf_text = (ROOT / ".github" / "workflows" / "refresh-bot.yml").read_text()
    check("ci: the refresh pipeline exports the secret for the `-e` to resolve",
          "TYPESAFE_API_KEY: ${{ secrets.TYPESAFE_API_KEY }}" in wf_text)


def main() -> int:
    print("nerve-plugin credential wiring (issue #120)")
    test_detector_catches_every_forbidden_shape()
    test_scan_walks_the_tree_by_directory()
    test_pre_change_tree_fails_the_guards()
    test_real_tree_is_clean()
    test_credential_name_is_verified()
    test_provider_names_match_the_pinned_plugin()
    test_wired_to_make_and_ci()
    print(f"\nPASSED {_PASS} | FAILED {_FAIL}")
    return 1 if _FAIL else 0


if __name__ == "__main__":
    raise SystemExit(main())
