#!/usr/bin/env python3
"""The agent's shell sees every credential a container receives (issue #359).

Hermes strips provider credentials from its terminal tool on purpose, so a key forwarded as
`-e FIRECRAWL_API_KEY` reached the container and Hermes while the agent's `curl` sent an EMPTY
Bearer — every refresh search leg got `HTTP 401` (runs 38902898149 … 39063620912) while the step
listing showed `FIRECRAWL_API_KEY: ***`. The fix forwards each key as `_HERMES_FORCE_<NAME>` from
ONE Makefile list; this suite proves it at three levels, with SENTINEL values only:

* the Makefile: the list names every credential a container receives, and the run wrappers forward
  every `_HERMES_FORCE_<NAME>` BY NAME — the value is never on a command line (a `make -n` with the
  sentinel set must not contain it);
* make's export: on the host, `make` really exports `_HERMES_FORCE_<NAME>` = `<NAME>` to a recipe
  (a fixture target run through the real Makefile), and exports nothing for an unset key;
* the REAL Hermes terminal (`scripts/agent_shell_keys_check.py` drives Hermes's own
  `LocalEnvironment`, no stand-in — rule 6m): RED with today's plain names (the blocklisted keys
  read EMPTY in the agent's shell), GREEN once the forced names are present.

NO-SKIP POLICY: a missing Hermes is a LOUD FAILURE, never a skip — `make test` runs this in the test
image, which carries the same Hermes the bots run.

Wired into `make test` (rule 6d). Runs as a plain script and under pytest.
"""
from __future__ import annotations

import os
import re
import subprocess
import tempfile
from pathlib import Path

from wiring import wired  # noqa: E402  (issues #176/#192)

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "scripts" / "agent_shell_keys_check.py"

# secret-output: test value — sentinels, never credentials.
SENTINEL = "SENTINELvalue0123456789abcdef"
FORCE = "_HERMES_FORCE_"

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


def _keys() -> list[str]:
    """AGENT_SHELL_KEYS as make itself expands it (never a second copy of the list)."""
    r = subprocess.run(["make", "-s", "--no-print-directory", "-f", "Makefile", "-f", "-", "_print-keys"],
                       cwd=ROOT, input="_print-keys:\n\t@echo $(AGENT_SHELL_KEYS)\n",
                       capture_output=True, text=True, env=_clean_env())
    return r.stdout.split()


def _clean_env(**extra) -> dict:
    """The process env with every credential and every forced name removed, plus `extra`."""
    env = {k: v for k, v in os.environ.items()
           if not k.startswith(FORCE) and k not in
           ("NOUS_API_KEY", "FIRECRAWL_API_KEY", "HF_TOKEN", "TYPESAFE_API_KEY", "GH_TOKEN", "GITHUB_TOKEN")}
    env.update(extra)
    return env


# ---------------------------------------------------------------------------
# the Makefile: one list, forwarded by NAME
# ---------------------------------------------------------------------------
def test_the_list_names_every_credential_a_container_receives():
    keys = _keys()
    mk = (ROOT / "Makefile").read_text()
    for name in ("DOCKER_RUN", "TEST_RUN"):
        blk = re.search(rf"(?ms)^{name}\s*:=.*?(?=^\S|\Z)", mk)
        body = blk.group(0) if blk else ""
        # TWO legal shapes reach a container (rule 3e): a credential forwarded BY NAME (`-e NAME` —
        # the agent's shell must be able to see it, so NAME must be in AGENT_SHELL_KEYS) and a
        # NON-SECRET SETTING given explicitly (`-e NAME=value`, a literal that is never a forwarded
        # host value, e.g. `PYTHONUNBUFFERED=1` for issue #591). The old single regex read the name
        # out of the setting shape too — `\b` matches on the `=` — so it demanded that
        # `PYTHONUNBUFFERED` be an agent-shell credential, which no credential list can hold.
        tokens = re.findall(r"-e\s+([^\s\\]+)", body)
        plain = [t for t in tokens if not t.startswith(FORCE)]
        check(f"{name}: forwards the forced names", "$(AGENT_SHELL_FORWARD)" in body, body[-160:])
        for p in plain:
            setting, eq, value = p.partition("=")
            if eq:
                # a non-secret SETTING: never credential-shaped, and its value is a literal (a `$`
                # there would forward a host value — the leak shape `check-secret-output` refuses).
                # `setting not in keys`: a credential is NEVER given a literal value here — it is
                # forwarded by name, so baking one in could only be a value read off some host.
                check(f"{name}: `-e {setting}` is a NON-SECRET setting, never a credential",
                      setting not in keys and not setting.endswith(
                          ("_KEY", "_TOKEN", "_SECRET", "_PASSWORD", "_CREDENTIAL")), setting)
                check(f"{name}: `-e {setting}={value}` is a literal, never a forwarded host value",
                      "$" not in value, p)
                continue
            resolved = "TYPESAFE_API_KEY" if p == "$(NERVE_KEY_ENV)" else p
            check(f"{name}: `-e {p}` is also in AGENT_SHELL_KEYS (no key the agent cannot see)",
                  resolved in keys, keys)
    for k in ("NOUS_API_KEY", "FIRECRAWL_API_KEY", "HF_TOKEN", "TYPESAFE_API_KEY"):
        check(f"AGENT_SHELL_KEYS names {k}", k in keys, keys)


def test_the_forced_names_travel_by_name_never_by_value():
    env = _clean_env(FIRECRAWL_API_KEY=SENTINEL, NOUS_API_KEY=SENTINEL, HF_TOKEN=SENTINEL,
                     TYPESAFE_API_KEY=SENTINEL, IN_CONTAINER="")
    r = subprocess.run(["make", "-n", "--no-print-directory", "agent-shell-keys-check", "IN_CONTAINER="],
                       cwd=ROOT, env=env, capture_output=True, text=True)
    out = r.stdout + r.stderr
    for k in _keys():
        check(f"make -n: `-e {FORCE}{k}` is forwarded", f"-e {FORCE}{k}" in out, out[-300:])
    check("make -n: the VALUE never reaches a command line", SENTINEL not in out, "sentinel in argv")


# ---------------------------------------------------------------------------
# make really exports the forced names (and only for a set key)
# ---------------------------------------------------------------------------
def _recipe_lengths(env: dict) -> dict[str, int]:
    probe = "_probe:\n" + "".join(
        f'\t@printf "%s=%s\\n" {FORCE}{k} "$${{#{FORCE}{k}}}"\n' for k in _keys())
    r = subprocess.run(["make", "-s", "--no-print-directory", "-f", "Makefile", "-f", "-", "_probe", "IN_CONTAINER="],
                       cwd=ROOT, input=probe, env=env, capture_output=True, text=True)
    out = {}
    for line in r.stdout.splitlines():
        k, _, v = line.partition("=")
        if v.isdigit():
            out[k] = int(v)
    return out


def test_make_exports_the_forced_name_from_the_plain_one():
    got = _recipe_lengths(_clean_env(FIRECRAWL_API_KEY=SENTINEL, HF_TOKEN=SENTINEL))
    check("export: a set key is exported as _HERMES_FORCE_<NAME> (same length)",
          got.get(f"{FORCE}FIRECRAWL_API_KEY") == len(SENTINEL) and got.get(f"{FORCE}HF_TOKEN") == len(SENTINEL), got)
    check("export: an unset key exports nothing (no empty forced name)",
          got.get(f"{FORCE}NOUS_API_KEY") == 0, got)
    inside = subprocess.run(
        ["make", "-s", "--no-print-directory", "-f", "Makefile", "-f", "-", "_probe", "IN_CONTAINER=1"],
        cwd=ROOT, input=f'_probe:\n\t@printf "%s\\n" "$${{#{FORCE}FIRECRAWL_API_KEY}}"\n',
        env=_clean_env(FIRECRAWL_API_KEY=SENTINEL), capture_output=True, text=True)
    check("export: inside a container nothing is re-created (the check proves what docker forwarded)",
          inside.stdout.strip() == "0", inside.stdout + inside.stderr)


# ---------------------------------------------------------------------------
# the REAL Hermes terminal
# ---------------------------------------------------------------------------
def _run_check(env: dict, *extra) -> subprocess.CompletedProcess:
    return subprocess.run(["python3", str(SCRIPT), *_keys(), *extra], env=env, capture_output=True,
                          text=True, timeout=300)


def test_plain_names_leave_the_agent_shell_blind():
    """The measured defect, on the real Hermes: today's `-e NAME` only."""
    with tempfile.TemporaryDirectory() as home:
        env = _clean_env(HERMES_HOME=home, **{k: SENTINEL for k in _keys()})
        r = _run_check(env)
    out = r.stdout + r.stderr
    check("real Hermes: plain names -> RED (exit 1)", r.returncode == 1, out[-500:])
    check("real Hermes: FIRECRAWL_API_KEY reads EMPTY in the agent shell",
          "FIRECRAWL_API_KEY: container=set agent-shell=EMPTY" in out, out[-500:])
    check("real Hermes: the failure names the fix", f"{FORCE}<NAME>" in out, out[-300:])
    check("real Hermes: the value is never printed", SENTINEL not in out, "sentinel printed")


def test_forced_names_make_every_key_visible():
    with tempfile.TemporaryDirectory() as home:
        env = _clean_env(HERMES_HOME=home, **{k: SENTINEL for k in _keys()},
                         **{FORCE + k: SENTINEL for k in _keys()})
        r = _run_check(env)
    out = r.stdout + r.stderr
    check("real Hermes: forced names -> GREEN (exit 0)", r.returncode == 0, out[-500:])
    for k in _keys():
        check(f"real Hermes: {k} visible in the agent shell", f"{k}: container=set agent-shell=set (match" in out,
              out[-400:])
    check("real Hermes: the value is never printed", SENTINEL not in out, "sentinel printed")


def test_a_key_missing_from_the_container_is_loud():
    r = _run_check(_clean_env())
    check("missing key: exit 2, never a skip", r.returncode == 2, r.stdout + r.stderr)
    check("missing key: it is named", "FIRECRAWL_API_KEY" in r.stderr, r.stderr)
    r = _run_check(_clean_env(), "--allow-unconfigured")
    check("opt-out: says NOT CONFIGURED", r.returncode == 0 and "NOT CONFIGURED" in r.stdout, r.stdout)
    wf_lines = [l for p in (ROOT / ".github" / "workflows").glob("*.yml") for l in p.read_text().splitlines()]
    check("opt-out: never in a workflow",
          not any("agent-shell-keys" in l and "allow-unconfigured" in l for l in wf_lines), "")


def test_the_check_is_wired_to_a_make_target_ci_runs():
    mk = (ROOT / "Makefile").read_text()
    check("wiring: `_agent-shell-keys-check` runs the script, defaulting to the ONE list",
          "python3 scripts/agent_shell_keys_check.py $(AGENT_SHELL_CHECK_KEYS)" in mk
          and "AGENT_SHELL_CHECK_KEYS ?= $(AGENT_SHELL_KEYS)" in mk, "")
    pre = re.search(r"\n_search-preflight:\n((?:\t.*\n)+)", mk)
    check("wiring: every search leg proves the AGENT can see the credentials it uses before it starts",
          bool(pre) and 'agent-shell-keys-check AGENT_SHELL_CHECK_KEYS="FIRECRAWL_API_KEY HF_TOKEN"' in pre.group(1),
          pre.group(1) if pre else "")
    check("wiring: the public target runs it inside DOCKER_RUN (the bot image)",
          "\tagent-shell-keys-check:" not in mk and "\t$(DOCKER_RUN) make _agent-shell-keys-check" in mk, "")
    qa = (ROOT / ".github" / "workflows" / "qa-validate.yml").read_text()
    check("wiring: qa-validate runs `make agent-shell-keys-check`", "make agent-shell-keys-check" in qa, "")
    check("wiring: this suite is in `make test`", wired(__file__), "")


def main() -> int:
    print("agent-shell credentials (issue #359)")
    test_the_list_names_every_credential_a_container_receives()
    test_the_forced_names_travel_by_name_never_by_value()
    test_make_exports_the_forced_name_from_the_plain_one()
    test_plain_names_leave_the_agent_shell_blind()
    test_forced_names_make_every_key_visible()
    test_a_key_missing_from_the_container_is_loud()
    test_the_check_is_wired_to_a_make_target_ci_runs()
    print(f"\nPASSED {_PASS} | FAILED {_FAIL}")
    return 1 if _FAIL else 0


if __name__ == "__main__":
    raise SystemExit(main())
