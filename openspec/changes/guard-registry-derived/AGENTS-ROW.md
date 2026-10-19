# The AGENTS.md text this change owes (application blocked — protected file)

`AGENTS.md` may not be written by an implementation run (protected
agent-instruction file, approval-gated). The exact text is recorded here so a
human applies it as one reviewed edit — never as a bot write, and never as a
silently-ticked checklist box.

Apply BOTH hunks.

---

## Hunk 1 — §6j, replace the "guarded pipelines are named in ONE place" sentence

**Find** (in rule 6j, just after the sentence about a guard refusing every
outside contribution):

> The guarded pipelines are named in ONE place — `tests/test_workflows.py`'s
> `BOT_GUARDS` — so a new pipeline cannot ship without a guard: adding one to the
> repo without adding it there fails the suite.

**Replace with:**

> The guarded pipelines are DERIVED FROM THE TREE, not remembered: every
> workflow whose jobs carry a guard step must be in `tests/test_workflows.py`'s
> `BOT_GUARDS`, every entry in `BOT_GUARDS` must still carry its guard, and the
> two must agree on WHICH job holds it. A literal registry is a registry that
> gets forgotten, and the forgetting is silent — measured before this rule:
> `code-review-bot.yml` and `queued-alarm.yml` carried guards that
> `ARCHITECTURE.md` described and no test ever ran, and `fix-bot.yml`'s entry
> named the wrong job, with the suite green throughout (issue #313). Every
> workflow that declares `workflow_dispatch` must carry a guard, because a
> manual start is the one start a caller chooses.

---

## Hunk 2 — §8, add this row to the regression-guard table

Insert immediately after the `tests/test_workflows.py — test_owner_guards,
test_guard_behaviour, test_every_bot_guard_with_a_cron_has_the_schedule_bypass`
row (the one ending "…ceasing to refuse a stranger's dispatch"):

> | `tests/test_workflows.py::test_the_guard_registry_is_derived_from_the_tree` (rule 6j, issue #313) | a guard nothing exercises: the guarded pipelines were a hand-kept tuple (`BOT_GUARDS`) that the guard tests iterated, so a workflow carrying a guard but missing from the tuple was invisible — measured on master: `code-review-bot.yml` and `queued-alarm.yml` guards that `ARCHITECTURE.md` described and no test ran, and `fix-bot.yml`'s entry naming the `fix` job while the guard lived elsewhere, with the suite green throughout; the pipelines are now DERIVED from the tree (a step whose name carries `guard`) and checked against the registry in BOTH directions, plus agreement on which JOB holds the guard, plus "every workflow declaring `workflow_dispatch` carries a guard" (a manual start is the one start a caller chooses), plus a non-vacuity floor so a scan that finds nothing cannot pass |

---

## Verification after applying

```
make lint
make validate
make test
```

`test_the_guard_registry_is_derived_from_the_tree` already passes on this
branch (669 passed / 0 failed); it only needs the rulebook to say what the tree
now enforces.
