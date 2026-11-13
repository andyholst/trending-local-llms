#!/usr/bin/env python3
"""Issue #858 — the starved-CPU-query class: a leg whose queries ANSWER and capture nothing.

The CPU search leg went green on its newest refreshes (2026-11-11: seven per-query
snapshots, ZERO models captured, while the same runs' other legs captured 16) after
capturing plenty all through October: its queries answered HTTP 200 with hundreds of
posts and no CPU figure among them, because every existing check (search-smoke,
engine-check, validate-fetch, query-coverage) stopped at HTTP status and nothing read
the WORDS. This suite locks the three halves of the fix (rule 6o):

  1. ONE home: scripts/query_vocab.py defines each leg's curated vocabulary;
     the Makefile prompt indirection `$(CPU_KEYWORDS)` RESOLVES to it, the
     smoke imports it, and the CPU fetch sampling IS it. A drifted copy is red.
  2. The yield gate: drive the REAL smoke_search main() over the CPU leg —
     answered pages that state no rate and name no model exit 2 naming the
     vocabulary; a leg that yields stays green; an all-timeout leg is still
     judged by the #258 budget rule, not double-charged.
  3. The measured vocabulary: the probe-verified co-occurrence queries are
     present, every query honours the `make query-coverage` token contract, the
     append-only raw store shows the starved-CPU/asymmetry evidence, and posts
     captured VERBATIM from the live mirror on 2026-11-13 DO yield candidates
     under the new queries' own regexes — proving the fix is grounded in real
     posts, not prose.

Run standalone: python3 tests/test_cpu_query_vocabulary.py
"""
import contextlib
import io
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import query_vocab  # noqa: E402  (the ONE home)
from update_trending import SEARCH_GROUPS  # noqa: E402

MAKEFILE = ROOT / "Makefile"
SMOKE = ROOT / "scripts" / "smoke_search.py"
RAW_DIR = ROOT / "data" / "raw"

_PASS = 0
_FAIL = 0


def check(name: str, cond: bool, detail: str = ""):
    global _PASS, _FAIL
    if cond:
        _PASS += 1
        print(f"  ok  {name}")
    else:
        _FAIL += 1
        print(f"  FAIL {name} {detail}")


def _load_smoke() -> dict:
    ns: dict = {"__file__": str(SMOKE)}  # smoke imports query_vocab via __file__'s dir
    exec(compile(SMOKE.read_text(), str(SMOKE), "exec"), ns)
    return ns


# ---------------------------------------------------------------- half 1: one home

def test_one_home_every_reader_resolves_to_it():
    """The Makefile prompt carries `($(CPU_KEYWORDS))` pointing at scripts/query_vocab.py;
    resolving the indirection for real must equal the home, and so must the smoke list."""
    text = MAKEFILE.read_text()
    for leg in query_vocab.LEGS:
        var = f"{leg.upper()}_KEYWORDS"
        m = re.search(rf"^{var} = \$\(shell python3 scripts/query_vocab\.py --print {leg}\b",
                      text, re.M)
        check(f"home: Makefile defines {var} from scripts/query_vocab.py --print {leg}",
              bool(m), "no $(shell query_vocab) definition")
        body = text[text.index(f"_search-{leg}:\n"):]
        body = body.split("\n.PHONY", 1)[0]
        m = re.search(r"keywords=\(\$\((\w+)\)\)", body)
        check(f"home: `_search-{leg}` passes keywords through $({var}), not a hand copy",
              bool(m) and m.group(1) == var, body[:200])
        resolved = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "query_vocab.py"), "--print", leg],
            capture_output=True, text=True, check=True).stdout.strip()
        check(f"home: `query_vocab.py --print {leg}` resolves to the reviewed list",
              [k.strip() for k in resolved.split(",")] == query_vocab.curated(leg))

    smoke = _load_smoke()
    for leg in query_vocab.LEGS:
        check(f"home: smoke_search's {leg} list IS query_vocab's (no private copy)",
              smoke["BACKEND_KEYWORDS"][leg] == query_vocab.curated(leg))

    check("home: the CPU fetch sampling in update_trending IS the leg vocabulary",
          SEARCH_GROUPS["CPU"] == query_vocab.curated("cpu"),
          f"got {SEARCH_GROUPS['CPU']}")


# ---------------------------------------------------------------- half 2: the yield gate

def test_the_yield_gate_refuses_a_silent_leg(S: dict):
    """Drive the REAL main() over the CPU leg: every query answers 200 with posts,
    no page states a rate or names a model — the exact #858 shape — so the run
    must go red AND name the vocabulary as the cause (not a dead mirror)."""
    import inspect
    if "probe_fn" not in inspect.signature(S["main"]).parameters:
        check("gate: main() exposes the probe seam", False, "no probe_fn parameter")
        return
    silent = {"label": "OK", "status": 200, "ok": True, "upstream": 200, "elapsed": 0.5,
              "attempts": 1, "rate_hits": 0, "model_hits": 0}

    def probe_fn(*_a, **_kw):
        return dict(silent)

    out = io.StringIO()
    argv = sys.argv
    sys.argv = ["smoke_search.py", "--backend", "cpu", "--key", "test"]
    try:
        with contextlib.redirect_stdout(out):
            rc = S["main"](probe_fn=probe_fn)
        text = out.getvalue()
        check("gate: a fully-SILENT answered CPU leg exits 2 (green-with-zero-capture is the defect)",
              rc == 2, f"rc={rc}")
        check("gate: the refusal names the vocabulary and where to fix it",
              "starved curated vocabulary" in text and "query_vocab.py" in text, text[-400:])
        check("gate: each query is labelled SILENT in the run, not just the verdict",
              "SILENT" in text, text[-200:])

        # And a leg that YIELDS stays green: the same leg, candidates on every page.
        yielding = dict(silent, rate_hits=1, model_hits=2)

        def probe_fn2(*_a, **_kw):
            return dict(yielding)

        out2 = io.StringIO()
        with contextlib.redirect_stdout(out2):
            rc2 = S["main"](probe_fn=probe_fn2)
        check("gate: a yielding CPU leg stays green (the gate is about CONTENT, not budget)",
              rc2 == 0, f"rc={rc2}")
        check("gate: yielding queries are labelled with their yield counts",
              "rate-posts" in out2.getvalue(), out2.getvalue()[-200:])

        # And a SILENT leg that timed out (answered=0) is judged by the #258 budget rule,
        # not double-charged as a vocabulary failure.
        def probe_fn3(*_a, **_kw):
            return {"label": "TIMEOUT", "status": 0, "ok": None, "upstream": None,
                    "elapsed": 3.0, "attempts": 2}

        out3 = io.StringIO()
        with contextlib.redirect_stdout(out3):
            rc3 = S["main"](probe_fn=probe_fn3)
        check("gate: an all-TIMEOUT leg still fails via the MAJORITY rule, without the starved label",
              rc3 == 2 and "starved" not in out3.getvalue(), out3.getvalue()[-300:])
    finally:
        sys.argv = argv


# ---------------------------------------------------------------- half 3: the measured vocabulary

def test_the_vocabulary_is_the_audited_one():
    cpu = query_vocab.curated("cpu")
    # Probe-verified on the live mirror (2026-11-13): these two queries returned
    # real posts stating CPU rates (see LIVE_VERIFIED_POSTS below). Losing them is a defect.
    check("vocab: carries the probe-verified co-occurrence queries",
          "cpu tokens per second" in cpu and "no gpu tokens per second" in cpu, str(cpu))
    check("vocab: still asks the engine and the edge device",
          "llama.cpp cpu tokens per second" in cpu and "raspberry pi tokens per second" in cpu,
          str(cpu))
    check("vocab: no query names a GPU except the explicit no-gpu one",
          all("gpu" in q for q in cpu if "gpu" in q), str(cpu))
    # `make query-coverage`'s token contract: model-id keys and dimension tokens
    # substring-match the curated queries; every query asks for a rate.
    check("vocab: every query asks for a rate in the contract's tokens",
          all(("tokens per second" in q or "tokens/s" in q) for q in cpu), str(cpu))
    check("vocab: the leg has at least three queries (one query cannot audit a leg)",
          len(cpu) >= 3, str(cpu))


def test_the_starved_run_is_recorded_in_the_store():
    """Evidence from the append-only raw store: the CPU leg HAS captured (October
    refreshes captured up to 44 models), and its newest runs answered and captured
    NOTHING — while the same refresh's other legs did capture. That asymmetry is
    the vocabulary defect #858 files; it is never re-written away, so this check
    stays green forever as the record."""
    groups: dict[str, int] = {}
    counts: dict[str, int] = {}
    for path in sorted(RAW_DIR.glob("cpu-*.json")):
        m = re.search(r"cpu-(\d{8})-", path.name)
        if not m:
            continue
        groups.setdefault(m.group(1), 0)
        groups[m.group(1)] += 1
        try:
            counts[m.group(1)] = counts.get(m.group(1), 0) + len(
                json.loads(path.read_text()).get("models", []))
        except (json.JSONDecodeError, OSError):
            pass
    starved_dates = sorted(d for d, n in groups.items() if counts.get(d, 0) == 0)
    check("store: the tree carries a whole refresh whose CPU leg captured zero models "
          "(the #858 evidence lives in data/raw, not in prose)", bool(starved_dates),
          str(sorted(groups.items())))
    # ...while the other legs of at least one of those same refreshes DID capture:
    # the mirror was up; the CPU queries were the starved ones.
    asymmetry = False
    for date in starved_dates:
        other = 0
        for path in RAW_DIR.glob(f"*-{date}-*.json"):
            try:
                other += len(json.loads(path.read_text()).get("models", []))
            except (json.JSONDecodeError, OSError):
                pass
        if other > 0:
            asymmetry = True
            break
    check("store: on a starved-CPU refresh the other legs captured models (leg defect, not outage)",
          asymmetry, "every leg captured nothing on the empty-CPU dates")


# Captured VERBATIM from the live mirror on 2026-11-13 by the issue's audit probe
# (lightbrd.com search pages for the new queries); these are real posts, quoted
# exactly as the page rendered them, with the status URL each came from.
LIVE_VERIFIED_POSTS = [
    # https://lightbrd.com/GpaAndy/status/2121056677302866236 — surfaced by the
    # `no gpu tokens per second` query the old vocabulary did not ask:
    "Their latest experiments also show Qwen3.5-9B running on Android phones at "
    "up to 9.3 generated tokens per second.\nNo massive GPU cluster required for "
    "every small inference task.",
    # https://lightbrd.com/Oluwaphilemon1/status/2121053447734579580 — surfaced by
    # the `cpu tokens per second` query, a hybrid CPU-offload llama.cpp run:
    "A 12GB RTX 3060 is reportedly running Qwen3.8-35B-A3B at around 50 tokens "
    "per second, with prompt processing reaching approximately 550 tok/s.\n"
    "CPU offloading: 26 MoE layers",
]


def test_the_new_queries_would_have_yielded_the_live_posts(S: dict):
    """Grounding check: run the REAL yield regexes (page_yields) over the posts the
    live audit PROVED the new queries surface. If the fix cannot catch a real CPU
    rate post, the vocabulary did not actually fix anything."""
    py = S["page_yields"]
    caught = [py(p) for p in LIVE_VERIFIED_POSTS]
    check("grounding: posts stating a CPU rate DO yield candidates for the new queries",
          all(r > 0 or m > 0 for r, m in caught), str(caught))
    # The Acurast post is the exact capture class the old AND-style queries missed:
    # it names a model AND a rate AND no GPU.
    r, m = py(LIVE_VERIFIED_POSTS[0])
    check("grounding: the no-gpu model+rate post yields BOTH a rate and a model candidate",
          r > 0 and m > 0, f"rate={r} model={m}")


def main() -> int:
    print("cpu_query_vocabulary: one home for the curated vocabulary (issue #858)")
    test_one_home_every_reader_resolves_to_it()
    S = _load_smoke()
    print("cpu_query_vocabulary: the yield gate over the CPU leg")
    test_the_yield_gate_refuses_a_silent_leg(S)
    print("cpu_query_vocabulary: the audited vocabulary")
    test_the_vocabulary_is_the_audited_one()
    test_the_starved_run_is_recorded_in_the_store()
    test_the_new_queries_would_have_yielded_the_live_posts(S)
    print(f"\n{ _PASS } passed, {_FAIL} failed")
    return 1 if _FAIL else 0


if __name__ == "__main__":
    raise SystemExit(main())
