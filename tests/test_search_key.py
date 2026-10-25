#!/usr/bin/env python3
"""The search legs' key wiring: the prompt names the variable, and a missing key fails loudly.

Issue #357. Two defects, both measured in the real pipeline:

* the four `_search-*` prompts told the agent to send `Authorization: Bearer \\$${FI...KEY}` — a
  variable name that does not exist (13 characters, byte-verified). The header it built resolved to
  nothing, so every leg failed with HTTP 401 while `FIRECRAWL_API_KEY` sat in its environment.
* nothing checked the key, so a leg with no usable credential ran anyway, and the agent spent its
  turns hunting for one — writing `export FIRECRAWL_API_KEY=<what to put here>` into a public log,
  the placeholder shape that is one paste away from a real value (#355).

The prompt must therefore name the variable and never carry the value: the escaping is asserted at
the SHELL level (a fixture recipe run through make), not by reading the Makefile — a backslash too
few would expand the secret straight into the prompt and into the log.

NO-SKIP POLICY: a missing prerequisite is a LOUD FAILURE, never a skip.

Wired into `make test` (rule 6d). Runs as a plain script (the test image's pytest path is dead,
issue #176) and under pytest.
"""
from __future__ import annotations

import os
import re
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "scripts" / "require_env.py"

_PASS = 0
_FAIL = 0

#: A sentinel for the shell-level proof. Not a credential: it exists so the assertions can look for
#: the VALUE where it must never appear (in the prompt an agent receives).
SENTINEL = "SENTINEL-KEY-VALUE-0123456789"


def check(name, cond, detail=""):
    global _PASS, _FAIL
    if cond:
        _PASS += 1
        print(f"  ok  {name}")
    else:
        _FAIL += 1
        print(f"  FAIL {name}" + (f"  [{detail}]" if detail else ""))


# ---------------------------------------------------------------------------
# the prompt names the variable — and can never carry its value
# ---------------------------------------------------------------------------
def test_every_leg_prompt_names_the_variable_it_must_use():
    """The measured defect: `Bearer \\$${FI...KEY}`, a name that does not exist."""
    mk = (ROOT / "Makefile").read_text()
    for leg in ("nvidia", "metal", "cpu", "amd"):
        prompt = re.search(rf"\n_search-{leg}:\n(.*?)\n\n", mk, re.S)
        body = prompt.group(1) if prompt else ""
        check(f"prompt {leg}: names the real variable",
              r"\$${FIRECRAWL_API_KEY}" in body, body[:120])
        check(f"prompt {leg}: carries no elided name",
              "FI...KEY" not in body and "FI..KEY" not in body, "elided form present")
    check("prompt: no elided variable name anywhere in the Makefile",
          mk.count("FI...KEY") == 0, mk.count("FI...KEY"))
    # Scoped to the prompts: the Makefile legitimately mentions the mask `***` in prose.
    for leg in ("nvidia", "metal", "cpu", "amd"):
        prompt = re.search(rf"\n_search-{leg}:\n(.*?)\n\n", mk, re.S)
        body = prompt.group(1) if prompt else ""
        check(f"prompt {leg}: no asterisk placeholder in the header instruction",
              "Authorization: Bearer ***" not in body, body[:120])


def test_every_leg_prompt_pins_the_tool_the_key_reaches():
    """Issue #362: #359 made the key visible in the TERMINAL tool, and `execute_code`
    children stay keyless — `tools/code_execution_env.py::_scrub_child_env` drops every
    name carrying a secret substring (`KEY`, `TOKEN`, `AUTH` …) and never unwraps
    `_HERMES_FORCE_`, while `env_passthrough` refuses a blocklisted provider name. The
    prompts said only "POST … with header", so the tool was the agent's choice: a leg
    that picks `execute_code` sends an EMPTY Bearer and brings back the silent 401.
    """
    mk = (ROOT / "Makefile").read_text()
    for leg in ("nvidia", "metal", "cpu", "amd"):
        prompt = re.search(rf"\n_search-{leg}:\n(.*?)\n\n", mk, re.S)
        body = prompt.group(1) if prompt else ""
        check(f"prompt {leg}: takes the tool pin from $(SCRAPE_ASK)",
              "$(SCRAPE_ASK)" in body, body[:140])
    definition = mk.split("SCRAPE_ASK :=", 1)[1].split("\n", 1)[0] if "SCRAPE_ASK :=" in mk else ""
    check("tool pin: names the terminal tool", "TERMINAL tool" in definition, definition[:100])
    check("tool pin: forbids execute_code", "Never make it from execute_code" in definition,
          definition[:140])
    check("tool pin: names the empty header it causes",
          "EMPTY Authorization header" in definition, definition[:140])
    check("tool pin: names the 401 that follows", "HTTP 401" in definition, definition[:140])
    check("tool pin: names the in-process route",
          "python3 scripts/update_trending.py" in definition, definition[:140])
    check("tool pin: a 401 is a blocker, not a key hunt",
          "blocker to report" in definition and "never a reason to hunt for a key" in definition,
          definition[-140:])


def test_the_tool_pin_has_exactly_one_definition():
    """ONE definition, like ENGINE_ASK / DIM_ASK: four inline copies would drift, and a
    leg that kept the old sentence would silently reopen the keyless route (issue #362).
    """
    mk = (ROOT / "Makefile").read_text()
    check("tool pin: SCRAPE_ASK is defined exactly once", mk.count("SCRAPE_ASK :=") == 1,
          str(mk.count("SCRAPE_ASK :=")))
    definition = mk.split("SCRAPE_ASK :=", 1)[1].split("\n", 1)[0] if "SCRAPE_ASK :=" in mk else ""
    check("tool pin: carries no double quote (it lives inside `hermes -z \"…\"`)",
          '"' not in definition, definition[:60])
    check("tool pin: carries no `$` (the shell would expand it)",
          "$" not in definition, definition[:60])
    for leg in ("nvidia", "metal", "cpu", "amd"):
        recipe = mk.split(f"_search-{leg}:", 1)[1].split("\n.PHONY", 1)[0]
        check(f"{leg}: keeps no second copy of the pin",
              "Never make it from execute_code" not in recipe, recipe[-160:])
    # The pin must be reachable from a target CI runs, not from a variable nothing uses.
    check("tool pin: a leg a workflow calls expands it",
          "make search-${{ matrix.backend }}" in
          (ROOT / ".github" / "workflows" / "refresh-bot.yml").read_text(), "")


def test_the_escaping_keeps_the_value_out_of_the_prompt():
    """Shell-level proof: `\\$${NAME}` reaches the agent as `${NAME}` — never as the value.

    The recipe is built in a fixture Makefile with the SAME escaping the real prompts use: one
    backslash fewer and the shell expands the secret into the prompt text (and from there into the
    log), which is the whole point of quoting it this way.
    """
    td = Path(tempfile.mkdtemp())
    out = td / "out.txt"
    (td / "Makefile").write_text(
        'x:\n\t@printf %s "with header \'Authorization: Bearer \\$${FIRECRAWL_API_KEY}\' and body" '
        f'> {out}\n')
    env = dict(os.environ, FIRECRAWL_API_KEY=SENTINEL)
    r = subprocess.run(["make", "x"], cwd=str(td), env=env, capture_output=True, text=True)
    check("escaping: the fixture recipe runs", r.returncode == 0, r.stderr[-200:])
    text = out.read_text()
    check("escaping: the agent receives the VARIABLE NAME",
          "${FIRECRAWL_API_KEY}" in text, text)
    check("escaping: and never the VALUE", SENTINEL not in text, text)


def test_every_public_leg_checks_the_key_before_the_agent():
    mk = (ROOT / "Makefile").read_text()
    for leg in ("nvidia", "metal", "cpu", "amd"):
        check(f"{leg}: the leg runs the pre-flight first",
              f"\nsearch-{leg}:\n\t@$(MAKE) --no-print-directory _search-preflight BACKEND={leg}\n" in mk, "")
    check("search: the parallel form checks the key too",
          "\nsearch:\n\t@$(MAKE) --no-print-directory _search-preflight" in mk, "")
    check("pre-flight: it requires the key by name",
          "scripts/require_env.py FIRECRAWL_API_KEY" in mk, "")
    check("pre-flight: and proves the backend answers (the ONE smoke implementation)",
          "\n_search-preflight:\n" in mk and "search-smoke BACKEND=$(BACKEND)" in mk, "")


# ---------------------------------------------------------------------------
# require_env.py
# ---------------------------------------------------------------------------
def _run_require(args, env):
    return subprocess.run(["python3", str(SCRIPT), *args], env=env, capture_output=True, text=True)


def test_a_set_variable_passes_and_the_value_is_never_printed():
    r = _run_require(["FIRECRAWL_API_KEY"], dict(os.environ, FIRECRAWL_API_KEY=SENTINEL))
    check("require-env: a set variable exits 0", r.returncode == 0, r.stderr[-200:])
    check("require-env: the value is never printed", SENTINEL not in (r.stdout + r.stderr), r.stdout)
    check("require-env: the NAME is reported", "FIRECRAWL_API_KEY" in r.stdout, r.stdout)


def test_a_missing_variable_fails_loudly():
    env = {k: v for k, v in os.environ.items() if k != "FIRECRAWL_API_KEY"}
    r = _run_require(["FIRECRAWL_API_KEY"], env)
    check("require-env: a missing variable exits 2", r.returncode == 2, r.returncode)
    check("require-env: it names the variable and says FATAL",
          "FIRECRAWL_API_KEY" in r.stderr and "FATAL" in r.stderr, r.stderr[-200:])
    check("require-env: it says how to fix it (the secret, on stdin)",
          "gh secret set" in r.stderr and "stdin" in r.stderr, r.stderr[-300:])


def test_an_empty_variable_counts_as_missing():
    """GitHub renders an unset secret as an empty string — the shape a missing key takes at run time."""
    r = _run_require(["FIRECRAWL_API_KEY"], dict(os.environ, FIRECRAWL_API_KEY=""))
    check("require-env: an EMPTY variable exits 2", r.returncode == 2, r.returncode)


def test_the_explicit_opt_out_is_loud_and_never_silent():
    env = {k: v for k, v in os.environ.items() if k != "FIRECRAWL_API_KEY"}
    r = _run_require(["FIRECRAWL_API_KEY", "--allow-unconfigured"], env)
    check("require-env: the opt-out exits 0", r.returncode == 0, r.returncode)
    check("require-env: and reports NOT CONFIGURED rather than a silent pass",
          "NOT CONFIGURED" in r.stdout, r.stdout)
    mk = (ROOT / "Makefile").read_text()
    check("require-env: the opt-out never reaches a workflow",
          "--allow-unconfigured" not in mk
          and all("--allow-unconfigured" not in p.read_text()
                  for p in (ROOT / ".github" / "workflows").glob("*.yml")), "")


def test_the_check_is_wired_to_a_make_target_ci_runs():
    """A script no target names runs nowhere (rule 6d)."""
    mk = (ROOT / "Makefile").read_text()
    check("wiring: `_search-preflight` exists", "_search-preflight:" in mk, "")
    check("wiring: it is in .PHONY", ".PHONY: _search-preflight" in mk, "")
    wf = (ROOT / ".github" / "workflows" / "refresh-bot.yml").read_text()
    check("wiring: the workflow calls a search leg that runs it",
          "make search-${{ matrix.backend }}" in wf, "")


def main() -> int:
    print("search-leg key wiring (issues #357/#355)")
    test_every_leg_prompt_names_the_variable_it_must_use()
    test_every_leg_prompt_pins_the_tool_the_key_reaches()
    test_the_tool_pin_has_exactly_one_definition()
    test_the_escaping_keeps_the_value_out_of_the_prompt()
    test_every_public_leg_checks_the_key_before_the_agent()
    test_a_set_variable_passes_and_the_value_is_never_printed()
    test_a_missing_variable_fails_loudly()
    test_an_empty_variable_counts_as_missing()
    test_the_explicit_opt_out_is_loud_and_never_silent()
    test_the_check_is_wired_to_a_make_target_ci_runs()
    print(f"\nPASSED {_PASS} | FAILED {_FAIL}")
    return 1 if _FAIL else 0


if __name__ == "__main__":
    raise SystemExit(main())
