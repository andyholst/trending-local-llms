#!/usr/bin/env python3
"""ONE derivation of the fleet's live test fixtures (issues #1744/#1745/#1750).

The weekly free refresh reads the live Nous catalogue and rewrites
``agents/model_chain.json``. Three guard modules used to FREEZE a snapshot of that
catalogue as literals (``SHIPPED_FREE``, ``default: meituan/longcat-2.5:free`` …),
so every legitimate refresh that retired/added a free model turned those guards
red while the seam under test stayed correct. Issue #1750 found the SAME frozen
shape one tier over: the credential-less local tier's bare model id, alias,
provider and endpoint were literals too, so a future local swap would red the
guards for the same non-regression. Rule 6d: one implementation, so the tests,
the guard and any future reader derive from the SAME source through HERE.

Nothing in this module invents a model. Every value returned is read from the
chain dict it is given — the shipped chain for the real tests, a synthetic chain
for the guard that proves the fixtures follow the data and not a frozen literal.
"""
from __future__ import annotations

import json
from pathlib import Path

FREE_ROLES = ("primary", "fallback")
LOCAL_ROLE = "local_fallback"
PAID_ROLE = "last_resort"


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


def local_step(chain: dict) -> dict:
    """The single credential-less local tier entry (role=local_fallback, issue #1192)."""
    return next(e for e in chain["chain"] if e.get("role") == LOCAL_ROLE)


def local_model(chain: dict) -> str:
    """The local step's BARE server model id (never a provider-qualified name)."""
    return local_step(chain)["model"]


def local_alias(chain: dict) -> str:
    """The alias the local tier is rendered under in a lane config."""
    return local_step(chain)["alias"]


def local_provider(chain: dict) -> str:
    """The local tier's OWN provider — the local tier is not a `nous` step."""
    return local_step(chain)["provider"]


def local_endpoint(chain: dict) -> str:
    """The local tier's OWN base_url — the credential-less local server."""
    return local_step(chain)["base_url"]


def paid_alias(chain: dict) -> str:
    """The paid last_resort alias — the rendered boundary after the local alias block."""
    return next(e for e in chain["chain"] if e.get("role") == PAID_ROLE)["alias"]
