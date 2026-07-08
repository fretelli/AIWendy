# KeelTrader Makefile

PIP_AUDIT_IMAGE ?= keeltrader-api:base
PIP_AUDIT_DOCKER_TIMEOUT ?= 600
PIP_AUDIT_TIMEOUT ?= 120
PIP_AUDIT_INDEX_URL ?= https://mirrors.aliyun.com/pypi/simple/
PIP_AUDIT_VULN_SERVICE ?= osv
# FastAPI 0.111 pins Starlette 0.37.x. FastAPI 0.139 + Starlette 1.x was
# tested and changes route mounting semantics, so keep these as explicit,
# reviewable exceptions until a dedicated framework migration.
PIP_AUDIT_IGNORE_VULNS ?= PYSEC-2026-161 PYSEC-2026-249 PYSEC-2026-248 PYSEC-2026-1943 PYSEC-2026-1941 CVE-2026-48818 CVE-2026-48817
PIP_AUDIT_IGNORE_ARGS = $(foreach vuln,$(PIP_AUDIT_IGNORE_VULNS),--ignore-vuln $(vuln))

.PHONY: help setup dev check check-web check-api audit audit-web audit-api audit-api-strict test build deploy clean db-migrate db-rollback

# Default target
help:
	@echo "Available commands:"
	@echo "  make check     - Run web checks and API container tests"
	@echo "  make check-web - Run web lint, type-check, and Jest"
	@echo "  make check-api - Build API test runner and run pytest"
	@echo "  make audit     - Run web and API dependency audits"
	@echo "  make audit-web - Run npm audit for high/critical web dependency issues"
	@echo "  make audit-api - Run pip-audit for API dependency issues"
	@echo "  make audit-api-strict - Run API dependency audit without accepted Starlette exceptions"
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

audit: audit-web audit-api

audit-web:
	@cd apps/web && npm audit --audit-level=high

audit-api:
	@docker image inspect "$(PIP_AUDIT_IMAGE)" >/dev/null 2>&1 || { echo "Missing $(PIP_AUDIT_IMAGE). Run make check-api first, or set PIP_AUDIT_IMAGE to an existing Python image." >&2; exit 1; }
	@timeout "$(PIP_AUDIT_DOCKER_TIMEOUT)" docker run --rm -u root -v "$(CURDIR)/apps/api:/src:ro" "$(PIP_AUDIT_IMAGE)" sh -c 'python -m pip install --quiet --disable-pip-version-check pip-audit && python -m pip_audit --vulnerability-service "$(PIP_AUDIT_VULN_SERVICE)" --timeout "$(PIP_AUDIT_TIMEOUT)" --index-url "$(PIP_AUDIT_INDEX_URL)" $(PIP_AUDIT_IGNORE_ARGS) -r /src/requirements-prod.txt && python -m pip_audit --vulnerability-service "$(PIP_AUDIT_VULN_SERVICE)" --timeout "$(PIP_AUDIT_TIMEOUT)" --index-url "$(PIP_AUDIT_INDEX_URL)" $(PIP_AUDIT_IGNORE_ARGS) -r /src/requirements.txt'

audit-api-strict:
	@$(MAKE) audit-api PIP_AUDIT_IGNORE_VULNS=

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
