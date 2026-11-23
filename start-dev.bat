@echo off
rem Start backend (8001) and frontend (5175) in two windows, then open the browser.
rem Close a window (or press Ctrl+C in it) to stop that server.
rem Paths are relative to this file to avoid non-ASCII path issues.
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
  echo [ERROR] .venv not found. See README "1. first-time setup".
  pause
  exit /b 1
)

start "Final Backend :8001" cmd /k ".venv\Scripts\python -m uvicorn app.main:app --app-dir backend --reload --host 127.0.0.1 --port 8001"
start "Final Frontend :5175" /d "%~dp0frontend" cmd /k "npm.cmd run dev -- --host localhost --port 5175 --strictPort"

rem Give Vite a few seconds before opening the page.
timeout /t 6 /nobreak >nul
start "" http://localhost:5175
