@echo off
setlocal

set "SCRIPT_DIR=%~dp0"

if "%~1"=="" (
  echo Usage:
  echo   clean_advisor_review.cmd INPUT.tex OUTPUT.tex [--force]
  echo.
  echo Example:
  echo   clean_advisor_review.cmd MB_LD_review_work.tex MB_LD_clean_source.tex --force
  exit /b 2
)

py -3 --version >nul 2>nul
if not errorlevel 1 (
  py -3 "%SCRIPT_DIR%clean_advisor_review.py" %*
  exit /b %errorlevel%
)

python --version >nul 2>nul
if not errorlevel 1 (
  python "%SCRIPT_DIR%clean_advisor_review.py" %*
  exit /b %errorlevel%
)

python3 --version >nul 2>nul
if not errorlevel 1 (
  python3 "%SCRIPT_DIR%clean_advisor_review.py" %*
  exit /b %errorlevel%
)

echo No usable Python command was found.
echo Install Python, or run clean_advisor_review.py with the full python.exe path.
exit /b 9009
