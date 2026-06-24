@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

:: Lay duong dan tuyet doi tu vi tri bat file (tranh loi tuong doi)
set "ROOT=%~dp0"
:: Xoa dau \ o cuoi neu co (Windows cmd quy tac)
if "!ROOT:~-1!"=="\" set "ROOT=!ROOT:~0,-1!"

set "BACKEND=!ROOT!\backend"
set "FRONTEND=!ROOT!\frontend"
set "VENV=!BACKEND!\venv"
set "ENV_FILE=!BACKEND!\.env"
set "ENV_EXAMPLE=!BACKEND!\.env.example"
set "REQS=!BACKEND!\requirements.txt"

:: Them Node.js vao PATH neu chua co (xu ly truong hop moi cai xong chua restart)
if exist "C:\Program Files\nodejs\npm.cmd" (
    set "PATH=C:\Program Files\nodejs;!PATH!"
)

echo ============================================================
echo   TBD RAG Chatbot - Khoi dong tu dong
echo   Truong Dai hoc Thai Binh Duong
echo ============================================================
echo.

:: ============================================================
:: BUOC 1: Kiem tra file .env
:: ============================================================
echo [1/5] Kiem tra cau hinh moi truong...

if not exist "!ENV_FILE!" (
    if not exist "!ENV_EXAMPLE!" (
        echo   LOI: Khong tim thay backend\.env.example
        pause
        exit /b 1
    )
    copy "!ENV_EXAMPLE!" "!ENV_FILE!" >nul
    echo   Da tao file .env tu .env.example.
    echo.
    echo   QUAN TRONG: Dien GEMINI_API_KEY vao file .env truoc khi tiep tuc.
    echo   File: !ENV_FILE!
    echo.
    notepad "!ENV_FILE!"
    echo   Nhan phim bat ky khi da chinh sua xong...
    pause >nul
)

:: Canh bao neu key van la mac dinh
findstr /c:"GEMINI_API_KEY=your_gemini_api_key_here" "!ENV_FILE!" >nul 2>&1
if not errorlevel 1 (
    echo   CANH BAO: GEMINI_API_KEY chua duoc doi!
    notepad "!ENV_FILE!"
    echo   Nhan phim bat ky khi da chinh sua xong...
    pause >nul
)

echo   OK
echo.

:: ============================================================
:: BUOC 2: Kiem tra Python venv
:: ============================================================
echo [2/5] Kiem tra Python virtual environment...

if not exist "!VENV!\Scripts\python.exe" (
    echo   Dang tao virtual environment...
    python -m venv "!VENV!"
    if errorlevel 1 (
        echo   LOI: Khong the tao venv. Dam bao Python 3.10 tro len da cai dat.
        pause
        exit /b 1
    )
    echo   Da tao venv thanh cong.
) else (
    echo   Virtual environment da ton tai.
)
echo   OK
echo.

:: ============================================================
:: BUOC 3: Kiem tra va cai dat thu vien Python
:: ============================================================
echo [3/5] Kiem tra thu vien backend Python...

:: Kiem tra bang cach thu import fastapi (dung ngoac kep de tranh parse loi)
"!VENV!\Scripts\python.exe" -c "import fastapi" 2>nul
if errorlevel 1 (
    echo   Chua co thu vien - dang cai dat co the mat 2-5 phut...
    "!VENV!\Scripts\pip.exe" install -r "!REQS!" --quiet --no-warn-script-location
    if errorlevel 1 (
        echo   LOI: Cai dat that bai. Kiem tra ket noi mang va thu lai.
        pause
        exit /b 1
    )
    echo   Da cai dat tat ca thu vien.
) else (
    echo   Thu vien da san sang.
)
echo   OK
echo.

:: ============================================================
:: BUOC 4: Kiem tra va cai dat Node.js modules
:: ============================================================
echo [4/5] Kiem tra thu vien frontend Node.js...

:: Kiem tra npm co san khong
call npm --version >nul 2>&1
if errorlevel 1 (
    echo   CANH BAO: npm khong tim thay. Dam bao Node.js da cai dat dung cach.
    echo   Tai Node.js tai: https://nodejs.org
    pause
    exit /b 1
)

if not exist "!FRONTEND!\node_modules\vite" (
    echo   Dang chay npm install...
    cd /d "!FRONTEND!"
    call npm install
    if errorlevel 1 (
        echo   LOI: npm install that bai. Dam bao Node.js 18 tro len da cai dat.
        pause
        exit /b 1
    )
    cd /d "!ROOT!"
    echo   Da cai dat xong.
) else (
    echo   node_modules da san sang.
)
echo   OK
echo.

:: ============================================================
:: BUOC 5: Khoi dong Backend va Frontend trong cua so rieng
:: ============================================================
echo [5/5] Khoi dong cac dich vu...
echo.

:: Giai phong cong truoc khi khoi dong (tranh loi "address already in use")
echo   Giai phong cong 8001 va 5173 neu dang su dung...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":8001 " ^| findstr "LISTENING" 2^>nul') do (
    taskkill /PID %%a /F >nul 2>&1
)
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":5173 " ^| findstr "LISTENING" 2^>nul') do (
    taskkill /PID %%a /F >nul 2>&1
)
ping -n 3 127.0.0.1 >nul

echo   Dang mo cua so Backend (FastAPI)...
start "TBD Backend" /D "!ROOT!" "!ROOT!\_run_backend.bat"

echo   Doi backend khoi dong (8 giay)...
ping -n 9 127.0.0.1 >nul

echo   Dang mo cua so Frontend (Vite)...
start "TBD Frontend" /D "!ROOT!" "!ROOT!\_run_frontend.bat"

echo   Doi frontend san sang (6 giay)...
ping -n 7 127.0.0.1 >nul

echo   Mo trinh duyet...
rundll32 url.dll,FileProtocolHandler http://localhost:5173

echo.
echo ============================================================
echo   He thong da khoi dong thanh cong!
echo.
echo   Chatbot:   http://localhost:5173
echo   Backend:   http://localhost:8001
echo   API Docs:  http://localhost:8001/api/docs
echo.
echo   De dung: Chay stop.bat hoac dong cac cua so backend/frontend
echo ============================================================
echo.
echo Nhan phim bat ky de dong cua so nay...
pause >nul
endlocal
