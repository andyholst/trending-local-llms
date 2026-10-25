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


# ---------------------------------------------------------------------------
# the tool pin (issue #362): the scrape is a TERMINAL call
# ---------------------------------------------------------------------------
#: The legs the tool rule must reach — ONE list, as everywhere else (`update_trending.SEARCH_LEGS`).
TOOL_LEGS = ("nvidia", "metal", "cpu", "amd")

#: What the rule must SAY to be a rule and not a slogan: the route, the forbidden tool, WHY it is
#: forbidden (the scrub, the forced form it does not unwrap, the 401 that follows), the two web
#: tools that cannot carry the key, and the one supported Python route (the in-process write).
TOOL_PHRASES = ("terminal", "execute_code", "_hermes_force_", "secret", "401",
                "web_extract", "web_search", "scripts/update_trending.py --write-raw")


def _leg_recipe(mk: str, leg: str) -> str:
    """The `_search-<leg>` recipe text (everything up to the next target)."""
    return mk.split(f"_search-{leg}:", 1)[1].split("\n.PHONY", 1)[0]


def _tool_ask(mk: str) -> str:
    """The ONE `TOOL_ASK` definition's value, or '' when there is none."""
    m = re.search(r"^TOOL_ASK\s*:=\s*(.+)$", mk, re.M)
    return m.group(1) if m else ""


def _tool_rule_violations(mk: str) -> list[str]:
    """Everything the tool rule is missing — empty means every leg is pinned (one predicate, so the
    RED proof below runs the SAME check against the pre-change prompts)."""
    bad: list[str] = []
    if len(re.findall(r"^TOOL_ASK\s*:=", mk, re.M)) != 1:
        bad.append("TOOL_ASK is not defined exactly once")
    body = _tool_ask(mk)
    # Case-insensitive: the rule says "TERMINAL tool" and "_HERMES_FORCE_" — the words, not a casing.
    for phrase in TOOL_PHRASES:
        if phrase not in body.lower():
            bad.append(f"TOOL_ASK never says {phrase!r}")
    # Embedded in each leg's `hermes -z "…"`: a `$` or a `"` would expand or close that string.
    for ch in ('"', "$"):
        if ch in body:
            bad.append(f"TOOL_ASK carries {ch!r}, which breaks the -z shell string")
    for leg in TOOL_LEGS:
        recipe = _leg_recipe(mk, leg)
        if "$(TOOL_ASK)" not in recipe:
            bad.append(f"prompt {leg} does not carry $(TOOL_ASK)")
        if "TERMINAL tool" in recipe:
            bad.append(f"prompt {leg} inlines its own copy of the rule")
    return bad


def test_every_search_leg_pins_the_scrape_to_the_terminal_tool():
    bad = _tool_rule_violations((ROOT / "Makefile").read_text())
    check("tool: every leg is pinned from ONE definition", not bad, "; ".join(bad))


def test_the_tool_rule_names_the_terminal_and_refuses_execute_code():
    body = _tool_ask((ROOT / "Makefile").read_text())
    check("tool: it names the terminal tool as the route", "TERMINAL tool" in body, body[:120])
    check("tool: it refuses execute_code outright",
          "execute_code" in body and "NEVER use execute_code" in body, body[:200])
    check("tool: it says WHY (the scrub, the forced form, the 401)",
          "secret-named" in body and "_HERMES_FORCE_" in body and "401" in body, body[:200])
    check("tool: it rules out the two web tools",
          "web_extract" in body and "web_search" in body, body[:200])
    check("tool: it names the supported Python route",
          "scripts/update_trending.py --write-raw" in body and "in-process" in body, body[:200])


def test_the_tool_rule_guard_is_red_on_the_old_makefile():
    """Rule 6c: a guard that passes on the code before the fix guards nothing.

    `origin/master`'s four prompts carried no tool rule — the shape this builds by dropping the
    definition and every reference to it. The SAME predicate must then go red, naming each leg.
    """
    mk = (ROOT / "Makefile").read_text()
    old = re.sub(r"^TOOL_ASK\s*:=.*\n", "", mk, flags=re.M).replace("$(TOOL_ASK) ", "")
    bad = _tool_rule_violations(old)
    check("old makefile: the guard goes RED", bool(bad), "no violation on the pre-change prompts")
    check("old makefile: it names the missing definition",
          any("exactly once" in b for b in bad), "; ".join(bad))
    check("old makefile: and every unpinned leg",
          all(any(leg in b for b in bad) for leg in TOOL_LEGS), "; ".join(bad))


def test_the_written_procedure_pins_the_same_tool():
    """A leg told to load the guide must not be led back to `execute_code` (issue #362)."""
    for rel in ("skills/gather-data.md", ".hermes/skills/data-search/SKILL.md"):
        text = (ROOT / rel).read_text()
        check(f"{rel}: names the terminal tool", "terminal" in text.lower(), "")
        check(f"{rel}: names execute_code as forbidden", "execute_code" in text, "")
        check(f"{rel}: says the child loses the credential",
              "_HERMES_FORCE_" in text and "401" in text, "")
        check(f"{rel}: names the in-process write route",
              "scripts/update_trending.py --write-raw" in text, "")
        check(f"{rel}: carries no instruction to scrape from execute_code",
              "scrape from `execute_code`" not in text, "")


def main() -> int:
    print("search-leg key wiring (issues #357/#355/#362)")
    test_every_leg_prompt_names_the_variable_it_must_use()
    test_the_escaping_keeps_the_value_out_of_the_prompt()
    test_every_public_leg_checks_the_key_before_the_agent()
    test_a_set_variable_passes_and_the_value_is_never_printed()
    test_a_missing_variable_fails_loudly()
    test_an_empty_variable_counts_as_missing()
    test_the_explicit_opt_out_is_loud_and_never_silent()
    test_the_check_is_wired_to_a_make_target_ci_runs()
    test_every_search_leg_pins_the_scrape_to_the_terminal_tool()
    test_the_tool_rule_names_the_terminal_and_refuses_execute_code()
    test_the_tool_rule_guard_is_red_on_the_old_makefile()
    test_the_written_procedure_pins_the_same_tool()
    print(f"\nPASSED {_PASS} | FAILED {_FAIL}")
    return 1 if _FAIL else 0


if __name__ == "__main__":
    raise SystemExit(main())
