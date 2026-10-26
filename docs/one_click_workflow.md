# One-click local workflow

## Accepted behavior

- One Build produces both advisor/reviewer PDFs and a clean LaTeX source.
- A normal document that does not actually load advisorreview follows the
  existing compiler route and produces no new review artifacts.
- Keep the original source and all review macros. Do not create manual wrapper
  files in the manuscript directory. Generated wrappers/cache belong in
  `.advisorreview/<working-source-stem>/`.
- Reuse the original build as one mode when its recorded runtime mode matches.
  Publish the two named PDFs and clean source only after both modes succeed.
- Detect edits to exported clean source using a saved SHA-256 hash and refuse
  to overwrite modified or unowned exports. Never delete user files.
- Install only the personal `.sty` and a user-level LaTeX Workshop recipe.
  Preserve the existing XeLaTeX default engine, other recipes, settings/comments,
  and existing tasks. Do not change PATH, system TeX configuration, or add watchers.

## Implementation and acceptance

- [x] Add failing build tests, including normal documents and failures.
- [x] Add `build_advisor_review.py`, reusing the existing cleanup functions.
- [x] Add a runtime mode log line to the package; change no rendering logic.
- [x] Add `install_advisor_review.py` and a comment-preserving settings editor
  using the TypeScript parser already distributed with VS Code.
- [x] Verify configuration updates in a project-owned test directory first.
- [x] Run the personal installation with backups and verify package lookup.
- [x] Execute the installed VS Code tool command on this project's example;
  inspect PDF comments and independently compile the clean source.
- [x] Run the existing spacing regressions and document verified boundaries.

Tests run sequential builds, including the existing bibliography/resource path
behavior. The source cleaner remains a single-file parser. If another local TeX
input contains review setup/markers, automatic clean export must stop with a
specific message rather than falsely reporting a standalone clean source.

## Use after setup

Run the installer once from the tool repository with an existing Python 3.10+,
Node.js, VS Code and TeX Live/latexmk installation:

```powershell
python .\install_advisor_review.py --dry-run
python .\install_advisor_review.py
```

The normal VS Code Build action uses the new default recipe
`Advisor Review: both PDFs + clean source`. Reload the window if the recipe
list has not refreshed. The manuscript needs only the usual package declaration
and review macros. No project-local tool copy, task, or manual wrapper is needed.
The tool repository must stay at its configured location.

For `main_review_work.tex`, named outputs are written into
`.advisorreview/main_review_work/`: `main_advisor.pdf`, `main_reviewer.pdf`, and
`main_clean_source.tex`. The editor's ordinary root PDF remains at its normal
location. The clean source is an automatically refreshed snapshot; editing that
snapshot prevents later automatic overwrites. The working manuscript is retained.

## Verification record (2026-10-26)

- Six build tests passed: both modes, resource/bibliography paths and repeated
  builds, normal source with a commented package declaration, an explicitly
  clean-mode source, edited-export protection, injected reviewer-compiler failure,
  and refusal to silently clean review code in a secondary input. (Resource and
  repeat assertions share one test.)
- The resource case also compiled the exported source independently; it was
  repeated in a project path containing both spaces and Chinese characters.
- The installation test passed: JSONC comments/unrelated settings survived, a
  backup was created, and a repeated install did not duplicate entries or backups.
- Five existing spacing/color/metadata regression tests passed after adding the
  runtime log marker.
- The actual user installation succeeded. Personal package lookup works, its
  bytes match the repository file, the existing XeLaTeX engine was retained, and
  zero unrelated user-setting values changed. Existing tasks were not edited.
- The exact command installed in VS Code was executed on both existing examples:
  advisor/reviewer/clean export succeeded for the marked working source; the
  ordinary example produced only its normal PDF and no review output directory.
- The existing `examples/latexmkrc` prefers the repository copy, so personal
  installation was additionally verified in `tests/_build/global_install_demo/`,
  which contains only a manuscript and generated build files, no tool files or
  latexmkrc. Its recorder confirms loading `<TEXMFHOME>/tex/latex/advisorreview/`
  and its PDFs contain six advisor comments and zero reviewer comments.
- The real exported example source compiled independently with XeLaTeX. No
  supported review tokens remain in it; the original working file retains them.
- The VS Code graphical Build button itself was not automated; the installed
  command/placeholder substitution and outputs were tested directly.

Generated evidence is retained under `tests/_build/` and
`examples/.advisorreview/`. Real installation/backup paths are recorded locally
in `.advisorreview/installation.json`, which is ignored by Git.

## Boundaries and recovery

This installer targets standard Windows VS Code user settings, not arbitrary
VS Code profiles, remote/WSL installations, or custom multi-tool compiler chains.
Workspace settings can override the user recipe. The existing auto-build and
auto-clean preferences are preserved, including any previously enabled on-save
build. No new background process is installed.

The cleaner is still single-file: review code spread across included TeX files
causes an explicit stop. Relative assets/inputs remain in the original project;
compile the clean source with that original project directory as the working
directory, or prepare a submission bundle separately.

The installer backs up each changed existing file beside it using a timestamped
`.advisorreview.bak-*` suffix. Preserve those backups if restoring the previous
user configuration is needed. The pre-existing README working-tree changes were
retained and extended, not reverted. Nothing was pushed to GitHub.
