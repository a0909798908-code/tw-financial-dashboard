@echo off
echo ==========================================================
echo   Starting Smart Financial Dashboard System
echo   Front-end: Streamlit  ^|  Back-end: FastAPI (Python)
echo ==========================================================
echo.

:: Detect Anaconda Python
set "CONDA_PATH=C:\Users\user\anaconda3"
if exist "%CONDA_PATH%\python.exe" (
    echo [INFO] Detected Anaconda Python at %CONDA_PATH%
    set "PATH=%CONDA_PATH%;%CONDA_PATH%\Scripts;%CONDA_PATH%\Library\bin;%PATH%"
    set "PYTHON_EXE=%CONDA_PATH%\python.exe"
    set "PIP_CMD=%CONDA_PATH%\python.exe -m pip"
    set "STREAMLIT_CMD=%CONDA_PATH%\Scripts\streamlit.exe"
    set "UVICORN_CMD=%CONDA_PATH%\Scripts\uvicorn.exe"
) else (
    echo [INFO] Using system default python
    set "PYTHON_EXE=python"
    set "PIP_CMD=python -m pip"
    set "STREAMLIT_CMD=streamlit"
    set "UVICORN_CMD=uvicorn"
)

:: Step 1: Install requirements
echo [1/3] Installing dependencies from requirements.txt...
%PIP_CMD% install -r requirements.txt
if %ERRORLEVEL% neq 0 (
    echo.
    echo [ERROR] Failed to install dependencies. Please ensure Python and pip are installed.
    pause
    exit /b %ERRORLEVEL%
)
echo.

:: Step 2: Start FastAPI Backend in background
echo [2/3] Starting FastAPI Backend on http://0.0.0.0:8000 ...
start "FastAPI Backend" /min %PYTHON_EXE% -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Failed to start FastAPI Backend.
    pause
    exit /b %ERRORLEVEL%
)

:: Wait 4 seconds for backend server to spin up and sync database
echo Waiting for backend server to initialize database...
timeout /t 4 /nobreak
echo.

:: Step 3: Start Streamlit Frontend
echo [3/3] Starting Streamlit Frontend...
%PYTHON_EXE% -m streamlit run app.py --server.headless=true
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Failed to start Streamlit Frontend.
    pause
    exit /b %ERRORLEVEL%
)

echo System closed.
pause

