# Review-mark spacing fix (2026-10-26)

## Report and scope

The user supplied three PDF crops showing visually inconsistent spaces around
marked mathematical fragments. The original manuscript source for those crops
was not supplied. The regression document reproduces the same kinds of
fragments; it does not certify the layout of the user's entire manuscript.

The maintained package is `advisorreview.sty` in this repository. The older demo
copy under `paper/test/review_demo/advisor_review_tool/` was not updated.

## Findings from the existing code and reproduction

- `\pdfrevformula` enclosed every fragment in nested math groups inside
  `\mathchoice`. This turned relations/operators into ordinary math atoms,
  changing spaces around `=`, `+`, and `\leq` and disrupting external limits.
- Its appended `\mbox` inserted another math atom. A script following the macro
  could attach to that box rather than to the intended operator.
- `\pdfrevblock` explicitly inserted `\par\smallskip\noindent` before its content
  and `\par\smallskip` afterwards. Review markings therefore changed layout.
- A separate reproduction showed that the previous text-comment path changed
  sentence spacing after a marked sentence. Native annotation nodes fixed it.

Before changing the package, the initial PDF comparison failed for both advisor
and reviewer modes (35,976 changed ink pixels at 144 dpi in that initial
fixture). That figure belongs to the initial fixture, which was later expanded;
it is not a directly comparable before/after benchmark for the final fixture.

## Changes

- Use LaTeX's `\mathcolor`, loading a local `mathcolor.ltx` when needed, rather
  than wrapping formula fragments in ordinary math atoms.
- Encode annotation contents in text mode and emit native PDF text annotations
  without typesetting an extra box. Math annotations precede their fragment so
  they do not intercept following subscripts/superscripts.
- Remove implicit paragraph breaks and vertical spacing from `\pdfrevblock`.
- Retain the existing five public macros, advisor/reviewer/clean options, blue
  RGB `(0, 0, 255)`, author customization, and clean-source exporter.
- Preserve the pre-existing README edits while documenting the changed behavior.

No manuscript theorem, equation, citation, or figure reference was changed.
The mathematical formulas added under `tests/` and `examples/` are test fixtures.

## Executed verification

The following commands were executed with existing local tools, without package
installation or global configuration changes. Each compiler passed all five
tests: glyph layout, comment counts, revision color, custom author/Unicode
contents, and a simulated missing-`mathcolor.ltx` fallback.

```powershell
python -m unittest discover -s tests -v
$env:LATEX_ENGINE = 'xelatex'
python -m unittest discover -s tests -v
$env:LATEX_ENGINE = 'lualatex'
python -m unittest discover -s tests -v
```

The compiler selections were process-local; no persistent environment was changed.
Windows refused to start the TeX Live executables in the sandbox (WinError 623);
the successful runs used approved execution of the existing installation.

In the regression fixture:

- Each advisor PDF contains 25 text comments; reviewer and clean PDFs contain zero.
- The five measured TeX formula boxes have exactly matching width/height/depth.
- Under pdfLaTeX, color-normalized advisor/reviewer glyph images match clean mode
  exactly with annotation icons hidden.
- Word coordinates are checked against a package-free reference within 0.05 PDF
  points. Investigation measured approximately 0.0254 points maximum for XeLaTeX
  and 0.00821 for LuaLaTeX; color-run output rounding prevents exact pixel equality
  with those drivers. A package-free reference can also differ from clean mode
  by 0.001 points due to PDF output rounding.
- The Unicode string `符号修正 (checked) 100%` is recovered intact from the PDF,
  and an author override to `Ada` is recovered intact.

The existing `example_advisor.tex`, `example_reviewer.tex`, and the new
`spacing_comparison.tex` were also compiled with the existing latexmk workflow.
The advisor example retains six comment-list entries. The Windows clean-source
launcher successfully exported the existing example; no supported review tokens
remained in the exported source, and that source compiled independently.

The first clean-source compile was invoked across directories from `examples/`;
Windows latexmk 4.76 converted the input path to backslashes and TeX read it as
control sequences. Running the same compile in the generated source's directory
resolved that path issue. The package and exporter required no additional change.

Generated PDFs, logs, and rendered pages are retained locally under
`tests/_build/` and ignored by Git. `tests/_build/examples/spacing_comparison.pdf`
shows the unmarked reference, previous formula wrapper, and fixed wrapper.

## Remaining boundaries

- PDF viewers choose the appearance of comment icons. Zero-size anchors preserve
  text layout; densely placed icons can still overlap. Interactive opening in
  Acrobat/Sumatra was not tested during this fix; PDF annotation data was inspected.
- No claim of background highlighting is made: revisions remain blue text.
- Without `\mathcolor`/`mathcolor.ltx`, the fallback compiles complete fragments
  but scripts and limits must be inside the marked argument.
- DVI/PostScript output, arbitrary theorem wrappers, and custom global pdfcomment
  appearance/list styles are outside the regression coverage.
- To apply this fix elsewhere, replace that project's actually loaded `.sty` copy
  and rebuild. Neither a global installation nor the GitHub repository is updated
  by these local changes.
