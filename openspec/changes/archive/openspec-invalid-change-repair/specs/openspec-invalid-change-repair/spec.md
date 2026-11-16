# openspec-invalid-change-repair

## ADDED Requirements

### Requirement: A structurally invalid ACTIVE change is classified by the ONE verdict seam

An ACTIVE OpenSpec change that ships without `proposal.md`, without at least one
`specs/<capability>/spec.md` or without a `tasks.md` carries body the gate cannot
validate, so the verdict seam that already decides a red `make openspec-check`
MUST name it as its own shape — `DRIFT=invalid-change` — with the change and the
archive remedy spelled out, and MUST NOT answer `index-only` for a red whose cause
is that shape (a regenerated index would merely catalogue the incomplete change).

#### Scenario: an active change with only a proposal goes red naming the change and its remedy

- **Given** a planted tree whose ACTIVE change directory holds `proposal.md` and nothing else
- **When** `make openspec-invalid-change-check` runs the real classifier over that tree
- **Then** it exits 1, names the change, states which artifact is missing (`specs/<capability>/spec.md`,
  `tasks.md`), and prints the exact archive remedy `make openspec-invalid-change-repair`
- **Test:** tests/test_openspec_invalid_change_repair.py::test_an_invalid_active_change_goes_red_naming_the_change_and_the_remedy

#### Scenario: the verdict seam reads the invalid change before it offers an index rewrite

- **Given** a planted tree whose `OPENSPEC.md` is stale AND whose ACTIVE change is structurally invalid
- **When** the verdict seam `scripts/openspec_index_repair.py --classify-and-write` runs over it
- **Then** it prints `DRIFT=invalid-change` naming that change and the named repairer, leaves
  `OPENSPEC.md` untouched, and exits 0 so the index keeper lands nothing for a red it does not own
- **Test:** tests/test_openspec_invalid_change_repair.py::test_the_verdict_seam_classifies_the_invalid_change_before_the_index

#### Scenario: an index-only drift still lands through the same seam beside valid changes

- **Given** a planted tree with structurally complete ACTIVE changes and a stale `OPENSPEC.md`
- **When** the same verdict seam runs over it
- **Then** it still prints `DRIFT=index-only`, rewrites only `OPENSPEC.md`, and exits 0
  (the #304 keeper path is unchanged by this requirement)
- **Test:** tests/test_openspec_invalid_change_repair.py::test_the_seam_still_lands_an_index_only_repair_beside_valid_changes

### Requirement: The keeper repairs an invalid ACTIVE change by archiving it, never by writing its content

The honest repair of a change nobody wrote is the archive move the lifecycle already defines: the
change goes to `openspec/changes/archive/<UTC-date>-<name>/` carrying exactly the files it shipped
with, its proposal declares the keeper exemption the binding gate recognises, and the index is
regenerated from the resulting tree. The repairer MUST NOT create a `specs/` directory, a spec file
or a task list it did not find (rule 2 — no invented content), and MUST leave every structurally
complete change where it is.

#### Scenario: the repair archives the invalid change and the regenerated index stays current

- **Given** a planted tree holding one invalid ACTIVE change and one complete ACTIVE change, with a
  current `OPENSPEC.md`
- **When** `make openspec-invalid-change-repair` runs the real repairer over that tree
- **Then** the invalid change sits under `openspec/changes/archive/<UTC-date>-<name>/`, the
  complete change is still ACTIVE, and `make openspec-index-check` (the real
  `scripts/openspec_index.py --check`) is green on the resulting tree
- **Test:** tests/test_openspec_invalid_change_repair.py::test_the_repair_archives_the_invalid_change_and_the_index_stays_current

#### Scenario: the archived proposal declares the keeper exemption and no content was fabricated

- **Given** the tree after that repair
- **When** the archived proposal and the archived directory are read
- **Then** the proposal carries `Binding-exempt: invalid active change repaired by keeper (<run id>)`
  — the #952 exemption shape the real `scripts/openspec_binding_check.py` accepts — the archived
  directory holds exactly the files the change shipped with (no invented `specs/` or `tasks.md`),
  and the binding gate reads the archived change as out of its ACTIVE scope
- **Test:** tests/test_openspec_invalid_change_repair.py::test_the_archived_proposal_carries_the_keeper_exemption_and_no_fabricated_content

#### Scenario: a structurally complete change is never archived by the repairer

- **Given** a planted tree whose ACTIVE changes all carry proposal, spec and tasks
- **When** the repairer runs over it
- **Then** it prints `REPAIR=none`, moves nothing, and leaves `OPENSPEC.md` byte-identical
- **Test:** tests/test_openspec_invalid_change_repair.py::test_a_structurally_complete_change_is_never_archived

### Requirement: A red openspec-check of the invalid-change shape has a named repairer in the pipeline and in the alarm

The gate half and the repair half must both be reachable the way every other gate is: the check is
bundled into `make openspec-check` (which `qa-validate` runs on every PR and push), the repair lands
through qa-validate's `invalid-change-repair` keeper job on a red push to `master`, its keeper PR
closes nothing, and `make master-alarm`'s keeper registry names that repairer for the shape instead
of leaving the shape unnamed in the alarm.

#### Scenario: qa-validate grows the sibling keeper job for this shape

- **Given** `.github/workflows/qa-validate.yml`
- **When** its `invalid-change-repair` job is read
- **Then** it `needs: [guard, validate]`, runs only on `failure()` of a push to `master`, classifies
  through `make openspec-invalid-change-repair`, refuses a tree whose drift is more than the archive
  move plus `OPENSPEC.md`, dedupes keepers through `mergeStateStatus`, and never merges or pushes
  `master`
- **Test:** tests/test_workflows.py::test_invalid_change_repair_job_is_the_sibling_keeper_for_an_incomplete_active_change

#### Scenario: the check is bundled into the merge gate and every seam is reached through make

- **Given** the `Makefile` and `qa-validate.yml`
- **When** the wiring is read
- **Then** `make openspec-check` lists `openspec-invalid-change-check` as a prerequisite, the repair
  and body targets exist, the workflow reaches all of them through `make` only, and this suite is
  discovered by `make test`
- **Test:** tests/test_openspec_invalid_change_repair.py::test_the_check_and_the_repair_are_wired_into_the_gate_and_the_keeper_job

#### Scenario: master-alarm names the repairer for the invalid-change shape

- **Given** a planted red push-to-master qa-validate run whose `validate` job failed at
  `make openspec-check`
- **When** `scripts/master_alarm.py` renders its verdict from the planted `gh` answers
- **Then** it exits 1 and prints the named repairer for that gate's `invalid-change` shape
  (`qa-validate invalid-change-repair`) beside the index keeper it already named
- **Test:** tests/test_master_alarm.py::test_an_invalid_change_red_run_names_its_repairer

#### Scenario: the keeper PR records the drift and closes nothing

- **Given** the keeper body composed by `make openspec-invalid-change-repair-pr-body` and the branch
  `ci/openspec-invalid-change-repair-<UTC>`
- **When** `scripts/pr_closure.py`'s own parser reads the branch and the body
- **Then** the branch implements no issue, the body carries no closing keyword, and the check accepts
  it as a keeper reference
- **Test:** tests/test_openspec_invalid_change_repair.py::test_the_keeper_body_records_the_drift_and_closes_nothing

### Requirement: A tree the seam cannot read is a loud refusal, never a silent clean

An unreadable `openspec/changes/` tree, or an archive destination that already exists, is a defect
in the tree — the check and the repairer must both exit 2 naming what could not be read, and never
report a clean repair over a tree they could not inspect.

#### Scenario: an unreadable tree and a colliding archive name both exit 2

- **Given** a planted tree with no `openspec/changes/` directory, and a second planted tree whose
  archive destination for the invalid change already exists
- **When** the check and the repairer run over them
- **Then** each exits 2 with the path it could not read named on stderr, and neither rewrites
  `OPENSPEC.md` nor moves a change
- **Test:** tests/test_openspec_invalid_change_repair.py::test_an_unreadable_tree_is_a_loud_exit_2_never_a_silent_clean
