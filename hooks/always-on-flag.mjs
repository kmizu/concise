// Manage the always-on opt-in flag that hooks/always-on.mjs checks at session
// start: $CLAUDE_CONFIG_DIR/.concise-always (default ~/.claude).
//
//   node hooks/always-on-flag.mjs on      # create the flag
//   node hooks/always-on-flag.mjs off     # delete the flag
//   node hooks/always-on-flag.mjs status  # report whether it exists
//
// This is the only file the plugin ever writes outside the repository, and
// only when the user runs /concise:always-on. "off" is the undo path.
// Output is one plain line; exit code is 0 unless the action itself failed.

import fs from "node:fs";
import os from "node:os";
import path from "node:path";

const claudeDir = process.env.CLAUDE_CONFIG_DIR || path.join(os.homedir(), ".claude");
const flagPath = path.join(claudeDir, ".concise-always");
const action = (process.argv[2] || "status").toLowerCase();

function exists() {
  try {
    return fs.statSync(flagPath).isFile();
  } catch {
    return false;
  }
}

try {
  switch (action) {
    case "on":
      if (!fs.existsSync(claudeDir)) {
        process.stdout.write(`always-on: not enabled. Config dir does not exist: ${claudeDir}\n`);
        process.exit(1);
      }
      if (!exists()) fs.writeFileSync(flagPath, "", { flag: "wx" });
      process.stdout.write(`always-on: enabled. Flag: ${flagPath}\n`);
      break;
    case "off":
      if (exists()) fs.unlinkSync(flagPath);
      process.stdout.write(`always-on: disabled. Removed: ${flagPath}\n`);
      break;
    case "status":
      process.stdout.write(
        exists()
          ? `always-on: enabled. Flag: ${flagPath}\n`
          : `always-on: disabled. Flag not present: ${flagPath}\n`,
      );
      break;
    default:
      process.stdout.write(`always-on: unknown action "${action}". Use on, off, or status.\n`);
      process.exit(2);
  }
} catch (error) {
  process.stdout.write(`always-on: failed to ${action}: ${error?.message || error}\n`);
  process.exit(1);
}
