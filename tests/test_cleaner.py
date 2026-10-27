"""Unit tests for clean-source transformation."""

from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from clean_advisor_review import clean_source


class CleanerTests(unittest.TestCase):
    def test_nested_review_macros_are_removed_recursively(self):
        source = (
            r"\usepackage{advisorreview}" "\n"
            r"\pdfrevblock{Outer text \pdfrevmark{inner text}{Inner note}.}{Outer note}"
        )

        cleaned = clean_source(source)

        self.assertEqual(cleaned, "Outer text inner text.")
        self.assertNotIn(r"\pdfrev", cleaned)


if __name__ == "__main__":
    unittest.main()
