# Proposal: search-skill-names-measurement-alias-key

Issue: #885

## Why

Issue #652 moved the attribution-exception map into DATA — the optional
`measurement_model_aliases` key on a model row — and #884 made the search
contract declare it, but the `data-search` skill the four search legs preload
(rule 6p) still describes only the attribution REFUSAL (issue #651's joint-figure
rule) and never names the key. An agent that hits a refusal-shaped situation
mid-search cannot record the exception it IS allowed to record: the contract half
and the prompt half drifted apart, and rule 6p forbids restating the rule inline
in the four Makefile prompts, so the skill is the only legal home for it.

## What Changes

- `agents/skills/data-search/SKILL.md` names `measurement_model_aliases` once:
  its shape (an optional list of store model ids on the ROW), when it is the
  right answer (variant naming its base model, a multi-figure bake-off naming
  what it compares against), and that it is validated by
  `check_measurement_alias_map` — a refusal is fixed by DOCUMENTING the alias,
  never by loosening the refusal.
- `tests/test_agent_skills.py` locks it: the real data-search skill must name
  the key (a red test if the paragraph is ever removed).

## Impact

- Capability `measurement-ingest`: the search-leg contract now carries the
  exception mapping, not just the refusal.
- No data, no contract, no Makefile change; `make check-agent-skills` stays
  green (the paragraph is data-search's own contract, not the unattended one).

## Not covered

- `bot-unattended` / `issue-review`: verified to state NO attribution rule, so
  the "#885 if the reviewer legs share it" half is empty — no change needed.
- Filling real alias values into `data/models.json`: that is acquisition/data
  work reviewed per row, not this change's job.
