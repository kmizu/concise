<p align="center">
  <img src="logo.svg" alt="concise" width="120" />
</p>
<h1 align="center">concise</h1>
<p align="center">
  <strong>Structured, concise answers from Claude Code.</strong><br/>
  Answer first. Steps numbered. Nothing to scroll past.
</p>
<p align="center">
  <sub>A fork of <a href="https://github.com/ayghri/i-have-adhd">i-have-adhd</a>, generalized for anyone who wants concise output.</sub>
</p>
<p align="center">
  <a href="LICENSE"><img src="https://img.shields.io/github/license/kmizu/concise-plugin?style=flat" alt="License"></a>
  <img src="https://img.shields.io/badge/claude%20code-plugin-0F172A?style=flat" alt="Claude Code plugin">
</p>

## Install

```bash
claude plugin marketplace add kmizu/concise-plugin
claude plugin install concise@concise
```

Then, inside Claude Code: `/concise`.

Update later with:

```bash
claude plugin marketplace update concise
claude plugin update concise@concise
```

## Commands

| Command | Scope | What it does |
| --- | --- | --- |
| `/concise` | This session | Apply the ruleset to every response until you turn it off |
| `/concise:off` | This session | Back to Claude's default style |
| `/concise:always-on` | Every session | Load the ruleset at session start, no command needed |
| `/concise:always-off` | Every session | Undo always-on; the current session is unchanged |
| `/concise:status` | | Is always-on enabled, and where the flag file lives |

Always-on is a single empty file, `~/.claude/.concise-always` (`$CLAUDE_CONFIG_DIR/.concise-always` if you set one). Installing the plugin writes nothing. `/concise:always-on` writes that one file, `/concise:always-off` deletes it. Saying "stop concise mode" does the same as `/concise:off`.

## What changes

<table>
<tr>
<td width="50%">

**Before**

> Great question! Docker build performance can depend on a lot of factors. Looking at your Dockerfile, I notice that you're copying the entire project directory before running `npm ci`, which means that any change to any file invalidates the layer cache and forces a full reinstall of dependencies. One approach would be to copy `package.json` and `package-lock.json` first, run the install, and then copy the rest. You might also want to add a `.dockerignore` file to exclude `node_modules` and other large directories. Hope this helps! Let me know if you'd like me to make these changes.

</td>
<td width="50%">

**After**

> Move `COPY . .` below `RUN npm ci` so the dependency layer caches (`Dockerfile:6`).
>
> 1. Add `COPY package*.json ./` before `RUN npm ci`
> 2. Move `COPY . .` after it
> 3. Rebuild: `docker build .` (the second build skips `npm ci`)
>
> Separately: no `.dockerignore`, so `node_modules` is sent to the daemon. Want that next?

</td>
</tr>
</table>

## The shape

Concise means fewer sentences, not compressed ones. Structured means the form matches the content, not more formatting. A one-line question gets a one-line answer; a longer response is built from these parts, each present only when it carries information:

| Part | Content |
| --- | --- |
| **Lead** | The answer, command, path, or next action. The first line. |
| **Steps** | Numbered, one bounded action per item |
| **Detail** | Only what is needed to act on the lead or to trust it |
| **State** | During multi-step work: `Done: X. Next: Y.` |

The form follows the content:

| Content | Form |
| --- | --- |
| Steps in order | Numbered list |
| Choices to pick from, or items you will refer back to | Numbered list, so you can reply "2" |
| Three or more items compared on two or more attributes | Table |
| Parallel items with no order | Bullets, at most five per group |
| Progress across several items | Task list (`- [x]`, `- [ ]`) |
| Terms with meanings, fields with values | Bullets with a bold label |
| Anything you will run or paste | Code block with a language tag |
| A change to existing code | `diff` block, or new lines with `file:line` |
| Logs, error output, a directory tree | Code block, verbatim and trimmed |
| Quoted words | Blockquote |
| A single fact, two items, or reasoning | Sentences |
| Sections of a long explanation | Headers |

Inline: code for commands, paths, and identifiers; bold for the one term you scan for; links with descriptive text. No headers on short answers, no one-item lists, no nested bullets, no italics for emphasis, no horizontal rules. The ceiling is one terminal screen, unless you ask to be walked through something.

## The rules

Ten rules. Full text with good/bad examples in [SKILL.md](skills/concise/SKILL.md).

1. Lead with the answer. Yes/no questions get "Yes" or "No" first.
2. Match length to the question.
3. Pick the form that fits.
4. Number multi-step work.
5. One topic per response.
6. Restate state and end with one next action, only while work is open.
7. Use concrete numbers. Never invent one.
8. Show results, not effort.
9. Errors: location, cause, fix.
10. Plain words, no filler: no preamble, no recap, no closers, no telegraphic compression.

The rules change presentation only, never how much analysis or work gets done. They apply in whatever language you write in, and to what Claude writes for you: pull request descriptions, commit messages, issues, and review comments. A repository template or convention outranks them. Safety still wins: destructive actions get a confirmation, "explain this" gets a full explanation, real ambiguity gets one question.

## How it works

| File | Role |
| --- | --- |
| `skills/concise/SKILL.md` | The ruleset. `/concise` loads it into the session. |
| `hooks/hooks.json`, `hooks/always-on.mjs` | `SessionStart` hook (startup, resume, clear, compact). When the always-on flag exists it re-injects the ruleset, so the mode survives compaction in long sessions. |
| `commands/*.md` | `/concise:off`, `:always-on`, `:always-off`, `:status`. |
| `hooks/always-on-flag.mjs` | The only code that creates or deletes the flag file. |

Needs Node.js on `PATH` for the hook and the `always-*` commands. Without it the hook fails silently and `/concise` still works per session.

## Customize

Fork, edit `skills/concise/SKILL.md`, then point Claude Code at your fork:

```bash
claude plugin uninstall concise
claude plugin marketplace remove concise
claude plugin marketplace add <you>/<your-fork>
claude plugin install concise@concise
```

Restart Claude Code, then `/concise`.

Tests and contribution rules are in [CONTRIBUTING.md](CONTRIBUTING.md).

## Acknowledgements

concise is a fork of [i-have-adhd](https://github.com/ayghri/i-have-adhd) by [Ayoub Ghriss](https://github.com/ayghri). The ten rules descend from that work, with thanks. They help any reader, so this fork generalizes them: it is for anyone who wants concise, structured output, whatever the reason. It also narrows the scope to Claude Code and adds the response shape and the command set. For the original, with adapters for a dozen other runtimes and translations in ten languages, use i-have-adhd.

## License

[MIT](LICENSE). Original work © Ayoub Ghriss. Modifications © Kota Mizushima.
