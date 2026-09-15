@echo off
setlocal
pushd "%~dp0"

set "LAUNCHER=scripts\launch_session_portal_visual_manual_000021.py"

if not exist "%LAUNCHER%" (
    echo [VERTEX SESSION PORTAL]
    echo Launcher not found:
    echo   %CD%\%LAUNCHER%
    echo.
    echo Please confirm this CMD is placed in:
    echo   G:\Vertex_Project\Development\vertex_session_portal
    echo.
    pause
    popd
    exit /b 1
)

rem Prefer the Python visible in PATH.
where python >nul 2>nul
if %errorlevel%==0 (
    python "%LAUNCHER%"
    set "RC=%errorlevel%"
    goto :done
)

rem Fallback for the current workstation environment.
if exist "C:\ProgramData\Anaconda3\python.exe" (
    "C:\ProgramData\Anaconda3\python.exe" "%LAUNCHER%"
    set "RC=%errorlevel%"
    goto :done
)

echo [VERTEX SESSION PORTAL]
echo Python was not found.
echo.
pause
set "RC=1"

:done
if not "%RC%"=="0" (
    echo.
    echo Launch failed. Exit code: %RC%
    pause
)

popd
exit /b %RC%
