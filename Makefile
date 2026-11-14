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
# ---- credentials the AGENT's shell must see (issue #359) ----------------------
# Hermes STRIPS provider credentials from its terminal tool on purpose
# (tools/environments/local_env_policy.py: FIRECRAWL_API_KEY, HF_TOKEN, NOUS_API_KEY
# ... are blocklisted, and env_passthrough can never re-allow one). So a key passed
# as `-e FIRECRAWL_API_KEY` reaches the container and Hermes, and the agent's `curl`
# still sends an EMPTY Bearer — measured: every refresh search leg got HTTP 401 while
# the step listing showed `FIRECRAWL_API_KEY: ***`. The one sanctioned way through is
# `_HERMES_FORCE_<NAME>`, which Hermes unwraps to `<NAME>` in the terminal child.
# ONE list: every credential a container receives. On the HOST, make exports
# `_HERMES_FORCE_<NAME>` from `<NAME>` (by reference — the value is never on a command
# line or in a recipe), only when `<NAME>` is set, and the run wrappers forward it by
# NAME. Inside a container (`/.dockerenv`) nothing is re-exported, so
# `make agent-shell-keys-check` proves what `docker run` forwarded, not what an inner
# make re-created. `IN_CONTAINER` is overridable for the tests only.
AGENT_SHELL_KEYS := NOUS_API_KEY FIRECRAWL_API_KEY HF_TOKEN $(NERVE_KEY_ENV)
AGENT_FORCE_PREFIX := _HERMES_FORCE_
IN_CONTAINER ?= $(if $(wildcard /.dockerenv),1,)
ifeq ($(IN_CONTAINER),)
$(foreach k,$(AGENT_SHELL_KEYS),$(if $(value $(k)),$(eval export $(AGENT_FORCE_PREFIX)$(k) = $$($(k)))))
endif
AGENT_SHELL_FORWARD := $(foreach k,$(AGENT_SHELL_KEYS),-e $(AGENT_FORCE_PREFIX)$(k))

# The container's OWN stdio is a pipe (`docker run` without a TTY), so a Python child
# block-buffers its output and writes nothing until it exits — which made a running fix round
# invisible even to a host that streamed it (issue #591, measured: run 39183131652, one line and
# then over an hour of silence). `PYTHONUNBUFFERED=1` is set EXPLICITLY (`-e NAME=value`, never a
# forwarded host value) so every Python process in the container — Hermes, and every
# `make`-invoked script — flushes each line into the stream the redactor is already reading.
DOCKER_RUN := docker run --rm -v "$$PWD":/workspace -w /workspace \
	-e PYTHONUNBUFFERED=1 \
	-e NOUS_API_KEY -e FIRECRAWL_API_KEY -e HF_TOKEN -e $(NERVE_KEY_ENV) $(AGENT_SHELL_FORWARD) $(IMAGE)

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
# `docker run --rm` removes the container only after the container exits. A killed
# client (a tool timeout) leaves it running (issue #720). The wrapper names the
# run and removes it when that client dies.
TEST_RUN := bash scripts/docker_test_run.sh --rm -v "$$PWD":/workspace $(if $(GIT_COMMON_DIR),-v "$(GIT_COMMON_DIR):$(GIT_COMMON_DIR)",) -w /workspace \
	-e PYTHONUNBUFFERED=1 \
	-e NOUS_API_KEY -e FIRECRAWL_API_KEY -e HF_TOKEN -e $(NERVE_KEY_ENV) $(AGENT_SHELL_FORWARD) $(TEST_IMAGE)


HERMES_MODEL := deepseek/deepseek-v4-flash-0731
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
# The pinned Hermes agent VERSION (issue #218): the seam asserts `hermes
# --version` equals it and bakes the verified version into the image. Raise it
# TOGETHER with the Dockerfile's ARG HERMES_VERSION default; an upgrade is then
# an explicit, reviewable change instead of whatever the channel serves.
HERMES_VERSION     ?= 0.23.1
# Raise the per-reply output cap. The deepseek model was truncating its reply
# mid-search (hit the default max_tokens), dropping the incomplete action and
# failing `make refresh`. At 8000 the heavier Metal search still
# truncated mid-payload; 16000 gives headroom (the model card supports up to
# 384K output). Input context is also raised to the model's 1M-token ceiling
# (model card: 1M input / 384K output) so a long AGENTS.md + skill + mirrors
# page is never squeezed. One variable each so CI + local runs agree.
# The current pin, deepseek/deepseek-v4-flash-0731, publishes
# max_completion_tokens 65536 (/v1/models, 2026-10-29). HERMES_MAX_TOKENS sits
# on that cap. A larger value is accepted SILENTLY and clamped, which is how
# 384000 once hid the real cap.
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
# the repair agent diagnoses a failure report, so it keeps a little (low).
HERMES_REASONING     := none
HERMES_FIX_REASONING := low
# Bound ONE Hermes fix round (issue #383). Without a bound the round that never
# returns is killed by the JOB's `timeout-minutes: 120` — measured on run
# 39124432576, where 1 h 58 m of the 2 h budget went on round 1 of 3 and the loop's
# own failure path never ran. The value is passed to `_fix` (which bounds the
# `hermes` call itself, so the container is reaped cleanly) and read by
# `scripts/fix_loop.sh` as the host-level backstop, so both are the SAME number.
HERMES_FIX_TIMEOUT   := 1800

# The NON-INTERACTIVE flag set every `hermes -z` recipe MUST pass (issue #351).
# `--yolo` alone is NOT enough: it covers "dangerous command approval prompts"
# only (hermes --help), while `--accept-hooks` is a SEPARATE flag for "unseen
# shell hooks". Measured on run 39079759124 (2026-10-17): the implementer's
# headless run stopped on an input prompt and DETACHED — "Input required;
# detached without cancelling. Resume this session interactively." — after
# 10m21s, returning rc=2 that the pipeline could only report as "no
# implementation". One variable, so a recipe can never carry half the set.
HERMES_NONINTERACTIVE := --yolo --accept-hooks

# ---- every public target that runs the agent SCRUBS its stream (issue #351/355) ----
# An agent's output IS the job's console log, and GitHub masks only the values it
# REGISTERS — a transformed one (URL-encoded, base64, a slice) sails past. The
# redaction lives HERE, in the public targets, because they are the ONE seam every
# caller shares: a workflow step (`make search-<backend>`), a bot script (`make fix`
# from `scripts/fix_loop.sh`) and a human all get it by calling `make`, and a new
# leg cannot forget it. `hermes-run.log` is gitignored; the REDACTED copy is what a
# workflow uploads as its artifact.
HERMES_LOG      := hermes-run.log
HERMES_LOG_SCRUBBED := hermes-run.scrubbed.log
# There is deliberately NO `HERMES_LOG_TAIL` knob (issue #630): the seam is LIVE `--stream`,
# which prints every redacted line as it arrives, so a "how many lines get printed" knob would
# change nothing — the only bound is `scripts/scrub_log.py`'s own `--tail` default in `--in`
# (post-mortem) mode. `make check-makefile-knobs` refuses a declared-but-unread knob, so a
# dead one cannot come back silently.
# `$(call scrubbed_run,<command>)`: run it, STREAMING through the redactor, and keep the
# command's own exit status (a red run must stay red). `scripts/scrub_log.py` reads the secret
# values BY NAME from this environment — the runner passes them with `env:`, the docker call
# forwards the NAMES — so a value the agent printed, in any spelling, never reaches the console.
#
# The redaction is LIVE, not a post-mortem (issue #591). It used to capture the whole stream into
# `$(HERMES_LOG)` and print only its tail once the command had ENDED, so a fix round printed one
# line and then nothing for over an hour (measured: fix-bot run 39183131652, the whole step empty
# in `gh run view --log` while it ran) and "is fix-bot working?" was answerable only from a
# post-mortem. Now each line is MASKED and then printed, flushed as it arrives, so the job log
# answers that question while the round runs — and the raw capture and the redacted copy are both
# still written for the artifact. `bash -o pipefail` is what keeps the command's status: a
# pipeline in `/bin/sh` would report the redactor's own 0 and turn a red leg green.
#
# The capture APPENDS per invocation (issue #631): `scripts/fix_loop.sh` runs up to FIX_ROUNDS
# `make fix` rounds against the SAME $(HERMES_LOG), and every round opened the captures with
# mode "w" — so the last round truncated the transcripts of all the earlier ones, including the
# detached-round message the artifact exists to keep (issue #566). `--append` opens both files
# in append mode behind a timestamped delimiter, so the one artifact file holds EVERY round.
#
# The command is passed to `bash -c` as a POSITIONAL argument (`$1`), never spliced into the
# script text (issue #632). The old seam interpolated `$(1)` inside a single-quoted script, so a
# caller whose command contained a single quote — which AGENTS.md §4 TELLS prompts to use ("prose
# inside a prompt uses single quotes") — closed the `-c` string early: bash parsed the rest of the
# prose as a command and the leg died with a syntax error far from its cause. `$(subst ','\'',…)`
# shell-escapes every quote in the value, `'$1'` hands it to bash untouched, and `eval "$$1"` runs
# it with the same parsing (and the same exit status under pipefail) the splice had.
define scrubbed_run
	@bash -o pipefail -c 'eval "$$1" 2>&1 | python3 scripts/scrub_log.py --stream --append --raw "$$2" --out "$$3"' _ '$(subst ','\'',$(1))' '$(subst ','\'',$(HERMES_LOG))' '$(subst ','\'',$(HERMES_LOG_SCRUBBED))'
endef


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
	python3 scripts/ensure_image.py publish $(if $(FORCE),--force=$(FORCE),)

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

# ---- the python-env seam (issue #712, Slice 1) -----------------------------
# Every `python3 scripts/…` `_command` runs inside the python-env image via this
# ONE seam, so a host with Docker but not the pinned Python/deps still runs the
# targets (OS-agnostic make). `$$PWD` is bind-mounted at /workspace (mounted src,
# so scripts/ + the Makefile are reachable and hero writes land back on host).
# The recipe stays a PURE command (`python3 scripts/X.py ...`) — the container
# harness lives here, not per-recipe.
PYTHON_IMAGE := trending-local-llms-python-env:latest
# Runs as the invoking user (like OS_OPTS) so a write lands owned by the repo's
# owner; PYTHONUNBUFFERED mirrors DOCKER_RUN so Python output streams live
# (issue #591). No HOME=/tmp: these scripts don't need a writable $HOME.
# PYTHON_RUN is the docker harness ONLY (mount, workdir, user, env) — the
# recipe keeps the pure command (`python3 scripts/X.py ...`), so a reader sees
# exactly what runs and the container seam stays in one place (issue #712).
PYTHON_RUN := docker run --rm --user $$(id -u):$$(id -g) -v "$$PWD":/workspace -w /workspace \
	-e PYTHONUNBUFFERED=1 $(PYTHON_IMAGE)

# ---- host-only exceptions to the python-env seam (issue #712, Slice 2) ------
# Not every host `python3 scripts/…` target routes through PYTHON_RUN; these stay
# on the runner, deliberately (each is doc'd at its own target too):
#  - gh-bound verifiers (openspec-archive-check, data-gap-issue/baseline,
#    code-review-file, file-findings, verify-closure, pr-closure, pr-health):
#    they read GitHub state / file issues, so they need the runner's `gh`+token;
#    the python-env image deliberately carries no gh.
#  - lint / lint-fix and check-commit-authorship: they run BEFORE `image-ensure`
#    in qa-validate by design ("cheapest gate first, needs no image"; the latter
#    is Git-only) — routing them through the container would force a python-env
#    build at the top of the guard job on every fresh runner. Kept host-side.
#  - already-$(TEST_RUN)/$(DOCKER_RUN)-wrapped seams (validate, update_trending,
#    data-gaps report) must NOT be rewrapped (no docker-in-docker).

.PHONY: openspec-image python-env-image openspec-new openspec-validate openspec-status openspec-archive openspec-shell openspec-tasks-check openspec-spec-tests-check openspec-duplicate-check openspec-index openspec-index-check openspec-index-repair openspec-index-repair-pr-body openspec-archive-check openspec-record-pr openspec-backlog-check openspec-binding-check openspec-check file-findings findings-check action-pin-check openspec-manifest-check
openspec-image: ## Ensure the OpenSpec CLI image (pull the published hash tag, else build it)
	python3 scripts/ensure_image.py ensure-openspec

python-env-image: ## Ensure the python-env image for the PYTHON_RUN seam (build from Dockerfile.python-env when absent; no registry probe)
	python3 scripts/ensure_image.py ensure-python

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

openspec-tasks-check: python-env-image ## Fail when an ACTIVE change still has an unticked `- [ ]` task; `- [~] … — blocked: <who/why>` is reported as review-required (NAME=<change> for one)
	$(PYTHON_RUN) python3 scripts/check_openspec_tasks.py $(NAME)

openspec-spec-tests-check: python-env-image ## Fail when an ACTIVE change's spec cites a `- **Test:** <path>::<test>` that does not resolve: `<path>` must exist and, for a Python module, the `<test>` must be defined top-level in it (NAME=<change> for one) (issue #621)
	$(PYTHON_RUN) python3 scripts/check_openspec_test_lines.py $(NAME)

openspec-duplicate-check: python-env-image ## Fail when two ACTIVE changes declare an ADDED/MODIFIED capability Requirement with the SAME heading of the SAME kind (issue #622; NAME=<change> for one)
	$(PYTHON_RUN) python3 scripts/openspec_duplicate_check.py $(NAME)

openspec-backlog-check: python-env-image ## Fail when the ACTIVE OpenSpec backlog hits MAX 50 — auto-merge to master is blocked until the tail is archived (issue #938)
	$(PYTHON_RUN) python3 scripts/openspec_backlog_check.py

openspec-manifest-check: ## Refuse a published OpenSpec image tag unless its manifest answers linux/arm64 AND linux/amd64 (issue #919) — host docker, like rebuild-decision; pass TAG=<exact published tag>
	@python3 scripts/openspec_manifest_check.py --tag "$(TAG)"
openspec-binding-check: python-env-image ## Fail when an ACTIVE change binds no Issue and declares no keeper exemption — caught before the PR, not at the record step (issue #952)
	$(PYTHON_RUN) python3 scripts/openspec_binding_check.py

openspec-index: python-env-image ## Regenerate the root OPENSPEC.md index from openspec/changes/**
	$(PYTHON_RUN) python3 scripts/openspec_index.py --write

openspec-index-check: python-env-image ## Fail when OPENSPEC.md is stale, or a change on disk has no row
	$(PYTHON_RUN) python3 scripts/openspec_index.py --check

# The event-driven keeper for a red master index gate (issue #304, rule 6q). A
# merged PR archives its change, so `master`'s tree no longer matches the
# committed OPENSPEC.md and the push-to-master `validate` goes red — with no PR
# repair path. qa-validate's `index-repair` job runs exactly this target against
# the post-merge tree that just went red; the DRIFT= verdict (rule 6d) decides
# whether the workflow may land a keeper PR, and the workflow re-decides nothing.
openspec-index-repair: python-env-image ## Classify a stale OPENSPEC.md against THIS tree and regenerate it when the drift is index-only (DRIFT=none|index-only; issue #304)
	$(PYTHON_RUN) python3 scripts/openspec_index_repair.py --classify-and-write

openspec-index-repair-pr-body: ## Print the index-repair keeper PR body — no closing keyword, it records drift (MASTER_SHA=… RUN_URL=… required; issue #304)
	@python3 scripts/openspec_index_repair.py --print-pr-body --master-sha "$(MASTER_SHA)" --run-url "$(RUN_URL)"

# The lifecycle's END (rule 6f, issue #183): a change whose PR merged must be
# archived in that PR, so an ACTIVE change naming a merged PR is a defect. Needs
# `gh` (PR state is a GitHub fact); run on the host, where the token lives —
# inside the agent container `gh` is absent, so it is NOT part of `openspec-check`
# (which the fix loop runs in the container) but its own step in qa-validate.
openspec-archive-check: ## Fail when an ACTIVE change names a MERGED PR, references a CLOSED issue with no recorded PR, or would be stranded by the PR being validated (PR=<n>) (rules 6f/#518/#779; host-side: needs gh)
	python3 scripts/openspec_archive_check.py $(if $(PR),--pr $(PR),)

# Recording half of the change lifecycle (issue #518): once the PR that will
# complete a change EXISTS, ITS PR number is written into the change's proposal
# and the index is regenerated — so no change can be merged-and-forgotten with a
# vacuous "none names a PR" again. Host-side (writes only the tree), called by
# issue-bot after `gh pr create`. REFUSES (exit 2) when no active change names
# the given issue, so a recording that matched nothing is loud, never silent.
openspec-record-pr: ## Write `PR: #<PR>` into every ACTIVE change whose `Issue:` is `#<ISSUE>`, then regenerate the index
	@test -n "$(ISSUE)" && test -n "$(PR)" || { echo "Usage: make openspec-record-pr ISSUE=<n> PR=<m>"; exit 1; }
	@python3 scripts/openspec_record_pr.py --issue "$(ISSUE)" --pr "$(PR)"

openspec-check: openspec-image openspec-tasks-check openspec-duplicate-check openspec-index-check openspec-spec-tests-check openspec-backlog-check openspec-binding-check ## CI gate: every active change validates, no task unticked or blocked, no two changes propose the same rule, every `- **Test:**` reference resolves, the ACTIVE backlog is under the 50 cap (issue #938), every ACTIVE change binds the Issue its PR closes or declares `Binding-exempt:` (issue #952), the index current
	docker run $(OS_OPTS) openspec validate --changes
	@echo "[openspec-check] OK: active changes validate, no task is unticked, no two ACTIVE changes propose the same Requirement, every \`- **Test:**\` reference resolves, OPENSPEC.md is current (a task marked 'blocked: <who/why>' is reported above as review-required)"

file-findings: ## File ONE issue per finding in findings.md (host-side: needs gh + the repo)
	python3 scripts/file_findings.py --file $(if $(PR),--pr $(PR)) $(if $(ISSUE),--issue $(ISSUE))

findings-check: python-env-image ## Fail when findings.md is missing or a finding lacks evidence / why / done-when
	$(PYTHON_RUN) python3 scripts/file_findings.py --check

# Immutable-SHA pin guard (issue #735, #714 Slice 1, folding #717): every
# third-party workflow `uses:` ref must be a 40-hex SHA or on the allow-ref list,
# and every third-party tool image (Makefile *_IMAGE / scripts / Dockerfile ARG)
# must be pinned (digest or fleet `<sha12>` tag) or allowlisted. Fails closed.
# Current mutable refs are on an allowlist with allow-till deadlines (the
# migration slices of #714/#715 will pin them); a NEW mutable ref is refused.
action-pin-check: python-env-image ## Fail when a third-party workflow uses: ref or tool-image tag is mutable and not allowlisted (issue #735)
	$(PYTHON_RUN) python3 scripts/action_pin_check.py

architecture-check: python-env-image ## Fail when ARCHITECTURE.md misses a make target, a workflow or a script — or its generated inventory is stale (rule 6h)
	$(PYTHON_RUN) python3 scripts/architecture_check.py
	$(PYTHON_RUN) python3 scripts/architecture_bot.py --check

# The LIVING half of this document (issue #479): the inventory of every pipeline
# (its triggers, its jobs, the make targets they call), the product end to end and
# one line per script is DERIVED from the tree, between two markers, so it cannot
# rot into prose nobody re-reads. `architecture-bot.yml` runs this daily and opens
# a PR only when the block changed; `architecture-check` above fails while it is
# stale, so the daily bot repairs drift instead of the drift living for weeks.
architecture-refresh: ## Regenerate ARCHITECTURE.md's inventory block from the tree (rule 6h, issue #479)
	python3 scripts/architecture_bot.py --write

# The event-driven keeper for a red master ARCHITECTURE block gate (issue #861, rule 6q) —
# the sibling of `openspec-index-repair` (#304) for the OTHER half of the generated pair.
# A merged PR that moved a target/script/job without `architecture-refresh` reds the
# push-to-master `validate` with no PR repair path; the Wednesday-only `architecture-bot`
# leaves the merge queue red for days (measured after merge `91eb093`). qa-validate's
# `architecture-repair` job runs exactly this target against the post-merge tree that just
# went red; the DRIFT= verdict (rule 6d) decides whether the workflow may land a keeper PR,
# and the workflow re-decides nothing.
.PHONY: architecture-block-repair architecture-block-repair-pr-body
architecture-block-repair: python-env-image ## Classify a stale ARCHITECTURE.md inventory block against THIS tree and regenerate it when the drift is block-only (DRIFT=none|block-only; issue #861)
	$(PYTHON_RUN) python3 scripts/architecture_block_repair.py --classify-and-write

architecture-block-repair-pr-body: ## Print the architecture-repair keeper PR body — no closing keyword, it records drift (MASTER_SHA=… RUN_URL=… required; issue #861)
	@python3 scripts/architecture_block_repair.py --print-pr-body --master-sha "$(MASTER_SHA)" --run-url "$(RUN_URL)"

# ---- the PR closes the issue it implements (rule 6e, issue #284) -------------
# The PR body is the only artifact in the pipeline whose whole purpose is "this merge
# closes that issue", and the only one with no guard on its content. GitHub binds a
# closing keyword to ONE reference, so `Closes #1 and #2` closes #1 and leaves #2 open
# (measured: PR #272 left #276 open after merging). Host-side, and it reads the webhook
# payload by PATH so nothing is ever interpolated into a run: block.
PR_EVENT ?= $(GITHUB_EVENT_PATH)

# The repository's agent identity has ONE definition (scripts/agent_identity.py, issue #325):
# every committing job calls this seam, and the authorship guard reads the same module. A new
# committing workflow therefore inherits the identity by construction, and a change to the
# address is one edit.
.PHONY: _git-identity git-identity
_git-identity:
	python3 scripts/agent_identity.py --git-config

git-identity:
	$(MAKE) _git-identity
# After the MERGE: did the issue the body claimed to close actually close? `make pr-closure`
# PREDICTS it; this proves it (issue #288 — PR #272 left #276 open with every job green).
.PHONY: _verify-closure verify-closure
_verify-closure:
	python3 scripts/verify_closure.py --pr "$(PR)" $(if $(REPO),--repo "$(REPO)",)

verify-closure:
	$(MAKE) _verify-closure PR="$(PR)" REPO="$(REPO)"

# A conflicting PR runs NO workflows (issue #442): its checks are ABSENT, not failed, so an
# empty check list looks like a quiet queue. The DECISION lives in scripts/pr_health.py; this
# target is how the sweep and a human reach it.
.PHONY: _pr-health pr-health
_pr-health:
	python3 scripts/pr_health.py $(if $(REPO),--repo "$(REPO)",) $(if $(COMMENT),--comment,)

# REPORT-ONLY since issue #814: the fix-bot repair pipeline was retired, so the sweep
# flags silent PRs and comments the remedy; it dispatches nothing.
pr-health:
	$(MAKE) _pr-health REPO="$(REPO)" COMMENT="$(COMMENT)"

pr-closure: ## Fail when this PR does not close the issue its branch implements (rule 6e)
	@test -n "$(PR_EVENT)" -o -n "$(BRANCH)" || { echo "Usage: make pr-closure [PR_EVENT=<event json>] | [BRANCH=<head ref> BODY_FILE=<pr body>]"; exit 1; }
	python3 scripts/pr_closure.py $(if $(PR_EVENT),--event "$(PR_EVENT)",--branch "$(BRANCH)" $(if $(BODY_FILE),--body-file "$(BODY_FILE)",))

pr-message-check: ## Fail when this PR does not follow the message pattern / close what it implements (issue #771)
	@test -n "$(PR_EVENT)" -o -n "$(BRANCH)" || { echo "Usage: make pr-message-check [PR_EVENT=<event json>] | [BRANCH=<head ref> BODY_FILE=<pr body>]"; exit 1; }
	@python3 scripts/pr_body.py $(if $(PR_EVENT),--event "$(PR_EVENT)",--check-body-file "$(BODY_FILE)" $(if $(BRANCH),--branch "$(BRANCH)",))

issue-message-check: ## Fail when an ISSUE body does not follow the message pattern (five ## sections, issue #771)
	@test -n "$(ISSUE_EVENT)" -o -n "$(BODY_FILE)" || { echo "Usage: make issue-message-check [ISSUE_EVENT=<event json>] | [BODY_FILE=<issue body>]"; exit 1; }
	@python3 scripts/pr_body.py $(if $(ISSUE_EVENT),--issue-event "$(ISSUE_EVENT)",--check-issue-file "$(BODY_FILE)" $(if $(ISSUE),--issue "$(ISSUE)",))

commit-message-check: ## Fail when a COMMIT message does not follow the message pattern / close what it implements (issue #771)
	@test -n "$(BODY_FILE)" || { echo "Usage: make commit-message-check BODY_FILE=<commit message> [BRANCH=<head ref>] [ISSUE=<n>]"; exit 1; }
	@python3 scripts/pr_body.py --check-commit-file "$(BODY_FILE)" $(if $(BRANCH),--branch "$(BRANCH)",) $(if $(ISSUE),--issue "$(ISSUE)",)

# ---- where work starts: a worktree off the freshly fetched base (rule 6n) ----
# ONE implementation (scripts/worktree_base.py) of the fetch, the assertion and the
# refusal, shared by CI (`make base-check` before a branch is cut, `IN_PLACE=1` when the
# fresh checkout IS the working copy) and by a human locally (`make worktree-new`). Host
# targets on purpose: git and its credentials live here, not in a container that would
# write root-owned objects into the shared .git (issue #271).
base-check: ## Fail unless this checkout IS the freshly fetched <BASE> (CI runs it before it cuts a branch)
	python3 scripts/worktree_base.py check $(if $(BASE),--base $(BASE),)

# The ADVANCE shape (issue #448): for a CI job that has written NOTHING yet. `base-check`
# refuses a checkout that is merely behind — the right answer where the tree carries work,
# and a scheduled data loss where it does not: refresh-bot's `aggregate` asserts its base
# after ~40 min of searching, and `master` routinely merges in that window (measured: run
# 39329834698, 4/4 legs green, HEAD 2 commits behind, whole refresh discarded). This
# fast-forwards a CLEAN checkout onto the fetched tip and refuses only a dirty tree or a
# HEAD with commits the base does not have. Same ONE implementation (rule 6d/6m).
branch-adopt: ## Cut or attach BRANCH at COMMIT time, reporting behind_base=N and asserting NO base; with ISSUE= a NEW branch's name must implement it (issue #500, #807) (BRANCH=, BASE=, ISSUE=)
	@test -n "$(BRANCH)" || { echo "Usage: make branch-adopt BRANCH=<branch> [BASE=master] [ISSUE=<n>]"; exit 1; }
	python3 scripts/worktree_base.py adopt --branch "$(BRANCH)" --base "$(if $(BASE),$(BASE),master)" $(if $(ISSUE),--issue $(ISSUE),)

base-rebase: ## Fetch the base and rebase BRANCH onto it; a conflict KEEPS the work and still SUCCEEDS (`base_rebase=conflict`) (BRANCH=, BASE=)
	@test -n "$(BRANCH)" || { echo "Usage: make base-rebase BRANCH=<branch> [BASE=master]"; exit 1; }
	@rc=0; python3 scripts/worktree_base.py rebase --branch "$(BRANCH)" --base "$(if $(BASE),$(BASE),master)" || rc=$$?; \
	if [ $$rc -eq 3 ]; then echo "base_rebase=conflict"; exit 0; fi; exit $$rc

base-advance: ## Fetch <BASE> and fast-forward this clean checkout onto it (a job that has written nothing yet)
	python3 scripts/worktree_base.py advance $(if $(BASE),--base $(BASE),)

# A refresh PR is entirely GENERATED files that every merge rewrites, so a branch cut
# from a base the queue has already left is a whole-file conflict waiting for
# `auto-merge` (issue #177: PR #164 rebased twice in one hour, then `GraphQL: Pull
# Request has merge conflicts` while `validate` + `live-smoke` were green).
# `refresh-sync` moves the generated tree onto the fetched tip and KEEPS the raw
# snapshots, so the caller re-runs `make merge` and re-derives the store/README/baseline
# instead of applying a stale copy of them; `refresh-require-tip` is the guard that then
# refuses to publish a branch the base has left. Host targets, like their `base-*` kin:
# git lives on the runner, not in the container.
refresh-sync: ## Move a refresh's generated tree onto the fetched <BASE>, keeping its raw snapshots (issue #177)
	@python3 scripts/refresh_base.py sync $(if $(BASE),--base $(BASE),)

refresh-require-tip: ## Fail unless the refresh branch contains the freshly fetched <BASE> (issue #177)
	python3 scripts/refresh_base.py require-tip $(if $(BASE),--base $(BASE),)

worktree-new: ## Start a new branch off the freshly fetched base, in a worktree; with ISSUE= the branch name is validated through the pr-closure parser at the cut (issue #807) (IN_PLACE=1 for the CI checkout)
	@test -n "$(BRANCH)" || { echo "Usage: make worktree-new BRANCH=<branch> [BASE=master] [IN_PLACE=1] [DIR=<path>] [ISSUE=<n>]"; exit 1; }
	python3 scripts/worktree_base.py new --branch "$(BRANCH)" $(if $(BASE),--base $(BASE),) $(if $(IN_PLACE),--in-place,) $(if $(DIR),--dir "$(DIR)",) $(if $(ISSUE),--issue $(ISSUE),)

worktree-resume: ## Resume an existing branch — fetched first, so a re-run of a one-ref checkout works
	@test -n "$(BRANCH)" || { echo "Usage: make worktree-resume BRANCH=<branch> [BASE=master] [IN_PLACE=1] [DIR=<path>]"; exit 1; }
	python3 scripts/worktree_base.py resume --branch "$(BRANCH)" $(if $(BASE),--base $(BASE),) $(if $(IN_PLACE),--in-place,) $(if $(DIR),--dir "$(DIR)",)

# ---- linefeeds: every tracked text file ends with a newline (issue #186) -----
# A file without a final newline makes git print `\ No newline at end of file`
# and turns the next append into a spurious last-line change. `make lint` is the
# gate (a `qa-validate` step, the first check in the fix loop), `make lint-fix`
# the repair. Pure python, so host and container agree.
# A conflict marker in a tracked file is never acceptable: in a PARSED file (Makefile, a
# workflow, a module) it does not merely look wrong, it makes every later `make` fail — the
# measured run 40202490846 died with `Makefile:588: *** missing separator` after one was
# committed. `#583` removed the producer; this is the last line of defence (issue #588).
.PHONY: _check-conflict-markers
_check-conflict-markers:
	python3 scripts/check_conflict_markers.py

.PHONY: check-conflict-markers
check-conflict-markers: ## Fail when a tracked file carries a merge-conflict block (issue #588)
	@$(MAKE) --no-print-directory _check-conflict-markers

# Every tests/test_*.py is a SCRIPT (issue #768): scripts/run_tests.sh runs each module in its own
# process and the TEST image deliberately has NO pytest, so an `import pytest` is host-green and
# dies only in the TEST image — measured as a ~15-minute red validate job (run 42800200326). The
# guard refuses the import and the `pytest.` API use at the gate that runs first everywhere.
.PHONY: _check-pytest-imports
_check-pytest-imports:
	python3 scripts/check_pytest_imports.py

.PHONY: check-pytest-imports
check-pytest-imports: ## Fail when a test module imports or calls pytest — the TEST image has none (issue #768)
	@$(MAKE) --no-print-directory _check-pytest-imports

# A `NAME ?=` knob is what an operator sets. When nothing in the runner's tree reads it, the
# operator's act changes nothing silently — measured with HERMES_LOG_TAIL, dead ever since the
# seam went live (--stream, issue #591) yet still declared (issue #630). The guard names the
# file:line and refuses the knob; the same rule as rule 6d's no-dead-code, on the Makefile.
.PHONY: _check-makefile-knobs
_check-makefile-knobs:
	python3 scripts/check_makefile_knobs.py

.PHONY: check-makefile-knobs
check-makefile-knobs: ## Fail when the Makefile declares a `?=` knob no recipe or script reads (issue #630)
	@$(MAKE) --no-print-directory _check-makefile-knobs

# §6j tree-wide identity-guard scan (issue #816): every .github/workflows/*.yml is
# scanned and its REAL guard script is executed for every caller class, the cron
# bypass and repository-event admissions are proved, and an `environment:` approval
# gate is refused — no pipeline may wait on a human to start. Bundled into lint,
# which is the FIRST gate of qa-validate's validate job and of scripts/fix_loop.sh.
.PHONY: _check-workflow-guards
_check-workflow-guards:
	python3 scripts/check_workflow_guards.py

.PHONY: check-workflow-guards
check-workflow-guards: ## Fail when a workflow .yml lacks its guard, gates a start on a human, or its guard misdecides a caller class (issue #816)
	@$(MAKE) --no-print-directory _check-workflow-guards

# The bot's working files, in ONE list (issue #543). They are gitignored, but both bots unstage
# them explicitly before `git add -A` because a name written before the ignore entry lands — or
# created in another checkout — can be staged anyway, and a committed `issue.md` publishes
# scratch inside the repository (the #390 class: a 0-byte `qa-report.txt.notes` reached PR #387).
# The list used to be two identical `git reset -q -- …` lines in `issue-bot.yml`, a third copy in
# `fix-bot.yml` and a fourth in `.gitignore`.
WORKING_FILES := scripts/issue_bot_working_files.txt

.PHONY: _reset-working-files
_reset-working-files:
	python3 scripts/reset_working_files.py

.PHONY: reset-working-files
reset-working-files: ## Unstage the bot's working files (one list: $(WORKING_FILES); issue #543)
	@$(MAKE) --no-print-directory _reset-working-files

.PHONY: _check-working-files
_check-working-files:
	python3 scripts/reset_working_files.py --check

.PHONY: check-working-files
check-working-files: ## Fail when a name in the bot's working-file list is not gitignored (issue #543)
	@$(MAKE) --no-print-directory _check-working-files

.PHONY: lint lint-fix
lint: ## Fail when a tracked text file does not end with a newline, a tracked Python module raises a SyntaxWarning, or a bot leg lost its project skill
	python3 scripts/lint_linefeeds.py
	python3 scripts/lint_syntax.py
	$(MAKE) --no-print-directory check-agent-skills
	$(MAKE) --no-print-directory check-working-files
	$(MAKE) --no-print-directory check-conflict-markers
	$(MAKE) --no-print-directory check-pytest-imports
	$(MAKE) --no-print-directory check-makefile-knobs
	$(MAKE) --no-print-directory check-workflow-guards

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
	@# The bot legs run one-shot `hermes` with `--yolo --accept-hooks` (issue #351) in a
	@# runner. Those two flags approve SHELL prompts and HOOKS — they do NOT answer
	@# the model's own `clarify` tool. A leg that asks a question therefore prints
	@# "Input required; detached without cancelling" and exits 3, killing that leg's
	@# refresh (measured on the amd leg, run 40407812898, and the cpu leg, run
	@# 40872677522). The root fix is to REMOVE the tool, not to trust the prompt to
	@# not use it: disable the `clarify` toolset here, once, at provision time, so no
	@# recipe can resurrect it. Strict on failure: an agent that can still ask is the bug.
	@hermes tools disable clarify >/dev/null 2>&1 || \
		{ echo "FAIL: 'hermes tools disable clarify' unsupported — the bot's legs can still call \`clarify\` and DETACH (the recurring refresh-leg failure)"; exit 1; }
	@# The bot contracts live in .hermes/skills and every leg preloads one with
	@# `hermes -s` (issue #549). Register the checkout's directory in THIS Hermes
	@# home and read it back: a container where `-s` resolves nothing would run
	@# every leg with no contract at all and still report success.
	$(MAKE) --no-print-directory _hermes-skills-register
	$(MAKE) --no-print-directory _hermes-skills-check

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

## ---------------------------------------------------------------------------
## Every agent leg runs from a project SKILL, never from an inline rulebook (issue #549)
## ---------------------------------------------------------------------------
# A leg's contract used to be one inline `hermes -z` string in this file, and nothing told the
# model it was running with nobody watching it. Measured on the issue-bot sweep: three of five runs
# on 2026-10-24/25 died with `Input required; detached without cancelling` (rc=3), because
# `--yolo --accept-hooks` answers shell and hook prompts but NOT the agent's own `clarify` tool.
# The contract now lives in `.hermes/skills/<name>/SKILL.md` (the layout Hermes discovers from a
# registered directory), each leg preloads it with `-s <skill>,bot-unattended`, and its inline
# prompt is a pointer plus that run's parameters. `scripts/check_agent_skills.py` (through
# `make check-agent-skills`, part of `make lint`) fails a leg that preloads nothing, names a skill
# that does not exist, inlines the unattended contract again, or grows past its pointer budget.
#
# The directory has to be REGISTERED in this container's Hermes home, or `-s` resolves nothing and
# every leg runs with no contract at all — so `_setup` registers it and reads it back (the image
# build runs `_setup`, and `WORKDIR /workspace` is where the repo is mounted at run time too).
HERMES_SKILLS_DIR := $(CURDIR)/.hermes/skills
HERMES_HOME_DIR ?= $(if $(HERMES_HOME),$(HERMES_HOME),$(HOME)/.hermes)

.PHONY: _hermes-skills-register
_hermes-skills-register:
	python3 scripts/hermes_skills_register.py --home "$(HERMES_HOME_DIR)" --dir "$(HERMES_SKILLS_DIR)"

.PHONY: hermes-skills-register
hermes-skills-register: ## Register this checkout's .hermes/skills in the container's Hermes home so `hermes -s <name>` resolves (issue #549)
	$(DOCKER_RUN) make _hermes-skills-register

.PHONY: _hermes-skills-check
_hermes-skills-check:
	@python3 scripts/hermes_skills_register.py --home "$(HERMES_HOME_DIR)" --dir "$(HERMES_SKILLS_DIR)" --check

.PHONY: _check-agent-skills
_check-agent-skills:
	python3 scripts/check_agent_skills.py check

.PHONY: check-agent-skills
check-agent-skills: ## Fail when a bot leg preloads no skill, names a missing one, inlines the unattended contract, or the AGENTS.md rule is gone (issue #549)
	python3 scripts/check_agent_skills.py check

.PHONY: agent-skills-report
agent-skills-report: ## Print every agent leg with its prompt size and preloaded skills, and every skill's frontmatter (issue #549)
	python3 scripts/check_agent_skills.py report


# The trending-model queries (issue #264). The searches were a fixed keyword list
# that named no model - of 24 queries the ONE model-specific one named qwen3.8-27b,
# so every figure for the model topping the trend list arrived incidentally and a
# higher one upstream could never enter. These come from the ONE implementation in
# scripts/update_trending.py (rule 6d), through scripts/query_coverage.py, so the
# prompts and the guard can never disagree. Recursive (=) so the script runs only
# when a prompt actually uses it, never on every make invocation.
MODEL_QUERIES = $(shell python3 scripts/query_coverage.py --queries 2>/dev/null)

# The curated vocabulary of each leg comes from ONE reviewed home —
# scripts/query_vocab.py (issue #858). The CPU leg's hand-copied words captured
# zero models for eight refreshes while every gate stayed green, because three
# copies (this file, scripts/smoke_search.py, and a near-copy in
# update_trending.SEARCH_GROUPS) could each drift and nothing read the WORDS.
# Recursive (=): the script runs only when a leg prompt uses the list.
NVIDIA_KEYWORDS = $(shell python3 scripts/query_vocab.py --print nvidia 2>/dev/null)
METAL_KEYWORDS = $(shell python3 scripts/query_vocab.py --print metal 2>/dev/null)
CPU_KEYWORDS = $(shell python3 scripts/query_vocab.py --print cpu 2>/dev/null)
AMD_KEYWORDS = $(shell python3 scripts/query_vocab.py --print amd 2>/dev/null)

# The guard: every top-N trending model must be named by a query in the set the
# searches use. Exit 1 when one is not, so a stale or broken derivation is LOUD
# and separable from "the query ran and found nothing" (issue #264).
.PHONY: query-coverage
query-coverage: python-env-image ## Report which of the top trending models the search queries name, and fail when one is named by none (TOP=N, default 10)
	$(PYTHON_RUN) python3 scripts/query_coverage.py $(if $(TOP),--top $(TOP),)

# ---- the four search legs: ONE skill, four parameter sets (issue #638) ------
# The rules a search leg obeys — the fixed scrape request, the key read BY NAME, the
# terminal-tool pin, the engine rule, the five measurement dimensions, the post-URL and
# counter rule, the per-query write, the AMD/ROCm rules — live in
# `.hermes/skills/data-search/SKILL.md`, which every leg preloads with
# `-s data-search,bot-unattended`. The recipe is a POINTER plus THIS run's parameters:
# the backend, its keyword list, the derived model queries and the write command.
# A rule is therefore corrected in ONE reviewed file, and `make check-agent-skills`
# fails a leg whose prompt grows back into a rulebook (PROMPT_BUDGET).
.PHONY: _search-nvidia
_search-nvidia:
	hermes -z "Follow the preloaded skill data-search. Parameters: backend=nvidia; keywords=($(NVIDIA_KEYWORDS)); model_queries=$(MODEL_QUERIES); write_raw=python3 scripts/update_trending.py --write-raw nvidia < payload.json. AGENTS.md governs." \
		-m $(HERMES_ALIAS) --reasoning $(HERMES_REASONING) $(HERMES_NONINTERACTIVE) -s data-search,bot-unattended

.PHONY: _search-metal
_search-metal:
	hermes -z "Follow the preloaded skill data-search. Parameters: backend=metal; keywords=($(METAL_KEYWORDS)); model_queries=$(MODEL_QUERIES); write_raw=python3 scripts/update_trending.py --write-raw metal < payload.json. AGENTS.md governs." \
		-m $(HERMES_ALIAS) --reasoning $(HERMES_REASONING) $(HERMES_NONINTERACTIVE) -s data-search,bot-unattended

.PHONY: _search-cpu
_search-cpu:
	hermes -z "Follow the preloaded skill data-search. Parameters: backend=cpu; keywords=($(CPU_KEYWORDS)); model_queries=$(MODEL_QUERIES); write_raw=python3 scripts/update_trending.py --write-raw cpu < payload.json. AGENTS.md governs." \
		-m $(HERMES_ALIAS) --reasoning $(HERMES_REASONING) $(HERMES_NONINTERACTIVE) -s data-search,bot-unattended

.PHONY: _search-amd
_search-amd:
	hermes -z "Follow the preloaded skill data-search, including its AMD leg's own rules. Parameters: backend=amd; keywords=($(AMD_KEYWORDS)); model_queries=$(MODEL_QUERIES); write_raw=python3 scripts/update_trending.py --write-raw amd < payload.json. AGENTS.md governs." \
		-m $(HERMES_ALIAS) --reasoning $(HERMES_REASONING) $(HERMES_NONINTERACTIVE) -s data-search,bot-unattended

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
	timeout $(HERMES_FIX_TIMEOUT) hermes -z "Follow the preloaded skill pr-fix. Inputs: qa-report.txt at the repo root (the failing checks' own output) and AGENTS.md. Repair the cause, run the gates the skill names, and do not push or merge." \
		-m $(HERMES_ALIAS) --reasoning $(HERMES_FIX_REASONING) $(HERMES_NONINTERACTIVE) -s pr-fix,bot-unattended
	python3 scripts/update_trending.py  # merge corrected raw -> models.json
	python3 scripts/validate.py --only links  # fail-fast: confirm the fix actually resolved the links

.PHONY: _merge
# SINCE is forwarded only when it is SET (rule 3d: an empty value is missing). A refresh
# that re-derives its store on a moved base (issue #177) passes the oldest capture stamp it
# gathered: the base's own `generated_utc` can be NEWER than that snapshot, and the derived
# boundary would then skip the very data the run collected (issue #175).
_merge:
	python3 scripts/update_trending.py $(if $(SINCE),--since "$(SINCE)",)

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

# Record GitHub metadata for every registry engine the OFFLINE test fixture
# lacks (issue #334). Ingest already fetches this to classify a new engine; the
# fixture is what `tests/test_engine_registry.py` proves "a registered engine is
# never refused" against, so a refresh that registers one used to turn `make
# test` red while `make validate` stayed green. Runs in the refresh aggregate
# AFTER the merge (the merge is what registers the engine) and before qa-report.
.PHONY: _engine-meta-capture
_engine-meta-capture:
	python3 scripts/engine_registry.py --capture-meta

.PHONY: _nerve-check
# Which keys to prove: all of them by default; a leg that receives a SUBSET narrows it, so the
# check never fails on a key the job legitimately lacks (the search job carries Firecrawl and the
# Hugging Face token, not the Nous or nerve credentials).
AGENT_SHELL_CHECK_KEYS ?= $(AGENT_SHELL_KEYS)
_agent-shell-keys-check:
	python3 scripts/agent_shell_keys_check.py $(AGENT_SHELL_CHECK_KEYS)

.PHONY: agent-shell-keys-check
agent-shell-keys-check: ## Prove every container credential is visible in the AGENT's shell (Hermes strips them; issue #359)
	$(DOCKER_RUN) make _agent-shell-keys-check AGENT_SHELL_CHECK_KEYS="$(AGENT_SHELL_CHECK_KEYS)"

_nerve-check:
	python3 scripts/nerve_key_check.py

.PHONY: nerve-check
nerve-check:
	$(TEST_RUN) make _nerve-check

.PHONY: _validate-search
_validate-search:
	python3 scripts/validate.py --only search,mapping
	python3 scripts/query_coverage.py
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
	bash scripts/run_tests.sh

# Every tests/test_*.py is a SCRIPT (it exits non-zero on its own failures), not a pytest
# test: `scripts/run_tests.sh` runs each in its own process and stops at the first red
# (issues #176/#192 — the old recipe tried pytest first, discarded its stderr, and
# fell back to a hand-maintained chain a new module could miss).

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
# qa-validate can flag issues and the repair loop can repair them on the PR branch.
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
	$(DOCKER_RUN) sh -c "make _setup 1>&2 && make _hermes-alias-check"

.PHONY: search-nvidia
search-nvidia:
	@$(MAKE) --no-print-directory _search-preflight BACKEND=nvidia
	$(call scrubbed_run,$(DOCKER_RUN) sh -c "make _setup && make _search-nvidia")

.PHONY: search-metal
search-metal:
	@$(MAKE) --no-print-directory _search-preflight BACKEND=metal
	$(call scrubbed_run,$(DOCKER_RUN) sh -c "make _setup && make _search-metal")

.PHONY: search-cpu
search-cpu:
	@$(MAKE) --no-print-directory _search-preflight BACKEND=cpu
	$(call scrubbed_run,$(DOCKER_RUN) sh -c "make _setup && make _search-cpu")

.PHONY: search-amd
search-amd:
	@$(MAKE) --no-print-directory _search-preflight BACKEND=amd
	$(call scrubbed_run,$(DOCKER_RUN) sh -c "make _setup && make _search-amd")

.PHONY: search
search:
	@$(MAKE) --no-print-directory _search-preflight BACKEND=nvidia
	$(call scrubbed_run,$(DOCKER_RUN) sh -c "make _setup && make _search")

# Every search leg runs this FIRST (issue #357). A leg whose Firecrawl key is missing
# or empty used to run anyway: the agent could not authenticate, spent its turns
# hunting for the key, and wrote `export FIRECRAWL_API_KEY=<what to put here>` into an
# open log — a public-log placeholder one paste away from a real value (#355). So the
# leg checks the credential it needs and the backend it reaches BEFORE the agent
# starts: `require_env.py` fails loudly on a missing/empty name (never printing a
# value), then the EXISTING `search-smoke` proves the key is accepted and the mirror
# answers — one implementation, the same one `live-smoke` runs (rule 6d).
# Both credentials the leg uses are then proven in the AGENT's shell (issue #363): the
# Firecrawl key the scrape sends, and HF_TOKEN, which the leg needs to verify a model's
# Hugging Face link (an unauthenticated lookup is rate-limited, so a gated repo reads as
# missing and the leg writes the marketing name). A leg whose job stopped forwarding
# either one fails HERE, loudly and before the agent, naming the variable.
.PHONY: _search-preflight
_search-preflight:
	@python3 scripts/require_env.py FIRECRAWL_API_KEY --why "the search legs cannot scrape lightbrd.com without it"
	@$(MAKE) --no-print-directory search-smoke BACKEND=$(BACKEND)
	@$(MAKE) --no-print-directory agent-shell-keys-check AGENT_SHELL_CHECK_KEYS="FIRECRAWL_API_KEY HF_TOKEN"

.PHONY: search-smoke
search-smoke:
	$(DOCKER_RUN) make _search-smoke $(if $(BACKEND),BACKEND=$(BACKEND),)

.PHONY: model-caps
model-caps:
	$(DOCKER_RUN) make _model-caps

.PHONY: hermes-smoke
hermes-smoke:
	$(DOCKER_RUN) sh -c "make _setup 1>&2 && make _hermes-smoke"

# Live pipeline smoke: real Firecrawl->lightbrd scrape for every nvidia/metal/
# cpu/amd query (3s cap each) + a real Hermes call through the search alias.
.PHONY: pipeline-smoke
pipeline-smoke: search-smoke model-caps hermes-smoke

.PHONY: correct-raw
correct-raw:
	$(DOCKER_RUN) make _correct-raw

.PHONY: fix
fix:
	$(call scrubbed_run,$(DOCKER_RUN) sh -c "make _setup && make _correct-raw && make _fix HERMES_FIX_REASONING=$(HERMES_FIX_REASONING) HERMES_FIX_TIMEOUT=$(HERMES_FIX_TIMEOUT) && make _merge")

.PHONY: merge
merge:
	$(DOCKER_RUN) make _merge SINCE="$(SINCE)"

# Render the README from the store WITHOUT merging raws: no `generated_utc` bump, no
# snapshot (issue #195). A template or docs change uses this, so the PR carries the
# README and nothing else — the store churn a `make merge` would add is not the change.
.PHONY: _render-readme
_render-readme:
	python3 scripts/update_trending.py --render-only

.PHONY: render-readme
render-readme:
	$(DOCKER_RUN) make _render-readme

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

.PHONY: engine-meta-capture
engine-meta-capture: ## Capture GitHub metadata for registry engines the offline test fixture lacks
	$(DOCKER_RUN) make _engine-meta-capture

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

# The filer's repair half (issue #174). `--issue` writes the baseline only when
# it FILES, so the "record the gap signature without filing" path had no target
# and no workflow: the flag was dead (rule 6d) and the ability to re-record a
# baseline lost by a rebase or a refresh PR closed without merging could not be
# exercised — so it could not be tested either. HOST-side like `data-gap-issue`
# (it writes data/gap_baseline.json as the caller, never as root through the
# container mount), and deliberately NOT in the refresh pipeline: run there it
# would set the baseline to the current gap set on every refresh and silently
# stop the analysis filing anything.
.PHONY: data-gap-baseline
data-gap-baseline:
	python3 scripts/data_gap_analysis.py --write-baseline

# The refresh run's window as a machine-readable block (issue #199): the REAL job
# timestamps read from the API (never a wall clock at PR-open time), with the marker
# line written by the shared helper (scripts/bot_markers.py, #197). The PR `aggregate`
# opens, and the data-gap issue `make data-gap-issue` files, both carry it — so an
# in-flight refresh is readable from the artifact a human actually opens.
# Host-run, like `data-gap-issue`: `gh` and the repo live on the runner, not in the
# image (issue #150).
.PHONY: refresh-run-block
refresh-run-block:
	python3 scripts/refresh_run_block.py render

# The implementation PR body is COMPOSED, never spelled in a workflow heredoc (issue
# #287): the body is what DECIDES whether the issue closes on merge (rule 6e), so its
# text belongs to a target that a test can run and that `make pr-closure` can read —
# not to a YAML block only a substring assertion could see. Both recipe lines are
# `@`-silenced: the workflow redirects this target's stdout into `pr-body.md`, so an
# echoed command line must never reach the body. Host-run, like `refresh-run-block`:
# the repo and `python3` live on the runner, not in the image.
.PHONY: refresh-pr-body
refresh-pr-body: ## Print the REFRESH PR body: the run's window block + the contract (issue #542)
	@python3 scripts/pr_body.py --for refresh $(if $(WINDOW_FILE),--window-file "$(WINDOW_FILE)",)

.PHONY: architecture-pr-body
architecture-pr-body: ## Print the ARCHITECTURE PR body (no closing keyword; issue #542)
	@python3 scripts/pr_body.py --for architecture --run-url "$(RUN_URL)"

.PHONY: pr-title
pr-title: ## Print the implementation PR TITLE for ISSUE=<n> [KIND=data-gap|tech-debt] (issue #541)
	@test -n "$(ISSUE)" || { echo "Usage: make pr-title ISSUE=<n> [KIND=data-gap|tech-debt]"; exit 1; }
	@python3 scripts/pr_body.py --issue "$(ISSUE)" --title --kind "$(if $(KIND),$(KIND),data-gap)"

.PHONY: pr-body
pr-body: ## Print the implementation PR body for ISSUE=<n> [BRANCH=<head branch>]
	@test -n "$(ISSUE)" || { echo "Usage: make pr-body ISSUE=<n> [BRANCH=<head branch>]"; exit 1; }
	@python3 scripts/pr_body.py --issue "$(ISSUE)" $(if $(BRANCH),--branch "$(BRANCH)",)

# ---- secret scan: no credential may reach the repo (issue #122) --------------
# gitleaks (MIT, the most widely adopted FOSS secret scanner) runs in ITS OWN
# container image, pinned by tag: the pipeline image has no docker inside, so the
# scanner cannot live in it. `make secret-scan` scans the working tree (staged
# files included) — run it BEFORE every push; CI runs it on every PR.
GITLEAKS_IMAGE := ghcr.io/gitleaks/gitleaks:v8.30.1@sha256:c00b6bd0aeb3071cbcb79009cb16a60dd9e0a7c60e2be9ab65d25e6bc8abbb7f
GITLEAKS_RUN := docker run --rm -v "$$PWD":/repo -w /repo $(GITLEAKS_IMAGE)

# ---- weekly container/dependency vulnerability scan (issue #715, Slice 1) ----
# One image PER scanner, each pinned to an immutable index digest (the
# tool-image seam in `scripts/action_pin_check.py` accepts `@sha256:…`), so the
# guard serves every scanner without an accumulating allowlist. `$$PWD` is
# bind-mounted at /workspace; each scanner runs against it in its own image,
# the same GITLEAKS_RUN shape above. The weekly `security-scan.yml` schedule +
# findings wiring + gate fail are Slices 2/3 of #715 — these targets are the
# pinned images the schedule will run.
TRIVY_IMAGE := ghcr.io/aquasecurity/trivy:0.76.1@sha256:790fd66d1697395d8693d1acaa1ea702406a20f109b6fc7bac8db623eca6c06c
TRIVY_RUN := docker run --rm -v "$$PWD":/workspace -w /workspace $(TRIVY_IMAGE)
CONTAINERFILE_IMAGE := ghcr.io/hadolint/hadolint:v2.12.0@sha256:30a8fd2e785ab6176eed53f74769e04f125afb2f74a6c52aef7d463583b6d45e
CONTAINERFILE_RUN := docker run --rm -v "$$PWD":/workspace -w /workspace $(CONTAINERFILE_IMAGE)
GRYPE_IMAGE := ghcr.io/anchore/grype:v0.104.2@sha256:7416f2fada8bd8f99095d955a6fed700b714b51ceb8150f838920932954b04aa
GRYPE_RUN := docker run --rm -v "$$PWD":/workspace -w /workspace $(GRYPE_IMAGE)
SYFT_IMAGE := ghcr.io/anchore/syft:v1.26.0@sha256:de078f51704a213906970b1475edd6006b8af50aa159852e125518237487b8c6
SYFT_RUN := docker run --rm -v "$$PWD":/workspace -w /workspace $(SYFT_IMAGE)

.PHONY: trivy-scan containerfile-scan grype-scan syft-sbom
trivy-scan: ## Trivy container/dependency vulnerability scan of the working tree (DIR=<scan dir>; exit 1 on a finding)
	$(TRIVY_RUN) fs --scanners vuln --quiet --no-progress --exit-code 1 $(if $(DIR),$(DIR),/workspace)

containerfile-scan: ## Containerfile/Dockerfile linter (hadolint) over the repo's Dockerfiles (exit 1 on a violation)
	$(CONTAINERFILE_RUN) /workspace/Dockerfile /workspace/Dockerfile.test /workspace/Dockerfile.python-env

grype-scan: ## Grype container/dependency vulnerability scan of the working tree (DIR=<scan dir>; exit 1 on a finding)
	$(GRYPE_RUN) dir:$(if $(DIR),$(DIR),/workspace) --quiet

syft-sbom: ## Syft software-bill-of-materials of the working tree (DIR=<scan dir>; writes the SBOM to stdout)
	@test -n "$(OUT)" || { echo "Usage: make syft-sbom OUT=<sbom.json> [DIR=<scan dir>]"; exit 1; }
	$(SYFT_RUN) dir:$(if $(DIR),$(DIR),/workspace) -o syft-json --quiet > $(OUT)

.PHONY: security-scan-self-test
security-scan-self-test: ## Prove the scanners are not a false green: a planted known-CVE fixture MUST fail trivy+grype, a clean one pass (issue #715)
	python3 scripts/security_scan_self_test.py

# The gate's file set is what git could commit (issue #836): gitleaks dir mode
# walks EVERY checked-out file and never consults .gitignore, so a local
# `make test` compiling the fixture fakes into tests/__pycache__/*.pyc used to go
# red on bytecode no commit could ever carry. The scan writes its findings as a
# JSON report; `scripts/secret_scan_report.py` is the ONE verdict — findings on
# paths git itself ignores (git check-ignore) are reported as gitignored
# artifacts, findings in committable files fail the gate.
# The report path is UNIQUE PER RUN (measured while fixing #836): a host-side
# `rm -f` immediately followed by the container creating the SAME path hits a
# stale virtiofs dentry — gitleaks FTLs "Report path is not writable: … no such
# file or directory" and the gate falsely reads BROKEN; a pause "fixes" it,
# which means the fixed name is a flaky gate. The container therefore only ever
# creates a path that never existed in the mount session; a glob sweep at the
# start clears a report left by a killed run.
.PHONY: _secret-scan
_secret-scan:
	@rm -f .secret-scan-report*.json; \
	REPORT=$$(python3 -c 'import time,os;print(".secret-scan-report-%d-%d.json" % (time.time_ns(), os.getpid()))'); \
	$(GITLEAKS_RUN) dir /repo --config /repo/.gitleaks.toml --redact --no-banner \
		--report-format json --report-path /repo/$$REPORT --exit-code 0; \
	python3 scripts/secret_scan_report.py --report $$REPORT; \
	STATUS=$$?; rm -f $$REPORT; exit $$STATUS

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
check-secret-output: python-env-image ## CI: fail when any file prints a secret's VALUE, passes it on a command line, xtraces it, dumps the environment around it, or commits a credential-shaped literal
	$(PYTHON_RUN) python3 scripts/check_secret_output.py check
secret-output-report: ## Show which files name a secret-shaped variable, and whether any prints it
	python3 scripts/check_secret_output.py report

# ---- agent-log redaction (issue #351) ----------------------------------------
# A bot job's agent stream must never be printed raw: it is captured to a file and
# THIS is the only thing that prints — the secret VALUES present in the environment
# are read BY NAME (the names live in scripts/check_secret_output.py, one list) and
# every spelling of each (raw, URL-encoded, base64) plus every credential SHAPE is
# replaced with `***`, and the printed part is bounded to a tail. Pure python +
# host filesystem, so a runner and a local run agree (like `make lint`).
# `make check-secret-output` refuses a workflow that captures a stream without it.
.PHONY: scrub-log
scrub-log: ## Redact a captured agent log and print at most a bounded tail, never the raw stream (FILE=… [LOG_OUT=…] [TAIL=40])
	@test -n "$(FILE)" || { echo "scrub-log: FILE=<the captured log> is required"; exit 2; }
	@python3 scripts/scrub_log.py --in "$(FILE)" $(if $(LOG_OUT),--out "$(LOG_OUT)",) --tail $(or $(TAIL),40)

# ---- commit-authorship guard (issue #317) -----------------------------------
# The only identities on this repo are Andy Holst and Asimov Agent. Nothing read a
# commit's MESSAGE or a commit's IDENTITY: `make secret-scan` reads credential
# values, `make check-secret-output` reads run-time leak shapes, `make pr-closure`
# reads the PR body — so a `Co-authored-by: Hermes Agent <hermes@nousresearch.com>`
# trailer landed on master. The trailer is SYNTHESIZED by GitHub at squash time
# from the AUTHOR identity of a commit inside the PR (measured: 054b0c8 is authored
# `Hermes Agent <hermes@nousresearch.com>`, committed `Andy Holst`, message with NO
# trailer), so the guard reads the identity AND the message. The default range is
# `origin/master..HEAD` — the commits a PR adds; history is never rewritten. A range
# that cannot be read fails loudly (exit 2), so a shallow CI checkout can never read
# as "no commits, pass" — the validate checkout uses `fetch-depth: 0`.
.PHONY: check-commit-authorship commit-authorship-report
check-commit-authorship: ## CI: fail when a commit's author/committer identity or a crediting trailer is not an allowed one (issue #317)
	python3 scripts/check_commit_authorship.py check
commit-authorship-report: ## Show every commit in the range with its author, committer and subject
	python3 scripts/check_commit_authorship.py report

# ---- fix-loop self-archive guard (issue #812, host-only like check-commit-authorship) --
# `scripts/fix_loop.sh` runs these two around every Hermes round. A round once ran
# `make openspec-archive` on its OWN change: the tree landed with the change moved
# into openspec/changes/archive/ while the PR was still open — green on every gate,
# and blind to `make openspec-archive-check` (#779), which reads the ACTIVE changes.
# `self-archive-snapshot` records the changes active after the loop's base merge
# (a merge may legitimately archive; a round may not); `self-archive-guard` refuses
# (and, with SELF_ARCHIVE_RESTORE=1, restores) a baseline-active change that vanished
# from the tree mid-run. Git-only: it reads the tree the loop is repairing.
.PHONY: self-archive-snapshot self-archive-guard
self-archive-snapshot: ## Record the OpenSpec changes active now as the fix loop's baseline (SELF_ARCHIVE_BASELINE)
	python3 scripts/self_archive_guard.py snapshot
self-archive-guard: ## Fail when a change active at the baseline is gone from the tree (issue #812); SELF_ARCHIVE_RESTORE=1 restores it first
	python3 scripts/self_archive_guard.py check

# ---- issue-bot: implement ONE filed data-gap issue (issue #113) --------------
# The issue's title + body are written to issue.md at the repo root by
# `.github/workflows/issue-bot.yml`; the agent reads it FIRST and implements
# exactly that issue, additive only, with everything wired to a make target.
.PHONY: _implement-issue
_implement-issue:
	hermes -z "Follow the preloaded skill issue-implement. Parameters: issue=#$(ISSUE); input=issue.md at the repo root; base=the freshly fetched origin/master that make base-check proved. Write triage.md first, then the change and findings.md. Do not push, do not merge, do not touch master." \
		-m $(HERMES_ALIAS) --reasoning $(HERMES_FIX_REASONING) $(HERMES_NONINTERACTIVE) -s issue-implement,bot-unattended

# The implementer's stream is redacted LIVE, inside the target (issue #629): the
# workflow used to capture `make implement-issue > implement.log` and scrub it only
# AFTER the agent ended, so the step printed nothing while the agent ran and the
# raw log lived in the runner's workspace the whole time. `scrubbed_run` (#591)
# masks each line before it reaches the console and writes both captures itself.
.PHONY: implement-issue
implement-issue:
	# `_setup` MUST run in the SAME container as the hermes call, exactly like
	# every other public hermes target (`search-*`, `fix`, `hermes-smoke`): it is
	# what writes `model.aliases.nous-deepseek.*` into that container's
	# ~/.hermes/config.yaml. Without it Hermes starts with NO alias and
	# auto-routes to whatever provider key is in the env — measured on the first
	# issue-bot run (#124, run 38502619350): `HF_TOKEN` -> Hugging Face ->
	# `HTTP 403 ... does not have sufficient permissions to call Inference Providers`.
	$(call scrubbed_run,$(DOCKER_RUN) sh -c "make _setup && make _implement-issue")
# Log names the run artifact uploads; the seam writes both captures (issue #629).
implement-issue: HERMES_LOG := implement.log
implement-issue: HERMES_LOG_SCRUBBED := implement.scrubbed.log

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

# The ONE line a sweep reads (issues #547/#548). The workflow used to re-derive its pick
# from `make issue-queue`'s row with a `sed` expression of its own, so the producer and
# the reader were two implementations of one contract and only one had a test against
# the real output. Here the producer names its own value: `issue=<n>`, or `issue=` when
# nothing is takeable. No slicing, no second parser in YAML.
.PHONY: issue-pick
issue-pick: ## Print the ONE key=value line a sweep reads (`issue=<n>` or `issue=`; issues #547/#548)
	@python3 scripts/issue_queue.py --pick --gap-hours $(REVIEW_GAP_HOURS) $(if $(RUN),--run $(RUN),)

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
issue-state: ## Print the issue's state: exit 0 = open, 4 = closed, 2 = unreadable (ISSUE=<n>, REPO=) (issue #520)
	python3 scripts/issue_verdict.py --state --issue "$(ISSUE)" $(if $(REPO),--repo "$(REPO)",)

issue-verdict: ## Apply the implementer's TRIAGE verdict from triage.md (ISSUE=<n>, TRIAGE_FILE=<path>)
	@python3 scripts/issue_verdict.py $(if $(ISSUE),--issue $(ISSUE),) $(if $(TRIAGE_FILE),--file $(TRIAGE_FILE),)

# The sweep's OWN outcome on a run that died before its verdict. The `implement` job speaks on
# the issue it picked only from a step that OWNS a comment (the verdict step, or the outcome
# comment gated on `verdict == implement`), so a run that started and then died (a resolver that
# could not read the issue, a refused base/image/smoke step, an agent that wrote no triage.md)
# posted the start marker and NOTHING ELSE: the issue kept showing an implementer in flight, and
# the queue lost that hour with no artifact on the queue item itself. The DECISION lives in
# scripts/sweep_outcome.py (rule 6d) — and it refuses one comment per run, deduped on the run id,
# so a re-run of the same run writes nothing. Every empty argument is TOLERATED (rule #487: an
# empty value forwarded into an int() crashed a whole sweep before it read a PR).
issue-outcome: ## Say on the picked issue that the sweep died before its verdict (ISSUE=<n>, REPO=, RUN_ID=, RUN_URL=, BRANCH=, STAGES=, VERDICT=, CLOSED=1)
	@python3 scripts/sweep_outcome.py --issue "$(ISSUE)" \
		$(if $(REPO),--repo "$(REPO)",) \
		$(if $(RUN_ID),--run-id "$(RUN_ID)",) \
		$(if $(RUN_URL),--run-url "$(RUN_URL)",) \
		$(if $(BRANCH),--branch "$(BRANCH)",) \
		$(if $(STAGES),--stages "$(STAGES)",) \
		$(if $(VERDICT),--verdict "$(VERDICT)",) \
		$(if $(CLOSED),--closed,) \
		--post

# The implementer's INPUT (issue #210): the WHOLE thread — title, body, every
# comment oldest-first with author and ISO8601Z, then the decision instruction the
# verdict answers. The reviewer was already told to read the whole thread; the
# implementer read only the body, so an issue whose fifth comment narrowed the
# request was implemented wrongly.
issue-thread: ## Print an issue's whole thread for the implementer (ISSUE=<n>, REPO=<owner/name>)
	@python3 scripts/issue_thread.py $(if $(ISSUE),--issue $(ISSUE),) $(if $(REPO),--repo $(REPO),)

# The queued-run alarm (issue #252): a job whose runner label matches nothing does not fail —
# it stays `queued` forever, so the run never concludes and every PR's checks sit at "pending".
# The DECISION lives in scripts/queued_run_alarm.py (rule 6d); the workflow calls this target.
# Exit 1 when a job is stuck, so the scheduled run goes red.
.PHONY: _freshness-alarm
_freshness-alarm:
	python3 scripts/freshness_alarm.py $(if $(REPO),--repo "$(REPO)",) $(if $(MAX_AGE_HOURS),--max-age-hours $(MAX_AGE_HOURS),)

.PHONY: freshness-alarm
freshness-alarm: ## Fail when the newest refresh snapshot is older than MAX_AGE_HOURS (issue #452)
	@$(MAKE) --no-print-directory _freshness-alarm

.PHONY: _bot-health
_bot-health:
	python3 scripts/bot_health.py $(if $(REPO),--repo "$(REPO)",) $(if $(LIMIT),--limit $(LIMIT),)

.PHONY: bot-health
bot-health: ## Fail when a cron pipeline's own scheduled runs are all red (issue #488)
	@$(MAKE) --no-print-directory _bot-health

# The owed-row ledger (issue #523): open issues carry `owed-row` markers naming the AGENTS.md
# §/row they are owed; this reads the ledger and reports each row as LANDED (with its
# AGENTS.md line) or OUTSTANDING, so a covered issue is closed on evidence, not on re-reading a
# thread. Host-side like the other gh-bound verifiers (it reads live issue state with the
# runner's gh); the DECISION lives in scripts/owed_rows_check.py (rule 6d). Exit 0 = a report
# was produced (a landed or outstanding row is news, not a failure); exit 2 = the ledger could
# not be read or a marker is malformed. Called by queued-alarm's alarm job, never a PR gate.
.PHONY: _owed-rows-check
_owed-rows-check:
	python3 scripts/owed_rows_check.py --repo "$(REPO)" $(if $(LIMIT),--limit $(LIMIT),)

.PHONY: owed-rows-check
owed-rows-check: ## Report the owed-row ledger: open issues' owed AGENTS.md rows vs the rulebook (REPO=<owner/name>, LIMIT=300; issue #523)
	@test -n "$(REPO)" || { echo "Usage: make owed-rows-check REPO=<owner/repo> [LIMIT=300]"; exit 1; }
	@$(MAKE) --no-print-directory _owed-rows-check

# Rule 1's mechanical guard (issue #959): "never push master directly" had no
# enforcement — master had zero branch protection and direct pushes landed
# (measured 2026-11-14: e571aa3, 4c7c555). The guard reads the base branch's
# protection (live `gh api` on the host, or a recorded payload via FROM_FILE —
# the fixture seam rule 6m allows) and refuses any shape that is not the one
# admitting ONLY qa-validate's auto-merge squash: strict required contexts
# naming `validate` + `live-smoke`, enforce_admins true. Exit 1 = absent or
# relaxed (named); exit 2 = the read itself failed, never a silent clean.
# Read-only: APPLYING the protection is an owner-approved repository-settings
# act (issue #959). Run by queued-alarm's alarm job (the scheduled half the
# issue names), never a PR gate — the check needs the owner PAT to read
# protection state, and a PR must not hold a secret it cannot read.
.PHONY: _check-branch-protection
_check-branch-protection:
	python3 scripts/check_branch_protection.py $(if $(REPO),--repo "$(REPO)",) --branch "$(if $(BRANCH),$(BRANCH),master)" $(if $(FROM_FILE),--from-file "$(FROM_FILE)",)

.PHONY: check-branch-protection
check-branch-protection: ## Guard Rule 1: the base branch must carry auto-merge-shaped branch protection (REPO=<owner/name> or FROM_FILE=<recorded.json>, BRANCH=master; issue #959)
	@test -n "$(REPO)" || test -n "$(FROM_FILE)" || { echo "Usage: make check-branch-protection REPO=<owner/repo> [BRANCH=master] [FROM_FILE=<recorded.json>]"; exit 1; }
	@$(MAKE) --no-print-directory _check-branch-protection

.PHONY: queued-alarm
sweep-alarm: ## Fail loudly when the WEEKLY issue sweep has not been DELIVERED (REPO=<owner/name>; the window is the script's weekly default unless MAX_AGE_HOURS is supplied — issue #804)
	@test -n "$(REPO)" || { echo "Usage: make sweep-alarm REPO=<owner/repo> [MAX_AGE_HOURS=<hours>]"; exit 1; }
	python3 scripts/sweep_alarm.py --repo "$(REPO)" $(if $(MAX_AGE_HOURS),--max-age-hours "$(MAX_AGE_HOURS)",)

queued-alarm: ## Report jobs stuck in `queued` far too long, and optionally comment once per affected run (REPO=<owner/name>, MINUTES=30, COMMENT=1)
	@test -n "$(REPO)" || { echo "Usage: make queued-alarm REPO=<owner/repo> [MINUTES=30] [COMMENT=1]"; exit 1; }
	python3 scripts/queued_run_alarm.py --repo "$(REPO)" --minutes "$(if $(MINUTES),$(MINUTES),30)" $(if $(COMMENT),--comment,)

# The master-alarm (issue #527): a deterministic gate in qa-validate's `validate` job goes red on
# a push to master AFTER `auto-merge`, and every repair path in this repo needs a PR — so a red
# master has no repairer and stays red until a human notices (measured: run 39625708799). This
# alarm reads the NEWEST push-to-master qa-validate run and exits 1 when it is red, so the
# scheduled alarm job goes RED in the Actions tab instead of staying quiet. The DECISION lives in
# scripts/master_alarm.py (rule 6d); the KEEPER/ALARM table for every validate gate lives beside
# it. Host-side (needs gh + Makefile), called by queued-alarm's alarm job, never a PR gate.
.PHONY: _master-alarm
_master-alarm:
	python3 scripts/master_alarm.py --repo "$(REPO)" $(if $(LIMIT),--limit $(LIMIT),)

.PHONY: master-alarm
master-alarm: ## Fail when the newest push-to-master qa-validate run is red, so a broken master has a signal (REPO=<owner/name>, LIMIT=10; issue #527)
	@test -n "$(REPO)" || { echo "Usage: make master-alarm REPO=<owner/repo> [LIMIT=10]"; exit 1; }
	@$(MAKE) --no-print-directory _master-alarm

# After a failure, KEEP TRACKING the main pipelines (issue #802). The alarms above SAY a run is
# red; this filer READS it: for every concluded-bad main-pipeline run inside the window that is
# not yet in the ledger `data/pipeline_failures.json`, it fetches the failed job's log (one
# retry), extracts a bounded error block, scrubs it through the shared redactor (rule 3f) and
# files ONE `tech-debt` issue carrying the run, the scrubbed block and the exact `make`
# reproduction command — deduped by the ledger run id and the registered `pipeline-run-failure`
# marker. The DECISION lives in scripts/pipeline_failure_issue.py (rule 6d); the fix lands as its
# OWN reviewed change (rule 6g) — this filer never fixes anything. Host-side, called by
# queued-alarm's alarm job after the alarms.
.PHONY: _pipeline-failure-issue
_pipeline-failure-issue:
	python3 scripts/pipeline_failure_issue.py --repo "$(REPO)" --window-hours "$(if $(WINDOW_HOURS),$(WINDOW_HOURS),192)" $(if $(DRY),--dry,) $(if $(LEDGER),--ledger "$(LEDGER)",)

.PHONY: pipeline-failure-issue
pipeline-failure-issue: ## Diagnose each unfiled main-pipeline failure from its logs and file it as a tech-debt issue (REPO=<owner/name>, WINDOW_HOURS=192, DRY=1 previews; issue #802)
	@test -n "$(REPO)" || { echo "Usage: make pipeline-failure-issue REPO=<owner/repo> [WINDOW_HOURS=192] [DRY=1]"; exit 1; }
	@$(MAKE) --no-print-directory _pipeline-failure-issue

# The QA half of the same rule (issue #802): every ledger entry whose fix PR has landed must name
# a guard test under tests/ that `make test` collects, and an issue CLOSED with no fix PR and no
# guard is RED — closed-without-a-guard is reintroducible, which is the defect this gate exists to
# refuse. Open entries are reported, never red. Runs in qa-validate's validate job on every PR.
.PHONY: _pipeline-failure-guard-check
_pipeline-failure-guard-check:
	python3 scripts/pipeline_failure_guard_check.py $(if $(REPO),--repo "$(REPO)",) $(if $(LEDGER),--ledger "$(LEDGER)",)

.PHONY: pipeline-failure-guard-check
pipeline-failure-guard-check: ## Refuse a closed pipeline-failure issue with no fix PR + guard test (REPO=<owner/name> optional; issue #802)
	@$(MAKE) --no-print-directory _pipeline-failure-guard-check

# The ledger itself must LAND on master (the sweep runs on a checkout it never pushes to, and
# direct pushes to master are refused — rule 1). Same pattern as the architecture-bot PR: the
# filer appends to `data/pipeline_failures.json`, and this body composes the PR that commits the
# append. It implements no issue, so it carries NO closing keyword (rule 6e) — the issues it
# records are referenced, never closed by the ledger PR.
.PHONY: pipeline-failure-ledger-pr-body
pipeline-failure-ledger-pr-body: ## Print the ledger-update PR body from data/pipeline_failures.json (no closing keyword; issue #802)
	@python3 scripts/pipeline_failure_issue.py --print-pr-body $(if $(LEDGER),--ledger "$(LEDGER)",)

# The code-review bot (issue #253): it reads the TREE and the PIPELINES and files what is
# actually wrong. Every check in scripts/code_review.py is DETERMINISTIC (no model), so a scan
# is free and cannot invent a finding; `file` writes ONE issue per NEW finding, marker-deduped
# and capped per run. Its whole output is issues (rule 6g): it never edits code, never merges.
.PHONY: code-review-scan code-review-file
code-review-scan: ## The code-review bot's checks: tree + pipelines -> findings (REPO=<owner/name>, STATIC=1 skips the checks that read the GitHub API, JSON=1 machine output; writes nothing)
	@test -n "$(REPO)" || { echo "Usage: make code-review-scan REPO=<owner/repo> [STATIC=1] [JSON=1]"; exit 1; }
	python3 scripts/code_review.py scan --repo "$(REPO)" $(if $(STATIC),--static-only,) $(if $(JSON),--json,)
code-review-file: ## File ONE issue per NEW code-review finding, capped per run (REPO=<owner/name>, CAP= issues per run, DRY=1 previews) — never edits code, never merges
	@test -n "$(REPO)" || { echo "Usage: make code-review-file REPO=<owner/repo> [CAP=3] [DRY=1]"; exit 1; }
	python3 scripts/code_review.py file --repo "$(REPO)" --cap "$(if $(CAP),$(CAP),3)" $(if $(DRY),--dry,)

.PHONY: review-issue-pick
review-issue-pick: ## Choose the ONE issue this review run works (action=/issue=/path=)
	@python3 scripts/issue_review.py --pick --gap-hours $(REVIEW_GAP_HOURS) $(if $(RUN),--run $(RUN),)

# Every reviewer target that takes ISSUE= takes the NUMBER the pick printed. A value
# carrying diagnostics is a parse defect upstream and MUST fail here, naming it,
# instead of dying inside argparse (measured: `--finish 266 position=-1 window=open
# reason=decided:agent:refined` -> `unrecognized arguments`, run 39040689085; issue #344).
.PHONY: _review-issue-number
_review-issue-number:
	@case "$(ISSUE)" in ''|*[!0-9]*) echo "ISSUE must be the issue NUMBER the pick printed, got '$(ISSUE)' - the pick's diagnostics must never ride on the issue= line (issue #344)"; exit 2;; esac

# Open the reviewer's window BEFORE anything is written: the `review-in-progress`
# label is what `issue-bot`'s pick defers to, and (body path) one marker comment
# `<!-- issue-review: <ISO8601Z> -->` records the instant for the next run.
.PHONY: review-issue-mark
review-issue-mark: _review-issue-number ## Open the reviewer's window on ISSUE= (PATH=body|window)
	@python3 scripts/issue_review.py --mark $(ISSUE) --path $(PATH) $(if $(RUN),--run $(RUN),)

# The TOCTOU re-check, run after the mark and BEFORE the write: the implementer
# may have started while the review was being prepared, in which case the body
# must not be touched (`PATH=window` re-checks the reply path instead).
.PHONY: review-issue-guard
review-issue-guard: _review-issue-number ## Re-check that ISSUE= may still be written (PATH=body|window)
	python3 scripts/issue_review.py --guard $(ISSUE) --for $(PATH) --gap-hours $(REVIEW_GAP_HOURS) $(if $(RUN),--run $(RUN),)

.PHONY: review-issue-body-hash
review-issue-body-hash: _review-issue-number ## Print the body hash of ISSUE= (proves the window path edited nothing)
	@python3 scripts/issue_review.py --body-hash $(ISSUE)

.PHONY: review-issue-check-markers
review-issue-check-markers: _review-issue-number ## Fail when FILE= dropped an invisible marker from ISSUE='s body
	python3 scripts/issue_review.py --check-markers $(ISSUE) --file $(if $(FILE),$(FILE),issue-body.md)

.PHONY: review-issue-finish
review-issue-finish: _review-issue-number ## Close the reviewer's window on ISSUE=
	python3 scripts/issue_review.py --finish $(ISSUE)

# The reviewer's judgement, in the container like every other hermes call. The
# issue (body + comments) is written to issue.md by the workflow; the agent
# writes the REWRITTEN body to issue-body.md and its one summary comment to
# comment.md - the workflow does the `gh` write, so no token ever reaches the
# container.
.PHONY: _review-issue
_review-issue:
	hermes -z "Follow the preloaded skill issue-review on its BODY path. Parameters: issue=#$(ISSUE); input=issue.md at the repo root (body and whole thread). Write issue-body.md, comment.md and findings.md." \
		-m $(HERMES_ALIAS) --reasoning $(HERMES_FIX_REASONING) $(HERMES_NONINTERACTIVE) -s issue-review,bot-unattended

# Live redaction inside the target, the same seam as `implement-issue` (issue #629).
.PHONY: review-issue
review-issue:
	# `_setup` in the SAME container as the hermes call, exactly like
	# `implement-issue` (#124: without the alias Hermes auto-routes to whatever
	# provider key is in the env -> HF_TOKEN -> HTTP 403).
	$(call scrubbed_run,$(DOCKER_RUN) sh -c "make _setup && make _review-issue")
review-issue: HERMES_LOG := review.log
review-issue: HERMES_LOG_SCRUBBED := review.scrubbed.log

# The WINDOW path: an implementer has STARTED this issue. The body is off-limits
# for REVIEW_GAP_HOURS, so the reviewer replies instead - one bounded comment
# with the reminders its review found - and files what it found as its own
# `tech-debt` issues. It writes comment.md (the reply) and findings.md, and it
# must NOT write issue-body.md: the workflow proves the body is unchanged.
.PHONY: _review-issue-window
_review-issue-window:
	hermes -z "Follow the preloaded skill issue-review on its WINDOW path. Parameters: issue=#$(ISSUE); input=issue.md at the repo root. Write comment.md and findings.md, never issue-body.md." \
		-m $(HERMES_ALIAS) --reasoning $(HERMES_FIX_REASONING) $(HERMES_NONINTERACTIVE) -s issue-review,bot-unattended

# Live redaction inside the target, the same seam (issue #629).
.PHONY: review-issue-window
review-issue-window:
	$(call scrubbed_run,$(DOCKER_RUN) sh -c "make _setup && make _review-issue-window")
review-issue-window: HERMES_LOG := review.log
review-issue-window: HERMES_LOG_SCRUBBED := review.scrubbed.log

.PHONY: test
test:
	@out="$$(mktemp)"; \
	$(TEST_RUN) make _test 2>&1 | tee "$$out"; rc=$${PIPESTATUS[0]}; \
	if ! grep -q '^\[test\] ' "$$out"; then \
		echo "[harness] FAIL: 'make test' captured NO '[test]' line from the suite (suite rc=$$rc) — the suite's stream never reached the capture; an rc over an empty capture is UNVERIFIABLE (issue #911)" >&2; \
		rm -f "$$out"; exit 1; \
	fi; \
	n_ok=$$(grep -c '^\[test\] ok ' "$$out" || true); \
	echo "[harness] captured $$n_ok per-module trace(s) and the verdict line (suite rc=$$rc)" >&2; \
	rm -f "$$out"; exit $$rc

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
