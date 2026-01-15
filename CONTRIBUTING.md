# Contributing

<a id="en"></a>
[English](#en) | [中文](#zh-cn)

Thanks for your interest in contributing to KeelTrader!

## Branch Strategy

We follow Git Flow for branch management:

### For Contributors

1. **New features**: Create from `develop`
   ```bash
   git checkout develop
   git pull origin develop
   git checkout -b feature/123-your-feature
   ```

2. **Submit PR**: Target `develop` branch (not `main`)

3. **Branch naming**:
   - Features: `feature/<issue>-<description>`
   - Bug fixes: `bugfix/<issue>-<description>`
   - Examples: `feature/123-add-dark-mode`, `bugfix/456-fix-login`

### For Maintainers

- **Release process**: Create `release/vX.Y.Z` from `develop`
- **Hotfixes**: Create `hotfix/vX.Y.Z-description` from `main`
- **Merging**: Release/hotfix branches merge to both `main` and `develop`

### Branch Overview

- `main`: Production-ready code (protected)
- `develop`: Integration branch for features (protected)
- `feature/*`: New features (delete after merge)
- `release/*`: Release preparation (delete after merge)
- `hotfix/*`: Emergency fixes (delete after merge)

## Quick start (recommended)

The easiest way to run the full stack locally is Docker Compose:

1. `cd keeltrader`
2. Copy env file: `Copy-Item .env.example .env` (PowerShell) or `cp .env.example .env`
3. Start: `docker compose up -d --build`

More details: `keeltrader/docs/SELF_HOSTING.md`

## Development (split mode)

You can also run DB/Redis in Docker and run the API/Web on your host:

- API: `keeltrader/docs/DEPLOYMENT.md`
- Web: `keeltrader/apps/web/package.json` scripts: `npm run dev`, `npm run lint`, `npm run type-check`

## Development Setup

### Initial Setup

After cloning the repository, install dependencies:

```bash
# Install root dependencies (commitlint, husky)
npm install

# Install frontend dependencies
cd keeltrader/apps/web
npm install

# Install backend dependencies (if not using Docker)
cd ../api
pip install -r requirements.txt
pip install pre-commit
```

### Running Tests

```bash
# Frontend tests
cd keeltrader/apps/web
npm run test              # Run tests
npm run test:watch        # Watch mode
npm run test:coverage     # With coverage

# Backend tests
cd keeltrader/apps/api
pytest                    # Run all tests
pytest tests/unit         # Unit tests only
pytest --cov=.            # With coverage
```

### Code Quality

The project uses automated code quality tools:

- **Frontend**: ESLint, Prettier, TypeScript
- **Backend**: black, isort, flake8, mypy

Run checks manually:
```bash
# Frontend
cd keeltrader/apps/web
npm run lint
npm run type-check

# Backend
cd keeltrader/apps/api
black .
isort .
flake8 .
mypy .
```

## Pull requests

- Keep PRs focused (one topic per PR).
- Include screenshots/GIFs for UI changes.
- Prefer adding/adjusting docs if behavior changes.
- Ensure CI passes (lint/type-check/compile checks).

## Commit Message Convention

We follow [Conventional Commits](https://www.conventionalcommits.org/) to maintain a clear and consistent commit history.

### Format

```
<type>(<scope>): <subject>

[optional body]

[optional footer]
```

### Types

- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code formatting (no functional changes)
- `refactor`: Code refactoring
- `perf`: Performance improvements
- `test`: Adding or updating tests
- `build`: Build system changes
- `ci`: CI configuration changes
- `chore`: Other changes (maintenance, dependencies, etc.)
- `revert`: Revert a previous commit

### Examples

```bash
feat(api): add user authentication endpoint
fix(web): resolve login form validation issue
docs: update README with new setup instructions
test(api): add tests for journal service
ci: add test coverage reporting
```

### Scope (optional)

The scope specifies which part of the codebase is affected:
- `api`: Backend API changes
- `web`: Frontend web app changes
- `db`: Database changes
- `docs`: Documentation changes

### Commit Message Validation

Commit messages are automatically validated using commitlint. If your commit message doesn't follow the convention, the commit will be rejected.

## Reporting bugs / requesting features

Please use GitHub Issues and include:

- What you expected vs what happened
- Steps to reproduce
- Logs (redact secrets)
- OS / Node / Python versions

## Security

If you believe you found a security issue, please follow `SECURITY.md` instead of opening a public issue.

---

<a id="zh-cn"></a>
## 中文

感谢你愿意为 KeelTrader 做贡献！

### 分支策略

我们遵循 Git Flow 分支管理策略：

#### 贡献者指南

1. **新功能开发**：从 `develop` 分支创建
   ```bash
   git checkout develop
   git pull origin develop
   git checkout -b feature/123-your-feature
   ```

2. **提交 PR**：目标分支选择 `develop`（不是 `main`）

3. **分支命名规范**：
   - 新功能：`feature/<issue编号>-<简短描述>`
   - Bug修复：`bugfix/<issue编号>-<简短描述>`
   - 示例：`feature/123-add-dark-mode`、`bugfix/456-fix-login`

#### 维护者指南

- **发布流程**：从 `develop` 创建 `release/vX.Y.Z` 分支
- **紧急修复**：从 `main` 创建 `hotfix/vX.Y.Z-description` 分支
- **合并规则**：release/hotfix 分支需要同时合并到 `main` 和 `develop`

#### 分支说明

- `main`：生产稳定版代码（受保护）
- `develop`：功能集成分支（受保护）
- `feature/*`：新功能分支（合并后删除）
- `release/*`：发布准备分支（合并后删除）
- `hotfix/*`：紧急修复分支（合并后删除）

### 快速开始（推荐）

最简单的本地运行方式是使用 Docker Compose：

1. `cd keeltrader`
2. 复制环境变量文件：PowerShell 用 `Copy-Item .env.example .env`，macOS/Linux 用 `cp .env.example .env`
3. 启动：`docker compose up -d --build`

更多细节：`keeltrader/docs/SELF_HOSTING.md`

### 开发（拆分模式）

你也可以只用 Docker 跑 DB/Redis，然后在宿主机运行 API/Web：

- API：`keeltrader/docs/DEPLOYMENT.md`
- Web：参考 `keeltrader/apps/web/package.json` scripts：`npm run dev`、`npm run lint`、`npm run type-check`

### 开发环境设置

#### 初始设置

克隆仓库后，安装依赖：

```bash
# 安装根目录依赖（commitlint, husky）
npm install

# 安装前端依赖
cd keeltrader/apps/web
npm install

# 安装后端依赖（如果不使用 Docker）
cd ../api
pip install -r requirements.txt
pip install pre-commit
```

#### 运行测试

```bash
# 前端测试
cd keeltrader/apps/web
npm run test              # 运行测试
npm run test:watch        # 监听模式
npm run test:coverage     # 带覆盖率

# 后端测试
cd keeltrader/apps/api
pytest                    # 运行所有测试
pytest tests/unit         # 只运行单元测试
pytest --cov=.            # 带覆盖率
```

#### 代码质量

项目使用自动化代码质量工具：

- **前端**：ESLint、Prettier、TypeScript
- **后端**：black、isort、flake8、mypy

手动运行检查：
```bash
# 前端
cd keeltrader/apps/web
npm run lint
npm run type-check

# 后端
cd keeltrader/apps/api
black .
isort .
flake8 .
mypy .
```

### Pull Request

- 保持 PR 聚焦（一个 PR 一个主题）。
- UI 变更请补充截图/GIF。
- 如果行为有变化，优先补充/调整文档。
- 确保 CI 通过（lint/type-check/compile checks）。

### 提交信息规范

我们遵循 [Conventional Commits](https://www.conventionalcommits.org/) 规范，以保持清晰一致的提交历史。

#### 格式

```
<type>(<scope>): <subject>

[可选的 body]

[可选的 footer]
```

#### 类型

- `feat`: 新功能
- `fix`: Bug 修复
- `docs`: 文档更新
- `style`: 代码格式（不影响功能）
- `refactor`: 重构
- `perf`: 性能优化
- `test`: 测试相关
- `build`: 构建系统
- `ci`: CI 配置
- `chore`: 其他杂项
- `revert`: 回滚提交

#### 示例

```bash
feat(api): 添加用户认证端点
fix(web): 修复登录表单验证问题
docs: 更新 README 安装说明
test(api): 添加交易日志服务测试
ci: 添加测试覆盖率报告
```

#### Scope（可选）

Scope 指定代码库的哪个部分受到影响：
- `api`: 后端 API 变更
- `web`: 前端 Web 应用变更
- `db`: 数据库变更
- `docs`: 文档变更

#### 提交信息验证

提交信息会通过 commitlint 自动验证。如果提交信息不符合规范，提交将被拒绝。

### 报告 Bug / 提需求

请使用 GitHub Issues，并包含：

- 期望行为 vs 实际发生了什么
- 复现步骤
- 日志（注意脱敏，不要提交密钥）
- OS / Node / Python 版本

### 安全

如果你认为发现了安全问题，请按 `SECURITY.md` 处理，不要直接开公开 Issue。
