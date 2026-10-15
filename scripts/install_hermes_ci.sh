#!/usr/bin/env bash
# install_hermes_ci.sh — the ONE way the Hermes CLI enters this repo's image.
#
# Why a seam (issue #207): the Dockerfile used to fetch the CLI with
# `ADD https://hermes-agent.nousresearch.com/install.sh`, which cannot be
# overridden by a build arg and fails as an opaque fetch error when the URL
# moves. With this script the Dockerfile carries the pin visibly:
#
#     ARG HERMES_INSTALL_URL=...   ARG HERMES_PACKAGE=...
#
# and a maintainer can point the build at a mirror or a pinned release without
# editing the Dockerfile. The mirror of `asimov-agent/llgenie`'s install seam
# (their issue #238, `containers/agent/Dockerfile`).
#
# Order, first hit wins:
#   1. `hermes` already on PATH  -> use it (a base image that ships the CLI)
#   2. HERMES_INSTALL_URL set    -> fetch that installer and run it
#   3. `uv` available            -> `uv tool install "$HERMES_PACKAGE"`
#   4. none of the above         -> FAIL LOUDLY
#
# The last branch is the point: an agent image without an agent is worse than no
# image at all, because every bot job would run and fail later, inside a model
# call, with a confusing error. So a build that cannot install Hermes must stop
# here.
#
# This script NEVER handles a credential. The CLI's key arrives at RUN time as
# `-e NOUS_API_KEY` and is resolved by NAME through the alias's `key_env`
# (AGENTS.md rule 3e); nothing here reads, prints or writes a key.

set -uo pipefail

HERMES_INSTALL_URL="${HERMES_INSTALL_URL:-}"
HERMES_PACKAGE="${HERMES_PACKAGE:-hermes-agent}"
# install.sh drops the CLI in ~/.local/bin; make it discoverable for the checks
# below without depending on a login shell (the image build runs `bash`).
export PATH="${HOME:-/root}/.local/bin:${PATH}"

say() { echo "[install-hermes] $*"; }

dump_version() {
	command -v hermes >/dev/null 2>&1 || return 1
	say "hermes at $(command -v hermes)"
	hermes --version 2>&1 | head -2 || true
}

# 1. already installed.
if command -v hermes >/dev/null 2>&1; then
	say "already installed; using it (no download)"
	dump_version
	exit 0
fi

# 2. the configured installer (the default is the official one).
if [ -n "$HERMES_INSTALL_URL" ]; then
	say "installing from HERMES_INSTALL_URL=$HERMES_INSTALL_URL"
	tmp="$(mktemp)"
	if ! curl -fsSL "$HERMES_INSTALL_URL" -o "$tmp"; then
		say "could not download the installer from $HERMES_INSTALL_URL"
		rm -f "$tmp"
		exit 1
	fi
	if ! bash "$tmp"; then
		say "the installer at $HERMES_INSTALL_URL failed"
		rm -f "$tmp"
		exit 1
	fi
	rm -f "$tmp"
	if command -v hermes >/dev/null 2>&1; then
		dump_version
		exit 0
	fi
	say "the installer finished but put no 'hermes' on PATH (checked ${HOME:-/root}/.local/bin)"
fi

# 3. the package-manager fallback.
if command -v uv >/dev/null 2>&1; then
	say "falling back to: uv tool install $HERMES_PACKAGE"
	if uv tool install "$HERMES_PACKAGE" && command -v hermes >/dev/null 2>&1; then
		dump_version
		exit 0
	fi
	say "uv tool install $HERMES_PACKAGE did not produce a working 'hermes'"
fi

# 4. nothing worked — say exactly what was tried.
say "FAIL: could not install the Hermes CLI"
say "  tried: an existing 'hermes' on PATH"
say "  tried: HERMES_INSTALL_URL='${HERMES_INSTALL_URL:-<unset>}'"
say "  tried: uv tool install ${HERMES_PACKAGE} (uv: $(command -v uv || echo 'not installed'))"
say "an agent image without an agent must not build: fix one of the three and rebuild"
exit 1
