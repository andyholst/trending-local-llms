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
# A git WORKTREE's gitdir lives OUTSIDE $PWD, so a container mounting only the
# worktree cannot answer `git ls-files` (measured: `fatal: not a git repository:
# .../worktrees/<name>` — it made the trailing-newline lint test red in a worktree
# and green in a clone). Mount the common git dir at its host path so the
# in-container suite sees exactly the tracked-file set the host does. Empty (no
# extra mount) when the directory is not a git checkout at all.
GIT_COMMON_DIR := $(shell cd "$$(git rev-parse --git-common-dir 2>/dev/null)" 2>/dev/null && pwd)
TEST_RUN := docker run --rm -v "$$PWD":/workspace $(if $(GIT_COMMON_DIR),-v "$(GIT_COMMON_DIR):$(GIT_COMMON_DIR)",) -w /workspace \
	-e NOUS_API_KEY -e FIRECRAWL_API_KEY -e HF_TOKEN -e $(NERVE_KEY_ENV) $(TEST_IMAGE)


HERMES_MODEL := deepseek/deepseek-v4.1-flash
NOUS_BASE   := https://inference-api.nousresearch.com/v1
# The ONE name of the model alias every hermes call passes with `-m` (issue #207):
# `_setup` writes `model.aliases.$(HERMES_ALIAS).*` and `_hermes-alias-check` reads
# the same name back, so the two can never drift.
HERMES_ALIAS := nous-deepseek
# The Hermes install pin, used by the ONE installer seam
# (`scripts/install_hermes_ci.sh`) that both `make _setup` and the image build go
# through. Override on the command line to point at a mirror or a pinned release:
#   make setup HERMES_INSTALL_URL=https://…/install.sh
# `tests/test_install_hermes_ci.py` asserts these defaults match the Dockerfile's
# ARG defaults, so the image and the host path install from the same place.
HERMES_INSTALL_URL ?= https://hermes-agent.nousresearch.com/install.sh
HERMES_PACKAGE     ?= hermes-agent
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
# The model-dimension ask (issue #167): ONE definition, used by every search leg.
# Four byte-identical copies could drift; a test keeps the legs on this string.
# No double quotes and no $ inside: it is embedded in each leg's `hermes -z "…"`.
DIM_ASK := MODEL DIMENSIONS - before writing each model, check the post for these five and record every one it STATES: RAM / unified memory -> system_ram_min (e.g. 16GB); model weight footprint -> weight_gb (e.g. 5.95GB Q4_K_M); context window -> context_tokens (e.g. 131072 or 128K); experts streamed from storage -> storage_offload (e.g. 640GB NVMe); minimum engine build or flags -> engine_min_version (e.g. b6xxx, --n-gpu-layers 99). A figure the post names belongs in its field, NOT only in the prose/why text. Copy only a figure the post gives: never guess, derive or invent one.

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

# ---- the agent image: publishing is a deliberate, guarded act (issue #206) ----
# The base image IS the agent image — it bakes the Hermes CLI and the pinned nerve
# plugin, and every bot job runs inside it — so publishing it is privileged, not a
# side effect of a data refresh. `.github/workflows/publish-agent-image.yml` runs
# these three, in this order: the owner/collaborator guard, the push probe, the
# publish. Publishing is what makes the hash tag exist, so every later `image-ensure`
# PULLS the toolchain instead of rebuilding it (measured on #220: a PR that did not
# touch the Dockerfile still paid a nine-minute build).
agent-image-ref: ## Print the GHCR refs of the agent image for this revision's Dockerfile
	python3 scripts/ensure_image.py ref

agent-image-push-check: ## CI: prove the ambient credential can PUSH the agent image, before the build
	python3 scripts/ensure_image.py push-check

publish-agent-image: ## Build + push the agent image when its hash tag is absent (FORCE=1 rebuilds the same inputs)
	python3 scripts/ensure_image.py publish $(if $(FORCE),--force,)

# ---- the rebuild decision, as data (issue #208) ------------------------------
# `refresh-bot`'s `build` and `openspec-image` jobs read this instead of computing
# the rule inline. The day comes from HERE (`date +%u`, one call site in the repo),
# the published-tag probes go through the same `docker` seam the tests fake, and
# `scripts/ensure_image.py decide` owns the rule — so every branch is tested
# instead of being observable only by running the pipeline (#135, #141).
# `FORCE` is parsed strictly in the script: FORCE=0/false means OFF.
rebuild-decision: ## Print built/test_built/publish_openspec + tags + reasons (FORCE=<bool>, DOW=<1-7>)
	@python3 scripts/ensure_image.py decide --force "$(if $(FORCE),$(FORCE),false)" --dow "$(if $(DOW),$(DOW),$$(date +%u))"

# ---- OpenSpec (spec-driven change tracking; Dockerized CLI) ------------------
# Every change is a TRACKED change: openspec/changes/<name>/ holds proposal.md,
# specs/<capability>/spec.md and tasks.md, created BEFORE the code is written and
# validated before the PR. `OPENSPEC.md` at the root is the generated index of
# every change (active + archived) — the one file that references them all.
#
# The CLI runs in its own image (openspec/Dockerfile), pulled by content hash or
# built here: ONE code path, identical locally and in CI, no host npm install
# (AGENTS.md: no fallback implementations).
OPENSPEC_VERSION := 1.10.0
OPENSPEC_IMAGE := trending-local-llms-openspec:latest
# Runs as the invoking user, so the change dirs the CLI creates are owned by the
# repo's owner and not by root (measured: `openspec new change` as root left a
# root-owned change directory the working tree could not write to).
OS_OPTS := --rm --user $$(id -u):$$(id -g) -e HOME=/tmp -v "$$PWD":/repo:rw -w /repo $(OPENSPEC_IMAGE)

.PHONY: openspec-image openspec-new openspec-validate openspec-status openspec-archive openspec-shell openspec-tasks-check openspec-index openspec-index-check openspec-check file-findings findings-check
openspec-image: ## Ensure the OpenSpec CLI image (pull the published hash tag, else build it)
	python3 scripts/ensure_image.py ensure-openspec

openspec-new: openspec-image ## openspec new change <NAME>
	@test -n "$(NAME)" || { echo "Usage: make openspec-new NAME=<kebab-name>"; exit 1; }
	docker run $(OS_OPTS) openspec new change $(NAME)

openspec-validate: openspec-image ## openspec validate <NAME> (fail-closed gate)
	@test -n "$(NAME)" || { echo "Usage: make openspec-validate NAME=<change>"; exit 1; }
	docker run $(OS_OPTS) openspec validate $(NAME)

openspec-status: openspec-image ## openspec status (every change and its progress)
	docker run $(OS_OPTS) openspec status

openspec-archive: openspec-image ## Move a completed change to openspec/changes/archive/<NAME>
	@test -n "$(NAME)" || { echo "Usage: make openspec-archive NAME=<change>"; exit 1; }
	docker run $(OS_OPTS) openspec archive $(NAME) -y

openspec-shell: openspec-image ## Interactive shell into the repo with the openspec CLI
	docker run --rm -it -v "$$PWD":/repo:rw -w /repo $(OPENSPEC_IMAGE) /bin/sh

openspec-tasks-check: ## Fail when an ACTIVE change still has an unticked `- [ ]` task (NAME=<change> for one)
	python3 scripts/check_openspec_tasks.py $(NAME)

openspec-index: ## Regenerate the root OPENSPEC.md index from openspec/changes/**
	python3 scripts/openspec_index.py --write

openspec-index-check: ## Fail when OPENSPEC.md is stale, or a change on disk has no row
	python3 scripts/openspec_index.py --check

openspec-check: openspec-image openspec-tasks-check openspec-index-check ## CI gate: every active change validates, every task ticked, the index current
	docker run $(OS_OPTS) openspec validate --changes
	@echo "[openspec-check] OK: active changes validate, their tasks are ticked, OPENSPEC.md is current"

file-findings: ## File ONE issue per finding in findings.md (host-side: needs gh + the repo)
	python3 scripts/file_findings.py --file $(if $(PR),--pr $(PR)) $(if $(ISSUE),--issue $(ISSUE))

findings-check: ## Fail when findings.md is missing or a finding lacks evidence / why / done-when
	python3 scripts/file_findings.py --check

architecture-check: ## Fail when ARCHITECTURE.md misses a make target, a workflow or a script (rule 6h)
	python3 scripts/architecture_check.py

# ---- linefeeds: every tracked text file ends with a newline (issue #186) -----
# A file without a final newline makes git print `\ No newline at end of file`
# and turns the next append into a spurious last-line change. `make lint` is the
# gate (a `qa-validate` step, the first check in the fix loop), `make lint-fix`
# the repair. Pure python, so host and container agree.
.PHONY: lint lint-fix
lint: ## Fail when a tracked text file does not end with a newline
	python3 scripts/lint_linefeeds.py

lint-fix: ## Append the missing final newline to every tracked text file that lacks one
	python3 scripts/lint_linefeeds.py --fix

## ---------------------------------------------------------------------------
## Internal recipes (host commands) — wrapped by the docker public targets
## ---------------------------------------------------------------------------

.PHONY: _setup
_setup:
	@# ONE installer path (issue #207): the same seam the image build runs —
	@# already installed -> HERMES_INSTALL_URL -> `uv tool install`, else FAIL
	@# loudly. There is no second, curl-pipe-bash implementation to drift from it.
	@HERMES_INSTALL_URL=$(HERMES_INSTALL_URL) HERMES_PACKAGE=$(HERMES_PACKAGE) \
		scripts/install_hermes_ci.sh
	hermes --version
	hermes config set model.aliases.$(HERMES_ALIAS).model $(HERMES_MODEL)
	hermes config set model.aliases.$(HERMES_ALIAS).provider custom
	hermes config set model.aliases.$(HERMES_ALIAS).base_url $(NOUS_BASE)
	hermes config set model.aliases.$(HERMES_ALIAS).key_env NOUS_API_KEY
	hermes config set model.aliases.$(HERMES_ALIAS).max_tokens $(HERMES_MAX_TOKENS)
	hermes config set model.aliases.$(HERMES_ALIAS).context_window $(HERMES_CONTEXT_WINDOW)
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

# Prove the image carries the agent it claims to carry (issue #207). `_setup` is
# the ONE writer of the alias — from HERMES_ALIAS / HERMES_MODEL / NOUS_BASE, the
# same variables this check reads — and the IMAGE BUILD runs this right after it,
# so a wrong model pin, a provider that is not `custom` or a `key_env` that is not
# NOUS_API_KEY fails the BUILD instead of a bot run (measured on #124: with no
# alias Hermes auto-routed to HF_TOKEN and died with `HTTP 403`).
# It reports EVERY mismatch, not just the first, and never prints a credential.
.PHONY: _hermes-alias-check
_hermes-alias-check:
	@fail=0; \
	for want in "model=$(HERMES_MODEL)" "provider=custom" "base_url=$(NOUS_BASE)" \
	            "key_env=NOUS_API_KEY" "max_tokens=$(HERMES_MAX_TOKENS)" \
	            "context_window=$(HERMES_CONTEXT_WINDOW)"; do \
		key="$${want%%=*}"; expect="$${want#*=}"; \
		got="$$(hermes config get "model.aliases.$(HERMES_ALIAS).$$key" 2>/dev/null || true)"; \
		if [ "$$got" = "$$expect" ]; then \
			echo "[hermes-alias] ok: $(HERMES_ALIAS).$$key = $$got"; \
		else \
			echo "[hermes-alias] FAIL: $(HERMES_ALIAS).$$key is '$${got:-<unset>}', expected '$$expect'"; \
			fail=1; \
		fi; \
	done; \
	if [ "$$fail" != "0" ]; then \
		echo "[hermes-alias] the image does not carry the alias the bots call with -m $(HERMES_ALIAS) — refusing"; \
		exit 1; \
	fi; \
	echo "[hermes-alias] OK: alias $(HERMES_ALIAS) matches the Makefile pin (the key itself arrives at run time)"

.PHONY: _search-nvidia
_search-nvidia:
	hermes -z "Load AGENTS.md for rules. Fetch X trending posts from lightbrd.com using the Firecrawl scrape API: POST https://api.firecrawl.dev/v1/scrape with header 'Authorization: Bearer \$${FI...KEY}' and body {\"url\":\"https://lightbrd.com/search?f=tweets&q=<urlencoded>\",\"formats\":[\"markdown\"]}. Search with NVIDIA keywords ONLY (rtx tokens per second llm, rtx 3090/4090/5090 tokens per second, bonsai 2 ternary, freetoken gpu, dflash speculative), one query at a time, last-3-day. Rank by interactions then t/s; record engine + model. Write tps as a CLEAN number with NO embedded text/comments (move context like 'DFlash spec-decode' into quant/hardware); record each post's likes/comments/reshares/views on the engine measurement. Set source_post to the exact post URL https://lightbrd.com/<user>/status/<id> - never the bare mirror URL or a profile page - and copy that post's likes, comments, reshares and views as integers onto the same measurement. If the post runs a fork or custom build of an engine (for example the PrismML llama.cpp fork that Ternary Bonsai 2 requires), record the engine exactly as that fork is named in the engines registry of data/models.json. Use engine names exactly as registered in data/models.json. An engine is an inference runtime or server that loads the weights (llama.cpp, MLX, vLLM, Ollama ...); harnesses, agent frameworks, plugins, chat apps, UIs and benchmarks are NOT engines - if a post only names one of those, record the runtime it uses instead, or skip the measurement. For an engine that is not registered yet, add engine_repo = its https://github.com/<owner>/<repo> URL as given in or linked from the post; if the post names the engine but links no repo, run ONE Firecrawl web search for the engine name plus github and record the repo only when its name matches the engine and the page resolves; never invent or guess a URL. After EACH query, immediately write only that query's captured models: python3 scripts/update_trending.py --write-raw nvidia < payload.json (each call writes its own data/raw/nvidia-<UTC>.json) - never collect all queries into one big payload, a reply has a 65536-token cap. $(DIM_ASK) Never remove a model. Do not merge or push." \
		-m nous-deepseek --reasoning $(HERMES_REASONING) --yolo

.PHONY: _search-metal
_search-metal:
	hermes -z "Load AGENTS.md for rules. Fetch X trending posts from lightbrd.com using the Firecrawl scrape API: POST https://api.firecrawl.dev/v1/scrape with header 'Authorization: Bearer \$${FI...KEY}' and body {\"url\":\"https://lightbrd.com/search?f=tweets&q=<urlencoded>\",\"formats\":[\"markdown\"]}. Search with Apple/Metal keywords ONLY (mlx tokens per second, mlx apple silicon, mac m4 mlx local llm, mlxfast bonsai, tensorfold dflash mlx), one query at a time, last-3-day. Rank by interactions then t/s; record engine + model. Write tps as a CLEAN number with NO embedded text/comments (move context like 'DFlash spec-decode' into quant/hardware); record each post's likes/comments/reshares/views on the engine measurement. Set source_post to the exact post URL https://lightbrd.com/<user>/status/<id> - never the bare mirror URL or a profile page - and copy that post's likes, comments, reshares and views as integers onto the same measurement. If the post runs a fork or custom build of an engine (for example the PrismML llama.cpp fork that Ternary Bonsai 2 requires), record the engine exactly as that fork is named in the engines registry of data/models.json. Use engine names exactly as registered in data/models.json. An engine is an inference runtime or server that loads the weights (llama.cpp, MLX, vLLM, Ollama ...); harnesses, agent frameworks, plugins, chat apps, UIs and benchmarks are NOT engines - if a post only names one of those, record the runtime it uses instead, or skip the measurement. For an engine that is not registered yet, add engine_repo = its https://github.com/<owner>/<repo> URL as given in or linked from the post; if the post names the engine but links no repo, run ONE Firecrawl web search for the engine name plus github and record the repo only when its name matches the engine and the page resolves; never invent or guess a URL. After EACH query, immediately write only that query's captured models: python3 scripts/update_trending.py --write-raw metal < payload.json (each call writes its own data/raw/metal-<UTC>.json) - never collect all queries into one big payload, a reply has a 65536-token cap. $(DIM_ASK) Never remove a model. Do not merge or push." \
		-m nous-deepseek --reasoning $(HERMES_REASONING) --yolo

.PHONY: _search-cpu
_search-cpu:
	hermes -z "Load AGENTS.md for rules. Fetch X trending posts from lightbrd.com using the Firecrawl scrape API: POST https://api.firecrawl.dev/v1/scrape with header 'Authorization: Bearer \$${FI...KEY}' and body {\"url\":\"https://lightbrd.com/search?f=tweets&q=<urlencoded>\",\"formats\":[\"markdown\"]}. Search with CPU/embedded/edge keywords ONLY (llm tokens per second no gpu cpu, llama.cpp cpu only, raspberry pi llm tokens per second, local llm cpu), one query at a time, last-3-day. Rank by interactions then t/s; record engine + model. Write tps as a CLEAN number with NO embedded text/comments (move context like 'DFlash spec-decode' into quant/hardware); record each post's likes/comments/reshares/views on the engine measurement. Set source_post to the exact post URL https://lightbrd.com/<user>/status/<id> - never the bare mirror URL or a profile page - and copy that post's likes, comments, reshares and views as integers onto the same measurement. If the post runs a fork or custom build of an engine (for example the PrismML llama.cpp fork that Ternary Bonsai 2 requires), record the engine exactly as that fork is named in the engines registry of data/models.json. Use engine names exactly as registered in data/models.json. An engine is an inference runtime or server that loads the weights (llama.cpp, MLX, vLLM, Ollama ...); harnesses, agent frameworks, plugins, chat apps, UIs and benchmarks are NOT engines - if a post only names one of those, record the runtime it uses instead, or skip the measurement. For an engine that is not registered yet, add engine_repo = its https://github.com/<owner>/<repo> URL as given in or linked from the post; if the post names the engine but links no repo, run ONE Firecrawl web search for the engine name plus github and record the repo only when its name matches the engine and the page resolves; never invent or guess a URL. After EACH query, immediately write only that query's captured models: python3 scripts/update_trending.py --write-raw cpu < payload.json (each call writes its own data/raw/cpu-<UTC>.json) - never collect all queries into one big payload, a reply has a 65536-token cap. $(DIM_ASK) Never remove a model. Do not merge or push." \
		-m nous-deepseek --reasoning $(HERMES_REASONING) --yolo

.PHONY: _search-amd
_search-amd:
	hermes -z "Load AGENTS.md for rules. Fetch X trending posts from lightbrd.com using the Firecrawl scrape API: POST https://api.firecrawl.dev/v1/scrape with header 'Authorization: Bearer \$${FI...KEY}' and body {\"url\":\"https://lightbrd.com/search?f=tweets&q=<urlencoded>\",\"formats\":[\"markdown\"]}. Search with AMD/ROCm keywords ONLY (rx 7900 xtx tokens per second, rx 9070 xt tokens per second, rocm tokens per second, llama.cpp vulkan amd tokens, strix halo tokens per second), one query at a time, last-3-day. AMD rules: record the AMD card exactly as posted in hardware (for example 'RX 7900 XTX 24GB', 'RX 9070 XT 16GB', 'Radeon 8060S / Strix Halo 128GB') - that is what puts the figure in the ROCm table; keep the engine name as registered (llama.cpp, Ollama, vLLM, SGLang, Strata ...) and put the API (ROCm, HIP, Vulkan) in quant, never in the engine name; record generation/decode t/s only, never prompt-processing or prefill t/s; skip datacenter Instinct (MI300/MI355) posts. Rank by interactions then t/s; record engine + model. Write tps as a CLEAN number with NO embedded text/comments (move context like 'DFlash spec-decode' into quant/hardware); record each post's likes/comments/reshares/views on the engine measurement. Set source_post to the exact post URL https://lightbrd.com/<user>/status/<id> - never the bare mirror URL or a profile page - and copy that post's likes, comments, reshares and views as integers onto the same measurement. If the post runs a fork or custom build of an engine (for example the PrismML llama.cpp fork that Ternary Bonsai 2 requires), record the engine exactly as that fork is named in the engines registry of data/models.json. Use engine names exactly as registered in data/models.json. An engine is an inference runtime or server that loads the weights (llama.cpp, MLX, vLLM, Ollama ...); harnesses, agent frameworks, plugins, chat apps, UIs and benchmarks are NOT engines - if a post only names one of those, record the runtime it uses instead, or skip the measurement. For an engine that is not registered yet, add engine_repo = its https://github.com/<owner>/<repo> URL as given in or linked from the post; if the post names the engine but links no repo, run ONE Firecrawl web search for the engine name plus github and record the repo only when its name matches the engine and the page resolves; never invent or guess a URL. After EACH query, immediately write only that query's captured models: python3 scripts/update_trending.py --write-raw amd < payload.json (each call writes its own data/raw/amd-<UTC>.json) - never collect all queries into one big payload, a reply has a 65536-token cap. $(DIM_ASK) Never remove a model. Do not merge or push." \
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
	python3 -m pytest tests/ -q 2>/dev/null || (python3 tests/test_mapping.py && python3 tests/test_validate.py && python3 tests/test_validate_readme.py && python3 tests/test_ingest_render.py && python3 tests/test_make_commands.py && python3 tests/test_hermes_update_needed.py && python3 tests/test_aggregate_recovery.py && python3 tests/test_7day_aggregation.py && python3 tests/test_fixture_mapping.py && python3 tests/test_validate_links.py && python3 tests/test_smoke_search.py && python3 tests/test_data_gap_analysis.py && python3 tests/test_secret_scan.py && python3 tests/test_hermes_prompts.py && python3 tests/test_engagement_contract.py && python3 tests/test_fix_loop.py && python3 tests/test_workflows.py && python3 tests/test_readme_render.py && python3 tests/test_post_signal.py && python3 tests/test_trend_score.py && python3 tests/test_engine_aliases.py && python3 tests/test_hermes_smoke.py && python3 tests/test_search_budget.py && python3 tests/test_engine_registry.py && python3 tests/test_amd_backend.py && python3 tests/test_nerve_key_wiring.py && python3 tests/test_qa_report.py && python3 tests/test_ensure_image.py && python3 tests/test_hf_id.py && python3 tests/test_check_openspec_tasks.py && python3 tests/test_openspec_index.py && python3 tests/test_file_findings.py && python3 tests/test_architecture.py && python3 tests/test_lint_linefeeds.py && python3 tests/test_secret_output.py && python3 tests/test_issue_review.py && python3 tests/test_install_hermes_ci.py && python3 tests/test_publish_agent_image.py && python3 tests/test_issue_triage.py)


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

# `hermes-alias-check`: run `_hermes-alias-check` against the image the bots use,
# on demand (the image build runs the same recipe, so a broken pin cannot be
# published even if nobody runs this).
.PHONY: hermes-alias-check
hermes-alias-check:
	$(DOCKER_RUN) sh -c "make _setup >/dev/null && make _hermes-alias-check"

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

.PHONY: data-gaps
data-gaps:
	$(TEST_RUN) make _data-gaps

# HOST-side on purpose (issue #150): filing needs the `gh` CLI + the repo, and
# the test image carries neither (measured: `command -v gh` -> not found, so the
# step died with FileNotFoundError: 'gh' and the whole refresh job went red with
# the data PR skipped). The script is stdlib-only, so the runner runs it as-is.
# `data-gaps` (the report) needs no `gh` and stays in the image — hence no
# internal `_data-gap-issue` wrapper here (rule 6d: no target without a caller).
.PHONY: data-gap-issue
data-gap-issue:
	python3 scripts/data_gap_analysis.py --issue

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

# The no-secret-VALUE guard (issue #219): gitleaks only catches a committed
# credential VALUE; this catches the run-time leak shapes — a printed value
# (`echo "$NOUS_API_KEY"`), a value on a command line (`-e KEY=$KEY`), a
# `${{ secrets.X }}` in a `run:` block, a `set -x` beside a key read, a bare
# `env` dump, a committed credential-shaped literal. Pure python + host
# filesystem scan, so host and container agree (like `make lint`).
.PHONY: check-secret-output secret-output-report
check-secret-output: ## CI: fail when any file prints a secret's VALUE, passes it on a command line, xtraces it, dumps the environment around it, or commits a credential-shaped literal
	python3 scripts/check_secret_output.py check
secret-output-report: ## Show which files name a secret-shaped variable, and whether any prints it
	python3 scripts/check_secret_output.py report

# ---- issue-bot: implement ONE filed data-gap issue (issue #113) --------------
# The issue's title + body are written to issue.md at the repo root by
# `.github/workflows/issue-bot.yml`; the agent reads it FIRST and implements
# exactly that issue, additive only, with everything wired to a make target.
.PHONY: _implement-issue
_implement-issue:
	hermes -z "Load AGENTS.md for rules. The issue you must implement is in issue.md at the repo root - read it FIRST and implement exactly its acceptance criteria; do not widen the scope and do not implement a different finding. FIRST, DECIDE (issue #210): issue.md carries the WHOLE thread (body + every comment with author and timestamp + a decision instruction), and the comments are part of the specification, so write your verdict to triage.md BEFORE anything else - 'TRIAGE: implement' when the thread matches the body; 'TRIAGE: refine' plus 'REFINED: <the restatement that WOULD be implementable, with acceptance criteria and the scope boundary>' when it cannot be implemented as written; or 'TRIAGE: close' plus 'EVIDENCE: <a file:line, a command with its output, or a measured behaviour>' and 'REASON: <why that proves it is obsolete, a duplicate or already fixed>' when it should not be implemented at all. A refine or a close means you implement NOTHING, change NO code and open NO PR - the workflow applies your verdict (one comment, a label, or a close) - and a close with no EVIDENCE block is REFUSED so the run fails. ONLY 'TRIAGE: implement' continues to the rules below.  HARD RULES: (0) OPENSPEC FIRST, and it is the checklist of record: create the tracked change with make openspec-new NAME=<kebab-slug-of-this-issue> BEFORE you write any code, then write openspec/changes/<name>/proposal.md (Why / What Changes / what is Not covered), openspec/changes/<name>/specs/<capability>/spec.md (one Requirement per behaviour, each Scenario in Given/When/Then lines and each Scenario ending with a '- **Test:** tests/test_x.py::test_y' line naming the test that locks it) and openspec/changes/<name>/tasks.md (a - [ ] checklist, one task per implemented step). Tick each task the moment it is verified. The change must also list itself in the root index: run make openspec-index at the end. make openspec-check must pass before you finish. (1) ADDITIVE ONLY - never remove or rename an existing key and never shrink an existing value in data/models.json, data/raw/*.json, data/snapshots/*.json or the contracts; a new key is OPTIONAL and must NOT be added to a contract's required list (AGENTS.md rules 3b and 6b). (2) NEVER fabricate data: every value must trace to a real X post or to a verified upstream source, or be marked (est); if you cannot verify it, leave the key unset and say so in your summary. (3) WIRE EVERYTHING: any script, subcommand or validator check you add must be reachable from a make target CI runs - bundle it into an existing stage or add an internal _name recipe plus its public wrapper (AGENTS.md rule 6d) - and update that stage's tests in the same change (rule 6b). (4) If the data changed, regenerate README.md with python3 scripts/update_trending.py; if a stage or guard changed, update AGENTS.md including its section 8 row; if you add, rename or remove a make target, a pipeline job, an image or a script, you MUST update ARCHITECTURE.md in the same change (rule 6h) - the description of the Makefile, the pipelines and the images is part of the change. (5) Edit the files themselves - NEVER add scratch artifacts: no *.patch, no *.rej, no report dumps, no backup copies; a change written into a patch file instead of the file is not an implementation. findings.md is the ONE working file you write (it is gitignored). (6) ANALYSIS SHIPS ISSUES, NEVER CODE: after implementing, write findings.md at the repo root with one '## <title>' section per real gap or piece of technical debt you found while working (each with Evidence: file:line or command output, Why, Done when), or the single line '- none' when you genuinely found nothing; NEVER fix a finding in this change and never fold one into it - each becomes its own tracked issue. Run make findings-check (it must pass). (7) ONLY when the verdict is 'TRIAGE: implement': run make validate, make validate-mapped, make test, make openspec-check and make architecture-check and fix what they report. Do not push, do not merge, do not touch master." \
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

# ---- the implementer's queue + the issue reviewer (issue #179) ----------------
# TWO bots share ONE queue of `data-gap-analysis` issues: `issue-bot` implements
# one per hour (oldest first), the issue reviewer refines the ones nobody has
# started. They must never write the same issue at once, so the reviewer keeps a
# quiet window around an implementer start — REVIEW_GAP_HOURS before the sweep
# reaches the issue and the same gap after it started. ONE constant, read by both
# bots through ONE queue implementation (scripts/issue_queue.py, rule 6d):
# `issue-bot`'s pick runs `make issue-queue` instead of keeping its own copy of
# the rule in shell.
REVIEW_GAP_HOURS := 3

.PHONY: issue-queue
issue-queue: ## Print the implementer's queue (oldest first) with each issue's window and its reviewer verdict hold
	python3 scripts/issue_queue.py --gap-hours $(REVIEW_GAP_HOURS)

# The reviewer's VERDICT is a hold, not advice (issue #200): while a verdict label
# (`needs-refinement`, and the obsolete/duplicate/already-fixed family) is FRESH —
# younger than VERDICT_TTL_HOURS, measured from the reviewer's newest marker
# comment, because a label carries no timestamp — the sweep takes another issue,
# and this target says so ON the held issue (one comment per review round). A
# comment, never a label: the verdict belongs to the reviewer or a human.
issue-skip-note: ## Say on the held issue why the sweep skipped it (one comment per review round)
	python3 scripts/issue_queue.py --skip-note --gap-hours $(REVIEW_GAP_HOURS)

# The implementer's TRIAGE verdict, applied DETERMINISTICALLY (issue #210): the
# implementer reads the whole thread and writes triage.md; this is the only thing
# that acts on it — `implement` does nothing (the run continues to its PR),
# `refine` posts ONE restatement + `agent:refined`, `close` posts the reason with
# its cited EVIDENCE, closes the issue and applies `agent:closed`. A close with no
# EVIDENCE, a refine with no restatement, and an unknown verdict all exit 2.
# The sweep skips a decided issue through the SHARED queue rule (#210), never a
# second copy in shell.
issue-verdict: ## Apply the implementer's TRIAGE verdict from triage.md (ISSUE=<n>, TRIAGE_FILE=<path>)
	python3 scripts/issue_verdict.py $(if $(ISSUE),--issue $(ISSUE),) $(if $(TRIAGE_FILE),--file $(TRIAGE_FILE),)

# The implementer's INPUT (issue #210): the WHOLE thread — title, body, every
# comment oldest-first with author and ISO8601Z, then the decision instruction the
# verdict answers. The reviewer was already told to read the whole thread; the
# implementer read only the body, so an issue whose fifth comment narrowed the
# request was implemented wrongly.
issue-thread: ## Print an issue's whole thread for the implementer (ISSUE=<n>, REPO=<owner/name>)
	python3 scripts/issue_thread.py $(if $(ISSUE),--issue $(ISSUE),) $(if $(REPO),--repo $(REPO),)

.PHONY: review-issue-pick
review-issue-pick: ## Choose the ONE issue this review run works (action=/issue=/path=)
	python3 scripts/issue_review.py --pick --gap-hours $(REVIEW_GAP_HOURS) $(if $(RUN),--run $(RUN),)

# Open the reviewer's window BEFORE anything is written: the `review-in-progress`
# label is what `issue-bot`'s pick defers to, and (body path) one marker comment
# `<!-- issue-review: <ISO8601Z> -->` records the instant for the next run.
.PHONY: review-issue-mark
review-issue-mark: ## Open the reviewer's window on ISSUE= (PATH=body|window)
	python3 scripts/issue_review.py --mark $(ISSUE) --path $(PATH) $(if $(RUN),--run $(RUN),)

# The TOCTOU re-check, run after the mark and BEFORE the write: the implementer
# may have started while the review was being prepared, in which case the body
# must not be touched (`PATH=window` re-checks the reply path instead).
.PHONY: review-issue-guard
review-issue-guard: ## Re-check that ISSUE= may still be written (PATH=body|window)
	python3 scripts/issue_review.py --guard $(ISSUE) --for $(PATH) --gap-hours $(REVIEW_GAP_HOURS) $(if $(RUN),--run $(RUN),)

.PHONY: review-issue-body-hash
review-issue-body-hash: ## Print the body hash of ISSUE= (proves the window path edited nothing)
	python3 scripts/issue_review.py --body-hash $(ISSUE)

.PHONY: review-issue-check-markers
review-issue-check-markers: ## Fail when FILE= dropped an invisible marker from ISSUE='s body
	python3 scripts/issue_review.py --check-markers $(ISSUE) --file $(if $(FILE),$(FILE),issue-body.md)

.PHONY: review-issue-finish
review-issue-finish: ## Close the reviewer's window on ISSUE=
	python3 scripts/issue_review.py --finish $(ISSUE)

# The reviewer's judgement, in the container like every other hermes call. The
# issue (body + comments) is written to issue.md by the workflow; the agent
# writes the REWRITTEN body to issue-body.md and its one summary comment to
# comment.md - the workflow does the `gh` write, so no token ever reaches the
# container.
.PHONY: _review-issue
_review-issue:
	hermes -z "Load AGENTS.md for rules. You are the ISSUE REVIEWER (issue #179), NOT an implementer. The issue you must review is #$(ISSUE); its current body and its comments are in issue.md at the repo root - read it FIRST and review the WHOLE thread, not just the body. Your job: make this issue implementable by the implementer bot, or say what it is. HARD RULES: (1) NEVER implement or fix the issue - no change to data/, scripts/, the Makefile, the workflows or any code; you refine an issue, you never write the fix, and you never open a PR or a branch. (2) NEVER remove or edit an invisible HTML comment in the body: keep every data-gap-signature, tech-debt-signature, issue-bot-start and issue-review marker byte-identical - they are the dedup keys other bots search for, and dropping one re-files an issue that already exists (measured on #184/#185). (3) THE BODY IS THE DELIVERABLE: write the COMPLETE refined body to issue-body.md at the repo root - the missing acceptance criteria, the scope boundary, the evidence (file:line, a command, measured behaviour) and a Not-covered section. Keep the author intent and wording; add, do not rewrite for style. If the issue is already implementable, write the body UNCHANGED (byte-identical) - that is the honest no-change-needed and the workflow will only comment. (4) You have NO gh CLI and NO network write in this container: do not run gh, do not comment, do not close, do not edit any label - the WORKFLOW publishes your issue-body.md and your comment.md and clears the needs-refinement label when the refinement lands. Never touch the labels tech-debt or data-gap-analysis (the chains key on them) and never remove a label a human added. (5) Write your ONE summary comment to comment.md: what you changed and why, or what is obsolete and the evidence for it, or no-change-needed and the reason. Never close the issue yourself. (6) ANALYSIS SHIPS ISSUES: write findings.md at the repo root with one section per real gap or piece of technical debt you noticed while reviewing (each with Evidence: file:line or a command, Why, Done when), or the single line - none; never fix a finding here. Run make findings-check (it must pass). (7) Do not push, do not merge, do not touch master, never edit .github/workflows/**." \
		-m nous-deepseek --reasoning $(HERMES_FIX_REASONING) --yolo

.PHONY: review-issue
review-issue:
	# `_setup` in the SAME container as the hermes call, exactly like
	# `implement-issue` (#124: without the alias Hermes auto-routes to whatever
	# provider key is in the env -> HF_TOKEN -> HTTP 403).
	$(DOCKER_RUN) sh -c "make _setup && make _review-issue"

# The WINDOW path: an implementer has STARTED this issue. The body is off-limits
# for REVIEW_GAP_HOURS, so the reviewer replies instead - one bounded comment
# with the reminders its review found - and files what it found as its own
# `tech-debt` issues. It writes comment.md (the reply) and findings.md, and it
# must NOT write issue-body.md: the workflow proves the body is unchanged.
.PHONY: _review-issue-window
_review-issue-window:
	hermes -z "Load AGENTS.md for rules. You are the ISSUE REVIEWER (issue #179) and an implementer has STARTED issue #$(ISSUE). An implementer run reads the body ONCE at its start, so the BODY IS OFF-LIMITS: do NOT write, edit or reword it, and do not run gh issue edit. The issue body and comments are in issue.md at the repo root - read it and review the WHOLE thread. What you DO: (1) write ONE short comment to comment.md: at most 5 bullets, each with evidence (a file:line, a command, a measured behaviour), for the things the implementation should know - an acceptance clause the body contradicts, a contract that cannot hold the value it needs, the issue a defect duplicates, a rule it will trip. No preamble, no restating the issue, no general advice; nothing-to-add is a valid comment when you found nothing. (2) Write findings.md at the repo root with one section per real gap or piece of technical debt your review found (each with Evidence: file:line or a command, Why, Done when), or the single line - none; every finding becomes its own issue, so nothing you noticed is lost just because the body is off-limits. Run make findings-check (it must pass). (3) NEVER write issue-body.md: the workflow compares the body hash and fails loudly if it changed. (4) You have NO gh CLI and NO network write in this container: the workflow posts your comment.md, so do not try to run gh, do not edit the issue, do not touch the labels tech-debt/data-gap-analysis, never close the issue, never implement anything, never push, never merge, never edit .github/workflows/**." \
		-m nous-deepseek --reasoning $(HERMES_FIX_REASONING) --yolo

.PHONY: review-issue-window
review-issue-window:
	$(DOCKER_RUN) sh -c "make _setup && make _review-issue-window"

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
