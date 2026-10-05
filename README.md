<p align="center">
  <img src="logo.svg" alt="concise" width="120" />
</p>
<h1 align="center">concise</h1>
<p align="center">
  <strong>Structured, concise answers from Claude Code and Codex.</strong><br/>
  Answer first. Steps numbered. Nothing to scroll past.
</p>
<p align="center">
  <sub>A fork of <a href="https://github.com/ayghri/i-have-adhd">i-have-adhd</a>, generalized for anyone who wants concise output.</sub>
</p>
<p align="center">
  <a href="LICENSE"><img src="https://img.shields.io/github/license/kmizu/concise?style=flat" alt="License"></a>
  <img src="https://img.shields.io/badge/claude%20code-plugin-0F172A?style=flat" alt="Claude Code plugin">
  <img src="https://img.shields.io/badge/codex-plugin-0F172A?style=flat" alt="Codex plugin">
</p>

[Claude Code users](#claude-code-users) · [Codex users](#codex-users)

## Claude Code users

### Install

```bash
claude plugin marketplace add kmizu/concise
claude plugin install concise@concise
```

Then, inside Claude Code: `/concise`.

Update later with:

```bash
claude plugin marketplace update concise
claude plugin update concise@concise
```

### Commands

| Command | Scope | What it does |
| --- | --- | --- |
| `/concise` | This session | Apply the ruleset to every response until you turn it off |
| `/concise:off` | This session | Back to Claude's default style |
| `/concise:always-on` | Every session | Load the ruleset at session start, no command needed |
| `/concise:always-off` | Every session | Undo always-on; the current session is unchanged |
| `/concise:status` | | Is always-on enabled, and where the flag file lives |

Always-on is a single empty file, `~/.claude/.concise-always` (`$CLAUDE_CONFIG_DIR/.concise-always` if you set one). Installing the plugin writes nothing. `/concise:always-on` writes that one file, `/concise:always-off` deletes it. Saying "stop concise mode" does the same as `/concise:off`.

### Output style (per project, no hook)

The same ruleset also ships as a Claude Code output style. Select it once in a
project and it stays selected for that project:

```text
/output-style concise:concise
```

`/output-style default` turns it off. The choice is stored by Claude Code in
`.claude/settings.local.json`; the plugin writes nothing. The style keeps
Claude Code's own coding instructions and only changes presentation. Use it
instead of always-on when you want the mode scoped to one project, or when
Node.js is not available for the hook. Claude Code also has a built-in style
named "Concise"; this one is `concise:concise`.

### How it works

| File | Role |
| --- | --- |
| `skills/concise/SKILL.md` | The ruleset, written in a small bracket notation (`[tag attrs]{body}`) so it is short and unambiguous. `/concise` loads it into the session. |
| `output-styles/concise.md` | The same ruleset as an output style, generated from `SKILL.md` by `scripts/build_output_style.py`; selected with `/output-style concise:concise`. |
| `hooks/hooks.json`, `hooks/always-on.mjs` | `SessionStart` hook (startup, resume, clear, compact). When the always-on flag exists it re-injects the ruleset, so the mode survives compaction in long sessions. |
| `commands/*.md` | `/concise:off`, `:always-on`, `:always-off`, `:status`. |
| `hooks/always-on-flag.mjs` | The only code that creates or deletes the flag file. |

Needs Node.js on `PATH` for the hook and the `always-*` commands. Without it the hook fails silently and `/concise` still works per session.

### Customize

Fork, edit `skills/concise/SKILL.md`, then point Claude Code at your fork:

```bash
claude plugin uninstall concise
claude plugin marketplace remove concise
claude plugin marketplace add <you>/<your-fork>
claude plugin install concise@concise
```

Restart Claude Code, then `/concise`.

## Codex users

### Install

Run these commands with a Codex CLI that provides `codex plugin add`
(tested with Codex CLI 0.160.0). No checkout or build is needed:

```bash
codex plugin marketplace add kmizu/concise --ref main
codex plugin add concise@concise-codex
```

Start a new Codex conversation after installation.

Check installation with:

```bash
codex plugin list --marketplace concise-codex --json
```

### Use

| Skill | Scope | What it does |
| --- | --- | --- |
| `$concise:concise` | This conversation | Apply the ruleset to every response until you turn it off |
| `$concise:concise-off` | This conversation | Return to the default response style |

Saying "stop concise mode" or "normal mode" also turns it off. Activation stays
in conversation context; there are no hooks, persistent settings, or always-on
controls in the Codex package.

### Package and customization

The separate package is in `codex/concise/`. Its rules are generated from the
canonical `skills/concise/SKILL.md`, with the off-switch adapted for Codex.
For desktop installation, local checkouts, ZIP packages, and rebuilding after
customizing the rules, see the [Codex package guide](codex/README.md).

## What changes

<table>
<tr>
<td width="50%">

## Before

> Great question! Docker build performance can depend on a lot of factors. Looking at your Dockerfile, I notice that you're copying the entire project directory before running `npm ci`, which means that any change to any file invalidates the layer cache and forces a full reinstall of dependencies. One approach would be to copy `package.json` and `package-lock.json` first, run the install, and then copy the rest. You might also want to add a `.dockerignore` file to exclude `node_modules` and other large directories. Hope this helps! Let me know if you'd like me to make these changes.

</td>
<td width="50%">

## After

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

Concise means fewer sentences, not compressed ones. Structured means the form matches the content, not more formatting. A simple fact gets a short answer; a complex task gets the detail needed to cover it, even when the question is one line. Accuracy, requested coverage, and material uncertainty come before brevity. Responses use these parts only when they carry information:

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

Inline: code for commands, paths, and identifiers; bold for the one term you scan for; links with descriptive text. No headers on short answers, no one-item lists, no nested bullets, no italics for emphasis, no horizontal rules. One terminal screen is a target; necessary detail and explanations can go longer.

## The rules

Ten rules. The full ruleset, with good/bad examples, is in [SKILL.md](skills/concise/SKILL.md).

1. Lead with the supported answer, including uncertainty when the evidence is incomplete.
2. Match length to the task.
3. Pick the form that fits.
4. Number multi-step work.
5. Stay within the task; cover every requested topic and authorized fix.
6. Restate state and end with one next action, only while work is open.
7. Use concrete numbers. Never invent one.
8. Show results, not effort.
9. Errors: location, cause, fix.
10. Plain words, no filler: no preamble, no recap, no closers, no telegraphic compression.

The rules change presentation only, never how much analysis or work gets done. They apply in whatever language you write in, and to what the assistant writes for you: pull request titles and descriptions, commit messages, issues, review comments, status updates, etc. A repository template or convention outranks them. Continue routine, reversible work within an authorized task without asking again. Destructive actions still get confirmation; missing information that changes correctness, scope, or a consequential action gets one focused question.

## Evaluation

The [response evaluation suite](evals/README.md) compares actual answers with no
concise rules, version 0.4.0, and version 0.5.0. It reports semantic review and
character counts separately: a shorter answer that omits necessary information
does not pass. The [pilot report](evals/PILOT.md) records the results and their
limits; it is a small scenario study, not proof of improvement across models.

Tests and contribution rules are in [CONTRIBUTING.md](CONTRIBUTING.md).

## Acknowledgements

concise is a fork of [i-have-adhd](https://github.com/ayghri/i-have-adhd) by [Ayoub Ghriss](https://github.com/ayghri). The ten rules descend from that work, with thanks. They help any reader, so this fork generalizes them: it is for anyone who wants concise, structured output, whatever the reason. It provides separate packages for Claude Code and Codex and adds the response shape and activation controls. For the original, with adapters for a dozen other runtimes and translations in ten languages, use i-have-adhd.

## License

[MIT](LICENSE). Original work © Ayoub Ghriss. Modifications © Kota Mizushima.
