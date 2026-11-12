#!/usr/bin/env python3
"""architecture_block_repair.py — the DECISION behind qa-validate's `architecture-repair` job (issue #861).

`ARCHITECTURE.md`'s §10 inventory block is generated from the tree by
`scripts/architecture_bot.py`, and `make architecture-check` fails when the
committed block no longer matches it. A merged PR that moved a make target, a
script or a workflow job — without re-running `make architecture-refresh` —
reds the `push`-to-`master` `validate` run (measured 2026-11-12 after merge
`91eb093`: `FAIL repo: ARCHITECTURE.md's block matches the tree — tree '11
pipelines, 201 make targets, 71 files in scripts/' vs on disk '…199…70…'`). A
red validate on master has no PR-side repairer (rule 6q) and auto-merge of
EVERY open PR waits behind it; the only keeper that existed was the
Wednesday-only `architecture-bot`, the identical failure shape issue #304
removed for `OPENSPEC.md` — the generated pair drifts from the SAME event.

qa-validate re-runs THIS script against the exact post-merge tree that just
went red (the workflow carries the branch; the decision lives here, rule 6d):

  --classify-and-write
      DRIFT=none        the committed block IS current against this tree — the
                        red was not block staleness; nothing is written. exit 0.
      DRIFT=block-only  the block was stale; it has been rewritten IN PLACE
                        (prose untouched) and the rewrite is current by the
                        generator's own comparison. exit 0.
      the tree itself is refused by the generator (the described flow is not
                        backed), the document is missing, or its BEGIN/END
                        markers are gone -> exit 2, LOUD, naming the refusal —
                        never a silent clean, never a write. A keeper PR must
                        not launder a broken tree with a rewritten block.

  --print-pr-body
      The keeper PR body. Like the index keeper (#304) and the ledger PR
      (#802), it implements no issue and carries NO closing keyword (rule 6e):
      the tracking issue is referenced (`refs #861`), never closed here.

Local equivalent:
  make architecture-block-repair
  make architecture-block-repair-pr-body MASTER_SHA=<sha> RUN_URL=<url>
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import architecture_bot as ab  # noqa: E402  (the ONE generator — write and check agree, #479)


def classify_and_write(root: Path) -> int:
    """Classify the ARCHITECTURE block gate against THIS tree; regenerate when the drift is block-only.

    The verdict is printed as a machine-checkable `DRIFT=…` line so the workflow
    step can branch on it without re-deciding anything (rule 6d). Only the block
    between the markers is ever written — the hand-written sections above it are
    the reviewer's territory (rule 6h).
    """
    doc_path = root / "ARCHITECTURE.md"
    if not doc_path.is_file():
        print(f"[block-repair] ERROR: {doc_path} is missing — a missing description is "
              "not block drift; nothing is written.", file=sys.stderr)
        return 2
    try:
        doc = doc_path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        print(f"[block-repair] ERROR: {doc_path} could not be read: {exc}", file=sys.stderr)
        return 2

    if ab.block_on_disk(doc) is None:
        print(f"[block-repair] ERROR: ARCHITECTURE.md carries no `{ab.BEGIN}` / `{ab.END}` "
              "marker pair — the description is not generated any more; restoring the "
              "markers is a human act, nothing is written.", file=sys.stderr)
        return 2

    # The generator's own pre-write guard (rule 6h/#479): a tree whose described
    # flow is not backed is a DEFECT, not staleness. Regenerating the block over
    # it would hide the defect behind fresh-looking prose.
    problems = ab._flow_problems(root) + ab._arch_calls_problems(root)
    if problems:
        print("[block-repair] ERROR: DRIFT=tree — the generator refuses this tree; a "
              "keeper PR must not launder it with a rewritten block:", file=sys.stderr)
        for p in problems:
            print(f"[block-repair]   - {p}", file=sys.stderr)
        return 2

    try:
        fresh = ab.render(root)
    except ab.ArchitectureBotError as exc:
        print(f"[block-repair] ERROR: the tree cannot be rendered: {exc}", file=sys.stderr)
        return 2

    current = ab.block_on_disk(doc)
    assert current is not None  # the marker check above already refused its absence
    if current.strip("\n") == fresh.strip("\n"):
        print("[block-repair] DRIFT=none — ARCHITECTURE.md's inventory block is current "
              f"against this tree ({len(fresh.splitlines())} lines); the red was NOT "
              "block staleness.")
        return 0

    print("[block-repair] the committed inventory block is stale against this tree:")
    for line in ab._first_differences(current.splitlines(), fresh.splitlines()):
        print(f"[block-repair]   {line}")

    try:
        doc_path.write_text(ab.write_block(doc, fresh), encoding="utf-8")
        recheck = ab.block_on_disk(doc_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, ab.ArchitectureBotError) as exc:
        print(f"[block-repair] ERROR: the block could not be rewritten: {exc}", file=sys.stderr)
        return 2

    if recheck.strip("\n") == fresh.strip("\n"):
        print(f"[block-repair] DRIFT=block-only — ARCHITECTURE.md's §10 block regenerated "
              f"({len(fresh.splitlines())} lines); the rewrite is current and only the "
              "generated block moved.")
        return 0

    # `write` and `check` agree by construction (#479); reaching here means the
    # tree itself is the problem.
    print("[block-repair] ERROR: DRIFT=stays-stale — the regenerated block still does "
          "not match the tree; this must be fixed before any keeper PR lands.",
          file=sys.stderr)
    return 3


def compose_pr_body(master_sha: str, run_url: str) -> str:
    """Body for the architecture-repair keeper PR. It implements no issue, so it
    carries NO closing keyword (rule 6e) — the tracking issue is referenced, never closed."""
    parts = [
        "Generated inventory repair (issue #861).",
        "",
        f"A `push`-to-`master` `qa-validate` run ({run_url}) went red at the architecture "
        f"gate because `master` merged changes whose targets/scripts/jobs the committed "
        f"§10 block of `ARCHITECTURE.md` never learned about. This branch carries exactly "
        f"the regenerated block (`make architecture-block-repair` ran "
        f"`scripts/architecture_bot.py`'s generator against the merged tree "
        f"`{master_sha[:10]}` and classified the drift `block-only`).",
        "",
        "The job refuses to land unless the regenerated block is current by the generator's "
        "own comparison and `ARCHITECTURE.md` is the ONLY changed file — a red with any "
        "other cause (prose, a malformed tree) keeps this PR from opening at all.",
        "",
        "This PR records generated-artifact drift; it implements no issue, so it closes none "
        "(rule 6e). The repair path itself is tracked in refs #861.",
    ]
    return "\n".join(parts) + "\n"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description=(__doc__ or "architecture block repair").splitlines()[0])
    ap.add_argument("--root", default=str(Path(__file__).resolve().parents[1]))
    ap.add_argument("--classify-and-write", action="store_true",
                    help="classify the block gate against this tree; rewrite §10 when block-only")
    ap.add_argument("--print-pr-body", action="store_true",
                    help="print the keeper PR body (no closing keyword)")
    ap.add_argument("--master-sha", default=None, help="required for --print-pr-body")
    ap.add_argument("--run-url", default=None, help="required for --print-pr-body")
    a = ap.parse_args(argv)

    if a.print_pr_body:
        if not a.master_sha or not a.run_url:
            print("[block-repair] --print-pr-body needs --master-sha AND --run-url "
                  "(the PR must name the exact red run it repairs)", file=sys.stderr)
            return 2
        sys.stdout.write(compose_pr_body(a.master_sha, a.run_url))
        return 0

    if a.classify_and_write:
        return classify_and_write(Path(a.root))

    print("[block-repair] nothing asked: pass --classify-and-write or --print-pr-body",
          file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
