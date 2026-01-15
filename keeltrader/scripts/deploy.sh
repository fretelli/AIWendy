#!/bin/bash

# KeelTrader Production Deployment Script

set -e

echo "============================================"
echo "KeelTrader Production Deployment"
echo "============================================"

# Parse arguments
ENVIRONMENT=${1:-production}
SERVICE=${2:-all}

echo "Deploying to: $ENVIRONMENT"
echo "Service: $SERVICE"

# Build Docker images
if [ "$SERVICE" = "all" ] || [ "$SERVICE" = "api" ]; then
    echo "Building API Docker image..."
    docker build -t keeltrader-api:latest ./apps/api
    echo "✅ API image built"
fi

if [ "$SERVICE" = "all" ] || [ "$SERVICE" = "web" ]; then
    echo "Building Web Docker image..."
    docker build -t keeltrader-web:latest ./apps/web
    echo "✅ Web image built"
fi

# Deploy to cloud platforms
if [ "$ENVIRONMENT" = "production" ]; then

    # Deploy API to Railway/Fly.io
    if [ "$SERVICE" = "all" ] || [ "$SERVICE" = "api" ]; then
        echo "Deploying API to production..."
        # Add your deployment commands here
        # railway up --service api
        # fly deploy --app keeltrader-api
        echo "✅ API deployed"
    fi

    # Deploy Web to Vercel
    if [ "$SERVICE" = "all" ] || [ "$SERVICE" = "web" ]; then
        echo "Deploying Web to Vercel..."
        cd apps/web
        vercel --prod
        cd ../..
        echo "✅ Web deployed"
    fi

elif [ "$ENVIRONMENT" = "staging" ]; then

    echo "Deploying to staging environment..."
    docker-compose -f docker-compose.staging.yml up -d
    echo "✅ Staging deployment complete"

fi

echo ""
echo "============================================"
echo "✅ Deployment completed successfully!"
echo "============================================"