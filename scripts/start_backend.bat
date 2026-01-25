@echo off
REM Backend Startup Script for Windows
REM This will start the backend in the current terminal so you can see all logs

echo ============================================================
echo Starting ScholarSync Backend
echo ============================================================
echo.
echo Backend will run on: http://localhost:8000
echo API Docs: http://localhost:8000/api/docs
echo.
echo All logs will appear in this terminal
echo.
echo Press Ctrl+C to stop the server
echo.
echo ============================================================
echo.

cd /d "%~dp0\.."

REM Activate virtual environment if it exists
if exist "venv\Scripts\activate.bat" (
    call venv\Scripts\activate.bat
) else if exist ".venv\Scripts\activate.bat" (
    call .venv\Scripts\activate.bat
)

REM Start the server using the virtual environment Python (updated path for new structure)
if exist "venv\Scripts\python.exe" (
    venv\Scripts\python.exe -m uvicorn apps.api.main:app --reload --host 0.0.0.0 --port 8000
) else if exist ".venv\Scripts\python.exe" (
    .venv\Scripts\python.exe -m uvicorn apps.api.main:app --reload --host 0.0.0.0 --port 8000
) else if exist "backend\venv\Scripts\python.exe" (
    backend\venv\Scripts\python.exe -m uvicorn apps.api.main:app --reload --host 0.0.0.0 --port 8000
) else (
    echo ERROR: Virtual environment not found!
    echo Please create a virtual environment first:
    echo   python -m venv venv
    echo   venv\Scripts\activate
    echo   pip install -r requirements.txt
    pause
    exit /b 1
)
