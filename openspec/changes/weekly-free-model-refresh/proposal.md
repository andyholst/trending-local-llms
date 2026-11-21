# Proposal: weekly-free-model-refresh

Issue: #1195

## Why

The chain's free tier is a LIVE truth, not a remembered list: the Nous catalogue moved from 413
to 415 models between the 2026-11-19 and 2026-11-21 reads while the `:free` set stayed at 5.
Today the only refresh path is a human editing `agents/model_chain.json` — a new free model (the
next Qwen) never enters the chain until someone re-reads, and a retired one stays named. The
owner directive of 2026-11-21 asks for a weekly seam that re-reads the live free tier and updates
the list, keeping the local strata fallback and `deepseek/deepseek-v4-flash-0731` last.

## What Changes

- `scripts/free_model_refresh.py`: reads `GET <chain.base_url>/models` with the credential by
  NAME, keeps every `:free` id with its real `context_length`, updates ONLY the free steps
  (survivors keep order/aliases, new ids append as fallbacks with deterministic aliases, retired
  ids drop, a retired primary hands over, contexts follow the read), NEVER touches the
  `local_fallback` tier or the paid `last_resort`, records the read in `measured` + an additive
  `refresh_history`, and writes nothing when the set is unchanged. Exit 2 on an absent credential
  or failed read; exit 1 when the live set carries no free model at all.
- Makefile: `free-model-refresh` + `free-model-refresh-pr-body` (internal `_` recipes + public
  wrappers, the repo pattern).
- `refresh-bot.yml`: a new deterministic `free-model-refresh` job (`needs: guard`) on the
  pipeline's existing Wednesday cron — rule 6t leaves refresh-bot as the ONLY scheduled
  pipeline, so the weekly refresh rides it rather than adding a second cron. The job renders the
  lanes and lands any change through the shared `make keeper-pr` seam (owner PAT, reviewed PR,
  #960 mergeable-only dedupe, no closing keyword). No model anywhere in the job.
- `tests/test_free_model_refresh.py`: the real script against a real local HTTP server (rule 6m),
  every behaviour + refusal + the wiring; ARCHITECTURE.md rows + regenerated §10; AGENTS.md §8
  row (rule 3c attended sign-off, comment on #1195).

## Impact

- Capability: `fleet-model-chain` (the chain's free tier gains a measured weekly refresh).
- Additive (rule 3b): the chain's non-free steps, every existing refusal and every rendered key
  are untouched; `refresh_history` only appends.
- No new workflow file, no new cron slot, no image: the job rides the one scheduled pipeline.
- The refresh never pushes master and never merges: a keeper PR through the normal gates.

## Not covered

- Re-provisioning the HOST homes after a refresh merges stays an attended act
  (`make agent-profile-provision`); the gap is filed as a finding, not silently wired here.
- The local tier's endpoint health (the strata chat hang, #1194) and the durable host credential
  (#1196) are their own issues.
- A standalone cron pipeline for the refresh is REFUSED by rule 6t (owner directive 2026-11-15);
  changing that rule is a rulebook amendment, not this change.
