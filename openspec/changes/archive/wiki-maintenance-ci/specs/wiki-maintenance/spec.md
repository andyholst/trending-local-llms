## ADDED Requirements

### Requirement: The checker derives truth from the tree, offline

The checker SHALL derive every fact it reports from `data/models.json` (the canonical
model names and `generated_utc`), the generated `README.md` render (its `[**name**]`
rows and its `Last generated` stamp) and the `ARCHITECTURE.md` inventory block —
never from an invented value, a network read or a model call. A truth source that
cannot be read SHALL be a loud exit 2, never a silent clean.

#### Scenario: A current tree is green

- **Given** a tree whose README rows and stamp and inventory paths match the store
- **When** the checker runs `--check` offline
- **Then** it exits 0 and reports no finding
- **Test:** tests/test_wiki_maintenance.py::test_a_current_tree_is_green

#### Scenario: An unreadable truth source refuses

- **Given** a tree with `data/models.json` missing
- **When** the checker runs `--check`
- **Then** it exits 2 with `READ FAILED` and never reports an empty finding set
- **Test:** tests/test_wiki_maintenance.py::test_an_unreadable_tree_is_exit_2_not_a_silent_clean

### Requirement: A false claim is reported as an update with an exact needle

A current doc carrying a false statement SHALL be reported with kind
`false-claim`, action `update`, the exact file and the exact matched needle, so a
reader can fix the claim without guessing.

#### Scenario: A stale render stamp

- **Given** a README whose `Last generated` minute differs from the store's
  `generated_utc` minute
- **When** the checker runs `--check`
- **Then** it exits 1 naming `README.md`, the planted stamp needle and `action=update`
- **Test:** tests/test_wiki_maintenance.py::test_a_stale_render_stamp_is_a_false_claim_to_update

#### Scenario: A store model with no rendered row

- **Given** a model in `data/models.json` that the README render dropped
- **When** the checker runs `--check`
- **Then** it exits 1 naming the model's `[**name**]` needle and `action=update`
- **Test:** tests/test_wiki_maintenance.py::test_a_store_model_with_no_row_is_a_false_claim_to_update

### Requirement: An obsolete doc is reported as an archive with evidence

A doc whose subject no longer exists in the tree SHALL be reported with kind
`obsolete-doc`, action `archive`, the exact file+needle and the tree evidence that
proves the subject is gone.

#### Scenario: A rendered row for a removed model

- **Given** a README `[**name**]` row absent from the store's `models[]`
- **When** the checker runs `--check`
- **Then** it exits 1 naming `README.md`, that row needle and `action=archive`
- **Test:** tests/test_wiki_maintenance.py::test_a_rendered_model_absent_from_the_store_is_an_obsolete_doc_to_archive

#### Scenario: An inventory line naming a deleted file

- **Given** an `ARCHITECTURE.md` inventory item whose path is absent from the tree
- **When** the checker runs `--check`
- **Then** it exits 1 naming `ARCHITECTURE.md`, the path needle and `action=archive`
- **Test:** tests/test_wiki_maintenance.py::test_an_inventory_line_naming_a_deleted_script_is_obsolete

### Requirement: Apply composes a keeper body and never edits a doc

`--apply` SHALL print a keeper PR body built from the current findings; it SHALL
NOT close an issue (rule 6e) and SHALL leave every doc byte-identical. With no
findings it SHALL refuse loudly rather than print an empty body.

#### Scenario: Findings compose a closing-free keeper body

- **Given** a tree with a planted finding
- **When** the checker runs `--apply`
- **Then** stdout carries the finding and both action sections, `pr_closure` reads
  no closing keyword, and no doc changes by a byte
- **Test:** tests/test_wiki_maintenance.py::test_apply_writes_a_keeper_body_without_mutating_a_doc_or_closing_an_issue

#### Scenario: No findings refuse

- **Given** a clean tree
- **When** the checker runs `--apply`
- **Then** it exits 2 and says `no findings` on stderr
- **Test:** tests/test_wiki_maintenance.py::test_apply_with_no_findings_refuses_loudly

### Requirement: The checker rides the one existing schedule as one guarded job

The seam SHALL be reachable through `_recipe` / public-wrapper Makefile targets and
through exactly ONE job on `refresh-bot.yml`'s existing schedule. No workflow other
than `refresh-bot.yml` SHALL gain an `on.schedule` block, and the job SHALL be gated
by the workflow's `guard` (rule 6t).

#### Scenario: The wiring is present and the cron cap holds

- **Given** the real Makefile and workflow tree
- **When** the wiring guard reads them
- **Then** the two public targets, the guarded `wiki-maintenance` job and the two
  original crons are present, and no other workflow schedules a run
- **Test:** tests/test_wiki_maintenance.py::test_the_seam_is_wired_where_it_bites
