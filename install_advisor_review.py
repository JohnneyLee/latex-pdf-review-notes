#!/usr/bin/env python
"""Install a personal LaTeX package, standalone scripts and a VS Code recipe."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys


ROOT = Path(__file__).resolve().parent
RUNTIME_FILES = ("build_advisor_review.py", "clean_advisor_review.py")


def typescript_location() -> Path:
    code = shutil.which("code") or shutil.which("code.cmd")
    if code:
        folder = Path(code).resolve().parent.parent
        candidates = [folder / "resources" / "app"]
        candidates.extend(folder.glob("*/resources/app"))
        for candidate in candidates:
            script = candidate / "extensions" / "node_modules" / "typescript" / "lib" / "typescript.js"
            if script.is_file():
                return script
    raise RuntimeError("VS Code's bundled TypeScript parser was not found. No files were installed.")


def replace_with_backup(path: Path, content: bytes) -> Path | None:
    if path.is_file() and path.read_bytes() == content:
        return None
    path.parent.mkdir(parents=True, exist_ok=True)
    backup = None
    if path.exists():
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
        backup = path.with_name(path.name + ".advisorreview.bak-" + stamp)
        with backup.open("xb") as stream:
            stream.write(path.read_bytes())
    path.write_bytes(content)
    return backup


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--settings", type=Path)
    parser.add_argument("--texmf-home", type=Path)
    parser.add_argument("--runtime-home", type=Path,
                        help="Installed scripts directory (default: LOCALAPPDATA/latex-pdf-review-notes)")
    parser.add_argument("--typescript", type=Path)
    args = parser.parse_args(argv)
    try:
        node = shutil.which("node")
        kpsewhich = shutil.which("kpsewhich")
        if not node or not kpsewhich or not shutil.which("latexmk"):
            raise RuntimeError("Existing node, kpsewhich and latexmk executables are required. Nothing was installed.")
        if args.settings:
            settings = args.settings.resolve()
        elif os.environ.get("APPDATA"):
            settings = Path(os.environ["APPDATA"]) / "Code" / "User" / "settings.json"
        else:
            raise RuntimeError("This installer targets VS Code on Windows; specify --settings explicitly elsewhere.")
        typescript = (args.typescript or typescript_location()).resolve()
        runtime = args.runtime_home
        if runtime is None:
            if not os.environ.get("LOCALAPPDATA"):
                raise RuntimeError("LOCALAPPDATA is unavailable; specify --runtime-home explicitly.")
            runtime = Path(os.environ["LOCALAPPDATA"]) / "latex-pdf-review-notes"
        runtime = runtime.resolve()
        if runtime == ROOT:
            raise RuntimeError("The installed runtime must be separate from the downloaded tool directory.")
        # Read every required payload before changing any package, script or setting.
        payload = {name: (ROOT / name).read_bytes() for name in RUNTIME_FILES}
        package_bytes = (ROOT / "advisorreview.sty").read_bytes()
        home = args.texmf_home
        if home is None:
            lookup = subprocess.run([kpsewhich, "-var-value=TEXMFHOME"], check=True,
                                    capture_output=True, text=True)
            home = Path(lookup.stdout.strip())
        home = home.resolve()
        target = home / "tex" / "latex" / "advisorreview" / "advisorreview.sty"
        plan = subprocess.run([node, str(ROOT / "integration" / "vscode_settings.cjs"),
                               str(settings), str(runtime), sys.executable, str(typescript)],
                              check=True, capture_output=True, text=True, encoding="utf-8")
        proposed = json.loads(plan.stdout)
        print(f"Personal package: {target}")
        print(f"Installed scripts: {runtime}")
        print(f"VS Code settings: {settings}")
        print(f"Preserved compiler: {proposed['engine']}")
        print("Changes: copy two runtime scripts; update one tool and one default recipe.")
        print("After installation, the download directory is not needed for builds.")
        print("All other recipes/settings/comments/tasks remain in place. PATH is unchanged.")
        if args.dry_run:
            print("Dry run: no files changed.")
            return 0
        backups = []
        destinations = [(runtime / name, content) for name, content in payload.items()]
        destinations.extend(((target, package_bytes),
                             (settings, proposed["text"].encode("utf-8"))))
        for destination, content in destinations:
            backup = replace_with_backup(destination, content)
            if backup:
                backups.append(str(backup))
        env = os.environ.copy()
        if args.texmf_home:
            env["TEXMFHOME"] = str(home)
        lookup = subprocess.run([kpsewhich, "--all", "advisorreview.sty"], cwd=home,
                                env=env, check=True, capture_output=True, text=True)
        found = [Path(line).resolve() for line in lookup.stdout.splitlines() if line.strip()]
        if target.resolve() not in found:
            raise RuntimeError("The personal package was written but kpsewhich did not find it.")
        record_dir = (settings.parent if args.settings else ROOT) / ".advisorreview"
        record_dir.mkdir(exist_ok=True)
        record = {"package": str(target), "runtime": str(runtime),
                  "scripts": [str(runtime / name) for name in RUNTIME_FILES],
                  "python": sys.executable, "settings": str(settings), "backups": backups,
                  "engine": proposed["engine"], "recipe": proposed["recipe"]}
        (runtime / "installation.json").write_text(
            json.dumps(record, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        (record_dir / "installation.json").write_text(
            json.dumps(record, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print("Installed and verified. Reload VS Code if it has not picked up the new recipe.")
        for backup in backups:
            print(f"Backup: {backup}")
        return 0
    except (OSError, RuntimeError, ValueError, subprocess.CalledProcessError) as error:
        print(str(error), file=sys.stderr)
        if isinstance(error, subprocess.CalledProcessError):
            print(error.stderr or "", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
