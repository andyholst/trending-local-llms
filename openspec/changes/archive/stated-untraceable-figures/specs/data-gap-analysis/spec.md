# data-gap-analysis

## ADDED Requirements

### Requirement: A stated figure no captured post states is its own class

The analysis MUST classify a requirement dimension the model's OWN free text states, and
that NO captured post states, as `untraceable` — never as `unstructured`, whose label is
"a post states it too, an ingest job". The classes (`not_captured`, `unstructured`,
`captured_prose`, `untraceable`) MUST remain a disjoint partition of `missing`, so a model
is counted once and never twice.

WHEN a model's `why`/`quant`/`hardware` states a dimension figure and no captured post's
text states one, THEN the model is reported in `untraceable` for that dimension and in no
other class of the split.

#### Scenario: a store-only figure is untraceable, a captured one stays an ingest job

- **Given** a store where three models state a context window in prose and no structured `context_tokens`, and a capture that states the window for one of them only
- **When** the store is analysed against that capture
- **Then** the two models whose sentence no captured post states are in `untraceable`, the third stays in `unstructured`, and the four classes partition `missing`
- **Test:** `tests/test_data_gap_analysis.py::test_a_stated_figure_no_post_supports_is_its_own_class`

#### Scenario: the shipped store reports the class it was measured on

- **Given** the repository's own store and raw snapshots
- **When** the analysis is run
- **Then** `gemma-4-12b` is the `context_tokens` model in `untraceable`, and it is no longer in `unstructured`
- **Test:** `tests/test_data_gap_analysis.py::test_the_real_store_reports_only_figures_it_can_point_at`

### Requirement: The class is reported as a capture job, and never files an issue

The report and the filed issue body MUST name the class as a CAPTURE job (a search that
brings back the post stating the figure), with its models, and the class MUST NOT add an
entry to the gap signature — a signature entry files an issue, and an issue per untraceable
sentence would re-file the same dimension on every refresh while only a new capture can
retire it.

WHEN the report is rendered, THEN it carries a section naming the class, its dimension and
its models, and the ranked line names the class as its own kind; WHEN the issue body is
composed, THEN it carries the same section; and the signature is unchanged by the class.

#### Scenario: the report and the issue body name the class and its models

- **Given** a report whose `untraceable` class is non-empty
- **When** the report is rendered and the issue body is composed
- **Then** both name the class as a capture job and name a model in it, and the signature carries no entry for the class
- **Test:** `tests/test_data_gap_analysis.py::test_a_stated_figure_no_post_supports_is_its_own_class`

#### Scenario: a store with no stated figure invents no section

- **Given** a store whose models state no requirement figure in prose
- **When** the report is rendered
- **Then** the untraceable section reports `- none`
- **Test:** `tests/test_data_gap_analysis.py::test_a_stated_figure_no_post_supports_is_its_own_class`

### Requirement: CI refuses a stated figure with no post, and reports the history

`make validate`'s `data` stage MUST fail when a model's free text states a requirement
figure while NO measurement on that row cites a real `…/status/<id>` post — nothing on the
row can ever attribute the sentence — and MUST report (never fail) the class where the row
does carry a real post but no captured post states the figure, because that is history the
store cannot repair without breaking additive-only.

WHEN a store carries a stated figure with no real post on the row, THEN validation fails and
names the model and where the figure belongs; WHEN the row has a real post but the sentence
is uncaptured, THEN validation reports it and fails nothing.

#### Scenario: an unattributable figure fails validation

- **Given** a store model whose `why` states a context window and whose only measurements cite a bare mirror URL and a profile page
- **When** `check_untraceable_figures` runs
- **Then** validation fails naming the model, and the message says to put the figure on the measurement whose post states it
- **Test:** `tests/test_data_gap_analysis.py::test_a_stated_figure_no_post_supports_is_its_own_class`

#### Scenario: the uncaptured class is reported, never failed

- **Given** a store model whose `why` states a context window and whose measurement cites a real post
- **When** `check_untraceable_figures` runs
- **Then** no failure is recorded and the scan reports the untraceable class
- **Test:** `tests/test_data_gap_analysis.py::test_a_stated_figure_no_post_supports_is_its_own_class`

### Requirement: The search prompt stops writing a model-level figure no post supports

The `data-search` skill the four refresh legs preload MUST state that a requirement figure
lives on the measurement whose post states it, never only in the model-level `why`/`quant`
prose, and that a figure no post states is not written at all.

WHEN a leg writes a model, THEN every requirement figure it records sits on a measurement
next to the `source_post` that states it.

#### Scenario: the skill carries the attribution rule

- **Given** the `data-search` skill the refresh legs preload
- **When** its rules are read
- **Then** it says a requirement figure lives where its post lives and that an untraceable figure is never written into `why`
- **Test:** `tests/test_data_gap_analysis.py::test_a_stated_figure_no_post_supports_is_its_own_class`
