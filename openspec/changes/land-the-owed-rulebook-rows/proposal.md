# Proposal: land-the-owed-rulebook-rows

Issues: #322 and #324 (the §2 authorship rule), #314 (the job-level guard sentence),
#212, #380, #385, #405 (four §8 guard rows). One change, because they are one ledger:
`AGENTS.md` rows that earlier runs could not write while it was an unwritable protected file.

## Why

Each of these issues was filed by rule 3c ("an issue that changes this file's behaviour must say
so, and that part is review-required") because the implementing run could not write `AGENTS.md` and
said so instead of working around the guard. The guard still exists — a write needs consent — but
the consent is now obtainable, so the owed text can finally land. Leaving them open costs more than
the text: eight issues describe one rulebook that is *almost* right, and a reader cannot tell which
row is missing and which was merely believed missing.

## What Changes

- **§2 rule `3f` — one identity per person.** Only `Andy Holst <andy.holst@protonmail.com>` and
  `Asimov Agent <support@docondee.com>` may author, commit or co-author. `make
  check-commit-authorship` reads the **identity AND the message** (GitHub synthesizes the squash
  `Co-authored-by:` trailer from the author identity, measured: 27 commits), refuses a second
  SPELLING of a known person, **allows the automation identities** (`github-actions[bot]`,
  `GitHub <noreply@github.com>`) so bot PRs are not reddened, requires `make git-identity` in every
  job whose `run:` reaches `git commit`, and fails loudly (exit 2) on an unreadable range — hence
  `fetch-depth: 0`.
- **§6j — the guard is a JOB, not a step.** It runs first, the working job declares `needs: guard`,
  and no secret reaches a refused run; a step-level guard would already carry the secret, so
  "checked first" would be a claim about ordering rather than access (#314).
- **§6b** — the fix-bot bullet names the identity it commits with instead of asserting that one
  exists (#324).
- **§8** — four rows and one correction: the `engine_min_version` invention guard (#212), the search
  legs' engine rule (#380), the fix loop's time bound / base-merge / no-op round (#385), the derived
  guard registry (#405), and the `tests/test_workflows.py` row's identity claim replacing "no git
  identity" (#324).

## Impact

`AGENTS.md` only, plus this change and `OPENSPEC.md`. No code, no target, no workflow.

## Not covered

- **#369** (a §8 row for the `storage_offload` footprint guard): its own body does not name the test
  it belongs beside, so the row cannot be written without re-deriving which guard it means — left
  open deliberately rather than guessed at.
- The issues are closed **after** this lands, each pointing at the row that answered it.
