## Tasks — #1089: record the human-owned index ruling in rule 6s

### Rulebook

- [x] AGENTS.md §6s carries the explicit ruling: the report-only partition for a human-owned branch is an owner decision (#1089), the branch is never rewritten, and the event-driven index keeper (§6q) is the declared repair
- [x] The ruling sentence names issue #1089 so the decision traces to its thread

### Guard

- [x] `tests/test_agents_rows.py::test_the_human_owned_index_ruling_is_recorded` reads `rule_section("6s")` and asserts the ruling phrase, the never-rewritten statement and the keeper repair
- [x] The assertion is on the exact phrase, so deleting the ruling is RED

### Verification

- [x] `make test` green (the new row test plus `tests/test_auto_merge_rebase.py`)
- [x] `make validate` green
- [x] `make lint` green
- [x] `make openspec-index` then `make openspec-check` green
- [x] `make architecture-check` green

### Scope boundary

- No change to `scripts/auto_merge_rebase.py` — the behaviour IS the ruling.
- No change to the §6q keeper.
