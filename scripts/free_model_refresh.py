#!/usr/bin/env python3
"""Refresh the chain's FREE tier from the LIVE Nous catalogue (issue #1195).

`agents/model_chain.json` is the ONE chain (issue #1140): free Nous models first, the
credential-less local strata tier second (issue #1192), the paid Makefile pin LAST. The free
set is a LIVE truth, not a remembered list: the catalogue moved from 413 to 415 models between
two reads while the `:free` set stayed at 5, and a new free model (the next Qwen) can only enter
the chain when someone re-reads. This seam is that re-read on a cadence — the weekly
`free-model-refresh` job of `refresh-bot` (the ONLY scheduled pipeline, rule 6t) runs it and
lands any change through the shared `make keeper-pr` seam, never a direct push.

What it does, and ONLY this:
- reads `GET <chain.base_url>/models` with the credential the chain names, by NAME (rule 3e —
  the value is never printed, measured for length, or written anywhere);
- keeps every `:free` id with its REAL `context_length` from that payload (rule 2 — an id that
  traces to no read is invented data);
- updates ONLY the free steps: surviving ids keep their order and aliases, new ids are appended
  as fallbacks with generated aliases, retired ids are dropped, and a surviving model's
  `context_window` follows the live read;
- NEVER touches the `local_fallback` tier or the paid `last_resort` (their bytes survive);
- records the read in `measured` (at/how) and appends a `refresh_history` row (additive, rule 3b);
- writes NOTHING when the live free set equals the chain's (a no-op is the healthy case).

Exit codes: 0 refreshed or no change, 1 the live set cannot form a legal free tier (no `:free`
model at all — a chain without one breaks its own gate), 2 the read or the credential failed
(never a silent clean). `--dry-run` prints the plan and writes nothing; `--pr-body` prints the
keeper PR body (no closing keyword — a refresh implements no issue, it refs #1195).
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from require_env import main as require_env_main  # noqa: E402  (ONE credential pre-flight, #357)

ROOT = Path(__file__).resolve().parent.parent
CHAIN_REL = "agents/model_chain.json"
FREE_ROLES = ("primary", "fallback")
EXIT_OK, EXIT_PROBLEM, EXIT_UNDECIDABLE = 0, 1, 2
ALIAS_RE = re.compile(r"^[a-z0-9][a-z0-9-]{1,31}$")


def utc_now() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


def read_live_models(base_url: str, key_env: str) -> tuple[list[dict], str | None]:
    """GET <base_url>/models with the bearer the NAME resolves to. Returns (models, fatal)."""
    key = os.environ.get(key_env, "")
    url = base_url.rstrip("/") + "/models"
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {key}"})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, OSError) as exc:
        return [], f"GET {url} failed: {exc} — the free tier cannot be refreshed from a read that did not happen"
    except json.JSONDecodeError as exc:
        return [], f"GET {url} answered unparseable JSON: {exc}"
    models = payload.get("data") if isinstance(payload, dict) else None
    if not isinstance(models, list):
        return [], f"GET {url} answered no `data` list — not a models payload"
    return [m for m in models if isinstance(m, dict) and m.get("id")], None


def free_models(models: list[dict]) -> tuple[list[dict], str | None]:
    """Every `:free` id with its REAL context_length — a free id without one is unreadable truth."""
    free = []
    for m in models:
        mid = str(m["id"])
        if not mid.endswith(":free"):
            continue
        ctx = m.get("context_length")
        if not isinstance(ctx, int) or ctx <= 0:
            return [], f"free model {mid} carries no usable context_length in the live payload ({ctx!r}) — rule 2 refuses an unmeasured window"
        free.append({"id": mid, "context_length": ctx})
    return sorted(free, key=lambda x: x["id"]), None


def generated_alias(model_id: str, taken: set[str]) -> str:
    """A deterministic lowercase alias for a new free id, unique against every alias in the chain."""
    slug = model_id.split("/")[-1].removesuffix(":free").lower()
    slug = re.sub(r"[^a-z0-9]+", "-", slug).strip("-")[:25] or "model"
    base = f"free-{slug}"
    alias, n = base, 2
    while alias in taken or not ALIAS_RE.match(alias):
        alias = f"{base[:28]}-{n}"
        n += 1
    return alias


def refresh_chain(data: dict, live_free: list[dict], stamp: str) -> tuple[dict | None, list[str]]:
    """The refreshed chain, or None when the live free set equals the chain's. Never touches non-free steps."""
    chain = data.get("chain")
    if not isinstance(chain, list) or not chain:
        return None, ["the chain carries no `chain` list to refresh"]
    free_entries = [e for e in chain if e.get("role") in FREE_ROLES]
    others = [e for e in chain if e.get("role") not in FREE_ROLES]
    live_by_id = {m["id"]: m for m in live_free}
    if not live_by_id:
        return None, ["the live catalogue carries NO `:free` model — refreshing would empty the free tier and break the chain's own gate; refusing, nothing written"]

    surviving = [e for e in free_entries if e.get("model") in live_by_id]
    retired = [e for e in free_entries if e.get("model") not in live_by_id]
    known = {e.get("model") for e in free_entries}
    added = [m for m in live_free if m["id"] not in known]

    changes: list[str] = []
    new_free: list[dict] = []
    taken = {str(e.get("alias")) for e in chain}
    for e in surviving:
        entry = dict(e)
        live_ctx = live_by_id[entry["model"]]["context_length"]
        if entry.get("context_window") != live_ctx:
            changes.append(f"context {entry['alias']}: {entry.get('context_window')} -> {live_ctx} (live read)")
            entry["context_window"] = live_ctx
        new_free.append(entry)
    for m in added:
        alias = generated_alias(m["id"], taken)
        taken.add(alias)
        new_free.append({"alias": alias, "model": m["id"], "role": "fallback",
                         "context_window": m["context_length"]})
        changes.append(f"added {alias} ({m['id']}, ctx={m['context_length']})")
    for e in retired:
        changes.append(f"retired {e.get('alias')} ({e.get('model')}) — no longer `:free` in the live catalogue")
    if not new_free:
        return None, ["the refresh would leave no free step — refusing, nothing written"]
    for i, e in enumerate(new_free):
        want = "primary" if i == 0 else "fallback"
        if e.get("role") != want:
            changes.append(f"role {e['alias']}: {e.get('role')} -> {want}")
            e["role"] = want

    if not changes:
        return None, []

    new_data = dict(data)
    new_data["chain"] = new_free + others
    measured = dict(data.get("measured") or {})
    history = list(measured.get("refresh_history") or [])
    history.append({"at": stamp, "added": [m["id"] for m in added],
                    "retired": [e.get("model") for e in retired],
                    "free_count": len(new_free)})
    measured["at"] = stamp[:10]
    measured["how"] = (f"GET /v1/models with the credential passed by NAME in the environment "
                       f"(refreshed {stamp}): {len(live_free)} models carrying the `:free` pricing "
                       f"suffix, every free `model` id below present in that payload with the "
                       f"`context_length` quoted below.")
    measured["refresh_history"] = history
    new_data["measured"] = measured
    return new_data, changes


def pr_body(run_url: str, changes: list[str], free_count: int) -> str:
    lines = [
        "Keeper: the weekly free-tier refresh re-read the LIVE Nous catalogue and updated the chain.",
        "",
        f"- free models after the refresh: {free_count}",
        "- the `local_fallback` tier and the paid `last_resort` are byte-untouched",
        "- every id and context_window traces to the read named in `measured` (rule 2)",
        "",
        "Changes:",
    ]
    lines += [f"- {c}" for c in changes] or ["- none (no-op)"]
    lines += ["", f"Run: {run_url}", "", "Refs #1195 (the refresh seam), refs #1140 (the chain).",
              "This PR implements no issue and closes none — it is a generated-artifact keeper."]
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    ap.add_argument("--write", action="store_true", help="refresh the chain from the live catalogue (default)")
    ap.add_argument("--dry-run", action="store_true", help="print the plan, write nothing")
    ap.add_argument("--pr-body", action="store_true", help="print the keeper PR body (RUN_URL env)")
    ap.add_argument("--root", default=str(ROOT), help="repository root to read (tests plant a scratch tree)")
    args = ap.parse_args(argv)
    root = Path(args.root).resolve()

    if args.pr_body:
        # The body is composed from the LAST refresh's own record — never invented.
        path = root / CHAIN_REL
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            print(f"[free-refresh] UNDECIDABLE: {CHAIN_REL} unreadable: {exc}", file=sys.stderr)
            return EXIT_UNDECIDABLE
        history = (data.get("measured") or {}).get("refresh_history") or []
        free_count = sum(1 for e in data.get("chain", []) if e.get("role") in FREE_ROLES)
        last = history[-1] if history else {}
        changes = ([f"added {i}" for i in last.get("added", [])]
                   + [f"retired {i}" for i in last.get("retired", [])])
        print(pr_body(os.environ.get("RUN_URL", "(run URL not provided)"), changes, free_count))
        return EXIT_OK

    path = root / CHAIN_REL
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"[free-refresh] UNDECIDABLE: {CHAIN_REL} unreadable: {exc}", file=sys.stderr)
        return EXIT_UNDECIDABLE
    base_url = str(data.get("base_url") or "")
    key_env = str(data.get("key_env") or "")
    if (not base_url or not key_env) and str(data.get("provider") or "") == "nous":
        # The built-in `nous` provider carries its own inference endpoint and Portal
        # session, so a clean chain names neither (issue #1203). The LIVE model
        # CATALOGUE read still needs an endpoint and a credential NAME: fall back to
        # Nous's catalogue URL and the registered key NAME. A chain that names both
        # keeps its own values — nothing is removed or overwritten (rule 3b).
        base_url = base_url or "https://inference-api.nousresearch.com/v1"
        key_env = key_env or "NOUS_API_KEY"
    if not base_url or not key_env:
        print(f"[free-refresh] UNDECIDABLE: {CHAIN_REL} names no base_url/key_env to read", file=sys.stderr)
        return EXIT_UNDECIDABLE

    rc = require_env_main([key_env, "--why",
                           "the free-tier refresh authenticates the live catalogue read by NAME, "
                           "or it cannot tell a retired model from an unreadable endpoint"])
    if rc != 0:
        print(f"[free-refresh] REFUSED: the chain names {key_env} and that credential is absent — nothing written",
              file=sys.stderr)
        return EXIT_UNDECIDABLE

    models, fatal = read_live_models(base_url, key_env)
    if fatal:
        print(f"[free-refresh] UNDECIDABLE: {fatal}", file=sys.stderr)
        return EXIT_UNDECIDABLE
    live_free, fatal = free_models(models)
    if fatal:
        print(f"[free-refresh] UNDECIDABLE: {fatal}", file=sys.stderr)
        return EXIT_UNDECIDABLE

    stamp = utc_now().strftime("%Y-%m-%dT%H:%M:%SZ")
    new_data, changes = refresh_chain(data, live_free, stamp)
    if new_data is None:
        if changes:
            for c in changes:
                print(f"[free-refresh] REFUSED: {c}", file=sys.stderr)
            return EXIT_PROBLEM
        print(f"[free-refresh] no change: the live free set ({len(live_free)} models) equals the chain's — nothing written")
        return EXIT_OK

    for c in changes:
        print(f"[free-refresh] {c}")
    if args.dry_run:
        print(f"[free-refresh] DRY RUN: {len(changes)} change(s) planned, nothing written")
        return EXIT_OK
    path.write_text(json.dumps(new_data, indent=2) + "\n", encoding="utf-8")
    print(f"[free-refresh] refreshed {CHAIN_REL}: {len(live_free)} free models, read {stamp} (render the lanes next: make agent-profile-model-render)")
    return EXIT_OK


if __name__ == "__main__":
    raise SystemExit(main())
