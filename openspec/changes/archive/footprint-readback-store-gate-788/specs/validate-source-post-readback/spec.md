# Spec delta: validate-source-post-readback (footprint-readback-store-gate-788)

## ADDED Requirements

### Requirement: The shipped store's readback residue is pinned at zero

The repository MUST ship a test that runs the real `source_post_figure_flags` scan against the
real `data/models.json` and `data/raw/` and fails, naming each flagged value (model, field,
stored value, source post), when any stored footprint value appears in neither its captured
post's structured fields nor its text. A reconciliation is only Done when a gate keeps it Done.

#### Scenario: a shipped store with no unsupported footprint values passes

- Given the shipped `data/models.json` and `data/raw/` where every stored footprint value is
  stated by the post it cites
- When the shipped-store readback test runs
- Then it passes with the flag count printed
- **Test:** tests/test_source_post_readback.py::test_the_shipped_store_flags_no_unsupported_footprint_values

#### Scenario: a reintroduced drift goes red with attribution

- Given a copy of the REAL shipped store with one measurement's `weight_gb` planted to a value
  no capture of its cited post states (the #531 `5.93GB` vs `5.95GB` class)
- When the same shipped-store scan runs over that copy
- Then the scan returns exactly that flag naming the model, field, value and source post, and
  the gate test fails on it
- **Test:** tests/test_source_post_readback.py::test_the_store_gate_fires_on_a_planted_drift

### Requirement: A footprint value the post does not state is corrected or declared, and the scan confirms precisely

Every value the readback scan flags MUST be resolved one of two ways before this change's merge:
corrected to the figure the cited capture states, or marked with the canonical `(est)` notation
(rule 2) so it is a declared, individually attributable estimate. The confirmation itself stays
precise: the capture's own structured value of the SAME field confirms the store's fuller
distillation of it, confirmation between free text and a stored value runs one-way, a structured
value of a different field confirms nothing, annotation brackets are presentation and never
break confirmation, and the report counts the `(est)` residue instead of hiding it.

#### Scenario: an (est)-marked value is attributable, not a contradiction

- Given a shipped measurement whose `weight_gb` carries `(est)` and whose capture states no such figure
- When the readback scan runs
- Then the value produces no flag and `source_post_declared_estimates` counts it
- And the same value without the marker is still flagged (the marker is the only exemption)
- **Test:** tests/test_source_post_readback.py::test_a_declared_estimate_is_attributable_not_a_contradiction

#### Scenario: the capture's own structured value confirms the store's distillation of the same claim

- Given a stored `engine_min_version` "llama.cpp with MTP=2" and a capture whose structured
  `engine_min_version` is "MTP=2"
- When the readback scan runs
- Then the value is confirmed (no flag)
- And a structured value under a DIFFERENT field confirms nothing, and a stored value longer
  than the capture's free-text phrase is still flagged
- **Test:** tests/test_source_post_readback.py::test_the_captures_own_structured_value_supports_a_fuller_distillation

#### Scenario: annotation brackets do not break confirmation

- Given a stored value `official checkpoints (no extreme quantization)` and a capture phrase
  `official checkpoints, no extreme quantization`
- When the readback scan runs
- Then the value is confirmed (brackets are stripped in the confirmation norm)
- **Test:** tests/test_source_post_readback.py::test_annotation_brackets_do_not_break_confirmation
