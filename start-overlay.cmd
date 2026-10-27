@echo off
rem Starts the overlay without a console window. Needs Python 3.10+ (python.org installer includes tkinter).
cd /d "%~dp0"
where pyw >nul 2>nul && (start "" pyw -3 run_overlay.py %* & exit /b)
where pythonw >nul 2>nul && (start "" pythonw run_overlay.py %* & exit /b)
echo Python 3.10+ not found. Install it from https://www.python.org/downloads/ or use the .exe from Releases.
pause
