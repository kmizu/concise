import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "hooks" / "always-on-flag.mjs"
NODE = shutil.which("node")


@unittest.skipUnless(NODE, "node is not available")
class AlwaysOnFlagScriptTest(unittest.TestCase):
    """hooks/always-on-flag.mjs: the only writer of the always-on flag file."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.config_dir = Path(self.temp_dir.name) / "claude config"
        self.config_dir.mkdir()
        self.flag = self.config_dir / ".concise-always"

    def run_script(self, *args, config_dir=None):
        env = os.environ.copy()
        env["CLAUDE_CONFIG_DIR"] = str(config_dir or self.config_dir)
        return subprocess.run(
            [NODE, str(SCRIPT), *args],
            check=False,
            capture_output=True,
            text=True,
            env=env,
        )

    def test_status_reports_disabled_without_flag(self):
        result = self.run_script("status")
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertIn("always-on: disabled", result.stdout)
        self.assertFalse(self.flag.exists())

    def test_on_creates_flag_and_is_idempotent(self):
        for _ in range(2):
            result = self.run_script("on")
            self.assertEqual(0, result.returncode, result.stderr)
            self.assertEqual("", result.stderr)
            self.assertIn("always-on: enabled", result.stdout)
        self.assertTrue(self.flag.is_file())
        self.assertEqual(0, self.flag.stat().st_size)
        self.assertIn("always-on: enabled", self.run_script("status").stdout)

    def test_off_removes_flag_and_is_idempotent(self):
        self.flag.touch()
        for _ in range(2):
            result = self.run_script("off")
            self.assertEqual(0, result.returncode, result.stderr)
            self.assertIn("always-on: disabled", result.stdout)
        self.assertFalse(self.flag.exists())

    def test_on_does_not_create_a_missing_config_dir(self):
        # Writes are scoped to an existing Claude config dir; never mkdir into
        # an arbitrary path that CLAUDE_CONFIG_DIR happens to point at.
        missing = Path(self.temp_dir.name) / "missing"
        result = self.run_script("on", config_dir=missing)
        self.assertEqual(1, result.returncode)
        self.assertIn("not enabled", result.stdout)
        self.assertFalse(missing.exists())

    def test_unknown_action_is_rejected(self):
        result = self.run_script("bogus")
        self.assertEqual(2, result.returncode)
        self.assertIn("unknown action", result.stdout)
        self.assertFalse(self.flag.exists())

    def test_only_the_flag_file_is_written(self):
        before = {p.name for p in self.config_dir.iterdir()}
        self.run_script("on")
        after = {p.name for p in self.config_dir.iterdir()}
        self.assertEqual({".concise-always"}, after - before)

    def test_flag_created_by_on_activates_the_session_start_hook(self):
        self.assertEqual(0, self.run_script("on").returncode)
        env = os.environ.copy()
        env["CLAUDE_CONFIG_DIR"] = str(self.config_dir)
        hook = subprocess.run(
            [NODE, str(ROOT / "hooks" / "always-on.mjs")],
            check=False,
            capture_output=True,
            text=True,
            env=env,
        )
        self.assertEqual(0, hook.returncode, hook.stderr)
        self.assertIn("CONCISE MODE ACTIVE (always-on)", hook.stdout)


if __name__ == "__main__":
    unittest.main()
