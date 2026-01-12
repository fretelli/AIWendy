module.exports = {
  extends: ['@commitlint/config-conventional'],
  rules: {
    'type-enum': [
      2,
      'always',
      [
        'feat',     // 新功能
        'fix',      // Bug 修复
        'docs',     // 文档更新
        'style',    // 代码格式（不影响功能）
        'refactor', // 重构
        'perf',     // 性能优化
        'test',     // 测试
        'build',    // 构建系统
        'ci',       // CI 配置
        'chore',    // 其他杂项
        'revert'    // 回滚
      ]
    ],
    'subject-case': [0], // 允许任意大小写
    'body-max-line-length': [0], // 不限制 body 行长度
    'footer-max-line-length': [0] // 不限制 footer 行长度
  }
};
