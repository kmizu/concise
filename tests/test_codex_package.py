import importlib.util
import json
import re
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "codex" / "concise"
BUILDER = ROOT / "scripts" / "build_codex.py"


class CodexPackageTest(unittest.TestCase):
    def test_generated_files_are_current(self):
        self.assertTrue(BUILDER.is_file(), "Codex package builder is missing")
        result = subprocess.run(
            [sys.executable, str(BUILDER), "--check"],
            capture_output=True, text=True, check=False,
        )
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)

    def test_rules_match_the_canonical_skill_with_only_the_off_switch_adapted(self):
        self.assertTrue((PACKAGE / "skills/concise/SKILL.md").is_file(), "Codex skill is missing")
        canonical = (ROOT / "skills/concise/SKILL.md").read_text(encoding="utf8")
        codex = (PACKAGE / "skills/concise/SKILL.md").read_text(encoding="utf8")
        expected = canonical.split("```text\n", 1)[1].split("\n```", 1)[0]
        actual = codex.split("```text\n", 1)[1].split("\n```", 1)[0]
        self.assertEqual(expected.replace("/concise:off", "$concise:concise-off"), actual)
        self.assertEqual(list(range(1, 11)), [int(n) for n in re.findall(r"\[rule (\d+) ", actual)])
        self.assertEqual(actual.count("{"), actual.count("}"))
        self.assertNotIn("/concise:off", codex)
        self.assertNotIn("Invoke with /concise", codex)
        self.assertNotIn("disable-model-invocation", codex)

    def test_native_and_portable_manifests_agree(self):
        self.assertTrue((PACKAGE / "plugin.json").is_file(), "Codex manifest is missing")
        portable = json.loads((PACKAGE / "plugin.json").read_text(encoding="utf8"))
        native = json.loads((PACKAGE / ".codex-plugin/plugin.json").read_text(encoding="utf8"))
        claude = json.loads((ROOT / ".claude-plugin/plugin.json").read_text(encoding="utf8"))
        for key in ("name", "version", "author", "license", "description"):
            self.assertEqual(portable[key], native[key])
        self.assertEqual(claude["version"], portable["version"])
        self.assertEqual("./skills/", native["skills"])
        self.assertNotIn("skills", portable)
        self.assertEqual(portable["extensions"]["com.openai"]["interface"], native["interface"])
        self.assertLessEqual(len(native["interface"]["shortDescription"]), 30)
        for key in ("logo", "composerIcon"):
            path = native["interface"][key]
            self.assertTrue(path.startswith("./"))
            self.assertTrue((PACKAGE / path).resolve().is_relative_to(PACKAGE.resolve()))
            self.assertTrue((PACKAGE / path).is_file())

    def test_marketplace_resolves_to_the_separate_package(self):
        catalog = ROOT / ".agents/plugins/marketplace.json"
        self.assertTrue(catalog.is_file(), "Codex marketplace is missing")
        marketplace = json.loads(catalog.read_text(encoding="utf8"))
        self.assertEqual("concise-codex", marketplace["name"])
        plugin, = marketplace["plugins"]
        self.assertEqual("concise", plugin["name"])
        self.assertEqual("local", plugin["source"]["source"])
        self.assertEqual(PACKAGE.resolve(), (ROOT / plugin["source"]["path"]).resolve())
        self.assertEqual("AVAILABLE", plugin["policy"]["installation"])
        self.assertIn(plugin["policy"]["authentication"], ("ON_INSTALL", "ON_USE"))

    def test_activation_is_explicit_and_off_does_not_write_configuration(self):
        for name in ("concise", "concise-off"):
            skill_dir = PACKAGE / "skills" / name
            self.assertTrue(skill_dir.is_dir(), f"{name} skill is missing")
            skill = (skill_dir / "SKILL.md").read_text(encoding="utf8")
            self.assertIn(f"name: {name}\n", skill)
            metadata = (skill_dir / "agents/openai.yaml").read_text(encoding="utf8")
            self.assertIn("allow_implicit_invocation: false", metadata)
        off = (PACKAGE / "skills/concise-off/SKILL.md").read_text(encoding="utf8")
        self.assertIn("default response style", off)
        self.assertIn("Do not", off)
        for forbidden in ("hooks", "commands", ".app.json", ".mcp.json", "mcp.json", ".claude-plugin"):
            self.assertFalse((PACKAGE / forbidden).exists(), forbidden)

    def test_credit_and_license_survive_packaging(self):
        self.assertTrue((PACKAGE / "LICENSE").is_file(), "Codex license is missing")
        self.assertEqual((ROOT / "LICENSE").read_text(encoding="utf8"), (PACKAGE / "LICENSE").read_text(encoding="utf8"))
        for path in (PACKAGE / "README.md", PACKAGE / "skills/concise/SKILL.md"):
            text = path.read_text(encoding="utf8")
            self.assertIn("i-have-adhd", text)
            self.assertIn("Ayoub Ghriss", text)

    def test_archive_contains_only_the_self_contained_plugin(self):
        self.assertTrue(BUILDER.is_file(), "Codex package builder is missing")
        spec = importlib.util.spec_from_file_location("build_codex", BUILDER)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        with tempfile.TemporaryDirectory() as temp:
            archive = Path(temp) / "concise.zip"
            module.write_archive(PACKAGE, archive)
            with zipfile.ZipFile(archive) as bundle:
                expected = {"concise/" + p.relative_to(PACKAGE).as_posix() for p in PACKAGE.rglob("*") if p.is_file()}
                self.assertEqual(expected, set(bundle.namelist()))
                for member in bundle.namelist():
                    self.assertEqual((PACKAGE.parent / member).read_bytes(), bundle.read(member))
                self.assertIn("concise/.codex-plugin/plugin.json", bundle.namelist())

    def test_check_detects_a_stale_generated_skill(self):
        self.assertTrue(BUILDER.is_file(), "Codex package builder is missing")
        spec = importlib.util.spec_from_file_location("build_codex", BUILDER)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            generated = {"skills/concise/SKILL.md": b"expected\n"}
            self.assertEqual(["skills/concise/SKILL.md"], module.stale_files(root, generated))
            skill = root / "skills/concise/SKILL.md"
            skill.parent.mkdir(parents=True)
            skill.write_bytes(b"changed\n")
            self.assertEqual(["skills/concise/SKILL.md"], module.stale_files(root, generated))
            skill.write_bytes(b"expected\n")
            self.assertEqual([], module.stale_files(root, generated))
