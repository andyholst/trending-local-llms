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
	-e NOUS_API_KEY -e FIRECRAWL_API_KEY $(IMAGE)

HERMES_MODEL := deepseek/deepseek-v4-flash-0731
NOUS_BASE   := https://inference-api.nousresearch.com/v1
# Raise the per-reply output cap. The deepseek model was truncating its reply
# mid-search (hit the default max_tokens), dropping the incomplete action and
# failing `make refresh`. At 8000 the heavier Metal/General searches still
# truncated mid-payload; 16000 gives headroom (the model card supports up to
# 384K output). Input context is also raised to the model's 1M-token ceiling
# (model card: 1M input / 384K output) so a long AGENTS.md + skill + mirrors
# page is never squeezed. One variable each so CI + local runs agree.
HERMES_MAX_TOKENS    := 16000
HERMES_CONTEXT_WINDOW := 1048576


## ---------------------------------------------------------------------------
## Build the image (do this once; CI does it in its own cached step)
## ---------------------------------------------------------------------------

.PHONY: docker-build
docker-build:
	docker build -t $(IMAGE) .

## ---------------------------------------------------------------------------
## Internal recipes (host commands) — wrapped by the docker public targets
## ---------------------------------------------------------------------------

.PHONY: _setup
_setup:
	@if command -v hermes >/dev/null 2>&1; then \
		echo "== hermes present; updating =="; \
		hermes update 2>/dev/null || echo "(update skipped; using existing)"; \
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
	hermes -z "Load AGENTS.md for rules. Fetch X trending posts from lightbrd.com using the Firecrawl scrape API: POST https://api.firecrawl.dev/v1/scrape with header 'Authorization: Bearer \$${FIRECRAWL_API_KEY}' and body {\"url\":\"https://lightbrd.com/search?f=tweets&q=<urlencoded>\",\"formats\":[\"markdown\"]}. Search with NVIDIA keywords ONLY (rtx tokens per second llm, rtx 3090/4090/5090 tokens per second, bonsai 2 ternary, freetoken gpu, dflash speculative), one query at a time, last-3-day. Rank by interactions then t/s; record engine + model. Write the captured models to data/raw/nvidia-<UTC>.json using:  python3 scripts/update_trending.py --write-raw nvidia < payload.json. Never remove a model. Do not merge or push." \
		-m nous-deepseek --yolo

.PHONY: _search-metal
_search-metal:
	hermes -z "Load AGENTS.md for rules. Fetch X trending posts from lightbrd.com using the Firecrawl scrape API: POST https://api.firecrawl.dev/v1/scrape with header 'Authorization: Bearer \$${FIRECRAWL_API_KEY}' and body {\"url\":\"https://lightbrd.com/search?f=tweets&q=<urlencoded>\",\"formats\":[\"markdown\"]}. Search with Apple/Metal keywords ONLY (mlx tokens per second, mlx apple silicon, mac m4 mlx local llm, mlxfast bonsai, tensorfold dflash mlx), one query at a time, last-3-day. Rank by interactions then t/s; record engine + model. Write the captured models to data/raw/metal-<UTC>.json using:  python3 scripts/update_trending.py --write-raw metal < payload.json. Never remove a model. Do not merge or push." \
		-m nous-deepseek --yolo

.PHONY: _search-cpu
_search-cpu:
	hermes -z "Load AGENTS.md for rules. Fetch X trending posts from lightbrd.com using the Firecrawl scrape API: POST https://api.firecrawl.dev/v1/scrape with header 'Authorization: Bearer \$${FIRECRAWL_API_KEY}' and body {\"url\":\"https://lightbrd.com/search?f=tweets&q=<urlencoded>\",\"formats\":[\"markdown\"]}. Search with CPU/embedded/edge keywords ONLY (llm tokens per second no gpu cpu, llama.cpp cpu only, raspberry pi llm tokens per second, local llm cpu), one query at a time, last-3-day. Rank by interactions then t/s; record engine + model. Write the captured models to data/raw/cpu-<UTC>.json using:  python3 scripts/update_trending.py --write-raw cpu < payload.json. Never remove a model. Do not merge or push." \
		-m nous-deepseek --yolo

.PHONY: _search-general
_search-general:
	hermes -z "Load AGENTS.md for rules. Fetch X trending posts from lightbrd.com using the Firecrawl scrape API: POST https://api.firecrawl.dev/v1/scrape with header 'Authorization: Bearer \$${FIRECRAWL_API_KEY}' and body {\"url\":\"https://lightbrd.com/search?f=tweets&q=<urlencoded>\",\"formats\":[\"markdown\"]}. Search with GENERAL t/s keywords (tokens per second llm, tokens per second benchmark llm, local llm tokens per second gpu, open weight llm benchmark gpu), one query at a time, last-3-day. Rank by interactions then t/s; record engine + model. Write the captured models to data/raw/general-<UTC>.json using:  python3 scripts/update_trending.py --write-raw general < payload.json. Never remove a model. Do not merge or push." \
		-m nous-deepseek --yolo

.PHONY: _search
_search:
	@echo "== running 4 searches in parallel (each writes its own data/raw/<backend>-<UTC>.json) =="
	@make -j4 _search-nvidia _search-metal _search-cpu _search-general

.PHONY: _correct-raw
_correct-raw:
	python3 scripts/self_correct_raw.py

.PHONY: _fix
_fix:
	hermes -z "The CI validation for the trending-local-llms PR failed. Load AGENTS.md for the acceptance criteria and fix the data so validation passes. The validation (scripts/validate.py) requires ALL of: (1) no model removed vs the previous snapshot; (2) every model has name/full_name/HF link/license/params/VRAM tier + at least one engine measurement with engine name + t/s + repo link; (3) each backend table (CUDA, Metal, CPU) sorted by highest t/s descending; (4) README in sync with data/models.json - every model and engine measurement in the JSON must appear in the README and the 'Last generated' timestamp must match (both must change together); (5) every model in the store appears in the README; (6) raw search snapshots must conform to data/search_contract.json. Inspect data/models.json, data/raw/*.json and README.md, fix what is rejected, regenerate README.md via scripts/update_trending.py. Do not remove any existing model. Do not push or merge." \
		-m nous-deepseek --yolo
	python3 scripts/update_trending.py  # merge corrected raw -> models.json

.PHONY: _merge
_merge:
	python3 scripts/update_trending.py

.PHONY: _validate
_validate:
	python3 scripts/validate.py

.PHONY: _validate-data
_validate-data:
	python3 scripts/validate.py --only data,removal

.PHONY: _validate-schema
_validate-schema:
	python3 scripts/validate.py --only schema

.PHONY: _validate-search
_validate-search:
	python3 scripts/validate.py --only search,mapping
	python3 tests/test_mapping.py && python3 tests/test_validate.py && python3 tests/test_validate_readme.py && python3 tests/test_ingest_render.py
	python3 scripts/self_correct_raw.py

.PHONY: _validate-readme
_validate-readme:
	python3 scripts/validate.py --only readme

.PHONY: _validate-mapped
_validate-mapped:
	python3 scripts/validate.py --only data,schema,mapping
	python3 tests/test_mapping.py && python3 tests/test_validate.py

.PHONY: _test
_test:
	python3 -m pytest tests/ -q 2>/dev/null || (python3 tests/test_mapping.py && python3 tests/test_validate.py && python3 tests/test_validate_readme.py && python3 tests/test_ingest_render.py && python3 tests/test_make_commands.py)

.PHONY: _requirements
_requirements:
	pip install --quiet pip-tools
	pip-compile --quiet --output-file requirements.txt requirements.in
	@echo "== regenerated requirements.txt from requirements.in =="

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

.PHONY: search-general
search-general:
	$(DOCKER_RUN) sh -c "make _setup && make _search-general"

.PHONY: search
search:
	$(DOCKER_RUN) sh -c "make _setup && make _search"

.PHONY: correct-raw
correct-raw:
	$(DOCKER_RUN) make _correct-raw

.PHONY: fix
fix:
	$(DOCKER_RUN) sh -c "make _setup && make _correct-raw && make _fix && make _merge"

.PHONY: merge
merge:
	$(DOCKER_RUN) make _merge

.PHONY: validate
validate:
	$(DOCKER_RUN) make _validate

.PHONY: validate-data
validate-data:
	$(DOCKER_RUN) make _validate-data

.PHONY: validate-schema
validate-schema:
	$(DOCKER_RUN) make _validate-schema

.PHONY: validate-search
validate-search:
	$(DOCKER_RUN) make _validate-search

.PHONY: validate-readme
validate-readme:
	$(DOCKER_RUN) make _validate-readme

.PHONY: validate-mapped
validate-mapped:
	$(DOCKER_RUN) make _validate-mapped

.PHONY: test
test:
	$(DOCKER_RUN) make _test

.PHONY: requirements
requirements:
	$(DOCKER_RUN) make _requirements

.PHONY: refresh
refresh:
	$(DOCKER_RUN) make _refresh

.PHONY: all
all: refresh
