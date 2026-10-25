---
name: bot-unattended
description: Use when you are running as an unattended trending-local-llms bot leg — never ask, never wait, decide from the input and write only the file your own skill names.
version: 1.0.0
author: Asimov Agent
license: CC-BY-4.0
metadata:
  hermes:
    tags: [trending-local-llms, bots, unattended, agent-leg]
---

# Unattended bot run

This skill is preloaded **alongside the bot's own skill** (`data-search`, `issue-implement`,
`issue-review`, `pr-fix`). That skill says what this run is; this one says how a run with nobody
watching it must behave.

## Inputs

- The bot's own skill, preloaded in the same session. Read its **Inputs** section for the files
  and the parameters this run was given.
- The checkout this run may write (inside the container it is `/workspace`). Nothing outside it
  exists for you.

## Output

- Exactly the artefacts the bot skill's **Output** section names, in the shape it requires.
- Nothing else: no push, no merge, no comment, no label, no issue. The deterministic step after
  you reads the files and performs the GitHub write; it refuses an output that breaks the shape.

## Rules

- **Never ask a question, never wait for input.** `--yolo` approves shell commands and
  `--accept-hooks` approves hooks; neither answers your own `clarify` tool. In a detached run
  Hermes prints "Input required; detached without cancelling", exits **3**, leaves the tree
  untouched, and the leg reports "produced no implementation" — a wrong diagnosis for a run that
  never ran. Measured on the issue-bot sweep: three of five runs on 2026-10-24/25 died this way.
- **A genuinely open decision is not a question either.** Take the path that changes nothing
  (decline / refine / no-change-needed) or the path that names what you checked (cited evidence),
  and say why in your output. Inventing a decision, or a close with no evidence, fails the
  deterministic step and is worse than doing nothing.
- **A failing tool is reported, never worked around.** If a command you need fails, say what failed
  in your output and stop; never fake the result the output is supposed to carry, and never write a
  raw snapshot with no real scrape behind it.
- **AGENTS.md still governs the repository.** This skill adds the unattended contract; it relaxes
  nothing there. Where the two meet, AGENTS.md wins.
- **Never print a credential, in any spelling.** Read a key from the environment by name at the
  moment you send it, and never echo, log, write or encode it — a value in a log is rotated, not
  excused (AGENTS.md rule 3d).
