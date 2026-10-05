# Response quality implementation plan

**Goal:** Evaluate real answers before changing concise, then remove pressure to
omit necessary detail or wait for unnecessary confirmation.

**Approved brief:** Compare no rules, current rules, and revised rules for
completeness, readability, and character count. Match response length to the
task, retain material uncertainty, and distinguish blocking questions from
routine decisions within already-authorized work.

**Architecture:** A fixed bilingual scenario suite and a standard-library
offline scorer. Capture actual agent answers, keep deterministic content
checks separate from an independent semantic review, and publish a bounded
pilot report. The plugin remains offline and presentation-only.

**Constraints:** Preserve canonical bracket notation, ten rules, attribution,
destructive-action confirmation, and explicit activation. Keep the complete
always-on hook output below 10,000 bytes. Generate the Codex package from the
canonical rules; never inspect credentials, home configuration, or caches.

## Tasks

- [x] Add scenarios and scorer tests; demonstrate missing implementation fails.
- [x] Implement the scorer, including missing/duplicate coverage rejection,
      unreviewed-answer handling, and quality gates independent of brevity.
- [x] Capture actual no-rules/current-rules pressure-scenario answers before
      editing the canonical skill. Record collection context and source hashes.
- [x] Revise length, uncertainty, and confirmation rules; bump the plugin
      version, update user documentation, and regenerate the Codex package.
- [x] Capture revised-rule answers, independently review anonymized outputs,
      score all conditions, and record limitations without claiming statistical
      or cross-model improvement from a small pilot.
- [x] Run the full test suite, manifest validation, package consistency checks,
      and fresh code review.

**Delivery:** One implementation commit and a PR.

## Verification and review focus

Simple answers must stay short; complex one-line requests must retain needed
detail; uncertainty must not become false certainty; authorized work must not
be paused for routine choices; genuinely blocking or destructive requests must
still require input. Checks must detect negated keywords, duplicated/missing
samples, malformed review data, and differences between text-only simulated
work reports and actual filesystem actions.
