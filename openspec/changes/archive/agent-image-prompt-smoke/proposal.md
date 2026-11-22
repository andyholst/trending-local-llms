# Proposal: agent-image-prompt-smoke

Issue: #1214
PR: #1229

## Why

The fleet's chain, lane SOULs and skills change in the repo, but no pipeline proved that
the agent image the bots run in is available AND that the profile homes they run carry the
prompts. A build could be green while the hash-tagged image was never published, or while a
provisioned lane lacked its SOUL/skill prompt files — the "reachable with prompts" half of a
real turn. Measured on this host: all 5 fleet homes have their prompts (0 findings), while
`ghcr.io/andyholst/trending-local-llms:dockerfile-a106db319f32` answers `manifest unknown`
(only `latest` is published).

## What Changes

- `scripts/agent_image_smoke.py`: read-only check of the ONE image ref seam
  (`ensure_image.py ref`) — manifest published or locally built by `image-ensure` — plus a
  prompt-tree check of every provisioned `tll-*` lane (config.yaml, SOUL.md, each skill's
  SKILL.md). No model call (owner directive #1029).
- Makefile `agent-image-smoke` (CI fallback-safe) and `agent-image-published-check` (strict
  owner check, requires published manifest).
- `qa-validate.yml` live-smoke step using `$RUNNER_TEMP/hermes-profiles` after provision.
- `tests/test_agent_image_smoke.py`: 14 checks incl. planted missing SOUL/skill and ref fakes.

## Impact

Specs: agent-image-smoke (new). Code: script, Makefile, workflow, tests. No data changes.

## Verification

14/14 tests; `--skip-image` on the real host profile home: 0 findings; validate QA PASSED;
lint_syntax and linefeeds green.
