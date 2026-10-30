# unattended-leg

## ADDED Requirements

### Requirement: a detached bot leg cannot call the `clarify` tool

The provisioning seam (`Makefile _setup`, which every bot-leg image runs) MUST execute
`hermes tools disable clarify`, and MUST fail the setup if that command is unsupported —
an unattended agent that can still call `clarify` is the defect under repair, not a
fallback.

#### Scenario: the seam removes the tool

- **Given** `make _setup` as the legs' provisioning seam
- **When** a leg's image is provisioned
- **Then** the seam runs `hermes tools disable clarify`, so no leg has the `clarify` tool
  and a model that would ask instead writes nothing (it cannot detach)
- **Test:** tests/test_hermes_prompts.py::test_the_provisioning_seam_disables_clarify
  and the `_setup` recipe itself

#### Scenario: a Hermes build that cannot disable clarify fails loudly

- **Given** a Hermes version without a usable `hermes tools disable clarify`
- **When** the seam runs
- **Then** the seam exits non-zero and names the failure, rather than provisioning a leg
  that can still detach
- **Test:** tests/test_hermes_prompts.py::test_the_provisioning_seam_disables_clarify
  (asserts the recipe is strict: `|| \` + `exit 1`)

#### Scenario: the regression is pinned

- **Given** the Makefile
- **When** someone later removes or softens the disable
- **Then** the suite turns RED, so the fix cannot be silently reverted
- **Test:** tests/test_hermes_prompts.py::test_the_provisioning_seam_disables_clarify
