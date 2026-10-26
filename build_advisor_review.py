#!/usr/bin/env python
"""Build normally, then export both review PDFs and clean source when enabled."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys

from clean_advisor_review import ALL_REVIEW_MACROS, clean_source


class BuildError(RuntimeError):
    pass


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def compile_tex(source: Path, cwd: Path, out_dir: Path, engine: str, label: str) -> Path:
    latexmk = shutil.which("latexmk")
    if not latexmk:
        raise BuildError("latexmk was not found. Use the project's existing TeX installation.")
    out_dir.mkdir(parents=True, exist_ok=True)
    option = {"pdflatex": "-pdf", "xelatex": "-xelatex", "lualatex": "-lualatex"}[engine]
    # Forward slashes avoid old Windows latexmk turning paths into TeX commands.
    command = [latexmk, option, "-MSWinBackSlash-", "-synctex=1", "-recorder",
               "-interaction=nonstopmode", "-halt-on-error", "-file-line-error",
               f"-outdir={out_dir.as_posix()}", source.as_posix()]
    print(f"Building {label} ({engine})...", flush=True)
    result = subprocess.run(command, cwd=cwd, capture_output=True, text=True,
                            encoding="utf-8", errors="replace")
    if result.returncode:
        raise BuildError(f"Build failed ({label}).\n" + "\n".join(
            (result.stdout + result.stderr).splitlines()[-30:]))
    pdf = out_dir / (source.stem + ".pdf")
    if not pdf.is_file() or not pdf.read_bytes().startswith(b"%PDF-"):
        raise BuildError(f"No valid PDF was produced: {pdf}")
    return pdf


def recorded_inputs(fls: Path, cwd: Path) -> set[Path]:
    if not fls.is_file():
        raise BuildError(f"Cannot inspect loaded packages: recorder file missing: {fls}")
    result = set()
    for line in fls.read_text(encoding="utf-8", errors="replace").splitlines():
        if line.startswith("INPUT "):
            path = Path(line[6:].strip().strip('"'))
            result.add((path if path.is_absolute() else cwd / path).resolve())
    return result


def validate_clean_source(source: Path, inputs: set[Path], text: str) -> str:
    tokens = {"advisorreview", r"\printpdfreviewlist"} | {
        "\\" + name for name in ALL_REVIEW_MACROS}
    # The existing cleaner processes one working source; never silently leave
    # annotations or package setup in a separately included TeX file.
    for path in inputs:
        if path == source or path.suffix.lower() != ".tex":
            continue
        if path.is_relative_to(source.parent) and ".advisorreview" in path.relative_to(source.parent).parts:
            continue
        child = path.read_text(encoding="utf-8-sig", errors="replace")
        if any(token in child for token in tokens):
            raise BuildError("Clean export currently supports single-file review sources; "
                             f"an included file contains review code: {path}")
    cleaned = clean_source(text)
    if any(token in cleaned for token in tokens):
        raise BuildError("Clean source still contains review code. No clean export was published.")
    return cleaned


def check_export(destination: Path, manifest: Path, source: Path) -> None:
    if not destination.exists():
        return
    if not manifest.is_file():
        raise BuildError(f"Unowned clean export already exists; refusing to overwrite: {destination}")
    try:
        metadata = json.loads(manifest.read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        raise BuildError(f"Cannot validate clean-export ownership: {manifest}") from error
    if metadata.get("source") != str(source) or metadata.get("clean_sha256") != digest(destination.read_bytes()):
        raise BuildError(f"Clean export was modified; refusing to overwrite: {destination}")


def mode_wrapper(source: Path, mode: str) -> str:
    if any(char in source.as_posix() for char in "%{}\n\r"):
        raise BuildError("TeX input paths containing percent signs, braces or newlines are unsupported.")
    comments = "true" if mode == "advisor" else "false"
    return (f"\\PassOptionsToPackage{{{mode}}}{{advisorreview}}\n"
            "\\AtBeginDocument{\\ifcsname advisorreviewhighlighttrue\\endcsname\n"
            f"  \\advisorreviewhighlighttrue\\advisorreviewcomments{comments}\\fi}}\n"
            f"\\input{{\\detokenize{{{source.as_posix()}}}}}\n")


def build(source: Path, engine: str, out_dir: Path | None = None) -> dict[str, str]:
    source = source.resolve()
    if source.suffix.lower() != ".tex" or not source.is_file():
        raise BuildError(f"Input TeX file not found: {source}")
    original = source.read_bytes()
    normal_out = (out_dir or source.parent).resolve()
    normal_pdf = compile_tex(source, source.parent, normal_out, engine, "normal document")
    inputs = recorded_inputs(normal_pdf.with_suffix(".fls"), source.parent)
    if not any(path.name.lower() == "advisorreview.sty" for path in inputs):
        print(f"Normal document: no review exports needed.\nPDF: {normal_pdf}")
        return {"pdf": str(normal_pdf)}

    output = source.parent / ".advisorreview" / source.stem
    if not output.resolve().is_relative_to(source.parent):
        raise BuildError("The generated-output directory resolves outside the project.")
    base = source.stem.removesuffix("_review_work")
    clean_path = output / f"{base}_clean_source.tex"
    manifest = output / "manifest.json"
    check_export(clean_path, manifest, source)
    cleaned = validate_clean_source(source, inputs, original.decode("utf-8-sig"))
    log = normal_pdf.with_suffix(".log").read_text(encoding="utf-8", errors="replace")
    modes = re.findall(r"ADVISORREVIEW-MODE:(advisor|reviewer|clean)", log)
    normal_mode = modes[-1] if modes else None
    pdfs = {}
    for mode in ("advisor", "reviewer"):
        if normal_mode == mode:
            pdfs[mode] = normal_pdf
        else:
            cache = output / "build" / mode
            cache.mkdir(parents=True, exist_ok=True)
            wrapper = cache / f"{base}_{mode}.tex"
            content = mode_wrapper(source, mode)
            if not wrapper.exists() or wrapper.read_text(encoding="utf-8") != content:
                wrapper.write_text(content, encoding="utf-8")
            pdfs[mode] = compile_tex(wrapper, source.parent, cache, engine, mode)
    if source.read_bytes() != original:
        raise BuildError("Working source changed during compilation; no review export was published.")
    check_export(clean_path, manifest, source)
    result = {}
    for mode, pdf in pdfs.items():
        destination = output / f"{base}_{mode}.pdf"
        shutil.copyfile(pdf, destination)
        result[mode] = str(destination)
    clean_path.write_text(cleaned, encoding="utf-8")
    result["clean_source"] = str(clean_path)
    metadata = {"source": str(source), "source_sha256": digest(original),
                "clean_sha256": digest(clean_path.read_bytes()), "engine": engine,
                "outputs": result}
    manifest.write_text(json.dumps(metadata, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print("Both PDFs and clean source are ready:")
    for name, path in result.items():
        print(f"  {name}: {path}")
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("--engine", choices=("pdflatex", "xelatex", "lualatex"), default="pdflatex")
    parser.add_argument("--out-dir", type=Path, help="Normal PDF directory used by the existing editor")
    args = parser.parse_args(argv)
    try:
        build(args.source, args.engine, args.out_dir)
    except (BuildError, OSError, ValueError) as error:
        print(str(error), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
