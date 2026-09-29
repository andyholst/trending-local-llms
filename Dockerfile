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
        libffi-dev liblzma-dev \
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

# Then the rest of the repo (invalidates only when source changes)
COPY . .

# Bake a real Hermes update into the image. `make update-hermes` runs the
# weekly update only on Sunday (scripts/hermes_update_needed.sh) — the image
# is (re)built only on Sunday, so this keeps Hermes fresh exactly weekly
# without re-downloading it on every daily run.
RUN export PATH="/root/.local/bin:$PATH" && make update-hermes

# Make hermes available on PATH for every RUN/CMD
ENV PATH="/root/.local/bin:$PATH"

# Default: run the full deterministic QA
CMD ["make", "validate"]
