# hf-link-verification

## ADDED Requirements

### Requirement: The search leg looks the canonical id up before writing it

The preloaded `data-search` skill MUST require the leg to confirm a model's `hf`
(and every `formats[].hf`) as the canonical `owner/repo` with the authenticated
Hugging Face API (`https://huggingface.co/api/models?search=<name>`, reading
`HF_TOKEN` by name) or `hf search models <name>` before it writes the value. A
plausible `owner/model-name` is not a lookup. An id that cannot be confirmed MUST
be left out, so the leg never emits a guess.

WHEN a leg extracts a model that names or links a Hugging Face repo,
THEN it looks the repo id up and writes only an id that answered.

#### Scenario: the skill states the lookup and the refusal

- **Given** `.hermes/skills/data-search/SKILL.md`
- **When** its rules are read
- **Then** it names the authenticated HF API lookup and says an unverified id is left out
- **Test:** `tests/test_ingest_hf_verify.py::test_the_search_skill_requires_the_hf_lookup`

### Requirement: A definitive dead id is refused before the snapshot lands

`write_raw_snapshot(..., verify_hf=True)` MUST check every model `hf` and every
`formats[].hf` with `hf_repo_resolves`. When the answer is definitively dead
(401/404), it MUST NOT write that id: the model row is dropped, or the bad
`formats` entry is dropped, and ONE loud `[write-raw] WARN:` line names the
backend, the model and the refused id so the leg can look it up and re-run.

WHEN a leg's payload carries a repo id that definitively does not resolve,
THEN the raw snapshot is written without that id and the leg says which one it refused.

#### Scenario: a 404 model is dropped and the good model survives

- **Given** a local HF stand-in answering 404 for `gone/model` and 200 for `good/model`
- **When** `write_raw_snapshot("amd", payload, verify_hf=True)` writes both models
- **Then** the bad model is absent, the good model is present, and the warning names `gone/model` and the backend
- **Test:** `tests/test_ingest_hf_verify.py::test_write_raw_refuses_an_unverified_hf`

#### Scenario: only the bad format entry is dropped

- **Given** a model whose `hf` resolves and whose single `formats[].hf` is a 404
- **When** the write runs with `verify_hf=True`
- **Then** the model is kept, the bad format entry is absent, and the warning names the format
- **Test:** `tests/test_ingest_hf_verify.py::test_write_raw_drops_a_bad_format_only`

### Requirement: An indeterminate answer never refuses a real id

When `hf_repo_resolves` cannot tell (a 429, a 5xx, a transport error), the value
MUST be kept. A rate-limited or briefly unavailable API MUST NOT look like a
fabricated id.

WHEN the HF API answers 429 for a repo id,
THEN the model is written unchanged and no refusal is printed.

#### Scenario: a 429 keeps the model

- **Given** a local HF stand-in answering 429 for `busy/model`
- **When** the write runs with `verify_hf=True`
- **Then** the model is present in the snapshot and no refusal names it
- **Test:** `tests/test_ingest_hf_verify.py::test_write_raw_keeps_an_indeterminate_hf`

### Requirement: The check is opt-in for callers and on for the `--write-raw` CLI

`write_raw_snapshot` MUST default `verify_hf` to `False`, so a direct call makes
no network request, and `main()` MUST pass `verify_hf=True` to the `--write-raw`
call, so the production search path enforces it.

WHEN the suite calls the writer directly,
THEN no request is made; WHEN the CLI writes a snapshot, THEN the check runs.

#### Scenario: the default makes no request

- **Given** an HF stand-in and a model whose repo does not resolve
- **When** `write_raw_snapshot` is called without `verify_hf`
- **Then** the stand-in receives no request and the model is written
- **Test:** `tests/test_ingest_hf_verify.py::test_write_raw_default_makes_no_request`

#### Scenario: the production path turns verification on

- **Given** `scripts/update_trending.py`
- **When** its `main()` is read
- **Then** it calls `write_raw_snapshot(args.write_raw, payload, verify_hf=True)`
- **Test:** `tests/test_ingest_hf_verify.py::test_write_raw_cli_turns_on_verification`

### Requirement: A full link is reduced to its repo id before it is verified

`normalize_hf_ref` MUST reduce a pasted Hugging Face link — including `hf.co`,
`www.huggingface.co`, a query string, a trailing slash and a doubled
`https://huggingface.co/` prefix — to `owner/repo` through the ONE definition in
`scripts/hf_id.py`, so a full link is verified as the repo it names rather than
as a malformed id.

WHEN a leg writes `hf` as a full Hugging Face URL,
THEN the snapshot carries `owner/repo` and the API is asked for that id.

#### Scenario: a short-host link becomes the id

- **Given** a model whose `hf` is `https://hf.co/Qwen/Qwen3-14B`
- **When** the snapshot is written
- **Then** the stored `hf` is `Qwen/Qwen3-14B`
- **Test:** `tests/test_ingest_hf_verify.py::test_write_raw_normalises_hf_co_urls`
