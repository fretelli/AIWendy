#!/bin/bash

# Build script for KeelTrader with optimization options

echo "KeelTrader Docker Build Script"
echo "=========================="
echo ""
echo "Choose build option:"
echo "1. Standard build (uses cache)"
echo "2. Clean build (no cache)"
echo "3. Optimized build (multi-stage, smaller image)"
echo "4. China-optimized build (uses China mirrors)"
echo ""
read -p "Enter your choice (1-4): " choice

case $choice in
    1)
        echo "Starting standard build with cache..."
        docker-compose build
        ;;
    2)
        echo "Starting clean build without cache..."
        docker-compose build --no-cache
        ;;
    3)
        echo "Starting optimized build..."
        docker-compose -f docker-compose.optimized.yml build
        ;;
    4)
        echo "Starting China-optimized build..."
        # Temporarily replace Dockerfiles with CN versions
        cp apps/api/Dockerfile apps/api/Dockerfile.backup
        cp apps/web/Dockerfile apps/web/Dockerfile.backup
        cp apps/api/Dockerfile.cn apps/api/Dockerfile
        cp apps/web/Dockerfile.cn apps/web/Dockerfile

        # Build with China mirrors
        docker-compose build

        # Restore original Dockerfiles
        mv apps/api/Dockerfile.backup apps/api/Dockerfile
        mv apps/web/Dockerfile.backup apps/web/Dockerfile
        ;;
    *)
        echo "Invalid choice. Exiting."
        exit 1
        ;;
esac

echo ""
echo "Build complete! You can now run: docker-compose up -d"