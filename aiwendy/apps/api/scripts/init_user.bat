@echo off
echo.
echo ========================================
echo KeelTrader - Initialize Test Users
echo ========================================
echo.

cd /d "%~dp0\.."

REM Activate virtual environment if exists
if exist "..\..\.venv\Scripts\activate.bat" (
    call ..\..\.venv\Scripts\activate.bat
) else if exist "venv\Scripts\activate.bat" (
    call venv\Scripts\activate.bat
)

REM Run the initialization script
python scripts\init_user.py

echo.
pause