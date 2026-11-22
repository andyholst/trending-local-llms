#!/usr/bin/env python3
"""Offline tests for scripts/agent_hermes_smoke.py (issue #1273)."""
from __future__ import annotations

import importlib.util
import json
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("ahs", ROOT / "scripts/agent_hermes_smoke.py")
assert spec is not None and spec.loader is not None
ahs = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ahs)

PASSED = FAILED = 0


def check(label: str, ok: bool, detail: str = "") -> None:
    global PASSED, FAILED
    if ok:
        PASSED += 1
    else:
        FAILED += 1
        print(f"  FAIL {label} {detail}".rstrip())


def fixture(tmp: Path) -> Path:
    (tmp / "scripts").mkdir()
    (tmp / "agents").mkdir()
    (tmp / "Makefile").write_text("HERMES_VERSION ?= 0.23.3\nhermes config set model.aliases.nous-deepseek.key_env NOUS_API_KEY\n")
    (tmp / "Dockerfile").write_text('ARG HERMES_VERSION="0.23.3"\n')
    (tmp / "scripts/install_hermes_ci.sh").write_text("install pinned hermes\n")
    (tmp / "agents/model_chain.json").write_text(json.dumps({
        "provider": "custom", "key_env": "NOUS_API_KEY",
        "measured": {"endpoint": "https://inference-api.nousresearch.com/v1"},
        "chain": [{"alias": "free", "model": "m/x:free", "role": "primary"}],
    }))
    return tmp


def main() -> int:
    with tempfile.TemporaryDirectory() as td:
        root = fixture(Path(td))
        check("baseline image config is clean", not ahs.problems(root), str(ahs.problems(root)))
        check("pin parser reads Makefile", ahs.pin((root / "Makefile").read_text()) == "0.23.3")

        import copy

        cases = {
            "Dockerfile pin drift": lambda d: (d / "Dockerfile").write_text('ARG HERMES_VERSION="0.23.1"\n'),
            "missing installer": lambda d: (d / "scripts/install_hermes_ci.sh").unlink(),
            "no primary model": lambda d: (d / "agents/model_chain.json").write_text(
                json.dumps({"provider": "custom", "key_env": "NOUS_API_KEY",
                            "measured": {"endpoint": "https://x/v1"}, "chain": []})),
            "no credential name": lambda d: (
                (d / "Makefile").write_text("HERMES_VERSION ?= 0.23.3\n"),
                (d / "agents/model_chain.json").write_text(json.dumps({
                    "provider": "custom", "measured": {"endpoint": "https://x/v1"},
                    "chain": [{"model": "m/x:free", "role": "primary"}]})),
            ),
            "insecure endpoint": lambda d: (d / "agents/model_chain.json").write_text(
                json.dumps({"provider": "custom", "key_env": "NOUS_API_KEY",
                            "measured": {"endpoint": "http://127.0.0.1:1/v1"},
                            "chain": [{"model": "m/x:free", "role": "primary"}]})),
            "credential value leak": lambda d: (d / "scripts/install_hermes_ci.sh").write_text(
                "sk-abcdefghijklmnopqrstuvwxyz012345\n"),
        }
        for name, break_it in cases.items():
            bad_root = Path(tempfile.mkdtemp(dir=td))
            import shutil
            shutil.rmtree(bad_root)
            shutil.copytree(root, bad_root)
            break_it(bad_root)
            check(f"refused: {name}", bool(ahs.problems(bad_root)), name)

    print(f"PASSED {PASSED} | FAILED {FAILED}")
    return 1 if FAILED else 0


if __name__ == "__main__":
    raise SystemExit(main())
