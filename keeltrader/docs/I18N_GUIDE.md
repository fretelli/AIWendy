# 国际化（i18n）使用指南（精简版）

<a id="zh-cn"></a>
[中文](#zh-cn) | [English](#en)

KeelTrader 支持英文（`en`）与简体中文（`zh`）。

更多文档见：`README.md`。

## 语言偏好存储

- Dashboard/i18n 系统使用 Cookie：`keeltrader-locale`（默认 1 年）
- 少量旧页面仍使用 Cookie/Storage：`keeltrader_lang`（后续建议统一迁移）

## 在组件中使用（推荐：JSON 翻译）

### 客户端组件

```tsx
'use client';
import { useI18n } from '@/lib/i18n/provider';

export function MyComponent() {
  const { t, locale, formatCurrency } = useI18n();
  return (
    <div>
      <h1>{t('dashboard.title')}</h1>
      <p>{locale}</p>
      <span>{formatCurrency(1999.99)}</span>
    </div>
  );
}
```

### 服务端组件

```tsx
import { getLocale, getTranslation } from '@/lib/i18n/server';

export default async function Page() {
  const locale = await getLocale();
  const title = await getTranslation('page.title', locale);
  return <h1>{title}</h1>;
}
```

## 添加/修改翻译

编辑以下文件：

- 英文：`keeltrader/apps/web/lib/i18n/translations/en.json`
- 中文：`keeltrader/apps/web/lib/i18n/translations/zh.json`

建议：

- Key 使用点分隔命名空间：`section.sub.key`
- 保持两种语言 key 完全一致
- 动态参数使用 `{name}` 形式：`t('dashboard.welcome', { name: 'John' })`

## 旧页面（TS 翻译，逐步淘汰）

少量页面仍使用 `keeltrader/apps/web/lib/i18n.ts` + `keeltrader/apps/web/components/language-provider.tsx`。

新功能优先使用 `@/lib/i18n/provider`（JSON 翻译）以减少分裂。

---

<a id="en"></a>
## English

KeelTrader supports English (`en`) and Simplified Chinese (`zh`).

More docs: `README.md`.

### Locale preference storage

- The dashboard i18n system uses a cookie: `keeltrader-locale` (default TTL: 1 year)
- A few legacy pages still use cookie/storage: `keeltrader_lang` (recommended to gradually migrate to one approach)

### Using i18n in components (recommended: JSON translations)

#### Client components

```tsx
'use client';
import { useI18n } from '@/lib/i18n/provider';

export function MyComponent() {
  const { t, locale, formatCurrency } = useI18n();
  return (
    <div>
      <h1>{t('dashboard.title')}</h1>
      <p>{locale}</p>
      <span>{formatCurrency(1999.99)}</span>
    </div>
  );
}
```

#### Server components

```tsx
import { getLocale, getTranslation } from '@/lib/i18n/server';

export default async function Page() {
  const locale = await getLocale();
  const title = await getTranslation('page.title', locale);
  return <h1>{title}</h1>;
}
```

### Adding/updating translations

Edit:

- English: `keeltrader/apps/web/lib/i18n/translations/en.json`
- Chinese: `keeltrader/apps/web/lib/i18n/translations/zh.json`

Recommendations:

- Use dot-separated namespaces for keys: `section.sub.key`
- Keep keys identical across languages
- Use `{name}` placeholders for parameters: `t('dashboard.welcome', { name: 'John' })`

### Legacy pages (TS translations, gradually being phased out)

Some pages still use `keeltrader/apps/web/lib/i18n.ts` + `keeltrader/apps/web/components/language-provider.tsx`.

For new features, prefer `@/lib/i18n/provider` (JSON translations) to reduce fragmentation.

