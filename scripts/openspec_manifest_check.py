#!/usr/bin/env python3
"""Verify the published OpenSpec CLI image tag answers every required platform.

This seam keeps its own Makefile target (`make openspec-manifest-check`,
issue #919) and its own report label, but the manifest verdict itself is the
ONE implementation in `scripts/image_manifest_check.py` (issue #958, rule 6d):
the base image, the test image and the OpenSpec image publish under the same
contract, so they verify through one shared unit. This file adds nothing but
the OpenSpec-specific entry point and label — no second copy of the
manifest-reading or verdict logic, which is exactly what would drift silently.
"""

from __future__ import annotations

import sys

from image_manifest_check import check, run  # noqa: F401 — check stays importable

LABEL = "openspec-manifest-check"


def main(argv: list[str] | None = None) -> int:
    return run(argv if argv is not None else sys.argv[1:], LABEL)


if __name__ == "__main__":
    sys.exit(main())
