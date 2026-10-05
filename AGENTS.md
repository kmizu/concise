# Agent guide

Map for agents working on **concise**, a Claude Code plugin. It says where the behavior lives and how to verify a change. It does not replace the rules in `skills/concise/SKILL.md`.

## Start here

1. `README.md` for purpose, commands, and user-facing behavior.
2. `skills/concise/SKILL.md` for the canonical ruleset.
3. `CONTRIBUTING.md` before proposing changes.

Do not read secrets, home-directory configuration, or local runtime caches. Run only the commands the task needs.

## Repository map

| Area | Location | Purpose |
| --- | --- | --- |
| Manifests | `.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json` | Plugin metadata and the single-plugin marketplace. Keep `version` in `plugin.json` current. |
| Skill | `skills/concise/SKILL.md` | Source of truth for the ten rules and the response shape. Invoked as `/concise`. |
| Commands | `commands/off.md`, `always-on.md`, `always-off.md`, `status.md` | `/concise:off`, `/concise:always-on`, `/concise:always-off`, `/concise:status`. |
| Hooks | `hooks/hooks.json`, `hooks/always-on.mjs` | `SessionStart` hook that injects the ruleset when the always-on flag exists. Fail-safe: any error exits 0. |
| Flag script | `hooks/always-on-flag.mjs` | The only code that creates or deletes `$CLAUDE_CONFIG_DIR/.concise-always` (default `~/.claude`). |
| Tests | `tests/` | Hook and flag-script tests. Use temp dirs; never touch the real config dir. |
| CI | `.github/workflows/plugin-load-check.yml` | Runs the tests on Ubuntu and Windows, then installs the plugin from the checkout into a scratch config and checks it loads. |

## Rules of the repository

- `skills/concise/SKILL.md` holds the ruleset in bracket notation inside a `text` code block: `[tag attrs]{body}`, no closing tags, `[txt]{...}` for literal text. Keep braces balanced.
- Behavior changes go in `skills/concise/SKILL.md`. Commands and hooks only load or toggle it; they do not restate the rules.
- Nothing in this repository writes outside the repository except `hooks/always-on-flag.mjs`, and only to the one flag file, and only when the user runs `/concise:always-on`. Keep it that way.
- Hooks must stay fast, offline, and fail-safe. A broken hook must never block session start.
- Keep the hook output under 10 KB (`SKILL.md` body plus banner). Above that, Claude Code injects only a 2 KB preview and always-on loses the rules. A test enforces this.
- Credit to the original project (`i-have-adhd` by Ayoub Ghriss, MIT) stays in `README.md`, `SKILL.md`, and `LICENSE`.

## Verification

```bash
python -m unittest discover -s tests -v
claude plugin validate .
```

For a load check, mirror CI: set `CLAUDE_CONFIG_DIR` to a scratch directory, `claude plugin marketplace add <checkout path>`, `claude plugin install concise@concise`, then confirm `claude plugin list` shows `enabled`. Run `git diff --check` before submitting.
