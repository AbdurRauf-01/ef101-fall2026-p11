@echo off
REM Windows bootstrap. Usage: bootstrap.bat start|reset|test
REM Makes sure Python 3.8+ exists, then hands over to launcher.py (which checks Flask, segno ... and shows its own menu).
REM If Python is missing, a menu asks first: 1 install automatically (default, per-user), 2 install it yourself
REM (official links shown), 3 continue anyway, 4 exit. Nothing is installed without that choice.
setlocal
set "ACTION=%~1"
if "%ACTION%"=="" set "ACTION=start"
set "EXTRA=%~2 %~3 %~4"
set "HERE=%~dp0"
cd /d "%~dp0.."
set "PYVER=3.12.10"
set "PYCMD="
set "PRESET=%LAUNCHER_CHOICE%"

REM Fast path: a working venv already exists.
if exist "venv\Scripts\python.exe" (
    "venv\Scripts\python.exe" -c "import sys" >nul 2>&1
    if not errorlevel 1 set PYCMD="%CD%\venv\Scripts\python.exe"
)
if defined PYCMD goto run

call :find_python
if defined PYCMD goto run

:pymenu
echo.
echo A usable Python 3.8 or newer was not found.
echo Official source: https://www.python.org/downloads/
echo.
echo   1. Install Python automatically (default; needs internet; the packages then go into venv\)
echo   2. Install Python yourself, system-wide (shows the official links first)
echo   3. Continue anyway (may stop with an error)
echo   4. Exit
set "CH="
if defined PRESET (
    set "CH=%PRESET%"
    echo Choice %PRESET% ^(preset^).
    set "PRESET="
) else (
    set /p "CH=Choose 1-4 [1]: "
)
if not defined CH set "CH=1"
if "%CH%"=="1" goto py_auto
if "%CH%"=="2" goto py_manual
if "%CH%"=="3" goto py_anyway
if "%CH%"=="4" goto py_exit
goto pymenu

:py_exit
echo Exited. Nothing was installed.
goto end

:py_anyway
echo.
echo Nothing can run without Python 3.8 or newer. Pick 1 or 2, or 4 to exit.
goto pymenu

:py_manual
echo.
echo Install Python yourself. Download only from the official site: https://www.python.org/downloads/
echo   Choose "Install just for me" (no administrator rights needed) and tick "Add python.exe to PATH".
echo   Before running the installer: right-click it, Properties, Digital Signatures. It must show "Python Software Foundation".
echo   Safer this way: this script runs nothing with administrator rights and downloads nothing.
choice /C YN /N /M "Done installing? Y = check again and launch, N = back to the menu [Y/N]: "
if errorlevel 2 goto pymenu
call :find_python
if defined PYCMD goto run
echo.
echo Checked again: Python 3.8 or newer was not found. If you just installed it, close this window and open it again.
goto pymenu

:py_auto
echo.
echo Installing Python for your user account ^(no administrator rights^)...
where winget >nul 2>&1
if errorlevel 1 goto download
winget install -e --id Python.Python.3.12 --scope user --silent --accept-package-agreements --accept-source-agreements
call :find_python
if defined PYCMD goto autook

:download
echo Downloading Python %PYVER% from python.org...
set "INSTALLER=%TEMP%\python-%PYVER%-installer.exe"
if exist "%INSTALLER%" del /q "%INSTALLER%"
powershell -NoProfile -Command "$ErrorActionPreference='Stop'; [Net.ServicePointManager]::SecurityProtocol=[Net.SecurityProtocolType]::Tls12; Invoke-WebRequest -UseBasicParsing 'https://www.python.org/ftp/python/%PYVER%/python-%PYVER%-amd64.exe' -OutFile '%INSTALLER%'; $s=Get-AuthenticodeSignature '%INSTALLER%'; if ($s.Status -ne 'Valid' -or $s.SignerCertificate.Subject -notmatch 'Python Software Foundation') { Remove-Item '%INSTALLER%' -Force; throw 'Installer signature check failed' }"
if errorlevel 1 goto failed
echo Installing Python (no admin rights needed)...
"%INSTALLER%" /quiet InstallAllUsers=0 PrependPath=1 Include_launcher=0 Include_test=0
del /q "%INSTALLER%" >nul 2>&1
call :find_python
if defined PYCMD goto autook

:failed
echo.
echo Could not install Python automatically. Check your internet connection, or pick option 2 and install it yourself.
goto pymenu

:autook
REM The user already chose "install automatically", so the packages step does not ask again.
set "LAUNCHER_CHOICE=1"

:run
%PYCMD% "%HERE%launcher.py" %ACTION% %EXTRA%

:end
echo.
pause
endlocal
exit /b

:find_python
REM Sets PYCMD to a working Python 3.8+ command, or leaves it empty.
set "PYCMD="
py -3 -c "import sys; sys.exit(0 if sys.version_info>=(3,8) else 1)" >nul 2>&1
if not errorlevel 1 (
    set PYCMD=py -3
    exit /b 0
)
python -c "import sys; sys.exit(0 if sys.version_info>=(3,8) else 1)" >nul 2>&1
if not errorlevel 1 (
    set PYCMD=python
    exit /b 0
)
REM Just installed: PATH of this window is not refreshed yet, so look in the usual per-user locations.
for /d %%D in ("%LOCALAPPDATA%\Programs\Python\Python3*") do (
    if exist "%%~D\python.exe" (
        "%%~D\python.exe" -c "import sys; sys.exit(0 if sys.version_info>=(3,8) else 1)" >nul 2>&1
        if not errorlevel 1 set PYCMD="%%~D\python.exe"
    )
)
exit /b 0
