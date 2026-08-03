@echo off
REM Build VOXD.exe via PyInstaller on Windows.
REM Prereqs: python, pip, pyinstaller, Inno Setup (ISCC on PATH).
REM Usage: installers\windows\build-exe.cmd

setlocal
cd /d "%~dp0\..\.."

echo ==^> Creating virtual environment
python -m venv venv
call venv\Scripts\activate.bat

echo ==^> Installing dependencies
pip install --upgrade pip
pip install -r requirements.txt pyinstaller

echo ==^> Building model discovery icon (ICO)
python -c "import sys; sys.path.insert(0,'.'); from app.core.model import MODELS; print(len(MODELS),'models registered')"

echo ==^> PyInstaller build
pyinstaller --noconfirm --clean installers\windows\voxd.spec

echo ==^> Building installer with Inno Setup (if ISCC available)
where iscc >nul 2>&1
if %errorlevel%==0 (
  iscc installers\windows\voxd.iss
) else (
  echo iscc not found. Build VOXD.exe manually, or install Inno Setup 6 and re-run.
)

echo Done. Outputs in build\windows\
endlocal
