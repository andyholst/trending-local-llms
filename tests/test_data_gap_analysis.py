#!/usr/bin/env python3
"""Post-refresh data-gap analysis (issue #115).

The analysis must (a) report a requirement dimension the CONTRACT cannot hold as a
contract gap, (b) separate a value that exists only as free text from one that is
actually stored, (c) file exactly ONE issue when the gap set changed — none when it
did not, and (d) be wired into the Makefile and the refresh pipeline (rule 6d: no
dead script). Every dimension it reports must also be CAPTURABLE end to end: its
key declared OPTIONAL in BOTH contracts and merged at ingest onto an existing
model — a dimension the store can hold but never receives is still a gap — and
every value a model CARRIES must trace to a real `…/status/<id>` post: closing a
gap by inventing a figure (or by reading one the post never gave) is the one
failure this stage must never make. Wired into `make test`.

Run:  python3 tests/test_data_gap_analysis.py    or   make test
"""
from __future__ import annotations

import json
import os
import re
import stat
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import data_gap_analysis as G  # noqa: E402

_PASS = 0
_FAIL = 0


def check(name, cond, detail=""):
    global _PASS, _FAIL
    if cond:
        _PASS += 1
        print(f"  ok  {name}")
    else:
        _FAIL += 1
        print(f"  FAIL {name}" + (f"  [{detail}]" if detail else ""))


def store_with(models: list[dict]) -> dict:
    return {"generated_utc": "2026-10-14T06:00:00Z",
            "engines": {"llama.cpp": {"backend": "CUDA / CPU", "note": "x", "url": "https://u"}},
            "models": models}


def model(mid: str, **extra) -> dict:
    m = {"id": mid, "name": mid, "full_name": mid, "type": "LLM", "license": "Apache 2.0",
         "params": "27B", "hf": f"a/{mid}", "vram_tier": "16GB", "vram_min": "12GB",
         "backends": ["CUDA"], "supported_engines": ["llama.cpp"], "why": "w",
         "last_seen": "2026-10-14",
         "engines": [{"engine": "llama.cpp", "tps": "91", "hardware": "RTX 4090 24GB",
                      "quant": "Q4_K_M", "date": "2026-10-14",
                      "source_post": "https://lightbrd.com/u/status/1"}]}
    m.update(extra)
    return m


def contract_declaring(*keys: str) -> dict:
    """A contract that declares `keys` on a model — the shape only matters for the
    keys, which is what the analysis reads."""
    return {
        "properties": {"models": {"items": {"properties": {k: {"type": "string"} for k in keys}
                                            | {"id": {"type": "string"}},
                                   }}},
    }


def test_contract_gap_vs_stored_dimension():
    """A dimension absent from the contract is a CONTRACT gap (ingest prunes it);
    one the contract declares is only 'missing values'."""

    # Given a store with a model and a contract that declares system_ram_min
    with tempfile.TemporaryDirectory() as td:
        cp = Path(td) / "contract.json"
        cp.write_text(json.dumps(contract_declaring("id", "system_ram_min")))
        saved_c, saved_s = G.CONTRACT, G.SEARCH_CONTRACT
        G.CONTRACT, G.SEARCH_CONTRACT = cp, Path(td) / "absent.json"
        try:
            contract = G.contract_keys()
        finally:
            G.CONTRACT, G.SEARCH_CONTRACT = saved_c, saved_s

        # When  the store is analysed
        report = G.analyse(store_with([model("m1")]), contract, raw_dir=Path(td) / "raw")

        # Then  system_ram_min is NOT a contract gap, but the value is missing
        check("declared key is not a contract gap", "system_ram_min" not in report["contract_gaps"])
        check("declared key with no value is 'missing'", report["missing"]["system_ram_min"] == ["m1"])
        # And  a dimension the contract does not declare IS a contract gap
        check("undeclared dimension is a contract gap", "context_tokens" in report["contract_gaps"])
        check("contract gap explains the prune",
              "pruned at ingest" in report["contract_gaps"]["context_tokens"])


def test_free_text_mention_is_unstructured_not_present():
    """A RAM figure that lives inside `quant` is unstructured data, not stored data —
    the exact gap measured on the store (Gemma 4 edge: '1432 MB peak RAM')."""

    # Given a model whose only RAM figure is free text inside `quant`
    m = model("gemma-4-e2b", quant=None)
    m["engines"][0]["quant"] = "1432 MB peak RAM"
    m["why"] = "runs on a Raspberry Pi 5 at 1432 MB peak RAM"

    # When  it is analysed
    report = G.analyse(store_with([m]), {"model": set(), "measurement": set(), "search_model": set()},
                       raw_dir=Path("/nonexistent"))

    # Then  it is reported as free-text-only, and never as having the dimension
    check("free-text RAM is flagged unstructured", report["unstructured"]["system_ram_min"] == ["gemma-4-e2b"])
    check("the model still counts as missing system_ram_min", report["missing"]["system_ram_min"] == ["gemma-4-e2b"])
    check("the finding names the free-text case",
          any("free text" in f for f in report["findings"]), str(report["findings"]))


def test_signature_tracks_the_store_not_the_noise():
    """The issue-triggering signature covers what the STORE lacks; volatile items
    (empty raw legs, estimates) stay in the report and out of the signature."""

    # Given one store, analysed twice
    contract = {"model": set(), "measurement": set(), "search_model": set()}
    a = G.analyse(store_with([model("m1")]), contract, raw_dir=Path("/nonexistent"))
    b = G.analyse(store_with([model("m1")]), contract, raw_dir=Path("/nonexistent"))

    # Then  the signature is stable
    check("same data -> same signature", a["signature"] == b["signature"])
    check("signature covers the missing dimensions",
          "missing:system_ram_min:m1" in a["signature"], str(a["signature"]))

    # And  a new model missing a dimension changes it
    c = G.analyse(store_with([model("m1"), model("m2")]), contract, raw_dir=Path("/nonexistent"))
    check("a new model changes the signature", c["signature"] != a["signature"])

    # And  an estimate-only difference does NOT (it is report-only)
    d = store_with([model("m1")])
    d["models"][0]["engines"][0]["tps"] = "91 (est)"
    report = G.analyse(d, contract, raw_dir=Path("/nonexistent"))
    check("an '(est)' t/s is reported but does not change the signature",
          report["signature"] == a["signature"] and bool(report["maintenance"]["estimated"]))


def test_one_issue_per_changed_gap_set(tmp_path=None, monkeypatch=None):
    """`--issue` files ONE issue when the gap set changed and none when it did not;
    the `gh` call is the real subprocess, against a stub CLI on PATH."""
    if tmp_path is None:  # the standalone runner passes no pytest fixture
        with tempfile.TemporaryDirectory() as td:
            return _one_issue_per_changed_gap_set(Path(td))
    return _one_issue_per_changed_gap_set(Path(tmp_path))


def _one_issue_per_changed_gap_set(tmp_path):
    # Given a stub `gh` on PATH that records how it was called
    bindir = tmp_path / "bin"
    bindir.mkdir()
    log = tmp_path / "gh.log"
    gh = bindir / "gh"
    # `issue view` answers the label verification (issue #161): the filer now
    # checks that the issue it filed carries the label the bots trigger on.
    gh.write_text(f"#!/bin/sh\nprintf '%s\\n' \"$@\" >> {log}\n"
                  "case \"$1 $2\" in\n"
                  "  'issue view') printf '%s\\n' '{\"labels\":[{\"name\":\"data-gap-analysis\"}]}' ;;\n"
                  "  'label list') printf '%s\\n' '[{\"name\":\"data-gap-analysis\"}]' ;;\n"
                  f"  *) cat >> {log}\n"
                  "     printf '%s\\n' 'https://github.com/andyholst/trending-local-llms/issues/999' ;;\n"
                  "esac\n")
    gh.chmod(gh.stat().st_mode | stat.S_IEXEC)

    store = tmp_path / "models.json"
    store.write_text(json.dumps(store_with([model("m1"), model("m2")])))
    baseline = tmp_path / "gap_baseline.json"
    saved_path = os.environ["PATH"]
    os.environ["PATH"] = f"{bindir}:{saved_path}"
    saved_store, saved_contract = G.STORE, G.CONTRACT
    G.STORE, G.CONTRACT = store, tmp_path / "absent-contract.json"
    try:
        # When  it runs the first time (no baseline)
        first = G.main(["--baseline", str(baseline), "--issue"])
        # Then  it files the issue, labels it, and writes the baseline
        args = log.read_text()
        check("first run exits 0", first == 0)
        check("first run files an issue", "issue" in args and "create" in args)
        check("issue carries the analysis label", G.LABEL in args)
        check("issue body names the ranked gap", "system_ram_min" in args, args[:200])
        check("baseline written", baseline.exists())

        # And  an unchanged gap set files NOTHING
        log.write_text("")
        second = G.main(["--baseline", str(baseline), "--issue"])
        check("unchanged gap set files no second issue", second == 0 and log.read_text() == "")

        # And  a changed gap set files again, and `--check` turns it into a signal
        store.write_text(json.dumps(store_with([model("m1"), model("m2"), model("m3")])))
        third = G.main(["--baseline", str(baseline), "--check"])
        check("a changed gap set exits 1 under --check", third == 1)
        fourth = G.main(["--baseline", str(baseline)])
        check("report-only runs stay exit 0", fourth == 0)
    finally:
        G.STORE, G.CONTRACT = saved_store, saved_contract
        os.environ["PATH"] = saved_path


def test_write_baseline_records_the_signature_without_filing(tmp_path=None):
    """Issue #174: `--write-baseline` records the CURRENT gap signature as the
    baseline and files NOTHING — the repair for a baseline write lost to a rebase
    or a refresh PR closed before it merged. The file it writes is the contract
    `changed()` reads on the next run, so it must equal `analyse(store)`'s
    signature exactly, and a run against it must then see "unchanged"."""
    if tmp_path is None:
        with tempfile.TemporaryDirectory() as td:
            return _write_baseline_records_the_signature_without_filing(Path(td))
    return _write_baseline_records_the_signature_without_filing(Path(tmp_path))


def _write_baseline_records_the_signature_without_filing(tmp_path):
    # Given a store and an ABSENT baseline
    store = tmp_path / "models.json"
    store.write_text(json.dumps(store_with([model("m1"), model("m2")])))
    baseline = tmp_path / "gap_baseline.json"
    saved_store, saved_contract = G.STORE, G.CONTRACT
    G.STORE, G.CONTRACT = store, tmp_path / "absent-contract.json"
    try:
        # When  `--write-baseline` runs — with NO `gh` on PATH, so a run that
        # tried to file would have raised instead of returning 0
        first = G.main(["--baseline", str(baseline), "--write-baseline",
                        "--out", str(tmp_path / "report.md")])

        # Then  it exits 0 and writes the baseline …
        check("--write-baseline exits 0", first == 0, str(first))
        check("--write-baseline writes the baseline file", baseline.exists())

        # … the written signature IS `analyse(store)` — the contract `changed()` reads …
        expected = G.analyse(G.load(store), G.contract_keys())["signature"]
        written = json.loads(baseline.read_text())["signature"]
        check("the written signature equals analyse(store)", written == expected,
              f"{written[:3]} != {expected[:3]}")

        # … and the next run sees NO change: `--check` is a green no-op against it
        check("a run against the fresh baseline sees no change",
              G.main(["--baseline", str(baseline), "--check",
                      "--out", str(tmp_path / "report2.md")]) == 0)

        # And  it filed nothing: the second run's baseline is still the one it wrote
        check("nothing re-filed or re-written by the check run",
              json.loads(baseline.read_text())["signature"] == written)
    finally:
        G.STORE, G.CONTRACT = saved_store, saved_contract


def test_real_store_dimensions_are_capturable_and_partly_filled():
    """On the REAL store + contracts: every reported dimension is CAPTURABLE end
    to end (declared OPTIONAL, so ingest keeps it instead of pruning it) and the
    backfill that closes the filed gaps is REAL data — at least one model now
    carries a structured value, a free-text mention is still never counted as a
    stored one, and a gap dimension is still ranked.

    The store used to have NO value for any of the five dimensions; asserting
    that emptiness is what this test must not do — it would fail the moment the
    gap actually closes (the point of the analysis)."""

    # Given the real store and the real contracts
    contract = G.contract_keys()
    store = G.load(G.STORE)
    report = G.analyse(store, contract, raw_dir=G.RAW_DIR)
    dims = [d["key"] for d in G.DIMENSIONS]

    # Then  each dimension is CAPTURABLE …
    check("real store: models exist", report["models"] > 0, str(report["models"]))
    for key in dims:
        check(f"real store: {key} is capturable (never a contract gap)",
              key not in report["contract_gaps"], str(report["contract_gaps"]))

    # … the backfill that closes the filed gaps has landed on at least one model …
    filled = [m.get("id") for m in store["models"] if any(m.get(k) for k in dims)]
    check("real store: at least one model carries a structured requirement dimension",
          bool(filled), "no model has any of " + str(dims))

    # … a figure that lives only in free text is still 'missing', never 'stored' …
    check("real store: free text is never counted as a stored value",
          all(set(report["unstructured"][k]) <= set(report["missing"][k]) for k in dims),
          str({k: report["unstructured"][k] for k in dims}))

    # … and the remaining gaps are still ranked and reported
    check("real store: a gap dimension is still ranked",
          bool(G.rank_impact(report)), str(G.rank_impact(report)[:3]))


def test_structured_dimensions_trace_to_a_real_post():
    """Every source-data dimension in the store must trace to a REAL X post.

    A model that carries one of the requirement dimensions must have at least
    one measurement whose `source_post` is a `…/status/<id>` URL: a figure
    without a post behind it is a fabrication, and the backfill measured on the
    store hit exactly this case (two models whose only 'source' was a placeholder
    URL or a profile page — their values were left unset, not invented)."""

    import update_trending as UT  # noqa: E402

    store = G.load(G.STORE)
    dims = [d["key"] for d in G.DIMENSIONS]
    untraceable = [
        f"{m.get('id')}:{k}"
        for m in store["models"] if any(m.get(k) for k in dims)
        for k in dims if m.get(k)
        and not any(UT._is_post_url(str(e.get("source_post", ""))) for e in (m.get("engines") or []))
    ]
    check("every structured dimension traces to a real …/status/<id> post",
          not untraceable, str(untraceable))
    check("and at least one dimension is actually filled (the guard is not vacuous)",
          any(m.get(k) for m in store["models"] for k in dims), "no dimension carries a value")


def test_every_dimension_is_a_declared_optional_key():
    """Every dimension the analysis reports must be CAPTURABLE, or the gap can
    never close: its key is declared in BOTH contracts (the search snapshot and
    the store), OPTIONAL in both (never added to `required` — AGENTS.md §2.3b),
    visible to the analysis, and merged at ingest onto an existing model."""

    # Given both real contracts and the ingest merge list
    mc = json.loads((ROOT / "data" / "model_contract.json").read_text())
    sc = json.loads((ROOT / "data" / "search_contract.json").read_text())
    m_items = mc["properties"]["models"]["items"]
    s_items = sc["properties"]["models"]["items"]
    import update_trending as UT  # noqa: E402  (sys.path already carries scripts/)

    # Then  every reported dimension is representable end to end
    declared = G.contract_keys()
    for dim in G.DIMENSIONS:
        key = dim["key"]
        check(f"{key}: declared in model_contract.json", key in m_items["properties"], str(key))
        check(f"{key}: declared in search_contract.json", key in s_items["properties"], str(key))
        check(f"{key}: OPTIONAL in both contracts (never in required)",
              key not in m_items.get("required", []) and key not in s_items.get("required", []))
        check(f"{key}: the analysis sees it as declared",
              key in declared["model"] or key in declared["measurement"] or key in declared["search_model"])
        check(f"{key}: merged at ingest for an EXISTING model",
              key in UT._ADDITIVE_MODEL_FIELDS, str(UT._ADDITIVE_MODEL_FIELDS))


def test_ingest_merge_list_covers_every_declared_dimension():
    """The ingest merge list and the reported dimensions are one set — a new
    dimension cannot be added to the analysis without ingest support (and a
    declared dimension cannot be reported as unfixable)."""

    import update_trending as UT  # noqa: E402
    check("ingest merge list == reported dimensions",
          set(UT._ADDITIVE_MODEL_FIELDS) == {d["key"] for d in G.DIMENSIONS},
          str(sorted(set(UT._ADDITIVE_MODEL_FIELDS) ^ {d["key"] for d in G.DIMENSIONS})))


def test_analysis_is_wired_to_make_and_the_refresh_pipeline():
    """Rule 6d: the analysis is a make target the refresh pipeline runs — a script
    no target calls is a defect."""

    # Given the Makefile and the refresh pipeline
    makefile = (ROOT / "Makefile").read_text()
    workflow = (ROOT / ".github/workflows/refresh-bot.yml").read_text()

    # Then  the report follows the internal-`_name` + public-wrapper pattern and
    #       runs in the image (it needs no `gh`) …
    for target in ("_data-gaps", "data-gaps", "data-gap-issue", "data-gap-baseline"):
        check(f"Makefile defines {target}", f"{target}:" in makefile)
    check("public target runs the container wrapper", "$(TEST_RUN) make _data-gaps" in makefile)
    check("the script is called from the Makefile", "scripts/data_gap_analysis.py" in makefile)

    # … and the filer's REPAIR half is reachable too (issue #174): `--write-baseline`
    # ran nowhere — no target, no workflow — so the "re-record the baseline without
    # filing" path was dead code (rule 6d) and could not be exercised or tested.
    baseline_t = (makefile.split("data-gap-baseline:", 1)[1].split("\n\n", 1)[0]
                  if "data-gap-baseline:" in makefile else "")
    check("data-gap-baseline records the baseline without filing",
          "python3 scripts/data_gap_analysis.py --write-baseline" in baseline_t, baseline_t)
    check("data-gap-baseline is HOST-side (writes the file as the caller, not as root)",
          "$(TEST_RUN)" not in baseline_t, baseline_t)
    check("no dead internal wrapper target is left behind (rule 6d)",
          "_data-gap-baseline:" not in makefile, "")

    # … and the FILER runs on the HOST, because the test image has no `gh`
    # (measured: the step died with FileNotFoundError: 'gh', issue #150).
    filer = makefile.split("data-gap-issue:", 1)[1].split("\n\n", 1)[0]
    check("filer target does NOT run in the image (no `gh` there)",
          "$(TEST_RUN)" not in filer and "python3 scripts/data_gap_analysis.py --issue" in filer,
          filer)
    check("no dead internal wrapper target is left behind (rule 6d)",
          "_data-gap-issue:" not in makefile, "")
    check("refresh pipeline runs the report", "make data-gaps" in workflow)
    check("refresh pipeline files the issue", "make data-gap-issue" in workflow)
    # The step's own comment promises the filer never blocks the data PR; that
    # promise is only kept with continue-on-error (measured: the job went red and
    # the PR step was skipped, run 38549751388).
    step = workflow.split("- name: File a data-gap issue", 1)[1].split("\n      - name:", 1)[0]
    # The token, corrected by the measurement in #277: the owner PAT declares no
    # Issues scope, so the filing it created carried NO label (the label is what
    # both bots' queues are keyed on) and the step failed silently. Issue writes
    # use the DEFAULT token with `issues: write` — the rule AGENTS.md §6b states.
    check("filer step uses the DEFAULT token (it must be able to write issues)",
          "github.token" in step and "FIXBOT_DISPATCH_TOKEN" not in step, step)
    check("the aggregate job requests `issues: write` for it",
          "issues: write" in workflow.split("- name: File a data-gap issue", 1)[0]
          .rsplit("aggregate:", 1)[-1], step)
    check("the filer step is report-only, as documented",
          "continue-on-error: true" in step, step)

    # Given the baseline the filer writes, derived from the script (not restated)
    baseline_rel = str(G.DEFAULT_BASELINE.relative_to(ROOT))
    check("the filer's baseline path is derived from the script",
          baseline_rel == "data/gap_baseline.json", baseline_rel)

    # When  the commit step that runs right AFTER the filer decides and stages
    commit = workflow.split("- name: Commit + open PR if changed", 1)[1]
    commit_head = commit.split("\n      - name:", 1)[0]

    # Then  its change test AND its git add include the baseline, or the new
    # baseline is discarded and the same gap issue is filed on every run (#152)
    diff_line = [l for l in commit_head.splitlines() if "git diff --quiet" in l]
    add_line = [l for l in commit_head.splitlines() if l.strip().startswith("git add ")]
    check("commit step: the change test includes the baseline",
          bool(diff_line) and baseline_rel in diff_line[0], str(diff_line))
    check("commit step: the baseline is staged",
          bool(add_line) and baseline_rel in add_line[0], str(add_line))

    # Then  the filer runs BEFORE that commit step: the file must exist when the
    # commit decides, and a baseline-only change must not print "No data changes"
    i_filer = workflow.index("run: make data-gap-issue")
    i_commit = workflow.index("- name: Commit + open PR if changed")
    check("ordering: the filer runs before the commit step", i_filer < i_commit,
          f"{i_filer} < {i_commit}")


# A fake `gh` on PATH: `issue list` answers from a store file, `issue create`
# records the signature marker from the body it receives on stdin and appends it
# to that store. The product code (the filer) runs for real; only the CLI is faked.
_GH_STUB = """#!/bin/sh
echo "$@" >> "$FAKE_GH_LOG"
case "$1 $2" in
  "issue list")
    sig=""
    for a in "$@"; do case "$a" in *" in:body") sig="${a% in:body}";; esac; done
    line=$(grep "^${sig}|" "$FAKE_GH_STORE" 2>/dev/null | head -1)
    if [ -n "$line" ]; then
      n=$(printf '%s' "$line" | cut -d'|' -f2)
      st=$(printf '%s' "$line" | cut -d'|' -f3)
      printf '[{"number":%s,"state":"%s","url":"https://example.test/issues/%s"}]\\n' "$n" "$st" "$n"
    else
      printf '[]\\n'
    fi ;;
  "issue create")
    body=$(cat)
    sig=$(printf '%s' "$body" | sed -n 's/.*data-gap-signature: \\([0-9a-f]*\\).*/\\1/p' | head -1)
    n=$(grep -c . "$FAKE_GH_STORE" 2>/dev/null || true)
    n=$(( ${n:-0} + 1 ))
    printf '%s|%s|OPEN\n' "$sig" "$n" >> "$FAKE_GH_STORE"
    printf 'https://example.test/issues/%s\n' "$n" ;;
  "issue view")
    printf '{"labels":[{"name":"data-gap-analysis"}]}\n' ;;
  "label list")
    # The repo already carries the label (issue #277: the filer checks before it
    # relies on it, and creates it when it is missing).
    printf '[{"name":"data-gap-analysis"}]\n' ;;
esac
exit 0
"""


def _run_filer(baseline_text, td):
    """Run `--issue` once with a stale baseline (a fresh checkout of master)."""
    baseline = td / "baseline.json"
    baseline.write_text(baseline_text)
    env = {**os.environ, "PATH": f"{td}{os.pathsep}{os.environ['PATH']}",
           "FAKE_GH_LOG": str(td / "gh.log"), "FAKE_GH_STORE": str(td / "issues.txt")}
    return subprocess.run(
        [sys.executable, "scripts/data_gap_analysis.py", "--issue", "--baseline", str(baseline)],
        cwd=ROOT, capture_output=True, text=True, env=env)


def test_a_gap_set_is_filed_once():
    """Issue #157: the baseline reaches master only through the refresh PR, so two
    runs before that merge see the same change. The second must file nothing."""
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        stub = td / "gh"
        stub.write_text(_GH_STUB)
        stub.chmod(0o755)
        (td / "gh.log").write_text("")
        (td / "issues.txt").write_text("")
        # A baseline whose signature differs from the store's = the stale master
        # state while the previous run's PR is still open.
        stale = json.dumps({"as_of": "2026-01-01T00:00:00Z", "signature": ["stale"]})

        # Given a refresh run that sees a changed gap set
        first = _run_filer(stale, td)

        # Then  it files exactly one issue, carrying the signature marker
        creates = [l for l in (td / "gh.log").read_text().splitlines() if l.startswith("issue create")]
        check("first run: files one issue", len(creates) == 1, str(creates))
        filed_sig = (td / "issues.txt").read_text().strip().split("|")[0]
        check("first run: the body carries the signature marker",
              len(filed_sig) == 12 and all(c in "0123456789abcdef" for c in filed_sig),
              (td / "issues.txt").read_text()[:80])
        # …and the baseline FILE is updated to this run's signature (the message
        # for that is only printed for the explicit `--write-baseline` flag)
        baseline_sig = json.loads((td / "baseline.json").read_text())["signature"]
        check("first run: the baseline is written",
              baseline_sig != ["stale"] and len(baseline_sig) > 1, str(baseline_sig)[:80])

        # When  the next run starts from master again (the baseline in the repo is
        # still the old one, because the first run's PR is not merged yet)
        second = _run_filer(stale, td)

        # Then  it recognises the gap set and files NO duplicate
        creates = [l for l in (td / "gh.log").read_text().splitlines() if l.startswith("issue create")]
        check("second run: no duplicate issue", len(creates) == 1, str(creates))
        check("second run: it says the gap set is already filed",
              "already filed" in second.stderr, second.stderr)

        # Given the previous issue was CLOSED (the work was done or dropped)
        store = (td / "issues.txt").read_text().replace("|OPEN", "|CLOSED")
        (td / "issues.txt").write_text(store)

        # When  the gap set is seen again
        third = _run_filer(stale, td)

        # Then  a closed issue does not block the new work
        creates = [l for l in (td / "gh.log").read_text().splitlines() if l.startswith("issue create")]
        check("third run: a CLOSED issue does not suppress a new one", len(creates) == 2, str(creates))
        check("third run: it files again", "filed https://example.test" in third.stderr, third.stderr)


# The same fake `gh`, extended for issue #161: `issue create` can silently DROP
# the label (measured in CI), `issue view` reports what the store holds, and
# `issue edit --add-label` can be made to fail as well.
_GH_STUB_LABELS = """#!/bin/sh
echo "$@" >> "$FAKE_GH_LOG"
case "$1 $2" in
  "issue list")
    sig=""
    for a in "$@"; do case "$a" in *" in:body") sig="${a% in:body}";; esac; done
    line=$(grep "^${sig}|" "$FAKE_GH_STORE" 2>/dev/null | head -1)
    if [ -n "$line" ]; then
      n=$(printf '%s' "$line" | cut -d'|' -f2)
      st=$(printf '%s' "$line" | cut -d'|' -f3)
      printf '[{"number":%s,"state":"%s","url":"https://example.test/issues/%s"}]\\n' "$n" "$st" "$n"
    else
      printf '[]\\n'
    fi ;;
  "issue create")
    body=$(cat)
    sig=$(printf '%s' "$body" | sed -n 's/.*data-gap-signature: \\([0-9a-f]*\\).*/\\1/p' | head -1)
    n=$(grep -c . "$FAKE_GH_STORE" 2>/dev/null || true)
    n=$(( ${n:-0} + 1 ))
    labels=""
    [ "${FAKE_GH_DROP_LABEL:-0}" = "1" ] || labels="data-gap-analysis"
    printf '%s|%s|OPEN|%s\\n' "$sig" "$n" "$labels" >> "$FAKE_GH_STORE"
    printf 'https://example.test/issues/%s\\n' "$n" ;;
  "issue view")
    line=$(cut -d'|' -f2,4 "$FAKE_GH_STORE" | grep "^${3}|" | head -1)
    labels=$(printf '%s' "$line" | cut -d'|' -f2)
    if [ -n "$labels" ]; then
      printf '{"labels":[{"name":"%s"}]}\\n' "$labels"
    else
      printf '{"labels":[]}\\n'
    fi ;;
  "issue edit")
    if [ "${FAKE_GH_EDIT_LABEL_FAILS:-0}" = "1" ]; then
      echo "could not add label: 'data-gap-analysis' not found" >&2
      exit 1
    fi
    n=""
    for a in "$@"; do case "$a" in [0-9]*) [ -z "$n" ] && n="$a";; esac; done
    awk -F'|' -v n="$n" 'BEGIN{OFS="|"} $2==n {$4="data-gap-analysis"} 1' \\
      "$FAKE_GH_STORE" > "$FAKE_GH_STORE.tmp" && mv "$FAKE_GH_STORE.tmp" "$FAKE_GH_STORE" ;;
  "label list")
    # The repo's label set is a FILE the test creates (or does not): a missing
    # label is exactly what GitHub silently ignores on `issue create`.
    if [ -f "$FAKE_GH_LABEL_FLAG" ]; then
      printf '[{"name":"data-gap-analysis"}]\\n'
    else
      printf '[]\\n'
    fi ;;
  "label create")
    # The repo gains the label — unless creating it is refused too.
    if [ "${FAKE_GH_LABEL_CREATE_FAILS:-0}" = "1" ]; then
      echo "HTTP 403: Resource not accessible by personal access token" >&2
      exit 1
    fi
    : > "$FAKE_GH_LABEL_FLAG" ;;
esac
exit 0
"""


def _run_filer_env(baseline_text, td, extra_env=None, label_exists=True):
    baseline = td / "baseline.json"
    baseline.write_text(baseline_text)
    label_flag = td / "label-exists"
    # Default: the repo already carries the label. With `label_exists=False` the
    # run starts WITHOUT it, and the stub writes the flag when it is asked to
    # create one — so a missing label is a case the test can set up, not an
    # accident of the environment.
    label_flag.unlink(missing_ok=True)
    if label_exists:
        label_flag.touch()
    env = {**os.environ, "PATH": f"{td}{os.pathsep}{os.environ['PATH']}",
           "FAKE_GH_LOG": str(td / "gh.log"), "FAKE_GH_STORE": str(td / "issues.txt"),
           "FAKE_GH_LABEL_FLAG": str(label_flag), **(extra_env or {})}
    return subprocess.run(
        [sys.executable, "scripts/data_gap_analysis.py", "--issue", "--baseline", str(baseline)],
        cwd=ROOT, capture_output=True, text=True, env=env)


def test_a_filed_issue_carries_the_label_the_bots_trigger_on():
    """Issue #161: the CLI created the issue with NO label while returning 0, and
    the label is exactly what issue-bot / its sweep key on — an unlabelled filing
    is invisible to both. The filer must verify, repair, or fail."""
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        stub = td / "gh"
        stub.write_text(_GH_STUB_LABELS)
        stub.chmod(0o755)
        (td / "gh.log").write_text("")
        (td / "issues.txt").write_text("")
        stale = json.dumps({"as_of": "2026-01-01T00:00:00Z", "signature": ["stale"]})

        # Given a create that returns 0 but applies no label
        dropped = _run_filer_env(stale, td, {"FAKE_GH_DROP_LABEL": "1"})

        # Then  the filed issue carries the label (re-applied), and it is a success
        check("label dropped: the run still exits 0", dropped.returncode == 0, dropped.stderr)
        check("label dropped: the issue ends up labelled",
              "data-gap-analysis" in (td / "issues.txt").read_text().splitlines()[0],
              (td / "issues.txt").read_text()[:80])
        check("label dropped: it re-applied the label with gh issue edit",
              any(l.startswith("issue edit") for l in (td / "gh.log").read_text().splitlines()),
              (td / "gh.log").read_text())

        # Given a create that drops the label AND an edit that cannot apply it
        (td / "issues.txt").write_text("")
        (td / "gh.log").write_text("")
        broken = _run_filer_env(stale, td, {"FAKE_GH_DROP_LABEL": "1",
                                            "FAKE_GH_EDIT_LABEL_FAILS": "1"})

        # Then  the filer FAILS LOUDLY instead of reporting an invisible filing
        check("label unappliable: the run fails", broken.returncode != 0, broken.stderr)
        check("label unappliable: it names the label and why it matters",
              "does not carry" in broken.stderr and "data-gap-analysis" in broken.stderr,
              broken.stderr)
        # …and it carries `gh`'s OWN words: the conclusion alone ("the label did
        # not stick") named no cause and no fix, which is what made the measured
        # failure (#277) unactionable.
        check("label unappliable: gh's own message reaches the operator",
              "not found" in broken.stderr, broken.stderr)


def test_the_filer_creates_the_label_the_bots_trigger_on():
    """Issue #277: GitHub IGNORES a label the repo does not have, so a filing made
    before `data-gap-analysis` exists lands UNLABELLED while `gh issue create`
    returns 0 — and `gh issue edit --add-label` then refuses it. The measured
    consequence on master: `make issue-queue` -> `candidates=0` and
    `make review-issue-pick` -> `action=none`, so the implementer's and the
    reviewer's jobs were SKIPPED every run while the pipeline stayed green. The
    filer must create the label rather than file into the void."""
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        stub = td / "gh"
        stub.write_text(_GH_STUB_LABELS)
        stub.chmod(0o755)
        (td / "gh.log").write_text("")
        (td / "issues.txt").write_text("")
        stale = json.dumps({"as_of": "2026-01-01T00:00:00Z", "signature": ["stale"]})

        # Given a repo that does NOT carry the label, and a create that drops it
        created = _run_filer_env(stale, td, {"FAKE_GH_DROP_LABEL": "1"}, label_exists=False)

        # Then  the label is created first, and the issue ends up carrying it
        calls = (td / "gh.log").read_text()
        check("label missing: the filer creates it", "label create" in calls, calls)
        check("label missing: the label now exists in the repo", (td / "label-exists").exists(), "")
        check("label missing: the run exits 0", created.returncode == 0, created.stderr)
        check("label missing: the filing is visible to both bots",
              "data-gap-analysis" in (td / "issues.txt").read_text().splitlines()[0],
              (td / "issues.txt").read_text()[:80])

        # Given the label cannot be created either
        (td / "issues.txt").write_text("")
        (td / "gh.log").write_text("")
        refused = _run_filer_env(stale, td, {"FAKE_GH_DROP_LABEL": "1",
                                             "FAKE_GH_LABEL_CREATE_FAILS": "1"},
                                 label_exists=False)

        # Then  the run fails loudly, naming gh's own refusal
        check("label uncreatable: the run fails", refused.returncode != 0, refused.stderr)
        check("label uncreatable: gh's refusal is quoted",
              "Resource not accessible" in refused.stderr, refused.stderr)


# ---- the backfill that closes the filed `engine_min_version` gap (issue #163) --
#
# A structured requirement dimension is only ever the SOURCE POST's own
# statement. The post is captured in data/raw/*.json, so the evidence for a
# value is the model's captured text there: a value whose version-like tokens
# (and at least one distinctive token) do not appear in it has no post behind it
# and is a fabrication — the one failure this stage must never make.

def _captured_text(store_models: set[str] | None = None) -> dict[str, str]:
    """Per model id, the free text the search captured in data/raw/*.json (the
    record of the real `…/status/<id>` post): the model's own prose plus every
    measurement's `quant` / `hardware`."""
    out: dict[str, list[str]] = {}
    for f in sorted(G.RAW_DIR.glob("*.json")):
        d = G.load(f, {}) or {}
        for m in d.get("models", []):
            mid = m.get("id")
            if not mid or (store_models is not None and mid not in store_models):
                continue
            parts = [m[k] for k in ("quant", "hardware", "why") if isinstance(m.get(k), str)]
            for e in m.get("engines", []) or []:
                parts += [e[k] for k in ("quant", "hardware") if isinstance(e.get(k), str)]
            out.setdefault(mid, []).append(" ".join(parts))
    return {k: " ".join(v) for k, v in out.items()}


def _engine_min_version_is_evidenced(value: str, captured: str) -> bool:
    """True when the captured source text supports the value: every version-like
    token of it appears in the text, and at least one distinctive token does."""
    hay = captured.lower()
    tokens = [t for t in re.split(r"[^A-Za-z0-9.]+", value or "") if len(t) >= 4]
    if not tokens or not any(t.lower() in hay for t in tokens):
        return False
    versioned = [t for t in tokens if re.search(r"\d+\.\d+", t) or re.fullmatch(r"b\d{3,}", t)]
    return all(t.lower() in hay for t in versioned)


def test_engine_min_version_backfill_traces_to_the_captured_source_text():
    """Issue #163's top-ranked gap closes with REAL data only: every structured
    `engine_min_version` in the store must be the source post's own statement of
    the build / required flags, i.e. its wording is present in the text the
    search captured for that model (`data/raw/*.json`) — and the post it came
    from is a real `…/status/<id>` URL."""

    import update_trending as UT  # noqa: E402

    store = G.load(G.STORE)
    captured = _captured_text()
    carried = [m for m in store["models"] if m.get("engine_min_version")]

    # Then  the guard is not vacuous …
    check("engine_min_version: at least one model carries a structured value",
          bool(carried), "no model carries engine_min_version")

    # … every value is evidenced by the captured text of a real post …
    unevidenced = [m.get("id") for m in carried
                   if not _engine_min_version_is_evidenced(m["engine_min_version"],
                                                           captured.get(m.get("id"), ""))]
    check("engine_min_version: every value is present in the model's captured source text",
          not unevidenced, str(unevidenced))

    # … and each such model has a real `…/status/<id>` post behind it
    untraceable = [m.get("id") for m in carried
                   if not any(UT._is_post_url(str(e.get("source_post", "")))
                              for e in (m.get("engines") or []))]
    check("engine_min_version: every value traces to a real …/status/<id> post",
          not untraceable, str(untraceable))

    # And  an invented value — one no captured snapshot mentions — is refused
    check("engine_min_version: an unsupported value fails the evidence rule",
          not _engine_min_version_is_evidenced("llama.cpp b999999, --invented-flag 7.7.7",
                                               captured.get(carried[0].get("id"), "")))


def test_engine_min_version_coverage_can_never_shrink():
    """The closed gap must not silently reopen. The dimension is carried by a
    floor of models, and the analysis reports fewer models missing it than the
    29/30 the filed issue (#163) recorded."""

    store = G.load(G.STORE)
    report = G.analyse(store, G.contract_keys(), raw_dir=G.RAW_DIR)
    n = sum(1 for m in store["models"] if m.get("engine_min_version"))
    missing = len(report["missing"]["engine_min_version"])

    check("engine_min_version: coverage floor holds (>= 25 models)",
          n >= 25, f"{n} models carry it")
    check("engine_min_version: fewer models are missing it than the filed issue's 29/30",
          missing < 29, f"{missing} still missing")


# A storage-offload value names a storage MEDIUM and (usually) a size. The value
# is only real when the model's captured source text says both.
_STORAGE_MEDIA = ("ssd", "nvme", "flash", "disk", "hdd")
_STORAGE_SIZE_RX = re.compile(r"\d+(?:\.\d+)?\s*(?:gb|mb|tb)", re.I)


def _storage_offload_is_evidenced(value: str, captured: str) -> bool:
    """True when the captured source text supports a `storage_offload` value:
    the value names a storage medium, the captured text names one too, every size
    token of the value appears in the text, and at least one distinctive token
    does. An invented offload ('8TB tape library') has no medium and is refused."""
    hay = (captured or "").lower()
    low = (value or "").lower()
    if not (any(med in low for med in _STORAGE_MEDIA) and any(med in hay for med in _STORAGE_MEDIA)):
        return False
    if any(s.lower() not in hay for s in _STORAGE_SIZE_RX.findall(low)):
        return False
    tokens = [t for t in re.split(r"[^A-Za-z0-9]+", low) if len(t) >= 4]
    return bool(tokens) and any(t in hay for t in tokens)


def test_storage_offload_backfill_traces_to_the_captured_source_text():
    """Issue #364's top-ranked gap closes with REAL data only: every structured
    `storage_offload` in the store must be the source post's own statement of the
    offload, i.e. its storage medium and every size token are present in the text
    the search captured for that model (`data/raw/*.json`) — and the post it came
    from is a real `…/status/<id>` URL."""

    import update_trending as UT  # noqa: E402

    store = G.load(G.STORE)
    captured = _captured_text()
    carried = [m for m in store["models"] if m.get("storage_offload")]

    # Then  the guard is not vacuous …
    check("storage_offload: at least one model carries a structured value",
          bool(carried), "no model carries storage_offload")

    # … every value is evidenced by the captured text of a real post …
    unevidenced = [m.get("id") for m in carried
                   if not _storage_offload_is_evidenced(m["storage_offload"],
                                                        captured.get(m.get("id"), ""))]
    check("storage_offload: every value is present in the model's captured source text",
          not unevidenced, str(unevidenced))

    # … and each such model has a real `…/status/<id>` post behind it
    untraceable = [m.get("id") for m in carried
                   if not any(UT._is_post_url(str(e.get("source_post", "")))
                              for e in (m.get("engines") or []))]
    check("storage_offload: every value traces to a real …/status/<id> post",
          not untraceable, str(untraceable))

    # And  an invented value — one no captured snapshot mentions — is refused
    check("storage_offload: an unsupported value fails the evidence rule",
          not _storage_offload_is_evidenced("8TB tape library, experts streamed",
                                            captured.get(carried[0].get("id"), "")),
          "a value naming no captured storage medium was accepted")


def test_storage_offload_coverage_can_never_shrink():
    """The closed gap must not silently reopen. The dimension is carried by a
    floor of models, and the analysis reports fewer models missing it than the
    41/49 the filed issue (#364) recorded."""

    store = G.load(G.STORE)
    report = G.analyse(store, G.contract_keys(), raw_dir=G.RAW_DIR)
    n = sum(1 for m in store["models"] if m.get("storage_offload"))
    missing = len(report["missing"]["storage_offload"])

    check("storage_offload: coverage floor holds (>= 9 models)",
          n >= 9, f"{n} models carry it")
    check("storage_offload: fewer models are missing it than the filed issue's 41/49",
          missing < 41, f"{missing} still missing")


def main() -> int:
    print("data-gap analysis: unit tests")
    test_contract_gap_vs_stored_dimension()
    test_free_text_mention_is_unstructured_not_present()
    test_signature_tracks_the_store_not_the_noise()
    with tempfile.TemporaryDirectory() as td:
        test_one_issue_per_changed_gap_set(Path(td))
    with tempfile.TemporaryDirectory() as td:
        test_write_baseline_records_the_signature_without_filing(Path(td))
    test_real_store_dimensions_are_capturable_and_partly_filled()
    test_structured_dimensions_trace_to_a_real_post()
    test_every_dimension_is_a_declared_optional_key()
    test_ingest_merge_list_covers_every_declared_dimension()
    test_analysis_is_wired_to_make_and_the_refresh_pipeline()
    test_a_gap_set_is_filed_once()
    test_a_filed_issue_carries_the_label_the_bots_trigger_on()
    test_the_filer_creates_the_label_the_bots_trigger_on()
    test_engine_min_version_backfill_traces_to_the_captured_source_text()
    test_engine_min_version_coverage_can_never_shrink()
    test_storage_offload_backfill_traces_to_the_captured_source_text()
    test_storage_offload_coverage_can_never_shrink()
    print(f"\nPASSED {_PASS} | FAILED {_FAIL}")
    return 1 if _FAIL else 0


if __name__ == "__main__":
    raise SystemExit(main())
