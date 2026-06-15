# LaTeX PDF Review Notes

Source-level LaTeX review notes that become blue revision-text PDF drafts for advisors and reviewers.

`latex-pdf-review-notes` is a lightweight workflow for writing review markers directly in LaTeX source and producing PDF drafts with visible blue revision text and optional PDF comments.

It is designed for manuscript revision workflows where authors need to show changes to advisors, supervisors, collaborators, or reviewers without manually editing the generated PDF.

## What It Produces

- Advisor / supervisor draft: blue revision text plus PDF bubble comments.
- Reviewer-facing marked draft: blue revision text only, without private internal comments.
- Clean LaTeX source: a generated `.tex` file with all review macros removed.

## Files

```text
advisorreview.sty             LaTeX package with review macros
clean_advisor_review.py       Clean-source generator
clean_advisor_review.cmd      Windows launcher for the clean-source generator
examples/                     Minimal LaTeX example project
```

## Requirements

LaTeX packages:

- `pdfcomment`
- `hyperref`
- `xcolor`
- `amsmath` for `equation*`, `align`, and related math environments

Runtime for clean-source export:

- Python 3
- On Windows, use `clean_advisor_review.cmd` so users do not need to know the full Python path.

PDF reader:

- Acrobat Reader or SumatraPDF is recommended for viewing PDF bubble comments.
- Browser PDF viewers may show the blue revision text but not all comment details.

## Quick Start

Copy these files into the same folder as your manuscript:

```text
advisorreview.sty
clean_advisor_review.py
clean_advisor_review.cmd
```

Create a review working copy of your manuscript:

```powershell
Copy-Item .\main.tex .\main_review_work.tex
```

In `main_review_work.tex`, load the package:

```latex
\usepackage{amsmath}
\usepackage{advisorreview}
```

Optionally set the PDF comment author:

```latex
\renewcommand{\advisorreviewauthor}{Johnnie}
```

Add review notes in the body:

```latex
\pdfrevmark{revised text}{Explain why this text changed.}
\pdfrevmath{$\alpha_k>0$}{Explain the notation change.}
```

Create an advisor wrapper:

```latex
% !TEX root = main_advisor.tex
\PassOptionsToPackage{advisor}{advisorreview}
\input{main_review_work.tex}
```

Create a reviewer wrapper:

```latex
% !TEX root = main_reviewer.tex
\PassOptionsToPackage{reviewer}{advisorreview}
\input{main_review_work.tex}
```

Compile:

```powershell
latexmk -pdf -interaction=nonstopmode -halt-on-error main_advisor.tex
latexmk -pdf -interaction=nonstopmode -halt-on-error main_reviewer.tex
```

Generate a clean source after the review draft is accepted:

```powershell
.\clean_advisor_review.cmd .\main_review_work.tex .\main_clean_source.tex --force
```

Verify that the clean source has no review macros:

```powershell
Select-String -Path .\main_clean_source.tex -Pattern "advisorreview|pdfrev|printpdfreviewlist"
```

No output means the clean source passed this check.

## Macro Reference

### PDF note at the current position

```latex
\pdfrevnote{comment}
```

- Advisor mode: PDF bubble comment.
- Reviewer mode: hidden.
- Clean source export: removed.

### Mark short text in blue

```latex
\pdfrevmark{text}{comment}
```

- Advisor mode: blue text plus PDF comment.
- Reviewer mode: blue text only.
- Clean source export: keeps `text`.

### Mark inline math in blue

```latex
\pdfrevmath{$\alpha_k>0$}{comment}
```

Keep the full `$...$` in the first argument. This makes clean-source export straightforward.

### Mark display math content in blue

```latex
\[
  \pdfrevformula{\dot V(t)\leq -\alpha\|x(t)\|^2+\eta\|e(t)\|^2}{comment}
\]
```

Use inside display math environments such as `\[...\]` or `equation*`.

### Mark a sentence or short paragraph in blue

```latex
\pdfrevblock{%
This revised sentence explains the model assumption more precisely.
}{comment}
```

Do not put blank lines inside the first argument. Split multiple paragraphs into multiple `\pdfrevblock` calls.

## Example

Build the example advisor and reviewer PDFs:

```powershell
cd examples
latexmk -pdf -interaction=nonstopmode -halt-on-error example_advisor.tex
latexmk -pdf -interaction=nonstopmode -halt-on-error example_reviewer.tex
cd ..
```

Generate a clean example source:

```powershell
.\clean_advisor_review.cmd .\examples\example_review_work.tex .\examples\example_clean_source.tex --force
```

Verify the clean example source:

```powershell
Select-String -Path .\examples\example_clean_source.tex -Pattern "advisorreview|pdfrev|printpdfreviewlist"
```

## VSCode And LaTeX Workshop

When using VSCode / LaTeX Workshop, compile the wrapper files:

```text
main_advisor.tex
main_reviewer.tex
```

Do not compile `main_review_work.tex` directly as the final output. The PDF name follows the root `.tex` file that is compiled.

Use root comments in wrapper files:

```latex
% !TEX root = main_advisor.tex
```

## Clean Source Export

The package option `clean` can hide marks visually, but it does not remove review macros from the source.

For final archival or submission source, use:

```powershell
.\clean_advisor_review.cmd .\main_review_work.tex .\main_clean_source.tex --force
```

The cleanup script removes:

- `\usepackage{advisorreview}`
- `\renewcommand{\advisorreviewauthor}{...}`
- `\pdfrevnote`
- `\pdfrevmark`
- `\pdfrevmath`
- `\pdfrevformula`
- `\pdfrevblock`
- `\printpdfreviewlist`

It uses balanced-brace parsing for the supported review macros. It is not a full TeX parser.

## Known Limitations

- PDF comment display depends on the PDF reader.
- `\pdfrevmark` is for short text, not arbitrary paragraphs.
- `\pdfrevformula` should be used inside math environments.
- Avoid fragile `\left...\right` constructions around complex marked formula fragments; fixed-size delimiters such as `\bigl...\bigr` are often more stable.
- The cleanup script handles the supported macros but may fail on unusual TeX category code tricks or verbatim-like content inside macro arguments.

## License

MIT License. See [LICENSE](LICENSE).

## 中文说明

这个工具用于论文修改阶段：

- 给导师看的 PDF：蓝色文字标记 + PDF 气泡批注，说明修改原因。
- 给审稿人看的 PDF：只保留蓝色文字标记，不显示内部批注。
- 最终干净源码：用脚本从带审阅宏的工作稿生成，不再包含 `advisorreview` 或 `\pdfrev...` 命令。

推荐流程：

1. 复制论文源文件为 `main_review_work.tex`。
2. 在工作稿中加入 `\usepackage{advisorreview}`。
3. 正文使用 `\pdfrevmark`、`\pdfrevmath`、`\pdfrevformula`、`\pdfrevblock`。
4. 编译 `main_advisor.tex` 给导师看。
5. 编译 `main_reviewer.tex` 给审稿人看。
6. 修改确认后运行 `clean_advisor_review.cmd` 生成真正干净的 LaTeX 源码。
