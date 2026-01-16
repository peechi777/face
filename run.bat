@echo off
echo Starting Face Attendance System...
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" goto Error

".venv\Scripts\python.exe" src\main.py
if %ERRORLEVEL% NEQ 0 pause
goto End

:Error
echo Error: Mismatched environment.
echo Virtual environment (.venv) not found.
echo Please ensure the project is set up correctly.
pause

:End
