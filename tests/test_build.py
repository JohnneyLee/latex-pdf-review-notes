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

    def test_loaded_package_without_used_commands_is_normal(self):
        for mode in ("advisor", "reviewer", "clean"):
            with self.subTest(mode=mode):
                self.source = self.project / f"unused_{mode}.tex"
                self.source.write_text(
                    "\\documentclass{article}\n\\usepackage{amsmath}\n"
                    + f"\\usepackage[{mode}]{{advisorreview}}\n"
                    + "\\renewcommand{\\advisorreviewauthor}{A User}\n"
                    + "\\begin{document}No review commands here.\\end{document}\n",
                    encoding="utf-8")
                result = self.invoke()
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertIn("no review commands were used", result.stdout.lower())
                self.assertTrue(self.source.with_suffix(".pdf").is_file())
                self.assertFalse((self.project / ".advisorreview").exists())

    def test_inactive_commented_literal_and_unexpanded_commands_do_not_trigger(self):
        (self.project / "inactive.tex").write_text(
            "% \\pdfrevblock{A comment}{Not executed}\n"
            "\\iffalse\\pdfrevnote{Not executed}\\fi\n"
            "\\newcommand{\\unusedreview}{\\pdfrevmark{Unused}{Not executed}}\n"
            "\\verb|\\pdfrevmark{Literal text}{Not executed}|\n", encoding="utf-8")
        self.source.write_text(
            "\\documentclass{article}\n\\usepackage{advisorreview}\n"
            "\\begin{document}\\input{inactive}\\end{document}\n", encoding="utf-8")
        result = self.invoke()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertFalse((self.project / ".advisorreview").exists())

    def test_each_review_command_triggers_even_when_normal_mode_is_clean(self):
        cases = {
            "pdfrevnote": r"\pdfrevnote{Only a note}",
            "pdfrevmark": r"\pdfrevmark{Only blue text}{}",
            "pdfrevmath": r"\pdfrevmath{\(a>0\)}{Inline math}",
            "pdfrevformula": r"\[a\pdfrevformula{=}{Math}b\]",
            "pdfrevblock": r"\pdfrevblock{A sentence.}{Block note}",
        }
        for name, body in cases.items():
            with self.subTest(command=name):
                self.source = self.project / f"{name}.tex"
                self.source.write_text(
                    "\\documentclass{article}\n\\usepackage{amsmath}\n"
                    "\\usepackage[clean]{advisorreview}\n\\begin{document}\n"
                    + "A baseline sentence. {" + body + "}\n\\end{document}\n", encoding="utf-8")
                result = self.invoke()
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                output = self.project / ".advisorreview" / self.source.stem
                self.assertTrue((output / f"{name}_advisor.pdf").is_file())
                self.assertTrue((output / f"{name}_reviewer.pdf").is_file())
                self.assertTrue((output / f"{name}_clean_source.tex").is_file())
                log = self.source.with_suffix(".log").read_text(encoding="utf-8", errors="replace")
                self.assertIn("ADVISORREVIEW-USED:yes", log)

    def test_end_document_review_command_is_detected(self):
        self.source.write_text(
            "\\documentclass{article}\n\\usepackage{advisorreview}\n"
            "\\AtEndDocument{\\pdfrevnote{A final note}}\n"
            "\\begin{document}An end-hook note.\\end{document}\n", encoding="utf-8")
        result = self.invoke()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        output = self.project / ".advisorreview" / self.source.stem
        self.assertEqual(len(self.notes(output / "paper_advisor.pdf")), 1)

    def test_used_command_without_package_has_actionable_error(self):
        cases = {
            "pdfrevnote": r"\pdfrevnote{Missing package}",
            "pdfrevmark": r"\pdfrevmark{Changed}{Missing package}",
            "pdfrevmath": r"\pdfrevmath{\(a>0\)}{Missing package}",
            "pdfrevformula": r"\[\pdfrevformula{a=b}{Missing package}\]",
            "pdfrevblock": r"\pdfrevblock{A sentence.}{Missing package}",
        }
        for name, body in cases.items():
            with self.subTest(command=name):
                self.source = self.project / f"missing_{name}.tex"
                self.source.write_text(
                    "\\documentclass{article}\n\\usepackage{amsmath}\n"
                    "\\begin{document}\n" + body + "\n\\end{document}\n", encoding="utf-8")
                result = self.invoke()
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("advisorreview.sty was not loaded", result.stderr)
                self.assertIn(r"\usepackage{advisorreview}", result.stderr)
                self.assertIn("\\" + name, result.stderr)
                self.assertFalse((self.project / ".advisorreview").exists())

    def test_inactive_command_without_package_is_not_an_error(self):
        self.source.write_text(
            "\\documentclass{article}\n\\begin{document}\n"
            "\\iffalse\\pdfrevmark{Not used}{Not used}\\fi\n"
            "Ordinary document.\\end{document}\n", encoding="utf-8")
        result = self.invoke()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertFalse((self.project / ".advisorreview").exists())

    def test_other_undefined_commands_do_not_get_missing_package_advice(self):
        for loaded in (False, True):
            with self.subTest(package_loaded=loaded):
                self.source = self.project / f"unrelated_{loaded}.tex"
                setup = "\\usepackage{advisorreview}\n" if loaded else ""
                body = (r"\pdfrevmark{\unknowncommand}{A note}" if loaded
                        else r"\unknowncommand \pdfrevmark{Not reached}{Not reached}")
                self.source.write_text("\\documentclass{article}\n" + setup
                                       + "\\begin{document}\n" + body
                                       + "\n\\end{document}\n", encoding="utf-8")
                result = self.invoke()
                self.assertNotEqual(result.returncode, 0)
                self.assertNotIn("advisorreview.sty was not loaded", result.stderr)
                self.assertIn("Undefined control sequence", result.stderr)

    def test_removing_all_marks_keeps_existing_exports_unchanged(self):
        self.write_source()
        result = self.invoke()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        output = self.project / ".advisorreview" / self.source.stem
        clean = output / "paper_clean_source.tex"
        clean.write_bytes(clean.read_bytes() + b"% A user's archived edits.\n")
        before = {path: (path.read_bytes(), path.stat().st_mtime_ns)
                  for path in output.rglob("*") if path.is_file()}
        self.source.write_text(
            "\\documentclass{article}\n\\usepackage{advisorreview}\n"
            "\\begin{document}All marks removed.\\end{document}\n", encoding="utf-8")
        for _ in range(2):
            result = self.invoke()
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("existing exports were retained", result.stdout.lower())
            after = {path: (path.read_bytes(), path.stat().st_mtime_ns)
                     for path in output.rglob("*") if path.is_file()}
            self.assertEqual(after, before)

    def test_old_package_without_usage_report_requires_update(self):
        (self.project / "advisorreview.sty").write_text(
            "\\ProvidesPackage{advisorreview}[2000/01/01 Old package fixture]\n"
            "\\newcommand{\\pdfrevmark}[2]{#1}\n", encoding="utf-8")
        self.source.write_text(
            "\\documentclass{article}\n\\usepackage{advisorreview}\n"
            "\\begin{document}\\pdfrevmark{Changed}{Note}\\end{document}\n", encoding="utf-8")
        result = self.invoke()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("usage report", result.stderr.lower())
        self.assertIn("update", result.stderr.lower())
        self.assertIn(str(self.project / "advisorreview.sty"), result.stderr)
        self.assertFalse((self.project / ".advisorreview").exists())

    def test_clean_mode_source_still_produces_both_marked_versions(self):
        self.write_source(setup=r"\usepackage[clean]{advisorreview}")
        result = self.invoke()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        output = self.project / ".advisorreview" / self.source.stem
        self.assertEqual(len(self.notes(output / "paper_advisor.pdf")), 2)
        self.assertEqual(len(self.notes(output / "paper_reviewer.pdf")), 0)

    def test_nested_review_marks_export_clean_source(self):
        self.source.write_text(
            "\\documentclass{article}\n\\usepackage{advisorreview}\n"
            "\\begin{document}\n"
            r"\pdfrevblock{Outer text \pdfrevmark{inner text}{Inner note}.}{Outer note}"
            "\n\\end{document}\n",
            encoding="utf-8",
        )
        result = self.invoke()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        output = self.project / ".advisorreview" / self.source.stem
        self.assertEqual(len(self.notes(output / "paper_advisor.pdf")), 2)
        self.assertEqual(len(self.notes(output / "paper_reviewer.pdf")), 0)
        cleaned = (output / "paper_clean_source.tex").read_text(encoding="utf-8")
        self.assertIn("Outer text inner text.", cleaned)
        self.assertNotIn(r"\pdfrev", cleaned)

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
