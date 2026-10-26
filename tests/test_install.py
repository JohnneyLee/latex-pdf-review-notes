"""Installation tests write only project-owned fixtures, not real user settings."""

import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


class InstallTests(unittest.TestCase):
    def test_jsonc_settings_preserved_and_installation_is_idempotent(self):
        if not shutil.which("node") or not shutil.which("code"):
            self.skipTest("The Windows desktop installer requires existing VS Code and Node.js.")
        from install_advisor_review import typescript_location

        try:
            typescript = typescript_location()
        except RuntimeError as error:
            self.skipTest(str(error))

        build = ROOT / "tests" / "_build"
        build.mkdir(exist_ok=True)
        project = Path(tempfile.mkdtemp(prefix="install ", dir=build))
        settings = project / "settings.json"
        original = '''{
  // An unrelated user comment must stay here.
  "editor.wordWrap": "on",
  "latex-workshop.latex.tools": [
    {"name": "old-xe", "command": "latexmk", "args": ["-xelatex", "%DOC%"]}
  ],
  "latex-workshop.latex.recipes": [{"name": "Existing", "tools": ["old-xe"]}],
  "latex-workshop.latex.recipe.default": "Existing",
}
'''
        settings.write_text(original, encoding="utf-8")
        command = [sys.executable, str(ROOT / "install_advisor_review.py"),
                   "--settings", str(settings), "--texmf-home", str(project / "texmf"),
                   "--typescript", str(typescript)]
        result = subprocess.run(command + ["--dry-run"], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(settings.read_text(encoding="utf-8"), original)
        result = subprocess.run(command, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        updated = settings.read_bytes()
        self.assertIn(b"An unrelated user comment", updated)
        self.assertIn(b'"editor.wordWrap": "on"', updated)
        self.assertIn(b'"name": "old-xe"', updated)
        self.assertIn(b"both PDFs + clean source", updated)
        self.assertIn(b'"xelatex"', updated)
        self.assertEqual(len(list(project.glob("settings.json.advisorreview.bak-*"))), 1)
        result = subprocess.run(command, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(settings.read_bytes(), updated)
        self.assertEqual(len(list(project.glob("settings.json.advisorreview.bak-*"))), 1)


if __name__ == "__main__":
    unittest.main()
