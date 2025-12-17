@echo off
REM
REM Multicam Partner Portal - Development Setup Script (Windows)
REM Usage: scripts\setup.bat [/with-test-users]
REM
REM This script sets up a local development environment:
REM - Creates Python virtual environment
REM - Installs dependencies
REM - Runs database migrations (SQLite)
REM - Loads initial data (camouflage types)
REM - Optionally creates test users
REM

setlocal enabledelayedexpansion

REM Parse arguments
set WITH_TEST_USERS=false
for %%a in (%*) do (
    if /i "%%a"=="/with-test-users" set WITH_TEST_USERS=true
    if /i "%%a"=="--with-test-users" set WITH_TEST_USERS=true
)

echo ========================================
echo   Multicam Partner Portal Setup
echo ========================================
echo.

REM Check if we're in the right directory
if not exist "manage.py" (
    echo Error: manage.py not found.
    echo Please run this script from the project root directory:
    echo   cd \path\to\MCP-3 ^&^& scripts\setup.bat
    exit /b 1
)

REM Check Python version
echo [1/6] Checking Python version...
where python >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo Error: Python is not installed.
    echo Please install Python 3.11 or higher from https://python.org
    exit /b 1
)

for /f "tokens=*" %%i in ('python -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"') do set PYTHON_VERSION=%%i
for /f "tokens=*" %%i in ('python -c "import sys; print(sys.version_info.major)"') do set PYTHON_MAJOR=%%i
for /f "tokens=*" %%i in ('python -c "import sys; print(sys.version_info.minor)"') do set PYTHON_MINOR=%%i

if %PYTHON_MAJOR% lss 3 (
    echo Error: Python 3.11+ required. Found: %PYTHON_VERSION%
    exit /b 1
)
if %PYTHON_MAJOR% equ 3 if %PYTHON_MINOR% lss 11 (
    echo Error: Python 3.11+ required. Found: %PYTHON_VERSION%
    exit /b 1
)
echo [OK] Python %PYTHON_VERSION% found

REM Create virtual environment
echo [2/6] Setting up virtual environment...
if not exist "venv" (
    python -m venv venv
    echo [OK] Virtual environment created
) else (
    echo [OK] Virtual environment already exists
)

REM Activate virtual environment
call venv\Scripts\activate.bat

REM Install dependencies
echo [3/6] Installing dependencies...
pip install --upgrade pip -q
pip install -r requirements.txt -q
if %ERRORLEVEL% neq 0 (
    echo Error: Failed to install dependencies
    exit /b 1
)
echo [OK] Dependencies installed

REM Run migrations
echo [4/6] Running database migrations...
python manage.py migrate --verbosity=0
if %ERRORLEVEL% neq 0 (
    echo Error: Failed to run migrations
    exit /b 1
)
echo [OK] Database migrations complete (SQLite)

REM Load initial data
echo [5/6] Loading initial data...
python manage.py load_initial_data
if %ERRORLEVEL% neq 0 (
    echo Error: Failed to load initial data
    exit /b 1
)
echo [OK] Initial data loaded

REM Optionally create test users
echo [6/6] Test users...
if "%WITH_TEST_USERS%"=="true" (
    python manage.py setup_test_users
    echo [OK] Test users created
) else (
    echo Skipped (use /with-test-users to create)
)

echo.
echo ========================================
echo   Setup Complete!
echo ========================================
echo.
echo Next steps:
echo.
echo   1. Activate the virtual environment:
echo      venv\Scripts\activate
echo.
echo   2. Start the development server:
echo      python manage.py runserver
echo.
echo   3. Visit: http://localhost:8000
echo.

if "%WITH_TEST_USERS%"=="true" (
    echo Test login credentials:
    echo   - partner / partner123
    echo   - primary_inspector / primary_inspector123
    echo   - final_inspector / final_inspector123
    echo   - staff / staff123
    echo.
)

echo Email Configuration (Optional):
echo   By default, emails print to console.
echo   To send real emails via Resend, create .env file:
echo     EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
echo     EMAIL_HOST_PASSWORD=your-resend-api-key
echo   Get API key: https://resend.com/api-keys
echo.
echo For more information, see Docs\DEVELOPMENT.md
echo.

endlocal

