#!/usr/bin/env python3
"""Do we have a test that a mutable third-party ref is refused? Yes — both surfaces.

`scripts/action_pin_check.py` is the guard (issue #735, #714 Slice 1, folding
#717); this file is its proof. Real logic on real fixture trees — the guard reads
the actual `.github/workflows/` + Makefile + scripts + Dockerfile tree, exactly
as it does in CI. No docker CLI is involved (the guard is pure filesystem).

Issue #737 (#714 Slice 2) migrated all 37 third-party workflow `uses:` refs to
immutable 40-hex SHAs and emptied ALLOWED_WORKFLOW_REFS. Issue #741 (#715 Slice
1) pinned gitleaks + the four scanner images (trivy/containerfile/grype/syft)
to immutable `@sha256:` digests and emptied ALLOWED_IMAGE_REFS — the #715
allow-till deadline is satisfied on master-as-is, and a NEW mutable third-party
ref (workflow or image) is refused. The tests below prove the migration.

The done-when:
  * a tree containing a mutable third-party `uses:` ref (not a 40-hex SHA, not
    allowlisted) → the guard exits non-zero (RED);
  * the same ref pinned to a 40-hex SHA → exits 0 (GREEN);
  * a mutable third-party tool image (e.g. gitleaks `v8.30.1`) not allowlisted →
    RED; pinned via `@sha256:` digest or a fleet `<sha12>` tag → GREEN;
  * the guard is GREEN on THIS repo as it stands (ALLOWED_WORKFLOW_REFS and
    ALLOWED_IMAGE_REFS are both empty, so master-as-is passes only because every
    third-party ref is pinned).

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
        # Post-#737 (empty ALLOWED_WORKFLOW_REFS) a bare mutable tag is ALWAYS
        # refused — a pinned 40-hex SHA is the green control, and a mutable tag
        # (any, not on the now-empty allowlist) is the RED proof.
        root = _tree(Path(td) / "green", {
            ".github/workflows/demo.yml": _workflow(f"uses: actions/checkout@{_SHA40}"),
            "Makefile": "TEST_IMAGE := trending-local-llms-test:latest\n",
        })
        root_red = _tree(Path(td) / "red", {
            ".github/workflows/demo.yml": _workflow("uses: actions/checkout@v4"),
            "Makefile": "TEST_IMAGE := trending-local-llms-test:latest\n",
        })
        check("workflow: a pinned 40-hex SHA ref is green",
              _run(root) == 0, f"exit={_run(root)}")
        check("workflow: a mutable tag (allowlist empty) is RED",
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
    """A mutable third-party image tag refuses the tree (allowlist is empty)."""
    with tempfile.TemporaryDirectory() as td:
        # ALLOWED_IMAGE_REFS is EMPTY (#741) — a bare mutable tag (e.g. a NEW
        # trivy tag, or the pinned gitleaks expressed WITHOUT its digest) is
        # RED, and only a digested/fleet-<sha12> ref is the green control.
        digest = "sha256:" + "b" * 64
        root = _tree(Path(td) / "green", {
            "Makefile": f"TRIVY_IMAGE := ghcr.io/aquasecurity/trivy@{digest}\n",
        })
        root_red = _tree(Path(td) / "red", {
            "Makefile": "TRIVY_IMAGE := ghcr.io/aquasecurity/trivy:v0.50.1\n",
        })
        check("image: a pinned digest is GREEN (empty allowlist)",
              _run(root) == 0, f"exit={_run(root)}")
        check("image: a NEW mutable third-party tag is RED (empty allowlist)",
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


def test_no_tag_based_third_party_refs_in_pinned_workflows():
    """#737 (#714 Slice 2): the pinned workflows contain NO tag-based third-party
    `uses:` refs — every third-party ref is a full 40-hex SHA. Reads the real
    tree, exactly as CI does. Own reusable (`./.github/workflows/…`) and
    `docker://` refs are exempt by design and not third-party."""
    import re
    bad: list[str] = []
    uses_re = re.compile(r"uses:\s*([A-Za-z0-9._-]+/[A-Za-z0-9._-]+)@(\S+)")
    sha40 = re.compile(r"^[0-9a-f]{40}$")
    for wf in sorted((ROOT / ".github" / "workflows").glob("*.yml")):
        for line_no, line in enumerate(wf.read_text().splitlines(), 1):
            for m in uses_re.finditer(line):
                owner_repo, ref = m.group(1), m.group(2)
                if sha40.match(ref):
                    continue
                bad.append(f"{wf.relative_to(ROOT)}:{line_no}: `{owner_repo}@{ref}`")
    check("migration: no tag-based third-party `uses:` ref remains in .github/workflows",
          not bad, "; ".join(bad[:5]))


def test_workflow_allowlist_empty_after_migration():
    """#737 (#714 Slice 2) + #741 (#715 Slice 1): ALLOWED_WORKFLOW_REFS and
    ALLOWED_IMAGE_REFS are BOTH empty — all 37 workflow refs are pinned to
    40-hex SHAs and gitleaks + the four scanners (trivy/containerfile/grype/syft)
    are pinned to `@sha256:` digests, so the #714/#715 allow-till deadlines are
    satisfied; a NEW mutable third-party ref is refused fails-closed."""
    check("migration: ALLOWED_WORKFLOW_REFS is empty (0 workflow allowlisted)",
          len(apc.ALLOWED_WORKFLOW_REFS) == 0,
          f"still allowlisted: {sorted(apc.ALLOWED_WORKFLOW_REFS)}")
    check("migration: ALLOWED_IMAGE_REFS is empty (0 image allowlisted)",
          len(apc.ALLOWED_IMAGE_REFS) == 0,
          f"still allowlisted: {sorted(apc.ALLOWED_IMAGE_REFS)}")
    # every third-party image ref our Makefile names is pinned (digest or sha12)
    import re
    sha_digest = re.compile(r"@sha256:[0-9a-f]{64}$")
    fleet_sha12 = re.compile(r":([A-Za-z0-9._-]+)-[0-9a-f]{12}$")
    bad = []
    for line_no, img in apc._makefile_image_refs((ROOT / "Makefile").read_text()):
        fleet = img.startswith(apc._FLEET_OWNED)
        pinned = bool(sha_digest.search(img)) or bool(fleet_sha12.search(img))
        if not fleet and not pinned and img not in apc.ALLOWED_IMAGE_REFS:
            bad.append(f"Makefile:{line_no}: {img}")
    check("migration: every third-party image ref in the Makefile is pinned",
          not bad, "; ".join(bad[:4]))


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
    test_no_tag_based_third_party_refs_in_pinned_workflows()
    test_workflow_allowlist_empty_after_migration()
    test_wired_into_make_test()
    print(f"PASSED {_PASS} | FAILED {_FAIL}")
    return 1 if _FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
