---
description: Turn concise mode on for every future Claude Code session (creates the always-on flag file)
allowed-tools: Bash(node:*)
---

Enable always-on mode by running exactly this command with the Bash tool:

```
node "${CLAUDE_PLUGIN_ROOT}/hooks/always-on-flag.mjs" on
```

It creates one empty file, `.concise-always`, inside the Claude config directory (`$CLAUDE_CONFIG_DIR`, default `~/.claude`). Nothing else is written. A `SessionStart` hook then loads the ruleset at the start of every session; `/concise:always-off` deletes the file again.

Report the command's single output line verbatim, then add one line: `Undo: /concise:always-off`. Nothing else.

Also apply the `concise` skill ruleset to the rest of this session, starting now.
