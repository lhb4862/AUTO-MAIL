@echo off
cd /d "%~dp0"

where python >nul 2>&1
if errorlevel 1 (
    echo Python is not installed. Please install Python first.
    pause
    exit /b 1
)

python settings_gui.py
if errorlevel 1 pause
