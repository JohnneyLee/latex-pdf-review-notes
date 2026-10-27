"""Installation tests write only project-owned fixtures, not real user settings."""

import json
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
        runtime = project / "personal tools"
        command = [sys.executable, str(ROOT / "install_advisor_review.py"),
                   "--settings", str(settings), "--texmf-home", str(project / "texmf"),
                   "--runtime-home", str(runtime),
                   "--typescript", str(typescript)]
        result = subprocess.run(command + ["--dry-run"], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(settings.read_text(encoding="utf-8"), original)
        self.assertFalse(runtime.exists())
        result = subprocess.run(command, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        updated = settings.read_bytes()
        self.assertIn(b"An unrelated user comment", updated)
        self.assertIn(b'"editor.wordWrap": "on"', updated)
        self.assertIn(b'"name": "old-xe"', updated)
        self.assertIn(b"both PDFs + clean source", updated)
        self.assertIn(b'"xelatex"', updated)
        for name in ("build_advisor_review.py", "clean_advisor_review.py"):
            self.assertEqual((runtime / name).read_bytes(), (ROOT / name).read_bytes())
        self.assertNotIn(str(ROOT / "build_advisor_review.py").replace("\\", "\\\\").encode(), updated)
        self.assertTrue((runtime / "installation.json").is_file())
        self.assertEqual(len(list(project.glob("settings.json.advisorreview.bak-*"))), 1)
        result = subprocess.run(command, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(settings.read_bytes(), updated)
        self.assertEqual(len(list(project.glob("settings.json.advisorreview.bak-*"))), 1)
        self.assertEqual(list(runtime.glob("*.advisorreview.bak-*")), [])

    def isolated_install(self):
        if not shutil.which("node") or not shutil.which("code"):
            self.skipTest("The Windows desktop installer requires existing VS Code and Node.js.")
        from install_advisor_review import typescript_location

        try:
            typescript = typescript_location()
        except RuntimeError as error:
            self.skipTest(str(error))
        build = ROOT / "tests" / "_build"
        build.mkdir(exist_ok=True)
        project = Path(tempfile.mkdtemp(prefix="installed runtime ", dir=build))
        download = project / "download"
        (download / "integration").mkdir(parents=True)
        for name in ("install_advisor_review.py", "build_advisor_review.py",
                     "clean_advisor_review.py", "advisorreview.sty"):
            shutil.copyfile(ROOT / name, download / name)
        shutil.copyfile(ROOT / "integration" / "vscode_settings.cjs",
                        download / "integration" / "vscode_settings.cjs")
        settings = project / "settings.json"
        settings.write_text("{}\n", encoding="utf-8")
        env = os.environ.copy()
        env["LOCALAPPDATA"] = str(project / "User Local")
        env["TEXMFHOME"] = str(project / "texmf")
        env.pop("TEXINPUTS", None)
        env.pop("PYTHONPATH", None)
        command = [sys.executable, str(download / "install_advisor_review.py"),
                   "--settings", str(settings), "--texmf-home", env["TEXMFHOME"],
                   "--typescript", str(typescript)]
        return project, download, settings, command, env

    def test_default_runtime_survives_unavailable_download_and_builds_normally(self):
        from pypdf import PdfReader

        project, download, settings, command, env = self.isolated_install()
        result = subprocess.run(command, env=env, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        runtime = Path(env["LOCALAPPDATA"]) / "latex-pdf-review-notes"
        tool = next(item for item in json.loads(settings.read_text(encoding="utf-8"))[
            "latex-workshop.latex.tools"] if item["name"] == "advisor-review-build")
        self.assertEqual(Path(tool["args"][0]), runtime / "build_advisor_review.py")
        self.assertNotIn(str(download), json.dumps(tool))
        # Make the original path unavailable without deleting any evidence.
        self.assertTrue(download.resolve().is_relative_to(project.resolve()))
        download.rename(project / "moved download")
        manuscript = project / "paper"
        manuscript.mkdir()
        source = manuscript / "main_review_work.tex"
        original = ("\\documentclass{article}\n\\usepackage{amsmath}\n"
                    "\\usepackage{advisorreview}\n"
                    "\\renewcommand{\\advisorreviewauthor}{Installed User}\n"
                    "\\begin{document}\n\\pdfrevnote{A note.}\n"
                    "\\pdfrevmark{Changed text}{Text note.}\n"
                    "\\pdfrevmath{\\(a>0\\)}{Inline note.}\n"
                    "\\[a\\pdfrevformula{=}{Formula note.}b\\]\n"
                    "\\pdfrevblock{A revised sentence.}{Block note.}\n"
                    "\\end{document}\n")
        source.write_text(original, encoding="utf-8")

        def build(path):
            args = [arg.replace("%DOC_EXT%", str(path)).replace("%OUTDIR%", str(manuscript))
                    for arg in tool["args"]]
            result = subprocess.run([tool["command"], *args], cwd=manuscript, env=env,
                                    capture_output=True, text=True, encoding="utf-8",
                                    errors="replace", timeout=120)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

        build(source)
        output = manuscript / ".advisorreview" / source.stem
        for mode, expected in (("advisor", 5), ("reviewer", 0)):
            notes = [ref.get_object() for page in PdfReader(output / f"main_{mode}.pdf").pages
                     for ref in page.get("/Annots", [])
                     if ref.get_object().get("/Subtype") == "/Text"]
            self.assertEqual(len(notes), expected)
        clean = output / "main_clean_source.tex"
        self.assertNotIn("advisorreview", clean.read_text(encoding="utf-8"))
        self.assertNotIn(r"\pdfrev", clean.read_text(encoding="utf-8"))
        self.assertEqual(source.read_text(encoding="utf-8"), original)
        build(clean)
        clean_pdf = manuscript / "main_clean_source.pdf"
        self.assertTrue(clean_pdf.is_file())
        self.assertFalse(any(page.get("/Annots", []) for page in PdfReader(clean_pdf).pages))
        self.assertFalse((manuscript / ".advisorreview" / clean.stem).exists())
        fls = source.with_suffix(".fls").read_text(encoding="utf-8").replace("\\", "/").lower()
        package = Path(env["TEXMFHOME"]) / "tex" / "latex" / "advisorreview" / "advisorreview.sty"
        self.assertIn(package.as_posix().lower(), fls)
        ordinary = manuscript / "ordinary.tex"
        ordinary.write_text("\\documentclass{article}\n\\begin{document}Ordinary."
                            "\\end{document}\n", encoding="utf-8")
        build(ordinary)
        self.assertTrue(ordinary.with_suffix(".pdf").is_file())
        self.assertFalse((manuscript / ".advisorreview" / "ordinary").exists())

    def test_update_backs_up_runtime_and_does_not_add_recipes(self):
        project, download, settings, command, env = self.isolated_install()
        result = subprocess.run(command, env=env, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        runtime = Path(env["LOCALAPPDATA"]) / "latex-pdf-review-notes"
        builder = runtime / "build_advisor_review.py"
        old = builder.read_bytes()
        updated = old + b"\n# Upgrade fixture.\n"
        (download / builder.name).write_bytes(updated)
        result = subprocess.run(command, env=env, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(builder.read_bytes(), updated)
        backups = list(runtime.glob(builder.name + ".advisorreview.bak-*"))
        self.assertEqual(len(backups), 1)
        self.assertEqual(backups[0].read_bytes(), old)
        config = json.loads(settings.read_text(encoding="utf-8"))
        self.assertEqual(len(config["latex-workshop.latex.tools"]), 1)
        self.assertEqual(len(config["latex-workshop.latex.recipes"]), 1)

    def test_missing_payload_leaves_settings_and_runtime_untouched(self):
        project, download, settings, command, env = self.isolated_install()
        missing = download / "clean_advisor_review.py"
        self.assertTrue(missing.resolve().is_relative_to(project.resolve()))
        missing.rename(download / "clean_advisor_review.py.unavailable")
        result = subprocess.run(command, env=env, capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(settings.read_text(encoding="utf-8"), "{}\n")
        self.assertFalse((Path(env["LOCALAPPDATA"]) / "latex-pdf-review-notes").exists())
        self.assertFalse((Path(env["TEXMFHOME"]) / "tex" / "latex" / "advisorreview").exists())


if __name__ == "__main__":
    unittest.main()
