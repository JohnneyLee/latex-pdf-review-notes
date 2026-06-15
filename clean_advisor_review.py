#!/usr/bin/env python
"""Create a clean LaTeX source from an advisorreview working source.

This script removes advisorreview commands from the source file itself. It does
not compile LaTeX and does not rely on advisorreview's clean mode.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


DROP_ONE_ARG = {"pdfrevnote"}
KEEP_FIRST_ARG = {"pdfrevmark", "pdfrevmath", "pdfrevformula", "pdfrevblock"}
ALL_REVIEW_MACROS = DROP_ONE_ARG | KEEP_FIRST_ARG


def strip_setup_lines(text: str) -> str:
    """Remove package setup and the optional comment list command."""
    text = re.sub(
        r"(?m)^[ \t]*%.*advisorreview.*\r?\n?",
        "",
        text,
    )
    text = re.sub(
        r"(?m)^[ \t]*\\usepackage(?:\[[^\]\n]*\])?\{advisorreview\}[ \t]*(?:%.*)?\r?\n?",
        "",
        text,
    )
    text = re.sub(
        r"(?m)^[ \t]*\\PassOptionsToPackage\{[^{}\n]*\}\{advisorreview\}[ \t]*(?:%.*)?\r?\n?",
        "",
        text,
    )
    text = re.sub(
        r"(?m)^[ \t]*\\renewcommand\*?[ \t]*(?:\{\\advisorreview[a-zA-Z@]*\}|\\advisorreview[a-zA-Z@]*)[ \t]*\{[^{}\n]*\}[ \t]*(?:%.*)?\r?\n?",
        "",
        text,
    )
    text = re.sub(
        r"(?m)^[ \t]*\\def[ \t]*\\advisorreview[a-zA-Z@]*[ \t]*\{[^{}\n]*\}[ \t]*(?:%.*)?\r?\n?",
        "",
        text,
    )
    text = re.sub(
        r"\r?\n[ \t]*\\clearpage[ \t]*\r?\n[ \t]*\\printpdfreviewlist[ \t]*",
        "\n",
        text,
    )
    text = re.sub(
        r"(?m)^[ \t]*\\printpdfreviewlist[ \t]*(?:%.*)?\r?\n?",
        "",
        text,
    )
    return text


def parse_braced_group(text: str, open_index: int) -> tuple[str, int]:
    """Return the content of a balanced braced group and the next index."""
    if open_index >= len(text) or text[open_index] != "{":
        raise ValueError("expected '{'")

    depth = 1
    i = open_index + 1
    content_start = i

    while i < len(text):
        ch = text[i]
        if ch == "\\":
            i += 2
            continue
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return text[content_start:i], i + 1
        i += 1

    raise ValueError("unbalanced braces")


def skip_space(text: str, index: int) -> int:
    while index < len(text) and text[index] in " \t\r\n":
        index += 1
    return index


def clean_kept_argument(value: str) -> str:
    """Remove LaTeX spacing helpers that should not survive source cleanup."""
    return re.sub(r"\A%[ \t]*(?:\r?\n)", "", value)


def clean_review_macros(text: str) -> str:
    out: list[str] = []
    i = 0

    while i < len(text):
        if text[i] != "\\":
            out.append(text[i])
            i += 1
            continue

        match = re.match(r"\\([A-Za-z@]+)", text[i:])
        if not match:
            out.append(text[i])
            i += 1
            continue

        macro_name = match.group(1)
        if macro_name not in ALL_REVIEW_MACROS:
            out.append(match.group(0))
            i += len(match.group(0))
            continue

        arg1_start = skip_space(text, i + len(match.group(0)))
        if arg1_start >= len(text) or text[arg1_start] != "{":
            raise ValueError(f"\\{macro_name} is missing its first braced argument")

        arg1, after_arg1 = parse_braced_group(text, arg1_start)

        if macro_name in DROP_ONE_ARG:
            i = after_arg1
            continue

        arg2_start = skip_space(text, after_arg1)
        if arg2_start >= len(text) or text[arg2_start] != "{":
            raise ValueError(f"\\{macro_name} is missing its second braced argument")

        _, after_arg2 = parse_braced_group(text, arg2_start)
        out.append(clean_kept_argument(arg1))
        i = after_arg2

    return "".join(out)


def clean_source(text: str) -> str:
    text = strip_setup_lines(text)
    text = clean_review_macros(text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Remove advisorreview macros and create a clean LaTeX source."
    )
    parser.add_argument("input", help="review work tex file, e.g. MB_LD_review_work.tex")
    parser.add_argument("output", help="clean output tex file, e.g. MB_LD_clean_source.tex")
    parser.add_argument(
        "--force",
        action="store_true",
        help="overwrite the output file if it already exists",
    )
    args = parser.parse_args(argv)

    input_path = Path(args.input)
    output_path = Path(args.output)

    if not input_path.exists():
        print(f"Input file not found: {input_path}", file=sys.stderr)
        return 2

    if output_path.exists() and not args.force:
        print(
            f"Output file already exists: {output_path}\n"
            "Use --force only after checking that overwriting is intended.",
            file=sys.stderr,
        )
        return 3

    text = input_path.read_text(encoding="utf-8-sig")
    cleaned = clean_source(text)

    leftovers = [
        token
        for token in (
            "advisorreview",
            "\\pdfrevnote",
            "\\pdfrevmark",
            "\\pdfrevmath",
            "\\pdfrevformula",
            "\\pdfrevblock",
            "\\printpdfreviewlist",
        )
        if token in cleaned
    ]
    if leftovers:
        print(
            "Cleaned source still contains review tokens: " + ", ".join(leftovers),
            file=sys.stderr,
        )
        return 4

    output_path.write_text(cleaned, encoding="utf-8")
    print(f"Wrote clean source: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
