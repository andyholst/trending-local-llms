# Proposal: publish-is-verified

Issue: #228 — `tech-debt: Nothing verifies what the registry serves after a publish`

## Why

`publish()` builds, pushes both refs, and returns:

```python
_run("docker", "push", tag)
_run("docker", "push", latest_tag())
return f"publish: pushed {tag} and {latest_tag()}"
```

A `docker push` that exits 0 is the **CLI's** opinion. What every consumer actually gets is
the **registry's** answer, asked with `docker manifest inspect` — and nothing asked it. A
push that "succeeded" into a package no client can read (private visibility, a token that
can write but not read back, a typo'd repository path) therefore reported success, and the
failure surfaced later and elsewhere: in a bot job's `docker pull`, or in `ensure`'s
pull-or-build decision. There was no test of `publish` at all, which is how it stayed
unobserved.

## What Changes

- **After the two pushes, `publish()` re-probes BOTH refs with `published()`** — the same
  predicate every consumer's decision uses — and raises `PublishUnverified` naming the refs
  the registry does not serve. `_serves()` retries `VERIFY_ATTEMPTS` (3) times with
  `VERIFY_DELAY_S` between, because a registry's read path can trail its write path by a
  moment (`ENSURE_VERIFY_DELAY_S` makes the delay injectable for tests).
- **The CLI turns that into exit 1** with `[publish] FAIL: …` naming the refs, so a
  workflow step fails where it used to print success.
- **The docker stub now behaves like a registry**: a successful `push` makes the ref
  readable (`available`), and `FAKE_DOCKER_PUSH_INVISIBLE=1` models a registry that
  accepts the write and never serves it.
- **`tests/test_ensure_image.py::test_a_publish_is_not_done_until_the_registry_serves_it`**:
  the happy path exits 0 and says `VERIFIED` after asking about both refs; the invisible
  path exits non-zero, says the registry does not serve them, and names both refs.

Verified RED against the pre-change script (4 failures — it reported success without ever
asking the registry) and GREEN after (`PASSED 82 | FAILED 0`).

## Impact

`scripts/ensure_image.py` (one helper, one exception, the tail of `publish()`, and the CLI
handler), `tests/test_ensure_image.py` (the stub + one test), this OpenSpec change and the
regenerated `OPENSPEC.md`. It is the sibling of #235: that one stopped a registry HICCUP
from being read as "absent"; this one stops a push from being believed without asking. No
make target, stage, job or image changes (`ARCHITECTURE.md` unchanged, rule 6h).

## Not covered

- **`docker push --quiet` / digest comparison.** Verification asks the registry "do you
  serve this ref?", not "is the digest I just built the one you serve" — a same-tag
  overwrite race is a different (and here, deliberate `--force`) case.
- **The OpenSpec and test images.** `publish()` is the agent (base) image's path; the other
  two are built by their own workflows, which pull what they just pushed on their next run.
