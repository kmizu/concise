# concise for Codex

Structured, concise answers: the answer first, numbered steps, and no filler.
This is a separate skills-only package. The Claude Code package remains at the
repository root.

## Install from the checkout

Run these commands at the root of the `kmizu/concise` checkout with a Codex CLI
that provides `codex plugin add`:

```bash
codex plugin marketplace add .
codex plugin add concise@concise-codex
codex plugin list --marketplace concise-codex --json
```

The repo marketplace is `.agents/plugins/marketplace.json`. Its source points
at `./codex/concise`, independently of the Claude Code marketplace. In the
desktop app, refresh or restart after adding the marketplace, then find
**Concise** under **Concise for Codex** in the Plugins Directory and install it.
Start a new conversation after installation.

## Use

Invoke the skill explicitly in the composer (choose the Concise skill if the
host shows a picker):

```text
$concise:concise
```

Concise mode applies to subsequent responses in that conversation until:

```text
$concise:concise-off
```

Saying "stop concise mode" or "normal mode" also turns it off. These skills
are instructions for the model; activation persists in conversation context,
not in a configuration file. They change presentation, not the amount of work
or verification. Higher-priority instructions and repository templates still
apply. Both skills disable implicit invocation.

This package provides conversation on/off controls. Claude Code's
`/concise:always-on`, `/concise:always-off`, and `/concise:status` are not included.
There are no hooks, MCP servers, dependencies, or flag-file writes.

## Build and verify

From the repository root, with Python 3.10 or later:

```bash
python scripts/build_codex.py
python scripts/build_codex.py --check
python -m unittest discover -s tests -v
```

The build writes `codex/concise/` and `dist/concise-codex-<version>.zip`.
The ZIP contains one self-contained `concise/` folder, including a portable
`plugin.json`, a `.codex-plugin/plugin.json` compatibility manifest, both skills,
the logo, this README, and the MIT license. Generated files are checked into
the repository; edit the canonical `skills/concise/SKILL.md` to change the ten
rules, then rebuild. Only the off-switch syntax is adapted for Codex.

To install an extracted ZIP from a local marketplace, put the `concise/`
folder in a new directory and create `.agents/plugins/marketplace.json`
alongside it:

```json
{
  "name": "concise-codex",
  "interface": { "displayName": "Concise for Codex" },
  "plugins": [{
    "name": "concise",
    "source": { "source": "local", "path": "./concise" },
    "policy": { "installation": "AVAILABLE", "authentication": "ON_INSTALL" },
    "category": "Productivity"
  }]
}
```

Run the installation commands above from that new directory. The builder and
tests belong to the source checkout and are not included in the plugin ZIP.

## Package format

Follows OpenAI's [plugin packaging documentation](https://developers.openai.com/plugins/build/plugins).
It includes both the portable manifest and the compatibility manifest for
Codex clients. Installation and discovery checks do not prove that every model
response will follow every presentation rule.

## Credit

Derived from [i-have-adhd](https://github.com/ayghri/i-have-adhd) by Ayoub Ghriss
(MIT). The ten rules descend from that skill; the framing and response shape
come from concise by Kota Mizushima.
