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
  <a href="LICENSE"><img src="https://img.shields.io/github/license/kmizu/concise?style=flat" alt="License"></a>
  <img src="https://img.shields.io/badge/claude%20code-plugin-0F172A?style=flat" alt="Claude Code plugin">
</p>

## Install

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

The same prompt, answered without and with the plugin. Real output from `claude -p` with no user settings, concise 0.3.1 always-on, generated on 2026-10-05. One run each, unedited except that headers inside an answer are shown as bold lines.

### A fix

The fix moves to the first line and the reason follows it.

<details>
<summary>The prompt</summary>

````text
My Docker build reinstalls every npm package whenever I change a source file, so each build takes minutes. Why, and how do I fix it? Here is my Dockerfile:

FROM node:22-slim
WORKDIR /app
COPY . .
RUN npm ci
RUN npm run build
CMD ["node", "dist/server.js"]
````

</details>

<table>
<tr>
<th width="50%">Before</th>
<th width="50%">After</th>
</tr>
<tr>
<td valign="top">

**Why it happens:** Docker caches each instruction as a layer. A layer gets reused only if nothing it depends on has changed. `COPY . .` copies your whole project, source files included. So any source edit invalidates that layer, and every layer after it gets rebuilt too, including `RUN npm ci`.

**Fix:** Copy only the dependency manifests first and install, then copy the rest:

```dockerfile
FROM node:22-slim
WORKDIR /app

# Only changes to these files invalidate the install layer
COPY package.json package-lock.json ./
RUN npm ci

# Source changes only invalidate layers from here down
COPY . .
RUN npm run build

CMD ["node", "dist/server.js"]
```

Now `npm ci` reruns only when `package.json` or `package-lock.json` changes. Ordinary code edits reuse the cached `node_modules` layer.

**Also add a `.dockerignore`.** Without one, `COPY . .` sends your local `node_modules` into the image, where it can overwrite the clean install. It also sends files like `.git`, which change often and break the cache for no reason:

```
node_modules
dist
.git
npm-debug.log
```

**Optional improvements:**

- **Cache mount:** Even when the lockfile changes, this lets npm reuse its download cache instead of fetching everything again (needs BuildKit, which is the default in current Docker):
  ```dockerfile
  RUN --mount=type=cache,target=/root/.npm npm ci
  ```
- **Multi-stage build:** This keeps devDependencies and build tools out of the final image:
  ```dockerfile
  FROM node:22-slim AS build
  WORKDIR /app
  COPY package.json package-lock.json ./
  RUN npm ci
  COPY . .
  RUN npm run build

  FROM node:22-slim
  WORKDIR /app
  COPY package.json package-lock.json ./
  RUN npm ci --omit=dev
  COPY --from=build /app/dist ./dist
  CMD ["node", "dist/server.js"]
  ```

The reordering alone should bring rebuilds after a code change down from minutes to roughly the time `npm run build` takes.

</td>
<td valign="top">

Copy `package.json` and `package-lock.json` first, run `npm ci`, and only then copy the rest of the source:

```dockerfile
FROM node:22-slim
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
RUN npm run build
CMD ["node", "dist/server.js"]
```

The cause is Docker's layer cache. Docker reuses a layer only if that step's inputs haven't changed. Right now `COPY . .` comes before `npm ci`, so editing any source file invalidates the cache for that copy and every step after it, including the install. With the new order, `npm ci` reruns only when one of the two package files changes.

Also add a `.dockerignore` that lists `node_modules` and `dist`. Without it, `COPY . .` sends your local `node_modules` into the build context, which slows the build and overwrites the modules you just installed.

</td>
</tr>
</table>

### A yes/no question

Both say "Yes" first. concise stops once you can act on it.

> Can I use top-level await in an ES module on Node 20?

<table>
<tr>
<th width="50%">Before</th>
<th width="50%">After</th>
</tr>
<tr>
<td valign="top">

Yes. Node has supported top-level `await` in ES modules without a flag since v14.8, so Node 20 handles it fine. The file has to be loaded as an ES module, which means either:

- the file uses the `.mjs` extension, or
- the nearest `package.json` has `"type": "module"` (and the file is `.js`).

```js
// index.mjs
const res = await fetch("https://example.com");
console.log(res.status);
```

Some things to watch for:

- **CommonJS doesn't support it.** Using top-level `await` in a `.cjs` file or a CommonJS `.js` file causes a `SyntaxError`. In that case, wrap the code in an async function or switch the file to ESM.
- **The REPL and `--eval` are different.** The REPL lets you use `await` at the top level. With `node -e`, you need `--input-type=module`.
- **`require()` of a module that uses it fails.** Node 20.19+ can `require()` ES modules, but not ones that use top-level `await`. Those throw `ERR_REQUIRE_ASYNC_MODULE`, so load them with `import` or `import()` instead.
- **Imports wait for it.** Any module that imports one using top-level `await` doesn't run until that `await` settles.

Also, Node 20 reached end-of-life in April 2026, so it no longer gets security patches. For anything you'll keep running, it's worth moving to Node 22 or 24 (both LTS). Top-level `await` works the same way on both.

</td>
<td valign="top">

Yes. Node 20 supports top-level `await` in ES modules without any flag. It has been stable since Node 14.8.

The file has to be treated as ESM, which means either of these:

1. Use the `.mjs` extension.
2. Set `"type": "module"` in `package.json`.

```js
// index.mjs
const res = await fetch("https://example.com");
console.log(res.status);
```

Top-level `await` does not work in CommonJS (`.cjs` files, or `.js` files without `"type": "module"`).

</td>
</tr>
</table>

### A question about options

Options are numbered, recommendation first, so you can reply "2".

> What are my options for running a Python script every hour on a Linux server?

<table>
<tr>
<th width="50%">Before</th>
<th width="50%">After</th>
</tr>
<tr>
<td valign="top">

Here are the main options, roughly from most to least common.

**1. cron (simplest)**
```bash
crontab -e
```
```cron
0 * * * * /usr/bin/python3 /path/to/script.py >> /var/log/myscript.log 2>&1
```
- It's on almost every system, and the setup is one line.
- Use absolute paths. cron runs with a minimal environment and a different `PATH`.
- If you use a virtualenv, point to its interpreter: `/path/to/venv/bin/python`.
- Downsides: no logging unless you redirect output yourself, and nothing stops two runs from overlapping. To prevent overlap, wrap the command in `flock -n /tmp/myscript.lock ...`.

**2. systemd timers (best default on modern distros)**
`/etc/systemd/system/myscript.service`:
```ini
[Unit]
Description=My hourly script

[Service]
Type=oneshot
User=myuser
WorkingDirectory=/path/to
ExecStart=/path/to/venv/bin/python /path/to/script.py
```
`/etc/systemd/system/myscript.timer`:
```ini
[Unit]
Description=Run myscript hourly

[Timer]
OnCalendar=hourly
Persistent=true
RandomizedDelaySec=60

[Install]
WantedBy=timers.target
```
```bash
sudo systemctl daemon-reload
sudo systemctl enable --now myscript.timer
systemctl list-timers            # check the schedule
journalctl -u myscript.service   # view the logs
```
- Logging goes to journald automatically, and runs can't overlap because a oneshot service won't start again while it's still running.
- `Persistent=true` catches up on runs missed while the server was down.
- You also get resource limits, dependencies, and failure hooks (`OnFailure=`).
- The trade-off is two files instead of one line.

**3. A long-running Python process with an internal scheduler**
You can use something like `APScheduler` or `schedule`, or a simple `while True: ...; sleep(3600)` loop, and run it under systemd or supervisor.
- This makes sense if the job needs shared in-memory state or you already have a daemon running.
- It drifts over time and dies if the process crashes, so you need a supervisor to restart it.

**4. Heavier orchestration (only if you need it)**
- **Airflow, Prefect, or Dagster**: for job dependencies, retries, a UI, and history.
- **Celery beat**: if you already use Celery.
- **Kubernetes CronJob**: if the server is part of a k8s cluster.
- **anacron**: for machines that aren't always on. Its finest schedule is daily, so it doesn't fit hourly jobs.

**Recommendation**
- Use a **systemd timer** if this is a real production job. Built-in logging, overlap protection, and catching up on missed runs are worth the two small files.
- Use **cron** for something quick and personal.

In both cases, make the script safe to run twice, and have it exit with a non-zero code when it fails so the scheduler and logs show the failure.

</td>
<td valign="top">

1. **cron** (recommended for most cases): built in, one line, nothing else to install. It skips missed runs while the server is down and gives no logging unless you add it.
   ```bash
   crontab -e
   # Runs at minute 0 of every hour; output is appended to a log file
   0 * * * * /usr/bin/python3 /path/to/script.py >> /var/log/script.log 2>&1
   ```
2. **systemd timer**: you get logs in `journalctl`, a missed run can fire after a reboot (`Persistent=true`), and overlapping runs are prevented. You write two unit files (`.service` and `.timer`) with `OnCalendar=hourly`.
3. **A long-running Python loop** (the `schedule` or `APScheduler` libraries): all scheduling stays in code. You have to keep the process alive yourself with systemd or supervisor, and a crash stops every future run.
4. **A container or orchestrator scheduler** (Kubernetes CronJob, Airflow): worth it only if you already run that platform or need retries, dependencies between jobs, and a dashboard.

Use absolute paths in cron. Cron runs with a minimal environment, so point it at the virtualenv interpreter directly, for example `/path/to/venv/bin/python`.

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

The rules change presentation only, never how much analysis or work gets done. They apply in whatever language you write in, and to what Claude writes for you: pull request titles and descriptions, commit messages, issues, review comments, status updates, etc. A repository template or convention outranks them. Safety still wins: destructive actions get a confirmation, "explain this" gets a full explanation, real ambiguity gets one question.

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
