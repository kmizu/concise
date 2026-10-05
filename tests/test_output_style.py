import importlib.util
import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BUILDER = ROOT / "scripts" / "build_output_style.py"
STYLE = ROOT / "output-styles" / "concise.md"


class OutputStyleTest(unittest.TestCase):
    """output-styles/concise.md is generated from the canonical skill."""

    def setUp(self):
        spec = importlib.util.spec_from_file_location("build_output_style", BUILDER)
        self.module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.module)

    def test_generated_style_is_up_to_date(self):
        result = subprocess.run([sys.executable, str(BUILDER), "--check"], capture_output=True, text=True)
        self.assertEqual(0, result.returncode, result.stderr)

    def test_style_frontmatter_keeps_coding_instructions(self):
        text = STYLE.read_text(encoding="utf8")
        self.assertTrue(text.startswith("---\nname: concise\n"))
        self.assertIn("keep-coding-instructions: true", text.split("\n---\n", 1)[0])
        self.assertNotIn("force-for-plugin", text)

    def test_style_body_is_the_canonical_ruleset(self):
        style = self.module.generated_text()
        skill = (ROOT / "skills" / "concise" / "SKILL.md").read_text(encoding="utf8").replace("\r\n", "\n")
        self.assertIn("[ruleset concise]{", style)
        self.assertEqual(10, style.count("[rule "))
        self.assertEqual(skill.count("[rule "), style.count("[rule "))
        self.assertNotIn("Derived from", style)
        self.assertNotIn("disable-model-invocation", style)


if __name__ == "__main__":
    unittest.main()
