#!/usr/bin/env python3
"""Hermetic checks for the code-review bot (issue #253).

The bot reads the TREE and the PIPELINES and files ONE issue per finding — analysis, never
implementation. These lock the narrowest promise and the checks themselves, over the REAL code
with a scratch tree / a fake `gh` on PATH:

  1. a workflow step that runs a repo script directly IS reported; a `make` step is not;
  2. two fixed crons in the same minute+hour on overlapping days ARE reported;
  3. a `workflow_call`-only file nothing references IS reported;
  4. the bot's only `gh` verbs are `issue list` and `issue create` (it never writes code, never
     merges, never touches anyone's PR);
  5. the filer is marker-deduped and capped;
  6. run over THIS repo, no check names the bot's own workflow (self-consistency).

Run standalone: python3 tests/test_code_review.py   or   make test
"""
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import code_review as cr  # noqa: E402

WF = ROOT / ".github" / "workflows"
_PASS = 0
_FAIL = 0


def check(name: str, cond: bool, detail: object = ""):
    global _PASS, _FAIL
    if cond:
        _PASS += 1
        print(f"  ok  {name}")
    else:
        _FAIL += 1
        print(f"  FAIL {name} {detail}")


def _scratch(files: dict[str, str]) -> Path:
    """A scratch repo root with the given `.github/workflows/*.yml` files."""
    root = Path(tempfile.mkdtemp())
    (root / ".github" / "workflows").mkdir(parents=True)
    for name, body in files.items():
        (root / ".github" / "workflows" / name).write_text(body)
    return root


def test_an_inline_repo_script_is_reported():
    # Given a workflow whose step runs a repo script directly
    root = _scratch({"bad.yml": "name: bad\non:\n  push:\n  workflow_dispatch:\n"
                                "jobs:\n  j:\n    runs-on: ubuntu-latest\n    steps:\n"
                                "      - name: go\n        run: |\n          python3 scripts/thing.py\n"})
    # When  the inline-script check runs
    found = cr.check_workflow_inline_scripts(root)
    # Then  it is reported
    check("check: an inline `python3 scripts/...` step is reported", len(found) == 1, found)
    check("check: the finding names the workflow",
          found and found[0]["key"] == "workflow-inline-scripts/bad.yml", found)
    # And a `make <target>` step is not
    ok_root = _scratch({"good.yml": "name: good\non:\n  push:\n  workflow_dispatch:\n"
                                    "jobs:\n  j:\n    runs-on: ubuntu-latest\n    steps:\n"
                                    "      - name: go\n        run: make some-target REPO=x\n"})
    check("check: a `make <target>` step is not reported",
          cr.check_workflow_inline_scripts(ok_root) == [])


def test_two_colliding_crons_are_reported():
    # Given two workflows scheduled at the same minute+hour on the same day
    root = _scratch({
        "a.yml": "name: a\non:\n  schedule:\n    - cron: \"23 7 * * 1\"\n  workflow_dispatch:\n",
        "b.yml": "name: b\non:\n  schedule:\n    - cron: \"23 7 * * 1\"\n  workflow_dispatch:\n",
    })
    # When  the cron-collision check runs
    found = cr.check_cron_collisions(root)
    # Then  the pair is reported
    check("check: a shared minute+hour slot is reported", len(found) == 1, found)
    # And  a different minute is not
    root2 = _scratch({
        "a.yml": "name: a\non:\n  schedule:\n    - cron: \"23 7 * * 1\"\n  workflow_dispatch:\n",
        "b.yml": "name: b\non:\n  schedule:\n    - cron: \"41 7 * * 1\"\n  workflow_dispatch:\n",
    })
    check("check: distinct minutes are not reported", cr.check_cron_collisions(root2) == [])


def test_a_reusable_orphan_is_reported():
    # Given a `workflow_call`-only file nothing references
    root = _scratch({"pipeline.yml": "name: p\non:\n  workflow_call:\n    inputs:\n      x:\n"
                                     "        required: true\n        type: string\n"})
    # When  the orphan check runs
    found = cr.check_reusable_orphan(root)
    # Then  it is reported
    check("check: an unreferenced workflow_call file is reported", len(found) == 1, found)


def _fake_gh(td: Path, existing: list[dict] | None = None):
    """A `gh` on PATH that records every argv and answers `issue list` / `issue create`."""
    gh = td / "gh"
    gh.write_text(f"""#!/usr/bin/env bash
python3 -c 'import json,sys;print(json.dumps(sys.argv[1:]))' "$@" >> "{td}/calls"
if [ "$1 $2" = "issue list" ]; then cat "{td}/existing"; exit 0; fi
if [ "$1 $2" = "issue create" ]; then echo "https://github.com/o/r/issues/1"; exit 0; fi
exit 0
""")
    gh.chmod(0o755)
    (td / "existing").write_text(json.dumps(existing or []))
    (td / "calls").write_text("")
    return gh


def test_the_bot_only_lists_and_creates_issues():
    # Given the bot with a fake gh, filing one finding
    td = Path(tempfile.mkdtemp())
    gh = _fake_gh(td)
    item = {"key": "workflow-inline-scripts/x.yml", "title": "t", "evidence": "e", "where": "w"}
    cr.file_findings(str(gh), "o/r", [item], cap=3)
    calls = (td / "calls").read_text()
    # When  every gh verb it used is read (one JSON argv per line)
    verbs = {tuple(json.loads(l)[:2]) for l in calls.splitlines() if l.strip()}
    # Then  only `issue list` and `issue create` appear — no code write, no merge, no PR
    check("narrowest promise: only issue list/create are used",
          verbs <= {("issue", "list"), ("issue", "create")}, verbs)
    check("narrowest promise: never a merge", "merge" not in calls)
    check("narrowest promise: never a pr comment", "pr comment" not in calls)


def test_the_filer_is_marker_deduped_and_capped():
    # Given a finding whose marker already exists
    td = Path(tempfile.mkdtemp())
    gh = _fake_gh(td, existing=[{"number": 3}])
    item = {"key": "cron-collisions/a-b", "title": "t", "evidence": "e", "where": "w"}
    created = cr.file_findings(str(gh), "o/r", [item], cap=3)
    # Then  nothing is filed
    check("filer: an already-filed key files nothing", created == [], created)
    # And   a fresh key IS filed, up to the cap
    td2 = Path(tempfile.mkdtemp())
    gh2 = _fake_gh(td2, existing=[])
    items = [{"key": f"k{i}", "title": f"t{i}", "evidence": "e", "where": "w"} for i in range(5)]
    created2 = cr.file_findings(str(gh2), "o/r", items, cap=2)
    check("filer: honours the per-run cap", len(created2) == 2, created2)


def test_no_check_flags_the_bots_own_workflow():
    # Given the REAL repo
    # When  the deterministic checks run over it
    found = (cr.check_workflow_inline_scripts(ROOT) + cr.check_cron_collisions(ROOT)
             + cr.check_reusable_orphan(ROOT))
    # Then  none of them names the code-review bot's own workflow
    naming = [f["key"] for f in found if "code-review-bot.yml" in f["key"] or "code-review-bot.yml" in f.get("where", "")]
    check("self-consistency: no check flags code-review-bot.yml", naming == [], naming)


def test_the_workflow_guards_first_and_calls_the_make_targets():
    # Given the bot's workflow
    text = (WF / "code-review-bot.yml").read_text()
    jobs = re.search(r"^jobs:\n(.*)", text, re.S | re.M).group(1)
    first_job = next(l for l in jobs.splitlines() if l.strip() and not l.lstrip().startswith("#"))
    # Then  the guard is first, admits the bot itself, lets a schedule through, and calls the targets
    check("wf: guard is the first job", first_job.lstrip().startswith("guard:"), first_job[:40])
    check("wf: the guard admits the bot itself", "github-actions[bot]" in text)
    check("wf: the guard lets a scheduled run through", '"schedule"' in text)
    check("wf: it calls make code-review-scan", "make code-review-scan REPO=" in text)
    check("wf: it calls make code-review-file", "make code-review-file REPO=" in text)
    check("wf: it never runs a repo script directly",
          not re.search(r"^\s*python3 scripts/", text, re.M))


def test_the_make_targets_pass_their_variables_through():
    for target, needle in (("code-review-scan", "scripts/code_review.py scan"),
                           ("code-review-file", "scripts/code_review.py file")):
        r = subprocess.run(["make", "-n", target, "REPO=o/r"], cwd=ROOT,
                           capture_output=True, text=True, timeout=60)
        out = r.stdout + r.stderr
        check(f"make: {target} runs the script", needle in out, out[-200:])


def test_a_secret_outside_the_contract_is_reported_with_no_api():
    """#278: the check must run WITHOUT the admin-only API, or a scan reports "no findings"
    while a third of its checks silently did not (measured: run 38868116656, `HTTP 403`).

    RED on the pre-change code: `findings()` was called with `secrets=None`, which SKIPPED
    `check_secrets_not_defined` entirely — so this finding did not exist.
    """

    # Given a workflow reading a secret the repo's contract does not declare
    root = _scratch({"a.yml": "name: a\non:\n  workflow_dispatch:\n"
                              "jobs:\n  a:\n    steps:\n      - run: echo ${{ secrets.NOT_A_SECRET }}\n"})

    # When  the deterministic checks run with NO live secret list (no `gh`, no admin)
    found = cr.findings(root)

    # Then  the undeclared secret IS reported, without any API read
    keys = [f["key"] for f in found]
    check("secrets: an undeclared secret is reported with no API read",
          "secrets-not-defined/NOT_A_SECRET" in keys, keys)
    evidence = next((f["evidence"] for f in found if f["key"] == "secrets-not-defined/NOT_A_SECRET"), "")
    check("secrets: the evidence names the contract, not `gh secret list`",
          "contract" in evidence and "gh secret list" not in evidence, evidence[:200])


def test_a_contract_secret_is_not_reported():
    """The other direction: a name IN the contract is never a finding."""
    root = _scratch({"a.yml": "name: a\non:\n  workflow_dispatch:\n"
                              "jobs:\n  a:\n    steps:\n      - run: echo ${{ secrets.HF_TOKEN }}\n"})
    keys = [f["key"] for f in cr.findings(root)]
    check("secrets: a declared secret is not reported", "secrets-not-defined/HF_TOKEN" not in keys, keys)
    check("secrets: GITHUB_TOKEN is exempt (GitHub injects it)",
          "secrets-not-defined/GITHUB_TOKEN" not in [f["key"] for f in cr.findings(
              _scratch({"b.yml": "name: b\non:\n  workflow_dispatch:\n"
                                 "jobs:\n  b:\n    steps:\n      - run: echo ${{ secrets.GITHUB_TOKEN }}\n"}))], "")


def test_the_declared_secret_contract_matches_what_the_workflows_read():
    """The contract cannot decay into a hand-maintained allowlist (#223): it must equal the set
    the workflows actually read, in BOTH directions — a new reference forces a declaration, and
    declaring a name nothing reads fails."""

    # Given this repository's workflows and the declared contract
    referenced = set(cr.referenced_secrets(ROOT)) - {"GITHUB_TOKEN"}
    declared = set(cr.DECLARED_SECRETS)

    # Then  the two sets agree exactly
    check("contract: every referenced secret is declared", referenced - declared == set(),
          f"undeclared={sorted(referenced - declared)}")
    check("contract: every declared secret is referenced", declared - referenced == set(),
          f"declared but unread={sorted(declared - referenced)}")


def test_a_commented_reference_is_not_a_read():
    """A documentation example in a comment is prose, not a secret the job reads.

    Measured: `.github/workflows/qa-validate.yml:144` documents the guard with a literal
    ``${{ secrets.X }}``. Read as a real reference it becomes a finding about the repo's own
    comment — and it did, on the first run of this check.
    """

    # Given a workflow whose ONLY mention of a secret is inside a comment
    root = _scratch({"c.yml": "name: c\non:\n  workflow_dispatch:\n"
                              "jobs:\n  c:\n    steps:\n"
                              "      # documents `${{ secrets.PROSE_ONLY }}` for the reader\n"
                              "      - run: echo hello\n"})

    # Then  nothing is reported for it
    keys = [f["key"] for f in cr.findings(root)]
    check("comments: a commented reference is not reported",
          "secrets-not-defined/PROSE_ONLY" not in keys, keys)
    check("comments: the real repo's own doc comment is not a finding",
          "secrets-not-defined/X" not in [f["key"] for f in cr.findings(ROOT)],
          [f["key"] for f in cr.findings(ROOT)])


def main() -> int:
    test_an_inline_repo_script_is_reported()
    test_two_colliding_crons_are_reported()
    test_a_reusable_orphan_is_reported()
    test_the_bot_only_lists_and_creates_issues()
    test_the_filer_is_marker_deduped_and_capped()
    test_no_check_flags_the_bots_own_workflow()
    test_the_workflow_guards_first_and_calls_the_make_targets()
    test_the_make_targets_pass_their_variables_through()
    test_a_secret_outside_the_contract_is_reported_with_no_api()
    test_a_contract_secret_is_not_reported()
    test_the_declared_secret_contract_matches_what_the_workflows_read()
    test_a_commented_reference_is_not_a_read()
    print(f"\nPASSED {_PASS} | FAILED {_FAIL}")
    return 1 if _FAIL else 0


if __name__ == "__main__":
    raise SystemExit(main())
