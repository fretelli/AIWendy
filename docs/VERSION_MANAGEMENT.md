# 版本管理指南 / Version Management Guide

[English](#english) | [中文](#chinese)

---

<a id="english"></a>
## English

### Overview

KeelTrader uses modern dependency management tools and automated workflows to ensure reproducible builds and secure dependency updates.

### Dependency Management

#### Python (Backend API)

**Tool**: Poetry

**Files**:
- `keeltrader/apps/api/pyproject.toml` - Project configuration and dependencies
- `keeltrader/apps/api/poetry.lock` - Locked dependency versions
- `keeltrader/apps/api/requirements.txt` - Generated for compatibility

**Installation**:
```bash
cd keeltrader/apps/api
poetry install
```

**Adding Dependencies**:
```bash
# Production dependency
poetry add fastapi

# Development dependency
poetry add --group dev pytest

# With specific version
poetry add "fastapi==0.111.0"
```

**Updating Dependencies**:
```bash
# Update all dependencies
poetry update

# Update specific package
poetry update fastapi

# Export to requirements.txt
poetry export -f requirements.txt --output requirements.txt --without-hashes
```

#### Node.js (Frontend Web)

**Tool**: npm

**Files**:
- `keeltrader/apps/web/package.json` - Project configuration and dependencies
- `keeltrader/apps/web/package-lock.json` - Locked dependency versions
- `keeltrader/apps/web/.npmrc` - npm configuration (exact versions)

**Installation**:
```bash
cd keeltrader/apps/web
npm ci  # Use ci for reproducible builds
```

**Adding Dependencies**:
```bash
# Production dependency
npm install react

# Development dependency
npm install --save-dev jest

# With specific version
npm install react@18.3.1
```

**Updating Dependencies**:
```bash
# Update all dependencies
npm update

# Update specific package
npm update react

# Check for outdated packages
npm outdated
```

### Automated Dependency Updates

**Tool**: Dependabot

**Configuration**: `.github/dependabot.yml`

**Features**:
- Weekly automated dependency update PRs
- Grouped updates for related packages
- Security vulnerability alerts
- Automatic PR creation

**Review Process**:
1. Dependabot creates PR with dependency updates
2. CI/CD runs automated tests
3. Review changes and test locally if needed
4. Merge PR if tests pass

### Version Release

**Tool**: standard-version

**Commands**:
```bash
# Automatic version bump based on commits
npm run release

# Specific version bump
npm run release:patch  # 1.0.0 -> 1.0.1
npm run release:minor  # 1.0.0 -> 1.1.0
npm run release:major  # 1.0.0 -> 2.0.0

# Dry run (preview changes)
npm run release:dry-run
```

**Release Process**:
1. Ensure all changes are committed
2. Run `npm run release`
3. Review generated CHANGELOG.md
4. Push commits and tags: `git push --follow-tags origin main`
5. GitHub Actions will create release automatically

### Docker Images

**Registry**: GitHub Container Registry (ghcr.io)

**Images**:
- API: `ghcr.io/fretelli/keeltrader/api`
- Web: `ghcr.io/fretelli/keeltrader/web`

**Tags**:
- `latest` - Latest build from main branch
- `v1.0.0` - Specific version
- `v1.0` - Major.minor version
- `v1` - Major version
- `sha-abc1234` - Specific commit

**Usage**:
```bash
# Pull specific version
docker pull ghcr.io/fretelli/keeltrader/api:v1.0.0

# Use in docker-compose.yml
services:
  api:
    image: ghcr.io/fretelli/keeltrader/api:v1.0.0
```

### Commit Convention

We follow [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<scope>): <subject>

<body>

<footer>
```

**Types**:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting, etc.)
- `refactor`: Code refactoring
- `perf`: Performance improvements
- `test`: Test changes
- `chore`: Build process or auxiliary tool changes

**Examples**:
```bash
feat(api): add user authentication endpoint
fix(web): resolve navigation menu overflow issue
docs(readme): update installation instructions
chore(deps): update fastapi to 0.111.0
```

### Best Practices

1. **Always use lock files**: Commit `poetry.lock` and `package-lock.json`
2. **Review dependency updates**: Don't blindly merge Dependabot PRs
3. **Test before releasing**: Run full test suite before version bump
4. **Use semantic versioning**: Follow semver for version numbers
5. **Keep CHANGELOG updated**: Document all notable changes

---

<a id="chinese"></a>
## 中文

### 概述

KeelTrader 使用现代化的依赖管理工具和自动化工作流，确保可复现的构建和安全的依赖更新。

### 依赖管理

#### Python（后端 API）

**工具**: Poetry

**文件**:
- `keeltrader/apps/api/pyproject.toml` - 项目配置和依赖
- `keeltrader/apps/api/poetry.lock` - 锁定的依赖版本
- `keeltrader/apps/api/requirements.txt` - 为兼容性生成

**安装**:
```bash
cd keeltrader/apps/api
poetry install
```

**添加依赖**:
```bash
# 生产依赖
poetry add fastapi

# 开发依赖
poetry add --group dev pytest

# 指定版本
poetry add "fastapi==0.111.0"
```

**更新依赖**:
```bash
# 更新所有依赖
poetry update

# 更新特定包
poetry update fastapi

# 导出到 requirements.txt
poetry export -f requirements.txt --output requirements.txt --without-hashes
```

#### Node.js（前端 Web）

**工具**: npm

**文件**:
- `keeltrader/apps/web/package.json` - 项目配置和依赖
- `keeltrader/apps/web/package-lock.json` - 锁定的依赖版本
- `keeltrader/apps/web/.npmrc` - npm 配置（精确版本）

**安装**:
```bash
cd keeltrader/apps/web
npm ci  # 使用 ci 确保可复现构建
```

**添加依赖**:
```bash
# 生产依赖
npm install react

# 开发依赖
npm install --save-dev jest

# 指定版本
npm install react@18.3.1
```

**更新依赖**:
```bash
# 更新所有依赖
npm update

# 更新特定包
npm update react

# 检查过时的包
npm outdated
```

### 自动化依赖更新

**工具**: Dependabot

**配置**: `.github/dependabot.yml`

**功能**:
- 每周自动创建依赖更新 PR
- 相关包的分组更新
- 安全漏洞警报
- 自动创建 PR

**审查流程**:
1. Dependabot 创建依赖更新 PR
2. CI/CD 运行自动化测试
3. 审查变更，必要时本地测试
4. 测试通过后合并 PR

### 版本发布

**工具**: standard-version

**命令**:
```bash
# 基于提交自动升级版本
npm run release

# 指定版本升级
npm run release:patch  # 1.0.0 -> 1.0.1
npm run release:minor  # 1.0.0 -> 1.1.0
npm run release:major  # 1.0.0 -> 2.0.0

# 预览变更（不实际执行）
npm run release:dry-run
```

**发布流程**:
1. 确保所有变更已提交
2. 运行 `npm run release`
3. 审查生成的 CHANGELOG.md
4. 推送提交和标签: `git push --follow-tags origin main`
5. GitHub Actions 将自动创建 release

### Docker 镜像

**仓库**: GitHub Container Registry (ghcr.io)

**镜像**:
- API: `ghcr.io/fretelli/keeltrader/api`
- Web: `ghcr.io/fretelli/keeltrader/web`

**标签**:
- `latest` - main 分支的最新构建
- `v1.0.0` - 特定版本
- `v1.0` - 主版本.次版本
- `v1` - 主版本
- `sha-abc1234` - 特定提交

**使用**:
```bash
# 拉取特定版本
docker pull ghcr.io/fretelli/keeltrader/api:v1.0.0

# 在 docker-compose.yml 中使用
services:
  api:
    image: ghcr.io/fretelli/keeltrader/api:v1.0.0
```

### 提交规范

我们遵循 [Conventional Commits](https://www.conventionalcommits.org/)：

```
<类型>(<范围>): <主题>

<正文>

<页脚>
```

**类型**:
- `feat`: 新功能
- `fix`: Bug 修复
- `docs`: 文档变更
- `style`: 代码风格变更（格式化等）
- `refactor`: 代码重构
- `perf`: 性能改进
- `test`: 测试变更
- `chore`: 构建过程或辅助工具变更

**示例**:
```bash
feat(api): 添加用户认证端点
fix(web): 解决导航菜单溢出问题
docs(readme): 更新安装说明
chore(deps): 更新 fastapi 到 0.111.0
```

### 最佳实践

1. **始终使用锁文件**: 提交 `poetry.lock` 和 `package-lock.json`
2. **审查依赖更新**: 不要盲目合并 Dependabot PR
3. **发布前测试**: 版本升级前运行完整测试套件
4. **使用语义化版本**: 遵循 semver 版本号规范
5. **保持 CHANGELOG 更新**: 记录所有重要变更
