"""End-to-end build tests using installed TeX tools; no downloads."""

import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from pypdf import PdfReader, PdfWriter


ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / "tests" / "_build"


class BuildTests(unittest.TestCase):
    def setUp(self):
        BUILD.mkdir(exist_ok=True)
        # Keep failure evidence; generated files are ignored by Git.
        self.project = Path(tempfile.mkdtemp(prefix="build space \u6d4b\u8bd5 ", dir=BUILD))
        self.env = os.environ.copy()
        self.env["TEXINPUTS"] = str(ROOT) + os.pathsep + self.env.get("TEXINPUTS", "") + os.pathsep
        self.source = self.project / "paper_review_work.tex"

    def invoke(self):
        return subprocess.run(
            [sys.executable, str(ROOT / "build_advisor_review.py"), str(self.source)],
            cwd=self.project, env=self.env, capture_output=True, text=True,
            encoding="utf-8", errors="replace", timeout=120,
        )

    def write_source(self, setup=r"\usepackage{advisorreview}", extra=""):
        text = ("\\documentclass{article}\n\\usepackage{amsmath,graphicx}\n"
                + setup + "\n\\begin{document}\n"
                + "Changed \\pdfrevmark{word}{A private note}.\n"
                + "\\[ a\\pdfrevformula{=}{Equation note}b \\]\n"
                + extra + "\n\\end{document}\n")
        self.source.write_text(text, encoding="utf-8")
        return text

    def notes(self, path):
        return [ref.get_object() for page in PdfReader(path).pages
                for ref in page.get("/Annots", [])
                if ref.get_object().get("/Subtype") == "/Text"]

    def test_both_pdfs_clean_export_resources_and_repeat_build(self):
        (self.project / "body.tex").write_text("An unchanged input.\n", encoding="utf-8")
        (self.project / "refs.bib").write_text(
            "@book{item, author={Ada Author}, title={A Test}, year={2020}, publisher={Test}}\n",
            encoding="utf-8")
        figure = PdfWriter()
        figure.add_blank_page(width=50, height=50)
        with (self.project / "figure.pdf").open("wb") as stream:
            figure.write(stream)
        original = self.write_source(extra=(
            r"\input{body}\includegraphics[width=1cm]{figure.pdf}" + "\n"
            + r"\cite{item}\bibliographystyle{plain}\bibliography{refs}"))
        result = self.invoke()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        output = self.project / ".advisorreview" / self.source.stem
        self.assertEqual(len(self.notes(output / "paper_advisor.pdf")), 2)
        self.assertEqual(len(self.notes(output / "paper_reviewer.pdf")), 0)
        cleaned = output / "paper_clean_source.tex"
        self.assertNotIn("advisorreview", cleaned.read_text(encoding="utf-8"))
        self.assertNotIn(r"\pdfrev", cleaned.read_text(encoding="utf-8"))
        self.assertEqual(self.source.read_text(encoding="utf-8"), original)
        self.assertFalse((self.project / "paper_advisor.tex").exists())
        result = self.invoke()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(len(self.notes(output / "paper_advisor.pdf")), 2)
        clean_check = output / "clean_check"
        clean_check.mkdir()
        result = subprocess.run(
            ["latexmk", "-pdf", "-MSWinBackSlash-", "-interaction=nonstopmode",
             "-halt-on-error", f"-outdir={clean_check.as_posix()}", cleaned.as_posix()],
            cwd=self.project, env=self.env, capture_output=True, text=True,
            encoding="utf-8", errors="replace", timeout=90)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(len(self.notes(clean_check / "paper_clean_source.pdf")), 0)

    def test_ordinary_document_does_not_create_review_outputs(self):
        self.source.write_text(
            "\\documentclass{article}\n% \\usepackage{advisorreview}\n"
            "\\begin{document}Ordinary paper.\\end{document}\n", encoding="utf-8")
        result = self.invoke()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertTrue(self.source.with_suffix(".pdf").exists())
        self.assertFalse((self.project / ".advisorreview").exists())

    def test_clean_mode_source_still_produces_both_marked_versions(self):
        self.write_source(setup=r"\usepackage[clean]{advisorreview}")
        result = self.invoke()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        output = self.project / ".advisorreview" / self.source.stem
        self.assertEqual(len(self.notes(output / "paper_advisor.pdf")), 2)
        self.assertEqual(len(self.notes(output / "paper_reviewer.pdf")), 0)

    def test_edited_clean_export_is_not_overwritten(self):
        self.write_source()
        result = self.invoke()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        clean = self.project / ".advisorreview" / self.source.stem / "paper_clean_source.tex"
        edited = clean.read_bytes() + b"% user edited this export\n"
        clean.write_bytes(edited)
        result = self.invoke()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("modified", result.stderr.lower())
        self.assertEqual(clean.read_bytes(), edited)

    def test_second_mode_failure_does_not_publish_a_clean_export(self):
        sys.path.insert(0, str(ROOT))
        import build_advisor_review as builder

        self.write_source()
        real_compile = builder.compile_tex

        def fail_reviewer(source, cwd, out_dir, engine, label):
            if label == "reviewer":
                raise builder.BuildError("Build failed (reviewer): injected compiler failure")
            return real_compile(source, cwd, out_dir, engine, label)

        with patch.dict(os.environ, self.env), patch.object(builder, "compile_tex", side_effect=fail_reviewer):
            with self.assertRaisesRegex(builder.BuildError, r"Build failed \(reviewer\)"):
                builder.build(self.source, "pdflatex")
        output = self.project / ".advisorreview" / self.source.stem
        self.assertFalse((output / "paper_clean_source.tex").exists())
        self.assertFalse((output / "paper_advisor.pdf").exists())

    def test_source_in_included_file_is_not_silently_left_marked(self):
        self.write_source(extra=r"\input{body}")
        (self.project / "body.tex").write_text(r"\pdfrevmark{A child revision}{Note}", encoding="utf-8")
        result = self.invoke()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("single-file", result.stderr.lower())
        output = self.project / ".advisorreview" / self.source.stem
        self.assertFalse((output / "paper_clean_source.tex").exists())


if __name__ == "__main__":
    unittest.main()
