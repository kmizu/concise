---
description: Turn always-on concise mode off (deletes the always-on flag file); the current session keeps its mode
allowed-tools: Bash(node:*)
---

Disable always-on mode by running exactly this command with the Bash tool:

```
node "${CLAUDE_PLUGIN_ROOT}/hooks/always-on-flag.mjs" off
```

It deletes `.concise-always` from the Claude config directory (`$CLAUDE_CONFIG_DIR`, default `~/.claude`) if it exists. Nothing else changes.

Report the command's single output line verbatim, then add one line: `Future sessions start in normal mode. This session is unchanged; /concise:off switches it now.` Nothing else.
