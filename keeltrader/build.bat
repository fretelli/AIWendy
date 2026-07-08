@echo off
setlocal

set TARGET=%1
if "%TARGET%"=="" set TARGET=all

if "%TARGET%"=="-h" goto :usage
if "%TARGET%"=="--help" goto :usage

if not "%2"=="" (
    echo Extra release options are supported by build.sh on Linux/macOS. 1>&2
    exit /b 2
)

if "%TARGET%"=="all" (
    call bash scripts/deploy.sh web --test-only
    if errorlevel 1 exit /b %errorlevel%
    call bash scripts/deploy.sh api --test-only
    exit /b %errorlevel%
)

if "%TARGET%"=="web" (
    call bash scripts/deploy.sh web --test-only
    exit /b %errorlevel%
)

if "%TARGET%"=="api" (
    call bash scripts/deploy.sh api --test-only
    exit /b %errorlevel%
)

if "%TARGET%"=="backend" (
    call bash scripts/deploy.sh api --test-only
    exit /b %errorlevel%
)

echo Unsupported build target: %TARGET% 1>&2
goto :usage_error

:usage
echo Usage:
echo   build.bat [all^|web^|api] [release options]
echo.
echo Build validation uses the same overlay path as production release, but it does
echo not tag latest, restart services, or run production smoke checks.
echo.
echo Examples:
echo   build.bat
echo   build.bat web
echo   build.bat api
exit /b 0

:usage_error
echo.
echo Usage:
echo   build.bat [all^|web^|api] [release options]
exit /b 2
