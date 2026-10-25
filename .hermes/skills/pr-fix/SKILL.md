---
name: pr-fix
description: Use when the fix loop hands you a red trending-local-llms PR — read qa-report.txt and repair the exact failing checks, never the report, never a test's strength.
version: 1.0.0
author: Asimov Agent
license: CC-BY-4.0
metadata:
  hermes:
    tags: [trending-local-llms, bots, fix-bot, ci]
---

# Repair a red PR

The fix loop runs the deterministic checks, writes `qa-report.txt` with the failing check's own
output plus the list that passed, and hands it to you. Repair what it names.

## Inputs

- **`qa-report.txt`** at the repo root — the EXACT failures (output of `make validate`,
  `validate-search`, `validate-mapped` and `test`). Read it FIRST; never guess.
- **`AGENTS.md`** — the acceptance criteria.
- The checkout: the PR's own branch, already checked out.

## Output

- **The fix, edited in place** on the branch. The loop re-runs the checks and pushes only when
  they are green; a red round is reported on the PR, not pushed.
- Nothing else — no push, no merge, no comment, no PR edit.

## Rules

- **Fix the cause, not the report.** Never edit `qa-report.txt`, never delete or weaken a test to
  get green, never widen a whitelist to capture a value (write the value instead), never invent a
  key or a link to pass validation.
- **Validation's own requirements** (AGENTS.md §4): no model removed; every model carries
  name/full_name/HF link/license/params/VRAM plus an engine measurement with engine, t/s and repo
  link; backend tables sorted by t/s; README regenerated together with the store; raw snapshots
  conform to `data/search_contract.json`.
- **Contract evolution:** a REAL, recurring new key is declared in the contract AND in its tests
  in the same change (rule 6b); a stray/empty one-off key is pruned by `self_correct_raw` instead.
  An additive change edits the file in place; a breaking change gets a new `*.vN.json` contract.
- **Link repair:** find the canonical URL, prove it resolves (HF API/CLI for model repos,
  Firecrawl for engine repos), then write it. Never invent a URL — leave it and report it instead.
- **Engine registry:** only real inference engines. A harness, agent framework, plugin, chat UI or
  benchmark is never registered; leave that failure for a human and say so.
- **Do not remove an existing model. Do not push or merge.** The loop does the push.

## The OpenSpec gate's own failures (measured: they killed the repair loop)

A red implementer PR is very often a red **OpenSpec** gate, not a data problem, and the check's own
line names what to do. Never turn it into a question — that detaches the run (rc=3) and the loop
burns all its rounds:

- **`unchecked task checkbox(es) at lines [n, …]`** — open the change's `tasks.md`. A box may be
  ticked ONLY when its step is genuinely done and verified; if a step was not done, do it now. If it
  cannot be done (a write-protected file, a step that needs a human), say so in the PR body and leave
  the box unticked — never tick a box to make a gate green.
- **the index is stale / `OPENSPEC.md` is not current** — run `make openspec-index` and keep the
  regenerated file; never hand-edit it.
- **a change does not validate** — read `openspec validate`'s own message (a Scenario with no
  `- **Test:**` line, a Requirement that states no behaviour) and fix the spec, not the check.
- **`openspec-archive-check`** — an ACTIVE change names a MERGED PR: `make openspec-archive
  NAME=<change>` then `make openspec-index`, never by editing the marker.

The same rule holds for every other gate: the failure's own output is the instruction. A check that
names nothing you can act on is reported in the PR body, never turned into a question.
