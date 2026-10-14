# trending-local-llms — CI/local container (self-contained)
#
# Everything the pipeline needs is baked into this image: the pinned Python
# deps AND the Hermes CLI. Every make command (search, fix, merge, validate,
# test) runs inside this container, so the pipeline is agnostic to host system
# changes — no reliance on the runner's Python, pip, or Hermes install.
#
# Build:  docker build -t trending-local-llms:latest .
# Run:    docker run --rm -v "$PWD":/workspace -w /workspace \
#           -e NOUS_API_KEY -e FIRECRAWL_API_KEY trending-local-llms:latest make validate
#
# Hermes files (CLI, skills, config) are downloaded into the image at build
# time under /root/.hermes and /root/.local/bin.

FROM python:3.12-slim

# System deps (git for the newline-terminator check; curl for Hermes install; make for the Makefile;
# build-essential + libs for Hermes' managed-Python install step)
RUN apt-get update && apt-get install -y --no-install-recommends \
        git curl ca-certificates make build-essential \
        libssl-dev zlib1g-dev libbz2-dev libreadline-dev libsqlite3-dev \
        libffi-dev liblzma-dev faketime \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /workspace

# Install pinned Python deps FIRST (cache layer) — only re-runs when requirements.txt changes
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Install the Hermes CLI into the image (downloaded at build time).
# Cache-friendly: only re-runs when the install script hash changes.
ADD https://hermes-agent.nousresearch.com/install.sh /tmp/hermes-install.sh
RUN bash /tmp/hermes-install.sh \
    && rm -f /tmp/hermes-install.sh \
    && export PATH="/root/.local/bin:$PATH" \
    && hermes --version

# Install the nerve supervision plugin (Hermes plugin catalog:
# https://github.com/keeltrace/hermes-nerve) as CODE ONLY, pinned — like the
# catalog — to an exact 40-character commit.
#
# The plugin's credential is NEVER part of this image: it reaches the process
# only as a `-e` env var at run time (Makefile DOCKER_RUN / TEST_RUN), and the
# plugin resolves it by NAME through the Hermes secret scope. Measured at the
# pinned revision, hermes_nerve/client.py::PROVIDER_API_KEY_ENV:
#   openrouter (the default jev_provider) -> OPENROUTER_API_KEY
#   typesafe                              -> TYPESAFE_API_KEY
#   opencode                              -> OPENCODE_API_KEY
# There is no JEV_KEY upstream, so wiring that name would be a key nothing
# reads; the pipeline wires the verified name (AGENTS.md rule 3e). No ENV, no
# COPYed config.yaml, no literal — a key in an image layer is readable by anyone
# who pulls the public GHCR image.
ARG NERVE_PLUGIN_REF=3de7d94982b7a2cb87c829e4b2366ced927d8fed
RUN export PATH="/root/.local/bin:$PATH" \
    && hermes plugins install keeltrace/hermes-nerve --ref "$NERVE_PLUGIN_REF" --yes-deps

# Then the rest of the repo (invalidates only when source changes)
COPY . .

# Bake a real Hermes update into the image. `make _update-hermes` (the HOST
# recipe, not the docker wrapper `update-hermes` — there is no docker inside
# the image build) runs the weekly update only on Sunday
# (scripts/hermes_update_needed.sh) — the image is (re)built only on Sunday,
# so this keeps Hermes fresh exactly weekly without re-downloading it on
# every daily run.
RUN export PATH="/root/.local/bin:$PATH" && make _update-hermes

# Make hermes available on PATH for every RUN/CMD
ENV PATH="/root/.local/bin:$PATH"

# Default: run the full deterministic QA
CMD ["make", "validate"]
