# Spec delta: agent-image-smoke (new capability)

## ADDED Requirements

### Requirement: The live smoke proves image availability and profile prompt reachability
The CI live-smoke stage SHALL verify, after `image-ensure` and profile provisioning, that
the agent image ref for the revision is either published (manifest answers) or built
locally by `image-ensure`, and that every provisioned `tll-*` profile carries `config.yaml`,
`SOUL.md` and each lane skill's `SKILL.md`. A failure SHALL name the missing artefact. The
check SHALL be read-only and SHALL NOT make a model call.

#### Scenario: a lane profile loses its prompt skill
- **Given** a provisioned profile home with a `tll-*` lane missing `skills/<lane>/SKILL.md`
- **When** the agent image smoke runs
- **Then** it exits non-zero and names the missing prompt file
- **Test:** tests/test_agent_image_smoke.py

#### Scenario: the hash image is absent and was not built locally
- **Given** no published manifest and no local image for the revision's hash ref
- **When** the smoke runs
- **Then** it reports `absent` and fails; a published manifest or a locally built image passes
- **Test:** tests/test_agent_image_smoke.py (faked docker seams)
