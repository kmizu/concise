# Contributing

Thanks for improving **concise**. Changes from humans and coding agents are both welcome. Keep them small, reviewable, and safe to run.

## Where things go

- Rule changes: `skills/concise/SKILL.md`. Keep the good/bad example pairs; they do most of the work.
- Command changes: `commands/*.md`. Each command does one thing and reports one line.
- Hook changes: `hooks/`. Hooks must stay fast, offline, and fail-safe (any error exits 0).

## Safety

- The plugin writes exactly one file outside the repository, `$CLAUDE_CONFIG_DIR/.concise-always`, and only when the user runs `/concise:always-on`. Do not add other writes, persistence, network calls, or privilege requirements.
- Skill text must stay about response structure. Do not add instructions that read or send private data, bypass confirmations for destructive actions, or override higher-priority instructions.
- Tests use temporary directories and never touch a real Claude config directory.

## Before opening a pull request

1. `python -m unittest discover -s tests -v` passes (needs `node` on `PATH`).
2. `claude plugin validate .` passes.
3. `git diff --check` is clean and the diff contains only the intended files.
4. The PR says what changed, why, and which commands you ran. If an agent wrote most of the change, say so and name the tool.

## Credit

concise is derived from [i-have-adhd](https://github.com/ayghri/i-have-adhd) by Ayoub Ghriss (MIT). Keep that credit in `README.md`, `SKILL.md`, and `LICENSE`.
