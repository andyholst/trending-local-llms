#!/usr/bin/env python3
"""One definition of a Hugging Face identifier: `owner/repo`.

The store, the raw snapshots, the README and the link checker all agree that
`hf` (and a format's `hf`) is an `owner/repo` id — the URL is BUILT from it. A
value that already IS a URL therefore ends up prefixed again, which is a
malformed link rather than a missing one. Measured (issue #165, refresh PR #160,
branch `ci/trending-refresh-20261014-1138`): every model of
`data/raw/amd-20261014-111033.json` carried

    "hf": "https://huggingface.co/Qwen/Qwen3.6-35B-A3B"

and `validate` failed the PR with

    https://huggingface.co/https://huggingface.co/Qwen/Qwen3.6-35B-A3B does not resolve

`normalise()` accepts what the search actually emits — a bare id, a full link
(http/https, `huggingface.co` or `hf.co`, `www.`, a `tree|blob|resolve|raw` path,
a query or fragment, a trailing slash or `.git`) — and returns `owner/repo`.
Anything that cannot be reduced to `owner/repo` becomes the empty string, so
callers treat it as MISSING (flagged for re-search) instead of silently carrying
a value that will fail later.

Usage:  from hf_id import normalise
"""

from __future__ import annotations

import re

# Hosts that mean "this is a link to a model", with or without a scheme/www.
_HOST_RE = re.compile(r"^(?:www\.)?(?:huggingface\.co|hf\.co)/(.*)$", re.I)
# A path INSIDE the repo (a file or a branch view) — the repo is what we want.
_IN_REPO_RE = re.compile(r"/(?:tree|blob|resolve|raw|commits?)/.*$", re.I)


def normalise(value: str) -> str:
    """`owner/repo` for any HF id or link; "" when it cannot be reduced to one."""
    v = (value or "").strip()
    if not v:
        return ""
    url_like = "://" in v or _HOST_RE.match(v) is not None
    v = re.sub(r"^[a-z]+://", "", v, flags=re.I)      # scheme
    v = v.split("?", 1)[0].split("#", 1)[0]           # query / fragment
    m = _HOST_RE.match(v)
    if m:
        v = m.group(1)
    v = _IN_REPO_RE.sub("", v)
    v = v.rstrip("/")
    if v.endswith(".git"):
        v = v[:-4]
    parts = [p for p in v.split("/") if p]
    if len(parts) >= 2:
        return f"{parts[0]}/{parts[1]}"
    # A bare id that is not a URL is passed through (validate judges it); a URL
    # that cannot become owner/repo is MISSING, never a value to build on.
    return "" if url_like else v
