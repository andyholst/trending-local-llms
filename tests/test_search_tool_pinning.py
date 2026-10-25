#!/usr/bin/env python3
"""The search legs scrape from the TERMINAL tool — the only one that can see the key (issue #362).

#359 made every credential a container receives visible in the agent's shell by forwarding it as
`_HERMES_FORCE_<NAME>`, which Hermes's terminal env builder unwraps. That route exists in exactly one
tool. The `execute_code` child is a different environment:
`tools/code_execution_env.py::_scrub_child_env` drops every name containing a secret substring
(`KEY`, `TOKEN`, `SECRET`, `PASSWORD`, `CREDENTIAL`, `AUTH`, `BEARER`, `COOKIE` …) and never unwraps
`_HERMES_FORCE_` (the forced name carries `KEY`, so it falls to the same rule). A leg that scraped
with `execute_code` would therefore read an EMPTY `FIRECRAWL_API_KEY` and send an empty Bearer — the
measured #359 defect, one tool over.

Nothing pinned the tool: the four `_search-*` prompts said "POST … with header", the preloaded
`data-search` skill named no tool, and `skills/gather-data.md` §1 told the agent to reach the mirror
"via `web_extract`" — which run 39063620912 (the amd leg) followed.

So the rule lives in ONE `TOOL_ASK` definition (the `ENGINE_ASK` / `DIM_ASK` shape) embedded by every
leg, and the two documents the agent reads say the same thing. This suite locks all of it — and
proves the wording really reaches the agent by expanding the recipe with `make -n`, never by
re-reading the Makefile's own text.

NO-SKIP POLICY: a leg whose prompt cannot be expanded is a LOUD failure, never a skip.

Wired into `make test` (rule 6d). Runs as a plain script and under pytest.
"""
from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "tests"))

from wiring import wired  # noqa: E402  (issues #176/#192)

LEGS = ("nvidia", "metal", "cpu", "amd")
SKILL = ROOT / ".hermes" / "skills" / "data-search" / "SKILL.md"
GUIDE = ROOT / "skills" / "gather-data.md"

#: A sentinel for the shell-level proof: it exists so the assertions can look for the VALUE where it
#: must never appear (inside the prompt an agent receives). Not a credential.
SENTINEL = "SENTINEL-KEY-VALUE-0123456789"

_PASS = 0
_FAIL = 0


def check(name, cond, detail: object = "") -> None:
    global _PASS, _FAIL
    if cond:
        _PASS += 1
        print(f"  ok  {name}")
    else:
        _FAIL += 1
        print(f"  FAIL {name}" + (f"  [{detail}]" if detail else ""))


def _makefile() -> str:
    return (ROOT / "Makefile").read_text(encoding="utf-8")


def _leg_body(mk: str, leg: str) -> str:
    """A leg's recipe text, the same shape `tests/test_search_key.py` reads."""
    m = re.search(rf"\n_search-{leg}:\n(.*?)\n\n", mk, re.S)
    return m.group(1) if m else ""


def _tool_ask(mk: str) -> str:
    m = re.search(r"^TOOL_ASK\s*:=\s*(.+)$", mk, re.M)
    return m.group(1) if m else ""


def _expanded_prompt(leg: str, extra_env: dict | None = None) -> str:
    """The prompt the agent really receives: `make -n` expands every variable for real.

    `_search-<leg>` is an INTERNAL target, so this needs no docker and no key. The environment is
    stripped of credentials unless the caller sets one, so a leaked value would be visible.
    """
    env = {k: v for k, v in os.environ.items()
           if k not in ("FIRECRAWL_API_KEY", "NOUS_API_KEY", "HF_TOKEN", "TYPESAFE_API_KEY")
           and not k.startswith("_HERMES_FORCE_")}
    env.update(extra_env or {})
    r = subprocess.run(["make", "-n", f"_search-{leg}"], cwd=str(ROOT), env=env,
                       capture_output=True, text=True, timeout=180)
    if r.returncode != 0:
        raise RuntimeError(f"`make -n _search-{leg}` failed (rc={r.returncode}): {r.stderr[-300:]}")
    m = re.search(r'hermes -z "(.*)"\s*\\', r.stdout, re.S)
    if not m:
        raise RuntimeError(f"`make -n _search-{leg}` printed no hermes -z prompt: {r.stdout[:300]}")
    return m.group(1)


# ---------------------------------------------------------------------------
# ONE definition, embedded by every leg
# ---------------------------------------------------------------------------
def test_the_rule_is_one_definition_and_every_leg_embeds_it():
    mk = _makefile()
    check("makefile: TOOL_ASK is defined exactly once",
          len(re.findall(r"^TOOL_ASK\s*:=", mk, re.M)) == 1,
          len(re.findall(r"^TOOL_ASK\s*:=", mk, re.M)))
    for leg in LEGS:
        body = _leg_body(mk, leg)
        check(f"{leg}: the prompt embeds $(TOOL_ASK)", "$(TOOL_ASK)" in body, body[:120])
    # The same rule must not be re-spelled inline: a copy drifts the moment one leg is edited.
    for leg in LEGS:
        body = _leg_body(mk, leg)
        check(f"{leg}: the rule is not restated inline",
              body.count("execute_code") == 0, body.count("execute_code"))


def test_the_rule_forbids_the_credential_less_tools():
    rule = _tool_ask(_makefile())
    check("rule: it exists", bool(rule), rule[:80])
    check("rule: it names the TERMINAL tool", "TERMINAL" in rule, rule[:120])
    check("rule: it names curl", "curl" in rule, rule[:120])
    for tool in ("execute_code", "web_extract", "web_search"):
        check(f"rule: it forbids {tool}", tool in rule, rule[:120])
    check("rule: it gives the reason (_scrub_child_env)",
          "_scrub_child_env" in rule, rule[:160])
    check("rule: it says the force form does not apply there",
          "_HERMES_FORCE_" in rule, rule[:160])
    check("rule: it names the in-process alternative",
          "scripts/update_trending.py" in rule, rule[:160])
    check("rule: it names the failure the agent would see (HTTP 401)",
          "401" in rule, rule[:160])
    # It is embedded in a `hermes -z "…"` string: a quote or a `$` would break the shell string or
    # expand a secret into the prompt (the #357 escaping defect).
    check("rule: it carries no double quote", '"' not in rule, rule[:120])
    check("rule: it carries no dollar sign", "$" not in rule, rule[:120])


def test_no_leg_prompt_invites_a_credential_less_tool():
    mk = _makefile()
    for leg in LEGS:
        body = _leg_body(mk, leg)
        # The prohibition itself lives in $(TOOL_ASK); what is left must not send the agent there.
        rest = body.replace("$(TOOL_ASK)", "")
        for tool in ("web_extract", "web_search", "execute_code"):
            check(f"{leg}: the prompt does not instruct {tool}", tool not in rest, rest[:160])


# ---------------------------------------------------------------------------
# the wording really reaches the agent
# ---------------------------------------------------------------------------
def test_the_wording_reaches_the_agent():
    for leg in LEGS:
        prompt = _expanded_prompt(leg)
        check(f"{leg}: the expanded prompt carries the terminal rule",
              "TERMINAL tool" in prompt, prompt[:160])
        check(f"{leg}: the expanded prompt forbids execute_code",
              "execute_code" in prompt and "web_extract" in prompt, prompt[:160])
        check(f"{leg}: the expanded prompt carries the reason",
              "empty Bearer" in prompt, prompt[:160])


def test_the_expanded_prompt_can_never_carry_the_value():
    prompt = _expanded_prompt("amd", {"FIRECRAWL_API_KEY": SENTINEL})
    check("escaping: the agent receives the VARIABLE NAME",
          "${FIRECRAWL_API_KEY}" in prompt, prompt[:160])
    check("escaping: and never the VALUE", SENTINEL not in prompt, "value leaked into the prompt")


# ---------------------------------------------------------------------------
# the documents the agent reads
# ---------------------------------------------------------------------------
def test_the_skill_and_the_guide_pin_the_same_tool():
    skill = SKILL.read_text(encoding="utf-8")
    guide = GUIDE.read_text(encoding="utf-8")
    for name, text in (("skill", skill), ("guide", guide)):
        check(f"{name}: it names the TERMINAL tool", "TERMINAL tool" in text, "")
        check(f"{name}: it forbids execute_code", "execute_code" in text, "")
        check(f"{name}: it explains why (_scrub_child_env)", "_scrub_child_env" in text, "")
        check(f"{name}: it offers the in-process route",
              "scripts/update_trending.py" in text, "")
    check("guide: it no longer sends the agent to web_extract for the mirror",
          "via `web_extract`" not in guide, "")
    check("guide: it says which tools must not be used for the mirror",
          "Do **not** reach the mirror with `execute_code`" in guide, "")


def test_the_documents_name_the_variable_that_exists():
    for name, path in (("skill", SKILL), ("guide", GUIDE)):
        text = path.read_text(encoding="utf-8")
        check(f"{name}: it names FIRECRAWL_API_KEY", "FIRECRAWL_API_KEY" in text, "")
        elided = [bad for bad in ("FIRE...Y", "FI..KEY", "FIRE…Y", "FIRECRAWL_API_K…") if bad in text]
        check(f"{name}: it carries no elided variable name", not elided, str(elided))


def test_the_rule_keeps_every_leg_inside_the_prompt_budget():
    """The gate's OWN measure, not a second copy of it: `check_agent_skills.prompt_of` sizes each
    recipe and `check()` reports an over-budget leg. Adding a rule must not push one over."""
    import check_agent_skills as CAS  # noqa: E402 — the gate's real implementation (rule 6m)

    for target, recipe in CAS.legs(_makefile()).items():
        size = len(CAS.prompt_of(recipe))
        check(f"{target}: prompt is inside the budget ({size} <= {CAS.PROMPT_BUDGET})",
              size <= CAS.PROMPT_BUDGET, f"{size} > {CAS.PROMPT_BUDGET}")
    findings = [f for f in CAS.check(ROOT) if "budget" in f]
    check("the agent-skills gate reports no over-budget leg", not findings, str(findings))


def test_the_guard_is_wired_into_the_suite():
    """Rule 6d: a test the runner never executes locks nothing."""
    check("wiring: `make test` runs the discovering runner", wired(__file__), "")


def main() -> int:
    print("search legs pin the terminal tool (issue #362)")
    test_the_rule_is_one_definition_and_every_leg_embeds_it()
    test_the_rule_forbids_the_credential_less_tools()
    test_no_leg_prompt_invites_a_credential_less_tool()
    test_the_wording_reaches_the_agent()
    test_the_expanded_prompt_can_never_carry_the_value()
    test_the_skill_and_the_guide_pin_the_same_tool()
    test_the_documents_name_the_variable_that_exists()
    test_the_rule_keeps_every_leg_inside_the_prompt_budget()
    test_the_guard_is_wired_into_the_suite()
    print(f"\nPASSED {_PASS} | FAILED {_FAIL}")
    return 1 if _FAIL else 0


if __name__ == "__main__":
    raise SystemExit(main())
