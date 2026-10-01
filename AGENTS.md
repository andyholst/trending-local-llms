# AGENTS.md — Operating behavior for agents in this repo

This file defines how any agent (a coding agent, a Hermes refresh session, or
an AI maintainer) behaves when working in **trending-local-llms**. Read it
before doing anything. If a contributor reverts a change and points here, that
change violated one of these rules.

## 1. What this repo is

A living index of **open-weight LLMs** that people actually run locally,
ranked by **real X engagement** and **measured t/s per inference engine**. Every
figure is community-reported on X (actual posts, not vendor claims), with the
hardware, quant and engine it was measured on. Data spans a rolling window but
retains 30 days of history.

## 2. Hard rules (non-negotiable)

1. **Never push to `master`/`main` directly — by manual action or automation.**
   Every change lands on a **feature branch** and is merged via a **PR reviewed
   by a human**. The CI pipeline may *open* PRs but must never *merge* them.
2. **Never fabricate data.** No engagement number, like count, or t/s figure
   may be invented. It must trace to a **real X post** (via the lightbrd.com
   mirror technique in `skills/gather-data.md`) or be marked explicitly as
   `(est)` / `estimated` when it is a reasonable projection from quant size.
3. **Never wipe history.** If a model stops trending or gets no new updates,
   it stays in the data store and the README — it just sorts **further down**.
   Only remove a model with an explicit human decision (e.g. confirmed dead
   repo / wrong model).
4. **Engagement-first, t/s second.** In the "most loved" rank: models are
   ranked by 7-day X engagement (likes/comments/views/interactions), with
   highest t/s as the tie-breaker **within** a rank. Do not reorder the whole
   table purely by t/s.
5. **t/s is always per engine.** A bare "40 tok/s" with no engine is not a
   valid entry. Format: `t/s (engine, hardware/quant)`.
5b. **Every entry carries its links.** Each model row must include its Hugging
   Face link, and every engine measurement must link to the engine's repo
   (or the specific model/draft repo that produced the figure when that is
   more precise, e.g. a DFlash2 draft). No bare engine name without a link
   in the generated tables or the engine guide.
6. **Backends are equal categories, not primary/secondary.** NVIDIA (CUDA),
   Apple (Metal), and CPU each render as a **first-class table**. A model
   measured on multiple backends appears under each with its own engine + t/s.
   The headline scope is GPU models serving **8–48 GB VRAM** (consumer/
   workstation); CPU and Metal tables exist alongside, not demoted below it.
   Do not pull in datacenter-only multi-TB models as top-line entries.
6b. **Change the data/format/contract → update the tests, in the same change.**
   Any edit to a contract (`model_contract.json`, `search_contract.json`), a
   data format (models.json model shape, raw search-snapshot shape), the README
   template, or a validator rule MUST update the corresponding tests in the
   same commit so `make test` still passes. The contract shape lives in per-file
   helpers — `good_store()`/`store()`/`sample_store()`/`cuda_table()` — so a
   format change is a one-place edit that ripples to all assertions. When a
   requirement changes, update the fixture helper(s) plus any test that asserts
   on the changed field; never leave a test suite that only matches the old
   contract. CI runs `make test` on every pipeline, so a contract change without
   a test update goes red and must not be merged.

## 3. Data source & collection

- X content comes from the **lightbrd.com mirror** (`lightbrd.com/search?f=tweets&q=...`),
  NOT x.com directly (bot-walled) or Nitter (mostly dead). See
  `skills/gather-data.md` for exact queries and the extraction method.
- For each post, record: author, timestamp, text, **likes / comments / views /
  interactions**, and any measured t/s figure with its hardware + quant.
- When the mirror is unreachable, **preserve last-known data** — never blank
  the store or README. The pipeline must fail gracefully.

## 4. Data store & regeneration model

The README is **generated**, not hand-maintained:

- `data/models.json` — canonical store. One row per model with: id, name, full
  name, HF link, license, params, type (LLM / GGUF / other), VRAM tier,
  backend(s), **supported_engines** (list of engines the model is supported by),
  and a list of **per-engine t/s measurements**, each with date, engine,
  hardware, quant, and the engagement + source post URL of the newest post
  supporting it. **No duplicate models** (by id or name). The exact JSON schema
  is documented in `data/MODEL_CONTRACT.md` — read it before adding/editing a
  model.
- `scripts/update_trending.py` — fetches new X data, merges it into the store,
  applies 7-day trending sort + 30-day retention, then regenerates `README.md`.
- **`Makefile` is the single source of truth for every stage** — CI and local
  runs use the exact same targets, and **every public `make X` runs inside the
  Docker container** (Python deps + Hermes CLI baked in; the repo is
  bind-mounted at `/workspace`, so all data writes back to the host). Internal
  `_`-prefixed recipes hold the host commands; the public names are docker
  wrappers. Targets: `make docker-build` (build the image once),
  `make setup`, `make search-nvidia|search-metal|search-cpu`
  (the three separate searches, each writing its own
  `data/raw/<backend>-<UTC>.json`), `make search` (all three), `make merge`
  (ingest raw → models.json + README + snapshot), `make validate` (QA),
  `make validate-search|validate-mapped|validate-readme` (stages), `make test`
  (unit tests), `make fix` (correct a red CI with Hermes), and `make refresh`
  (the full pipeline = setup + search + merge + validate + test, in one
  container). Run after `make docker-build` with
  `NOUS_API_KEY=... FIRECRAWL_API_KEY=... make refresh`.
- **Base image is built ONCE and pulled, never rebuilt per-run.** The base
  image (`ghcr.io/andyholst/trending-local-llms:latest` — Python deps + Hermes
  CLI baked in) is **built and pushed to GHCR only by `refresh-bot.yml`**, and
  only when it does not exist yet or it is **Sunday** (weekly Hermes update).
  Every other pipeline that uses the base image — `qa-validate.yml` (PR CI) and
  `fix-bot.yml` — **pulls** it from GHCR and **only builds the TEST image**
  (`Dockerfile.test`, base + current `requirements-test.txt`) on each run. They
  must never rebuild the base image locally. The GHCR image is public, so no
  login is needed to pull it.
- **Snapshots:** every refresh writes a timestamped snapshot to
  `data/snapshots/trending-<UTC>.json` (full store). This is the history that
  proves no model was ever removed and lets the README be rebuilt from any
  point.
- **QA/validation:** `scripts/validate.py` runs in CI (`.github/workflows/
  qa-validate.yml`) on PRs and pushes. It enforces: (1) no model removed vs the
  previous snapshot, (2) every model has name/full_name/HF link/license/params/
  VRAM + at least one engine measurement with engine name + t/s + repo link,
  (3) each README backend table is sorted by highest t/s descending, (4) every
  model in the store appears in the README, (5) every README **markdown table is
  well-formed** (parsed with `markdown-it-py`: separator column count == header,
  every data row == header, no empty cells), (6) **every link resolves** — from
  `data/models.json` (engine registry, model HF, per-format HF, source_post),
  `data/raw/*.json` search snapshots, and `README.md`, HEAD/GET-checked; a
  404/410 or connection error fails CI (403/429/5xx are indeterminate), and a
  known-good engine repo URL that was wrong is auto-corrected in the store.
  `check_readme_tables_wellformed` + `check_links_resolve` are registered in the
  `make validate` stages so a malformed table or a dead/wrong link in any new
  raw snapshot, the store, or the README fails CI. This is a **validation**
  action, not a data-gathering bot.
- **Never hand-edit the generated tables.** Fix the template or the data store
  instead, then regenerate. The "How to contribute" section points contributors
  at the store, not direct table edits.

## 5. Sort rules

1. **Trending (last 7 days, has new engagement):** on top, ranked by engagement.
2. **Recent (last 30 days, no new engagement):** retained, grouped below.
3. **Stale (>30 days, no new updates):** retained, sorted furthest down — old
   t/s and supported engines still shown, clearly marked with the measurement
   date so a reader knows it is not current.

## 6. Refresh workflow — GitHub Actions invoking the Hermes CLI

The refresh is driven by the **GitHub Actions pipelines** (`refresh-bot.yml`,
`fix-bot.yml`), which invoke the **Hermes CLI** (deepseek-v4-flash-0731 via the
Nous portal, using the repo's `NOUS_PORTAL_API_TOKEN` secret). The agent loads
this `AGENTS.md` and the `gather-data` skill, then:

1. Runs the **three search groups** against **lightbrd.com only**, fetched via
   the Firecrawl scrape API (`FIRECRAWL_API_KEY`) — NVIDIA/CUDA, Metal/MLX, and
   CPU (see `skills/gather-data.md`), last-3-day
   window. **One search at a time** to keep context small: run a query, capture
   its results, then move to the next — never hold all results in context at
   once. Each search writes its own timestamped raw snapshot to
   `data/raw/<backend>-<UTC>.json`.
2. After gathering, **reviews the captured data** and updates `data/models.json`
   via `resolve_model_mapping` (id → name → hf) + `ingest_raw_snapshots`:
   adds new models, updates existing models' t/s + engagement, and **never
   removes any existing model**.
3. Applies the 7-day trending / 30-day retention sort and regenerates
   `README.md` via `scripts/update_trending.py`; writes a timestamped snapshot.
4. Commits on a **feature branch** and opens a **PR** to `master` for manual
   review. It never pushes to or merges `master` itself.

## 6b. Three pipelines (refresh → validate → fix)

- **`refresh-bot.yml`** — the **bot** pipeline. Scheduled (daily) + manual
  dispatch. Runs the full Hermes refresh (three search groups, one at a time) →
  updates `data/models.json` + `README.md` + snapshot, and **opens a PR only
  when there is new data**. Never auto-merges.
- **`qa-validate.yml`** — the **PR CI** pipeline. Runs whenever a PR is created
  or updated (or on push/dispatch). It **validates the data content** on the PR
  (`scripts/validate.py`: no-removal, fields+links, backend sort by t/s, all
  models in README). It does not refresh data or commit.
- **`fix-bot.yml`** — the **fix** pipeline. Triggered when `qa-validate` is
  **red** (failure). Re-runs the Hermes CLI to inspect what the validation
  rejected, fix the data/logic, and push the correction to the same PR branch
  so the CI re-runs green (up to 5 rounds), then leaves the PR for manual
  review. Never auto-merges.

**Link-repair behavior for fix-bot (when CI reports a dead/wrong link).** The
CI link validator (`scripts/validate.py` `check_links_present` +
`check_links_resolve`) only **reports** which link failed — it never calls the
LLM. The fix-bot is the one that repairs. For each failing link it MUST search
for the correct one and verify it resolves before writing:

- **Model / format Hugging Face link** (`model-hf`, `format-hf`, `raw-hf`):
  find the canonical repo id via the Hugging Face CLI / `huggingface_hub`
  (e.g. `hf search models <name>` or the HF API
  `https://huggingface.co/api/models?search=<name>`), then confirm
  `https://huggingface.co/<id>` returns 200.
- **Engine / inference-server link** (`engine-registry`, `source_post`): do a
  regular Firecrawl web search (`FIRECRAWL_API_KEY`) for the engine's canonical
  repo URL and confirm it resolves. Known-good engine repos are in
  `KNOWN_ENGINE_URLS` in `scripts/validate.py`.
- Only write a link the fix-bot has actually verified resolves. If it cannot
  find a verified replacement, it leaves the link and reports it in the PR body
  for manual review — it never invents a URL.
- It updates `data/models.json` (and the raw snapshot if the wrong link came
  from `data/raw/*.json`), then regenerates `README.md` via
  `scripts/update_trending.py`. See `skills/gather-data.md` §3 for the exact
  search technique.

Contract evolution for fix-bot: when validation fails because the search
agent now emits a **new key/value that the data genuinely needs** (a new
engine, backend, format, engagement field, or top-level metadata that is
real and would be lost by pruning), fix-bot SHOULD update the contract
(`data/search_contract.json` and/or `data/model_contract.json`) to declare it,
**and update the corresponding tests in the same change** (rule 6b — the
contract shape lives in the per-file helpers, so a format change is a
one-place edit that ripples to all assertions). Only add a key when it is
real, traceable data — never to paper over a malformed snapshot. If a new key
is noise (a one-off artifact of a bad prompt), PRUNE it via
`self_correct_raw` instead of widening the contract. Distinguish the two: a
key that recurs across multiple backends/runs and carries real value → widen
the contract + tests; a stray/empty/malformed key → prune. Manual review is
still required before either lands.

**Contract versioning — additive vs breaking changes.** The contract is
versioned so OLD data can always be validated against the OLD contract and
NEW data against the NEW contract:

- **Additive change (backward-compatible):** adding a NEW key, a new enum
  value, or widening a constraint does NOT break existing data. Update the
  SAME contract file in place (`data/search_contract.json` /
  `data/model_contract.json`) and the tests in the same change. Old snapshots
  still validate (they simply lack the new optional key). No version bump.

- **Breaking change (backward-incompatible):** removing or renaming an
  existing key, changing a key's type, or removing an enum value makes OLD
  data fail the NEW contract. Do NOT edit the existing file in place. Instead
  create a NEW versioned contract — `data/search_contract.v2.json` /
  `data/model_contract.v2.json` (and so on for v3, v4, …) — that declares the
  new shape, and keep the old file untouched so old snapshots still validate
  against it. Update the validator (`scripts/validate.py`) and the tests to
  pick the right contract per data set: old raw snapshots / old models.json
  validate against the old contract, new ones against the new. The
  `generated_utc` timestamp (or a `contract_version` field) is what routes a
  snapshot to the correct contract version.

Rule of thumb: if every existing record still conforms after the change, it
is additive → edit in place. If any existing record would now fail, it is
breaking → new `*.vN.json` contract + validator/test routing. Never silently
re-validate old data against a changed contract.

Flow: bot refreshes + opens PR → PR CI validates → if red, fix-bot corrects with
Hermes → CI re-runs → green → human merges.

Rules for the refresh run:
- **Only lightbrd.com** is used for X signal — no other X source.
- If the mirror is unreachable, **preserve last-known data**; never blank the
  store or README. Report the failure in the PR/commit instead.
- The PR body states what changed, how many models were added/updated for
  trending, and that manual review is required before merge.
- The Nous token is read from the repo secret `NOUS_PORTAL_API_TOKEN`; never
  hardcode it in files or commit it.

## 7. Style

- Terse, factual tables. No marketing fluff.
- One specific engine per t/s measurement (llama.cpp, Ollama, vLLM, SGLang,
  MLX, TensorFold, FreeToken, TensorRT-LLM, LiteRT, Strata, MLX-fast, DFlash2).
- Mark estimates as `(est)`. Note hardware on every figure.
- Attribute each model to its real creator/community source; do not republish
  one person's private curation as your own.
