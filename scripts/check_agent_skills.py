#!/usr/bin/env python3
"""Guard the bots' Hermes project skills (issue #549).

Every agent leg used to carry its whole contract as one inline string in the `Makefile`: the same
rules restated per leg, and nothing that told the model it was running with nobody watching it. That
is the measured shape of the issue-bot's failures — on 2026-10-24/25 three of five sweep runs died
with `Input required; detached without cancelling` (rc=3), because `--yolo --accept-hooks` answers
shell and hook prompts but NOT the agent's own `clarify` tool.

The contract now lives in a Hermes **project skill** — `.hermes/skills/<name>/SKILL.md`, the layout
Hermes discovers from a registered directory — preloaded by the leg with `hermes -s <name>`, and the
leg's inline prompt is a pointer plus that run's parameters.

This gate keeps that true, because nothing else can:

* a leg that preloads nothing is back to an inline rulebook;
* a leg naming a skill that does not exist runs with NO contract at all and reports success;
* a skill whose frontmatter `name` disagrees with its directory is not resolvable by `-s`;
* a skill whose `Inputs`/`Output`/`Rules` section went missing is a contract with a hole in it;
* the unattended contract inlined in a recipe is the duplication this change removed;
* a rule moved out of the recipes never arriving in the skill it moved to, or restated inline in a
  recipe — the search legs' 1.7-2.3 KB prompts and the three ~4.7 KB rule variables (issue #638);
* an `AGENTS.md` that no longer states the rule lets the seam be deleted silently;
* a `_setup` that no longer registers the directory leaves every leg preloading nothing.

Scan scope: the `Makefile`'s `hermes -z` recipes — the bot legs. `scripts/hermes_smoke.sh` also
calls `hermes -z`, but it is a routing PROBE with no contract to carry (it asserts the alias
answers), so it is named here as the one exemption rather than silently skipped.

Usage:
    python3 scripts/check_agent_skills.py check    # exit 1 on any finding, 2 when the tree is unreadable
    python3 scripts/check_agent_skills.py report   # print what the gate reads, always exit 0
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SKILLS_DIR = Path(".hermes") / "skills"
SKILL_FILE = "SKILL.md"
#: The shared unattended contract, preloaded beside each bot's own skill.
UNATTENDED_SKILL = "bot-unattended"
#: Every bot skill states what it is given, what it may write, and what it must not do.
REQUIRED_SECTIONS = ("## Inputs", "## Output", "## Rules")
#: Text that belongs in `bot-unattended/SKILL.md` and nowhere near a make recipe.
INLINE_UNATTENDED = "NEVER ask a question"
#: The rule AGENTS.md must keep, so the seam cannot be deleted silently. The gate's `check`
#: asserts the seam's own documented block in the Makefile (always enforceable); `report` prints
#: whether AGENTS.md states the rule too — §2 rule 6p — which issue #638 landed.
AGENTS_MARKER = "**Every agent leg runs from a project skill"
#: The seam's documentation, in the file the seam lives in — enforced, unlike the AGENTS.md prose.
MAKEFILE_MARKER = "## Every agent leg runs from a project SKILL"
#: `hermes -z` callers with no bot contract to carry (documented, not skipped by accident).
PROBES = {Path("scripts") / "hermes_smoke.sh"}
#: A leg's inline prompt is a pointer plus that run's parameters. 900 characters covers the
#: longest pointer (a search leg, whose keyword list IS a parameter) and nothing more: the rules a
#: leg obeys used to occupy 1.7-2.3 KB per search recipe and three ~4.7 KB variables, and a budget
#: of 3200 let that whole rulebook sit "inside budget" (issue #638).
PROMPT_BUDGET = 900
#: A rule retired from the recipes into a skill (issue #638). Each MUST appear in its skill and MUST
#: NOT appear in any recipe: the duplication is what this gate exists to prevent, and a rule that
#: left the recipe and never arrived in the skill is a contract with a hole in it.
RETIRED_RULES = {
    "engine_repo": "data-search",
    "system_ram_min": "data-search",
    "execute_code": "data-search",
    "/status/<id>": "data-search",
    "reshares and views": "data-search",
}

_TARGET = re.compile(r"^([A-Za-z0-9_.-]+):")
_SKILL_FLAG = re.compile(r"(?:^|\s)(?:-s|--skills)[\s=]+(\S+)")


def legs(makefile: str) -> dict[str, str]:
    """Every `hermes -z` recipe in the Makefile, as {target: joined recipe text}."""
    out: dict[str, str] = {}
    target = ""
    body: list[str] = []

    def flush() -> None:
        if target and body and any("hermes -z" in line for line in body):
            out[target] = "\n".join(body)
        body.clear()

    for line in makefile.splitlines():
        m = _TARGET.match(line)
        if m and not line.startswith("\t"):
            flush()
            target = m.group(1)
            continue
        if line.startswith("\t"):
            body.append(line)
        elif line.strip() == "":
            continue
        else:
            flush()
            target = ""
    flush()
    return out


def preloaded(text: str) -> list[str]:
    """The skill names a leg preloads with `-s`, split on commas, in order."""
    names: list[str] = []
    for m in _SKILL_FLAG.finditer(text):
        for part in m.group(1).split(","):
            part = part.strip().strip("'\"")
            if part:
                names.append(part)
    return names


def prompt_of(text: str) -> str:
    """The `-z "…"` payload of a leg, best effort, for the size and duplication checks."""
    m = re.search(r'hermes -z "(.*?)"\s*\\?\s*$', text, re.S | re.M)
    return m.group(1) if m else text


def skill_meta(path: Path) -> tuple[dict[str, str], str]:
    """Frontmatter fields and the body of a SKILL.md."""
    text = path.read_text(encoding="utf-8")
    fields: dict[str, str] = {}
    body = text
    if text.startswith("---"):
        parts = text.split("---", 2)
        if len(parts) >= 3:
            body = parts[2]
            for line in parts[1].splitlines():
                if ":" in line and not line.startswith((" ", "\t", "#")):
                    k, v = line.split(":", 1)
                    fields[k.strip()] = v.strip().strip('"').strip("'")
    return fields, body


def check(root: Path = REPO_ROOT) -> list[str]:
    """Every finding, in a stable order. An empty list is a green gate."""
    findings: list[str] = []
    makefile_path = root / "Makefile"
    if not makefile_path.is_file():
        return [f"{makefile_path} is missing — the gate cannot read the legs"]
    text = makefile_path.read_text(encoding="utf-8")
    found = legs(text)
    if not found:
        return ["no `hermes -z` recipe found in the Makefile — the gate would be vacuous"]

    skills = root / SKILLS_DIR
    if not skills.is_dir():
        findings.append(f"{SKILLS_DIR} is missing — no leg can preload a contract")

    for target, recipe in sorted(found.items()):
        names = preloaded(recipe)
        if not names:
            findings.append(f"{target}: preloads no skill (add `-s <skill>,{UNATTENDED_SKILL}`) — "
                            f"its rules are inline, which is what this gate replaced")
            continue
        if UNATTENDED_SKILL not in names:
            findings.append(f"{target}: does not preload `{UNATTENDED_SKILL}` — a detached run "
                            f"that asks a question exits 3 with nothing done")
        for name in names:
            path = skills / name / SKILL_FILE
            if not path.is_file():
                findings.append(f"{target}: preloads `{name}`, but {path.relative_to(root)} does "
                                f"not exist — the leg would run with no contract at all")
                continue
            fields, body = skill_meta(path)
            if fields.get("name") != name:
                findings.append(f"{path.relative_to(root)}: frontmatter name is "
                                f"'{fields.get('name', '')}', directory is '{name}' — `-s {name}` "
                                f"would not resolve it")
            for section in REQUIRED_SECTIONS:
                if section not in body:
                    findings.append(f"{path.relative_to(root)}: missing section `{section}`")
        if INLINE_UNATTENDED.lower() in recipe.lower():
            findings.append(f"{target}: inlines the unattended contract — it belongs in "
                            f"{SKILLS_DIR / UNATTENDED_SKILL / SKILL_FILE}")
        size = len(prompt_of(recipe))
        if size > PROMPT_BUDGET:
            findings.append(f"{target}: prompt is {size} characters (budget {PROMPT_BUDGET}) — the "
                            f"rules crept back into the recipe")

    for needle, skill_name in sorted(RETIRED_RULES.items()):
        path = skills / skill_name / SKILL_FILE
        body = path.read_text(encoding="utf-8") if path.is_file() else ""
        if needle not in body:
            findings.append(f"{path.relative_to(root)} no longer states '{needle}' — the rule left "
                            f"the recipes and never arrived in the skill it was moved to")
        offenders = sorted(t for t, recipe in found.items() if needle in recipe)
        if offenders:
            findings.append(f"{', '.join(offenders)} restate '{needle}' inline — it belongs in "
                            f"{SKILLS_DIR / skill_name / SKILL_FILE}, not in a recipe")

    agents = root / "AGENTS.md"
    if MAKEFILE_MARKER not in text:
        findings.append(f"the Makefile no longer documents the seam (marker: {MAKEFILE_MARKER}) — "
                        f"the rule could be deleted silently")
    if not agents.is_file():
        findings.append("AGENTS.md is missing")

    if "_hermes-skills-register" not in text:
        findings.append("the Makefile has no `_hermes-skills-register` target — nothing registers "
                        f"{SKILLS_DIR}, so `hermes -s` resolves nothing in the container")

    for probe in sorted(PROBES):
        if not (root / probe).is_file():
            findings.append(f"{probe} is named as a contract-free probe but does not exist — "
                            f"the exemption is stale")
    return findings


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description="Guard the bots' Hermes project skills (every leg preloads its contract)")
    ap.add_argument("mode", choices=("check", "report"), nargs="?", default="check")
    args = ap.parse_args(argv)
    root = REPO_ROOT
    if not (root / "Makefile").is_file():
        print(f"[agent-skills] cannot read {root}/Makefile", file=sys.stderr)
        return 2
    if args.mode == "report":
        for target, recipe in sorted(legs((root / "Makefile").read_text(encoding="utf-8")).items()):
            names = preloaded(recipe)
            print(f"{target:24s} prompt={len(prompt_of(recipe)):5d} skills={','.join(names) or '-'}")
        for path in sorted((root / SKILLS_DIR).glob(f"*/{SKILL_FILE}")):
            fields, _ = skill_meta(path)
            print(f"skill {path.parent.name:24s} name={fields.get('name', '-')}")
        agents = root / "AGENTS.md"
        stated = agents.is_file() and AGENTS_MARKER in agents.read_text(encoding="utf-8")
        print(f"AGENTS.md rule 6p (issues #549/#638): {'stated' if stated else 'OWED'}")
        return 0
    findings = check(root)
    for f in findings:
        print(f"FAIL: {f}")
    if findings:
        print(f"\n[agent-skills] {len(findings)} finding(s). A bot leg's contract is a project "
              f"skill preloaded with `hermes -s`; see AGENTS.md rule 6p.")
        return 1
    print("[agent-skills] ok: every leg preloads an existing skill and the unattended contract")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
