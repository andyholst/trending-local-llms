# A detached bot leg must not be able to call `clarify`

**Issue:** #679 — the recurring refresh-leg failure (measured on the amd leg, run
40407812898, and the cpu leg, run 40872677522): a search leg's model occasionally calls the
`clarify` tool, `--yolo --accept-hooks` answer SHELL and HOOK prompts only, so the detached
runner prints "Input required; detached without cancelling" and exits 3 — killing that leg,
which reports as a red `search (<backend>)` job while `aggregate` still succeeds.

## Why

`bot-unattended/SKILL.md` already tells the model "never ask a question, never wait for
input". The measured legs show that is not enough: a model CAN still call `clarify`, and
Hermes then cannot get the answer it needs. The rulebook's defense has three layers —
`--yolo --accept-hooks` (issue #351), `bot-unattended`'s "never ask", and the
`check-agent-skills` gate (rule 6p) forcing every leg to preload that skill — but they
all rely on the MODEL choosing not to ask. The reliable fix is to make asking IMPOSSIBLE:
disable the `clarify` toolset in the provisioning seam every leg's image runs, so an
unattended leg literally does not have the tool.

## What Changes

- **`Makefile` `_setup`** — the provisioning seam (run by the image build and by every
  leg's `make _setup`) gains `hermes tools disable clarify`, and it is STRICT: a Hermes
  version that cannot disable the toolset FAILS the setup (an agent that can still ask is
  the bug under repair) rather than continuing and re-admitting the detach.
- **`tests/test_hermes_prompts.py`** — `test_the_provisioning_seam_disables_clarify` pins
  the seam (the recipe contains `hermes tools disable clarify`, strict via `|| \` + `exit
  1`), so a future edit that removes the disable turns the suite red.
- **`AGENTS.md`** — rule 6p / §8 gains a row naming the guard and the measured failure.
- Events stay unchanged; the agent image simply stops carrying the tool.

## Impact

`Makefile`, `tests/test_hermes_prompts.py`, `AGENTS.md` §8, this change and the
regenerated `OPENSPEC.md`. No data, no schedule, no workflow job shape.

## Not covered

- A leg that still asks AFTER this change (the tool is gone, so the only path left is the
  model emitting `clarify` as free text, which is not a tool call and cannot detach).
- The `-z … --yolo --accept-hooks` flags and `bot-unattended` stay — they guard the other
  prompt classes; removing `clarify` is additive to them.
