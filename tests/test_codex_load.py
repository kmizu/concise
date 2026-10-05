"""Real Codex load check when available. Uses a temporary CODEX_HOME and checkout."""

import json
import os
import queue
import shutil
import subprocess
import tempfile
import threading
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CODEX = shutil.which("codex")


@unittest.skipUnless(CODEX, "codex is not available for the native load check")
class CodexLoadTest(unittest.TestCase):
    def test_install_separate_package_in_scratch_home(self):
        with tempfile.TemporaryDirectory(prefix="concise codex ") as temp:
            scratch = Path(temp)
            checkout = scratch / "marketplace with spaces"
            checkout.mkdir()
            shutil.copytree(ROOT / "codex/concise", checkout / "codex/concise")
            catalog = checkout / ".agents/plugins/marketplace.json"
            catalog.parent.mkdir(parents=True)
            shutil.copyfile(ROOT / ".agents/plugins/marketplace.json", catalog)
            home = scratch / "codex home"
            home.mkdir()
            env = os.environ.copy()
            env["CODEX_HOME"] = str(home)

            def run(*args):
                result = subprocess.run(
                    [CODEX, *args], cwd=checkout, env=env,
                    capture_output=True, text=True, check=False, timeout=60,
                )
                self.assertEqual(0, result.returncode, result.stdout + result.stderr)
                return json.loads(result.stdout)

            run("plugin", "marketplace", "add", str(checkout), "--json")
            installed = run("plugin", "add", "concise@concise-codex", "--json")
            listed = run("plugin", "list", "--marketplace", "concise-codex", "--json")
            self.assertEqual("concise@concise-codex", installed["pluginId"])
            plugin, = listed["installed"]
            self.assertEqual(installed["pluginId"], plugin["pluginId"])
            self.assertTrue(plugin["installed"])
            self.assertTrue(plugin["enabled"])
            cached = Path(installed["installedPath"])
            self.assertTrue(cached.resolve().is_relative_to(home.resolve()))
            for path in (ROOT / "codex/concise").rglob("*"):
                if path.is_file():
                    self.assertEqual(path.read_bytes(), (cached / path.relative_to(ROOT / "codex/concise")).read_bytes())

            # Discovery is checked through the host, not just by listing files.
            server = subprocess.Popen(
                [CODEX, "app-server"], cwd=checkout, env=env,
                stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                text=True, encoding="utf8",
            )
            messages = queue.Queue()

            def read_messages():
                for line in server.stdout:
                    messages.put(json.loads(line))

            reader = threading.Thread(target=read_messages, daemon=True)
            reader.start()

            def send(message):
                server.stdin.write(json.dumps(message) + "\n")
                server.stdin.flush()

            def request(identifier, method, params):
                send({"id": identifier, "method": method, "params": params})
                while True:
                    message = messages.get(timeout=30)
                    if message.get("id") == identifier:
                        self.assertNotIn("error", message, message)
                        return message["result"]

            try:
                request(1, "initialize", {
                    "clientInfo": {"name": "concise-load-check", "version": "1.0.0"},
                    "capabilities": {"experimentalApi": True},
                })
                send({"method": "initialized", "params": {}})
                skills = request(2, "skills/list", {"cwds": [str(checkout)], "forceReload": True})
                entry, = skills["data"]
                self.assertEqual([], entry["errors"])
                loaded = {skill["name"]: skill for skill in entry["skills"]
                          if skill.get("pluginId") == installed["pluginId"]}
                self.assertEqual({"concise:concise", "concise:concise-off"}, set(loaded))
                for name, skill in loaded.items():
                    self.assertTrue(skill["enabled"])
                    path = Path(skill["path"])
                    self.assertTrue(path.resolve().is_relative_to(cached.resolve()))
                    self.assertIn("$" + name, skill["interface"]["defaultPrompt"])
            finally:
                server.terminate()
                server.wait(timeout=10)
                reader.join(timeout=10)
                server.stdin.close()
                server.stdout.close()
