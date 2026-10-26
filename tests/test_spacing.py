"""Compile real PDFs and compare glyph geometry, ignoring revision color/icons.

Run: python -m unittest discover -s tests -v
Requires local pdflatex, pdftoppm, pdftotext, Pillow, and pypdf.
No packages are installed. LATEX_ENGINE selects another installed compiler.
"""

import os
from pathlib import Path
import re
import shutil
import subprocess
import unittest
import xml.etree.ElementTree as ET

from PIL import Image, ImageChops
from pypdf import PdfReader


ROOT = Path(__file__).resolve().parents[1]
ENGINE = os.environ.get("LATEX_ENGINE", "pdflatex")
BUILD = ROOT / "tests" / "_build" / ENGINE


def run(command, env):
    result = subprocess.run(
        command, cwd=BUILD, env=env, capture_output=True, text=True,
        encoding="utf-8", errors="replace", timeout=90,
    )
    if result.returncode:
        raise AssertionError(result.stdout[-5000:] + result.stderr[-1000:])


def ink_mask(path):
    with Image.open(path) as image:
        red, green, blue = image.convert("RGB").split()
        # Pure blue and black have the same minimum channel, including antialiasing.
        return ImageChops.darker(ImageChops.darker(red, green), blue).copy()


def word_positions(pdf, env):
    result = subprocess.run(["pdftotext", "-bbox", str(pdf), "-"], env=env,
                            capture_output=True, check=True, timeout=30)
    words = ET.fromstring(result.stdout).findall(".//{http://www.w3.org/1999/xhtml}word")
    return sorted([(word.text, tuple(float(word.get(key)) for key in
                                     ("xMin", "yMin", "xMax", "yMax"))) for word in words],
                  key=lambda word: (round(word[1][1], 2), word[1][0]))


class SpacingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        for tool in (ENGINE, "pdftoppm", "pdftotext"):
            if not shutil.which(tool):
                raise RuntimeError(f"Required local executable not found: {tool}")
        BUILD.mkdir(parents=True, exist_ok=True)
        env = os.environ.copy()
        env["TEXINPUTS"] = str(ROOT) + os.pathsep + env.get("TEXINPUTS", "") + os.pathsep
        cls.env = env
        cls.pages = {}
        cls.notes = {}
        cls.has_blue = {}
        cls.dimensions = {}
        cls.positions = {}
        for mode in ("plain", "advisor", "reviewer", "clean"):
            source = ("" if mode == "plain" else rf"\def\ReviewMode{{{mode}}}")
            source += rf"\input{{{(ROOT / 'tests' / 'spacing_cases.tex').as_posix()}}}"
            for _ in range(2):
                run([ENGINE, "-interaction=nonstopmode", "-halt-on-error",
                     f"-jobname=spacing_{mode}", source], env)
            pdf = BUILD / f"spacing_{mode}.pdf"
            log = pdf.with_suffix(".log").read_text(encoding="utf-8", errors="replace")
            cls.dimensions[mode] = re.findall(r"REVIEW-DIM:[^\r\n]+", log)
            cls.positions[mode] = word_positions(pdf, env)
            reader = PdfReader(pdf)
            cls.notes[mode] = [
                ref.get_object() for page in reader.pages
                for ref in page.get("/Annots", [])
                if ref.get_object().get("/Subtype") == "/Text"
            ]
            run(["pdftoppm", "-r", "144", "-hide-annotations", "-png",
                 str(pdf), str(BUILD / f"spacing_{mode}")], env)
            cls.pages[mode] = [
                ink_mask(BUILD / f"spacing_{mode}-{i + 1}.png")
                for i in range(len(reader.pages))
            ]
            with Image.open(BUILD / f"spacing_{mode}-1.png") as image:
                red, _, blue = image.convert("RGB").split()
                cls.has_blue[mode] = ImageChops.subtract(blue, red).getbbox() is not None

    def test_glyph_positions_match_unmarked_source(self):
        # Same package/driver initialization avoids unrelated PDF rounding when
        # checking exact pixels. The raw source is checked independently below.
        reference = self.pages["clean"]
        for mode in ("advisor", "reviewer", "clean"):
            with self.subTest(mode=mode):
                self.assertEqual(len(reference), len(self.pages[mode]))
                for index, (expected, actual) in enumerate(zip(reference, self.pages[mode])):
                    delta = ImageChops.difference(expected, actual)
                    changed = sum(value != 0 for value in delta.tobytes())
                    if ENGINE == "pdflatex":
                        self.assertEqual(changed, 0,
                                         f"{mode} page {index + 1}: {changed} changed glyph pixels")
                # Xe/Lua output drivers round separate color runs differently;
                # verify positions directly rather than accepting shifted pixels.
                self.assertEqual(self.dimensions[mode], self.dimensions["plain"])
                self.assertEqual(len(self.dimensions[mode]), 5)
                expected_words = self.positions["plain"]
                actual_words = self.positions[mode]
                self.assertEqual(len(expected_words), len(actual_words))
                for (word, coordinates), (actual_word, actual_coordinates) in zip(
                        expected_words, actual_words):
                    self.assertEqual(word, actual_word)
                    self.assertLessEqual(max(abs(a - b) for a, b in
                                             zip(coordinates, actual_coordinates)), 0.05)

    def test_comments_only_in_advisor_pdf(self):
        # One PDF annotation per call, even inside align and script styles.
        self.assertEqual(len(self.notes["advisor"]), 25)
        self.assertEqual(len(self.notes["reviewer"]), 0)
        self.assertEqual(len(self.notes["clean"]), 0)
        self.assertTrue(all(note.get("/T") == "Johnnie" for note in self.notes["advisor"]))

    def test_revision_color_only_in_marked_modes(self):
        self.assertEqual(self.has_blue,
                         {"plain": False, "advisor": True, "reviewer": True, "clean": False})

    def test_custom_author_and_unicode_comment(self):
        note = "\u7b26\u53f7\u4fee\u6b63 (checked) 100%"
        source = (r"\documentclass{article}\usepackage{advisorreview}"
                  r"\renewcommand{\advisorreviewauthor}{Ada}"
                  r"\begin{document}Note\pdfrevnote{"
                  + note.replace("%", r"\%") + r"}\end{document}")
        run([ENGINE, "-interaction=nonstopmode", "-halt-on-error",
             "-jobname=metadata", source], self.env)
        reader = PdfReader(BUILD / "metadata.pdf")
        annotations = [ref.get_object() for ref in reader.pages[0].get("/Annots", [])
                       if ref.get_object().get("/Subtype") == "/Text"]
        self.assertEqual(len(annotations), 1)
        self.assertEqual(annotations[0].get("/T"), "Ada")
        self.assertEqual(annotations[0].get("/Contents"), note)

    def test_missing_mathcolor_still_compiles_complete_fragments(self):
        source = (r"\documentclass{article}\usepackage{amsmath,xcolor}\makeatletter"
                  r"\let\mathcolor\@undefined"
                  r"\let\review@savedinput\InputIfFileExists"
                  r"\def\InputIfFileExists#1#2#3{\def\review@file{#1}"
                  r"\def\review@missing{mathcolor.ltx}"
                  r"\ifx\review@file\review@missing#3"
                  r"\else\review@savedinput{#1}{#2}{#3}\fi}"
                  r"\makeatother\usepackage{advisorreview}\begin{document}"
                  r"\[a\pdfrevformula{=}{Relation}b+"
                  r"\pdfrevformula{\sum_{k=1}^n k}{Complete limits}\]\end{document}")
        run([ENGINE, "-interaction=nonstopmode", "-halt-on-error",
             "-jobname=fallback", source], self.env)
        log = (BUILD / "fallback.log").read_text(encoding="utf-8", errors="replace")
        self.assertIn("mathcolor.ltx not found", log)


if __name__ == "__main__":
    unittest.main()
