@echo off
echo KeelTrader Docker Build Script
echo ==========================
echo.
echo Choose build option:
echo 1. Standard build (uses cache)
echo 2. Clean build (no cache)
echo 3. Optimized build (multi-stage, smaller image)
echo 4. China-optimized build (uses China mirrors)
echo.
set /p choice="Enter your choice (1-4): "

if "%choice%"=="1" (
    echo Starting standard build with cache...
    docker-compose build
) else if "%choice%"=="2" (
    echo Starting clean build without cache...
    docker-compose build --no-cache
) else if "%choice%"=="3" (
    echo Starting optimized build...
    docker-compose -f docker-compose.optimized.yml build
) else if "%choice%"=="4" (
    echo Starting China-optimized build...
    REM Temporarily replace Dockerfiles with CN versions
    copy apps\api\Dockerfile apps\api\Dockerfile.backup
    copy apps\web\Dockerfile apps\web\Dockerfile.backup
    copy apps\api\Dockerfile.cn apps\api\Dockerfile
    copy apps\web\Dockerfile.cn apps\web\Dockerfile

    REM Build with China mirrors
    docker-compose build

    REM Restore original Dockerfiles
    move /Y apps\api\Dockerfile.backup apps\api\Dockerfile
    move /Y apps\web\Dockerfile.backup apps\web\Dockerfile
) else (
    echo Invalid choice. Exiting.
    exit /b 1
)

echo.
echo Build complete! You can now run: docker-compose up -d
pause