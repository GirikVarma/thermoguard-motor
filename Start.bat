@echo off
cd /d "%~dp0"
where py >nul 2>nul
if %errorlevel% equ 0 (
  py server.py
) else (
  start "" ThermoGuard_Standalone.html
)
