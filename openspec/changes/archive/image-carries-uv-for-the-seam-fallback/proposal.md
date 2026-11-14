# Proposal: image-carries-uv-for-the-seam-fallback

Issue: #217
PR: #916

## Why

`scripts/install_hermes_ci.sh` promises a three-path install contract — already-installed,
`HERMES_INSTALL_URL`, or `uv tool install` — and its failure message even reports
`uv: not installed` (scripts/install_hermes_ci.sh:129). But the base image installs no `uv`
at all: the Dockerfile's apt line and `requirements.txt` contain neither (measured for issue
#217: `grep -i uv requirements.txt` finds nothing; the apt install list has no uv). So path 3
is dead code inside the very image the seam was written for: when the URL installer fails in
a build, the fallback that the contract advertises cannot run, and the only honest outcome is
the loud FAIL — which is right, but the advertised third path was never real there.

## What Changes

- `Dockerfile`: install `uv` in the image **before** the seam runs
  (`RUN pip install --no-cache-dir uv`), so `uv tool install` is actually executable inside
  the container the seam was written for.
- `tests/test_install_hermes_ci.py`: a new check that the Dockerfile installs `uv` before the
  line that invokes `install_hermes_ci.sh` — the test goes red on the old Dockerfile.
- The seam script itself is NOT changed: its three-path contract and loud failure stay as
  written (#207); only the image gains the tool the contract names.

## Impact

`Dockerfile` (one RUN line), `tests/test_install_hermes_ci.py` (one test). The Dockerfile
content hash changes, so the next refresh publishes the new base tag (issue #135 mechanism).
No target, stage, job or rule changes.

## Not covered

- Pinning a `uv` VERSION (the seam calls whatever `uv` the image carries; the issue asks only
  that the fallback be runnable).
