#!/bin/bash

# KeelTrader Setup Script
# This script sets up the development environment

set -e

echo "============================================"
echo "KeelTrader Development Environment Setup"
echo "============================================"

# Check prerequisites
echo "Checking prerequisites..."

# Check Node.js
if ! command -v node &> /dev/null; then
    echo "❌ Node.js is not installed. Please install Node.js 20+"
    exit 1
fi

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python is not installed. Please install Python 3.11+"
    exit 1
fi

# Check Docker
if ! command -v docker &> /dev/null; then
    echo "⚠️  Docker is not installed. You'll need it for databases"
fi

echo "✅ Prerequisites checked"

# Copy environment files
echo "Setting up environment files..."
if [ ! -f .env ]; then
    cp .env.example .env
    echo "✅ Created .env file from .env.example"
    echo "⚠️  Please edit .env and add your API keys"
else
    echo "✅ .env file already exists"
fi

# Start databases with Docker
if command -v docker &> /dev/null; then
    echo "Starting database services..."
    docker-compose up -d db redis
    echo "✅ Database services started"
else
    echo "⚠️  Skipping database setup (Docker not installed)"
fi

# Setup backend
echo "Setting up backend..."
cd apps/api

# Create virtual environment
if [ ! -d venv ]; then
    python3 -m venv venv
    echo "✅ Python virtual environment created"
fi

# Activate virtual environment and install dependencies
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
echo "✅ Backend dependencies installed"

# Run database migrations
echo "Running database migrations..."
alembic upgrade head
echo "✅ Database migrations completed"

cd ../..

# Setup frontend
echo "Setting up frontend..."
cd apps/web
npm install
echo "✅ Frontend dependencies installed"

cd ../..

echo ""
echo "============================================"
echo "✅ Setup completed successfully!"
echo "============================================"
echo ""
echo "Next steps:"
echo "1. Edit .env file and add your API keys"
echo "2. Start the backend: cd apps/api && source venv/bin/activate && uvicorn main:app --reload"
echo "3. Start the frontend: cd apps/web && npm run dev"
echo "4. Open http://localhost:3000 in your browser"
echo ""