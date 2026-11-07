@echo off
REM ================================================================
REM Quick Launcher for IQ NFFICE AI Chatbot Web Interface
REM ================================================================

REM Change directory to project root (parent directory of scripts)
cd /d "%~dp0.."

echo ================================================================
echo    LAUNCHING IQ NFFICE AI CHATBOT WEB INTERFACE (PORT 8080)
echo ================================================================
echo Working Directory: %CD%
echo URL: http://localhost:8080
echo.

start http://localhost:8080
C:\Users\admin\miniconda3\envs\chat\python.exe scripts\run_web_ui.py --port 8080
pause
