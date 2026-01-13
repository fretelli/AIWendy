# Changelog

<a id="en"></a>
[English](#en) | [中文](#zh-cn)

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project aims to follow [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Poetry dependency management for Python backend
- Dependabot configuration for automated dependency updates
- `.npmrc` configuration for exact version locking
- Automated CHANGELOG generation support

### Changed
- Unified Node.js dependency versions (removed caret ranges)
- Updated `pyproject.toml` with complete Poetry configuration
- Improved dependency management workflow

### Security
- Fixed SQL injection vulnerability in journal symbol search
- Enhanced file upload validation with magic bytes verification
- Implemented authentication bypass prevention for sensitive endpoints
- Fixed guest email constant inconsistency

## [1.0.0] - 2026-01-11

### Added
- Git Flow branch strategy for better collaboration
- Automated release workflow via GitHub Actions
- Branch protection guidelines in CONTRIBUTING.md

### Changed
- Updated documentation to reflect new branching model
- Version bumped to 1.0.0 for official release

## [0.1.0] - 2026-01-09

Initial open-source release (Community edition).

---

<a id="zh-cn"></a>
## 中文

本文件记录本项目的所有重要变更。

格式基于 [Keep a Changelog](https://keepachangelog.com/en/1.1.0/)，
并遵循 [语义化版本](https://semver.org/spec/v2.0.0.html)。

## [未发布]

### 新增
- Python 后端 Poetry 依赖管理
- Dependabot 自动化依赖更新配置
- `.npmrc` 配置文件，锁定精确版本
- 自动化 CHANGELOG 生成支持

### 变更
- 统一 Node.js 依赖版本（移除 caret 范围）
- 更新 `pyproject.toml`，完整的 Poetry 配置
- 改进依赖管理工作流

### 安全
- 修复交易日志符号搜索中的 SQL 注入漏洞
- 增强文件上传验证（magic bytes 验证）
- 实施敏感端点的认证绕过防护
- 修复 guest 邮箱常量不一致问题

## [1.0.0] - 2026-01-11

### 新增
- Git Flow 分支策略，更好地支持协作开发
- 通过 GitHub Actions 实现自动化发布流程
- 在 CONTRIBUTING.md 中添加分支保护指南

### 变更
- 更新文档以反映新的分支管理模型
- 版本号升级至 1.0.0，正式发布

## [0.1.0] - 2026-01-09

首次开源发布（Community 社区版）。
