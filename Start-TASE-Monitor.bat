@echo off
if /i "%~1"=="__openbrowser__" goto :openbrowser

chcp 65001 >nul
set PYTHONUTF8=1

set "PROJECT_ROOT=%~dp0"
set "BACKEND_DIR=%PROJECT_ROOT%backend"
set "VENV_DIR=%BACKEND_DIR%\.venv"
set "VENV_PY=%VENV_DIR%\Scripts\python.exe"

echo ============================================================
echo   TASE Spread Monitor
echo ============================================================
echo.

py -3 -c "import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)" >nul 2>nul
if %errorlevel%==0 (
    set "PYLAUNCHER=py -3"
    goto :python_found
)

python -c "import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)" >nul 2>nul
if %errorlevel%==0 (
    set "PYLAUNCHER=python"
    goto :python_found
)

echo.
echo [ERROR] A working Python 3.11 or newer was not found on this computer.
echo.
echo   Please install Python from:
echo       https://www.python.org/downloads/
echo.
echo   IMPORTANT: on the first setup screen, check the box that says
echo   "Add python.exe to PATH" before clicking Install Now.
echo.
echo   After installing, please RESTART THE COMPUTER once, then
echo   double-click this file again.
echo.
pause
exit /b 1

:python_found
echo Found Python:
%PYLAUNCHER% --version
echo.

if exist "%VENV_PY%" goto :env_ready

echo First-time setup: creating a private Python environment for this app...
echo This only happens once and may take a minute or two. Please wait...
echo.
%PYLAUNCHER% -m venv "%VENV_DIR%"
if not exist "%VENV_PY%" (
    echo.
    echo [ERROR] Failed to create the Python environment.
    pause
    exit /b 1
)

echo.
echo Installing required packages ^(this needs an internet connection^)...
echo.
pushd "%BACKEND_DIR%"
"%VENV_PY%" -m pip install --upgrade pip
"%VENV_PY%" -m pip install .
set "INSTALL_RESULT=%errorlevel%"
popd
if not "%INSTALL_RESULT%"=="0" (
    echo.
    echo [ERROR] Failed to install the required packages.
    echo Please check your internet connection and try again.
    pause
    exit /b 1
)
echo.
echo Setup complete.
echo.

:env_ready

pushd "%BACKEND_DIR%"
if errorlevel 1 (
    echo [ERROR] Could not find the "backend" folder next to this launcher.
    pause
    exit /b 1
)

if not exist ".env" (
    echo.
    echo ============================================================
    echo   Missing configuration file: backend\.env
    echo ============================================================
    echo.
    echo   This app needs a small settings file named ".env" for the
    echo   email alerts. It was not found at:
    echo.
    echo       %BACKEND_DIR%\.env
    echo.
    echo   Copy the .env file Ben gave you into the "backend" folder,
    echo   making sure it is named exactly ".env" ^(not ".env.txt"^),
    echo   then double-click this launcher again.
    echo.
    pause
    popd
    exit /b 1
)

echo Starting TASE Spread Monitor...
echo Your browser will open automatically in a moment.
echo.
echo To stop monitoring, simply close this window.
echo ============================================================
echo.

start "" /min "%~f0" __openbrowser__
"%VENV_PY%" -m uvicorn app.main:app --host 127.0.0.1 --port 8099

echo.
echo ============================================================
echo   The server has stopped.
echo ============================================================
echo.
pause
popd
exit /b 0

:openbrowser
where curl >nul 2>nul
if errorlevel 1 goto :openbrowser_fallback

for /l %%i in (1,1,30) do (
    curl -s -o nul http://127.0.0.1:8099/ 2>nul
    if not errorlevel 1 goto :openbrowser_launch
    timeout /t 1 /nobreak >nul
)

:openbrowser_fallback
timeout /t 3 /nobreak >nul

:openbrowser_launch
start http://127.0.0.1:8099
exit /b 0
