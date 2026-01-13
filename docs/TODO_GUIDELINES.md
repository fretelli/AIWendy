# TODO 注释规范

本文档定义了 AIWendy 项目中 TODO 注释的标准格式和最佳实践。

## 标准格式

### 基本语法

```python
# TODO(category): Brief description
#   - Detailed step 1
#   - Detailed step 2
#   - Additional context
```

### 支持的注释类型

| 类型 | 用途 | 示例 |
|------|------|------|
| `TODO` | 计划中的功能或改进 | `TODO(feature): Add pagination` |
| `FIXME` | 已知的 bug 需要修复 | `FIXME(bug): Handle edge case` |
| `HACK` | 临时解决方案，需要重构 | `HACK: Workaround for library issue` |
| `XXX` | 危险或需要特别注意的代码 | `XXX: This breaks in production` |

### 类别标签

使用括号标注类别，帮助优先级排序：

| 类别 | 说明 | 优先级 |
|------|------|--------|
| `security` | 安全相关 | 🔴 高 |
| `performance` | 性能优化 | 🟡 中 |
| `feature` | 新功能 | 🟢 低 |
| `refactor` | 代码重构 | 🟢 低 |
| `docs` | 文档改进 | 🟢 低 |
| `test` | 测试覆盖 | 🟡 中 |
| `bug` | Bug 修复 | 🔴 高 |

## 示例

### ✅ 好的 TODO 注释

```python
# TODO(security): Implement session revocation mechanism
#   - Store active sessions in Redis with user_id:session_id as key
#   - Add session_id to JWT payload
#   - Check session validity in get_current_user middleware
#   - Implement /api/v1/auth/sessions endpoint to list active sessions
# Currently using stateless JWT - tokens expire naturally after jwt_expire_minutes
```

**优点**：
- 明确的类别标签 `(security)`
- 简洁的一行描述
- 详细的实现步骤
- 说明当前状态

### ✅ 带 Issue 引用

```python
# TODO(#123): Implement rate limiting for API endpoints
#   See GitHub issue #123 for detailed requirements
```

### ❌ 不好的 TODO 注释

```python
# TODO: fix this
```

**问题**：
- 没有类别标签
- 描述不清晰
- 没有实现细节

```python
# TODO: This needs to be improved
```

**问题**：
- 太模糊，不知道如何改进

## 扫描 TODO

使用提供的脚本扫描项目中的所有 TODO：

```bash
# 扫描所有 TODO
python scripts/scan_todos.py

# 生成 Markdown 报告
python scripts/scan_todos.py --format markdown --output TODO_REPORT.md

# 只查看安全相关的 TODO
python scripts/scan_todos.py --category security

# 查看统计摘要
python scripts/scan_todos.py --format summary
```

## 工作流程

### 1. 添加 TODO

在开发过程中，遇到以下情况时添加 TODO：

- 发现需要改进但当前不在范围内的代码
- 实现临时解决方案（HACK）
- 发现潜在的安全问题
- 计划未来的功能增强

### 2. 定期审查

每个 Sprint 开始时：

```bash
# 生成 TODO 报告
python scripts/scan_todos.py --format markdown --output docs/TODO_REPORT.md

# 查看高优先级项目
python scripts/scan_todos.py --category security
```

### 3. 转换为 Issue

对于重要的 TODO：

1. 在 GitHub 创建 Issue
2. 更新 TODO 注释引用 Issue 编号
3. 在 Issue 中链接到代码位置

```python
# TODO(#456): Implement user profile update
#   See https://github.com/yourorg/aiwendy/issues/456
```

### 4. 完成后删除

实现功能后，删除对应的 TODO 注释。

## CI/CD 集成

### GitHub Actions 示例

在 `.github/workflows/todo-check.yml` 中添加：

```yaml
name: TODO Check

on: [pull_request]

jobs:
  check-todos:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Scan TODOs
        run: |
          python scripts/scan_todos.py --format summary

      - name: Check for security TODOs
        run: |
          COUNT=$(python scripts/scan_todos.py --category security | grep -c "TODO")
          if [ $COUNT -gt 10 ]; then
            echo "Warning: $COUNT security TODOs found"
          fi
```

## 最佳实践

### ✅ 推荐

1. **具体明确**：描述清楚要做什么
2. **添加上下文**：说明为什么需要这个改进
3. **提供步骤**：列出实现的具体步骤
4. **标注类别**：使用标准类别标签
5. **及时更新**：完成后立即删除

### ❌ 避免

1. **模糊描述**：`TODO: fix this`
2. **没有类别**：`TODO: improve performance`
3. **过时的 TODO**：已经实现但忘记删除
4. **重复的 TODO**：同一个问题在多处标注
5. **个人笔记**：`TODO: remember to test this`

## 工具集成

### VS Code

安装 [Todo Tree](https://marketplace.visualstudio.com/items?itemName=Gruntfuggly.todo-tree) 插件：

```json
// .vscode/settings.json
{
  "todo-tree.general.tags": [
    "TODO",
    "FIXME",
    "HACK",
    "XXX"
  ],
  "todo-tree.highlights.customHighlight": {
    "TODO": {
      "icon": "check",
      "iconColour": "#00ff00"
    },
    "FIXME": {
      "icon": "alert",
      "iconColour": "#ff0000"
    }
  }
}
```

### PyCharm

PyCharm 内置 TODO 支持，在 `View > Tool Windows > TODO` 查看。

## 参考资源

- [Google Style Guide - TODO Comments](https://google.github.io/styleguide/pyguide.html#312-todo-comments)
- [PEP 350 - Codetags](https://www.python.org/dev/peps/pep-0350/)
- [TODO or not TODO](https://www.yegor256.com/2017/04/05/todo-comments.html)

## 示例报告

运行 `python scripts/scan_todos.py --format summary` 的输出示例：

```
TODO Summary Report
================================================================================
Total items: 6

By Type:
  TODO: 6

By Category:
  security: 2
  feature: 4

Top 10 Files:
  aiwendy/apps/api/routers/auth.py: 1
  aiwendy/apps/api/routers/chat.py: 2
  aiwendy/apps/api/routers/coaches.py: 1
  aiwendy/apps/api/routers/tasks.py: 1
  aiwendy/apps/api/routers/users.py: 1
```
