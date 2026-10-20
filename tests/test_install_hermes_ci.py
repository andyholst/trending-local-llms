#!/usr/bin/env python3
"""scripts/install_hermes_ci.sh — the ONE seam that installs the Hermes CLI.

The seam is the behaviour under test; the EXTERNAL systems it talks to are
stubbed (a `curl`, a `uv` and a `hermes` on PATH, the same allowance the repo
already uses for `docker`, `gh` and `hermes`). The script itself runs for real,
with a real PATH and a real temp HOME — no logic is mocked.

  - `hermes` already on PATH      -> use it, download nothing
  - no hermes, HERMES_INSTALL_URL -> fetch that installer and run it
  - the download fails            -> loud failure, no second attempt
  - the URL installer no-ops      -> falls through to `uv tool install`
  - nothing works                 -> non-zero, naming all three paths tried

and the shape the IMAGE depends on (issue #207):

  - the Dockerfile uses the seam (no `ADD https://…/install.sh`), carries the
    install pin as build args, and runs `make _setup` + `make _hermes-alias-check`
  - the Dockerfile's ARG defaults are the Makefile's defaults (one pin, two files
    that a guard keeps in step)
  - `_setup` writes the alias from `$(HERMES_ALIAS)` and `_hermes-alias-check`
    reads the same variable back (so the writer and the reader cannot drift)
  - `_hermes-alias-check` fails on a wrong model/provider/key_env and reports
    every mismatch; it passes on the pinned alias
  - no credential is baked: no key VALUE anywhere in the Dockerfile, and the seam
    never reads one

Run:  python3 tests/test_install_hermes_ci.py   or   make test
"""
from __future__ import annotations

import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

from wiring import wired  # noqa: E402  (issues #176/#192)

ROOT = Path(__file__).resolve().parent.parent
SEAM = ROOT / "scripts" / "install_hermes_ci.sh"
DOCKERFILE = ROOT / "Dockerfile"
MAKEFILE = ROOT / "Makefile"

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


def _stub(directory: Path, name: str, body: str) -> Path:
    p = directory / name
    p.write_text("#!/usr/bin/env bash\n" + body)
    p.chmod(0o755)
    return p


def run_seam(*, hermes: str | None = None, curl_stub: str | None = None,
             uv_stub: str | None = None, install_url: str | None = None,
             package: str | None = None):
    """Run the seam for real in a temp HOME with only the stubs on PATH."""
    td = Path(tempfile.mkdtemp())
    bindir = td / "bin"
    bindir.mkdir()
    calls = td / "calls.log"

    if hermes is not None:
        _stub(bindir, "hermes", f"echo '{hermes}'\n")
    if curl_stub is not None:
        _stub(bindir, "curl", curl_stub.replace("@CALLS@", str(calls)))
    if uv_stub is not None:
        _stub(bindir, "uv", uv_stub.replace("@CALLS@", str(calls)))

    env = {
        "PATH": f"{bindir}:/usr/bin:/bin",
        "HOME": str(td),                 # empty: no ~/.local/bin/hermes
        "HERMES_INSTALL_URL": install_url or "",
        "HERMES_PACKAGE": package or "hermes-agent",
    }
    proc = subprocess.run(["bash", str(SEAM)], capture_output=True, text=True,
                          env=env, timeout=60)
    return proc, (calls.read_text() if calls.exists() else ""), td


# ------------------------------------------------------------------ the seam --

def test_a_present_cli_is_used_and_nothing_is_downloaded():
    """Branch 1: a `hermes` on PATH is used as-is."""

    # Given a PATH that already has a hermes
    # When  the seam runs
    proc, calls, _ = run_seam(
        hermes="hermes 9.9-stub",
        curl_stub="echo 'curl was called' >> @CALLS@\nexit 0",
        uv_stub="echo 'uv was called' >> @CALLS@\nexit 0",
        install_url="https://example.invalid/install.sh",
    )

    # Then  it succeeds, reports the version, and downloads nothing
    check("seam: a present hermes exits 0", proc.returncode == 0, proc.stderr[-200:])
    check("seam: it says the CLI is already installed",
          "already installed" in proc.stdout, proc.stdout)
    check("seam: it prints the version", "hermes 9.9-stub" in proc.stdout, proc.stdout)
    check("seam: no download, no package manager", calls == "", calls)


def test_the_configured_installer_is_fetched_and_run():
    """Branch 2: HERMES_INSTALL_URL is fetched and executed."""

    # Given no hermes, a curl that yields an installer which drops one in ~/.local/bin
    installer = ("mkdir -p \"$HOME/.local/bin\" && "
                 "printf '#!/usr/bin/env bash\\necho \"hermes 1.0-from-url\"\\n' "
                 "> \"$HOME/.local/bin/hermes\" && chmod +x \"$HOME/.local/bin/hermes\"")

    # When  the seam runs
    proc, calls, _ = run_seam(
        curl_stub=f"echo \"curl $*\" >> @CALLS@\ncat > \"$4\" <<'EOS'\n{installer}\nEOS\nexit 0",
        install_url="https://mirror.invalid/hermes/install.sh",
    )

    # Then  the configured URL was used and the installed CLI is reported
    check("seam: the configured URL is fetched",
          "https://mirror.invalid/hermes/install.sh" in calls, calls)
    check("seam: it exits 0 after a successful install", proc.returncode == 0,
          proc.stderr[-300:])
    check("seam: the installed CLI is reported",
          "hermes 1.0-from-url" in proc.stdout, proc.stdout)


def test_a_failed_download_is_a_loud_failure_without_a_second_attempt():
    """Branch 2, download fails: no silent fallback into another installer."""

    # Given a curl that fails (a moved URL is the reason the seam exists)
    # When  the seam runs
    proc, calls, _ = run_seam(
        curl_stub="echo \"curl $*\" >> @CALLS@\nexit 22",
        uv_stub="echo 'uv was called' >> @CALLS@\nexit 0",
        install_url="https://gone.invalid/install.sh",
    )

    # Then  it fails, names the URL, and never reaches the package manager
    check("seam: an undownloadable installer exits non-zero", proc.returncode != 0, proc.stdout)
    check("seam: it names the URL it could not fetch",
          "gone.invalid" in proc.stdout, proc.stdout)
    check("seam: it does not silently fall through to uv", "uv was called" not in calls, calls)


def test_an_installer_that_produces_nothing_falls_through_to_uv():
    """Branch 2 -> 3: a URL installer that yields no CLI is not the end."""

    # Given a curl that hands over an installer which installs nothing, and a uv that does
    # When  the seam runs
    proc, calls, _ = run_seam(
        curl_stub="echo \"curl $*\" >> @CALLS@\nprintf 'true\\n' > \"$4\"\nexit 0",
        uv_stub=("echo \"uv $*\" >> @CALLS@\n"
                 "mkdir -p \"$HOME/.local/bin\" && "
                 "printf '#!/usr/bin/env bash\\necho \"hermes 2.0-from-uv\"\\n' "
                 "> \"$HOME/.local/bin/hermes\" && chmod +x \"$HOME/.local/bin/hermes\"\n"
                 "exit 0"),
        install_url="https://mirror.invalid/hermes/install.sh",
    )

    # Then  the package-manager path ran and its CLI is reported
    check("seam: it says the installer produced no hermes",
          "put no 'hermes' on PATH" in proc.stdout, proc.stdout)
    check("seam: uv tool install ran with the configured package",
          "tool install hermes-agent" in calls, calls)
    check("seam: the uv-installed CLI is reported",
          "hermes 2.0-from-uv" in proc.stdout, proc.stdout)
    check("seam: exit 0", proc.returncode == 0, proc.stderr[-200:])


def test_nothing_works_is_a_loud_failure_naming_every_path():
    """Branch 4: an agent image without an agent must not build."""

    # Given no hermes, no url, no uv
    # When  the seam runs
    proc, _, _ = run_seam()

    # Then  it fails and names all three things it tried
    out = proc.stdout + proc.stderr
    check("seam: nothing available exits non-zero", proc.returncode != 0, out)
    check("seam: it names the PATH attempt", "on PATH" in out, out)
    check("seam: it names the URL attempt", "HERMES_INSTALL_URL" in out, out)
    check("seam: it names the uv attempt", "uv tool install hermes-agent" in out, out)
    check("seam: it says why that must fail the build",
          "without an agent must not build" in out, out)


def test_the_seam_never_handles_a_credential():
    """The seam installs a CLI; the key arrives at run time (rule 3e)."""

    # Given the seam's source
    src = SEAM.read_text()

    # When  it is read for credential handling
    # Then  it only ever mentions the NAME of the env var, never a value read
    check("seam: it never reads a key value",
          not re.search(r"\$\{?(NOUS_API_KEY|TYPESAFE_API_KEY|OPENROUTER_API_KEY)", src), "")
    check("seam: it never writes config", "config set" not in src, "")
    check("seam: it never passes a key to a command",
          not re.search(r"(curl|uv|bash|hermes)\b[^\n]*(API_KEY|TOKEN)", src), "")


# ------------------------------------------------------- the image's shape ----

def test_the_dockerfile_installs_through_the_seam():
    """The image must not go back to a bare `ADD <url>`."""

    # Given the Dockerfile
    text = DOCKERFILE.read_text()

    # When  its install step is read
    # Then  the seam does the install and the pin is a build arg
    check("dockerfile: no `ADD https://…/install.sh` any more",
          "ADD https://hermes-agent.nousresearch.com" not in text, "")
    check("dockerfile: it copies and runs the seam",
          "COPY scripts/install_hermes_ci.sh /usr/local/bin/install_hermes_ci.sh" in text
          and "/usr/local/bin/install_hermes_ci.sh" in text, "")
    check("dockerfile: HERMES_INSTALL_URL is a build arg",
          re.search(r'^ARG HERMES_INSTALL_URL="\S+"$', text, re.M) is not None, "")
    check("dockerfile: HERMES_PACKAGE is a build arg",
          re.search(r'^ARG HERMES_PACKAGE="\S+"$', text, re.M) is not None, "")
    check("dockerfile: the args reach the seam as env",
          "ENV HERMES_INSTALL_URL=${HERMES_INSTALL_URL} HERMES_PACKAGE=${HERMES_PACKAGE}" in text,
          "")


def test_the_dockerfile_asserts_the_alias_at_build_time():
    """A bad pin must fail the BUILD, not a bot run."""

    # Given the Dockerfile
    text = DOCKERFILE.read_text()

    # When  its post-copy steps are read
    # Then  it writes the alias and then checks it
    setup_at = text.find("make _setup")
    check_at = text.find("make _hermes-alias-check")
    check("dockerfile: it runs `make _setup`", setup_at != -1, "")
    check("dockerfile: it runs the alias assertion", check_at != -1, "")
    check("dockerfile: the assertion runs AFTER _setup wrote the alias",
          setup_at != -1 and check_at > setup_at, f"{setup_at} {check_at}")
    check("dockerfile: both run in one RUN with PATH set",
          bool(re.search(r"RUN export PATH=\"/root/\.local/bin:\$PATH\" \\\n\s+&& make _setup \\\n\s+&& make _hermes-alias-check", text)),
          "")


def test_no_credential_value_is_baked_into_the_image():
    """Rule 3e: the image knows the NAME of the key, never its value."""

    # Given the Dockerfile and the seam
    text = DOCKERFILE.read_text()
    seam = SEAM.read_text()

    # When  they are read for a key VALUE
    # Then  only names appear
    check("dockerfile: no `ENV <KEY>=value`",
          not re.search(r"^\s*ENV\s+\w*(API_KEY|TOKEN)\s*=", text, re.M), "")
    check("dockerfile: no ARG carrying a key value",
          not re.search(r"^ARG\s+\w*(API_KEY|TOKEN)\b", text, re.M), "")
    # Every *_API_KEY token in the Dockerfile is a NAME (a comment documenting the
    # mapping, or the alias's key_env) — never an assignment to a value.
    check("dockerfile: the alias's key_env name is declared",
          "key_env=NOUS_API_KEY" in text, "")
    check("dockerfile: no key name is ever assigned a value",
          not re.search(r"\w*_API_KEY\s*=\s*\S", text), "")
    check("dockerfile: the nerve key mapping is described, not applied",
          re.findall(r"TYPESAFE_API_KEY", text) != []
          and "TYPESAFE_API_KEY" not in text.split("# Then the rest of the repo")[0].split("RUN ")[-1],
          "")
    check("seam: it does not touch config.yaml", "config.yaml" not in seam, "")


def test_the_install_pin_has_one_definition_across_the_two_files():
    """The Dockerfile's ARG default and the Makefile's ?= must agree."""

    # Given both files
    docker = DOCKERFILE.read_text()
    make = MAKEFILE.read_text()

    # When  their defaults are compared
    d_url = re.search(r'^ARG HERMES_INSTALL_URL="(\S+)"$', docker, re.M)
    m_url = re.search(r"^HERMES_INSTALL_URL \?= (\S+)$", make, re.M)
    d_pkg = re.search(r'^ARG HERMES_PACKAGE="(\S+)"$', docker, re.M)
    m_pkg = re.search(r"^HERMES_PACKAGE\s+\?= (\S+)$", make, re.M)

    # Then  they are the same pin
    check("pin: the install URL default matches in both files",
          d_url and m_url and d_url.group(1) == m_url.group(1),
          f"{d_url and d_url.group(1)} vs {m_url and m_url.group(1)}")
    check("pin: the package default matches in both files",
          d_pkg and m_pkg and d_pkg.group(1) == m_pkg.group(1),
          f"{d_pkg and d_pkg.group(1)} vs {m_pkg and m_pkg.group(1)}")


def test_the_alias_has_one_name_for_the_writer_and_the_reader():
    """`_setup` writes `$(HERMES_ALIAS)…`; the check reads the same variable."""

    # Given the Makefile
    make = MAKEFILE.read_text()
    setup = make.split("_setup:", 1)[1].split("_hermes-alias-check", 1)[0]
    check_block = make.split("_hermes-alias-check:", 1)[1]

    # When  the writer and the reader are read
    # Then  both go through $(HERMES_ALIAS) and the literal name is defined once
    check("alias: _setup writes the alias from the variable",
          "model.aliases.$(HERMES_ALIAS).model $(HERMES_MODEL)" in setup, "")
    check("alias: _setup writes no hardcoded alias name",
          "model.aliases.nous-deepseek" not in setup, "")
    check("alias: the check reads the same variable",
          'model.aliases.$(HERMES_ALIAS).$$key' in check_block, "")
    check("alias: the name is defined exactly once",
          len(re.findall(r"^HERMES_ALIAS\s*:?=", make, re.M)) == 1, "")
    check("alias: the definition is the alias the hermes calls pass with -m",
          re.search(r"^HERMES_ALIAS :?= nous-deepseek$", make, re.M) is not None, "")


def test_the_alias_check_passes_on_the_pin_and_fails_on_a_different_one():
    """The real recipe, a stubbed hermes: green on the pin, red otherwise."""

    # Given a stub hermes answering the pinned values, and one answering others
    good = ("#!/usr/bin/env bash\ncase \"$3\" in\n"
            "  *.model) echo deepseek/deepseek-v4.1-flash-1017;;\n"
            "  *.provider) echo custom;;\n"
            "  *.base_url) echo \"https://inference-api.nousresearch.com/v1\";;\n"
            "  *.key_env) echo NOUS_API_KEY;;\n"
            "  *.max_tokens) echo 65536;;\n"
            "  *.context_window) echo 1048576;;\nesac\n")
    bad = ("#!/usr/bin/env bash\ncase \"$3\" in\n"
           "  *.provider) echo openrouter;;\n  *) echo wrong;;\nesac\n")

    results = {}
    for label, body in (("good", good), ("bad", bad)):
        td = Path(tempfile.mkdtemp())
        (td / "hermes").write_text(body)
        (td / "hermes").chmod(0o755)
        env = dict(os.environ, PATH=f"{td}:/usr/bin:/bin")
        results[label] = subprocess.run(
            ["make", "_hermes-alias-check"], cwd=ROOT, capture_output=True,
            text=True, env=env, timeout=120)

    # When  the check runs in both worlds
    # Then  it passes on the pin and refuses a different one, naming each mismatch
    check("alias check: exit 0 on the pinned alias", results["good"].returncode == 0,
          results["good"].stdout[-300:])
    check("alias check: it says what it proved",
          "matches the Makefile pin" in results["good"].stdout, results["good"].stdout)
    check("alias check: exit non-zero on a different alias",
          results["bad"].returncode != 0, results["bad"].stdout[-200:])
    check("alias check: it names the wrong provider",
          "provider is 'openrouter', expected 'custom'" in results["bad"].stdout,
          results["bad"].stdout)
    check("alias check: it reports EVERY mismatch, not just the first",
          results["bad"].stdout.count("FAIL:") >= 2, results["bad"].stdout)
    check("alias check: it refuses in words",
          "the image does not carry the alias" in results["bad"].stdout, results["bad"].stdout)


def test_the_seam_and_the_check_are_wired_where_ci_looks():
    """Rule 6d: the gate and the script must be reachable, not decorative."""

    # Given the Makefile and the suite
    make = MAKEFILE.read_text()

    # When  the wiring is read
    # Then  the seam is the only installer, the public check exists, and this file runs
    check("wiring: `_setup` calls the seam",
          "scripts/install_hermes_ci.sh" in make.split("_setup:", 1)[1][:400], "")
    check("wiring: no second curl-pipe-bash installer is left",
          "curl -fsSL https://hermes-agent.nousresearch.com/install.sh | bash" not in make, "")
    check("wiring: the public `hermes-alias-check` target exists",
          re.search(r"^hermes-alias-check:", make, re.M) is not None, "")
    check("wiring: this test file runs in `make test`",
          wired(__file__), "")
    check("wiring: the seam is tracked as executable",
          (SEAM.stat().st_mode & 0o111) != 0, oct(SEAM.stat().st_mode))


def test_no_wrapper_discards_the_seams_diagnosis():
    """Issue #222: `hermes-alias-check` and `hermes-smoke` ran the seam through
    `make _setup >/dev/null`, so the one line that explains a setup failure was
    thrown away and the target failed with nothing said — the same class as a seam
    that fails silently. Every wrapped target keeps it: bare, or `1>&2` so the
    target's own stdout stays what the caller parses."""
    make = (ROOT / "Makefile").read_text()

    # Given every wrapper that runs the seam inside a container
    wrapped = [line.strip() for line in make.splitlines()
               if "make _setup" in line and "sh -c" in line]

    # Then  there are several, none discards the output, and each keeps it
    check("wrappers: the container wrappers are found (guard not vacuous)", len(wrapped) >= 8, len(wrapped))
    discarded = [l for l in wrapped if "_setup >/dev/null" in l or "_setup 1>/dev/null" in l]
    check("wrappers: none throws the seam's diagnosis away", discarded == [], discarded)
    kept = [l for l in wrapped if "make _setup" in l and ">/dev/null" not in l.split("make _setup")[1][:12]]
    check("wrappers: every one keeps it (bare, or 1>&2)", len(kept) == len(wrapped), wrapped)
    for target in ("hermes-alias-check", "hermes-smoke"):
        recipe = make.split(f"\n{target}:\n", 1)[1].split("\n", 1)[0] if f"\n{target}:\n" in make else ""
        check(f"wrappers: {target} keeps _setup's output", "make _setup" in recipe
              and "_setup >/dev/null" not in recipe, recipe)


def main() -> int:
    print("install_hermes_ci.sh: one seam, one pin, a build that proves the alias")
    test_a_present_cli_is_used_and_nothing_is_downloaded()
    test_the_configured_installer_is_fetched_and_run()
    test_a_failed_download_is_a_loud_failure_without_a_second_attempt()
    test_an_installer_that_produces_nothing_falls_through_to_uv()
    test_nothing_works_is_a_loud_failure_naming_every_path()
    test_the_seam_never_handles_a_credential()
    test_the_dockerfile_installs_through_the_seam()
    test_the_dockerfile_asserts_the_alias_at_build_time()
    test_no_credential_value_is_baked_into_the_image()
    test_the_install_pin_has_one_definition_across_the_two_files()
    test_the_alias_has_one_name_for_the_writer_and_the_reader()
    test_the_alias_check_passes_on_the_pin_and_fails_on_a_different_one()
    test_the_seam_and_the_check_are_wired_where_ci_looks()
    test_no_wrapper_discards_the_seams_diagnosis()
    print(f"\nPASSED {_PASS} | FAILED {_FAIL}")
    return 1 if _FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
