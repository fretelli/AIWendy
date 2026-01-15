# KeelTrader Makefile

.PHONY: help setup dev test build deploy clean

# Default target
help:
	@echo "Available commands:"
	@echo "  make setup    - Set up development environment"
	@echo "  make dev      - Start development servers"
	@echo "  make test     - Run tests"
	@echo "  make build    - Build production images"
	@echo "  make deploy   - Deploy to production"
	@echo "  make clean    - Clean up generated files"

# Setup development environment
setup:
	@chmod +x scripts/setup.sh
	@./scripts/setup.sh

# Start development servers
dev:
	@docker-compose up -d db redis
	@echo "Starting backend and frontend..."
	@tmux new-session -d -s aiwendy-api "cd apps/api && source venv/bin/activate && uvicorn main:app --reload"
	@tmux new-session -d -s aiwendy-web "cd apps/web && npm run dev"
	@echo "Services started in tmux sessions: aiwendy-api, aiwendy-web"

# Run tests
test:
	@echo "Running backend tests..."
	@cd apps/api && source venv/bin/activate && pytest
	@echo "Running frontend tests..."
	@cd apps/web && npm test

# Build production images
build:
	@docker-compose build

# Deploy to production
deploy:
	@chmod +x scripts/deploy.sh
	@./scripts/deploy.sh production all

# Clean up
clean:
	@echo "Cleaning up..."
	@find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name "node_modules" -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name ".next" -exec rm -rf {} + 2>/dev/null || true
	@echo "Clean complete"

# Database operations
db-migrate:
	@cd apps/api && source venv/bin/activate && alembic upgrade head

db-rollback:
	@cd apps/api && source venv/bin/activate && alembic downgrade -1

db-reset:
	@docker-compose down -v
	@docker-compose up -d db redis
	@sleep 5
	@make db-migrate