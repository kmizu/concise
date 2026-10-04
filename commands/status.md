---
description: Show whether concise always-on mode is enabled and where the flag file lives
allowed-tools: Bash(node:*)
---

Run exactly this command with the Bash tool:

```
node "${CLAUDE_PLUGIN_ROOT}/hooks/always-on-flag.mjs" status
```

Reply with the command's single output line verbatim, followed by one line of options:

- If it says `enabled`: `Turn off for good: /concise:always-off`
- If it says `disabled`: `This session: /concise. Every session: /concise:always-on`

Nothing else.
