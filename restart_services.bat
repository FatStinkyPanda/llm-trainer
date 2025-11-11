@echo off
echo ========================================
echo LLM Trainer - Service Restart Script
echo ========================================
echo.

echo [1/4] Killing existing Python processes...
taskkill /F /IM python.exe 2>nul
if %errorlevel%==0 (
    echo [OK] Stopped all Python processes
) else (
    echo [OK] No existing Python processes found
)

echo.
echo [2/4] Clearing Python cache files...
del /S /Q __pycache__ 2>nul
del /S /Q *.pyc 2>nul
echo [OK] Cache cleared

echo.
echo [3/4] Waiting 3 seconds for cleanup...
timeout /t 3 /nobreak >nul

echo.
echo [4/4] Starting launcher with fresh code...
echo.
python start_llm_trainer.py

pause
