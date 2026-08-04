@echo off
REM Build VOXD.exe via PyInstaller on Windows.
REM Prereqs: python, pip, pyinstaller, Inno Setup (ISCC on PATH).
REM Usage: installers\windows\build-exe.cmd [version]
REM        (version defaults to the version in app\__init__.py)

setlocal
cd /d "%~dp0\..\.."

if "%~1"=="" (
  for /f %%v in ('python -c "from app import __version__; print(__version__)"') do set VOXD_VERSION=%%v
) else (
  set VOXD_VERSION=%~1
)

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
  iscc /DMyAppVersion=%VOXD_VERSION% installers\windows\voxd.iss
) else (
  echo iscc not found. Build VOXD.exe manually, or install Inno Setup 6 and re-run.
)

echo Done. Outputs in build\windows\ (%VOXD_VERSION%)
endlocal
