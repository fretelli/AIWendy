# Git 工作流程设置指南

本指南说明如何激活和使用新的 Git 工作流程改进。

## 已添加的内容

### 1. 测试基础设施
- ✅ 前端：Jest + React Testing Library
- ✅ 后端：pytest 带覆盖率
- ✅ CI：每次推送/PR 自动测试

### 2. 代码质量工具
- ✅ Python：black、isort、flake8、mypy
- ✅ JavaScript/TypeScript：ESLint、Prettier
- ✅ Pre-commit hooks 自动格式化

### 3. 提交信息规范
- ✅ Commitlint 配合 Conventional Commits
- ✅ Husky 管理 Git hooks
- ✅ Lint-staged 自动代码格式化

### 4. CI/CD 改进
- ✅ CI 中运行完整测试套件
- ✅ 构建验证
- ✅ 代码覆盖率报告
- ✅ Release 工作流带测试

---

## 设置步骤

### 步骤 1：安装根目录依赖

```bash
# 在项目根目录
cd C:\github_project\AIWendy
npm install
```

这会安装：
- commitlint
- husky
- lint-staged

### 步骤 2：初始化 Husky

```bash
npx husky install
```

这会激活 Git hooks：
- 提交信息验证
- 提交前代码格式化

### 步骤 3：安装前端依赖

```bash
cd aiwendy/apps/web
npm install
```

这会安装新的测试依赖：
- jest
- @testing-library/react
- @testing-library/jest-dom

### 步骤 4：安装 Pre-commit（Python）

```bash
cd aiwendy/apps/api
pip install pre-commit
pre-commit install
```

这会激活 Python 代码质量 hooks。

### 步骤 5：测试设置

#### 测试前端
```bash
cd aiwendy/apps/web
npm run test
npm run build
```

#### 测试后端
```bash
cd aiwendy/apps/api
pytest
black --check .
isort --check-only .
flake8 .
```

---

## 使用方法

### 提交代码

当你提交时，会自动执行以下操作：

1. **Pre-commit hook 运行**：
   - 格式化 JavaScript/TypeScript 代码（ESLint + Prettier）
   - 格式化 Python 代码（black + isort）
   - 运行 flake8 和 mypy 检查

2. **提交信息验证**：
   - 检查你的提交信息是否符合 Conventional Commits 格式
   - 示例：`feat(api): add new endpoint`

### 提交信息格式

```
<type>(<scope>): <subject>

示例：
feat(api): 添加用户认证功能
fix(web): 修复登录表单验证问题
docs: 更新 README
test(api): 添加交易日志测试
ci: 改进测试覆盖率
```

### 本地运行测试

```bash
# 前端
cd aiwendy/apps/web
npm run test              # 运行测试
npm run test:watch        # 监听模式
npm run test:coverage     # 带覆盖率

# 后端
cd aiwendy/apps/api
pytest                    # 运行所有测试
pytest tests/unit         # 只运行单元测试
pytest --cov=.            # 带覆盖率
```

### CI/CD 工作流

当你推送代码或创建 PR 时：

1. **CI 自动运行**：
   - 代码检查（lint）
   - 类型检查
   - 运行所有测试
   - 构建应用
   - 报告代码覆盖率

2. **分支保护**（需要 GitHub 配置）：
   - 要求 CI 通过
   - 要求代码审查
   - 防止直接推送到 main/develop

### 发布流程

当你创建 tag 时：

```bash
git tag v1.0.0
git push origin v1.0.0
```

Release 工作流会：
1. 运行完整测试套件
2. 只有测试通过才创建 release
3. 自动生成 release notes

---

## 需要的 GitHub 配置

### 分支保护规则

进入：`Settings → Branches → Branch protection rules`

**为 `main` 分支配置**：
- ✅ Require a pull request before merging（合并前需要 PR）
- ✅ Require approvals: 1（需要 1 个审查）
- ✅ Require status checks to pass（需要状态检查通过）：
  - `web`（CI job）
  - `api`（CI job）
- ✅ Require conversation resolution（需要解决所有讨论）
- ✅ Restrict who can push（限制推送权限，仅维护者）

**为 `develop` 分支配置**：
- ✅ Require a pull request before merging
- ✅ Require approvals: 1
- ✅ Require status checks to pass：
  - `web`（CI job）
  - `api`（CI job）

### Codecov 集成（可选）

1. 访问 https://codecov.io/
2. 使用 GitHub 登录
3. 添加你的仓库
4. 复制上传 token（如果需要）
5. 添加到 GitHub Secrets 作为 `CODECOV_TOKEN`（可选，公开仓库不需要）

---

## 故障排除

### Husky hooks 不工作

```bash
# 重新安装 husky
rm -rf .husky
npx husky install
chmod +x .husky/commit-msg
chmod +x .husky/pre-commit
```

### Pre-commit 不运行

```bash
cd aiwendy/apps/api
pre-commit install
pre-commit run --all-files  # 测试它
```

### 测试在 CI 中失败但本地通过

- 确保你已提交所有测试文件
- 检查依赖是否在 package.json/requirements.txt 中
- 验证 Node.js 和 Python 版本与 CI 匹配

### 提交信息被拒绝

你的提交信息必须遵循以下格式：
```
type(scope): subject

示例：
feat(api): 添加新功能
fix(web): 修复 bug
```

---

## 创建的文件

### 配置文件
- `package.json`（根目录）- Node.js 依赖
- `commitlint.config.js` - 提交信息规则
- `.lintstagedrc.json` - 提交前格式化
- `.pre-commit-config.yaml` - Python pre-commit hooks
- `codecov.yml` - 代码覆盖率配置

### 前端测试
- `aiwendy/apps/web/jest.config.js`
- `aiwendy/apps/web/jest.setup.js`
- `aiwendy/apps/web/__tests__/example.test.tsx`

### 后端测试
- `aiwendy/apps/api/pytest.ini`
- `aiwendy/apps/api/pyproject.toml`
- `aiwendy/apps/api/.flake8`
- `aiwendy/apps/api/tests/conftest.py`
- `aiwendy/apps/api/tests/test_health.py`

### Git Hooks
- `.husky/commit-msg`
- `.husky/pre-commit`

### CI/CD
- `.github/workflows/ci.yml`（已更新）
- `.github/workflows/release.yml`（已更新）

### 文档
- `CONTRIBUTING.md`（已更新）

---

## 下一步

1. ✅ 在项目根目录运行 `npm install`
2. ✅ 运行 `npx husky install`
3. ✅ 在 `aiwendy/apps/web` 运行 `npm install`
4. ✅ 用一次提交测试设置
5. ✅ 配置 GitHub 分支保护规则
6. ⚠️ 可选：设置 Codecov 集成

---

## 优势

设置完成后，你将获得：

1. 🔵 **本地 Git Hooks** - 提交前捕获问题
2. 🟢 **CI 自动化** - 每次推送运行完整测试套件
3. 🟡 **代码审查** - 合并前必需
4. 🔴 **分支保护** - 防止坏代码进入 main

**质量保障层级**：
- 第一道防线：Pre-commit hooks（格式化、lint）
- 第二道防线：提交信息验证
- 第三道防线：CI 测试和构建
- 第四道防线：代码审查
- 最后防线：分支保护规则

---

## 提交信息类型说明

| 类型 | 说明 | 示例 |
|------|------|------|
| `feat` | 新功能 | `feat(api): 添加用户认证端点` |
| `fix` | Bug 修复 | `fix(web): 修复登录表单验证` |
| `docs` | 文档更新 | `docs: 更新 README 安装说明` |
| `style` | 代码格式（不影响功能） | `style(api): 格式化代码` |
| `refactor` | 重构 | `refactor(web): 重构用户组件` |
| `perf` | 性能优化 | `perf(api): 优化数据库查询` |
| `test` | 测试 | `test(api): 添加交易日志测试` |
| `build` | 构建系统 | `build: 更新 webpack 配置` |
| `ci` | CI 配置 | `ci: 添加测试覆盖率报告` |
| `chore` | 其他杂项 | `chore: 更新依赖` |
| `revert` | 回滚 | `revert: 回滚提交 abc123` |

---

## 常见问题

### Q: 为什么我的提交被拒绝了？
A: 检查你的提交信息格式是否正确。必须是 `type(scope): subject` 格式。

### Q: Pre-commit hook 运行很慢怎么办？
A: 这是正常的，因为它在格式化和检查代码。你可以用 `git commit --no-verify` 跳过（不推荐）。

### Q: 如何跳过 CI 检查？
A: 不能跳过。这是为了保证代码质量。如果 CI 失败，请修复问题后再推送。

### Q: 我可以直接推送到 main 分支吗？
A: 配置分支保护后不可以。你必须创建 PR 并通过审查。

### Q: 测试失败了怎么办？
A: 查看 CI 日志，修复失败的测试，然后重新推送。

---

## 联系支持

如果遇到问题：
1. 查看本文档的故障排除部分
2. 查看 `CONTRIBUTING.md` 了解更多细节
3. 在 GitHub Issues 中提问
