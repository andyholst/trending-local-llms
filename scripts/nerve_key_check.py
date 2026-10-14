#!/usr/bin/env python3
"""The nerve-plugin credential guard (issue #120).

The nerve supervision plugin is baked into the image as CODE (Dockerfile, pinned
to the Hermes plugin catalog commit). Its credential must reach the process ONLY
as a `-e` env var at run time — never baked into a layer, never written into a
file, never committed — exactly like NOUS_API_KEY / FIRECRAWL_API_KEY / HF_TOKEN
already are (AGENTS.md rule 3e).

THE NAME IS MEASURED, NOT ASSUMED. The issue that asked for this wiring proposed
`JEV_KEY` and explicitly left it "to be confirmed against the plugin's expected
env var". Measured at the pinned revision, the plugin resolves its provider key
by NAME in `hermes_nerve/client.py::PROVIDER_API_KEY_ENV` via the Hermes secret
scope / process env:

    openrouter -> OPENROUTER_API_KEY   (the plugin's own default jev_provider)
    typesafe   -> TYPESAFE_API_KEY     <- PRODUCTION: the provider this setup runs
    opencode   -> OPENCODE_API_KEY

There is no `JEV_KEY` anywhere in the plugin (or in the Hermes plugin catalog
entry that pins it), so wiring that name would register a variable nothing
reads — a silent failure, which is the opposite of what the issue asks for. The
pipeline therefore wires the VERIFIED name, and this guard fails if anyone wires
a name the plugin does not resolve.

What it checks (all offline; the live plugin proof runs when the image has it):

  * Dockerfile   — the plugin is installed pinned as code; no ENV/COPY of a
                   credential; no credential literal anywhere in the build context.
  * Makefile     — DOCKER_RUN and TEST_RUN forward the credential with `-e`
                   ONLY, under the verified NAME; `_setup` never writes a key
                   value into config.yaml (non-secret settings only).
  * workflows    — every pipeline workflow that runs the container exports the
                   secret by that name so the `-e` resolves, and never echoes it.
  * plugin proof — with the key ABSENT the plugin raises its loud "… is not
                   configured"; with a placeholder present it does not, so a run
                   missing the key can never degrade silently.

  python3 scripts/nerve_key_check.py            # human report, exit 1 on a finding
  python3 scripts/nerve_key_check.py --quiet    # only the verdict line

Wired: `make nerve-check` (internal `_nerve-check` recipe + docker wrapper), run
by qa-validate's `validate` job. Guarded by tests/test_nerve_key_wiring.py
(rule 6d — a check no target runs is a defect). Stdlib only.
"""
from __future__ import annotations

import argparse
import glob
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# The pin is the Hermes plugin catalog's own entry (plugin-catalog/nerve.yaml in
# the Hermes source tree): keeltrace/hermes-nerve at this exact commit, MIT,
# requires_env: []. `hermes plugins install` accepts only an exact 40-char SHA.
PLUGIN_SOURCE = "keeltrace/hermes-nerve"
PLUGIN_REF = "3de7d94982b7a2cb87c829e4b2366ced927d8fed"

# The verified credential NAME per provider, from the plugin's client at the pin
# (hermes_nev/client.py::PROVIDER_API_KEY_ENV). The pipeline pins the provider
# PRODUCTION uses (never the plugin's own default), so it forwards THAT name; the
# alternates are listed for the guard and documented in AGENTS.md, never wired as
# well.
PROVIDER_KEY_ENV = {
    "openrouter": "OPENROUTER_API_KEY",
    "typesafe": "TYPESAFE_API_KEY",
    "opencode": "OPENCODE_API_KEY",
}
# PRODUCTION's provider, measured on the host Hermes that this pipeline mirrors:
# `plugins.entries.nerve.settings.jev_provider = typesafe` (and
# `typesafe_model = jev-latest`), with `TYPESAFE_API_KEY` in the profile env.
# Wiring the plugin's own default (`openrouter`) would forward a name production
# never sets, so the plugin would fail on `TYPESAFE_API_KEY is not configured`.
DEFAULT_PROVIDER = "typesafe"

# ANY provider's credential name — echoing must be caught whichever one a file
# happens to use, not only the provider this pipeline pins.
ANY_KEY_RE = "(?:" + "|".join(re.escape(v) for v in sorted(PROVIDER_KEY_ENV.values())) + ")"

# Workflows that run a container target (and therefore need the `-e` to resolve).
CONTAINER_WORKFLOWS = ("refresh-bot.yml", "fix-bot.yml", "qa-validate.yml", "issue-bot.yml")

_SHA40 = re.compile(r"^[0-9a-f]{40}$")

# Credential SHAPES. Assembled so this file never trips the secret scan itself.
_SHAPES = (
    ("anthropic/openai key", re.compile(r"\bsk-[A-Za-z0-9_-]{16,}")),
    ("huggingface/github/slack token",
     re.compile(r"\b(?:hf_|ghp_|gho_|github_pat_|xox[baprs]-)[A-Za-z0-9_-]{16,}")),
    ("bearer literal", re.compile(r"(?i)authorization:\s*bearer\s+(?!\*\*\*)[A-Za-z0-9._-]{20,}")),
    ("long signed literal", re.compile(r"\beyJ[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{20,}")),
)

# `ENV <NAME>_KEY=<value>` / `ARG <NAME>_TOKEN=<value>` — a credential baked into
# the image (a layer is readable by anyone who pulls the public GHCR image).
_DOCKER_ENV_SECRET = re.compile(
    r"(?im)^\s*(?:ENV|ARG)\s+([A-Z0-9_]*(?:KEY|TOKEN|SECRET|PASSWORD)[A-Z0-9_]*)\s*=\s*\S+")

# `hermes config set <path with key/token/secret> <value>` where the value is NOT
# an env-var NAME (an all-caps identifier) and not a shell reference: such a
# value is a literal written into config.yaml. The path must name a credential —
# `…key_env NOUS_API_KEY` is a NAME and stays legal, `…max_tokens 65536` is not
# a credential path at all.
_CONFIG_SET = re.compile(r"(?im)^.*hermes\s+config\s+set\s+(\S+)\s+(\S+)\s*$")
_CRED_SEGMENT = re.compile(r"(?i)^(?:[a-z0-9]+_)*(?:api_)?(?:key|token|secret|password)(?:_env)?$")
_ENV_NAME = re.compile(r"^[A-Z][A-Z0-9_]*$")


def _credential_path(path: str) -> bool:
    return bool(_CRED_SEGMENT.match(path.rsplit(".", 1)[-1]))


def _literal_value(value: str) -> bool:
    """A value that is a secret literal: not an env-var NAME, not a shell/env
    reference, not a plain scalar."""
    if value.startswith("$") or value.startswith('"$'):
        return False
    return not (_ENV_NAME.match(value) or re.fullmatch(r"-?[0-9.]+", value))

# `-e` flags the container wrappers pass.
_ENV_EXPORT = re.compile(r"(?m)^\s*([A-Z][A-Z0-9_]*):\s*\$\{\{\s*secrets\.([A-Za-z0-9_]+)\s*\}\}\s*$")

_KEY_ENV_VAR = re.compile(r"(?m)^NERVE_KEY_ENV\s*:?=\s*(\S+)\s*$")
_PROVIDER_VAR = re.compile(r"(?m)^NERVE_PROVIDER\s*:?=\s*(\S+)\s*$")


def read(rel: str) -> str:
    p = ROOT / rel
    return p.read_text(errors="ignore") if p.exists() else ""


def forbidden_shapes(text: str, rel: str = "") -> list[str]:
    """Credential SHAPES present in `text` — a value must never be written into a
    tracked file, so any hit is a finding (rule 3d, enforced by `make secret-scan`
    in CI, and by this check for the nerve credential specifically)."""
    hits = []
    for label, rx in _SHAPES:
        for m in rx.finditer(text):
            hits.append(f"{rel}: {label} at offset {m.start()}: {m.group(0)[:12]}…")
    return hits


def check_dockerfile(text: str) -> list[str]:
    """The plugin is CODE in the image; the credential is not."""
    out = []
    if PLUGIN_SOURCE not in text:
        out.append(f"Dockerfile: does not install the plugin from {PLUGIN_SOURCE}")
    if '--ref "$NERVE_PLUGIN_REF"' not in text:
        out.append("Dockerfile: the plugin install is not pinned with --ref \"$NERVE_PLUGIN_REF\"")
    m = re.search(r"(?m)^ARG\s+NERVE_PLUGIN_REF\s*=\s*(\S+)\s*$", text)
    if not m or not _SHA40.match(m.group(1)):
        out.append("Dockerfile: ARG NERVE_PLUGIN_REF is not an exact 40-character commit SHA")
    baked = [f"ENV {g}" for g in _DOCKER_ENV_SECRET.findall(text)]
    if baked:
        out.append(f"Dockerfile: a credential is baked into the image: {', '.join(sorted(set(baked)))}")
    for line in text.splitlines():
        if re.match(r"\s*(ENV|ARG)\s+JEV_KEY\b", line):
            out.append("Dockerfile: JEV_KEY is not an env var the plugin resolves — do not bake it")
        if re.match(r"\s*COPY\s+.*(?:config\.yaml|\.env)\s*$", line):
            out.append("Dockerfile: a config/.env file is COPYed into the image")
    return out


def check_makefile(text: str) -> list[str]:
    """The credential is forwarded with `-e` only, under the verified NAME."""
    out = []
    m = re.search(r"(?m)^\s*(?:DOCKER_RUN|TEST_RUN)\s*:?=\s*docker run[^\n]*", text)
    if not m:
        out.append("Makefile: no DOCKER_RUN/TEST_RUN docker wrapper found")
    for name in ("DOCKER_RUN", "TEST_RUN"):
        blk = re.search(rf"(?ms)^{name}\s*:?=.*?(?=^\S|\Z)", text)
        body = blk.group(0) if blk else ""
        if "$(NERVE_KEY_ENV)" not in body or not re.search(r"-e\s+\$\(NERVE_KEY_ENV\)", body):
            out.append(f"Makefile: {name} does not forward the credential as `-e $(NERVE_KEY_ENV)`")
    key_env_var = _KEY_ENV_VAR.search(text)
    if not key_env_var:
        out.append("Makefile: NERVE_KEY_ENV is not defined (the name the plugin actually resolves)")
    else:
        name = key_env_var.group(1)
        if name not in PROVIDER_KEY_ENV.values():
            out.append(f"Makefile: NERVE_KEY_ENV={name} is not a name the pinned plugin resolves "
                       f"({', '.join(sorted(PROVIDER_KEY_ENV.values()))})")
        prov = _PROVIDER_VAR.search(text)
        want = PROVIDER_KEY_ENV.get(prov.group(1), "") if prov is not None else ""
        if want and name != want:
            out.append(f"Makefile: NERVE_PROVIDER={prov.group(1) if prov else '?'} resolves {want}, not {name}")
        # A CONSISTENT pair is not enough: the provider must be the one the setup
        # runs. `openrouter` + `OPENROUTER_API_KEY` is self-consistent and still
        # wrong — production sets TYPESAFE_API_KEY, so the plugin would be
        # configured for a provider whose key is not in the env at all (the
        # mistake this guard was written after).
        if prov is None:
            out.append(f"Makefile: NERVE_PROVIDER is not defined (the setup runs {DEFAULT_PROVIDER})")
        elif prov.group(1) != DEFAULT_PROVIDER:
            out.append(f"Makefile: NERVE_PROVIDER={prov.group(1)} is not the provider the setup runs "
                       f"({DEFAULT_PROVIDER}) — the plugin would be pointed at a provider whose key "
                       f"is not in the env, so it fails on {PROVIDER_KEY_ENV[DEFAULT_PROVIDER]} "
                       f"is not configured")
    if re.search(r"-e\s+JEV_KEY\b", text):
        out.append("Makefile: forwards -e JEV_KEY, which the pinned plugin never reads")
    # `_setup` writes SETTINGS, never a key value
    setup = re.search(r"(?ms)^_setup:.*?(?=^\S|\Z)", text)
    body = setup.group(0) if setup else ""
    for path, value in _CONFIG_SET.findall(body):
        if _credential_path(path) and _literal_value(value):
            out.append(f"Makefile: _setup writes a literal credential into config.yaml "
                       f"(`config set {path} …{value[-4:] if len(value) > 4 else ''}`)")
    if re.search(rf"(?im)^.*echo\s+.*\$\(NERVE_KEY_ENV\)|^.*echo\s+.*\$\{{?{ANY_KEY_RE}\b", body):
        out.append("Makefile: _setup echoes the credential")
    return out


def check_workflows(texts: dict[str, str]) -> list[str]:
    """Every workflow that runs the container must let the `-e` resolve."""
    out = []
    key = PROVIDER_KEY_ENV[DEFAULT_PROVIDER]
    for name in CONTAINER_WORKFLOWS:
        text = texts.get(name, "")
        if not text:
            out.append(f"{name}: missing")
            continue
        exported = {n: s for n, s in _ENV_EXPORT.findall(text)}
        if key not in exported:
            out.append(f"{name}: does not pass the credential via `env: … ${{{{ secrets.… }}}}` "
                       f"(the `-e` flag would resolve to nothing)")
        elif exported[key] != key:
            out.append(f"{name}: exports secrets.{exported[key]} as "
                       f"{key} — the name the plugin resolves must be the env name")
        for line in text.splitlines():
            if re.search(rf"\becho\b.*\$\{{?\s*{ANY_KEY_RE}\b", line):
                out.append(f"{name}: echoes the credential")
    return out


def plugin_dir() -> Path | None:
    """Where the pinned plugin lives in this environment, if it is installed."""
    homes = [os.environ.get("HERMES_HOME") or "", str(Path.home() / ".hermes")]
    for home in homes:
        if not home:
            continue
        pats = [f"{home}/plugins/*/hermes_nerve", f"{home}/plugins/hermes_nerve",
                f"{home}/profiles/*/plugins/*/hermes_nerve"]
        for pat in pats:
            for hit in glob.glob(pat):
                if (Path(hit) / "client.py").exists():
                    return Path(hit).parent
    return None


def runtime_proof(directory: Path | None) -> tuple[bool | None, str]:
    """With the credential ABSENT the plugin must fail LOUDLY (a run without the
    key may never degrade silently to another provider). Returns (ok|None, msg);
    A missing plugin is NOT a pass with a note: the image must be built from the
    repo's Dockerfile, which installs it, and a check that cannot run may not
    silently degrade (the repo's "no skipped tests" rule). The caller turns this
    into a finding naming the cause and the fix."""
    if directory is None:
        return False, ("the nerve plugin is NOT installed in this environment: this image "
                       "predates the Dockerfile that pins it. Rebuild it (`make docker-build`) "
                       "or run against the base the pipeline publishes for this Dockerfile — "
                       "the plugin-presence assertion may not degrade to a note [#135]")
    code = (
        "import sys; sys.path.insert(0, sys.argv[1]);\n"
        "from hermes_nerve.client import JevClient, JevError\n"
        "try:\n"
        "    JevClient()\n"
        "except JevError as e:\n"
        "    print('LOUD:', e); sys.exit(3)\n"
        "print('NO-ERROR')\n"
    )
    # Every provider key is stripped, then PRODUCTION's provider is SELECTED
    # explicitly: `HERMES_NERVE_PROVIDER` decides which name the plugin reads, so
    # a bare run would test the plugin's own default instead of the setup's.
    # With the provider selected and no key, the plugin must name THAT key as
    # missing; with a placeholder under that name it must construct.
    key = PROVIDER_KEY_ENV[DEFAULT_PROVIDER]
    env = {k: v for k, v in os.environ.items()
           if k not in set(PROVIDER_KEY_ENV.values())}
    env["HERMES_NERVE_PROVIDER"] = DEFAULT_PROVIDER
    absent = subprocess.run([sys.executable, "-c", code, str(directory)],
                            capture_output=True, text=True, env=env, timeout=60)
    if absent.returncode != 3 or f"{key} is not configured" not in absent.stdout:
        return False, (f"plugin did not fail loudly without the key, naming {key} "
                       f"(rc={absent.returncode}, out={absent.stdout.strip()[:120]!r}, "
                       f"err={absent.stderr.strip()[-160:]!r})")
    with_key = subprocess.run([sys.executable, "-c", code, str(directory)],
                              capture_output=True, text=True, timeout=60,
                              env={**env, key: "placeholder-not-a-key"})
    if with_key.returncode == 3:
        return False, (f"plugin still reports {key} missing when it IS present in the "
                       f"environment (provider {DEFAULT_PROVIDER})")
    return True, (f"loud without the key ({key} is not configured, provider {DEFAULT_PROVIDER}), "
                  f"silent-with-key proof ok")


def scan_tree() -> list[str]:
    """Walk the tracked pipeline files by DIRECTORY + suffix (never a hand-kept
    list — the same technique as the model-pin scan) for a credential SHAPE. A
    new script, workflow, skill or test is covered the moment it lands;
    `data/` (captured X post text) and fixtures are excluded on purpose."""
    targets = ["Makefile", "AGENTS.md", "README.md", ".gitleaks.toml", "Dockerfile",
               "Dockerfile.test", "config.yaml", ".env", "site/.env",
               "requirements.txt", "requirements-test.txt"]
    for d in (".github", "scripts", "skills", "tests"):
        targets += [str(p.relative_to(ROOT)) for p in sorted((ROOT / d).rglob("*"))
                    if p.is_file() and p.suffix in {".md", ".yml", ".yaml", ".sh", ".py", ".toml"}
                    and "__pycache__" not in p.parts]
    hits = []
    for rel in targets:
        p = ROOT / rel
        if p.exists() and p.is_file():
            hits += forbidden_shapes(p.read_text(errors="ignore"), rel)
    return hits


def run_all() -> tuple[list[str], list[str]]:
    """Returns (findings, notes)."""
    findings: list[str] = []
    notes: list[str] = []
    findings += scan_tree()
    files = {
        "Dockerfile": read("Dockerfile"),
        "Makefile": read("Makefile"),
    }
    findings += check_dockerfile(files["Dockerfile"])
    findings += check_makefile(files["Makefile"])
    findings += check_workflows({n: read(f".github/workflows/{n}") for n in CONTAINER_WORKFLOWS})
    ok, msg = runtime_proof(plugin_dir())
    if not ok:
        findings.append(f"plugin: {msg}")
    else:
        notes.append(f"plugin: {msg}")
    return findings, notes


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="nerve-plugin credential guard (issue #120)")
    ap.add_argument("--quiet", action="store_true", help="print only the verdict line")
    a = ap.parse_args(argv)
    findings, notes = run_all()
    if not a.quiet:
        print("nerve credential guard (issue #120)")
        print(f"  plugin: {PLUGIN_SOURCE} @ {PLUGIN_REF[:8]} (Hermes plugin catalog pin)")
        print(f"  credential name: {PROVIDER_KEY_ENV[DEFAULT_PROVIDER]} "
              f"(provider {DEFAULT_PROVIDER}; alternates {', '.join(sorted(set(PROVIDER_KEY_ENV.values()) - {PROVIDER_KEY_ENV[DEFAULT_PROVIDER]}))})")
        for n in notes:
            print(f"  note: {n}")
        for f in findings:
            print(f"  FAIL {f}")
    if findings:
        print(f"NERVE KEY CHECK FAILED ({len(findings)} finding(s)): the credential must reach "
              f"Hermes only as a `-e` env var under a name the plugin resolves, never baked and "
              f"never a literal (AGENTS.md rule 3e).")
        return 1
    print("NERVE KEY CHECK PASSED: plugin pinned as code, credential forwarded by name only, "
          "no literal in the tree, plugin fails loudly without it.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
