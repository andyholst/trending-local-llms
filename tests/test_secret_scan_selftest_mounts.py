#!/usr/bin/env python3
"""The self-test probe's docker mounts are proven (issue #840).

`make secret-scan-self-test` once "passed" while its probe scanned 0 BYTES: macOS's
/var/folders TMPDIR mounted into a colima container as an EMPTY tree, gitleaks wrote
no report, and the probe had no way to notice. The probe half is fixed in the script
(repo-local scratch dir + loud no-report refusal); THIS file is the pinned proof the
issue's Done-when demands:

  1. every container mount the probe makes is under the REPO-LOCAL scratch dir
     (`ROOT/.secret-self-test-tmp`), never under the host TMPDIR — proven by running
     the real probe end-to-end with a PATH stub standing in for the external docker
     CLI (rule 6m: the production probe code still runs; the mount arguments it
     builds are what we assert on);
  2. a scan whose mounted tree yields NO report FAILS LOUDLY (exit 1 naming the
     missing report) instead of reporting a clean tree — the exact false-green
     shape #840 measured;
  3. with a stub scanner that behaves like gitleaks, the probe's own directions
     (plant -> detect, clean -> quiet, gitignored bytecode -> artifact-only) all
     land — the guard's green is not an accident of the stub.

Run:  python3 tests/test_secret_scan_selftest_mounts.py    or   make test
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRATCH = ROOT / ".secret-self-test-tmp"
SCRIPT = ROOT / "scripts" / "secret_scan_self_test.py"

# Credential SHAPES the probe plants (mirrors its _PARTS prefixes) — the stub
# scanner recognises exactly these, never a real secret (none here).
SHAPE_MARKERS = ("ghp_", "hf_", "sk-proj-", "wJalrXUtnFEMI")

_DOCKER_STUB = """#!/usr/bin/env python3
import json, os, sys
from pathlib import Path
argv = sys.argv[1:]
mounts, report_dst = [], None
i = 0
while i < len(argv):
    if argv[i] == "-v":
        mounts.append(argv[i + 1]); i += 2
    elif argv[i] == "--report-path":
        report_dst = argv[i + 1]; i += 2
    else:
        i += 1
log = os.environ["TLL_STUB_MOUNTLOG"]
with open(log, "a") as fh:
    for m in mounts:
        fh.write(m + "\\n")
if os.environ.get("TLL_STUB_MODE") != "scanner_ok":
    sys.exit(0)  # the no-report shape: the scan "runs" and writes NOTHING
scan_src = out_dir = None
for m in mounts:
    src, _, dst = m.partition(":")
    if dst.startswith("/scan"):
        scan_src = Path(src)
    elif dst.startswith("/out"):
        out_dir = Path(src)
if scan_src is None or out_dir is None or report_dst is None:
    sys.exit(0)
findings = []
for f in scan_src.rglob("*"):
    if not f.is_file():
        continue
    try:
        text = f.read_text(errors="ignore")
    except OSError:
        continue
    if any(marker in text for marker in ("ghp_", "hf_", "sk-proj-", "wJalrXUtnFEMI")):
        findings.append({"RuleID": "probe-shape", "File": "/scan/" + str(f.relative_to(scan_src)),
                         "Secret": "***"})
(out_dir / Path(report_dst).name).write_text(json.dumps(findings))
"""


def _run_probe(tmp: Path, mode: str) -> tuple[subprocess.CompletedProcess, list[str], Path]:
    """Run the REAL probe script with the docker seam stubbed; return proc + mounts."""
    bin_dir = tmp / "bin"
    bin_dir.mkdir(parents=True, exist_ok=True)
    stub = bin_dir / "docker"
    stub.write_text(_DOCKER_STUB)
    stub.chmod(0o755)
    mountlog = tmp / "mounts.tsv"
    mountlog.write_text("")
    # Host TMPDIR parked OUTSIDE the scratch tree: if the probe ever mounts under
    # the host temp dir again (the macOS /var/folders shape), the assertion goes red.
    foreign_dir = tmp / "foreign"
    foreign_dir.mkdir(parents=True, exist_ok=True)
    foreign_tmp = Path(tempfile.mkdtemp(dir=foreign_dir))
    env = dict(os.environ)
    env["PATH"] = f"{bin_dir}{os.pathsep}{env.get('PATH', '')}"
    env["TLL_STUB_MOUNTLOG"] = str(mountlog)
    env["TLL_STUB_MODE"] = mode
    env["TMPDIR"] = str(foreign_tmp)
    proc = subprocess.run([sys.executable, str(SCRIPT)], capture_output=True,
                          text=True, env=env, cwd=str(ROOT), timeout=300)
    mounts = mountlog.read_text().splitlines()
    return proc, [m for m in mounts if m], foreign_tmp


_PASS = 0
_FAIL = 0


def check(name, cond, detail=""):
    global _PASS, _FAIL
    if cond:
        _PASS += 1
        print(f"  ok  {name}")
    else:
        _FAIL += 1
        print(f"  FAIL {name}" + (f"  [{detail}]" if detail else ""))


def test_an_empty_mounted_tree_fails_loudly_never_clean():
    """The measured #840 shape: the scan 'runs', writes no report — that is exit 1."""
    with tempfile.TemporaryDirectory() as td:
        proc, mounts, _ = _run_probe(Path(td), mode="no_report")
        check("no-report scan exits non-zero (a scanner writing nothing is never a clean tree)",
              proc.returncode == 1, str(proc.returncode))
        check("no-report scan is named LOUDLY in the output",
              "wrote no report" in proc.stdout, proc.stdout[:200])
        check("no-report refusal names the mount-failure hypothesis",
              "docker mount failed" in proc.stdout, proc.stdout[:200])


def test_every_probe_mount_is_repo_local_never_the_host_tmpdir():
    with tempfile.TemporaryDirectory() as td:
        proc, mounts, foreign_tmp = _run_probe(Path(td), mode="no_report")
        # full "src:dst[:ro]" lines; keep only the scan/out mounts (the
        # .gitleaks.toml read-only mount lives in ROOT already)
        scan_out_mounts = [m.partition(":")[0] for m in mounts if ":/scan" in m or ":/out" in m]
        check("the probe mounted the scan tree and the out dir (the stub saw mounts)",
              len(scan_out_mounts) >= 2, str(scan_out_mounts))
        check("every scan/out mount lives under the repo-local scratch dir",
              all(Path(m).resolve().is_relative_to(SCRATCH.resolve()) for m in scan_out_mounts),
              str(scan_out_mounts))
        check("no mount escaped into the parked host temp dir",
              all(not Path(m).resolve().is_relative_to(foreign_tmp.resolve())
                  for m in scan_out_mounts), str(scan_out_mounts))


def test_with_a_stub_scanner_all_probe_directions_land():
    """The probe is not green by accident: with a scanner that behaves, every direction fires."""
    with tempfile.TemporaryDirectory() as td:
        proc, _, _ = _run_probe(Path(td), mode="scanner_ok")
        check("planted shapes are detected (no false green)",
              "detected" in proc.stdout and proc.returncode == 0, proc.stdout[-300:])
        check("clean fixture stays quiet (no over-match)",
              "clean fixture: no findings" in proc.stdout, proc.stdout[-300:])
        check("gitignored bytecode is an artifact, not a gate-red finding",
              "gitignored cache" in proc.stdout and "artifact" in proc.stdout,
              proc.stdout[-300:])


def main() -> int:
    print("secret self-test mounts: proof (issue #840)")
    SCRATCH.mkdir(exist_ok=True)
    test_an_empty_mounted_tree_fails_loudly_never_clean()
    test_every_probe_mount_is_repo_local_never_the_host_tmpdir()
    test_with_a_stub_scanner_all_probe_directions_land()
    print(f"\nPASSED {_PASS} | FAILED {_FAIL}")
    return 1 if _FAIL else 0


if __name__ == "__main__":
    raise SystemExit(main())
