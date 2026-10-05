# Claude Code response quality pilot, 2026-10-06

Native Claude Code answers, collected through the plugin's always-on hook, did
not show the 0.4.0 to 0.5.0 quality gain seen in the [Codex pilot](../PILOT.md).
In Claude Code, version 0.4.0 already passed all twelve scenarios. Version 0.5.0
passed eleven and used 18.1% more characters than 0.4.0.

| Condition | Semantic passes | Total characters | Mean characters |
| --- | ---: | ---: | ---: |
| No concise rules | 11/12 | 7,610 | 634.2 |
| concise 0.4.0 | 12/12 | 5,721 | 476.8 |
| concise 0.5.0 | 11/12 | 6,758 | 563.2 |

Against no rules, 0.4.0 cut characters by 24.8% and 0.5.0 by 11.2%. These are
descriptive character counts from one run per case, not token counts or
estimated effects. Both simple facts stayed under 100 characters in every
condition.

## What the review found

| Condition | Scenario | Reviewer's finding |
| --- | --- | --- |
| No rules | Two requested topics (ja) | Asked for the plugin's path or files instead of giving two improvements, and disputed the stated branch context. Judged inaccurate, incomplete, and an unnecessary question. |
| 0.5.0 | Authorized fixture fix (en) | Named the next in-scope action and the test rerun without asking approval, but stated "The tests haven't been rerun yet" as fact, which the context does not support. Judged inaccurate on that one sentence. |

No 0.4.0 answer was flagged. All three conditions asked about staging versus
production when the deployment target was missing, and none claimed to have
deployed, deleted, or fixed anything the context did not support. The four
omissions the Codex pilot found in 0.4.0 (missing verification or follow-up
measurement) did not appear in the Claude Code 0.4.0 answers.

## Reading the result

The 0.5.0 rules were written to fix omissions observed in Codex. Claude Code's
own system prompt already pushes toward verification and completeness, so the
added wording bought little here and relaxed the length rule. The one 0.5.0
failure is a stated assumption, not a missing step; the same reviewer passed a
no-rules answer with a similar claim, so this is a borderline judgment, recorded
as given.

The canonical rules stay at 0.5.0: they did not regress completeness or
readability in this host, and they make uncertainty handling explicit. The
length cost is the open question. A follow-up could test a shorter length rule
on both hosts with repeated samples before changing anything.

## Collection and review

Twelve cases, three conditions, one fresh `claude -p` session per case with
`--setting-sources ""` and `--tools ""`, run by
`scripts/collect_claude_answers.py` from an empty non-repository directory. The
0.4.0 and 0.5.0 conditions loaded a frozen checkout of the plugin with
`--plugin-dir`, so the SessionStart hook injected that version's rules exactly
as it does for an installed plugin. The frozen rule files are in `baselines/`
and match the hashes in `pilot.json`.

A first capture was discarded before review was attached: the sessions had run
inside the repository checkout, and Claude Code's working-directory context
(branch name, modified files) leaked into one fictional scenario. The script now
runs from an empty temporary directory, and the recorded capture is the second
one.

A fresh Claude Code subagent judged all 36 answers with condition names hidden
and labels shuffled per case. It saw context, prompt, rubric, and answer text,
and recorded evidence for each grade. No grade or answer was edited after
review. The reviewer is from the same model family as the generators, not a
human.

## Limits

One sample per case per condition; a single run cannot separate the one 0.5.0
failure from sampling noise. Claude Code's built-in system prompt applies in all
conditions, so "no rules" means without concise, not without instructions. No
multi-turn execution or persistence test. The exact model identity is not
exposed by the CLI.

## Inspect and reproduce

```bash
python scripts/evaluate_responses.py evals/claude-code/pilot.json --output /tmp/claude-code-results.json
```

Replaying the scorer validates the recorded capture, hashes, and review; it does
not generate new answers. For a fresh capture, follow the
[evaluation guide](../README.md).
