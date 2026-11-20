#!/usr/bin/env python3
"""Only a stage that DECLARES a landing may write the refusals ledger (issue #1155).

`data/refusals.json` is DATA, and rule 3b lets it grow only on a real observation. Before
issue #1155 the ingest refusal seams wrote it from EVERY pass over the tree, so a branch that
touched no data grew it anyway: on the `tech-debt-agent-profile-provision-1142` worktree, a
suite + validator run for a fleet-profile change left `M data/refusals.json` in
`git status --short` with `seen_count` raised to 2 (and `last_seen_utc` stamped) on three
findings the refresh delivery had already recorded — churn discarded by hand before the
branch was pushed. A PR diff holding rows of findings its issue never observed is a diff
nobody can review, a counter that grows on validation instead of observation is a data value
CI invented (rule 2), and two branches raising the same counters collide in the merge queue.

The contract now: `python3 scripts/update_trending.py` lands refusals ONLY when the run
declares itself a delivery stage with `--land-refusals`, which the Makefile's delivery
recipes (`_merge`, `_merge-fetch`, and the `_fix` merge) carry. Any other pass — a
validator, `--dry-run`, a test module, an implementation leg — prints every refusal, prints
one line naming the count it did NOT land, and leaves the tracked file byte-identical.
`--dry-run --land-refusals` is a contradiction (a dry-run writes nothing) and exits 2.

Driven through the REAL CLI over a REAL git checkout the real `git` reports on (rule 6m): the
scratch tree is a copy of the checkout (minus `.git`) + `git init` + one seed commit, so the
verdict is `git status --porcelain` — exactly what a PR diff is — never an in-memory guess. No
stand-in replaces the product: the same `update_trending.py`, the same Makefile text, the same
three test modules that measured the churn. `git` is run ONLY inside that scratch tree, never
aimed at the checkout the suite happens to run in (see `scratch_repo` for the container-uid
refusal that made this a rule).

  - test_an_undeclared_full_ingest_lands_no_refusals      the measured churn is gone
  - test_an_undeclared_pass_still_reports_every_refusal   loud log, a NOT-landed line
  - test_a_declared_delivery_stage_lands_the_ledger       --land-refusals appends/grows
  - test_a_dry_run_writes_nothing_at_all                  the `make validate` analogue
  - test_a_dry_run_cannot_declare_a_landing               exit 2, tree untouched
  - test_the_measured_suite_modules_leave_the_tree_clean  #1148's three dirty modules
  - test_the_makefile_delivery_recipes_declare_the_landing  wired, and no validator does
  - test_the_scratch_builder_never_aims_git_at_the_checkout_it_runs_in  container-safe tree

Run:  python3 tests/test_refusals_land_declaration.py   or   make test
"""
from __future__ import annotations

import ast
import inspect
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
UPDATE = ROOT / "scripts" / "update_trending.py"
MAKEFILE = ROOT / "Makefile"

# The modules issue #1148 measured: they ingest over the SHIPPED data dir, which is how the
# shipped ledger accumulated 92 records for 3 findings.
# HOST CAVEAT (measured 2026-11-20): each of these modules also carries the #972 shipped
# engine-check alarm, whose GitHub reachability probe is UNAUTHENTICATED. When this host's
# 60/hr anonymous quota is spent (`api.github.com` -> 403, `remaining: 0`) the probe reports
# 'repo not found / unreachable' and that check goes red here while CI (authenticated, other
# IP) stays green — the host/container split rule 6c names. CI is the authority on those two
# sub-checks; everything this module owns about #1155 is host-verifiable and green here.
MEASURED_MODULES = (
    "tests/test_engine_registry.py",
    "tests/test_engine_aliases.py",
    "tests/test_measurement_attribution.py",
)

# Older than every shipped snapshot: forces the ingest to walk ALL of data/raw, which is the
# shape of the pass that produced the measured churn.
EVERY_SNAPSHOT = "2000-01-01T00:00:00Z"

_PASS = 0
_FAIL = 0


def check(name, cond, detail: object = ""):
    global _PASS, _FAIL
    if cond:
        _PASS += 1
        print(f"  ok  {name}")
    else:
        _FAIL += 1
        print(f"  FAIL {name}" + (f"  [{detail}]" if detail else ""))


def git(repo: Path, *args) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], cwd=str(repo), capture_output=True,
                          text=True, timeout=600)


IGNORED_COPY_DIRS = (".git", "__pycache__", ".pytest_cache", ".mypy_cache",
                     "node_modules", ".venv", "venv", ".hermes", ".local")


def scratch_repo() -> Path:
    """The tree under test, as a real git checkout: copy the checkout, `git init`, one seed commit.

    The `git status --porcelain` of this tree answers the question the issue asks: what a run
    leaves in the working tree that a commit could carry into a PR. `.gitignore` rides along in
    the copy, so the seed commit ignores exactly what the repository ignores.

    NOT `git -C <ROOT> archive HEAD` (the shape this module shipped with): in the test container
    the checkout at `/workspace` is OWNED BY ANOTHER UID than the user running the suite, and git
    refuses EVERY command aimed at it —
    `fatal: detected dubious ownership in repository at '/workspace'` → exit 128. Measured on
    qa-validate run 44660030227 (job `validate`, step `Run unit tests (in container)`), where
    this was the suite's only red module out of 138 while every module that shells git only in
    ITS OWN scratch directory passed. So the scratch tree is built git-free (a copy of the
    checkout minus the VCS directory), and git is then run only inside the scratch tree, which
    this process created and therefore owns.
    """
    tmp = Path(tempfile.mkdtemp(prefix="refusals-land-"))
    shutil.copytree(ROOT, tmp / "tree", symlinks=True,
                    ignore=shutil.ignore_patterns(*IGNORED_COPY_DIRS),
                    ignore_dangling_symlinks=True)
    tree = tmp / "tree"
    written = sum(1 for _ in tree.rglob("*") if _.is_file())
    if written < 200:
        raise RuntimeError(f"the scratch checkout has only {written} file(s); the seed tree is not the repo")
    tmp = tree
    r = git(tmp, "init", "-q")
    if r.returncode:
        raise RuntimeError(f"git init failed: {r.stderr}")
    r = git(tmp, "add", "-A")
    if r.returncode:
        raise RuntimeError(f"git add failed: {r.stderr}")
    r = git(tmp, "-c", "user.email=seed@test", "-c", "user.name=seed",
            "commit", "-qm", "seed HEAD of the repo under test")
    if r.returncode:
        raise RuntimeError(f"git commit failed: {r.stderr}")
    if git(tmp, "status", "--porcelain").stdout.strip():
        raise RuntimeError("the seed checkout is not clean; the verdict would be meaningless")
    return tmp


def changed(repo: Path, path: str = "") -> list[str]:
    """`git status --porcelain` — the files a run left different from HEAD."""
    args = ["status", "--porcelain"] + (["--", path] if path else [])
    out = git(repo, *args).stdout
    return [line for line in out.splitlines() if line.strip()]


def run_cli(repo: Path, *args: str) -> subprocess.CompletedProcess:
    """The REAL CLI, cwd = the scratch checkout, host environment (no stubs)."""
    return subprocess.run([sys.executable, "scripts/update_trending.py", *args],
                          cwd=str(repo), capture_output=True, text=True, timeout=900)


def run_module(repo: Path, rel: str) -> subprocess.CompletedProcess:
    """The REAL suite module, run the way `make test` runs it, in the scratch checkout."""
    return subprocess.run([sys.executable, rel], cwd=str(repo), capture_output=True,
                          text=True, timeout=900)


def ledger_rows(repo: Path) -> list[dict]:
    doc = json.loads((repo / "data" / "refusals.json").read_text())
    return doc["refusals"]


def ledger_total(rows: list[dict]) -> int:
    return sum(int(r.get("seen_count", 1)) for r in rows)


# ---------------------------------------------------------------- guards

def test_an_undeclared_full_ingest_lands_no_refusals():
    repo = scratch_repo()
    try:
        before = ledger_rows(repo)
        proc = run_cli(repo, "--since", EVERY_SNAPSHOT)
        check("an undeclared ingest run exits 0", proc.returncode == 0,
              f"rc={proc.returncode} {proc.stderr[-400:]}")
        dirty = changed(repo, "data/refusals.json")
        check("#1155: an undeclared pass leaves data/refusals.json byte-identical",
              dirty == [],
              f"git status --porcelain -- data/refusals.json: {dirty}")
        check("#1155: the ledger's records and counters are the ones HEAD carries",
              ledger_rows(repo) == before,
              f"rows {len(before)} -> {len(ledger_rows(repo))}")
        # The merge itself still happened (the delivery shape is unchanged for models.json);
        # it is the REFUSAL landing that a non-delivery pass may not do.
        check("the pass still merges (it reports its ingest), so it is not a no-op CLI",
              "ingested raw snapshots" in proc.stdout, proc.stdout[-300:])
        check("#1155: the refusals ledger is absent from everything the pass left behind",
              not any("data/refusals.json" in line for line in changed(repo)),
              changed(repo)[:6])
    finally:
        shutil.rmtree(repo, ignore_errors=True)


def test_an_undeclared_pass_still_reports_every_refusal():
    repo = scratch_repo()
    try:
        proc = run_cli(repo, "--since", EVERY_SNAPSHOT)
        out = proc.stdout
        refused = [line for line in out.splitlines() if line.startswith("[ingest] REFUSED")]
        check("every refusal is still printed (refusing silently is the old defect)",
              len(refused) > 0, f"{len(refused)} REFUSED lines")
        count_lines = [line for line in out.splitlines()
                       if "refused at ingest this run" in line]
        check("the run total line keeps its shape (the #882 grouping guard reads it)",
              len(count_lines) == 1, count_lines)
        check("#1155: the summary says the refusals were NOT landed",
              count_lines and "NONE landed in data/refusals.json" in count_lines[0]
              and "no declared" in count_lines[0],
              count_lines)
        per_file = [line for line in out.splitlines()
                    if "refusal(s) NOT landed in the refusals ledger" in line]
        check("#1155: the per-file summary names the ledger AND says nothing landed",
              len(per_file) > 0, f"{len(per_file)} per-file NOT-landed lines")
        check("the CLI states the declaration a delivery must make",
              "--land-refusals" in "\n".join(count_lines), count_lines)
    finally:
        shutil.rmtree(repo, ignore_errors=True)


def test_a_declared_delivery_stage_lands_the_ledger():
    repo = scratch_repo()
    try:
        before_rows = ledger_rows(repo)
        before_total = ledger_total(before_rows)
        proc = run_cli(repo, "--since", EVERY_SNAPSHOT, "--land-refusals")
        check("a declared delivery run exits 0", proc.returncode == 0,
              f"rc={proc.returncode} {proc.stderr[-400:]}")
        check("the delivery announces its declaration before it writes",
              "landing declared (delivery stage, issue #1155)" in proc.stdout,
              proc.stdout[:300])
        dirty = changed(repo, "data/refusals.json")
        check("#1155: a DECLARED stage is the one that lands the ledger",
              dirty == [" M data/refusals.json"], f"git status: {dirty}")
        after_rows = ledger_rows(repo)
        check("rule 3b: nothing is removed, records only grow",
              len(after_rows) >= len(before_rows),
              f"{len(before_rows)} -> {len(after_rows)}")
        check("the counters grew (repeats raise seen_count, issue #1148)",
              ledger_total(after_rows) > before_total,
              f"total {before_total} -> {ledger_total(after_rows)}")
        check("#1155: the per-file summary now says 'recorded in the refusals ledger'",
              "refusal(s) recorded in the refusals ledger" in proc.stdout,
              proc.stdout[-600:])
        check("and the run total says every one was recorded",
              "every one recorded in data/refusals.json" in proc.stdout,
              proc.stdout[-400:])
    finally:
        shutil.rmtree(repo, ignore_errors=True)


def test_a_dry_run_writes_nothing_at_all():
    repo = scratch_repo()
    try:
        proc = run_cli(repo, "--dry-run", "--since", EVERY_SNAPSHOT)
        check("a dry-run pass exits 0", proc.returncode == 0,
              f"rc={proc.returncode} {proc.stderr[-400:]}")
        check("#1155: a dry-run pass leaves the whole tracked tree byte-identical",
              changed(repo) == [], f"git status --porcelain: {changed(repo)}")
        check("and it still refuses loudly in the log",
              any(line.startswith("[ingest] REFUSED") for line in proc.stdout.splitlines()),
              proc.stdout[-300:])
    finally:
        shutil.rmtree(repo, ignore_errors=True)


def test_a_dry_run_cannot_declare_a_landing():
    repo = scratch_repo()
    try:
        proc = run_cli(repo, "--dry-run", "--since", EVERY_SNAPSHOT, "--land-refusals")
        check("#1155: --dry-run + --land-refusals is refused (exit 2, not a silent pick)",
              proc.returncode == 2, f"rc={proc.returncode}")
        check("the refusal names both flags and the issue",
              "--dry-run" in proc.stderr and "--land-refusals" in proc.stderr
              and "#1155" in proc.stderr, proc.stderr[:300])
        check("the refusal writes nothing", changed(repo) == [], changed(repo))
        check("no refusal was landed on the refused run",
              ledger_rows(repo) == json.loads(
                  (ROOT / "data" / "refusals.json").read_text())["refusals"],
              "the ledger changed on a run that exited 2")
    finally:
        shutil.rmtree(repo, ignore_errors=True)


def test_the_measured_suite_modules_leave_the_tree_clean():
    repo = scratch_repo()
    try:
        for rel in MEASURED_MODULES:
            proc = run_module(repo, rel)
            check(f"{rel} still passes on the declared-landing rule",
                  proc.returncode == 0,
                  f"rc={proc.returncode} tail={proc.stdout[-300:]}{proc.stderr[-200:]}")
        dirty = changed(repo)
        check("#1155: the three modules that grew the shipped ledger now leave the tree clean",
              dirty == [], f"git status --porcelain: {dirty[:6]}")
    finally:
        shutil.rmtree(repo, ignore_errors=True)


def _recipe(makefile_text: str, target: str) -> str:
    """The recipe lines of one Makefile target (tab-indented lines after its rule)."""
    lines = makefile_text.splitlines()
    out: list[str] = []
    inside = False
    for line in lines:
        if line.startswith(f"{target}:"):
            inside = True
            continue
        if inside:
            if line.startswith("\t"):
                out.append(line)
            elif line.strip() == "":
                continue
            else:
                break
    return "\n".join(out)


def test_the_makefile_delivery_recipes_declare_the_landing():
    text = MAKEFILE.read_text()
    for target in ("_merge", "_merge-fetch", "_fix"):
        recipe = _recipe(text, target)
        check(f"the delivery recipe `{target}` declares the landing",
              "--land-refusals" in recipe, recipe[:300])
        check(f"`{target}` still runs the ingest through the Makefile (rule 6m)",
              "scripts/update_trending.py" in recipe, recipe[:200])
    dry_targets = [t for t in ("_merge", "_merge-fetch", "_validate-fetch", "validate-data")
                   if "--dry-run" in _recipe(text, t)]
    for target in dry_targets:
        check(f"the dry-run recipe `{target}` never declares a landing",
              "--land-refusals" not in _recipe(text, target),
              _recipe(text, target)[:200])
    check("the guard saw a dry-run recipe to check (a renamed away guard is a defect)",
          dry_targets, "no --dry-run ingest recipe found in the Makefile")
    # A declaration is a delivery's act, so it must not appear in a validation-stage recipe.
    offenders = [t for t in ("_validate-merge", "_validate-data", "_validate-fetch")
                 if "--land-refusals" in _recipe(text, t)]
    check("no validation stage declares a landing", not offenders, offenders)


def git_at_root_offenders(src: str) -> list[str]:
    """Every call in `src` that asks git about the checkout the suite happens to run in.

    Detected on the SYNTAX (not the text), so a docstring that merely MENTIONS the forbidden
    call cannot raise a false red: a call to the `git` helper whose arguments mention `ROOT`, or
    a subprocess/`git` call carrying the literal "git" alongside `ROOT`.
    """
    out = []
    for node in ast.walk(ast.parse(src)):
        if not isinstance(node, ast.Call):
            continue
        called = node.func.id if isinstance(node.func, ast.Name) else getattr(node.func, "attr", "")
        names = {n.id for n in ast.walk(node) if isinstance(n, ast.Name)}
        strings = {n.value for n in ast.walk(node)
                   if isinstance(n, ast.Constant) and isinstance(n.value, str)}
        if ("git" in strings or called == "git") and "ROOT" in names:
            out.append(ast.get_source_segment(src, node) or called)
    return out


OLD_SCRATCH_SHAPE = '''
def _scratch_repo_shipped_before_1157():
    tmp = Path(tempfile.mkdtemp(prefix="refusals-land-"))
    with open(tmp / "tree.tar", "wb") as tar_file:
        subprocess.run(["git", "-C", str(ROOT), "archive", "HEAD"],
                       stdout=tar_file, check=True, timeout=600)
'''


def test_the_scratch_builder_never_aims_git_at_the_checkout_it_runs_in():
    """The container refusal this module actually hit (qa-validate run 44660030227).

    In the test container the checkout at `/workspace` belongs to a DIFFERENT uid than the user
    running the suite, so every `git -C <ROOT> …` exits 128 with `fatal: detected dubious
    ownership in repository at '/workspace'`. A scratch tree built by asking git about the
    checkout is therefore green on a host and red in CI — the host/container split this repo has
    measured before (rule 6c) — so the scratch tree is built git-free and `git` is run only
    inside the tree this process created. The tree must still be a REAL work tree carrying the
    data store the product ingests, or the guard proves nothing.
    """
    src = inspect.getsource(scratch_repo)
    offenders = git_at_root_offenders(src)
    check("scratch_repo asks git NOTHING about the checkout the suite runs in",
          not offenders, "; ".join(offenders))
    # The guard is not vacuous: the shape this module SHIPPED with must trip it.
    planted = git_at_root_offenders(OLD_SCRATCH_SHAPE)
    check("the guard goes red on the shipped shape (git -C ROOT archive HEAD)",
          len(planted) == 1, planted)
    repo = scratch_repo()
    st = git(repo, "rev-parse", "--is-inside-work-tree")
    check("the scratch tree is a real git work tree the real git reports on",
          st.stdout.strip() == "true", st.stderr)
    tracked = git(repo, "ls-files", "data/refusals.json").stdout.strip()
    check("the scratch tree carries the data store the product ingests", bool(tracked), tracked)
    data_files = git(repo, "ls-files", "data").stdout.splitlines()
    check("the scratch tree carries the repo's tracked files in full (a partial copy is not a checkout)",
          len(data_files) >= 5, f"data files: {len(data_files)}")


def main() -> int:
    for fn in (
        test_an_undeclared_full_ingest_lands_no_refusals,
        test_an_undeclared_pass_still_reports_every_refusal,
        test_a_declared_delivery_stage_lands_the_ledger,
        test_a_dry_run_writes_nothing_at_all,
        test_a_dry_run_cannot_declare_a_landing,
        test_the_measured_suite_modules_leave_the_tree_clean,
        test_the_makefile_delivery_recipes_declare_the_landing,
        test_the_scratch_builder_never_aims_git_at_the_checkout_it_runs_in,
    ):
        print(f"\n== {fn.__name__}")
        fn()
    print(f"\n{_PASS} passed, {_FAIL} failed")
    return 1 if _FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
