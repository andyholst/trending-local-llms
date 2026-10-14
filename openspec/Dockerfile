# OpenSpec CLI container for trending-local-llms.
#
# Runs the official @fission-ai/openspec CLI inside a Node image. The repository
# is bind-mounted at /repo (the working dir), so `openspec new change <name>` and
# `openspec validate <name>` operate on THIS repository's openspec/ tree.
#
# Build/ensure the image through the Makefile, never by hand:
#     make openspec-image            # pull the published hash tag, else build
#
# Drive the CLI through the Makefile targets:
#     make openspec-new NAME=<change>        # openspec new change <change>
#     make openspec-validate NAME=<change>   # openspec validate <change>
#     make openspec-check                    # validate all + tasks + index
#     make openspec-status                   # openspec status
#     make openspec-shell                    # interactive shell into the repo
#
# Mount layout inside the container:
#     /repo   -> repository root (bind mount, rw): contains openspec/ + repo files
#
# There is exactly ONE code path: the CLI runs in this image, locally and in CI
# (both pull the published tag for this Dockerfile's content hash, or build it).
# No host npm install, no second implementation — see AGENTS.md.
FROM node:22-alpine

# openspec CLI (pinned; @fission-ai/openspec). Keep in step with
# OPENSPEC_VERSION in the Makefile — the make targets are what drive it.
ARG OPENSPEC_VERSION=1.10.0
RUN npm install -g @fission-ai/openspec@${OPENSPEC_VERSION} \
    && openspec --version

WORKDIR /repo

# The repo is mounted at /repo by the Makefile targets.
CMD ["openspec", "--help"]
