#!/usr/bin/env python3
"""Live model-catalog guard for the Hermes search/fix model.

Reads the endpoint's /v1/models and FAILS (exit 1) when:
  - the configured model id is not served,
  - the configured max_tokens exceeds the model's real max_completion_tokens
    (the endpoint accepts a larger value SILENTLY and clamps it — 384000 hid
    a 65,536 cap until a search burned it),
  - the model does not accept a `reasoning` parameter (then --reasoning none
    cannot turn thinking off and the budget burns again).
Exit 0 when everything fits; SKIP (exit 0) when NOUS_API_KEY is unset.

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
            print("[model-caps] SKIP: NOUS_API_KEY not set")
            return 0
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
