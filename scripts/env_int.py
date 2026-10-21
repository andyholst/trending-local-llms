#!/usr/bin/env python3
"""Read an integer setting from the environment — EMPTY means MISSING (issue #487).

The measured failure: `.github/workflows/pr-health.yml` calls
`make pr-health REPO=… COMMENT=1`, the public target always forwards
`MAX_FIXBOT_COMMITS="$(MAX_FIXBOT_COMMITS)"`, and so the recipe ran with
`MAX_FIXBOT_COMMITS=` (set, empty). `int(os.environ.get("MAX_FIXBOT_COMMITS", "2"))`
treats *unset* as the default but *empty* as a value, and `int("")` raised:

    ValueError: invalid literal for int() with base 10: ''
    make: *** [Makefile:354: pr-health] Error 2

The sweep that exists to make a SILENT PR loud was itself silently refused on every
run since #475 — the guard was red for a reason nobody reads.

This is the same rule AGENTS.md §2.3d already states for credentials ("an empty value
counts as missing: that is the shape a missing GitHub secret takes at run time",
issue #357), applied to settings. One implementation, so the six scripts that read an
integer setting cannot drift apart again (`tests/test_env_int.py` fails on a new bare
`int(os.environ…)`).

A NON-NUMERIC value is a loud failure naming the variable and what it held: a typo
must never be silently read as the default.
"""
from __future__ import annotations

import os


class EnvSettingError(ValueError):
    """An environment setting is present but not an integer."""


def env_int(name: str, default: int) -> int:
    """`int(os.environ[name])`, where unset OR blank ("" / "  ") yields `default`."""
    return int(_raw(name, default))


def env_float(name: str, default: float) -> float:
    """`float(os.environ[name])`, where unset OR blank yields `default` (issue #487)."""
    return float(_raw(name, default))


def _raw(name: str, default: object) -> str:
    raw = os.environ.get(name)
    if raw is None or not raw.strip():
        return str(default)
    raw = raw.strip()
    try:
        int(raw) if isinstance(default, int) else float(raw)
    except ValueError:
        raise EnvSettingError(
            f"{name}={raw!r} is not a number — unset it (or leave it empty) for the "
            f"default ({default}), or give it a whole {'number' if isinstance(default, int) else 'decimal'}") from None
    return raw
