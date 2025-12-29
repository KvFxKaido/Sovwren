@echo off
setlocal

set "ROOT=%~dp0"
if "%ROOT:~-1%"=="\" set "ROOT=%ROOT:~0,-1%"

set "WT_PROFILE="
if defined SOVWREN_WT_PROFILE set "WT_PROFILE=%SOVWREN_WT_PROFILE%"

if /i "%~1"=="--in-wt" shift /1

REM Batch files can't "load a font" (they can barely load themselves).
REM If we're launched from Explorer, relaunch inside Windows Terminal so your Nerd Font actually applies.
if not defined WT_SESSION (
    where wt >nul 2>&1
    if %ERRORLEVEL% equ 0 (
        if defined WT_PROFILE (
            wt -p "%WT_PROFILE%" -d "%ROOT%" cmd /k ""%~f0" --in-wt"
        ) else (
            wt -d "%ROOT%" cmd /k ""%~f0" --in-wt"
        )
        exit /b
    )
)

chcp 65001 >nul
cd /d "%ROOT%"
call "%ROOT%\run-sovwren.bat"
