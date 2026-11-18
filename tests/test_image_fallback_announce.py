#!/usr/bin/env python3
"""Issue #1120 (change `announce-corrupt-tag-fallback-1120`): the corrupt-tag
fallback announcement on the PR.

`scripts/ensure_image.py` announces a but-corrupt fallback with
`corrupt-tag-fallback=<image>=<tag>` (pinned in tests/test_ensure_image.py);
qa-validate's `validate` job captures those lines into allowlisted
GITHUB_OUTPUT keys and calls `make announce-image-fallback`, which posts ONE
marker-deduplicated comment naming exactly which runner images CI built
without a pull. This suite drives the REAL announcer with `gh` stubbed on
PATH (an EXTERNAL system only — rule 6m) and pins the workflow wiring.
"""
from __future__ import annotations

import datetime as dt
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "scripts" / "announce_image_fallback.py"
sys.path.insert(0, str(ROOT / "scripts"))
import bot_markers as bm  # noqa: E402

NOW = "2026-11-18T09:00:00Z"
REPO = "andyholst/trending-local-llms"
PR = "1130"
RUN_ID = "44123456789"
IMAGES = "corrupt-tag-fallback=base=ghcr.io/andyholst/trending-local-llms:dockerfile-5b44520adc6c " \
         "corrupt-tag-fallback=openspec=ghcr.io/andyholst/trending-local-llms-openspec:openspec-322b2b9f240c"

_GH_STUB = '''#!/usr/bin/env python3
import json, os, sys
from pathlib import Path
D = Path(os.environ["FAKE_GH_DIR"])
args = sys.argv[1:]
with (D / "calls.log").open("a") as fh:
    fh.write(json.dumps(args) + "\\n")
if (D / "fail-comments.txt").exists() and "/comments" in " ".join(args):
    sys.stderr.write("HTTP 502\\n")
    sys.exit(1)
if args[:2] == ["issue", "comment"]:
    path = args[args.index("--body-file") + 1]
    body = Path(path).read_text()
    with (D / "posted.jsonl").open("a") as fh:
        fh.write(json.dumps({"issue": args[2], "repo": args[args.index("--repo") + 1],
                            "body": body}) + "\\n")
    print("https://github.com/andyholst/trending-local-llms/pull/1130#issuecomment-1")
    sys.exit(0)
if args[:1] == ["api"] and "/comments" in args[1]:
    data = json.loads((D / "comments.json").read_text())
    if "--paginate" in args:
        # --paginate + `.[]` answers one JSON object PER LINE across every page.
        for c in data:
            print(json.dumps(c))
    else:
        # NO --paginate: GitHub answers the FIRST page only (oldest-first, 100 max).
        print(json.dumps(data[:100]))
    sys.exit(0)
sys.exit(2)
'''

passed = failed = 0


def check(name: str, ok: bool, detail: object = "") -> None:
    global passed, failed
    if ok:
        passed += 1
        print(f"  ok  {name}")
    else:
        failed += 1
        print(f"  FAIL {name}  [{detail}]")


def env_for(td: Path, comments: list[dict] | None = None, fail: bool = False) -> dict:
    """The announcer's environment with `gh` stubbed on PATH (external system, rule 6m)."""
    bindir = td / "bin"
    bindir.mkdir(exist_ok=True)
    gh = bindir / "gh"
    gh.write_text(_GH_STUB, encoding="utf-8")
    gh.chmod(0o755)
    (td / "comments.json").write_text(json.dumps(comments or []), encoding="utf-8")
    if fail:
        (td / "fail-comments.txt").write_text("1")
    env = {**os.environ, "PATH": f"{bindir}{os.pathsep}{os.environ['PATH']}",
           "FAKE_GH_DIR": str(td), "REPO": REPO, "PR_NUMBER": PR, "GITHUB_RUN_ID": RUN_ID,
           "IMAGES": IMAGES, "RUN_URL": f"https://github.com/{REPO}/actions/runs/{RUN_ID}"}
    return env


def run(args: list[str], env: dict) -> tuple[int, str]:
    proc = subprocess.run([sys.executable, str(SCRIPT), *args],
                          cwd=ROOT, capture_output=True, text=True, env=env)
    return proc.returncode, proc.stdout + proc.stderr


def calls(td: Path) -> list[list[str]]:
    log = td / "calls.log"
    return [json.loads(l) for l in log.read_text().splitlines() if l.strip()] if log.exists() else []


def posted(td: Path) -> list[dict]:
    p = td / "posted.jsonl"
    return [json.loads(l) for l in p.read_text().splitlines()] if p.exists() else []


def marker_comment(run_id: str) -> dict:
    body = "## Corrupt-tag fallback\n\n" + bm.start_marker(
        "qa-validate", dt.datetime.fromisoformat(NOW.replace("Z", "+00:00")),
        run=run_id, kind="image_fallback")
    return {"createdAt": NOW, "body": body}


def test_the_announcement_names_the_images_and_carries_the_registered_marker() -> None:
    """Scenario: A fallback is announced as ONE comment (dry run prints the exact body)."""
    with tempfile.TemporaryDirectory() as t:
        td = Path(t)
        rc, out = run(["--now", NOW], env_for(td))
        check("dry run exits 0", rc == 0, out[-300:])
        check("the comment names the base tag rebuilt without a pull",
              "dockerfile-5b44520adc6c" in out and "blobs unfetchable" in out, out[-500:])
        check("the comment names the openspec tag too",
              "openspec-322b2b9f240c" in out, out[-500:])
        marker = bm.read_marker(out, "qa-validate", "image_fallback")
        check("the comment carries the registered corrupt-tag-fallback marker",
              marker is not None, out[-300:])
        check(f"the marker is stamped run={RUN_ID} (the dedup key)", f"run={RUN_ID}" in out, out[-300:])
        check("nothing is posted without --post", posted(td) == [], str(posted(td)))


def test_the_announcement_is_deduplicated_by_the_run_id() -> None:
    """Scenarios: A CI run announces once; a different run announces again."""
    with tempfile.TemporaryDirectory() as t:
        td = Path(t)
        rc, out = run(["--now", NOW, "--post"], env_for(td))
        check("--post posts through `gh issue comment <pr> --repo … --body-file`",
              rc == 0 and any(c[:2] == ["issue", "comment"] and c[2] == PR
                              and "--repo" in c for c in calls(td)), str(calls(td)))
        entry = (posted(td) or [{}])[0]
        check("the comment lands on the right PR of the right repo",
              entry.get("issue") == PR and entry.get("repo") == REPO, str(entry))

        # Same run id already announced -> silence, no second comment.
        again = run(["--now", NOW, "--post"],
                    env_for(td, comments=[marker_comment(RUN_ID)]))
        check("a run that already announced posts nothing (run=<id> dedup)",
              again[0] == 0 and "deduped" in again[1] and len(posted(td)) == 1,
              f"{again[0]} {again[1][-200:]} posts={len(posted(td))}")

        # A DIFFERENT run's marker does not suppress this run.
        other = run(["--now", NOW, "--post"],
                    env_for(td, comments=[marker_comment("99999999999")]))
        check("a fresh CI run announces even when an older run announced",
              other[0] == 0 and len(posted(td)) == 2, f"{other[0]} posts={len(posted(td))}")


def test_a_long_thread_is_read_whole_for_the_dedupe() -> None:
    """The #662 class: newest-last on page 2. A first-page read would double-post."""
    with tempfile.TemporaryDirectory() as t:
        td = Path(t)
        busy = [{"createdAt": NOW, "body": f"reply {i}"} for i in range(149)]
        busy.append(marker_comment(RUN_ID))  # newest comment, would sit on page 2
        rc, out = run(["--now", NOW, "--post"], env_for(td, comments=busy))
        check("the whole-thread read finds the marker on a later page and stays silent",
              rc == 0 and "deduped" in out and posted(td) == [], f"{rc} {out[-200:]}")
        reads = [c for c in calls(td) if c[:1] == ["api"] and "/comments" in c[1]]
        check("the comment read asks GitHub with --paginate",
              bool(reads) and all("--paginate" in c for c in reads), str(reads))


def test_missing_inputs_fail_loudly() -> None:
    """Scenario: A missing input is a loud failure."""
    with tempfile.TemporaryDirectory() as t:
        td = Path(t)
        base_env = env_for(td)

        no_pr = {k: v for k, v in base_env.items() if k != "PR_NUMBER"}
        rc, out = run([], no_pr)
        check("no PR number -> exit 2 naming the missing input",
              rc == 2 and "PR" in out, f"{rc} {out[-200:]}")

        no_images = {k: v for k, v in base_env.items() if k != "IMAGES"}
        rc, out = run([], no_images)
        check("no images reported -> exit 2 (there is nothing to announce)",
              rc == 2 and "no images" in out.lower(), f"{rc} {out[-200:]}")

        no_repo = {k: v for k, v in base_env.items() if k != "REPO"}
        no_repo.pop("GITHUB_REPOSITORY", None)
        rc, out = run([], no_repo)
        check("no repo -> exit 2 naming it", rc == 2 and "repo" in out.lower(), f"{rc} {out[-200:]}")

        # An unreadable thread is a loud failure too (never a silent 'not announced').
        rc, out = run(["--now", NOW, "--post"], env_for(td, fail=True))
        check("an unreadable PR thread -> exit 2, nothing posted",
              rc == 2 and posted(td) == [], f"{rc} {out[-200:]}")


def test_the_target_is_wired_to_the_makefile_and_ci() -> None:
    """Rules 6d/6m: the announcer is reachable only through a make target CI calls.

    (issue #1120) The qa-validate STEP wiring — capture shape, gate, token,
    permissions — is pinned in tests/test_workflows.py::
    test_the_corrupt_tag_fallback_is_announced_on_the_pr; this half keeps the
    Makefile target and its single caller unique to the PR gate."""
    mk = (ROOT / "Makefile").read_text()
    check("make announce-image-fallback runs the ONE script",
          "announce-image-fallback:" in mk
          and "python3 scripts/announce_image_fallback.py" in mk, mk[:0] or "target missing")
    wf = (ROOT / ".github" / "workflows" / "qa-validate.yml").read_text()
    check("qa-validate calls it", "make announce-image-fallback" in wf, "no caller")
    check("no other pipeline announces it (announcement belongs to the PR gate)",
          sum(1 for p in (ROOT / ".github" / "workflows").glob("*.yml")
              if "announce-image-fallback" in p.read_text()) == 1, "duplicate caller")


def main() -> int:
    print("corrupt-tag fallback announcement (scripts/announce_image_fallback.py, issue #1120)")
    test_the_announcement_names_the_images_and_carries_the_registered_marker()
    test_the_announcement_is_deduplicated_by_the_run_id()
    test_a_long_thread_is_read_whole_for_the_dedupe()
    test_missing_inputs_fail_loudly()
    test_the_target_is_wired_to_the_makefile_and_ci()
    print(f"\n{passed} passed, {failed} failed")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
