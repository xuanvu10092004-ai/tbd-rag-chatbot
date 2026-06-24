@echo off
chcp 65001 >nul
echo ============================================================
echo   TBD RAG Chatbot - Dung tat ca dich vu
echo ============================================================
echo.

echo Dang dung Backend (uvicorn tren cong 8001)...
for /f "tokens=5" %%p in ('netstat -ano ^| findstr ":8001 " ^| findstr "LISTENING"') do (
    taskkill /PID %%p /F >nul 2>&1
    echo   Da dung tien trinh PID %%p
)

echo Dang dung Frontend (vite tren cong 5173)...
for /f "tokens=5" %%p in ('netstat -ano ^| findstr ":5173 " ^| findstr "LISTENING"') do (
    taskkill /PID %%p /F >nul 2>&1
    echo   Da dung tien trinh PID %%p
)

echo.
echo Da dung tat ca dich vu.
timeout /t 2 /nobreak >nul
