#!/usr/bin/env python3
"""Do we have a test that a mutable third-party ref is refused? Yes — both surfaces.

`scripts/action_pin_check.py` is the guard (issue #735, #714 Slice 1, folding
#717); this file is its proof. Real logic on real fixture trees — the guard reads
the actual `.github/workflows/` + Makefile + scripts + Dockerfile tree, exactly
as it does in CI. No docker CLI is involved (the guard is pure filesystem).

The done-when:
  * a tree containing a mutable third-party `uses:` ref (not a 40-hex SHA, not
    allowlisted) → the guard exits non-zero (RED);
  * the same ref pinned to a 40-hex SHA → exits 0 (GREEN);
  * a mutable third-party tool image (e.g. gitleaks `v8.30.1`) not allowlisted →
    RED; pinned via `@sha256:` digest or a fleet `<sha12>` tag → GREEN;
  * the guard is GREEN on THIS repo as it stands (the current mutable refs are
    on the documented allowlist, so master-as-is passes while a NEW mutable ref
    is refused).

Wired into `make test` (rule 6d). Runs as a plain script.
"""
from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import action_pin_check as apc  # noqa: E402

from wiring import wired  # noqa: E402  (issues #176/#192)

_PASS = 0
_FAIL = 0
_SHA40 = "a" * 40


def check(name, cond, detail=""):
    global _PASS, _FAIL
    if cond:
        _PASS += 1
        print(f"  ok  {name}")
    else:
        _FAIL += 1
        print(f"  FAIL {name}" + (f"  [{detail}]" if detail else ""))


def _tree(td: Path, files: dict[str, str]) -> Path:
    root = td / "repo"
    root.mkdir(parents=True, exist_ok=True)
    for name, body in files.items():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(body)
    return root


def _run(root: Path) -> int:
    return subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "action_pin_check.py"), "--root", str(root)],
        capture_output=True, text=True,
    ).returncode


def _workflow(uses_line: str) -> str:
    return (
        "name: demo\non: push\njobs:\n  x:\n"
        "    runs-on: ubuntu-latest\n"
        "    steps:\n"
        f"      - {uses_line}\n"
    )


def test_workflow_uses_mutable_ref_reds():
    """A mutable third-party `uses:` tag not on the allowlist refuses the tree."""
    with tempfile.TemporaryDirectory() as td:
        # `actions/checkout@v4` IS allowlisted (it is the current tree's ref), so
        # the guard is green on it — the RED proof uses a mutable ref NOT on the
        # allowlist, which is what a NEW mutable dep would look like.
        root = _tree(Path(td) / "green", {
            ".github/workflows/demo.yml": _workflow("uses: actions/checkout@v4"),
            "Makefile": "TEST_IMAGE := trending-local-llms-test:latest\n",
        })
        root_red = _tree(Path(td) / "red", {
            ".github/workflows/demo.yml": _workflow("uses: actions/setup-python@v5"),
            "Makefile": "TEST_IMAGE := trending-local-llms-test:latest\n",
        })
        check("workflow: an allowlisted current tag is green",
              _run(root) == 0, f"exit={_run(root)}")
        check("workflow: a NEW mutable tag not allowlisted is RED",
              _run(root_red) != 0, f"exit={_run(root_red)}")


def test_workflow_uses_pinned_sha_green():
    """The same mutable ref pinned to a 40-hex SHA passes."""
    with tempfile.TemporaryDirectory() as td:
        root = _tree(Path(td), {
            ".github/workflows/demo.yml": _workflow(f"uses: actions/setup-python@{_SHA40}"),
            "Makefile": "TEST_IMAGE := trending-local-llms-test:latest\n",
        })
        check("workflow: a 40-hex SHA ref is GREEN",
              _run(root) == 0, f"exit={_run(root)}")


def test_own_reusable_workflow_exempt():
    """Own reusable workflows (`./.github/workflows/…`) are not third-party."""
    with tempfile.TemporaryDirectory() as td:
        root = _tree(Path(td), {
            ".github/workflows/demo.yml": _workflow("uses: ./.github/workflows/reuse.yml"),
            "Makefile": "TEST_IMAGE := trending-local-llms-test:latest\n",
        })
        check("workflow: own reusable workflow is exempt",
              _run(root) == 0, f"exit={_run(root)}")


def test_mutable_image_reds():
    """A mutable third-party image tag (gitleaks v8.30.1) refuses the tree."""
    with tempfile.TemporaryDirectory() as td:
        # gitleaks v8.30.1 IS allowlisted (current tree), so use a mutable ref NOT
        # on the allowlist to prove RED — a NEW mutable tool image.
        root = _tree(Path(td) / "green", {
            "Makefile": "GITLEAKS_IMAGE := ghcr.io/gitleaks/gitleaks:v8.30.1\n",
        })
        root_red = _tree(Path(td) / "red", {
            "Makefile": "TRIVY_IMAGE := ghcr.io/aquasecurity/trivy:v0.50.1\n",
        })
        check("image: an allowlisted current mutable tag is green",
              _run(root) == 0, f"exit={_run(root)}")
        check("image: a NEW mutable third-party tag is RED",
              _run(root_red) != 0, f"exit={_run(root_red)}")


def test_image_pinned_digest_green():
    """A mutable image pinned via `@sha256:` digest passes."""
    digest = "sha256:" + "b" * 64
    with tempfile.TemporaryDirectory() as td:
        root = _tree(Path(td), {
            "Makefile": f"TRIVY_IMAGE := ghcr.io/aquasecurity/trivy@{digest}\n",
        })
        check("image: a pinned digest is GREEN",
              _run(root) == 0, f"exit={_run(root)}")


def test_image_fleet_sha12_green():
    """The fleet-owned `<sha12>` tag form passes (the ensure_image.py scheme)."""
    with tempfile.TemporaryDirectory() as td:
        root = _tree(Path(td), {
            "Makefile": "TRIVY_IMAGE := ghcr.io/andyholst/trending-local-llms:dockerfile-abcdef123456\n",
        })
        check("image: a fleet `<sha12>` tag is GREEN",
              _run(root) == 0, f"exit={_run(root)}")


def test_fleet_owned_image_exempt():
    """Fleet-owned images (local consumer + published) are not third-party."""
    with tempfile.TemporaryDirectory() as td:
        root = _tree(Path(td), {
            "Makefile": (
                "TEST_IMAGE := trending-local-llms-test:latest\n"
                "OPENSPEC_IMAGE := trending-local-llms-openspec:latest\n"
            ),
        })
        check("image: fleet-owned consumer images are exempt",
              _run(root) == 0, f"exit={_run(root)}")


def test_guard_green_on_this_repo():
    """The guard passes on THIS repository as it stands (allowlist is honest)."""
    check("this repo: the guard is GREEN on master-as-is",
          _run(ROOT) == 0, f"exit={_run(ROOT)}")


def test_wired_into_make_test():
    check("wiring: action_pin_check test is discovered by `make test`",
          wired(ROOT / "tests" / "test_action_pin.py"), "")


def main() -> int:
    print("action-pin guard: workflow uses: + tool-image seam (issue #735)")
    test_workflow_uses_mutable_ref_reds()
    test_workflow_uses_pinned_sha_green()
    test_own_reusable_workflow_exempt()
    test_mutable_image_reds()
    test_image_pinned_digest_green()
    test_image_fleet_sha12_green()
    test_fleet_owned_image_exempt()
    test_guard_green_on_this_repo()
    test_wired_into_make_test()
    print(f"PASSED {_PASS} | FAILED {_FAIL}")
    return 1 if _FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
