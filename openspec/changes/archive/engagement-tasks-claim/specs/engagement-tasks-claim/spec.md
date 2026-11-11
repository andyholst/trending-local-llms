# engagement-tasks-claim

## ADDED Requirements

### Requirement: merged measurement-store-normalized task list makes no false byte-identical claim

The `measurement-store-normalized/tasks.md` on master must not claim the README is
byte-identical. Every task line in that change dir that mentions the README must instead
disclose that the README is regenerated from the flattened view and its engagement-derived
buzz/trend lines are re-resolved from the canonical `data/posts.json` (the intended GWT2
consequence).

#### Scenario: tasks.md discloses re-resolution, not byte-identity

- **Given** the merged `openspec/changes/measurement-store-normalized/tasks.md`
- **When** its README-bearing task lines are inspected
- **Then** none asserts `README.md byte-identical`; the re-resolution disclosure from the corrected proposal is reflected
- **Test:** openspec-check + manual grep — `git show master:.../tasks.md` contains no `README.md byte-identical`
