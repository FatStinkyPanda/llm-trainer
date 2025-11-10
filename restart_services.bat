@echo off
echo ========================================
echo LLM Trainer - Service Restart Script
echo ========================================
echo.

echo [1/3] Killing existing Python processes...
taskkill /F /IM python.exe 2>nul
if %errorlevel%==0 (
    echo [OK] Stopped all Python processes
) else (
    echo [OK] No existing Python processes found
)

echo.
echo [2/3] Waiting 3 seconds for cleanup...
timeout /t 3 /nobreak >nul

echo.
echo [3/3] Starting launcher...
echo.
python start_llm_trainer.py

pause
