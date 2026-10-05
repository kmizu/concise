import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
NODE = shutil.which("node")


@unittest.skipUnless(NODE, "node is not available")
class AlwaysOnHookTest(unittest.TestCase):
    """hooks/always-on.mjs: silent without the flag, injects the ruleset with it."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        # Paths with spaces catch quoting mistakes in the hooks.json launcher.
        self.plugin_root = Path(self.temp_dir.name) / "plugin with spaces"
        shutil.copytree(ROOT / "hooks", self.plugin_root / "hooks")
        shutil.copytree(ROOT / "skills", self.plugin_root / "skills")
        self.config_dir = Path(self.temp_dir.name) / "claude config"
        self.config_dir.mkdir()
        self.flag = self.config_dir / ".concise-always"

    def env(self, plugin_root=None):
        env = os.environ.copy()
        env["CLAUDE_CONFIG_DIR"] = str(self.config_dir)
        env["CLAUDE_PLUGIN_ROOT"] = str(plugin_root or self.plugin_root)
        return env

    def run_hook(self):
        return subprocess.run(
            [NODE, str(self.plugin_root / "hooks" / "always-on.mjs")],
            check=False,
            capture_output=True,
            text=True,
            env=self.env(),
        )

    def run_launcher(self, plugin_root=None):
        # Run the exact command Claude Code runs, as declared in hooks.json.
        config = json.loads((ROOT / "hooks" / "hooks.json").read_text(encoding="utf8"))
        hook = config["hooks"]["SessionStart"][0]["hooks"][0]
        return subprocess.run(
            hook["command"],
            check=False,
            capture_output=True,
            text=True,
            shell=True,
            env=self.env(plugin_root),
            input=json.dumps(
                {
                    "session_id": "test-session",
                    "cwd": str(self.plugin_root),
                    "hook_event_name": "SessionStart",
                    "source": "startup",
                }
            ),
        )

    def test_hook_is_silent_without_flag(self):
        result = self.run_hook()
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual("", result.stdout)
        self.assertEqual("", result.stderr)

    def test_hook_injects_ruleset_without_frontmatter_when_flag_exists(self):
        self.flag.touch()
        result = self.run_hook()
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual("", result.stderr)
        self.assertIn("CONCISE MODE ACTIVE (always-on)", result.stdout)
        self.assertIn("/concise:off", result.stdout)
        self.assertIn(str(self.flag), result.stdout)
        self.assertIn("(rules", result.stdout)
        self.assertNotIn("Derived from", result.stdout)
        self.assertNotIn("disable-model-invocation", result.stdout)

    def test_hook_output_stays_under_the_context_limit(self):
        # Claude Code injects only a 2 KB preview of hook output that is "too
        # large" (seen at 10.1 KB); the rest goes to a file the model does not
        # read. Above the limit, always-on silently loses the rules.
        self.flag.touch()
        result = self.run_hook()
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertIn("(pre-send-check", result.stdout)
        self.assertLess(len(result.stdout.encode("utf8")), 10_000)

    def test_hook_strips_frontmatter_with_trailing_whitespace(self):
        skill = self.plugin_root / "skills" / "concise" / "SKILL.md"
        skill.write_text("---   \nname: fixture\n--- \t\nFixture body.\n", encoding="utf8")
        self.flag.touch()
        result = self.run_hook()
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertNotIn("name: fixture", result.stdout)
        self.assertIn("\n\nFixture body.\n", result.stdout.replace("\r\n", "\n"))

    def test_hook_keeps_content_when_frontmatter_is_unclosed(self):
        # An opening --- with no closing delimiter is not frontmatter. Keeping
        # the file beats a banner that promises "the ruleset below" and nothing.
        skill = self.plugin_root / "skills" / "concise" / "SKILL.md"
        skill.write_text("---\nname: fixture\nFixture body, fence never closed.\n", encoding="utf8")
        self.flag.touch()
        result = self.run_hook()
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertIn("Fixture body, fence never closed.", result.stdout)

    def test_hook_is_silent_when_skill_is_missing(self):
        shutil.rmtree(self.plugin_root / "skills")
        self.flag.touch()
        result = self.run_hook()
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual("", result.stdout)

    def test_launcher_runs_the_hook(self):
        self.flag.touch()
        result = self.run_launcher()
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual("", result.stderr)
        self.assertIn("CONCISE MODE ACTIVE (always-on)", result.stdout)

    def test_launcher_is_silent_without_flag(self):
        result = self.run_launcher()
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual("", result.stdout)
        self.assertEqual("", result.stderr)

    def test_launcher_swallows_missing_plugin_root(self):
        result = self.run_launcher(self.plugin_root / "missing plugin")
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual("", result.stdout)
        self.assertEqual("", result.stderr)

    def test_launcher_resolves_the_module_from_the_plugin_root(self):
        config = json.loads((ROOT / "hooks" / "hooks.json").read_text(encoding="utf8"))
        hook = config["hooks"]["SessionStart"][0]["hooks"][0]
        self.assertEqual("command", hook["type"])
        self.assertNotIn("args", hook)
        self.assertIn("process.env.CLAUDE_PLUGIN_ROOT", hook["command"])
        self.assertIn("always-on.mjs", hook["command"])
        self.assertIn(".catch", hook["command"])
        self.assertEqual("startup|resume|clear|compact", config["hooks"]["SessionStart"][0]["matcher"])


class RulesetSyntaxTest(unittest.TestCase):
    """skills/concise/SKILL.md holds the ruleset as one balanced S-expression."""

    def test_ruleset_s_expression_is_balanced(self):
        text = (ROOT / "skills" / "concise" / "SKILL.md").read_text(encoding="utf8")
        self.assertEqual(1, text.count("```lisp"))
        code = text.split("```lisp", 1)[1].split("```", 1)[0]
        depth, in_string, escaped = 0, False, False
        for char in code:
            if in_string:
                if escaped:
                    escaped = False
                elif char == "\\":
                    escaped = True
                elif char == '"':
                    in_string = False
            elif char == '"':
                in_string = True
            elif char == "(":
                depth += 1
            elif char == ")":
                depth -= 1
                self.assertGreaterEqual(depth, 0, "unmatched closing parenthesis")
        self.assertFalse(in_string, "unterminated string")
        self.assertEqual(0, depth, "unclosed parenthesis")
        self.assertEqual(10, code.count("(rule "))


if __name__ == "__main__":
    unittest.main()
