// SessionStart hook: injects the full concise ruleset when the user has opted
// in by creating $CLAUDE_CONFIG_DIR/.concise-always (default ~/.claude).
// Never blocks session start: any failure exits 0.
//
// Runs under Node so it behaves the same on macOS, Linux, and Windows. The
// hooks.json launcher resolves this module from the plugin root rather than
// relying on platform-specific shell expansion for the script path.

import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";

try {
  const claudeDir = process.env.CLAUDE_CONFIG_DIR || path.join(os.homedir(), ".claude");
  const flagPath = path.join(claudeDir, ".concise-always");

  // Only fire when the user has opted in.
  if (!fs.existsSync(flagPath)) process.exit(0);

  // Resolve SKILL.md relative to this script's own location, not a trusted env var.
  const scriptDir = path.dirname(fileURLToPath(import.meta.url));
  const skillPath = path.join(scriptDir, "..", "skills", "concise", "SKILL.md");
  if (!fs.existsSync(skillPath)) process.exit(0);

  // Strip a leading YAML frontmatter block (--- ... --- at the very top of file).
  const body = fs
    .readFileSync(skillPath, "utf8")
    .replace(
      /^---[^\S\r\n]*\r?\n[\s\S]*?\r?\n---[^\S\r\n]*(?:\r?\n|$)/,
      "",
    )
    .replace(/(?:\r?\n)+$/, "")
    // A CRLF checkout adds a byte per line; the output must stay under the
    // size Claude Code injects in full.
    .replace(/\r\n/g, "\n")
    // The closing credit line is for people reading the file, not the model.
    .replace(/\n---\n\n[^\n]*$/, "");

  process.stdout.write(
    "CONCISE MODE ACTIVE (always-on). The user opted in. Apply these standing presentation rules to every response. " +
      '/concise:off or "stop concise mode" turns them off this session; ' +
      `/concise:always-off (or deleting ${flagPath}) disables always-on.\n\n${body}\n`,
  );
} catch {
  // Never block session start.
  process.exit(0);
}
