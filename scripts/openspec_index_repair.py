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
      unreadable index or change tree -> exit 2, LOUD, naming what could not be
                        read — never a silent clean.

  --print-pr-body
      The keeper PR body. Like the ledger PR (issue #802), it implements no
      issue and carries NO closing keyword (rule 6e): the tracking issue is
      referenced (`refs #304`), never closed here.

Local equivalent:
  make openspec-index-repair
  make openspec-index-repair-pr-body MASTER_SHA=<sha> RUN_URL=<url>
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import openspec_index as oi  # noqa: E402  (the ONE generator — write and check agree, #474)


def classify_and_write() -> int:
    """Classify the index gate against THIS tree; regenerate when the drift is index-only.

    The verdict is printed as a machine-checkable `DRIFT=…` line so the workflow
    step can branch on it without re-deciding anything (rule 6d).
    """
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
    for reason in oi._why_stale(current, fresh, active, archived):
        print(f"[index-repair]   {reason}")

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


def compose_pr_body(master_sha: str, run_url: str) -> str:
    """Body for the index-repair keeper PR. It implements no issue, so it carries
    NO closing keyword (rule 6e) — the tracking issue is referenced, never closed."""
    parts = [
        "Generated index repair (issue #304).",
        "",
        f"A `push`-to-`master` `qa-validate` run ({run_url}) went red at the OpenSpec gate "
        f"because `master` merged changes whose rows/archive state the committed `OPENSPEC.md` "
        f"never learned about. This branch carries exactly the regenerated file "
        f"(`make openspec-index-repair` ran `scripts/openspec_index.py`'s generator against "
        f"the merged tree `{master_sha[:10]}` and classified the drift `index-only`).",
        "",
        "The job refuses to land unless the regenerated index is current by the generator's "
        "own verdict and `OPENSPEC.md` is the ONLY changed file — a red with any other cause "
        "keeps this PR from opening at all.",
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
    a = ap.parse_args(argv)

    if a.print_pr_body:
        if not a.master_sha or not a.run_url:
            print("[index-repair] --print-pr-body needs --master-sha AND --run-url "
                  "(the PR must name the exact red run it repairs)", file=sys.stderr)
            return 2
        sys.stdout.write(compose_pr_body(a.master_sha, a.run_url))
        return 0

    if a.classify_and_write:
        return classify_and_write()

    print("[index-repair] nothing asked: pass --classify-and-write or --print-pr-body",
          file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
