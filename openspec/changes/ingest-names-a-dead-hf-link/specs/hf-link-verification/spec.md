# hf-link-verification

## ADDED Requirements

### Requirement: Only a definitive answer is a finding

`hf_repo_resolves(repo_id)` MUST return `True` when the Hugging Face API answers
for the id, `False` ONLY on a definitive 401 or 404, and `None` when the check
cannot tell — an id that is not `owner/repo`, a transport error, or a 403 / 429 /
5xx answer. A rate-limited or briefly unavailable API MUST NOT be reported as a
dead link.

WHEN a repo id is checked,
THEN the verdict distinguishes "does not exist" from "could not ask".

#### Scenario: a 404 and a 401 are definitive, a 429 and a 500 are not

- **Given** a local HF stand-in answering 200, 404, 401, 429 and 500 for five ids
- **When** `hf_repo_resolves` asks for each
- **Then** it returns True, False, False, None, None respectively
- **Test:** `tests/test_ingest_hf_verify.py::test_only_a_definitive_answer_is_a_finding`

#### Scenario: a value that is not a repo id is not checked

- **Given** `None` and `"no-slash"`
- **When** `hf_repo_resolves` is called
- **Then** both return `None`, so an empty or malformed id can never read as a dead link
- **Test:** `tests/test_ingest_hf_verify.py::test_only_a_definitive_answer_is_a_finding`

### Requirement: A merge names a NEW model's dead repo

When a merge adds a NEW model, `note_unresolved_hf` MUST print ONE line naming
the HF field, the repo id and the model id for each repo that is definitively
dead, and MUST print nothing for a repo that resolves. Only NEW models are
checked: updating an existing model MUST cost no request.

WHEN a refresh merge introduces a model whose repo id does not exist,
THEN the run that introduced it names the id instead of leaving it to CI.

#### Scenario: the dead id is named and the good one is silent

- **Given** a raw snapshot adding two new models, one with a 404 repo and one whose repo answers
- **When** the merge runs with `verify_hf=True`
- **Then** the output names the dead id and its model, and does not mention the good one
- **Test:** `tests/test_ingest_hf_verify.py::test_a_dead_repo_is_named_and_a_good_one_is_silent`

#### Scenario: an existing model costs no request

- **Given** a store that already holds the model a snapshot updates
- **When** the merge runs with `verify_hf=True`
- **Then** the HF stand-in receives no request
- **Test:** `tests/test_ingest_hf_verify.py::test_only_new_models_cost_a_request`

### Requirement: The check is opt-in for callers and on for the CLI

`ingest_raw_snapshots` MUST default `verify_hf` to `False`, so a direct call (every
existing ingest test) makes no network request, and `main()` MUST pass
`verify_hf=True`, so the production merge performs the check.

WHEN the suite calls ingest directly,
THEN no request is made; WHEN the CLI merges, THEN the check runs.

#### Scenario: the default makes no request

- **Given** an HF stand-in and a new model with a dead repo
- **When** ingest runs without `verify_hf`
- **Then** the stand-in receives no request, and `HF_MODEL_API` still defaults to the real API
- **Test:** `tests/test_ingest_hf_verify.py::test_the_default_makes_no_request`

#### Scenario: the production path turns it on

- **Given** `scripts/update_trending.py`
- **When** its `main()` is read
- **Then** it calls `ingest_raw_snapshots(store, since=since, verify_hf=True)`
- **Test:** `tests/test_ingest_hf_verify.py::test_main_passes_verify_hf`
