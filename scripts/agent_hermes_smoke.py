#!/usr/bin/env python3
"""Offline smoke for the new agent Docker image's Hermes call path (issue #1273).

Proves the image's baked pin, its installer, and the chain-derived request shape are
internally consistent WITHOUT a network call and WITHOUT reading a credential value.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

VALUE_TOKEN = re.compile(r"(?:gh[pousr]_|sk-|eyJ)[A-Za-z0-9_\-]{16,}")


def pin(text: str) -> str:
    m = re.search(r"^HERMES_VERSION\s*\?=\s*[\"']?([\d.]+)[\"']?", text, re.M)
    return m.group(1) if m else ""


def arg_pin(text: str) -> str:
    m = re.search(r'^ARG HERMES_VERSION[=\s]+[\"\' ]*([\d.]+)', text, re.M)
    return m.group(1) if m else ""


def problems(root: Path) -> list[str]:
    bad: list[str] = []
    mk = root / "Makefile"; df = root / "Dockerfile"
    if not mk.exists() or not df.exists():
        return ["Makefile or Dockerfile missing"]
    mk_text = mk.read_text(encoding="utf-8")
    a, b = pin(mk_text), arg_pin(df.read_text())
    if not a or not re.fullmatch(r"\d+\.\d+\.\d+", a):
        bad.append(f"Makefile HERMES_VERSION pin unreadable: {a!r}")
    if not b or b != a:
        bad.append(f"Dockerfile ARG HERMES_VERSION {b!r} != Makefile pin {a!r}")
    installer = root / "scripts/install_hermes_ci.sh"
    if not installer.exists():
        bad.append("scripts/install_hermes_ci.sh missing from image build")
        return bad
    chain = root / "agents/model_chain.json"
    if not chain.exists():
        bad.append("agents/model_chain.json missing")
        return bad
    data = json.loads(chain.read_text(encoding="utf-8"))
    primaries = [step for step in data.get("chain", []) if step.get("role") == "primary"]
    if not primaries:
        bad.append("chain has no primary model for a Hermes call")
    endpoint = (data.get("measured") or {}).get("endpoint", "")
    if not endpoint.startswith("https://"):
        bad.append(f"chain endpoint is not an https base_url: {endpoint!r}")
    km = re.search(r"key_env\s+([A-Z][A-Z0-9_]*)", mk_text)
    key_name = data.get("key_env") if isinstance(data.get("key_env"), str) else (km.group(1) if km else "")
    if not key_name:
        bad.append("no credential NAME (key_env) in Makefile or chain")
    request = {
        "model": primaries[0]["model"] if primaries else "",
        "provider": data.get("provider", ""),
        "base_url": endpoint,
        "key_env": key_name,
    }
    blob = json.dumps(request) + installer.read_text(encoding="utf-8", errors="replace")
    if VALUE_TOKEN.search(blob):
        bad.append("credential VALUE-like token in image config (rule 3e)")
    return bad


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root", default=".")
    args = ap.parse_args(argv)
    bad = problems(Path(args.root))
    if bad:
        for b in bad:
            print(f"[agent-hermes-smoke] FAIL {b}")
        return 1
    print("[agent-hermes-smoke] OK pin, installer and chain-derived request are consistent; no network, no values")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
