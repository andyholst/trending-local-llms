# fleet-model-chain

## ADDED Requirements

### Requirement: The chain's local-tier id reaches the host's auxiliary blocks

When the chain carries a `local_fallback` tier (issue #1192), the host sync MUST propagate that
tier's bare model id into every named Hermes home's `custom_providers:` entry whose `name` equals
the tier's provider (its `model:` field and its `models:` map key + `context_length`, the tier's
measured window) and into every `moa:` preset entry (aggregator and reference models) whose
`provider:`/`base_url:` names the tier — `default` naming the Hermes home's own config.yaml beside
the profiles root, `--all-profiles` covering every profile dir AND default. The sync MUST touch
ONLY those two top-level blocks, keep every other block and the leading prose byte-for-byte
(verified after the write, with a legal-changed-line guard and one-pass convergence), keep the
prior file as `config.yaml.bak-<UTC>` (rule 3b), be idempotent (a clean home is never written),
compute ALL homes before the first write (one refusal writes nothing anywhere), and require NO
credential — it writes only credential-less local-tier references and never a remote step.
`--check` MUST exit 1 on drift and 0 clean, writing nothing; `--dry-run` previews and exits 0.
The sync MUST REFUSE (exit 2, writing nothing) when the chain names no local tier, when a stale
moa id is ALSO named by a non-local entry (ambiguous), when the strata `models:` map carries more
than one distinct stale key, when a named home has no config, or when nothing was named.

#### Scenario: stale auxiliary blocks take the chain's local id and every other byte survives

- **Given** a home whose `custom_providers[strata]` and `moa:` presets name a retired local id,
  with a non-local provider entry, hand-written leading prose and other top-level blocks
- **When** the sync runs
- **Then** the strata entry's model + models-map key/context and every local moa entry name the
  chain's local id, the retired id is gone, every other block and the leading prose are
  byte-identical, the env-substitution NAMEs are untouched, and the prior file is kept as a backup
- **Test:** tests/test_agent_aux_local_sync.py::test_the_stale_auxiliary_blocks_take_the_chain_local_id_and_every_other_byte_survives

#### Scenario: a chain without the local tier is refused in words

- **Given** a chain with no `local_fallback` entry (master's shape until issue #1192 / PR #1197 lands)
- **When** the sync runs
- **Then** it exits 2 naming the missing tier and writes nothing
- **Test:** tests/test_agent_aux_local_sync.py::test_a_chain_without_the_local_tier_is_refused_and_writes_nothing

#### Scenario: ambiguous or multi-key drift is refused, never guessed

- **Given** a stale moa id also named by a non-local entry, or a models map with two distinct
  stale keys, in any home of a named set
- **When** the sync runs
- **Then** it exits 2 and NO home is written — the clean-syncable siblings keep their bytes too
- **Test:** tests/test_agent_aux_local_sync.py::test_an_ambiguous_stale_id_shared_with_a_non_local_moa_entry_is_refused

#### Scenario: check gates the drift without writing and the sync is idempotent

- **Given** a stale home
- **When** `--check` runs, then the sync, then `--check` again, then the sync again
- **Then** the first check exits 1 naming the drift and writes nothing, the sync exits 0, the
  second check exits 0, and the second sync writes no byte and keeps no second backup
- **Test:** tests/test_agent_aux_local_sync.py::test_check_reports_drift_without_writing_and_reads_clean_after_the_sync
