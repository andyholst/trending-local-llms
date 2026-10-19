#!/usr/bin/env python3
"""Unit tests for the hermes -z prompt shell-string validation.

Ensures no make-recipe hermes -z "..." prompt carries an unescaped quote (which
would close the -z string early, turn the rest of the prompt into stray args,
and make hermes error: '... is not a hermes command' — killing every search).

  - test_makefile_prompts_valid     dry-run against the REAL Makefile
  - test_prompt_permutations        data-driven matrix of broken/correct prompts

Run:  python3 tests/test_hermes_prompts.py   or   make test
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import validate as V  # noqa: E402

_PASS = 0
_FAIL = 0

#: The model flag every `hermes -z` continuation line must carry. The alias has ONE
#: definition — `HERMES_ALIAS`, which the Dockerfile writes into the config and
#: `make _hermes-alias-check` reads back — so a call site that hardcodes the name is
#: a second copy of a fact nothing keeps in step (issue #221).
MODEL_FLAG = r"^\t\t-m\s+\$\(HERMES_ALIAS\)\s+--reasoning\b"


def _defined_alias() -> str:
    """The alias as the Makefile defines it — this suite hardcodes nothing (issue #221)."""
    import re
    m = re.search(r"^HERMES_ALIAS\s*:=\s*(\S+)\s*$", (ROOT / "Makefile").read_text(), re.M)
    return m.group(1) if m else ""


def check(name, cond, detail=""):
    global _PASS, _FAIL
    if cond:
        _PASS += 1
        print(f"  ok  {name}")
    else:
        _FAIL += 1
        print(f"  FAIL {name}" + (f"  [{detail}]" if detail else ""))


def test_makefile_prompts_valid():
    """Dry-run: every `hermes -z "..."` line in the real Makefile (4 search +
    fix-bot) must be a valid shell string (no unescaped quote in the body)."""
    bad = []
    count = 0
    for line in (ROOT / "Makefile").read_text().splitlines():
        if line.lstrip().startswith("hermes -z"):
            count += 1
            ok, why = V._hermes_prompt_ok(line)
            if not ok:
                bad.append(f"{why}: {line.strip()[:50]}")
    check("prompts: Makefile has hermes -z prompts to check", count >= 4, f"count={count}")
    check("prompts: all Makefile hermes -z prompts are valid shell strings", len(bad) == 0, str(bad))


def test_makefile_prompts_cap_reasoning():
    """Every hermes call in the Makefile must pass an explicit --reasoning level.
    Without it the search model can spend its whole max_tokens budget on
    reasoning on every continuation ('No visible answer was produced'), write
    no raw snapshot, and fail the search leg with exit 2 (seen on search-cpu)."""
    import re
    lines = (ROOT / "Makefile").read_text().splitlines()
    calls = [l for l in lines if re.match(MODEL_FLAG, l)]
    check("reasoning: found hermes model-flag lines", len(calls) >= 4, f"count={len(calls)}")
    missing = [l.strip() for l in calls if "--reasoning " not in l]
    check("reasoning: every hermes call sets --reasoning", not missing, str(missing))
    levels = dict(re.findall(r"^(HERMES_(?:FIX_)?REASONING)\s*:=\s*(\S+)", "\n".join(lines), re.M))
    valid = {"none", "minimal", "low", "medium", "high"}
    check("reasoning: search level defined + valid", levels.get("HERMES_REASONING") in valid, str(levels))
    check("reasoning: fix level defined + valid", levels.get("HERMES_FIX_REASONING") in valid, str(levels))


HERMES_TARGETS = ("_search-nvidia", "_search-metal", "_search-cpu", "_search-amd", "_fix")


def _noninteractive_violations(makefile_text: str) -> list[str]:
    """The recipes whose `hermes -z` continuation line does not pass the WHOLE non-interactive set.

    `--yolo` alone is not enough (issue #351): it covers "dangerous command approval prompts" only,
    while `--accept-hooks` is a separate flag — and a `-z` run that needs input DETACHES
    ("Input required; detached without cancelling") instead of proceeding or failing loudly.
    """
    import re
    out: list[str] = []
    # this is the one variable every recipe must use, so a recipe cannot carry half the set
    var = re.search(r"^HERMES_NONINTERACTIVE\s*:=\s*(.+)$", makefile_text, re.M)
    flags = var.group(1) if var else ""
    for line in makefile_text.splitlines():
        if not re.match(MODEL_FLAG, line):
            continue
        if "$(HERMES_NONINTERACTIVE)" not in line:
            out.append(line.strip()[-60:])
    if "$(HERMES_NONINTERACTIVE)" not in makefile_text:
        out.append("HERMES_NONINTERACTIVE is not defined")
    for required in ("--yolo", "--accept-hooks"):
        if required not in flags:
            out.append(f"HERMES_NONINTERACTIVE lacks {required}")
    return out


def test_every_headless_agent_call_passes_the_noninteractive_flag_set():
    """issue #351, measured on run 39079759124: the implementer's headless run stopped on an
    input prompt and DETACHED after 10m21s, returning rc=2 that the pipeline could only report as
    'no implementation'. Every `hermes -z` recipe must pass the whole set."""
    text = (ROOT / "Makefile").read_text()
    bad = _noninteractive_violations(text)
    check("non-interactive: every hermes call passes the whole flag set", not bad, str(bad))
    import re
    calls = [l for l in text.splitlines() if re.match(MODEL_FLAG, l)]
    check("non-interactive: the recipes were really found (guard not vacuous)", len(calls) >= 8,
          f"count={len(calls)}")


def test_a_recipe_with_only_yolo_is_refused():
    """Falsify the rule on the MEASURED shape: a recipe whose line ends `--yolo` only."""
    old = ("HERMES_NONINTERACTIVE := --yolo --accept-hooks\n"
           ".PHONY: x\nx:\n\thermes -z \"do a thing\" \\\n"
           "\t\t-m $(HERMES_ALIAS) --reasoning low --yolo\n")
    check("non-interactive: a recipe carrying only --yolo is refused",
          _noninteractive_violations(old) != [], "")
    check("non-interactive: and carries no --accept-hooks in the variable either",
          any("accept-hooks" in v for v in _noninteractive_violations(
              old.replace("--yolo --accept-hooks", "--yolo"))), "")





def _logical_commands(text: str) -> list[str]:
    """Join make -n output lines continued with a trailing backslash."""
    out, cur = [], ""
    for line in text.splitlines():
        if line.rstrip().endswith("\\"):
            cur += line.rstrip()[:-1] + " "
        else:
            out.append(cur + line)
            cur = ""
    if cur:
        out.append(cur)
    return [c.strip() for c in out if c.strip()]


def test_make_dry_run_single_hermes_command():
    """`make -n <target>` must yield ONE shell command that carries the prompt
    AND `-m $(HERMES_ALIAS) --reasoning`. If the -z line loses its trailing
    backslash, make runs the model flag as its OWN command (the
    leading '-' even becomes make's ignore-errors prefix) and hermes starts
    with NO alias — it auto-routed to Hugging Face via HF_TOKEN and 403'd on
    every fix-bot run. This checks what make actually executes."""
    import re
    import shutil
    import subprocess
    if not shutil.which("make"):
        print("  SKIP make dry-run: make not installed")
        return
    alias = _defined_alias()
    check("alias: the Makefile defines HERMES_ALIAS", bool(alias), alias)
    for t in HERMES_TARGETS:
        p = subprocess.run(["make", "-s", "-n", t], cwd=ROOT, capture_output=True, text=True)
        cmds = _logical_commands(p.stdout)
        # Issue #383: a recipe may BOUND its call with `timeout <seconds>`; the
        # command is still the one hermes command that recipe runs.
        hermes = [c for c in cmds
                  if c.startswith("hermes -z") or re.match(r"^timeout \S+ hermes -z", c)]
        stray = [c for c in cmds if f"-m {alias}" in c and c not in hermes]
        check(f"make -n {t}: exactly one hermes -z command", len(hermes) == 1, f"rc={p.returncode} {len(hermes)}")
        check(f"make -n {t}: that command carries -m {alias} --reasoning",
              bool(hermes) and f"-m {alias} --reasoning " in hermes[0], hermes[0][-80:] if hermes else "")
        check(f"make -n {t}: no detached model-flag command", not stray, [c[:60] for c in stray])

    # Issue #383: `make fix` MUST bound the Hermes call itself, so one hung round is
    # reaped by the loop (the container dies with it) instead of surviving as an
    # orphan until the JOB's `timeout-minutes` kills the whole run.
    p = subprocess.run(["make", "-s", "-n", "_fix"], cwd=ROOT, capture_output=True, text=True)
    bounded = [c for c in _logical_commands(p.stdout) if re.match(r"^timeout \S+ hermes -z", c)]
    check("make -n _fix: the hermes call is bounded by a timeout", len(bounded) == 1,
          f"rc={p.returncode} {[c[:50] for c in _logical_commands(p.stdout)][:2]}")


def test_every_search_leg_asks_for_the_model_dimensions_from_one_definition():
    """Issue #167: the dimension ask was four byte-identical copies buried in the
    legs' prompts, and the latest refresh emitted ZERO of the five values while the
    posts named them (the analysis reports 5/25 models with a free-text RAM figure).
    No value can be stored unless the gathering step actually asks for it."""
    mk = (ROOT / "Makefile").read_text()

    # Given ONE shared definition
    check("make: DIM_ASK is defined exactly once", mk.count("DIM_ASK :=") == 1, mk.count("DIM_ASK :="))
    definition = mk.split("DIM_ASK :=", 1)[1].split("\n", 1)[0]

    # Then  it names every dimension the store and the search contract can hold
    for dim in ("system_ram_min", "weight_gb", "context_tokens", "storage_offload",
                "engine_min_version"):
        check(f"dimension ask: names {dim}", dim in definition, definition[:90])

    # Then  it says WHERE the figure goes and forbids inventing one
    check("dimension ask: a stated figure belongs in its field, not only in prose",
          "belongs in its field" in definition and "NOT only" in definition, definition[-120:])
    check("dimension ask: never guess, derive or invent",
          "never guess" in definition and "invent one" in definition, definition[-120:])
    check("dimension ask: carries no double quote (it lives inside `hermes -z \"…\"`)",
          '"' not in definition, definition[:60])

    # Then  it says WHICH dimensions the MEASUREMENT itself carries (issue #371): a
    #       minimum engine build or a set of required flags is a property of the
    #       engine that produced the figure, so the ask must send it to the
    #       measurement — the contract used to refuse it exactly there.
    check("dimension ask: names engine_min_version ON the measurement",
          "engine_min_version on the measurement" in definition, definition[-200:])
    check("dimension ask: names storage_offload ON the measurement",
          "storage_offload on the measurement" in definition, definition[-200:])

    # Then  every leg references it and keeps no divergent copy of the old sentence
    for leg in ("nvidia", "metal", "cpu", "amd"):
        recipe = mk.split(f"_search-{leg}:", 1)[1].split("\n.PHONY", 1)[0]
        check(f"{leg}: takes the ask from $(DIM_ASK)", "$(DIM_ASK)" in recipe, recipe[-140:])
        check(f"{leg}: carries no second copy of the buried sentence",
              "also record the optional model fields" not in recipe, "")


def test_every_search_leg_asks_for_the_engine_rule_from_one_definition():
    """Issue #378: the legs fabricated an ENGINE out of the MODEL name when a post
    named no engine (`Nvidia/Qwen3.8-Flash-Next-FP4-Local` running NVFP4 became
    engine `NVIDIA FP4-Local`). An engine with no repo can never be registered, so
    the whole refresh PR went red for it. The rule that forbids it was four
    byte-identical inline copies; it is now ONE definition no leg can diverge from.
    """
    mk = (ROOT / "Makefile").read_text()

    # Given ONE shared definition
    check("make: ENGINE_ASK is defined exactly once", mk.count("ENGINE_ASK :=") == 1, mk.count("ENGINE_ASK :="))
    parts = mk.split("ENGINE_ASK :=", 1)
    definition = parts[1].split("\n", 1)[0] if len(parts) > 1 else ""

    # Then  it requires an engine the POST names, and forbids manufacturing one
    for want in ("must be the engine the post ACTUALLY NAMES",
                 "names no engine at all, SKIP that measurement",
                 "a t/s with no engine is not a valid entry",
                 "A model name, a vendor name or a quantization is NEVER an engine",
                 "NVFP4"):
        check(f"engine ask: names the rule ({want[:38]}…)", want in definition, definition[:120])

    # Then  it keeps the rules it already carried (one definition, not a rewrite)
    for want in ("Use engine names exactly as registered in data/models.json",
                 "record the engine exactly as that fork is named",
                 "add engine_repo =",
                 "never invent or guess a URL"):
        check(f"engine ask: keeps the existing rule ({want[:38]}…)", want in definition, definition[:120])
    check("engine ask: carries no double quote (it lives inside `hermes -z \"…\"`)",
          '"' not in definition, definition[:60])

    # Then  every leg takes it from $(ENGINE_ASK) and keeps no divergent copy
    for leg in ("nvidia", "metal", "cpu", "amd"):
        recipe = mk.split(f"_search-{leg}:", 1)[1].split("\n.PHONY", 1)[0]
        check(f"{leg}: takes the engine rule from $(ENGINE_ASK)", "$(ENGINE_ASK)" in recipe, recipe[-160:])
        check(f"{leg}: carries no second copy of the buried engine sentence",
              "Use engine names exactly as registered in data/models.json" not in recipe, "")


def test_prompt_permutations():
    """DATA-DRIVEN: correct prompt bodies pass; every broken form (unescaped
    quote, malformed -z, missing quotes) is rejected."""
    good = [
        'hermes -z "Load AGENTS.md. Search. Write the payload. Never remove a model. Do not merge or push." \\',
        "hermes -z \"Fetch posts. Move context like 'DFlash spec-decode' into quant. Write data/raw/x.json.\" \\",
        "hermes -z \"JSON body {control:\\\"url\\\":\\\"v\\\"}. Rank by likes/comments/reshares. Write to data/raw/x.json.\" \\",
    ]
    bad = [
        # unescaped double-quote inside the -z body (the PR #38 bug)
        "hermes -z \"move context like \"DFlash spec-decode\" into quant. Write data/raw/x.json.\" \\",
        # unescaped quote mid-body
        "hermes -z \"Record engine \"+ model. Write.\" \\",
        # malformed: no closing quote / missing -z
        "hermes -z \"unclosed",
        "hermes fetch posts write data",
        # valid body but NO trailing backslash: make runs `-m <alias> --yolo` as a
        # separate command, so hermes starts without the model alias (the _fix bug)
        'hermes -z "Fix the data so validation passes. Then regenerate README.md."',
    ]
    for s in good:
        ok, _ = V._hermes_prompt_ok(s)
        check(f"prompt-perm: GOOD passes: {s[:38]!r}", ok, s)
    for s in bad:
        ok, why = V._hermes_prompt_ok(s)
        check(f"prompt-perm: BAD rejected: {s[:38]!r}", not ok, why)


def test_the_alias_has_exactly_one_definition():
    """Issue #221: the alias name exists once, and every call site USES it.

    `-m nous-deepseek` appeared as a literal in eight recipes while the config was
    written from `HERMES_ALIAS` — a rename then meant editing every call site, and
    nothing proved the two agreed. The flag is now the variable, and this proves the
    expansion really is the defined alias (a `make -n` dry run), not just that some
    line looks right.
    """
    import re
    import subprocess
    text = (ROOT / "Makefile").read_text()
    defined = re.search(r"^HERMES_ALIAS\s*:=\s*(\S+)\s*$", text, re.M)

    # Given the Makefile
    flag_lines = [l for l in text.splitlines() if l.startswith("\t\t-m ")]

    # Then  every model flag is the one variable, and no alias literal is left in a recipe
    check("alias: defined once", bool(defined), text[:200])
    check("alias: every model flag uses $(HERMES_ALIAS)",
          len(flag_lines) >= 4 and all(re.match(MODEL_FLAG, l) for l in flag_lines),
          str(flag_lines[:3]))
    recipe_lines = [l for l in text.splitlines()
                    if not l.lstrip().startswith("#") and f"-m {defined.group(1)}" in l] if defined else []
    check("alias: no recipe hardcodes the alias name", recipe_lines == [], str(recipe_lines[:3]))

    # And   a dry run expands it to exactly the defined value
    for target in HERMES_TARGETS:
        proc = subprocess.run(["make", "-n", target, "ISSUE=1"], cwd=str(ROOT),
                              capture_output=True, text=True)
        expanded = [l for l in proc.stdout.splitlines() if re.search(r"\s-m\s+(\S+)\s", l)]
        check(f"alias: `make -n {target}` expands the flag to the defined alias",
              bool(expanded) and all(f"-m {defined.group(1)} " in l for l in expanded),
              proc.stdout[:300] or proc.stderr[:300])


def main() -> int:
    print("hermes -z prompt shell-string validation")
    test_makefile_prompts_valid()
    test_makefile_prompts_cap_reasoning()
    test_make_dry_run_single_hermes_command()
    test_every_search_leg_asks_for_the_model_dimensions_from_one_definition()
    test_every_search_leg_asks_for_the_engine_rule_from_one_definition()
    test_every_headless_agent_call_passes_the_noninteractive_flag_set()
    test_the_alias_has_exactly_one_definition()
    test_a_recipe_with_only_yolo_is_refused()
    test_prompt_permutations()
    print(f"\nPASSED {_PASS} | FAILED {_FAIL}")
    return 1 if _FAIL else 0


if __name__ == "__main__":
    raise SystemExit(main())
