# KeelTrader Makefile

PIP_AUDIT_IMAGE ?= keeltrader-api:base
PIP_AUDIT_DOCKER_TIMEOUT ?= 600
PIP_AUDIT_TIMEOUT ?= 120
PIP_AUDIT_INDEX_URL ?= https://pypi.org/simple/
PIP_AUDIT_VULN_SERVICE ?= osv
PIP_AUDIT_IGNORE_VULNS ?=
PIP_AUDIT_IGNORE_ARGS = $(foreach vuln,$(PIP_AUDIT_IGNORE_VULNS),--ignore-vuln $(vuln))
NPM_AUDIT_REGISTRY ?= https://registry.npmjs.org/
NPM_AUDIT_LEVEL ?= high
NPM_AUDIT_FETCH_RETRIES ?= 3
NPM_AUDIT_FETCH_TIMEOUT ?= 120000

.PHONY: help setup dev check check-web check-api check-api-static check-security-defaults audit audit-root audit-web audit-api audit-api-strict audit-api-static-candidates test build selfhost-smoke up down clean db-migrate db-rollback

# Default target
help:
	@echo "Available commands:"
	@echo "  make check     - Run web checks and API container tests"
	@echo "  make check-web - Run web lint, type-check, and Jest"
	@echo "  make check-api - Build API test runner and run pytest"
	@echo "  make check-api-static - Run lightweight API static contract checks"
	@echo "  make check-security-defaults - Reject hardcoded development default passwords"
	@echo "  make audit     - Run root, web, and API dependency audits"
	@echo "  make audit-root - Check repository content, README governance, and public safety"
	@echo "  make audit-web - Run npm audit for high/critical web dependency issues"
	@echo "  make audit-api - Run strict pip-audit checks for API dependency issues"
	@echo "  make audit-api-strict - Alias for API dependency audit with no vulnerability exceptions"
	@echo "  make audit-api-static-candidates - Report black/isort/mypy candidates without enforcing them"
	@echo "  make test      - Alias for make check"
	@echo "  make build     - Validate distributable API and Web images"
	@echo "  make selfhost-smoke - Run a disposable clean-room Compose smoke test"
	@echo "  make up/down   - Start or stop the local self-hosted stack"
	@echo "  make clean     - Clean up generated files"

# Setup development environment
setup:
	@chmod +x scripts/setup.sh
	@./scripts/setup.sh

# Start development servers
dev:
	@echo "Use apps/web/npm run dev for frontend work, or ./build.sh for container validation."

check: check-web check-api-static check-api

check-web:
	@cd apps/web && npm run lint
	@cd apps/web && npm run type-check
	@cd apps/web && npm test -- --runInBand

check-api:
	@scripts/check-api-docker.sh

check-api-static:
	@scripts/check-api-static.sh

check-security-defaults:
	@scripts/check-public-safety.sh

audit: audit-root audit-web audit-api

audit-root:
	@scripts/audit-root.sh

audit-web:
	@scripts/audit-web.sh

audit-api:
	@docker image inspect "$(PIP_AUDIT_IMAGE)" >/dev/null 2>&1 || { echo "Missing $(PIP_AUDIT_IMAGE). Run make check-api first, or set PIP_AUDIT_IMAGE to an existing Python image." >&2; exit 1; }
	@timeout "$(PIP_AUDIT_DOCKER_TIMEOUT)" docker run --rm -u root -v "$(CURDIR)/apps/api:/src:ro" "$(PIP_AUDIT_IMAGE)" sh -c 'python -m pip install --quiet --disable-pip-version-check --index-url "$(PIP_AUDIT_INDEX_URL)" pip-audit && python -m pip_audit --vulnerability-service "$(PIP_AUDIT_VULN_SERVICE)" --timeout "$(PIP_AUDIT_TIMEOUT)" --index-url "$(PIP_AUDIT_INDEX_URL)" $(PIP_AUDIT_IGNORE_ARGS) -r /src/requirements-prod.txt && python -m pip_audit --vulnerability-service "$(PIP_AUDIT_VULN_SERVICE)" --timeout "$(PIP_AUDIT_TIMEOUT)" --index-url "$(PIP_AUDIT_INDEX_URL)" $(PIP_AUDIT_IGNORE_ARGS) -r /src/requirements.txt'

audit-api-strict:
	@$(MAKE) audit-api PIP_AUDIT_IGNORE_VULNS=

audit-api-static-candidates:
	@docker image inspect "$(PIP_AUDIT_IMAGE)" >/dev/null 2>&1 || { echo "Missing $(PIP_AUDIT_IMAGE). Run make check-api first, or set PIP_AUDIT_IMAGE to an existing Python image." >&2; exit 0; }
	@docker run --rm -u root -v "$(CURDIR)/apps/api:/src:ro" "$(PIP_AUDIT_IMAGE)" sh -lc 'python -m pip install --quiet --disable-pip-version-check --index-url "$(PIP_AUDIT_INDEX_URL)" -r /src/requirements-static.txt && printf "%s\n" "[isort]" "profile=black" "line_length=88" "known_first_party=app" > /tmp/isort-candidate.cfg && cd /src && echo "[candidate] black --check ." && black --check . || true; echo "[candidate] isort --check-only ." && isort --settings-path /tmp/isort-candidate.cfg --check-only . || true; echo "[candidate] mypy ." && mypy . || true'

# Run tests
test: check

# Validate distributable images without deploying
build:
	@./build.sh

selfhost-smoke:
	@scripts/selfhost-smoke.sh

up:
	@docker compose -f docker-compose.selfhost.yml up -d --build

down:
	@docker compose -f docker-compose.selfhost.yml down

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
	@docker compose -f docker-compose.selfhost.yml exec -T api alembic upgrade head

db-rollback:
	@docker compose -f docker-compose.selfhost.yml exec -T api alembic downgrade -1
