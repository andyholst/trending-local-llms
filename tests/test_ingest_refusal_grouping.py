"""Issue #882 — re-captured posts repeat across search legs; ingest must report
each refusal ONCE per (rule, model, engine, post) per run, not once per snapshot.

The refusals themselves, their ledger records and the per-file ledger summaries
are unchanged; only the per-snapshot `[ingest] REFUSED` log line dedupes. Every
test here drives the REAL `ingest_raw_snapshots` (rule 6m): fixture snapshots go
through the merge in a subprocess whose TRENDING_DATA_DIR points at a scratch
copy of the data dir — the same seam `test_cross_model_attribution.py` uses.
"""
import io
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path
from contextlib import redirect_stdout

ROOT = Path(__file__).resolve().parent.parent
_PASS = 0
_FAIL = 0


def check(name, ok, detail=""):
    global _PASS, _FAIL
    if ok:
        _PASS += 1
        print(f"  ok  {name}")
    else:
        _FAIL += 1
        print(f"  FAIL {name}: {detail}")
    return ok


SEAM_LINE = re.compile(
    r"\[ingest\] REFUSED (fabricated engine|misattributed measurement|"
    r"cross-model duplicate measurement|weight-gb contradiction) '(?P<engine>.*?)' on "
    r"(?P<mid>[^:]+): .*post (?P<post>https?://\S+)"
)


def _run_ingest(script_body: str, tmp: Path) -> tuple[subprocess.CompletedProcess, str]:
    """Run a scratch-data ingest subprocess and return (proc, combined stdout)."""
    shutil.rmtree(tmp, ignore_errors=True)
    tmp.mkdir(parents=True, exist_ok=True)
    script = (
        "import json, os, shutil, sys\n"
        "from pathlib import Path\n"
        "ROOT = Path(sys.argv[1]); tmp = Path(sys.argv[2])\n"
        "for name in ('models.json', 'measurements.json', 'posts.json'):\n"
        "    shutil.copy(ROOT / 'data' / name, tmp / name)\n"
        "(tmp / 'raw').mkdir(parents=True, exist_ok=True)\n"
        "os.environ['TRENDING_DATA_DIR'] = str(tmp)\n"
        "sys.path.insert(0, str(ROOT / 'scripts'))\n"
        "import update_trending as ut\n"
        "store = ut.load_store()\n"
        + script_body
    )
    buf = io.StringIO()
    with redirect_stdout(buf):
        r = subprocess.run([sys.executable, "-c", script, str(ROOT), str(tmp)],
                           capture_output=True, text=True, timeout=300)
    return r, buf.getvalue() + r.stdout + r.stderr


COPY_ROW = {
    "id": "gemma-3-1b", "name": "Gemma 3 1B Instruct",
    "hf": "google/gemma-3-1b-it", "formats": [{"format": "MLX"}],
    "engines": [{
        "engine": "MLX", "tps": "18", "hardware": "Apple M5 Pro Mac mini, 64GB unified memory",
        "quant": "MLX build", "date": "2026-10-10",
        "source_post": "https://lightbrd.com/pratikg/status/2108994425166967019",
        "likes": 9, "comments": 6, "reshares": 226, "views": 38759,
    }],
}
COPY_POST = COPY_ROW["engines"][0]["source_post"]


def test_a_post_refused_by_every_leg_prints_one_grouped_line():
    # The #882 shape verbatim: the SAME post is captured by an amd, a cpu and a
    # nvidia leg. Each re-merge used to print the identical refusal three times;
    # the run must now print ONE grouped line naming how often it was seen.
    tmp = ROOT / "tmp-882-group-e2e"
    row = json.dumps(COPY_ROW)
    files = "\n".join(
        f"(tmp / 'raw' / '{name}.json').write_text(json.dumps("
        f'{{"generated_utc": "2026-11-0{T}_T23:00:00Z", "backend": "{T}", '
        f'"models": [{row}]}}))'
        for name, T in (("amd-re", "amd"), ("cpu-re", "cpu"), ("nvidia-re", "nvidia"))
    ) + "\n"
    body = files + (
        "added, updated = ut.ingest_raw_snapshots(store, since=None)\n"
        "g1b = {m['id']: m for m in store['models']}['gemma-3-1b']\n"
        "print('COPIED_PRESENT=' + str(any(e.get('tps') == '18' and e.get('date') == '2026-10-10' "
        "for e in g1b.get('engines', []))))\n"
    )
    r, out = _run_ingest(body, tmp)
    check("the scratch ingest subprocess runs clean", r.returncode == 0, (r.returncode, out[-400:]))
    lines = [ln for ln in out.splitlines()
             if ln.startswith("[ingest] REFUSED") and COPY_POST in ln]
    check("the thrice-captured post prints exactly ONE refusal line",
          len(lines) == 1, lines)
    check("the grouped line names the repetition across snapshots",
          len(lines) == 1 and "seen 3x across snapshots" in lines[0]
          and "amd-re.json" in lines[0] and "cpu-re.json" in lines[0]
          and "nvidia-re.json" in lines[0], lines)
    check("the copy is still refused (never merges)",
          "COPIED_PRESENT=False" in out, out[-400:])
    shutil.rmtree(tmp, ignore_errors=True)


def test_distinct_refusals_each_still_get_their_own_line():
    # Dedup must never SWALLOW a refusal: two different refusals (a cross-model
    # copy on one post, a fabricated engine on another) each print their own line,
    # with no repetition suffix for a post seen once.
    tmp = ROOT / "tmp-882-distinct-e2e"
    fabricated = json.dumps({
        "id": "gemma-3-4b", "name": "Gemma 3 4B",
        "hf": "google/gemma-3-4b-it", "formats": [{"format": "GGUF"}],
        "engines": [{
            "engine": "Q4_K_M", "tps": "77", "hardware": "RTX 4090 24GB",
            "quant": "Q4_K_M", "date": "2026-11-05",
            "source_post": "https://lightbrd.com/fakepost/status/2120000000000000001",
        }],
    })
    body = (
        f'(tmp / \'raw\' / \'copy-leg.json\').write_text(json.dumps('
        f'{{"generated_utc": "2026-11-01T23:00:00Z", "backend": "amd", '
        f'"models": [{json.dumps(COPY_ROW)}]}}))\n'
        f"(tmp / 'raw' / 'fabricated-leg.json').write_text(json.dumps("
        f'{{"generated_utc": "2026-11-02T23:00:00Z", "backend": "nvidia", '
        f'"models": [{fabricated}]}}))\n'
        "added, updated = ut.ingest_raw_snapshots(store, since=None)\n"
    )
    r, out = _run_ingest(body, tmp)
    check("the scratch ingest subprocess runs clean", r.returncode == 0, (r.returncode, out[-400:]))
    copy_lines = [ln for ln in out.splitlines()
                  if ln.startswith("[ingest] REFUSED") and COPY_POST in ln]
    fab_lines = [ln for ln in out.splitlines()
                 if ln.startswith("[ingest] REFUSED") and "2120000000000000001" in ln]
    check("the cross-model copy refusal is reported", len(copy_lines) == 1, copy_lines)
    check("the fabricated-engine refusal is reported on its own line",
          len(fab_lines) == 1 and "fabricated engine" in fab_lines[0], fab_lines)
    check("a refusal seen once carries no repetition suffix",
          len(fab_lines) == 1 and "seen" not in fab_lines[0], fab_lines)
    shutil.rmtree(tmp, ignore_errors=True)


def test_shipped_raw_replay_reports_each_refusal_once_per_post_and_rule():
    # The Done-when replay (issue #882): ALL shipped data/raw snapshots re-ingest
    # against a copy of the shipped store, and every seam refusal line must be
    # unique per (rule, model, post) — while the run-level refusal COUNT in the
    # summary line stays the full 253-style number (the ledger never shrinks).
    tmp = ROOT / "tmp-882-replay-e2e"
    body = (
        "shutil.copytree(ROOT / 'data' / 'raw', tmp / 'raw', dirs_exist_ok=True)\n"
        "added, updated = ut.ingest_raw_snapshots(store, since=None)\n"
    )
    r, out = _run_ingest(body, tmp)
    check("the shipped replay subprocess runs clean", r.returncode == 0, (r.returncode, out[-400:]))
    seam_lines = [ln for ln in out.splitlines() if SEAM_LINE.match(ln)]
    keys = [(m.group(1), m.group("engine"), m.group("mid").strip(), m.group("post"))
            for ln in seam_lines if (m := SEAM_LINE.match(ln))]
    dupes = {k for k in keys if keys.count(k) > 1}
    check("no (rule, model, post) prints more than one refusal line",
          not dupes, sorted(dupes)[:3])
    grouped = [ln for ln in seam_lines if "seen " in ln and "x across snapshots" in ln]
    check("real re-captured posts are reported as grouped repetitions",
          len(grouped) >= 3, len(grouped))
    m = re.search(r"\[ingest\] (\d+) measurement\(s\) refused at ingest this run", out)
    check("the refusal COUNT stays the full number while lines dedupe",
          m is not None and int(m.group(1)) > len(seam_lines) > 0,
          (m.group(0) if m else None, len(seam_lines)))
    shutil.rmtree(tmp, ignore_errors=True)


def main() -> int:
    test_a_post_refused_by_every_leg_prints_one_grouped_line()
    test_distinct_refusals_each_still_get_their_own_line()
    test_shipped_raw_replay_reports_each_refusal_once_per_post_and_rule()
    print(f"refusal-grouping: {_PASS} passed, {_FAIL} failed")
    return 1 if _FAIL else 0


if __name__ == "__main__":
    raise SystemExit(main())
