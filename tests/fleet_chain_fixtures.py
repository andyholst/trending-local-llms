#!/usr/bin/env python3
"""ONE derivation of the fleet's live free-tier test fixtures (issues #1744/#1745).

The weekly free refresh reads the live Nous catalogue and rewrites
``agents/model_chain.json``. Three guard modules used to FREEZE a snapshot of that
catalogue as literals (``SHIPPED_FREE``, ``default: meituan/longcat-2.5:free`` …),
so every legitimate refresh that retired/added a free model turned those guards
red while the seam under test stayed correct. Rule 6d: one implementation, so the
tests, the guard and any future reader derive from the SAME source through HERE.

Nothing in this module invents a model. Every value returned is read from the
chain dict it is given — the shipped chain for the real tests, a synthetic chain
for the guard that proves the fixtures follow the data and not a frozen literal.
"""
from __future__ import annotations

import json
from pathlib import Path

FREE_ROLES = ("primary", "fallback")


def read_chain(path: str | Path) -> dict:
    """Read the ONE chain source at TEST time, never a baked-in snapshot."""
    return json.loads(Path(path).read_text(encoding="utf-8"))


def free_steps(chain: dict) -> list[tuple[str, int]]:
    """``(model, context_window)`` for every free step, in chain order."""
    return [(e["model"], e["context_window"]) for e in chain["chain"]
            if e["role"] in FREE_ROLES]


def primary_step(chain: dict) -> dict:
    """The single free primary entry (model, alias, context_window)."""
    return next(e for e in chain["chain"] if e["role"] == "primary")


def alias_order(chain: dict) -> list[str]:
    """Every step's alias in chain order — the renderer's reported order."""
    return [e["alias"] for e in chain["chain"]]


def fallback_models(chain: dict) -> list[str]:
    """Model ids in ``fallback_providers`` order: every step after the primary."""
    return [e["model"] for e in chain["chain"][1:]]


def default_line(chain: dict) -> str:
    """The rendered config's ``default:`` needle for the chain's primary."""
    return f"default: {primary_step(chain)['model']}"
