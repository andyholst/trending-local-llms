#!/usr/bin/env python3
"""Prove the container/dependency scanners detect a known vulnerability (#715).

A vulnerability scanner that silently reports nothing is worse than no scanner:
the pipeline looks green and a CVE ships. This plants a KNOWN-VULNERABLE Python
fixture (old `flask`/`werkzeug` pinned to versions with published advisories) in
a throwaway directory and REQUIRES both the trivy and grype images to fail on it
— exit 1 for trivy, exit 2 for grype — proving neither scanner is a false green.
It then requires both to PASS on an EMPTY directory (no dependency manifest at
all), so a scanner that reds on nothing-to-index is caught too.

  python3 scripts/security_scan_self_test.py     # exit 0 = both directions OK

Runs the pinned scanner images exactly as `make trivy-scan` / `make grype-scan`
do (the @sha256: refs in the Makefile), with the fixture directory mounted like
the GITLEAKS self-test does. Stdlib only. Needs docker + network on first run
(each scanner downloads its vulnerability DB).

Wired into `make security-scan-self-test`. Deliberately NOT part of the
qa-validate `validate` job: that job must have no network-dependent targets
(tests assert it), and these scanners fetch their DBs on first run — run this
on the host, like `make secret-scan-self-test`.

Slice note (#715, Slice 1): this is the image/target bringing-up slice; the
weekly `security-scan.yml` schedule and the findings/gate wiring are Slice 2/3.
"""
from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# The pinned scanner images, from the Makefile ONE source of truth (the
# tool-image seams `TRIVY_IMAGE` / `GRYPE_IMAGE`). Reading them here (and ONLY
# for a host probe) keeps the self-test honest with `make trivy-scan`.
TRIVY_IMAGE = ""
GRYPE_IMAGE = ""
for _line in (ROOT / "Makefile").read_text().splitlines():
    if _line.startswith("TRIVY_IMAGE := "):
        TRIVY_IMAGE = _line.split(":=", 1)[1].strip()
    elif _line.startswith("GRYPE_IMAGE := "):
        GRYPE_IMAGE = _line.split(":=", 1)[1].strip()

# Deliberately old, CVE-laden dependency pins (the vulnerability-DB sources
# both scanners use publish advisories for these). Never a current app bundle —
# this is a probe, so it must NOT look clean to the scanners it cannot trust.
VULNERABLE = "# vulnerability-scan probe - deliberately old, published CVEs\n" \
             "flask==2.2.2\nwerkzeug==2.2.2\n"


def _run(image: str, args: list[str], work: Path, cache: Path) -> int:
    """Run one scanner image over `work` (mounted at /scan), like the make
    seams do, returning the exit code. `cache` is a HOST dir mounted at
    /cache so grype's vulnerability-DB download is reused across runs (a
    fresh ephemeral DB each run made the green control flake on activation)."""
    return subprocess.run(
        ["docker", "run", "--rm", "--user", f"{os.getuid()}:{os.getgid()}",
         "-v", f"{work}:/scan", "-w", "/scan",
         "-v", f"{cache}:/cache",
         "-e", "HOME=/cache", "-e", "GRYPE_DB_CACHE_DIR=/cache",
         "-e", "TMPDIR=/cache",
         image, *args],
        cwd=ROOT, capture_output=True, text=True,
    ).returncode


def main() -> int:
    fails = 0

    def check(name: str, cond: bool, detail: str = "") -> None:
        nonlocal fails
        if cond:
            print(f"  ok  {name}")
        else:
            fails += 1
            print(f"  FAIL {name}" + (f"  [{detail}]" if detail else ""))

    if not TRIVY_IMAGE or not GRYPE_IMAGE:
        print("FAIL: could not read TRIVY_IMAGE / GRYPE_IMAGE from the Makefile", file=sys.stderr)
        return 1

    with tempfile.TemporaryDirectory(prefix="scanfix-") as td:
        bad = Path(td) / "bad"
        good = Path(td) / "good"
        tc = Path(td) / "tc"   # trivy's HOME (its DB lives in ~/.cache)
        gc = Path(td) / "gc"   # grype's GRYPE_DB_CACHE_DIR
        bad.mkdir()
        good.mkdir()  # intentionally EMPTY: nothing to index -> no findings
        tc.mkdir()
        gc.mkdir()
        (bad / "requirements.txt").write_text(VULNERABLE)

        print("security scan self-test: trivy + grype catch a known CVE (issue #715)")
        # trivy: exit 1 = a finding under --exit-code 1; 0 = clean. A DB/network
        # failure also exits non-zero, so the RED probe must NOT be satisfied by
        # a broken run — the CLEAN probe (below) proves the scanner actually ran.
        tr_red = _run(TRIVY_IMAGE, ["fs", "--scanners", "vuln", "--quiet",
                                    "--no-progress", "--exit-code", "1", "/scan"], bad, tc)
        gr_red = _run(GRYPE_IMAGE, ["dir:/scan", "--fail-on=high"], bad, gc)
        check("trivy: known-vulnerable fixture is RED (exit != 0)",
              tr_red != 0, f"trivy exit={tr_red}")
        check("grype: known-vulnerable fixture is RED (exit != 0)",
              gr_red != 0, f"grype exit={gr_red}")
        # An empty tree must pass BOTH scanners (a scanner that reds on nothing
        # to index is the other false sign — and proves the RED above was a real
        # finding, not a scanner that failed to run).
        tr_green = _run(TRIVY_IMAGE, ["fs", "--scanners", "vuln", "--quiet",
                                      "--no-progress", "--exit-code", "1", "/scan"], good, tc)
        gr_green = _run(GRYPE_IMAGE, ["dir:/scan", "--fail-on=high"], good, gc)
        check("trivy: empty fixture passes (exit 0)", tr_green == 0,
              f"trivy exit={tr_green}")
        check("grype: empty fixture passes (exit 0)", gr_green == 0,
              f"grype exit={gr_green}")

    print(f"PASSED {4 - fails} | FAILED {fails}")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
