# Tasks: seam-positional-command (#632)

- [x] `Makefile` `scrubbed_run` seam rewritten: the command reaches
  `bash -c` as positional `$1` (`$(subst ','\'',$(1))` escaping +
  `eval "$$1"`), the capture paths as `$2`/`$3` — the command is never
  spliced into the script text.
- [x] Proven red-then-green: the single-quote probe command exits 2 with a
  bash splice syntax error on the OLD seam (fixture run) and exits 0 on the
  new one.
- [x] `tests/test_scrubbed_run_seam.py` (new): drives the REAL shipped seam
  through a fixture Makefile — quoted-prose command survives; the seam text
  refuses the old splice shape; redaction (mask on console, both capture
  files) and the pipefail status contract are preserved.
- [x] `AGENTS.md` §8 guard row for the new suite (rule 6c).
- [x] OpenSpec change recorded (proposal, spec delta, tasks) and the root
  index regenerated (`make openspec-index`).
