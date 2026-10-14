# trending-local-llms — Makefile
#
# SINGLE source of truth for every CI/local stage. Every public `make X`
# target runs the command INSIDE the Docker container (Python deps + Hermes CLI
# baked in), so the pipeline is agnostic to host system changes — the runner's
# Python/pip/Hermes are never relied on.
#
#   make docker-build       build the image once
#   make refresh            full pipeline in container  (setup,search,merge,validate,test)
#   make validate           validate in container
#   make test               unit tests in container
#   make fix                correct a red CI in container
#
# Internal recipes are prefixed `_` (host commands); public names are docker
# wrappers. The repo is bind-mounted at /workspace, so all data (raw snapshots,
# models.json, README, snapshots) writes back to the host.
#
# Requires (passed into the container): NOUS_API_KEY, FIRECRAWL_API_KEY.

SHELL := /bin/bash

# ---- nerve supervision plugin credential (issue #120) ------------------------
# The nerve plugin is baked into the image as CODE (Dockerfile, pinned to the
# Hermes plugin catalog commit) and is the ONLY consumer of this credential. The
# NAME below is the one the plugin actually resolves — measured at the pinned
# revision, hermes_nerve/client.py::PROVIDER_API_KEY_ENV:
#   openrouter -> OPENROUTER_API_KEY   (the plugin's own default jev_provider)
#   typesafe   -> TYPESAFE_API_KEY     <- PRODUCTION runs this provider
#   opencode   -> OPENCODE_API_KEY
# The provider is NOT the plugin's default: it is the one this setup runs, read
# from the host Hermes that mirrors this pipeline
# (`plugins.entries.nerve.settings.jev_provider = typesafe`, `typesafe_model =
# jev-latest`, `TYPESAFE_API_KEY` in the profile env). Wiring the default
# (`openrouter`) forwards a name production never sets, so the plugin fails on
# `TYPESAFE_API_KEY is not configured` — the silent failure AGENTS.md rule 3e
# forbids. There is NO `JEV_KEY` upstream (plugin source and the Hermes plugin
# catalog entry that pins it both say so), so that name would register a variable
# nothing reads. The key itself is never written anywhere: it reaches the
# container only as `-e $(NERVE_KEY_ENV)` at run time.
NERVE_PROVIDER := typesafe
NERVE_KEY_ENV  := TYPESAFE_API_KEY
NERVE_MODEL    := jev-latest

IMAGE := trending-local-llms:latest
DOCKER_RUN := docker run --rm -v "$$PWD":/workspace -w /workspace \
	-e NOUS_API_KEY -e FIRECRAWL_API_KEY -e HF_TOKEN -e $(NERVE_KEY_ENV) $(IMAGE)

# The TEST image layers the CURRENT requirements-test.txt on top of the base
# image at build time, so unit/QA tests (which need markdown-it-py + tabulate
# to validate the README tables) never depend on the base image's Sunday-only
# rebuild. `make test` / `make validate` run inside THIS image in CI.
TEST_IMAGE := trending-local-llms-test:latest
# What Dockerfile.test layers on. Defaults to the PUBLISHED base (CI pulls it);
# pass `BASE_IMAGE=$(IMAGE)` to layer on the base just built here — the path CI
# takes when the published base was not built from this Dockerfile (issue #135).
BASE_IMAGE ?= ghcr.io/andyholst/trending-local-llms:latest
TEST_REQUIREMENTS := requirements-test.txt
TEST_RUN := docker run --rm -v "$$PWD":/workspace -w /workspace \
	-e NOUS_API_KEY -e FIRECRAWL_API_KEY -e HF_TOKEN -e $(NERVE_KEY_ENV) $(TEST_IMAGE)


HERMES_MODEL := deepseek/deepseek-v4.1-flash
NOUS_BASE   := https://inference-api.nousresearch.com/v1
# Raise the per-reply output cap. The deepseek model was truncating its reply
# mid-search (hit the default max_tokens), dropping the incomplete action and
# failing `make refresh`. At 8000 the heavier Metal search still
# truncated mid-payload; 16000 gives headroom (the model card supports up to
# 384K output). Input context is also raised to the model's 1M-token ceiling
# (model card: 1M input / 384K output) so a long AGENTS.md + skill + mirrors
# page is never squeezed. One variable each so CI + local runs agree.
# The 65,536 figure below was measured against the PREVIOUS pin of this family
# (/v1/models -> top_provider.max_completion_tokens).
# The current pin, deepseek/deepseek-v4.1-flash, declares NO
# max_completion_tokens on the endpoint, so we keep the conservative 65,536
# until a live measurement of the new SKU. A larger value is accepted SILENTLY
# and clamped, which is how 384000 once hid the real cap.
# `make model-caps` checks this live against the catalog (no declared cap -> no
# false alarm; if a cap is declared it must be >= HERMES_MAX_TOKENS).
HERMES_MAX_TOKENS    := 65536
HERMES_CONTEXT_WINDOW := 1048576
# Reasoning per hermes call. Measured on the deepseek flash family: the SKU
# thinks by default and takes a generic `reasoning` switch (V4.1 Flash also
# exposes `reasoning_effort`). Effort 'low' STILL produces reasoning tokens, and
# a long multi-query search burned the whole 65,536-token budget on them
# ('No visible answer was produced ... reasoning consumed the entire budget').
# 'none' sends reasoning.enabled=false -> 0 reasoning tokens (measured). The
# searches are mechanical (scrape -> extract -> write JSON), so thinking OFF;
# the fix-bot diagnoses a failure report, so it keeps a little (low).
HERMES_REASONING     := none
HERMES_FIX_REASONING := low


## ---------------------------------------------------------------------------
## Build the image (do this once; CI does it in its own cached step)
## ---------------------------------------------------------------------------

.PHONY: docker-build
docker-build:
	docker build -t $(IMAGE) .

# The test image is FROM the base, so build the base first when it is missing.
.PHONY: docker-test-build
docker-test-build:
	docker build -f Dockerfile.test --build-arg BASE_IMAGE=$(BASE_IMAGE) -t $(TEST_IMAGE) .

# ---- runner images: pulled when published for THIS revision, else built -------
# The single code path every workflow and developer uses (issue #141). The
# publisher (refresh-bot) pushes the tags this decides on:
#   ghcr.io/<owner>/trending-local-llms:dockerfile-<sha12>       (base)
#   ghcr.io/<owner>/trending-local-llms-test:test-<sha12>        (test image)
IMAGE_REPO ?= ghcr.io/andyholst/trending-local-llms

.PHONY: image-tags image-ensure image-ensure-base image-ensure-test
image-tags:
	python3 scripts/ensure_image.py tags

# Both images (base + test): what a job that runs the suite needs.
image-ensure:
	python3 scripts/ensure_image.py ensure

# The base alone: what a job that only runs the image needs.
image-ensure-base:
	python3 scripts/ensure_image.py ensure-base

image-ensure-test:
	python3 scripts/ensure_image.py ensure-test

## ---------------------------------------------------------------------------
## Internal recipes (host commands) — wrapped by the docker public targets
## ---------------------------------------------------------------------------

.PHONY: _setup
_setup:
	@if command -v hermes >/dev/null 2>&1; then \
		echo "== hermes present; using image build (no per-run update) =="; \
	else \
		echo "== installing hermes =="; \
		curl -fsSL https://hermes-agent.nousresearch.com/install.sh | bash; \
	fi
	hermes --version
	hermes config set model.aliases.nous-deepseek.model $(HERMES_MODEL)
	hermes config set model.aliases.nous-deepseek.provider custom
	hermes config set model.aliases.nous-deepseek.base_url $(NOUS_BASE)
	hermes config set model.aliases.nous-deepseek.key_env NOUS_API_KEY
	hermes config set model.aliases.nous-deepseek.max_tokens $(HERMES_MAX_TOKENS)
	hermes config set model.aliases.nous-deepseek.context_window $(HERMES_CONTEXT_WINDOW)
	@# The nerve plugin is baked into this image as code (Dockerfile). Only its
	@# NON-SECRET setting is written to config.yaml — the credential itself is
	@# never here: the plugin resolves it by NAME
	@# ($(NERVE_KEY_ENV)) from the environment, which the run wrappers inject
	@# with `-e $(NERVE_KEY_ENV)` (AGENTS.md rule 3e).
	@if hermes plugins list 2>/dev/null | grep -qi 'nerve'; then \
		echo "== nerve plugin present; pinning its Jev provider ($(NERVE_PROVIDER), model $(NERVE_MODEL)) — the key stays in the env =="; \
		hermes config set plugins.entries.nerve.settings.jev_provider $(NERVE_PROVIDER); \
		hermes config set plugins.entries.nerve.settings.typesafe_model $(NERVE_MODEL); \
	else \
		echo "== nerve plugin NOT installed in this image; \`make nerve-check\` fails until it is =="; \
	fi

.PHONY: _search-nvidia
_search-nvidia:
	hermes -z "Load AGENTS.md for rules. Fetch X trending posts from lightbrd.com using the Firecrawl scrape API: POST https://api.firecrawl.dev/v1/scrape with header 'Authorization: Bearer \$${FI...KEY}' and body {\"url\":\"https://lightbrd.com/search?f=tweets&q=<urlencoded>\",\"formats\":[\"markdown\"]}. Search with NVIDIA keywords ONLY (rtx tokens per second llm, rtx 3090/4090/5090 tokens per second, bonsai 2 ternary, freetoken gpu, dflash speculative), one query at a time, last-3-day. Rank by interactions then t/s; record engine + model. Write tps as a CLEAN number with NO embedded text/comments (move context like 'DFlash spec-decode' into quant/hardware); record each post's likes/comments/reshares/views on the engine measurement. Set source_post to the exact post URL https://lightbrd.com/<user>/status/<id> - never the bare mirror URL or a profile page - and copy that post's likes, comments, reshares and views as integers onto the same measurement. If the post runs a fork or custom build of an engine (for example the PrismML llama.cpp fork that Ternary Bonsai 2 requires), record the engine exactly as that fork is named in the engines registry of data/models.json. Use engine names exactly as registered in data/models.json. An engine is an inference runtime or server that loads the weights (llama.cpp, MLX, vLLM, Ollama ...); harnesses, agent frameworks, plugins, chat apps, UIs and benchmarks are NOT engines - if a post only names one of those, record the runtime it uses instead, or skip the measurement. For an engine that is not registered yet, add engine_repo = its https://github.com/<owner>/<repo> URL as given in or linked from the post; if the post names the engine but links no repo, run ONE Firecrawl web search for the engine name plus github and record the repo only when its name matches the engine and the page resolves; never invent or guess a URL. After EACH query, immediately write only that query's captured models: python3 scripts/update_trending.py --write-raw nvidia < payload.json (each call writes its own data/raw/nvidia-<UTC>.json) - never collect all queries into one big payload, a reply has a 65536-token cap. When the post states them, also record the optional model fields system_ram_min, weight_gb, context_tokens, storage_offload and engine_min_version - copy only a figure the post actually gives, never guess, derive or invent one. Never remove a model. Do not merge or push." \
		-m nous-deepseek --reasoning $(HERMES_REASONING) --yolo

.PHONY: _search-metal
_search-metal:
	hermes -z "Load AGENTS.md for rules. Fetch X trending posts from lightbrd.com using the Firecrawl scrape API: POST https://api.firecrawl.dev/v1/scrape with header 'Authorization: Bearer \$${FI...KEY}' and body {\"url\":\"https://lightbrd.com/search?f=tweets&q=<urlencoded>\",\"formats\":[\"markdown\"]}. Search with Apple/Metal keywords ONLY (mlx tokens per second, mlx apple silicon, mac m4 mlx local llm, mlxfast bonsai, tensorfold dflash mlx), one query at a time, last-3-day. Rank by interactions then t/s; record engine + model. Write tps as a CLEAN number with NO embedded text/comments (move context like 'DFlash spec-decode' into quant/hardware); record each post's likes/comments/reshares/views on the engine measurement. Set source_post to the exact post URL https://lightbrd.com/<user>/status/<id> - never the bare mirror URL or a profile page - and copy that post's likes, comments, reshares and views as integers onto the same measurement. If the post runs a fork or custom build of an engine (for example the PrismML llama.cpp fork that Ternary Bonsai 2 requires), record the engine exactly as that fork is named in the engines registry of data/models.json. Use engine names exactly as registered in data/models.json. An engine is an inference runtime or server that loads the weights (llama.cpp, MLX, vLLM, Ollama ...); harnesses, agent frameworks, plugins, chat apps, UIs and benchmarks are NOT engines - if a post only names one of those, record the runtime it uses instead, or skip the measurement. For an engine that is not registered yet, add engine_repo = its https://github.com/<owner>/<repo> URL as given in or linked from the post; if the post names the engine but links no repo, run ONE Firecrawl web search for the engine name plus github and record the repo only when its name matches the engine and the page resolves; never invent or guess a URL. After EACH query, immediately write only that query's captured models: python3 scripts/update_trending.py --write-raw metal < payload.json (each call writes its own data/raw/metal-<UTC>.json) - never collect all queries into one big payload, a reply has a 65536-token cap. When the post states them, also record the optional model fields system_ram_min, weight_gb, context_tokens, storage_offload and engine_min_version - copy only a figure the post actually gives, never guess, derive or invent one. Never remove a model. Do not merge or push." \
		-m nous-deepseek --reasoning $(HERMES_REASONING) --yolo

.PHONY: _search-cpu
_search-cpu:
	hermes -z "Load AGENTS.md for rules. Fetch X trending posts from lightbrd.com using the Firecrawl scrape API: POST https://api.firecrawl.dev/v1/scrape with header 'Authorization: Bearer \$${FI...KEY}' and body {\"url\":\"https://lightbrd.com/search?f=tweets&q=<urlencoded>\",\"formats\":[\"markdown\"]}. Search with CPU/embedded/edge keywords ONLY (llm tokens per second no gpu cpu, llama.cpp cpu only, raspberry pi llm tokens per second, local llm cpu), one query at a time, last-3-day. Rank by interactions then t/s; record engine + model. Write tps as a CLEAN number with NO embedded text/comments (move context like 'DFlash spec-decode' into quant/hardware); record each post's likes/comments/reshares/views on the engine measurement. Set source_post to the exact post URL https://lightbrd.com/<user>/status/<id> - never the bare mirror URL or a profile page - and copy that post's likes, comments, reshares and views as integers onto the same measurement. If the post runs a fork or custom build of an engine (for example the PrismML llama.cpp fork that Ternary Bonsai 2 requires), record the engine exactly as that fork is named in the engines registry of data/models.json. Use engine names exactly as registered in data/models.json. An engine is an inference runtime or server that loads the weights (llama.cpp, MLX, vLLM, Ollama ...); harnesses, agent frameworks, plugins, chat apps, UIs and benchmarks are NOT engines - if a post only names one of those, record the runtime it uses instead, or skip the measurement. For an engine that is not registered yet, add engine_repo = its https://github.com/<owner>/<repo> URL as given in or linked from the post; if the post names the engine but links no repo, run ONE Firecrawl web search for the engine name plus github and record the repo only when its name matches the engine and the page resolves; never invent or guess a URL. After EACH query, immediately write only that query's captured models: python3 scripts/update_trending.py --write-raw cpu < payload.json (each call writes its own data/raw/cpu-<UTC>.json) - never collect all queries into one big payload, a reply has a 65536-token cap. When the post states them, also record the optional model fields system_ram_min, weight_gb, context_tokens, storage_offload and engine_min_version - copy only a figure the post actually gives, never guess, derive or invent one. Never remove a model. Do not merge or push." \
		-m nous-deepseek --reasoning $(HERMES_REASONING) --yolo

.PHONY: _search-amd
_search-amd:
	hermes -z "Load AGENTS.md for rules. Fetch X trending posts from lightbrd.com using the Firecrawl scrape API: POST https://api.firecrawl.dev/v1/scrape with header 'Authorization: Bearer \$${FI...KEY}' and body {\"url\":\"https://lightbrd.com/search?f=tweets&q=<urlencoded>\",\"formats\":[\"markdown\"]}. Search with AMD/ROCm keywords ONLY (rx 7900 xtx tokens per second, rx 9070 xt tokens per second, rocm tokens per second, llama.cpp vulkan amd tokens, strix halo tokens per second), one query at a time, last-3-day. AMD rules: record the AMD card exactly as posted in hardware (for example 'RX 7900 XTX 24GB', 'RX 9070 XT 16GB', 'Radeon 8060S / Strix Halo 128GB') - that is what puts the figure in the ROCm table; keep the engine name as registered (llama.cpp, Ollama, vLLM, SGLang, Strata ...) and put the API (ROCm, HIP, Vulkan) in quant, never in the engine name; record generation/decode t/s only, never prompt-processing or prefill t/s; skip datacenter Instinct (MI300/MI355) posts. Rank by interactions then t/s; record engine + model. Write tps as a CLEAN number with NO embedded text/comments (move context like 'DFlash spec-decode' into quant/hardware); record each post's likes/comments/reshares/views on the engine measurement. Set source_post to the exact post URL https://lightbrd.com/<user>/status/<id> - never the bare mirror URL or a profile page - and copy that post's likes, comments, reshares and views as integers onto the same measurement. If the post runs a fork or custom build of an engine (for example the PrismML llama.cpp fork that Ternary Bonsai 2 requires), record the engine exactly as that fork is named in the engines registry of data/models.json. Use engine names exactly as registered in data/models.json. An engine is an inference runtime or server that loads the weights (llama.cpp, MLX, vLLM, Ollama ...); harnesses, agent frameworks, plugins, chat apps, UIs and benchmarks are NOT engines - if a post only names one of those, record the runtime it uses instead, or skip the measurement. For an engine that is not registered yet, add engine_repo = its https://github.com/<owner>/<repo> URL as given in or linked from the post; if the post names the engine but links no repo, run ONE Firecrawl web search for the engine name plus github and record the repo only when its name matches the engine and the page resolves; never invent or guess a URL. After EACH query, immediately write only that query's captured models: python3 scripts/update_trending.py --write-raw amd < payload.json (each call writes its own data/raw/amd-<UTC>.json) - never collect all queries into one big payload, a reply has a 65536-token cap. When the post states them, also record the optional model fields system_ram_min, weight_gb, context_tokens, storage_offload and engine_min_version - copy only a figure the post actually gives, never guess, derive or invent one. Never remove a model. Do not merge or push." \
		-m nous-deepseek --reasoning $(HERMES_REASONING) --yolo

.PHONY: _search
_search:
	@echo "== running 4 searches in parallel (each writes its own data/raw/<backend>-<UTC>.json) =="
	@make -j4 _search-nvidia _search-metal _search-cpu _search-amd

.PHONY: _search-smoke
_search-smoke:
	python3 scripts/smoke_search.py --budget 3 $(if $(BACKEND),--backend $(BACKEND),)

# Live Hermes routing smoke: ONE tiny real call through the exact alias the
# search/fix recipes use, with every provider key the pipeline passes (incl.
# HF_TOKEN). Catches a broken alias, a dead NOUS key, or hermes silently
# routing to another provider (the HF 403 that killed every fix-bot run) in
# seconds instead of after a 20-minute search. Skips when NOUS_API_KEY is unset.
HERMES_SMOKE_TIMEOUT := 90
# Live model-catalog guard: HERMES_MODEL exists on the endpoint, HERMES_MAX_TOKENS
# fits its real max_completion_tokens, and it accepts `reasoning`. Skips w/o key.
.PHONY: _model-caps
_model-caps:
	python3 scripts/model_caps_check.py --base $(NOUS_BASE) --model $(HERMES_MODEL) --max-tokens $(HERMES_MAX_TOKENS)

.PHONY: _hermes-smoke
_hermes-smoke:
	HERMES_SMOKE_TIMEOUT=$(HERMES_SMOKE_TIMEOUT) bash scripts/hermes_smoke.sh

.PHONY: _correct-raw
_correct-raw:
	python3 scripts/self_correct_raw.py

# Weekly Hermes update. Runs only on Sunday (or UPDATE_HERMES=1 forced). The
# Dockerfile bakes this via `make _update-hermes` (the host recipe), and the
# CI build job only rebuilds the image on Sunday — so Hermes is updated at
# most once per week. The search/aggregate jobs use the prebuilt image as-is
# (no per-run update).
.PHONY: _update-hermes
_update-hermes:
	@if [ "$$(scripts/hermes_update_needed.sh)" = "1" ]; then \
		echo "== weekly hermes update (Sunday or UPDATE_HERMES=1) =="; \
		hermes update || echo "(update failed; using existing)"; \
	else \
		echo "== no hermes update needed (not Sunday, UPDATE_HERMES unset) =="; \
	fi

.PHONY: _fix
_fix:
	hermes -z "The CI validation for the trending-local-llms PR failed. The EXACT failures are in qa-report.txt at the repo root (output of make validate, validate-search, validate-mapped and test) - read it FIRST and fix those specific failures; do not guess. Load AGENTS.md for the acceptance criteria and fix the data so validation passes. The validation (scripts/validate.py) requires ALL of: (1) no model removed vs the previous snapshot; (2) every model has name/full_name/HF link/license/params/VRAM tier + at least one engine measurement with engine name + t/s + repo link; (3) each backend table (CUDA, Metal, CPU, ROCm) sorted by highest t/s descending; (4) README in sync with data/models.json - every model and engine measurement in the JSON must appear in the README and the Last generated timestamp must match (both must change together); (5) every model in the store appears in the README; (6) raw search snapshots must conform to data/search_contract.json. Inspect data/models.json, data/raw/*.json and README.md, fix what is rejected, regenerate README.md via scripts/update_trending.py. Do not remove any existing model. Do not push or merge. CONTRACT EVOLUTION: if validation fails because a raw snapshot now carries a new key/value that is REAL, recurring data (a new engine/backend/format/engagement field/top-level metadata) which would otherwise be lost, update data/search_contract.json and/or data/model_contract.json to declare it AND update the corresponding tests in the same change (per AGENTS.md rule 6b - the helpers in the test files carry the contract shape). Only widen the contract for real, traceable data; if the new key is a stray/empty/malformed one-off artifact, PRUNE it via self_correct_raw instead of widening the contract. Never invent a key to pass validation. CONTRACT VERSIONING: an ADDITIVE change (new key / new enum value / widened constraint that existing records still satisfy) edits the SAME contract file in place. A BREAKING change (removing/renaming a key, changing a type, removing an enum value that makes OLD data fail) must NOT edit the existing file - create a NEW versioned contract data/search_contract.v2.json or data/model_contract.v2.json (and so on for v3, v4, ...) that declares the new shape, and keep the old file untouched so old snapshots still validate against it. Update the validator (scripts/validate.py) and the tests to pick the right contract per data set: old raw snapshots / old models.json validate against the old contract, new ones against the new. The generated_utc timestamp (or a contract_version field) is what routes a snapshot to the correct contract version. LINK REPAIR (when validation reports a dead/wrong link): the CI link validator (scripts/validate.py check_links_resolve) only reports which link failed - it does NOT call the LLM. YOU are the fixer. For each failing link, SEARCH for the correct one and validate it before writing: (a) for a model/format Hugging Face link, use the Hugging Face CLI / huggingface_hub (e.g. hf search models <name> or the HF API) to find the canonical repo id, then confirm https://huggingface.co/<id> resolves; (b) for an engine/inference-server link, do a regular Firecrawl web search (FIRECRAWL_API_KEY) for the engines canonical repo URL and confirm it resolves. Only write a corrected link you have actually verified resolves. ENGINE REGISTRY: only register real inference engines (runtimes or servers that load the weights). Never register a harness, agent framework, plugin, chat app, UI or benchmark even if its repo resolves - leave that failure for manual review and say so in your summary. If you cannot find a verified replacement, leave the link and report it in the PR body for manual review - never invent a URL. Update data/models.json (and the raw snapshot if the wrong link came from data/raw/*.json), then regenerate README.md." \
		-m nous-deepseek --reasoning $(HERMES_FIX_REASONING) --yolo
	python3 scripts/update_trending.py  # merge corrected raw -> models.json
	python3 scripts/validate.py --only links  # fail-fast: confirm the fix actually resolved the links

.PHONY: _merge
_merge:
	python3 scripts/update_trending.py

.PHONY: _merge-fetch
_merge-fetch:
	python3 scripts/update_trending.py --fetch

.PHONY: _validate
_validate:
	python3 scripts/validate.py

.PHONY: _validate-fetch
_validate-fetch:
	python3 scripts/update_trending.py --fetch --require-hits --dry-run

.PHONY: _validate-data
_validate-data:
	python3 scripts/validate.py --only data,removal

.PHONY: _validate-schema
_validate-schema:
	python3 scripts/validate.py --only schema

# Report (never fails) unregistered engines in the raw snapshots and what
# ingest will decide for each: registered / not-engine / unknown / no-repo.
# Runs in every refresh search job and the aggregate, so a new engine shows up
# in the refresh run instead of first failing PR CI.
.PHONY: _engine-check
_engine-check:
	python3 scripts/engine_registry.py --check-raw data/raw

.PHONY: _nerve-check
_nerve-check:
	python3 scripts/nerve_key_check.py

.PHONY: nerve-check
nerve-check:
	$(TEST_RUN) make _nerve-check

.PHONY: _validate-search
_validate-search:
	python3 scripts/validate.py --only search,mapping
	python3 tests/test_mapping.py && python3 tests/test_validate.py && python3 tests/test_validate_readme.py && python3 tests/test_ingest_render.py && python3 tests/test_aggregate_recovery.py && python3 tests/test_7day_aggregation.py && python3 tests/test_fixture_mapping.py && python3 tests/test_validate_links.py
	python3 scripts/self_correct_raw.py

.PHONY: _validate-readme
_validate-readme:
	python3 scripts/validate.py --only readme

.PHONY: _validate-links
_validate-links:
	python3 scripts/validate.py --only links
	python3 tests/test_validate_links.py

.PHONY: _validate-mapped
_validate-mapped:
	python3 scripts/validate.py --only data,schema,mapping,removal
	python3 tests/test_mapping.py && python3 tests/test_validate.py && python3 tests/test_aggregate_recovery.py && python3 tests/test_7day_aggregation.py && python3 tests/test_fixture_mapping.py && python3 tests/test_validate_links.py && python3 tests/test_engagement_contract.py && python3 tests/test_amd_backend.py

# The refresh aggregate job's QA pass (issue #147). Every target here runs (in
# the container) and its FINDINGS are reported — but a target that could not run
# at all (docker 125 = no image, 127 = no such command) FAILS the job: green must
# mean "the data landed and the QA pass actually ran".
QA_REPORT_TARGETS := validate validate-search validate-fetch validate-mapped test

.PHONY: qa-report
qa-report:
	bash scripts/qa_report.sh $(QA_REPORT_TARGETS)


.PHONY: _test
_test:
	python3 -m pytest tests/ -q 2>/dev/null || (python3 tests/test_mapping.py && python3 tests/test_validate.py && python3 tests/test_validate_readme.py && python3 tests/test_ingest_render.py && python3 tests/test_make_commands.py && python3 tests/test_hermes_update_needed.py && python3 tests/test_aggregate_recovery.py && python3 tests/test_7day_aggregation.py && python3 tests/test_fixture_mapping.py && python3 tests/test_validate_links.py && python3 tests/test_smoke_search.py && python3 tests/test_data_gap_analysis.py && python3 tests/test_secret_scan.py && python3 tests/test_hermes_prompts.py && python3 tests/test_engagement_contract.py && python3 tests/test_fix_loop.py && python3 tests/test_workflows.py && python3 tests/test_readme_render.py && python3 tests/test_post_signal.py && python3 tests/test_trend_score.py && python3 tests/test_engine_aliases.py && python3 tests/test_hermes_smoke.py && python3 tests/test_search_budget.py && python3 tests/test_engine_registry.py && python3 tests/test_amd_backend.py && python3 tests/test_nerve_key_wiring.py && python3 tests/test_qa_report.py)


.PHONY: _requirements-test
_requirements-test:
	python3 -m piptools compile --quiet --output-file $(TEST_REQUIREMENTS) requirements-test.in

.PHONY: _requirements
_requirements:
	pip install --quiet pip-tools
	pip-compile --quiet --output-file requirements.txt requirements.in
	@echo "== regenerated requirements.txt from requirements.in =="

# Regenerate EVERY requirements-*.txt from its *.in (base + any test pairs)
# with ONE command. Iterates all requirements*.in in the repo root.
.PHONY: _generate-requirements
_generate-requirements:
	pip install --quiet pip-tools
	@for f in requirements*.in; do \
		out=$${f%.in}.txt; \
		echo "== pip-compile $$f -> $$out =="; \
		pip-compile --quiet --output-file $$out $$f; \
	done
	@echo "== regenerated all requirements*.txt from requirements*.in =="

## ---------------------------------------------------------------------------
## Public targets — EVERYTHING runs inside the Docker container
## ---------------------------------------------------------------------------

# Soft-validation refresh: gather + merge are HARD (a broken merge must abort),
# but validation/testing failures are recorded and reported, NOT fatal. This
# lets the CI "Commit + open PR" step always land the merged data as a PR so
# qa-validate can flag issues and fix-bot can repair them on the PR branch.
# If validation were fatal here, a data-quality problem would abort refresh
# before any PR is opened and nobody could ever review or fix it.
.PHONY: _refresh
_refresh:
	@echo "== _setup =="; make _setup || exit 1
	@echo "== _search (parallel, soft) =="; make _search || echo "[refresh] one or more searches failed; aggregating the successful ones"
	@echo "== _merge =="; make _merge || exit 1
	@echo "== _validate (soft) =="; make _validate || echo "[refresh] _validate reported issues (see above); opening PR for review"
	@echo "== _validate-search (soft) =="; make _validate-search || echo "[refresh] _validate-search reported issues (see above)"
	@echo "== _validate-mapped (soft) =="; make _validate-mapped || echo "[refresh] _validate-mapped reported issues (see above)"
	@echo "== _test (soft) =="; make _test || echo "[refresh] _test reported failures (see above)"
	@echo "== refresh complete (data landed; validation findings reported above) =="

.PHONY: update-hermes
update-hermes:
	$(DOCKER_RUN) make _update-hermes

.PHONY: setup
setup:
	$(DOCKER_RUN) make _setup

.PHONY: search-nvidia
search-nvidia:
	$(DOCKER_RUN) sh -c "make _setup && make _search-nvidia"

.PHONY: search-metal
search-metal:
	$(DOCKER_RUN) sh -c "make _setup && make _search-metal"

.PHONY: search-cpu
search-cpu:
	$(DOCKER_RUN) sh -c "make _setup && make _search-cpu"

.PHONY: search-amd
search-amd:
	$(DOCKER_RUN) sh -c "make _setup && make _search-amd"

.PHONY: search
search:
	$(DOCKER_RUN) sh -c "make _setup && make _search"

.PHONY: search-smoke
search-smoke:
	$(DOCKER_RUN) make _search-smoke $(if $(BACKEND),BACKEND=$(BACKEND),)

.PHONY: model-caps
model-caps:
	$(DOCKER_RUN) make _model-caps

.PHONY: hermes-smoke
hermes-smoke:
	$(DOCKER_RUN) sh -c "make _setup >/dev/null && make _hermes-smoke"

# Live pipeline smoke: real Firecrawl->lightbrd scrape for every nvidia/metal/
# cpu/amd query (3s cap each) + a real Hermes call through the search alias.
.PHONY: pipeline-smoke
pipeline-smoke: search-smoke model-caps hermes-smoke

.PHONY: correct-raw
correct-raw:
	$(DOCKER_RUN) make _correct-raw

.PHONY: fix
fix:
	$(DOCKER_RUN) sh -c "make _setup && make _correct-raw && make _fix HERMES_FIX_REASONING=$(HERMES_FIX_REASONING) && make _merge"

.PHONY: merge
merge:
	$(DOCKER_RUN) make _merge

.PHONY: merge-fetch
merge-fetch:
	$(DOCKER_RUN) sh -c "make _merge-fetch"

.PHONY: validate
validate:
	$(TEST_RUN) make _validate

.PHONY: validate-fetch
validate-fetch:
	$(TEST_RUN) make _validate-fetch

.PHONY: validate-data
validate-data:
	$(TEST_RUN) make _validate-data

.PHONY: validate-schema
validate-schema:
	$(TEST_RUN) make _validate-schema

.PHONY: engine-check
engine-check:
	$(DOCKER_RUN) make _engine-check

.PHONY: validate-search
validate-search:
	$(TEST_RUN) make _validate-search

.PHONY: validate-readme
validate-readme:
	$(TEST_RUN) make _validate-readme

.PHONY: validate-links
validate-links:
	$(TEST_RUN) make _validate-links

.PHONY: validate-mapped
validate-mapped:
	$(TEST_RUN) make _validate-mapped

# ---- post-refresh data-gap analysis (issue #115) -----------------------------
# Every refresh asks what the acquired data still does NOT capture (system RAM
# first: the store has vram_tier/vram_min and nothing else) and files it as ONE
# issue (label data-gap-analysis) when the gap set changed vs data/gap_baseline.json.
# Report only: it never fails the data PR.
.PHONY: _data-gaps
_data-gaps:
	python3 scripts/data_gap_analysis.py

.PHONY: _data-gap-issue
_data-gap-issue:
	python3 scripts/data_gap_analysis.py --issue

.PHONY: data-gaps
data-gaps:
	$(TEST_RUN) make _data-gaps

.PHONY: data-gap-issue
data-gap-issue:
	$(TEST_RUN) make _data-gap-issue

# ---- secret scan: no credential may reach the repo (issue #122) --------------
# gitleaks (MIT, the most widely adopted FOSS secret scanner) runs in ITS OWN
# container image, pinned by tag: the pipeline image has no docker inside, so the
# scanner cannot live in it. `make secret-scan` scans the working tree (staged
# files included) — run it BEFORE every push; CI runs it on every PR.
GITLEAKS_IMAGE := ghcr.io/gitleaks/gitleaks:v8.30.1
GITLEAKS_RUN := docker run --rm -v "$$PWD":/repo -w /repo $(GITLEAKS_IMAGE)

.PHONY: _secret-scan
_secret-scan:
	$(GITLEAKS_RUN) dir /repo --config /repo/.gitleaks.toml --redact --no-banner --exit-code 1

.PHONY: secret-scan
secret-scan:
	@$(MAKE) _secret-scan || { \
		echo "SECRET SCAN FAILED: a credential shape is present in the working tree."; \
		echo "Remove the value, rotate the key in the provider + in the GitHub secret, and only"; \
		echo "then push. Never add it to .gitleaks.toml to make the scan pass — an allowlist is"; \
		echo "for a documented PLACEHOLDER, never for a real value."; \
		exit 1; }

.PHONY: _secret-scan-history
_secret-scan-history:
	@if [ -f .git ]; then \
		echo "SECRET SCAN (history) needs a real clone: this checkout is a git worktree (.git is a file)."; \
		echo "Run it in the primary checkout or in CI."; \
		exit 1; \
	fi
	$(GITLEAKS_RUN) git /repo --config /repo/.gitleaks.toml --redact --no-banner --exit-code 1

.PHONY: secret-scan-history
secret-scan-history:
	@$(MAKE) _secret-scan-history

# Prove the scan is not a false green: a planted fake credential MUST be caught.
.PHONY: secret-scan-self-test
secret-scan-self-test:
	python3 scripts/secret_scan_self_test.py

# ---- issue-bot: implement ONE filed data-gap issue (issue #113) --------------
# The issue's title + body are written to issue.md at the repo root by
# `.github/workflows/issue-bot.yml`; the agent reads it FIRST and implements
# exactly that issue, additive only, with everything wired to a make target.
.PHONY: _implement-issue
_implement-issue:
	hermes -z "Load AGENTS.md for rules. The data-gap issue you must implement is in issue.md at the repo root - read it FIRST and implement exactly its acceptance criteria; do not widen the scope and do not implement a different finding. HARD RULES: (1) ADDITIVE ONLY - never remove or rename an existing key and never shrink an existing value in data/models.json, data/raw/*.json, data/snapshots/*.json or the contracts; a new key is OPTIONAL and must NOT be added to a contract's required list (AGENTS.md rules 3b and 6b). (2) NEVER fabricate data: every value must trace to a real X post or to a verified upstream source, or be marked (est); if you cannot verify it, leave the key unset and say so in your summary. (3) WIRE EVERYTHING: any script, subcommand or validator check you add must be reachable from a make target CI runs - bundle it into an existing stage or add an internal _name recipe plus its public wrapper (AGENTS.md rule 6d) - and update that stage's tests in the same change (rule 6b). (4) If the data changed, regenerate README.md with python3 scripts/update_trending.py; if a stage or guard changed, update AGENTS.md including its section 8 row. (5) Edit the files themselves - NEVER add scratch artifacts: no *.patch, no *.rej, no report dumps, no backup copies; a change written into a patch file instead of the file is not an implementation. (6) Run make validate, make validate-mapped and make test and fix what they report. Do not push, do not merge, do not touch master." \
		-m nous-deepseek --reasoning $(HERMES_FIX_REASONING) --yolo

.PHONY: implement-issue
implement-issue:
	# `_setup` MUST run in the SAME container as the hermes call, exactly like
	# every other public hermes target (`search-*`, `fix`, `hermes-smoke`): it is
	# what writes `model.aliases.nous-deepseek.*` into that container's
	# ~/.hermes/config.yaml. Without it Hermes starts with NO alias and
	# auto-routes to whatever provider key is in the env — measured on the first
	# issue-bot run (#124, run 38502619350): `HF_TOKEN` -> Hugging Face ->
	# `HTTP 403 ... does not have sufficient permissions to call Inference Providers`.
	$(DOCKER_RUN) sh -c "make _setup && make _implement-issue"

.PHONY: test
test:
	$(TEST_RUN) make _test

.PHONY: requirements generate-requirements
requirements:
	$(DOCKER_RUN) make _requirements

# docker wrapper -> _generate-requirements (handles all *.in files via pip-compile)
generate-requirements:
	$(DOCKER_RUN) make _generate-requirements

.PHONY: refresh
refresh:
	$(DOCKER_RUN) make _refresh

.PHONY: all
all: refresh
