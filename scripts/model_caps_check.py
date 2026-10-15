#!/usr/bin/env python3
"""Live model-catalog guard for the Hermes search/fix model.

Reads the endpoint's /v1/models and FAILS (exit 1) when:
  - the configured model id is not served,
  - the configured max_tokens exceeds the model's real max_completion_tokens
    (the endpoint accepts a larger value SILENTLY and clamps it — 384000 hid
    a 65,536 cap until a search burned it),
  - the model does not accept a `reasoning` parameter (then --reasoning none
    cannot turn thinking off and the budget burns again).
Exit 0 when everything fits.

NO SILENT SKIP (issue #209): with no NOUS_API_KEY this used to print
`SKIP: NOUS_API_KEY not set` and exit 0 — a green pre-flight that had checked
nothing, on the step that guards the same 20-minute leg as `make hermes-smoke`
(AGENTS.md: "a skipped test is a loud FAILURE, never a silent skip"). It now FAILS,
naming the variable and what could not be checked. A caller that knowingly runs
without a key may ask for the old behaviour with LIVE_CHECK_ALLOW_UNCONFIGURED=1,
which reports NOT CONFIGURED instead; CI never sets it.

Usage: python3 scripts/model_caps_check.py --base URL --model ID --max-tokens N
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.request


def evaluate(catalog: dict, model: str, max_tokens: int) -> list[str]:
    """Pure check over a /v1/models payload. Returns a list of problems."""
    entry = next((m for m in catalog.get("data", []) if m.get("id") == model), None)
    if entry is None:
        return [f"model {model!r} is not served by this endpoint"]
    problems = []
    cap = (entry.get("top_provider") or {}).get("max_completion_tokens")
    if isinstance(cap, int) and max_tokens > cap:
        problems.append(f"max_tokens {max_tokens} > provider max_completion_tokens {cap} "
                        f"(silently clamped; set HERMES_MAX_TOKENS <= {cap})")
    params = entry.get("supported_parameters") or []
    if params and "reasoning" not in params:
        problems.append(f"model does not accept 'reasoning' (supported: {params}); "
                        f"--reasoning none cannot disable thinking")
    return problems


def fetch(base: str, key: str) -> dict:
    req = urllib.request.Request(base.rstrip("/") + "/models", headers={"Authorization": f"Bearer {key}"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode("utf-8"))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--base", required=True)
    ap.add_argument("--model", required=True)
    ap.add_argument("--max-tokens", type=int, required=True)
    ap.add_argument("--catalog", help="read /v1/models JSON from this file (offline)")
    args = ap.parse_args()
    if args.catalog:
        catalog = json.loads(open(args.catalog).read())
    else:
        key = os.environ.get("NOUS_API_KEY", "").strip()
        if not key:
            # The explicit, non-default opt-out (see the module docstring).
            if os.environ.get("LIVE_CHECK_ALLOW_UNCONFIGURED", "") == "1":
                print("[model-caps] NOT CONFIGURED: NOUS_API_KEY is unset, so the endpoint cannot be read.")
                print("[model-caps] LIVE_CHECK_ALLOW_UNCONFIGURED=1 was set deliberately — this check did NOT run.")
                return 0
            print("[model-caps] FAIL: NOUS_API_KEY is not set.")
            print("[model-caps]   Without it the endpoint cannot be read, so the model id, its real")
            print("[model-caps]   max_completion_tokens and its `reasoning` support are all unverified —")
            print("[model-caps]   a green pre-flight here would tell you nothing.")
            print("[model-caps] Set NOUS_API_KEY, or run with LIVE_CHECK_ALLOW_UNCONFIGURED=1 to skip the")
            print("[model-caps] live check deliberately (CI never sets that flag).")
            return 1
        try:
            catalog = fetch(args.base, key)
        except Exception as e:  # noqa: BLE001
            print(f"[model-caps] FAIL: could not read {args.base}/models: {e}")
            return 1
    problems = evaluate(catalog, args.model, args.max_tokens)
    for p in problems:
        print(f"[model-caps] FAIL: {p}")
    if problems:
        return 1
    print(f"[model-caps] OK: {args.model} served; max_tokens {args.max_tokens} fits; accepts reasoning")
    return 0


if __name__ == "__main__":
    sys.exit(main())
