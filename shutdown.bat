@echo off
echo Stopping The Scriptorium...

for /f "tokens=5" %%a in ('netstat -ano ^| findstr :8501 ^| findstr LISTENING') do (
    echo Found process PID %%a on port 8501
    taskkill /PID %%a /F >nul 2>&1
    echo Server stopped.
    goto done
)

echo No server found running on port 8501.
:done
pause
