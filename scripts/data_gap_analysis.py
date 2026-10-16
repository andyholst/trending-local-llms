#!/usr/bin/env python3
"""Post-refresh data-gap analysis (issue #115).

Every refresh acquires new data and merges it into `data/models.json`. This
stage asks the question the merge cannot: **what does the store still not
capture** — and files it as a GitHub issue, so the missing dimension is a
tracked work item instead of a paragraph in a PR body.

The flagship gap is memory that is not VRAM. The store records `vram_tier` /
`vram_min` and nothing else, while
  * the CPU and Metal tables are RAM-bound (Apple Silicon is unified memory —
    "VRAM" and system RAM are one pool),
  * llama.cpp partial offload keeps the un-offloaded layers + the KV cache in
    system RAM for every "8-48 GB GPU" entry,
  * MoE offload (Strata) splits experts across GPU / RAM / SSD,
and `skills/gather-data.md` already asks the search agent for "VRAM / RAM" — a
figure the contract (`additionalProperties: false`) prunes silently, which is
why it survives only as free text inside `quant` / `why` / notes.

  data_gap_analysis.py                  # report to stdout
  data_gap_analysis.py --out report.md
  data_gap_analysis.py --baseline FILE  # set the baseline path (default data/gap_baseline.json)
  data_gap_analysis.py --issue          # file ONE issue when the signature changed
  data_gap_analysis.py --write-baseline # record the signature as the baseline, filing nothing
  data_gap_analysis.py --check          # exit 1 when the gap set changed (CI-visible)

The baseline is written on TWO paths: `--issue` records it when it files (so a
day with the same gap set files nothing), and `--write-baseline` records it
WITHOUT filing — the repair for a baseline write lost to a rebase or a refresh
PR closed before it merged, reachable as `make data-gap-baseline`.

Report only by default: it never fails the data PR. Stdlib only.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# The refresh run's window block (issue #199) — the ONE composer this and the aggregate
# PR step both use, so an issue filed BY a refresh carries the same block as the PR.
sys.path.insert(0, str(Path(__file__).resolve().parent))

import refresh_run_block  # noqa: E402
DATA = Path(os.environ.get("TRENDING_DATA_DIR", str(ROOT / "data")))
STORE = DATA / "models.json"
CONTRACT = DATA / "model_contract.json"
SEARCH_CONTRACT = DATA / "search_contract.json"
RAW_DIR = DATA / "raw"
DEFAULT_BASELINE = DATA / "gap_baseline.json"
LABEL = "data-gap-analysis"
LABEL_COLOR = "5319e7"
LABEL_DESCRIPTION = "Post-refresh data-gap analysis (missing requirement dimensions in the store)"

# Requirement dimensions the index SHOULD carry. `key` is the structured key the
# contract must declare for the dimension to be representable at all; `text` is
# how the figure shows up today when it is only prose (measured on the store).
DIMENSIONS = (
    {
        "key": "system_ram_min",
        "label": "system RAM / unified memory requirement",
        "text": re.compile(r"\b\d+(?:\.\d+)?\s*(?:gb|mb|tb)\b[^.\n]{0,20}\bram\b|\bram\b[^.\n]{0,20}\b\d+(?:\.\d+)?\s*(?:gb|mb)\b", re.I),
        "why": "CPU and Metal tables are RAM-bound; partial offload + KV cache live in system RAM",
    },
    {
        "key": "weight_gb",
        "label": "weight footprint per format + quant",
        "text": re.compile(r"\b\d+(?:\.\d+)?\s*(?:gb|mb)\b", re.I),
        "why": "the real budget a run needs before any context is allocated",
    },
    {
        "key": "context_tokens",
        "label": "context window / KV-cache cost",
        "text": re.compile(r"\b\d+\s*k\b|\bcontext\b|\bkv[- ]?cache\b", re.I),
        "why": "KV cache scales with context and consumes RAM and VRAM alike",
    },
    {
        "key": "storage_offload",
        "label": "storage-offload requirement (experts on SSD)",
        "text": re.compile(r"\bssd\b|\bdisk\b|\boffload", re.I),
        "why": "MoE engines (Strata) run big models by streaming experts from storage",
    },
    {
        "key": "engine_min_version",
        "label": "engine minimum version / required flags",
        "text": re.compile(r"\bflag\b|\bn[-_]gpu[-_]layers\b|\b--\w", re.I),
        "why": "many figures only reproduce on a specific engine build or with explicit flags",
    },
)

# Fields whose free text is scanned for a dimension that has no structured key.
TEXT_FIELDS = ("quant", "hardware", "why")
STALE_DAYS = 30


def load(path: Path, default=None):
    if not path.exists():
        return default
    return json.loads(path.read_text())


def contract_keys() -> dict:
    """The keys the contracts can actually hold, so a dimension the store cannot
    represent is reported as a CONTRACT gap (the field is pruned at ingest)."""
    model, measurement = set(), set()
    c = load(CONTRACT, {}) or {}
    items = ((c.get("properties") or {}).get("models") or {}).get("items") or {}
    model = set((items.get("properties") or {}).keys())
    eng = (items.get("properties") or {}).get("engines") or {}
    measurement = set(((eng.get("items") or {}).get("properties") or {}).keys())
    s = load(SEARCH_CONTRACT, {}) or {}
    sitems = ((s.get("properties") or {}).get("models") or {}).get("items") or {}
    return {
        "model": model,
        "measurement": measurement,
        "search_model": set((sitems.get("properties") or {}).keys()),
    }


def analyse(store: dict, contract: dict, raw_dir: Path = RAW_DIR) -> dict:
    """The gap report: per-dimension coverage, free-text-only mentions, and the
    store/maintenance gaps the refresh cannot see."""
    models = store.get("models") or []
    declared_model = contract["model"] | contract["search_model"]
    declared_measurement = contract["measurement"]
    gaps: list[str] = []          # volatile-ish findings, reported but not signatured
    missing: dict[str, list[str]] = {}   # dimension -> model ids with no structured value
    unstructured: dict[str, list[str]] = {}
    contract_gaps: dict[str, str] = {}

    for dim in DIMENSIONS:
        key = dim["key"]
        if key not in declared_model and key not in declared_measurement:
            contract_gaps[key] = (
                f"`{key}` is not declared in model_contract.json/search_contract.json — "
                f"the value is pruned at ingest, so {dim['label']} cannot be stored")
        ids = [m.get("id", "?") for m in models if not m.get(key)]
        missing[key] = ids
        text_models = []
        for m in models:
            if m.get(key):
                continue
            # free text lives on the model (quant/why) AND on every measurement
            # (a figure written into a measurement's `quant` is exactly the case
            # measured on the store: "1432 MB peak RAM")
            hay = " ".join(str(m.get(f, "")) for f in TEXT_FIELDS)
            hay += " ".join(str(e.get(f, "")) for e in (m.get("engines") or []) for f in TEXT_FIELDS)
            hay += " ".join(str((store.get("engines") or {}).get(n, {}).get("note", ""))
                            for n in (m.get("supported_engines") or []))
            if dim["text"].search(hay):
                text_models.append(m.get("id", "?"))
        unstructured[key] = text_models

    # maintenance gaps the merge/sort cannot report
    as_of = None
    gen = store.get("generated_utc")
    if gen:
        as_of = datetime.strptime(gen, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    cutoff = (as_of - timedelta(days=STALE_DAYS)).date() if as_of else None
    stale = []
    for m in models:
        dates = sorted(str(e.get("date", "")) for e in (m.get("engines") or []))
        if cutoff and (not dates or dates[-1] < cutoff.isoformat()):
            stale.append(m.get("id", "?"))
    thin = [f"{m.get('id', '?')}/{e.get('engine', '?')}"
            for m in models for e in (m.get("engines") or [])
            if not e.get("hardware") or not e.get("quant")]
    estimated = [f"{m.get('id', '?')}/{e.get('engine', '?')}:{e.get('tps')}"
                 for m in models for e in (m.get("engines") or [])
                 if "est" in str(e.get("tps", "")).lower()]
    empty_legs = []
    for f in sorted(raw_dir.glob("*.json")) if raw_dir.exists() else []:
        d = load(f, {}) or {}
        if not (d.get("models") or []):
            empty_legs.append(f.name)

    for key, ids in missing.items():
        if ids:
            gaps.append(f"{len(ids)}/{len(models)} models have no structured `{key}` "
                        f"(e.g. {', '.join(ids[:5])})")
    for key, ids in unstructured.items():
        if ids:
            gaps.append(f"{len(ids)} model(s) name the value only in free text, not in `{key}`: "
                        f"{', '.join(ids[:5])}")
    if stale:
        gaps.append(f"{len(stale)} model(s) have no measurement in the last {STALE_DAYS} days: "
                    f"{', '.join(stale[:5])}")
    if thin:
        gaps.append(f"{len(thin)} measurement(s) carry no hardware or no quant: {', '.join(thin[:5])}")
    if estimated:
        gaps.append(f"{len(estimated)} measurement(s) are estimates: {', '.join(estimated[:5])}")
    # Empty raw legs are INFORMATIONAL: a per-query write legitimately captures
    # nothing (the query had no hits), so they are reported but never filed as a
    # gap — only a whole refresh with no models at all would be a defect.
    informational = []
    if empty_legs:
        informational.append(f"{len(empty_legs)} raw leg(s) captured 0 models "
                             f"(a query with no hits — informational)")

    # signature = what the STORE lacks (stable across refreshes), so a day with
    # identical gaps opens no second issue; volatile findings (raw legs, estimates)
    # stay in the report only.
    signature = sorted(
        [f"contract:{k}" for k in contract_gaps]
        + [f"missing:{k}:{mid}" for k, ids in missing.items() for mid in ids]
        + [f"unstructured:{k}:{mid}" for k, ids in unstructured.items() for mid in ids]
    )
    return {
        "as_of": gen,
        "models": len(models),
        "dimensions": {d["key"]: {"label": d["label"], "why": d["why"]} for d in DIMENSIONS},
        "contract_gaps": contract_gaps,
        "missing": missing,
        "unstructured": unstructured,
        "maintenance": {"stale": stale, "thin_measurements": thin,
                        "estimated": estimated, "empty_raw_legs": empty_legs},
        "findings": gaps,
        "informational": informational,
        "signature": signature,
    }


def rank_impact(report: dict) -> list[tuple[str, int]]:
    """Gaps ranked by how many models they unblock (a dimension that is missing on
    every model outranks a per-model maintenance item)."""
    ranked = []
    for key, ids in report["missing"].items():
        if ids:
            ranked.append((key, len(ids)))
    for key, ids in report["unstructured"].items():
        if ids:
            ranked.append((f"unstructured:{key}", len(ids)))
    return sorted(ranked, key=lambda kv: (-kv[1], kv[0]))


def render(report: dict) -> str:
    lines = [
        "# data-gap analysis",
        "",
        f"- as of: `{report['as_of']}`",
        f"- models: {report['models']}",
        f"- gap signature entries: {len(report['signature'])}",
        "",
        "## Gaps, ranked by models unblocked",
        "",
    ]
    for key, n in rank_impact(report):
        lines.append(f"- **{key}** — {n} model(s)")
    if not report["findings"]:
        lines.append("- none")
    lines += ["", "## Contract gaps (the store cannot hold the value)", ""]
    for key, why in report["contract_gaps"].items():
        lines.append(f"- {why}")
    if not report["contract_gaps"]:
        lines.append("- none")
    lines += ["", "## Findings", ""]
    lines += [f"- {f}" for f in report["findings"]] or ["- none"]
    return "\n".join(lines) + "\n"


def changed(report: dict, baseline_path: Path) -> tuple[bool, dict | None]:
    previous = load(baseline_path)
    if previous is None:
        return True, None
    return report["signature"] != previous.get("signature", []), previous


def write_baseline(report: dict, path: Path) -> None:
    path.write_text(json.dumps({"as_of": report["as_of"], "signature": report["signature"]},
                               indent=2, sort_keys=True) + "\n")


def signature_id(report: dict) -> str:
    """A stable id for the gap SET (the issue marker), independent of `as_of`."""
    return hashlib.sha256("\n".join(report["signature"]).encode()).hexdigest()[:12]


def marker(sig: str) -> str:
    """The invisible marker carried in the issue body, searched for on the next run."""
    return f"<!-- data-gap-signature: {sig} -->"


def already_filed(sig: str) -> str | None:
    """The URL of an OPEN issue already carrying this gap signature, or None.

    The baseline only reaches the repository through the refresh PR, so between
    filing and that merge every run computes "changed" from the same old baseline
    and would file the same issue again (two crons a day can both do it) — and a
    refresh PR closed without merging would re-file it forever. A CLOSED issue
    does not block: a closed gap-issue means the work was done or dropped, so the
    gap set re-appearing later is new information, not a duplicate (#157).
    """
    out = subprocess.run(
        ["gh", "issue", "list", "--state", "all", "--label", LABEL,
         "--search", f"{sig} in:body", "--json", "number,state,url"],
        text=True, capture_output=True)
    if out.returncode != 0:
        raise SystemExit(f"[data-gaps] gh issue list failed: {out.stderr.strip()}")
    try:
        items = json.loads(out.stdout or "[]")
    except json.JSONDecodeError:
        items = []
    for item in items:
        if item.get("state") == "OPEN":
            return str(item.get("url") or item.get("number"))
    return None


def label_exists() -> bool:
    """Does the repo already carry LABEL?"""
    out = subprocess.run(["gh", "label", "list", "--search", LABEL, "--json", "name"],
                         text=True, capture_output=True)
    if out.returncode != 0:
        raise SystemExit(f"[data-gaps] gh label list failed: {out.stderr.strip()}")
    try:
        return LABEL in {str(l.get("name", "")) for l in json.loads(out.stdout or "[]")}
    except json.JSONDecodeError:
        return False


def ensure_label_exists() -> None:
    """Create LABEL when the repo does not have it yet, or fail loudly.

    GitHub IGNORES a label it does not know instead of refusing the create, so a
    filing made before the label exists lands UNLABELLED while `gh issue create`
    still returns 0 — and `gh issue edit --add-label` then refuses it, which is
    the shape measured on master (issue #277, the same shape #161 recorded): the
    filed issue carried nothing, the step was `continue-on-error`, and BOTH bot
    queues stayed empty while every run reported green. Creating the label first
    is what makes the label land instead of being dropped.
    """
    if label_exists():
        return
    out = subprocess.run(["gh", "label", "create", LABEL, "--color", LABEL_COLOR,
                          "--description", LABEL_DESCRIPTION], text=True, capture_output=True)
    if not label_exists():
        why = (out.stderr or out.stdout or "").strip() or f"gh exited {out.returncode} without a message"
        raise SystemExit(
            f"[data-gaps] the repo does not carry `{LABEL}` and it could not be created — the "
            f"bot chain triggers on that label, so every filing would be invisible; failing "
            f"instead of reporting it. gh said: {why}")


def ensure_label(number: str) -> None:
    """Make the filed issue carry LABEL, or fail loudly (issue #161).

    The label is the trigger of the downstream chain: `issue-bot.yml` reacts to
    newly opened issues, its sweep picks open `data-gap-analysis` ones — one
    implementer per issue. Measured: the CLI created the issue and returned 0
    while applying NO label (the label exists and is appliable to that issue), so
    the filing was invisible to both bots and nothing was red.
    """
    def labels() -> set[str]:
        out = subprocess.run(["gh", "issue", "view", number, "--json", "labels"],
                             text=True, capture_output=True)
        if out.returncode != 0:
            raise SystemExit(f"[data-gaps] gh issue view {number} failed: {out.stderr.strip()}")
        try:
            return {str(l.get("name", "")) for l in json.loads(out.stdout or "{}").get("labels", [])}
        except json.JSONDecodeError:
            return set()

    if LABEL in labels():
        return
    # The label must EXIST before an edit can apply it: GitHub ignores a label it
    # does not know, which is how a filing lands unlabelled while `gh` returns 0.
    ensure_label_exists()
    edit = subprocess.run(["gh", "issue", "edit", number, "--add-label", LABEL],
                          text=True, capture_output=True)
    if LABEL not in labels():
        # `gh`'s OWN diagnosis is the actionable half: measured (issue #277), the
        # refusal is `Resource not accessible by personal access token` because the
        # step ran with a PAT that declares no Issues scope. Swallowing it left
        # "the label did not stick" with no cause and no fix.
        why = (edit.stderr or edit.stdout or "").strip() or f"gh exited {edit.returncode} without a message"
        raise SystemExit(
            f"[data-gaps] issue {number} does not carry `{LABEL}` after re-applying it — the "
            f"bot chain triggers on that label, so this filing would be invisible; failing "
            f"instead of reporting it. gh said: {why}")


def file_issue(report: dict, previous: dict | None) -> str:
    """One issue per changed gap set. The body is the report + the ranked gaps."""
    added = sorted(set(report["signature"]) - set((previous or {}).get("signature", [])))
    ranked = rank_impact(report)
    body = [
        "## Goal",
        "",
        "Close the data gaps the refresh acquired but the store does not capture.",
        "Every item below is real data the search sees and the contract drops or",
        "leaves unstructured — never invent a value, and never remove a key",
        "(additive contract changes only; a new key is OPTIONAL, never `required`).",
        "",
        "## Ranked gaps",
        "",
    ]
    body += [f"- **{k}** — {n} model(s)" for k, n in ranked] or ["- none"]
    body += ["", "## Contract gaps", ""]
    body += [f"- {why}" for why in report["contract_gaps"].values()] or ["- none"]
    if added:
        body += ["", "## New since the last analysis", ""] + [f"- `{a}`" for a in added[:40]]
    body += ["", "## Full report", "", "```", render(report).strip(), "```"]
    # The window of the run that FILED this, at the TOP (issue #199): the same block the
    # refresh PR carries, from the same composer — so an issue filed BY a refresh can be
    # told apart from one filed by an earlier run. "" only when there is no run to
    # describe (a local `make data-gap-issue`); a `gh` read that fails raises instead.
    block = refresh_run_block.current_block()
    if block:
        body = [*block.splitlines(), "", *body]
    # The marker lets the NEXT run recognise this gap set (issue #157). Invisible
    # in the rendered issue, searchable in the body.
    body += ["", marker(signature_id(report))]
    title = (f"data-gap: {ranked[0][0]} ({ranked[0][1]} models)" if ranked else "data-gap: refresh analysis")
    # The label must exist BEFORE the create: GitHub silently ignores an unknown
    # label, so `--label` below would be dropped and the filing would be invisible
    # to both bots while `gh` still exits 0 (issue #277).
    ensure_label_exists()
    out = subprocess.run(
        ["gh", "issue", "create", "--title", f"{title} ({report['as_of']})",
         "--body-file", "-", "--label", LABEL],
        input="\n".join(body), text=True, capture_output=True)
    if out.returncode != 0:
        raise SystemExit(f"[data-gaps] gh issue create failed: {out.stderr.strip()}")
    url = out.stdout.strip()
    # The label is what the downstream bot chain triggers on; a create that
    # returns 0 without it files an issue nothing will ever implement (#161).
    ensure_label(url.rstrip("/").split("/")[-1])
    return url


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Post-refresh data-gap analysis")
    ap.add_argument("--out", help="write the markdown report here (default stdout)")
    ap.add_argument("--baseline", default=str(DEFAULT_BASELINE))
    ap.add_argument("--issue", action="store_true", help="file ONE issue when the gap set changed")
    ap.add_argument("--check", action="store_true", help="exit 1 when the gap set changed")
    ap.add_argument("--write-baseline", action="store_true",
                    help="record the current gap signature as the baseline (no issue)")
    a = ap.parse_args(argv)

    store = load(STORE)
    if store is None:
        print(f"[data-gaps] {STORE} missing", file=sys.stderr)
        return 1
    report = analyse(store, contract_keys())
    text = render(report)

    baseline_path = Path(a.baseline)
    is_changed, previous = changed(report, baseline_path)
    if a.out:
        Path(a.out).write_text(text)
    else:
        print(text)
    print(f"[data-gaps] signature {'CHANGED' if is_changed else 'unchanged'} "
          f"({len(report['signature'])} entries, {len(rank_impact(report))} ranked gaps)",
          file=sys.stderr)

    if a.write_baseline:
        write_baseline(report, baseline_path)
        print(f"[data-gaps] baseline written to {baseline_path} ({len(report['signature'])} entries)",
              file=sys.stderr)
    if a.issue and is_changed:
        sig = signature_id(report)
        existing = already_filed(sig)
        if existing:
            # The baseline reaches master only through the refresh PR, so a second
            # run before that merge (or after a PR was closed) sees the same change:
            # report it, file nothing (issue #157).
            print(f"[data-gaps] gap set {sig} is already filed: {existing} — no duplicate",
                  file=sys.stderr)
        else:
            url = file_issue(report, previous)
            print(f"[data-gaps] filed {url}", file=sys.stderr)
            write_baseline(report, baseline_path)
    elif a.issue:
        print("[data-gaps] no new gap set — no issue filed", file=sys.stderr)
    if a.check and is_changed:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
