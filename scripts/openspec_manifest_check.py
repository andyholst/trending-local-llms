#!/usr/bin/env python3
"""Verify a published OpenSpec CLI image tag answers EVERY required platform.

The `openspec-image` job of refresh-bot.yml publishes a multi-architecture
manifest (linux/amd64 + linux/arm64, issue #919). A manifest that answers only
one architecture makes `docker pull` die on the other host with
`no matching manifest for linux/arm64/v8` — the exact issue-#767 failure a fresh
arm64 checkout still hits. This check is what keeps the publisher and the
seam's pull path in step: run it against the tag a refresh just published (or
reused) BEFORE any run is allowed to pull it.

Verdict (exit codes, all loud):
  0  the manifest lists every required platform (the default: linux/amd64 + linux/arm64)
  1  the manifest is published but answers fewer platforms than required
  2  the check cannot decide: no --tag given, `docker manifest inspect` failed,
     or the output is not a manifest document at all — never a silent clean
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys

REQUIRED_PLATFORMS = (("linux", "amd64"), ("linux", "arm64"))


def _read_manifest(tag: str) -> tuple[dict | None, str]:
    """`docker manifest inspect <tag>` -> (document, error). One read, no retry:
    a registry we cannot read is a loud 2, not a flaky pass."""
    try:
        proc = subprocess.run(
            ["docker", "manifest", "inspect", tag],
            capture_output=True, text=True, timeout=120,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return None, f"docker manifest inspect could not run: {exc}"
    if proc.returncode != 0:
        return None, (f"docker manifest inspect exited {proc.returncode}: "
                      f"{(proc.stderr or proc.stdout).strip()[:400]}")
    text = proc.stdout.strip()
    if not text:
        return None, "docker manifest inspect printed no document"
    try:
        return json.loads(text), ""
    except json.JSONDecodeError as exc:
        return None, f"manifest document is not JSON: {exc}"


def _platforms(doc: dict) -> list[tuple[str, str]]:
    """(os, architecture) pairs a manifest index answers, de-duplicated."""
    seen: list[tuple[str, str]] = []
    for entry in doc.get("manifests") or []:
        plat = entry.get("platform") or {}
        os_, arch = plat.get("os"), plat.get("architecture")
        if os_ and arch and (os_, arch) not in seen:
            seen.append((os_, arch))
    return seen


def check(tag: str, required: tuple[tuple[str, str], ...] = REQUIRED_PLATFORMS) -> int:
    doc, err = _read_manifest(tag)
    if doc is None:
        print(f"[openspec-manifest-check] REFUSED (undecidable): {err}")
        return 2
    present = _platforms(doc)
    if not present:
        # A single-image manifest carries no manifest list: exactly the
        # one-architecture publication this guard exists to refuse.
        print(f"[openspec-manifest-check] REFUSED: {tag} is not a manifest "
              f"list — a single-architecture publication. Required: "
              f"{', '.join(f'{o}/{a}' for o, a in required)}")
        return 1
    missing = [p for p in required if p not in present]
    print(f"[openspec-manifest-check] {tag} answers: "
          f"{', '.join(f'{o}/{a}' for o, a in present)}")
    if missing:
        print(f"[openspec-manifest-check] REFUSED: {tag} lacks "
              f"{', '.join(f'{o}/{a}' for o, a in missing)} — the publisher "
              f"must declare platforms {', '.join(f'{o}/{a}' for o, a in required)} "
              f"(issue #919); a host of the missing architecture would die at "
              f"`docker pull` with 'no matching manifest'")
        return 1
    print(f"[openspec-manifest-check] OK: {tag} answers every required "
          f"platform ({', '.join(f'{o}/{a}' for o, a in required)})")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tag", default="",
                        help="exact published content-hash tag to verify "
                             "(the openspec-image job publishes it)")
    parser.add_argument("--require", action="append", default=[],
                        help="required platform as os/arch (repeatable; "
                             "default linux/amd64 and linux/arm64)")
    args = parser.parse_args(argv)
    if not args.tag:
        print("[openspec-manifest-check] REFUSED (undecidable): --tag is "
              "required — the check verifies ONE exact published tag")
        return 2
    required: tuple[tuple[str, str], ...]
    if args.require:
        parsed = []
        for item in args.require:
            parts = item.split("/")
            if len(parts) != 2 or not all(parts):
                print(f"[openspec-manifest-check] REFUSED (undecidable): bad "
                      f"--require {item!r} (want os/arch)")
                return 2
            parsed.append((parts[0], parts[1]))
        required = tuple(parsed)
    else:
        required = REQUIRED_PLATFORMS
    return check(args.tag, required)


if __name__ == "__main__":
    sys.exit(main())
