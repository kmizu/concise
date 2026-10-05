# Response quality pilot, 2026-10-06

Version 0.5.0 retained the required information in all twelve reviewed scenarios.
Version 0.4.0 omitted verification or follow-up measurement in four. The revised
answers were longer than the old concise answers and shorter than answers
without concise rules.

| Condition | Semantic passes | Total characters | Mean characters |
| --- | ---: | ---: | ---: |
| No concise rules | 12/12 | 3,511 | 292.6 |
| concise 0.4.0 | 8/12 | 1,764 | 147.0 |
| concise 0.5.0 | 12/12 | 2,071 | 172.6 |

The revised batch used 17.4% more characters than 0.4.0 and 41.0% fewer than the
no-rules batch. These are descriptive character counts, not token counts or
statistically estimated effects. Both simple facts remained under 100
characters in every condition.

## What the review found

| Scenario | Omission in 0.4.0 | What 0.5.0 retained |
| --- | --- | --- |
| Release rollback | Checking successful requests alone does not establish that the failure rate recovered. | Check success and failure rates under comparable traffic. |
| One-run benchmark | The observation was qualified correctly, but no next measurement was given. | Repeat both versions and compare timing distributions. |
| Authorized fixture fix | The next fix was named; test verification was missing. | Correct the newline and rerun tests. |
| Repeated HTTP 401 failure | The new diagnosis and correction were named; verification was missing. | Add authorization and rerun the test. |

The reviewer accepted 0.4.0's immediately qualified “Yes, in this run” as
accurate. The issue in that answer was omitted measurement, not false certainty.
All three conditions asked for the unknown deployment target and preserved
unapproved user data. None was judged to ask an unnecessary question, so this
pilot does not demonstrate fewer permission requests. The new rule makes that
boundary explicit; broader pressure tests are still needed.

## Collection and review

The fixed bilingual suite contained twelve cases. One fresh Codex agent per
condition generated a batch using only prompt/context inputs and that
condition's frozen rules. The two baselines were captured before the canonical
skill was edited. No scenario actions were executed; a statement of intended
work was graded separately from a claim of completion.

Another fresh agent judged all 36 answers with condition names hidden and labels
shuffled independently per case. It saw the context, prompt, semantic rubric,
and answer text. Each grade records specific evidence. No grade or captured
answer was changed after review.

The generators and reviewer inherited the current Codex session's model and
reasoning settings; the exact backend identity was not independently exposed.
They also shared harness instructions. The no-rules condition therefore means
“without concise,” not “without any instructions.”

This is one response per case per condition, with cases batched in the same
condition context. It is an agent review from the same model family, not human
review. Style may reveal a condition despite hidden labels. The study does not
measure native Claude Code response behavior, repeated-sample variance,
multi-turn execution, mode persistence, or general performance across models.

## Inspect and reproduce

`pilot.json` records collection details and hashes of cases and rule snapshots.
`*-answers.json` contains the untouched answers. `review-input.json` and
`review-key.json` show the anonymization; `blind-decisions.json` contains the
independent judgments; `reviews.json` binds them to answer hashes. `results.json`
contains per-case quality decisions, indicators, character counts, and lines.

```bash
python scripts/evaluate_responses.py evals/pilot.json --require-quality --condition revised
```

The [evaluation guide](README.md) describes fresh collection and review. Replaying
the scorer validates recorded evidence; it does not generate new model answers.
