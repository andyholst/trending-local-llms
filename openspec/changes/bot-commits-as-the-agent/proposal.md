# Every committing bot job commits as the repo's own agent

**Issue:** #323
**Capability:** `commit-authorship` (whose guard, added by #317/#319, already states the rule)

## Why

The repo states that its only identities are **Andy Holst** and **Asimov Agent** — the
commit-authorship guard (`scripts/check_commit_authorship.py`) reads exactly that, and the
sibling repo's history shows the canonical pair as `Asimov Agent <support@docondee.com>`:

```
$ git -C ../llgenie log --all --format='%an <%ae>' | sort | uniq -c | sort -rn | head -3
    182 Asimov Agent <support@docondee.com>
     50 Mr. Asimov <support@docondee.com>
    112 Andy Holst <andy.holst@protonmail.com>
```

The pipeline that produces most of the commits contradicts it. Measured on `origin/master`
`ff98119` — four `git config` sites, all `github-actions[bot]`:

```
.github/workflows/fix-bot.yml:209-210
.github/workflows/issue-bot.yml:336-337, 491-492
.github/workflows/refresh-bot.yml:446-447
```

`github-actions[bot]` is GitHub's generic automation account, not this repo's agent. The
cost is not cosmetic: the authorship guard gates new commits on identity, and GitHub
SYNTHESIZES a squash `Co-authored-by:` trailer from the author identity inside the PR — the
measured leak #317 exists for. An identity the repo does not intend is the same class of
defect, arriving 32 times in the trailers already on master.

The guard also did not list `support@docondee.com` in `ALLOWED_EMAILS`: the correct agent
address was tolerated only because `ALLOWED_NAMES` happens to match its name.

And nothing pinned the value: `tests/test_workflows.py` inspected **`fix-bot.yml` only** and
only asserted that a `git config` line *exists* — a job could commit as anyone and stay green.

## What Changes

- All four committing sites set `git config user.name "Asimov Agent"` /
  `git config user.email "support@docondee.com"`.
- `scripts/check_commit_authorship.py`: `ALLOWED_EMAILS` lists the agent's own address, and
  the docstring names it as the identity every committing bot job uses.
- `tests/test_workflows.py`: the identity assertion checks the **value**, and a new test walks
  **every** workflow, job and step whose `run:` contains `git commit` — requiring the agent
  identity and refusing `github-actions[bot]` at each one (and failing when it finds none, so
  a guard that finds nothing cannot pass for a pass).
- `tests/test_commit_authorship.py`: the agent's own address is allowed by itself.

## Not covered

- `asimov-agent/llgenie`'s bot jobs set their identity from `gh api user --jq .login` (the PAT
  owner — a *human* identity) and from `github-actions[bot]`; the same fix there is its own
  issue in that repo.
- Rewriting existing history: the guard gates new commits only, and the measured history is
  left alone.
- The `AGENTS.md` wording (§8 row + the §6b bullets; the §2 rule itself is #322's) is
  **review-required** — rule 3c is satisfied by the issue comment naming the sections, and the
  protected file refused the write (`BLOCKED: … approval prompt timed out`), so the wording is
  recorded here and filed as **#324** (the #212/#310/#322 precedent). The guard's read-only
  consequence: nothing cites a rule id §2 does not declare, so `tests/test_rule_numbers.py`
  stays green.
- The identity is still a literal repeated per workflow (four sites + the guard's allowlist):
  one definition is its own issue: **#325**.
