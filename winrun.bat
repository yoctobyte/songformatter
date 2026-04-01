@echo off
setlocal

set "ROOT_DIR=%~dp0"
set "VENV_DIR=%ROOT_DIR%.venv"
set "REQUIREMENTS_FILE=%ROOT_DIR%requirements.txt"
set "STAMP_FILE=%VENV_DIR%\.requirements.stamp"

if not exist "%REQUIREMENTS_FILE%" (
    echo Missing %REQUIREMENTS_FILE%
    exit /b 1
)

if not exist "%VENV_DIR%\Scripts\python.exe" (
    py -3 -m venv "%VENV_DIR%"
    if errorlevel 1 exit /b 1
)

for /f %%i in ('certutil -hashfile "%REQUIREMENTS_FILE%" SHA256 ^| findstr /r /v "hash of file CertUtil"') do (
    if not defined CURRENT_STAMP set "CURRENT_STAMP=%%i"
)

set "INSTALLED_STAMP="
if exist "%STAMP_FILE%" (
    set /p INSTALLED_STAMP=<"%STAMP_FILE%"
)

if /i not "%CURRENT_STAMP%"=="%INSTALLED_STAMP%" (
    "%VENV_DIR%\Scripts\python.exe" -m pip install --upgrade pip
    if errorlevel 1 exit /b 1
    "%VENV_DIR%\Scripts\python.exe" -m pip install -r "%REQUIREMENTS_FILE%"
    if errorlevel 1 exit /b 1
    >"%STAMP_FILE%" echo %CURRENT_STAMP%
)

"%VENV_DIR%\Scripts\python.exe" "%ROOT_DIR%SongFormatter.py" %*
