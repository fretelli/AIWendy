# KeelTrader Makefile

.PHONY: help setup dev check check-web check-api test build deploy clean db-migrate db-rollback

# Default target
help:
	@echo "Available commands:"
	@echo "  make check     - Run web checks and API container tests"
	@echo "  make check-web - Run web lint, type-check, and Jest"
	@echo "  make check-api - Build API test runner and run pytest"
	@echo "  make test      - Alias for make check"
	@echo "  make build     - Build production images"
	@echo "  make deploy    - Deploy to production"
	@echo "  make clean     - Clean up generated files"

# Setup development environment
setup:
	@chmod +x scripts/setup.sh
	@./scripts/setup.sh

# Start development servers
dev:
	@echo "Use apps/web/npm run dev for frontend work, or scripts/deploy.sh web --no-deploy for production build validation."

check: check-web check-api

check-web:
	@cd apps/web && npm run lint
	@cd apps/web && npm run type-check
	@cd apps/web && npm test -- --runInBand

check-api:
	@scripts/release-api-overlay.sh --test-only

# Run tests
test: check

# Build production images
build:
	@docker compose build

# Deploy to production
deploy:
	@chmod +x scripts/deploy.sh
	@./scripts/deploy.sh web
	@./scripts/deploy.sh api

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
	@docker compose exec -T api alembic upgrade head

db-rollback:
	@docker compose exec -T api alembic downgrade -1
