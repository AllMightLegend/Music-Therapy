@echo off
REM Setup script for Music Therapy App with Hume AI (Windows)

echo.
echo 🎵 Music Therapy Recommender - Setup Script
echo ============================================
echo.

REM Check Python version
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python is not installed. Please install Python 3.8 or higher.
    echo    Download from: https://www.python.org/downloads/
    pause
    exit /b 1
)

for /f "tokens=*" %%i in ('python --version') do set PYTHON_VERSION=%%i
echo ✓ Python found: %PYTHON_VERSION%
echo.

REM Check if .env exists
if not exist .env (
    echo 📝 Creating .env file from template...
    if exist .env.example (
        copy .env.example .env
        echo ✓ .env created. Please edit it and add your HUME_API_KEY
        echo    Get your key from: https://platform.hume.ai/settings/keys
    ) else (
        echo ❌ .env.example not found!
        pause
        exit /b 1
    )
) else (
    echo ✓ .env file already exists
)

echo.

REM Create virtual environment
if not exist .venv (
    echo 📦 Creating virtual environment...
    python -m venv .venv
    if errorlevel 1 (
        echo ❌ Failed to create virtual environment
        pause
        exit /b 1
    )
    echo ✓ Virtual environment created
) else (
    echo ✓ Virtual environment already exists
)

echo.

REM Activate virtual environment
echo 🔧 Activating virtual environment...
call .venv\Scripts\activate.bat

echo.

REM Install requirements
echo 📚 Installing dependencies...
pip install -r requirements.txt
if errorlevel 1 (
    echo ❌ Failed to install dependencies
    pause
    exit /b 1
)

echo.
echo ✅ Setup complete!
echo.
echo Next steps:
echo 1. Edit .env and add your HUME_API_KEY
echo    - Get your key from: https://platform.hume.ai/settings/keys
echo 2. Download muse_v3.csv to the project root if not already present
echo 3. Run: streamlit run app.py
echo.
pause
