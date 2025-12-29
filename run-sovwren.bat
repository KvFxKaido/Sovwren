@echo off
REM Sovwren IDE Launcher (Windows)
REM Friction-free first-run experience

setlocal enabledelayedexpansion
chcp 65001 >nul
set PYTHONUTF8=1
cd /d "%~dp0"

REM Optional glyph sanity check (set SOVWREN_GLYPH_TEST=1)
if /i "%SOVWREN_GLYPH_TEST%"=="1" (
    echo.
    echo Glyph test (U+F17C / U+F489 / U+F120):
    powershell -NoProfile -Command "$OutputEncoding=[Console]::OutputEncoding=[Text.UTF8Encoding]::UTF8; Write-Host ([char]0xF17C) ([char]0xF489) ([char]0xF120)"
    echo.
)

echo.
echo Sovwren IDE
echo Partnership-First Interface
echo.

REM Check Python
where python >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo Python not found. Please install Python 3.8+
    pause
    exit /b 1
)

REM Check Python version
for /f "tokens=*" %%i in ('python -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"') do set PYVER=%%i
echo Python %PYVER%

REM Install dependencies
echo Checking dependencies...

if not exist "venv" (
    echo Creating virtual environment...
    python -m venv venv
)

REM Activate venv
call venv\Scripts\activate.bat

REM Install requirements
if exist "requirements.txt" (
    if exist "requirements.lock" (
        pip install -q -r requirements.lock 2>nul
        if %ERRORLEVEL% neq 0 pip install -r requirements.lock
    ) else (
        pip install -q -r requirements.txt 2>nul
        if %ERRORLEVEL% neq 0 pip install -r requirements.txt
    )
)

echo Dependencies ready

REM Check LM Studio
echo Checking LM Studio...
curl -s -o nul -w "%%{http_code}" http://127.0.0.1:1234/v1/models 2>nul | findstr "200" >nul
if %ERRORLEVEL% equ 0 (
    echo LM Studio connected
) else (
    echo LM Studio not detected at http://127.0.0.1:1234
    echo.
    echo Please start LM Studio and enable the local server:
    echo   1. Open LM Studio
    echo   2. Go to Local Server tab
    echo   3. Load a model
    echo   4. Click 'Start Server'
    echo.
    pause
)

REM Launch IDE
echo.
echo Launching Sovwren IDE...
echo.
python -B sovwren_ide.py

endlocal
