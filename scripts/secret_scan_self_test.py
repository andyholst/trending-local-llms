#!/usr/bin/env python3
"""Prove the secret scan actually detects a credential (issue #122).

A scanner that quietly does nothing is worse than no scanner: the pipeline looks
green and a key leaks. This plants a WELL-FORMED, fake credential in a throwaway
directory and REQUIRES gitleaks to flag it (with the repo's own
`.gitleaks.toml`, so a rule/allowlist added to make a real finding go away also
has to survive here), then scans a clean directory and REQUIRES no finding.

  python3 scripts/secret_scan_self_test.py        # exit 0 = both directions OK

Runs the pinned gitleaks container, exactly like `make secret-scan` does.
Stdlib only. Needs docker.
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
IMAGE = "ghcr.io/gitleaks/gitleaks:v8.30.1"
CONFIG = ROOT / ".gitleaks.toml"

# Deliberately credential-shaped and NOT allowlisted: a GitHub PAT, a Hugging
# Face token, an OpenAI key and an AWS secret. Fake randomness — never a real key.
# Built from parts ON PURPOSE: this file must not itself look like a leak, so the
# repo scan needs no allowlist for it and an allowlist can never mask the probe.
_PARTS = (
    ("GITHUB_TOKEN", "ghp_", "9xK2mQ7pL4vR8tN1sW6yB3jD5hF0gA2cE4uI"),
    ("HF_TOKEN", "hf_", "Qz7mK2pR9vT4wX1yB6nD3jL8sA5cE0gU2iO"),
    ("OPENAI_API_KEY", "sk-proj-", "Zq7mK2pR9vT4wX1yB6nD3jL8sA5cE0gU2iO7pQ4rS8tV"),
    ("AWS_SECRET_ACCESS_KEY", "", "wJalrXUtnFEMI/K7MDENG/bPxRfiCYzEXAMPL3"),
)
FAKE = ("# throwaway probe file - fake credential shapes, never a real key\n"
        + "".join(f"{name}={prefix}{body}\n" for name, prefix, body in _PARTS))
CLEAN = "generated_utc = \"2026-10-14T06:00:00Z\"\nnote = nothing to see here\n"


def scan(path: Path) -> list[dict]:
    """Run gitleaks over `path` and return its findings (empty = clean)."""
    # the report has to land somewhere the host can read: mount its directory too
    report = path.parent / f"{path.name}-report.json"
    cmd = ["docker", "run", "--rm",
           "-v", f"{path}:/scan", "-v", f"{report.parent}:/out",
           "-v", f"{CONFIG}:/cfg/.gitleaks.toml:ro",
           IMAGE, "dir", "/scan",
           "--config", "/cfg/.gitleaks.toml",
           "--report-format", "json", "--report-path", f"/out/{report.name}",
           "--redact", "--no-banner", "--exit-code", "0"]
    subprocess.run(cmd, check=False, capture_output=True, text=True)
    if not report.exists():
        raise SystemExit(f"[secret-self-test] gitleaks wrote no report ({report})")
    return json.loads(report.read_text() or "[]")


def main() -> int:
    if shutil.which("docker") is None:
        print("[secret-self-test] docker is required (the scanner runs in its own image)")
        return 1
    if not CONFIG.exists():
        print(f"[secret-self-test] {CONFIG} missing")
        return 1

    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        dirty, clean = root / "dirty", root / "clean"
        dirty.mkdir()
        clean.mkdir()
        (dirty / "creds.env").write_text(FAKE)
        (clean / "store.json").write_text(CLEAN)

        found = scan(dirty)
        rules = sorted({f.get("RuleID", "?") for f in found})
        if not found:
            print("[secret-self-test] FAIL: the planted credential shapes were NOT detected — "
                  "the scan is a false green")
            return 1
        print(f"[secret-self-test] detected {len(found)} finding(s): {', '.join(rules)}")
        if any("ghp_" in json.dumps(f.get("Secret", "")) for f in found):
            print("[secret-self-test] WARNING: the report carried an unredacted secret (--redact is off?)")

        leaks = scan(clean)
        if leaks:
            print(f"[secret-self-test] FAIL: the clean fixture reported {len(leaks)} finding(s)")
            return 1
        print("[secret-self-test] clean fixture: no findings — the config does not over-match")

    print("[secret-self-test] OK: a credential is caught, a clean tree is not")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
