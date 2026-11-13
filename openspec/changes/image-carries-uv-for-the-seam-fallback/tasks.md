# Tasks: image-carries-uv-for-the-seam-fallback

- [x] `tests/test_install_hermes_ci.py::test_the_image_installs_uv_before_the_seam_runs` written first and run against the OLD Dockerfile (verify: it goes red — the seam runs with no `uv` install anywhere before it)
- [ ] `Dockerfile` installs `uv` (`RUN pip install --no-cache-dir uv`) before the seam's `RUN` (verify: the new test green; the existing seam tests green)
- [ ] The one-liner proven on the real base image (verify: `docker run python:3.12-slim pip install --no-cache-dir uv` answers a working `command -v uv`)
- [ ] `make test` suite green; `make lint`, `make secret-scan`, `make openspec-check` green (verify: run output)
