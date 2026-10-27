# One-click local workflow

## Accepted behavior

- One Build produces both advisor/reviewer PDFs and clean source only if a
  supported review command actually executes in the normal compile.
- A document with no executed review commands follows the normal compiler route,
  even with the package loaded. Do not create or refresh review artifacts.
- A used but undefined review command without the package must fail with a
  specific missing-package hint, retaining the original LaTeX error.
- Keep the original source and all review macros. Do not create manual wrapper
  files in the manuscript directory. Generated wrappers/cache belong in
  `.advisorreview/<working-source-stem>/`.
- Reuse the original build as one mode when its recorded runtime mode matches.
  Publish the two named PDFs and clean source only after both modes succeed.
- Detect edits to exported clean source using a saved SHA-256 hash and refuse
  to overwrite modified or unowned exports. Never delete user files.
- Install the personal `.sty`, two standalone runtime scripts in
  `%LOCALAPPDATA%\latex-pdf-review-notes`, and a user-level LaTeX Workshop recipe.
  The recipe must not depend on the download directory after setup.
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
The installed recipe calls `%LOCALAPPDATA%\latex-pdf-review-notes\build_advisor_review.py`,
which imports the installed `clean_advisor_review.py` beside it. The download
directory can be moved or deleted after successful installation. Keep the
installed directory, personal macro package, Python and TeX tools available.
The optional `--runtime-home` selects a different permanent scripts directory.
Rerun setup from a fresh download to update installed copies, or with a new Python
interpreter if its location changes. No `.cmd` is used by the installed recipe.

For `main_review_work.tex`, named outputs are written into
`.advisorreview/main_review_work/`: `main_advisor.pdf`, `main_reviewer.pdf`, and
`main_clean_source.tex`. The editor's ordinary root PDF remains at its normal
location. The clean source is an automatically refreshed snapshot; editing that
snapshot prevents later automatic overwrites. The working manuscript is retained.
These extra outputs are conditional on actual review-command execution. Removing
all marks makes the next Build normal-only; every existing export/cache file is
retained unchanged and is not a result of that latest normal-only build.

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

## Standalone installation update (2026-10-27)

The earlier 2026-10-26 installation copied only the macro package and pointed
VS Code at scripts in the repository. That version required the repository to
remain in place. The current installer also copies the two runtime scripts and
points the recipe at those copies; its Node/TypeScript integration remains a
setup-only dependency. Read all required payloads before modifying any files.
Existing changed files receive timestamped backups; repeated installation with
unchanged payloads does not duplicate recipes or script backups.

The installation record now also lives at `<runtime>/installation.json`, so it
survives removal of the download. A copy remains in the download's ignored
`.advisorreview/installation.json`. This is not a realtime edit history and is
separate from each manuscript's clean-export ownership manifest.

Verification performed on 2026-10-27:

- `python -m unittest discover -s tests -v`: 15 tests passed in 67.359 seconds.
  The four installation tests cover an explicit runtime path and JSONC
  preservation/idempotence; the default runtime path plus builds without the
  original download path; upgrade backups; and missing-payload refusal before
  changing scripts, macro package or settings.
- The unavailable-download test installs from a project-owned copy, renames
  that download directory, and runs the command extracted from the generated
  settings in a separate manuscript directory. It removes inherited TEXINPUTS
  and PYTHONPATH overrides. Both PDFs, all five macro types, independent clean
  compilation, unchanged source and ordinary compilation pass. Recorder evidence
  confirms the installed personal package. No original user directory was moved
  or deleted to perform this test.
- Upgraded the actual user installation: scripts are now under
  `C:\Users\Johnn\AppData\Local\latex-pdf-review-notes`. The actual user settings
  were backed up as `settings.json.advisorreview.bak-20261027T034404723985Z`.
  Parsed comparisons against that backup confirm only the build-script path
  changed; the existing Python path, XeLaTeX engine, other tools, recipes and
  unrelated setting values remain unchanged.
- Executed the exact real installed recipe command (substituting its document
  and output-directory placeholders) in `tests/_build/installed_runtime_demo/`,
  containing no tool files or local latexmkrc. XeLaTeX generated five advisor
  comments, zero reviewer comments and clean source without supported review
  code. The clean source compiled independently, and the ordinary manuscript
  produced only its normal PDF. Its recorder loads the personal `.sty`.
- The graphical VS Code Build button was not automated. Verification scripts,
  sample manuscripts and generated evidence are retained under `tests/_build/`.
  The sandbox redirects LOCALAPPDATA and cannot start this TeX runtime reliably
  (WinError 623), so the real installation and compiler checks used approved
  ordinary local processes. No dependency installation or PATH change occurred.

## Runtime usage routing (2026-10-27)

The package-loading-only rule was replaced with execution tracking. Each of the
five supported public review commands sets one global flag without adding any
layout material. The LaTeX `enddocument/afterlastpage` hook prints
`ADVISORREVIEW-USED:yes|no`, including commands executed by end-document hooks.
This requires LaTeX 2020-10-01 or newer. The flag counts TeX execution, not proof
that content is visible in a shipped page; measuring/boxed content can execute.

The builder still performs the normal build first. With no loaded package it
returns the normal PDF; with the package loaded but `USED:no`, it also returns
only the normal PDF and explicitly reports that previous exports were retained.
It does not create, validate, rewrite or remove the review output tree in this
case, even when an old clean export has been hand-edited. Used commands still
trigger both review modes and clean export in clean/reviewer preview modes.

On a failed build, the builder retains the original log/error and adds a hint
only when the first undefined command is a supported review command and the
recorder shows that the package was not loaded. Other undefined commands are
not reclassified. Missing usage reports in old local package copies stop with
an update instruction and the loaded package path rather than silently skipping
review export.

Verified after resuming the interrupted task:

- `python -m unittest discover -s tests -v`: all **26 tests passed**, 219.509
  seconds. This includes all five commands, empty explanations, grouped calls,
  clean preview, unused packages in all three modes, comments/verbatim/uncalled
  macros/inactive input branches, late end hooks, five missing-package errors,
  unrelated errors, old package refusal, nested cleaning, installation tests,
  resources/bibliography and spacing/color/author/Unicode regressions.
- Marked-to-unmarked builds preserve the entire existing export tree's bytes
  and modification timestamps, including a deliberately edited clean-source
  fixture; repeating a cached normal-only build also preserves it.
- The packaged desktop app resolves the former AppData runtime path into its
  private LocalCache even when given explicitly. Read-only previews confirmed
  this; the installer itself was not rewritten to guess around it. The real
  installation now uses the supported explicit runtime option:
  `--runtime-home C:\Users\Johnn\texmf\scripts\advisorreview`. The original
  AppData installation remained in place at that verification stage; the
  explicit cleanup recorded below later removed it. Daily Build still uses the
  same recipe.
- Installation refreshed the personal package and standalone scripts, retained
  XeLaTeX, and backed up changed files. This run's backup names end in
  `advisorreview.sty.advisorreview.bak-20261027T075844570871Z` and
  `settings.json.advisorreview.bak-20261027T075844571716Z`. The parsed settings
  comparison confirms only the tool's script path changed, not other settings,
  recipes, tools, engine arguments or the Python interpreter.
- The exact installed recipe command/placeholder substitutions were executed
  on a fresh project without local tool files or inherited TEXINPUTS/PYTHONPATH.
  Loaded-but-unused produced only normal PDF. Active markers produced five
  advisor comments, zero reviewer comments, and clean source that compiled
  independently. Removing markers while retaining the package kept exports
  unchanged; a separate missing-package input produced the explicit hint and
  original undefined-command error. A separate ordinary input built normally.
- **35 pre-existing export/cache files** under the example and earlier real
  installation demo retained identical SHA-256 hashes and modification times.
  Evidence, source snapshots, expected error log and `verification.json` are
  retained in `tests/_build/usage_routing_real_install/`. No actual VS Code UI
  click was automated; its configured command was tested directly.

One acceptance attempt intentionally removed the package from a previously
marked test job and failed earlier while reading stale `.aux` data containing
`\ulp@afterend`. That was not an executed missing review command and was correctly
left as the original error. The failed fixture was retained; separate fresh
inputs were then used to verify the missing-package and ordinary routes. This
cache boundary is documented in README. No auxiliary files or old PDFs were
automatically deleted to obtain a passing result.

## Explicit old-runtime cleanup (2026-10-27)

The user subsequently requested removal of the inactive installation rather
than retaining it for comparison. The active VS Code entry was verified to use
`C:\Users\Johnn\texmf\scripts\advisorreview\build_advisor_review.py`; project
configuration searches found no remaining reference to the old AppData runtime.
The logical old AppData path and its packaged-app LocalCache path were verified
to identify the same directory, not two independent installations.

Cleanup validated the exact absolute target and every child: only the two old
scripts, their installation record, old in-directory backups and Python bytecode
were allowed; unexpected files, subdirectories or reparse points would stop the
operation. Native PowerShell removed that one inactive directory: **6 files,
34,962 bytes**. Both old path aliases were then absent, and the active script
still existed. No manuscript, PDF/source export, personal macro package, active
runtime or settings backup outside that old directory was deleted.

README documents the same migration/cleanup boundary in English and Chinese.
This does not introduce automatic cleanup or a new background process.
After cleanup, a fresh XeLaTeX smoke build through the active installed script
still produced both PDFs and clean source: one advisor comment, zero reviewer
comments, and no supported review tokens in the clean source. This check wrote
only a new `tests/_build/post_cleanup_smoke/` fixture; it did not rebuild or
overwrite the existing exported manuscripts. No program logic changed during
cleanup/publication; the preceding 26-test regression result remains the recorded
full-suite check, not a claim that the full suite ran again at publication time.

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
retained and extended, not reverted. Installation and verification do not publish
automatically; publishing is a separate action requiring user authorization.
