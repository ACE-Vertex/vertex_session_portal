@echo off
setlocal EnableExtensions

rem VXS_BUILD_BEFORE_LAUNCH_GUARD_000028
rem Always resolve the real Session Portal project root from this launcher.
cd /d "%~dp0"

echo [VXS] Session Portal current-generation launcher
echo [VXS] Root: %CD%
echo [VXS] Step 1/2: npm run build

call npm.cmd run build
set "BUILD_EXIT=%ERRORLEVEL%"

if not "%BUILD_EXIT%"=="0" (
  echo [VXS] BUILD FAILED. Electron will NOT be started.
  echo [VXS] Exit: %BUILD_EXIT%
  exit /b %BUILD_EXIT%
)

if not exist "out\main\index.js" (
  echo [VXS] BUILD CONTRACT FAILED: out\main\index.js was not produced.
  exit /b 66
)

echo [VXS] Step 2/2: launch Electron from current out/main
echo [VXS] Build succeeded.

if not exist "node_modules\.bin\electron.cmd" (
  echo [VXS] Electron launcher not found: node_modules\.bin\electron.cmd
  exit /b 67
)

call "node_modules\.bin\electron.cmd" .
exit /b %ERRORLEVEL%
