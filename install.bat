@echo off
REM AgenticRAG MCP Server Installation Script for Windows

echo ========================================
echo    AgenticRAG MCP Server Installer
echo ========================================
echo.

REM Check Python version
echo [INFO] Checking Python version...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python is not installed or not in PATH.
    echo Please install Python 3.8 or higher from https://python.org
    pause
    exit /b 1
)

for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PYTHON_VERSION=%%i
echo [SUCCESS] Python %PYTHON_VERSION% detected
echo.

REM Create virtual environment
echo [INFO] Creating virtual environment...
if exist venv (
    echo [WARNING] Virtual environment already exists. Using existing environment.
) else (
    python -m venv venv
    echo [SUCCESS] Virtual environment created
)
echo.

REM Activate virtual environment
echo [INFO] Activating virtual environment...
call venv\Scripts\activate.bat

REM Upgrade pip
echo [INFO] Upgrading pip...
python -m pip install --upgrade pip setuptools wheel >nul 2>&1

REM Install dependencies
echo [INFO] Installing dependencies...
echo This may take a few minutes...
pip install -r requirements.txt >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Failed to install dependencies.
    pause
    exit /b 1
)
echo [SUCCESS] Dependencies installed
echo.

REM Create necessary directories
echo [INFO] Creating necessary directories...
if not exist chroma_db mkdir chroma_db
if not exist logs mkdir logs
echo [SUCCESS] Directories created
echo.

REM Setup .env file
echo [INFO] Setting up environment configuration...
if exist .env (
    echo [WARNING] .env file already exists. Skipping configuration.
    echo To reconfigure, delete the .env file and run this script again.
) else (
    copy .env.example .env >nul
    echo.
    echo =======================================
    echo API Key Configuration
    echo =======================================
    echo.
    
    set /p OPENAI_KEY="Enter your OpenAI API key (sk-...): "
    set /p ANTHROPIC_KEY="Enter your Anthropic API key (sk-ant-...): "
    
    REM Update .env file using PowerShell
    powershell -Command "(Get-Content .env) -replace 'OPENAI_API_KEY=sk-...', 'OPENAI_API_KEY=%OPENAI_KEY%' | Set-Content .env"
    powershell -Command "(Get-Content .env) -replace 'ANTHROPIC_API_KEY=sk-ant-...', 'ANTHROPIC_API_KEY=%ANTHROPIC_KEY%' | Set-Content .env"
    
    echo [SUCCESS] Environment configuration completed
)
echo.

REM Get absolute path
set ABSOLUTE_PATH=%cd%

REM Create configuration snippet
echo [INFO] Creating Claude configuration snippet...
(
echo {
echo   "mcpServers": {
echo     "agenticrag": {
echo       "command": "python",
echo       "args": [
echo         "%ABSOLUTE_PATH%\mcp_launcher.py"
echo       ],
echo       "env": {
echo         "OPENAI_API_KEY": "%OPENAI_KEY%",
echo         "ANTHROPIC_API_KEY": "%ANTHROPIC_KEY%"
echo       }
echo     }
echo   }
echo }
) > claude_config_snippet.json

echo.
echo =======================================
echo [SUCCESS] Installation completed!
echo =======================================
echo.
echo [INFO] Next steps:
echo.
echo 1. Add the AgenticRAG server to Claude:
echo    - Open %%APPDATA%%\Claude\claude_desktop_config.json
echo    - Add the configuration from: claude_config_snippet.json
echo.
echo 2. Restart Claude to load the new MCP server
echo.
echo 3. Use the following tools in Claude:
echo    - init_repo: Index a repository for search
echo    - search_repo: Search indexed repositories
echo    - get_repo_stats: Get repository statistics
echo.
echo For more information, see README.md
echo.

set /p TEST_SERVER="Would you like to test the server now? (y/n): "
if /i "%TEST_SERVER%"=="y" (
    echo [INFO] Starting test server...
    echo Press Ctrl+C to stop the test server
    python -m src.main
)

pause