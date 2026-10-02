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

IMAGE := trending-local-llms:latest
DOCKER_RUN := docker run --rm -v "$$PWD":/workspace -w /workspace \
	-e NOUS_API_KEY -e FIRECRAWL_API_KEY -e HF_TOKEN $(IMAGE)

# The TEST image layers the CURRENT requirements-test.txt on top of the base
# image at build time, so unit/QA tests (which need markdown-it-py + tabulate
# to validate the README tables) never depend on the base image's Sunday-only
# rebuild. `make test` / `make validate` run inside THIS image in CI.
TEST_IMAGE := trending-local-llms-test:latest
TEST_REQUIREMENTS := requirements-test.txt
TEST_RUN := docker run --rm -v "$$PWD":/workspace -w /workspace \
	-e NOUS_API_KEY -e FIRECRAWL_API_KEY -e HF_TOKEN $(TEST_IMAGE)


HERMES_MODEL := deepseek/deepseek-v4-flash-0731
NOUS_BASE   := https://inference-api.nousresearch.com/v1
# Raise the per-reply output cap. The deepseek model was truncating its reply
# mid-search (hit the default max_tokens), dropping the incomplete action and
# failing `make refresh`. At 8000 the heavier Metal search still
# truncated mid-payload; 16000 gives headroom (the model card supports up to
# 384K output). Input context is also raised to the model's 1M-token ceiling
# (model card: 1M input / 384K output) so a long AGENTS.md + skill + mirrors
# page is never squeezed. One variable each so CI + local runs agree.
HERMES_MAX_TOKENS    := 384000
HERMES_CONTEXT_WINDOW := 1048576
# Reasoning effort per hermes call. Raising max_tokens alone does NOT stop a
# search from failing with 'No visible answer was produced ... its reasoning
# consumed the entire budget each time' -- the model just reasons longer. The
# searches are mechanical (scrape -> extract -> write JSON), so cap reasoning
# low; the fix-bot gets medium since it has to diagnose a failure report.
HERMES_REASONING     := low
HERMES_FIX_REASONING := medium


## ---------------------------------------------------------------------------
## Build the image (do this once; CI does it in its own cached step)
## ---------------------------------------------------------------------------

.PHONY: docker-build
docker-build:
	docker build -t $(IMAGE) .

# The test image is FROM the base, so build the base first when it is missing.
.PHONY: docker-test-build
docker-test-build:
	docker build -f Dockerfile.test -t $(TEST_IMAGE) .

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

.PHONY: _search-nvidia
_search-nvidia:
	hermes -z "Load AGENTS.md for rules. Fetch X trending posts from lightbrd.com using the Firecrawl scrape API: POST https://api.firecrawl.dev/v1/scrape with header 'Authorization: Bearer \$${FI...KEY}' and body {\"url\":\"https://lightbrd.com/search?f=tweets&q=<urlencoded>\",\"formats\":[\"markdown\"]}. Search with NVIDIA keywords ONLY (rtx tokens per second llm, rtx 3090/4090/5090 tokens per second, bonsai 2 ternary, freetoken gpu, dflash speculative), one query at a time, last-3-day. Rank by interactions then t/s; record engine + model. Write tps as a CLEAN number with NO embedded text/comments (move context like 'DFlash spec-decode' into quant/hardware); record each post's likes/comments/reshares/views on the engine measurement. Set source_post to the exact post URL https://lightbrd.com/<user>/status/<id> - never the bare mirror URL or a profile page - and copy that post's likes, comments, reshares and views as integers onto the same measurement. Write the captured models to data/raw/nvidia-<UTC>.json using:  python3 scripts/update_trending.py --write-raw nvidia < payload.json. Never remove a model. Do not merge or push." \
		-m nous-deepseek --reasoning $(HERMES_REASONING) --yolo

.PHONY: _search-metal
_search-metal:
	hermes -z "Load AGENTS.md for rules. Fetch X trending posts from lightbrd.com using the Firecrawl scrape API: POST https://api.firecrawl.dev/v1/scrape with header 'Authorization: Bearer \$${FI...KEY}' and body {\"url\":\"https://lightbrd.com/search?f=tweets&q=<urlencoded>\",\"formats\":[\"markdown\"]}. Search with Apple/Metal keywords ONLY (mlx tokens per second, mlx apple silicon, mac m4 mlx local llm, mlxfast bonsai, tensorfold dflash mlx), one query at a time, last-3-day. Rank by interactions then t/s; record engine + model. Write tps as a CLEAN number with NO embedded text/comments (move context like 'DFlash spec-decode' into quant/hardware); record each post's likes/comments/reshares/views on the engine measurement. Set source_post to the exact post URL https://lightbrd.com/<user>/status/<id> - never the bare mirror URL or a profile page - and copy that post's likes, comments, reshares and views as integers onto the same measurement. Write the captured models to data/raw/metal-<UTC>.json using:  python3 scripts/update_trending.py --write-raw metal < payload.json. Never remove a model. Do not merge or push." \
		-m nous-deepseek --reasoning $(HERMES_REASONING) --yolo

.PHONY: _search-cpu
_search-cpu:
	hermes -z "Load AGENTS.md for rules. Fetch X trending posts from lightbrd.com using the Firecrawl scrape API: POST https://api.firecrawl.dev/v1/scrape with header 'Authorization: Bearer \$${FI...KEY}' and body {\"url\":\"https://lightbrd.com/search?f=tweets&q=<urlencoded>\",\"formats\":[\"markdown\"]}. Search with CPU/embedded/edge keywords ONLY (llm tokens per second no gpu cpu, llama.cpp cpu only, raspberry pi llm tokens per second, local llm cpu), one query at a time, last-3-day. Rank by interactions then t/s; record engine + model. Write tps as a CLEAN number with NO embedded text/comments (move context like 'DFlash spec-decode' into quant/hardware); record each post's likes/comments/reshares/views on the engine measurement. Set source_post to the exact post URL https://lightbrd.com/<user>/status/<id> - never the bare mirror URL or a profile page - and copy that post's likes, comments, reshares and views as integers onto the same measurement. Write the captured models to data/raw/cpu-<UTC>.json using:  python3 scripts/update_trending.py --write-raw cpu < payload.json. Never remove a model. Do not merge or push." \
		-m nous-deepseek --reasoning $(HERMES_REASONING) --yolo

.PHONY: _search
_search:
	@echo "== running 3 searches in parallel (each writes its own data/raw/<backend>-<UTC>.json) =="
	@make -j4 _search-nvidia _search-metal _search-cpu

.PHONY: _search-smoke
_search-smoke:
	python3 scripts/smoke_search.py --budget 3 $(if $(BACKEND),--backend $(BACKEND),)

# Live Hermes routing smoke: ONE tiny real call through the exact alias the
# search/fix recipes use, with every provider key the pipeline passes (incl.
# HF_TOKEN). Catches a broken alias, a dead NOUS key, or hermes silently
# routing to another provider (the HF 403 that killed every fix-bot run) in
# seconds instead of after a 20-minute search. Skips when NOUS_API_KEY is unset.
HERMES_SMOKE_TIMEOUT := 90
.PHONY: _hermes-smoke
_hermes-smoke:
	@if [ -z "$$NOUS_API_KEY" ]; then echo "[hermes-smoke] SKIP: NOUS_API_KEY not set"; exit 0; fi; \
	out=$$(timeout $(HERMES_SMOKE_TIMEOUT) hermes -z "Reply with exactly the word PONG and nothing else." \
		-m nous-deepseek --reasoning none 2>&1); rc=$$?; \
	echo "$$out" | tail -5; \
	if [ $$rc -ne 0 ] || ! echo "$$out" | grep -q PONG; then \
		echo "[hermes-smoke] FAIL rc=$$rc: alias nous-deepseek did not answer PONG"; exit 1; fi; \
	echo "[hermes-smoke] OK: nous-deepseek answered via the configured alias"

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
	hermes -z "The CI validation for the trending-local-llms PR failed. The EXACT failures are in qa-report.txt at the repo root (output of make validate, validate-search, validate-mapped and test) - read it FIRST and fix those specific failures; do not guess. Load AGENTS.md for the acceptance criteria and fix the data so validation passes. The validation (scripts/validate.py) requires ALL of: (1) no model removed vs the previous snapshot; (2) every model has name/full_name/HF link/license/params/VRAM tier + at least one engine measurement with engine name + t/s + repo link; (3) each backend table (CUDA, Metal, CPU) sorted by highest t/s descending; (4) README in sync with data/models.json - every model and engine measurement in the JSON must appear in the README and the Last generated timestamp must match (both must change together); (5) every model in the store appears in the README; (6) raw search snapshots must conform to data/search_contract.json. Inspect data/models.json, data/raw/*.json and README.md, fix what is rejected, regenerate README.md via scripts/update_trending.py. Do not remove any existing model. Do not push or merge. CONTRACT EVOLUTION: if validation fails because a raw snapshot now carries a new key/value that is REAL, recurring data (a new engine/backend/format/engagement field/top-level metadata) which would otherwise be lost, update data/search_contract.json and/or data/model_contract.json to declare it AND update the corresponding tests in the same change (per AGENTS.md rule 6b - the helpers in the test files carry the contract shape). Only widen the contract for real, traceable data; if the new key is a stray/empty/malformed one-off artifact, PRUNE it via self_correct_raw instead of widening the contract. Never invent a key to pass validation. CONTRACT VERSIONING: an ADDITIVE change (new key / new enum value / widened constraint that existing records still satisfy) edits the SAME contract file in place. A BREAKING change (removing/renaming a key, changing a type, removing an enum value that makes OLD data fail) must NOT edit the existing file - create a NEW versioned contract data/search_contract.v2.json or data/model_contract.v2.json (and so on for v3, v4, ...) that declares the new shape, and keep the old file untouched so old snapshots still validate against it. Update the validator (scripts/validate.py) and the tests to pick the right contract per data set: old raw snapshots / old models.json validate against the old contract, new ones against the new. The generated_utc timestamp (or a contract_version field) is what routes a snapshot to the correct contract version. LINK REPAIR (when validation reports a dead/wrong link): the CI link validator (scripts/validate.py check_links_resolve) only reports which link failed - it does NOT call the LLM. YOU are the fixer. For each failing link, SEARCH for the correct one and validate it before writing: (a) for a model/format Hugging Face link, use the Hugging Face CLI / huggingface_hub (e.g. hf search models <name> or the HF API) to find the canonical repo id, then confirm https://huggingface.co/<id> resolves; (b) for an engine/inference-server link, do a regular Firecrawl web search (FIRECRAWL_API_KEY) for the engines canonical repo URL and confirm it resolves. Only write a corrected link you have actually verified resolves. If you cannot find a verified replacement, leave the link and report it in the PR body for manual review - never invent a URL. Update data/models.json (and the raw snapshot if the wrong link came from data/raw/*.json), then regenerate README.md." \
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
	python3 scripts/validate.py --only data,schema,mapping
	python3 tests/test_mapping.py && python3 tests/test_validate.py && python3 tests/test_aggregate_recovery.py && python3 tests/test_7day_aggregation.py && python3 tests/test_fixture_mapping.py && python3 tests/test_validate_links.py && python3 tests/test_engagement_contract.py

.PHONY: _test
_test:
	python3 -m pytest tests/ -q 2>/dev/null || (python3 tests/test_mapping.py && python3 tests/test_validate.py && python3 tests/test_validate_readme.py && python3 tests/test_ingest_render.py && python3 tests/test_make_commands.py && python3 tests/test_hermes_update_needed.py && python3 tests/test_aggregate_recovery.py && python3 tests/test_7day_aggregation.py && python3 tests/test_fixture_mapping.py && python3 tests/test_validate_links.py && python3 tests/test_smoke_search.py && python3 tests/test_hermes_prompts.py && python3 tests/test_engagement_contract.py && python3 tests/test_fix_loop.py && python3 tests/test_workflows.py && python3 tests/test_readme_render.py && python3 tests/test_post_signal.py)


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

.PHONY: search
search:
	$(DOCKER_RUN) sh -c "make _setup && make _search"

.PHONY: search-smoke
search-smoke:
	$(DOCKER_RUN) make _search-smoke $(if $(BACKEND),BACKEND=$(BACKEND),)

.PHONY: hermes-smoke
hermes-smoke:
	$(DOCKER_RUN) sh -c "make _setup >/dev/null && make _hermes-smoke"

# Live pipeline smoke: real Firecrawl->lightbrd scrape for every nvidia/metal/
# cpu query (3s cap each) + a real Hermes call through the search alias.
.PHONY: pipeline-smoke
pipeline-smoke: search-smoke hermes-smoke

.PHONY: correct-raw
correct-raw:
	$(DOCKER_RUN) make _correct-raw

.PHONY: fix
fix:
	$(DOCKER_RUN) sh -c "make _setup && make _correct-raw && make _fix && make _merge"

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
