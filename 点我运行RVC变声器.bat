@echo off
setlocal enabledelayedexpansion

REM Get the directory where this bat file is located
set SCRIPT_DIR=%~dp0

REM Define the exe path
set EXE_PATH=%SCRIPT_DIR%ComfyVoiceGen.exe

echo Running: %EXE_PATH% 3
"%EXE_PATH%" 3

REM Check if execution was successful
if errorlevel 1 (
    echo.
    echo Error: Script failed with exit code %errorlevel%
    pause
    exit /b %errorlevel%
)

echo.
echo Script executed successfully
pause