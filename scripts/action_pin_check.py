#!/usr/bin/env python3
"""Immutable-SHA pin guard for GitHub Actions workflow refs and tool-image refs.

Issue #735 (#714 Slice 1, folding #717). Two surfaces, one fail-closed guard:

  1. WORKFLOW USES  — every third-party `uses: <owner>/<repo>@<ref>` in
     `.github/workflows/**` must be a 40-hex commit SHA or on the explicit
     own-repo allow-ref list. Own reusable workflows (`./.github/workflows/…`)
     are exempt. Fails closed: a ref that is neither is a violation.

  2. TOOL-IMAGE SEAM — a third-party container image tag named in the Makefile
     `*_IMAGE :=` refs, `scripts/*.py` or a Dockerfile `ARG` must be pinned: a
     digest (`@sha256:…`) or the fleet-owned `<sha12>` tag form (e.g.
     `dockerfile-<sha12>`), NOT a bare mutable `:vX.Y.Z` / `:latest`.

Current mutable refs live on an explicit allowlist, each with an "allow-till
<issue>" deadline (the migration slice that will pin it): the workflow `uses:`
tags currently in the tree (allow-till #714's migration slice) and gitleaks
`v8.30.1` (allow-till #715). A NEW mutable third-party ref not on that list is
refused — the guard is real on master-as-is because it catches the next mutable
ref, while the current ones are tracked, not silently tolerated.

As of #737 (#714 Slice 2) the workflow allowlist is EMPTY — all 37 third-party
workflow `uses:` refs are pinned to immutable 40-hex SHAs, so only the gitleaks
image ref remains on the image allowlist (allow-till #715). A NEW mutable
third-party workflow ref or tool-image tag is refused.

Run:  python3 scripts/action_pin_check.py [--root DIR]
Exit: 0 = every third-party workflow ref is a 40-hex SHA or allowlisted, and
          every third-party tool image is pinned or allowlisted
      1 = at least one mutable third-party ref (fails closed)
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

#: A third-party `uses:` ref: `<owner>/<repo>@<ref>`. Own reusable workflows
#: (`./.github/workflows/…`) and docker:// refs are not third-party actions.
_USES = re.compile(r"uses:\s*([A-Za-z0-9._-]+/[A-Za-z0-9._-]+)@(\S+)")
_OWN_REUSABLE = re.compile(r"uses:\s*\./")
_DOCKER_REF = re.compile(r"uses:\s*docker://")
#: A 40-hex commit SHA — the only immutable action ref.
_SHA40 = re.compile(r"^[0-9a-f]{40}$")
#: A pinned image ref: `@sha256:<64 hex>` digest, or the fleet-owned
#: `<name>-<12 hex>` tag form (the ensure_image.py scheme).
_DIGEST = re.compile(r"@sha256:[0-9a-f]{64}$")
_SHA12_TAG = re.compile(r":([A-Za-z0-9._-]+)-[0-9a-f]{12}$")
#: A third-party container image ref: `<registry-host>/<owner>/<repo>:<tag>` where
#: the first segment is a registry host (contains a dot, e.g. `ghcr.io`, `docker.io`,
#: `quay.io`). Requiring the host excludes file paths (`path/to/file.py:1412`), URLs
#: and bare `owner/repo` strings — the tool-image seam is about registry refs.
#: Fleet-owned images are `trending-local-llms*` (local consumer names) and
#: `ghcr.io/andyholst/trending-local-llms*` (published) — those are the fleet's
#: OWN images, exempt from the third-party pin rule.
_IMAGE = re.compile(
    r"([A-Za-z0-9._-]+\.[a-z]{2,}/[A-Za-z0-9._/-]+(?::[A-Za-z0-9._-]+)?)"
)
_FLEET_OWNED = ("trending-local-llms", "ghcr.io/andyholst/trending-local-llms")

#: The explicit own-repo allow-ref list for workflow `uses:` — each entry is a
#: mutable third-party tag that is NOT yet pinned, with the slice that will pin
#: it. A mutable third-party ref NOT here is refused. Keys are
#: `<owner>/<repo>@<ref>`.
#:
#: As of #737 (#714 Slice 2) this list is EMPTY: all 37 third-party workflow
#: `uses:` refs in `.github/workflows/**` are pinned to immutable 40-hex commit
#: SHAs, so the #714 allow-till deadline is satisfied. A NEW mutable third-party
#: ref is refused (fails closed). Own reusable workflows (`./.github/workflows/…`)
#: and `docker://` refs are exempt at scan time and never need an entry here.
ALLOWED_WORKFLOW_REFS: dict[str, str] = {}

#: The explicit allowlist for third-party tool-image refs — the CURRENT mutable
#: tag, with the slice that will pin it through ensure_image.py's sha12 scheme.
ALLOWED_IMAGE_REFS: dict[str, str] = {
    "ghcr.io/gitleaks/gitleaks:v8.30.1": "allow-till #715 (sha12 pin)",
}


def _is_fleet_owned(image: str) -> bool:
    """An image the fleet builds/publishes itself is not a third-party tool."""
    return image.startswith(_FLEET_OWNED)


def _image_is_pinned(image: str) -> bool:
    """A pinned image carries a digest or the fleet-owned `<sha12>` tag form."""
    if _DIGEST.search(image):
        return True
    m = _SHA12_TAG.search(image)
    return bool(m) and m.group(1) != "latest"


def workflow_violations(root: Path) -> list[str]:
    """Mutable third-party workflow `uses:` refs not on the allow-ref list."""
    bad: list[str] = []
    for wf in sorted((root / ".github" / "workflows").glob("*.yml")):
        text = wf.read_text()
        for line_no, line in enumerate(text.splitlines(), 1):
            if _OWN_REUSABLE.search(line) or _DOCKER_REF.search(line):
                continue
            for m in _USES.finditer(line):
                owner_repo, ref = m.group(1), m.group(2)
                key = f"{owner_repo}@{ref}"
                if _SHA40.match(ref):
                    continue
                if key in ALLOWED_WORKFLOW_REFS:
                    continue
                where = ALLOWED_WORKFLOW_REFS.get(key)
                bad.append(
                    f"{wf.relative_to(root)}:{line_no}: `uses: {key}` is a mutable "
                    f"third-party ref (not a 40-hex SHA"
                    + (f"; allowlisted {where}" if where else "")
                    + ") — pin it to a commit SHA or add it to ALLOWED_WORKFLOW_REFS"
                )
    return bad


def _makefile_image_refs(text: str) -> list[tuple[int, str]]:
    """`*_IMAGE := <ref>` lines in the Makefile."""
    out = []
    for line_no, line in enumerate(text.splitlines(), 1):
        m = re.match(r"^[A-Z][A-Z0-9_]*_IMAGE\s*:=\s*(\S+)", line)
        if m:
            out.append((line_no, m.group(1)))
    return out


def _script_image_refs(root: Path) -> list[tuple[str, int, str]]:
    """Third-party image refs in quoted strings under scripts/*.py."""
    out = []
    for py in sorted((root / "scripts").glob("*.py")):
        try:
            text = py.read_text()
        except (UnicodeDecodeError, OSError):
            continue
        for line_no, line in enumerate(text.splitlines(), 1):
            for m in _IMAGE.finditer(line):
                img = m.group(1)
                if not _is_fleet_owned(img) and ":" in img:
                    out.append((py.name, line_no, img))
    return out


def _dockerfile_arg_refs(root: Path) -> list[tuple[str, int, str]]:
    """`ARG <NAME>=<ref>` lines in Dockerfile* — the ARG-level tool refs."""
    out = []
    for df in sorted(root.glob("Dockerfile*")):
        try:
            text = df.read_text()
        except (UnicodeDecodeError, OSError):
            continue
        for line_no, line in enumerate(text.splitlines(), 1):
            m = re.match(r"^ARG\s+[A-Za-z0-9_]+\s*=\s*(\S+)", line)
            if m:
                img = m.group(1)
                if "://" in img:  # a URL (e.g. an install script), not an image ref
                    continue
                if not _is_fleet_owned(img) and ":" in img:
                    out.append((df.name, line_no, img))
    return out


def image_violations(root: Path) -> list[str]:
    """Mutable third-party tool-image tags not pinned and not allowlisted."""
    bad: list[str] = []
    mk = (root / "Makefile").read_text()
    for line_no, img in _makefile_image_refs(mk):
        if _is_fleet_owned(img):
            continue
        if _image_is_pinned(img):
            continue
        if img in ALLOWED_IMAGE_REFS:
            continue
        bad.append(
            f"Makefile:{line_no}: `{img}` is a mutable third-party image tag "
            "(not a digest, not a fleet `<sha12>` tag, not allowlisted) — pin it "
            "or add it to ALLOWED_IMAGE_REFS"
        )
    for name, line_no, img in _script_image_refs(root):
        if _image_is_pinned(img):
            continue
        if img in ALLOWED_IMAGE_REFS:
            continue
        bad.append(
            f"scripts/{name}:{line_no}: `{img}` is a mutable third-party image "
            "tag — pin it or add it to ALLOWED_IMAGE_REFS"
        )
    for name, line_no, img in _dockerfile_arg_refs(root):
        if _image_is_pinned(img):
            continue
        if img in ALLOWED_IMAGE_REFS:
            continue
        bad.append(
            f"{name}:{line_no}: `{img}` is a mutable third-party image tag "
            "(Dockerfile ARG) — pin it or add it to ALLOWED_IMAGE_REFS"
        )
    return bad


def violations(root: Path = ROOT) -> list[str]:
    """Every mutable third-party workflow uses: or tool-image ref in the tree."""
    return workflow_violations(root) + image_violations(root)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="action_pin_check", description=__doc__)
    p.add_argument("--root", default=str(ROOT))
    args = p.parse_args(argv)
    root = Path(args.root)
    bad = violations(root)
    if bad:
        print(f"[action-pin-check] {len(bad)} mutable third-party ref(s):",
              file=sys.stderr)
        for b in bad:
            print(f"  - {b}", file=sys.stderr)
        print("[action-pin-check] FAIL: pin each to a 40-hex SHA / digest / "
              "fleet `<sha12>` tag, or allowlist it with an allow-till deadline.",
              file=sys.stderr)
        return 1
    print(f"[action-pin-check] OK: every third-party workflow `uses:` ref is a "
          f"40-hex SHA or allowlisted, and every third-party tool image is pinned "
          f"or allowlisted ({len(ALLOWED_WORKFLOW_REFS)} workflow + "
          f"{len(ALLOWED_IMAGE_REFS)} image allowlisted).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
