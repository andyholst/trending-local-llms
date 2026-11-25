## ADDED Requirements

### Requirement: The offline --check summary names the #1265 §3B live-run exemption

The `--check` summary SHALL state, beside the doubled run-bearing pair, that a claim whose
evidence is still LIVE is exempt entirely — not merely doubled — citing `#1265` §3B, because a
host reading the printed contract must see the post-#1635 rule. The doubled pair itself SHALL stay
in the same summary, so the pre-exemption bound remains readable.

#### Scenario: The printed contract carries the exemption

- **Given** the `--check` offline contract runs with the pinned defaults
- **When** its summary line is printed
- **Then** the live-run clause reads `(x2 when the claim carries a run id, unless its evidence is still LIVE, #1265 §3B)`
- **Test:** tests/test_stale_claim_sweep.py::test_the_offline_contract_needs_no_network

#### Scenario: The doubled pair is still named

- **Given** the same `--check` summary
- **When** a reader looks for the run-bearing bound
- **Then** the `x2 when the claim carries a run id` pair is still present alongside the exemption
- **Test:** tests/test_stale_claim_sweep.py::test_the_offline_contract_needs_no_network

### Requirement: The decision logic is unchanged by the summary edit

Changing the printed prose SHALL NOT alter any decision: the authority limits, the pinned grace
pairs, the floors, the `S:` marker vocabulary and every exit code stay exactly as they are.

#### Scenario: Only output prose moved

- **Given** the pre-change tree and this change
- **When** the sweep decides a claim's verdict
- **Then** no verdict, threshold or exit code differs
- **Test:** tests/test_stale_claim_sweep.py::test_the_threshold_pairs_are_pinned_with_floors_and_makefile_overrides
