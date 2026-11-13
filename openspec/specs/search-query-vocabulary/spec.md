# search-query-vocabulary Specification

## Purpose
TBD - created by archiving change cpu-leg-query-vocabulary-audit. Update Purpose after archive.

## Requirements

### Requirement: Each search leg's curated keyword vocabulary has exactly ONE home

The curated per-leg keyword vocabulary MUST be defined once — in
`scripts/query_vocab.py` — and every consumer MUST receive it from that home:
the four `_search-<backend>` prompts through the `Makefile`'s
`$(<BACKEND>_KEYWORDS)` indirections (whose resolved values the guard compares
to the dict), `scripts/smoke_search.py`, and the CPU fetch sampling in
`scripts/update_trending.py`. No consumer may keep a private spelling of the
keyword list.

#### Scenario: the Makefile prompts carry the home's value, not a copy

- **Given** the `Makefile`'s `SEARCH_<BACKEND>_QUERIES` indirections
- **When** the guard resolves each `$(<BACKEND>_KEYWORDS)` to its literal list in `scripts/query_vocab.py`
- **Then** every leg's prompt query list equals the home dictionary, and an edited literal in a prompt or a drifted dict goes red
- **Test:** tests/test_cpu_query_vocabulary.py::test_one_home_every_reader_resolves_to_it

#### Scenario: the CPU fetch sampling IS the leg vocabulary

- **Given** the CPU leg's sampled queries in `scripts/update_trending.py`
- **When** the guard compares them to `query_vocab.LEG_KEYWORDS["cpu"]`
- **Then** they are the same list, imported — not a re-spelled copy
- **Test:** tests/test_cpu_query_vocabulary.py::test_one_home_every_reader_resolves_to_it

### Requirement: A search leg whose answered pages state nothing is a red run

A leg whose queries ANSWER (the mirror responds with post content) and whose
pages yield NO candidate — no generation rate in a form posts use, and no model
name the store ranks — MUST fail `make search-smoke` loudly, naming the leg,
the answer/capture asymmetry, and the vocabulary home to fix. The classification
is content, not HTTP status: reachability was exactly the state the starved CPU
leg sat in. The budget-majority rule (#258) and the outage classification
(#291/#296) keep their own verdicts, and each rule's sentence prints only for
the rule that fired.

#### Scenario: an answered-but-silent CPU leg exits 2

- **Given** every CPU query answered within budget with post content that states no rate and names no ranked model (the fixture texts are the archived 2026-11-11 pages)
- **When** the real `smoke_search.main()` runs over the leg
- **Then** it exits 2, labels every query SILENT, and its verdict names the starved vocabulary and `scripts/query_vocab.py`
- **Test:** tests/test_cpu_query_vocabulary.py::test_the_yield_gate_refuses_a_silent_leg

#### Scenario: a yielding leg stays green, labelled with its yield

- **Given** the same queries answered with pages that state rates and name models
- **When** the real `smoke_search.main()` runs
- **Then** it exits 0 and each query line carries its yield counts
- **Test:** tests/test_cpu_query_vocabulary.py::test_the_yield_gate_refuses_a_silent_leg

#### Scenario: an unreachable source is still judged by the budget rule, not double-charged

- **Given** every CPU query missed the budget (all TIMEOUT)
- **When** the real `smoke_search.main()` runs
- **Then** it exits 2 through the MAJORITY rule, and the starved-vocabulary verdict is not applied to unanswered pages
- **Test:** tests/test_cpu_query_vocabulary.py::test_the_yield_gate_refuses_a_silent_leg

### Requirement: The CPU vocabulary is the probe-audited one, and the starved state is recorded as evidence

The CPU leg's queries MUST be the probe-verified co-occurrence queries
(`cpu tokens per second`, `llama.cpp cpu tokens per second`, `raspberry pi
tokens per second`, `no gpu tokens per second`), every query MUST ask for a rate
in the `query-coverage` contract's tokens, and the tree MUST carry the measured
starved run (a whole refresh whose CPU raw snapshots captured zero models while
the other legs captured) plus posts captured verbatim from the live mirror that
the new queries' own regexes DO yield.

#### Scenario: the audited queries are present and contract-shaped

- **Given** `scripts/query_vocab.py`'s CPU vocabulary
- **When** the guard checks the probe-verified queries, the rate-ask tokens, and that only the explicit no-gpu query may name a GPU
- **Then** all hold, and dropping one goes red
- **Test:** tests/test_cpu_query_vocabulary.py::test_the_vocabulary_is_the_audited_one

#### Scenario: the starved refresh lives in the raw store, with its asymmetry

- **Given** `data/raw/*.json`
- **When** the guard groups the snapshots per refresh run
- **Then** a run exists whose every `cpu-*.json` holds zero models while that same run's other legs captured models — proving leg defect, not outage
- **Test:** tests/test_cpu_query_vocabulary.py::test_the_starved_run_is_recorded_in_the_store

#### Scenario: posts captured from the live mirror yield candidates under the new queries

- **Given** CPU-rate posts captured VERBATIM from the mirror (2026-11-13), a silent control page, and the archived starved pages
- **When** the real `page_yields` regexes run over them
- **Then** the real posts yield rate and model candidates (the no-gpu post yields both), and the silent/starved pages yield zero
- **Test:** tests/test_cpu_query_vocabulary.py::test_the_new_queries_would_have_yielded_the_live_posts
