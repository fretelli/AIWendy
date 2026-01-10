export const supportedLanguages = ["en", "zh"] as const

export type Language = (typeof supportedLanguages)[number]

export const defaultLanguage: Language = "en"

export function isLanguage(value: unknown): value is Language {
  return supportedLanguages.includes(value as Language)
}

export const en = {
  "language.enShort": "EN",
  "language.zhShort": "中文",

  "home.hero.title": "AI Trading Psychology Coach",
  "home.hero.subtitle":
    'Like Wendy Rhodes in "Billions" — helping you stay calm, consistent, and perform better.',
  "home.hero.cta.startFree": "Start free",
  "home.hero.cta.signIn": "Sign in",
  "home.hero.cta.tryDemo": "Try demo",

  "home.features.title": "Core features",
  "home.features.realtime.title": "Real-time emotional support",
  "home.features.realtime.desc":
    "In-the-moment psychological coaching with low latency to help you respond calmly to volatility.",
  "home.features.patterns.title": "Behavior pattern analysis",
  "home.features.patterns.desc":
    "Detect FOMO, revenge trading, and other pitfalls — get personalized improvement suggestions.",
  "home.features.review.title": "Trade journaling & review",
  "home.features.review.desc":
    "Deep dive into your mental state behind every trade and identify the emotional drivers of P/L.",
  "home.features.risk.title": "Risk mindset coaching",
  "home.features.risk.desc":
    "Build healthy risk awareness and overcome overconfidence and loss aversion.",

  "home.cta.title": "Ready to level up your trading psychology?",
  "home.cta.subtitle":
    "Join thousands of traders and improve your performance with AI coaching.",
  "home.cta.button": "Start free",

  "pricing.title": "Choose your plan",
  "pricing.periodMonthly": "/mo",
  "pricing.free.desc": "Best for getting started",
  "pricing.free.feature1": "3 journal entries per day",
  "pricing.free.feature2": "Basic AI insights",
  "pricing.free.feature3": "3 starter coaches",
  "pricing.free.cta": "Get started",

  "pricing.pro.desc": "Best for serious traders",
  "pricing.pro.feature1": "Unlimited journaling",
  "pricing.pro.feature2": "Unlimited AI coaching chat",
  "pricing.pro.feature3": "All coaches unlocked",
  "pricing.pro.feature4": "Weekly analysis report",
  "pricing.pro.cta": "Upgrade now",

  "pricing.elite.desc": "Institutional-grade support",
  "pricing.elite.feature1": "Everything in Pro",
  "pricing.elite.feature2": "Priority response",
  "pricing.elite.feature3": "Monthly deep-dive report",
  "pricing.elite.feature4": "1 human coaching session/month",
  "pricing.elite.cta": "Contact us",

  "auth.back": "Back",
  "auth.orContinueWith": "Or continue with",
  "auth.email": "Email",
  "auth.password": "Password",

  "auth.login.title": "Welcome back",
  "auth.login.subtitle": "Enter your email and password to sign in",
  "auth.login.submit": "Sign in",
  "auth.login.forgot": "Forgot your password?",
  "auth.login.noAccount": "Don't have an account? Sign up",
  "auth.login.error": "Failed to sign in. Please try again.",

  "auth.register.title": "Create an account",
  "auth.register.subtitle": "Enter your information to get started",
  "auth.register.fullName": "Full name",
  "auth.register.confirmPassword": "Confirm password",
  "auth.register.termsPrefix": "I agree to the",
  "auth.register.termsLink": "terms and conditions",
  "auth.register.submit": "Create account",
  "auth.register.hasAccount": "Already have an account?",
  "auth.register.error": "Failed to create account. Please try again.",
  "auth.register.validation.passwordMismatch": "Passwords do not match",
  "auth.register.validation.passwordTooShort":
    "Password must be at least 8 characters long",
  "auth.register.validation.mustAgree":
    "You must agree to the terms and conditions",

  "auth.forgot.title": "Reset password",
  "auth.forgot.subtitle":
    "Enter your email address and we'll send you a reset link",
  "auth.forgot.submit": "Send reset email",
  "auth.forgot.error": "Failed to send reset email. Please try again.",
  "auth.forgot.backToLogin": "Back to login",
  "auth.forgot.success.title": "Check your email",
  "auth.forgot.success.subtitle": "We've sent a reset link to {email}",
  "auth.forgot.success.body":
    "If an account exists for {email}, you'll receive an email with reset instructions within a few minutes.",
  "auth.forgot.success.noEmail": "Didn't receive the email? Check spam or",
  "auth.forgot.success.tryDifferent": "Try a different email",

  "app.dashboard.title": "Dashboard",
  "app.dashboard.subtitle": "You're in (placeholder page).",
  "app.dashboard.tipTitle": "Tip",
  "app.dashboard.chat": "Go to chat",
  "app.dashboard.journal": "Go to journal",
  "app.dashboard.home": "Home",
  "app.dashboard.tip":
    "Login/register requires the backend API running at http://localhost:8000 (or set NEXT_PUBLIC_API_URL).",

  "app.chat.title": "Chat (placeholder)",
  "app.chat.body": "This page will host the chat UI and streaming output.",
  "app.backToDashboard": "Back to dashboard",

  "app.journal.title": "Journal (placeholder)",
  "app.journal.body": "This page will host journaling, review, and analytics.",

  "app.onboarding.title": "Onboarding (placeholder)",
  "app.onboarding.toDashboard": "Go to dashboard",
  "app.onboarding.toLogin": "Go to login",
} as const

export type MessageKey = keyof typeof en

export const zh: Record<MessageKey, string> = {
  "language.enShort": "EN",
  "language.zhShort": "中文",

  "home.hero.title": "AI 交易心理教练",
  "home.hero.subtitle":
    '像《Billions》里的 Wendy Rhodes 一样，帮助你保持冷静、提升一致性与交易表现。',
  "home.hero.cta.startFree": "免费开始",
  "home.hero.cta.signIn": "登录",
  "home.hero.cta.tryDemo": "直接体验",

  "home.features.title": "核心功能",
  "home.features.realtime.title": "实时情绪支持",
  "home.features.realtime.desc":
    "盘中低延迟心理支持，帮助你冷静应对市场波动。",
  "home.features.patterns.title": "行为模式分析",
  "home.features.patterns.desc":
    "识别 FOMO、报复性交易等陷阱，并给出个性化改进建议。",
  "home.features.review.title": "交易日志与复盘",
  "home.features.review.desc":
    "深度分析每笔交易背后的心理状态，找出影响盈亏的情绪因素。",
  "home.features.risk.title": "风险心态管理",
  "home.features.risk.desc": "培养健康风险意识，克服过度自信与损失厌恶。",

  "home.cta.title": "准备好提升你的交易心理了吗？",
  "home.cta.subtitle": "加入数千名交易者，用 AI 教练提升你的表现。",
  "home.cta.button": "立即免费开始",

  "pricing.title": "选择你的计划",
  "pricing.periodMonthly": "/月",
  "pricing.free.desc": "适合尝试体验",
  "pricing.free.feature1": "每天 3 次交易日志",
  "pricing.free.feature2": "基础 AI 洞察",
  "pricing.free.feature3": "3 个基础教练",
  "pricing.free.cta": "开始使用",

  "pricing.pro.desc": "专业交易者首选",
  "pricing.pro.feature1": "无限交易日志",
  "pricing.pro.feature2": "无限 AI 教练对话",
  "pricing.pro.feature3": "全部教练解锁",
  "pricing.pro.feature4": "周度分析报告",
  "pricing.pro.cta": "立即升级",

  "pricing.elite.desc": "机构级服务",
  "pricing.elite.feature1": "包含 Pro 全部功能",
  "pricing.elite.feature2": "优先响应",
  "pricing.elite.feature3": "月度深度报告",
  "pricing.elite.feature4": "每月 1 次人工教练",
  "pricing.elite.cta": "联系我们",

  "auth.back": "返回",
  "auth.orContinueWith": "或使用",
  "auth.email": "邮箱",
  "auth.password": "密码",

  "auth.login.title": "欢迎回来",
  "auth.login.subtitle": "输入邮箱和密码登录",
  "auth.login.submit": "登录",
  "auth.login.forgot": "忘记密码？",
  "auth.login.noAccount": "没有账号？注册",
  "auth.login.error": "登录失败，请重试。",

  "auth.register.title": "创建账号",
  "auth.register.subtitle": "填写信息开始使用",
  "auth.register.fullName": "姓名",
  "auth.register.confirmPassword": "确认密码",
  "auth.register.termsPrefix": "我已阅读并同意",
  "auth.register.termsLink": "用户条款",
  "auth.register.submit": "注册",
  "auth.register.hasAccount": "已有账号？",
  "auth.register.error": "注册失败，请重试。",
  "auth.register.validation.passwordMismatch": "两次输入的密码不一致",
  "auth.register.validation.passwordTooShort": "密码至少 8 位",
  "auth.register.validation.mustAgree": "请先同意用户条款",

  "auth.forgot.title": "重置密码",
  "auth.forgot.subtitle": "输入邮箱，我们会发送重置链接",
  "auth.forgot.submit": "发送重置邮件",
  "auth.forgot.error": "发送失败，请重试。",
  "auth.forgot.backToLogin": "返回登录",
  "auth.forgot.success.title": "请查收邮件",
  "auth.forgot.success.subtitle": "我们已向 {email} 发送重置链接",
  "auth.forgot.success.body":
    "如果 {email} 存在对应账号，你将在几分钟内收到包含重置说明的邮件。",
  "auth.forgot.success.noEmail": "没收到邮件？请检查垃圾箱，或",
  "auth.forgot.success.tryDifferent": "换个邮箱再试",

  "app.dashboard.title": "控制台",
  "app.dashboard.subtitle": "你已进入应用（占位页）。",
  "app.dashboard.tipTitle": "提示",
  "app.dashboard.chat": "进入聊天",
  "app.dashboard.journal": "交易日志",
  "app.dashboard.home": "返回首页",
  "app.dashboard.tip":
    "登录/注册需要后端 API 在 http://localhost:8000 运行（或设置 NEXT_PUBLIC_API_URL）。",

  "app.chat.title": "聊天（占位）",
  "app.chat.body": "这里后续可以接入对话 UI / 流式输出等。",
  "app.backToDashboard": "返回控制台",

  "app.journal.title": "交易日志（占位）",
  "app.journal.body": "这里后续可以接入日志记录、复盘、统计等功能。",

  "app.onboarding.title": "新手引导（占位）",
  "app.onboarding.toDashboard": "进入控制台",
  "app.onboarding.toLogin": "去登录",
}

function formatMessage(
  template: string,
  vars?: Record<string, string | number>
): string {
  if (!vars) return template
  return template.replace(/\{(\w+)\}/g, (_, key: string) => {
    const value = vars[key]
    return value === undefined ? `{${key}}` : String(value)
  })
}

export function translate(
  language: Language,
  key: MessageKey,
  vars?: Record<string, string | number>
): string {
  const dict = language === "zh" ? zh : en
  return formatMessage(dict[key], vars)
}
