#!/usr/bin/env python3
"""openspec_index_repair.py — the DECISION behind qa-validate's `index-repair` job (issue #304).

A merged PR archives its OpenSpec change — `openspec/changes/<name>` moves to
`archive/` — so the merged tree no longer matches the committed, generated
`OPENSPEC.md`, and `make openspec-check` reds the `push`-to-`master` `validate`
run (measured 2026-11-12: pushes `28f2cd3` and `ce57e9b`, both red at the
OpenSpec gate). A red validate on master has no PR-side repairer (rule 6q) and
auto-merge of EVERY open PR waits behind it; the weekly `architecture-bot`
keeper is Wednesday-only, so the whole queue sat red for hours.

qa-validate now re-runs THIS script against the exact post-merge tree that just
went red (the workflow carries the branch; the decision lives here, rule 6d):

  --classify-and-write
      DRIFT=none        the committed index IS current against this tree — the
                        red was not index staleness; nothing is written. exit 0.
      DRIFT=index-only  the index was stale; it has been rewritten, and the
                        rewrite is current by the generator's own verdict. exit 0.
                        The drift count and its tolerance come from the generator's
                        ONE measure (`index_drift` / MAX_OPENSPEC_INDEX_DRIFT,
                        issue #1415): a drift `--check` only WARNs about is still
                        classified and repaired here, never left to accumulate.
      DRIFT=invalid-change an ACTIVE change is structurally incomplete (rule 6f:
                        proposal.md + specs/<capability>/spec.md + tasks.md). This
                        red is NOT index staleness: `openspec validate --changes`
                        refuses the change, and a regenerated index would only
                        catalogue an incomplete change. The index is left untouched
                        and the named repairer is printed — qa-validate's
                        `invalid-change-repair` job, `make
                        openspec-invalid-change-repair` (issue #962, measured on
                        run 43610043055: the keeper answered `DRIFT=none` and owned
                        nothing while every PR sat red). exit 0.
      unreadable index or change tree -> exit 2, LOUD, naming what could not be
                        read — never a silent clean.

  --print-pr-body
      The keeper PR body. Like the ledger PR (issue #802), it implements no
      issue and carries NO closing keyword (rule 6e): the tracking issue is
      referenced (`refs #304`), never closed here.

      The body names what the cited run ACTUALLY concluded, so it is true for both
      of the keeper's triggers (issue #1651). `RUN_GREEN=1` means the run's
      `validate` job stayed GREEN and only REPORTED drift, so the body says the run
      was green; without it the run red at the OpenSpec gate. The drift number is
      read from the same `index_drift` output key the `if:` clause reads — never
      re-decided here (rule 6d).

Local equivalent:
  make openspec-index-repair
  make openspec-index-repair-pr-body MASTER_SHA=<sha> RUN_URL=<url> [RUN_GREEN=1]
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import openspec_index as oi  # noqa: E402  (the ONE generator — write and check agree, #474)
# Issue #962: the structural classifier is NOT re-spelled here — one definition shared
# by the gate (`--check`), the repairer (`--classify-and-archive`) and this verdict
# (rules 6d/6m: one implementation, no second copy in the seam that reads it).
from openspec_invalid_change_repair import invalid_active_changes  # noqa: E402

#: The named repairer for the invalid-active-change shape, printed by the verdict so
#: a reader of the red run sees who owns that shape instead of assuming the index
#: keeper does (issue #962).
INVALID_REPAIRER = ("qa-validate invalid-change-repair "
                    "(`make openspec-invalid-change-repair`)")


def classify_and_write() -> int:
    """Classify the index gate against THIS tree; regenerate when the drift is index-only.

    The verdict is printed as a machine-checkable `DRIFT=…` line so the workflow
    step can branch on it without re-deciding anything (rule 6d).
    """
    # Issue #962 first, before any index rewrite: an ACTIVE change that shipped
    # without its spec/tasks is a red the index keeper must NOT answer with a
    # regenerated index (that would only catalogue the incomplete change), and it
    # must not be reported as `DRIFT=none` either — that is the shape that left
    # run 43610043055 with every PR red and no named repairer.
    try:
        invalid = invalid_active_changes(oi.CHANGES)
    except Exception as exc:  # noqa: BLE001 - an unreadable tree is a loud defect, never a clean
        print(f"[index-repair] ERROR: the change tree cannot be read: {exc}", file=sys.stderr)
        return 2
    if invalid:
        print(f"[index-repair] DRIFT=invalid-change — {len(invalid)} ACTIVE change(s) are "
              "structurally incomplete (rule 6f):")
        for name, problems in invalid:
            print(f"[index-repair]   {name}: {', '.join(problems)}")
        print(f"[index-repair] this red is NOT index staleness: {oi.INDEX.name} is left "
              f"untouched, and the named repairer is {INVALID_REPAIRER}")
        return 0

    try:
        fresh = oi.render()
    except Exception as exc:  # noqa: BLE001 - an unreadable tree is a loud defect, never a clean
        print(f"[index-repair] ERROR: the change tree cannot be read: {exc}", file=sys.stderr)
        return 2

    try:
        current = oi.INDEX.read_text(encoding="utf-8") if oi.INDEX.is_file() else ""
    except (OSError, UnicodeDecodeError) as exc:
        print(f"[index-repair] ERROR: {oi.INDEX} could not be read: {exc}", file=sys.stderr)
        return 2

    active, archived = oi.discover()

    if current == fresh:
        print(f"[index-repair] DRIFT=none — {oi.INDEX.name} is current against this tree "
              f"({len(active)} active, {len(archived)} archived); the red was NOT index staleness.")
        return 0

    print(f"[index-repair] the committed index is stale against this tree "
          f"({len(active)} active, {len(archived)} archived on disk):")
    # Issue #1415: the drift measure is the generator's ONE (`index_drift`), and
    # the tolerance is its ONE constant — so a drift the gate only WARNs about is
    # still classified by count here and repaired, never left to accumulate.
    drift, reasons = oi.index_drift(current, fresh, active, archived)
    for reason in reasons:
        print(f"[index-repair]   {reason}")
    tolerated = "within" if drift <= oi.MAX_OPENSPEC_INDEX_DRIFT else "above"
    print(f"[index-repair]   {drift} differing change(s) — {tolerated} the tolerated "
          f"MAX_OPENSPEC_INDEX_DRIFT={oi.MAX_OPENSPEC_INDEX_DRIFT}; regenerating")

    try:
        oi.INDEX.write_text(fresh, encoding="utf-8")
        recheck = oi.render()
    except Exception as exc:  # noqa: BLE001
        print(f"[index-repair] ERROR: the index could not be rewritten: {exc}", file=sys.stderr)
        return 2

    if recheck == oi.INDEX.read_text(encoding="utf-8"):
        print(f"[index-repair] DRIFT=index-only — {oi.INDEX.name} regenerated "
              f"({len(active)} active, {len(archived)} archived); the rewrite is current.")
        return 0

    # `write` and `check` agree by construction (#474); reaching here means the
    # tree itself is the problem, and the named changes are the ones to fix.
    print(f"[index-repair] ERROR: DRIFT=stays-stale — the regenerated index still does not "
          f"match disk; these changes must be fixed before any keeper PR: "
          f"{', '.join(name for name, _ in active + archived)}", file=sys.stderr)
    return 3


def compose_pr_body(master_sha: str, run_url: str, *, run_green: bool = False,
                    index_drift: int | None = None) -> str:
    """Body for the index-repair keeper PR. It implements no issue, so it carries
    NO closing keyword (rule 6e) — the tracking issue is referenced, never closed.

    The FIRST sentence names what the cited run actually concluded (issue #1651):
    a red `validate` (`run_green=False`) versus a GREEN `validate` that only
    reported drift (`run_green=True`). Both are true of one of this keeper's two
    triggers — `failure()` and the drift clause — so the record never claims a red
    the run did not have (rules 2/6g). `index_drift` is the number the run's
    `validate.outputs.index_drift` key carried; it is REPORTED, never decided here.
    """
    if run_green:
        lead = (f"A `push`-to-`master` `qa-validate` run ({run_url}) stayed GREEN at the "
                f"OpenSpec gate and only REPORTED index drift")
        if index_drift is not None:
            lead += f" (`drift={index_drift}`)"
        lead += (" because `master` merged changes whose rows/archive state the committed "
                 "`OPENSPEC.md` never learned about.")
    else:
        lead = (f"A `push`-to-`master` `qa-validate` run ({run_url}) went red at the "
                f"OpenSpec gate because `master` merged changes whose rows/archive state "
                f"the committed `OPENSPEC.md` never learned about.")
    parts = [
        "Generated index repair (issue #304).",
        "",
        lead + f" This branch carries exactly the regenerated file "
        f"(`make openspec-index-repair` ran `scripts/openspec_index.py`'s generator against "
        f"the merged tree `{master_sha[:10]}` and classified the drift `index-only`).",
        "",
        "The job refuses to land unless the regenerated index is current by the generator's "
        "own verdict and `OPENSPEC.md` is the ONLY changed file — a validate with any other "
        "cause keeps this PR from opening at all.",
        "",
        "This PR records generated-artifact drift; it implements no issue, so it closes none "
        "(rule 6e). The repair path itself is tracked in refs #304.",
    ]
    return "\n".join(parts) + "\n"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=(__doc__ or "openspec index repair").splitlines()[0])
    ap.add_argument("--classify-and-write", action="store_true",
                    help="classify the index gate against this tree; rewrite OPENSPEC.md when index-only")
    ap.add_argument("--print-pr-body", action="store_true",
                    help="print the keeper PR body (no closing keyword)")
    ap.add_argument("--master-sha", default=None, help="required for --print-pr-body")
    ap.add_argument("--run-url", default=None, help="required for --print-pr-body")
    ap.add_argument("--run-green", action="store_true",
                    help="the cited run's validate stayed GREEN and only reported drift (issue #1651)")
    ap.add_argument("--index-drift", type=int, default=None,
                    help="the drift count the run's validate reported (issue #1651)")
    a = ap.parse_args(argv)

    if a.print_pr_body:
        if not a.master_sha or not a.run_url:
            print("[index-repair] --print-pr-body needs --master-sha AND --run-url "
                  "(the PR must name the exact run it repairs)", file=sys.stderr)
            return 2
        sys.stdout.write(compose_pr_body(a.master_sha, a.run_url,
                                         run_green=a.run_green, index_drift=a.index_drift))
        return 0

    if a.classify_and_write:
        return classify_and_write()

    print("[index-repair] nothing asked: pass --classify-and-write or --print-pr-body",
          file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
