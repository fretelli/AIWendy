# Git Workflow Setup Guide

This guide explains how to activate and use the new Git workflow improvements.

## What Was Added

### 1. Testing Infrastructure
- ✅ Frontend: Jest + React Testing Library
- ✅ Backend: pytest with coverage
- ✅ CI: Automated testing on every push/PR

### 2. Code Quality Tools
- ✅ Python: black, isort, flake8, mypy
- ✅ JavaScript/TypeScript: ESLint, Prettier
- ✅ Pre-commit hooks for automatic formatting

### 3. Commit Message Standards
- ✅ Commitlint with Conventional Commits
- ✅ Husky for Git hooks
- ✅ Lint-staged for automatic code formatting

### 4. CI/CD Improvements
- ✅ Full test suite in CI
- ✅ Build verification
- ✅ Code coverage reporting
- ✅ Release workflow with tests

---

## Setup Instructions

### Step 1: Install Root Dependencies

```bash
# In project root directory
cd C:\github_project\AIWendy
npm install
```

This installs:
- commitlint
- husky
- lint-staged

### Step 2: Initialize Husky

```bash
npx husky install
```

This activates the Git hooks for:
- Commit message validation
- Pre-commit code formatting

### Step 3: Install Frontend Dependencies

```bash
cd aiwendy/apps/web
npm install
```

This installs the new testing dependencies:
- jest
- @testing-library/react
- @testing-library/jest-dom

### Step 4: Install Pre-commit (Python)

```bash
cd aiwendy/apps/api
pip install pre-commit
pre-commit install
```

This activates Python code quality hooks.

### Step 5: Test the Setup

#### Test Frontend
```bash
cd aiwendy/apps/web
npm run test
npm run build
```

#### Test Backend
```bash
cd aiwendy/apps/api
pytest
black --check .
isort --check-only .
flake8 .
```

---

## How to Use

### Making a Commit

When you commit, the following happens automatically:

1. **Pre-commit hook runs**:
   - Formats JavaScript/TypeScript code (ESLint + Prettier)
   - Formats Python code (black + isort)
   - Runs flake8 and mypy checks

2. **Commit message validation**:
   - Checks if your message follows Conventional Commits format
   - Example: `feat(api): add new endpoint`

### Commit Message Format

```
<type>(<scope>): <subject>

Examples:
feat(api): add user authentication
fix(web): resolve login bug
docs: update README
test(api): add journal tests
ci: improve test coverage
```

### Running Tests Locally

```bash
# Frontend
cd aiwendy/apps/web
npm run test              # Run tests
npm run test:watch        # Watch mode
npm run test:coverage     # With coverage

# Backend
cd aiwendy/apps/api
pytest                    # Run all tests
pytest tests/unit         # Run unit tests only
pytest --cov=.            # With coverage
```

### CI/CD Workflow

When you push code or create a PR:

1. **CI runs automatically**:
   - Lints code
   - Runs type checks
   - Runs all tests
   - Builds the application
   - Reports code coverage

2. **Branch protection** (needs GitHub configuration):
   - Requires CI to pass
   - Requires code review
   - Prevents direct pushes to main/develop

### Release Process

When you create a tag:

```bash
git tag v1.0.0
git push origin v1.0.0
```

The release workflow:
1. Runs full test suite
2. Only creates release if tests pass
3. Auto-generates release notes

---

## GitHub Configuration Required

### Branch Protection Rules

Go to: `Settings → Branches → Branch protection rules`

**For `main` branch**:
- ✅ Require a pull request before merging
- ✅ Require approvals: 1
- ✅ Require status checks to pass:
  - `web` (CI job)
  - `api` (CI job)
- ✅ Require conversation resolution
- ✅ Restrict who can push (maintainers only)

**For `develop` branch**:
- ✅ Require a pull request before merging
- ✅ Require approvals: 1
- ✅ Require status checks to pass:
  - `web` (CI job)
  - `api` (CI job)

### Codecov Integration (Optional)

1. Go to https://codecov.io/
2. Sign in with GitHub
3. Add your repository
4. Copy the upload token (if needed)
5. Add to GitHub Secrets as `CODECOV_TOKEN` (optional, public repos don't need it)

---

## Troubleshooting

### Husky hooks not working

```bash
# Reinstall husky
rm -rf .husky
npx husky install
chmod +x .husky/commit-msg
chmod +x .husky/pre-commit
```

### Pre-commit not running

```bash
cd aiwendy/apps/api
pre-commit install
pre-commit run --all-files  # Test it
```

### Tests failing in CI but passing locally

- Make sure you've committed all test files
- Check that dependencies are in package.json/requirements.txt
- Verify Node.js and Python versions match CI

### Commit message rejected

Your commit message must follow this format:
```
type(scope): subject

Examples:
feat(api): add new feature
fix(web): fix bug
```

---

## Files Created

### Configuration Files
- `package.json` (root) - Node.js dependencies
- `commitlint.config.js` - Commit message rules
- `.lintstagedrc.json` - Pre-commit formatting
- `.pre-commit-config.yaml` - Python pre-commit hooks
- `codecov.yml` - Code coverage config

### Frontend Testing
- `aiwendy/apps/web/jest.config.js`
- `aiwendy/apps/web/jest.setup.js`
- `aiwendy/apps/web/__tests__/example.test.tsx`

### Backend Testing
- `aiwendy/apps/api/pytest.ini`
- `aiwendy/apps/api/pyproject.toml`
- `aiwendy/apps/api/.flake8`
- `aiwendy/apps/api/tests/conftest.py`
- `aiwendy/apps/api/tests/test_health.py`

### Git Hooks
- `.husky/commit-msg`
- `.husky/pre-commit`

### CI/CD
- `.github/workflows/ci.yml` (updated)
- `.github/workflows/release.yml` (updated)

### Documentation
- `CONTRIBUTING.md` (updated)

---

## Next Steps

1. ✅ Run `npm install` in project root
2. ✅ Run `npx husky install`
3. ✅ Run `npm install` in `aiwendy/apps/web`
4. ✅ Test the setup with a commit
5. ✅ Configure GitHub branch protection rules
6. ⚠️ Optional: Set up Codecov integration

---

## Benefits

After setup, you get:

1. 🔵 **Local Git Hooks** - Catch issues before commit
2. 🟢 **CI Automation** - Full test suite on every push
3. 🟡 **Code Review** - Required before merge
4. 🔴 **Branch Protection** - Prevent bad code from reaching main

**Quality Assurance Layers**:
- First line: Pre-commit hooks (formatting, linting)
- Second line: Commit message validation
- Third line: CI tests and builds
- Fourth line: Code review
- Final line: Branch protection rules
