# measurement-ingest

## ADDED Requirements

### Requirement: The data-search skill names the attribution-exception key

The `data-search` skill every search leg preloads (rule 6p) MUST state the
attribution refusal AND its data-shaped exception: the optional
`measurement_model_aliases` key on a model row — a list of store model ids whose
names that row's measurements may legitimately mention — validated by
`make validate`'s `check_measurement_alias_map`. A search agent that meets an
attribution refusal is told, in the same skill it reads the refusal from, how to
DOCUMENT a legitimate exception instead of inventing an attribution or loosening
the rule.

#### Scenario: a search agent reads the exception in the same skill as the refusal

- **Given** the preloaded `agents/skills/data-search/SKILL.md` is the only
  contract a search leg reads
- **When** the leg's measurement text legitimately names another model (a variant
  row naming its base model, a multi-figure bake-off naming what it compares)
- **Then** the skill names `measurement_model_aliases`, its row-level shape, and
  its validator
- **Test:** tests/test_agent_skills.py::test_data_search_skill_names_the_measurement_alias_key

#### Scenario: removing the exception paragraph turns the suite red

- **Given** the shipped data-search skill carries the exception paragraph
- **When** the paragraph naming `measurement_model_aliases` is deleted
- **Then** `make test` fails on the pinned test that names the key
- **Test:** tests/test_agent_skills.py::test_data_search_skill_names_the_measurement_alias_key
