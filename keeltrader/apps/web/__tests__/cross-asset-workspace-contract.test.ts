import fs from "node:fs";
import path from "node:path";

const root = path.resolve(__dirname, "..");
const market = fs.readFileSync(path.join(root, "app/(app)/agent/market/page.tsx"), "utf8");

test("market module is evidence-first and refuses synthetic substitutes", () => {
  expect(market).toContain("NO SUBSTITUTION");
  expect(market).toContain("不以静态 PE、指数代理或原型模拟值代替历史分位");
  expect(market).toContain("只有频率、截至日和 publication 版本一致时才计算相关矩阵");
  expect(market).toContain("OBSERVED PROXIES");
});

test("legacy cross-asset routes redirect to canonical market tabs", () => {
  const redirects: Record<string, string> = {
    "market/rates": "/agent/market?tab=macro&view=rates&period=1Y",
    "market/macro": "/agent/market?tab=macro&view=dashboard&period=1Y",
    "market/capital": "/agent/market?tab=market&view=capital&period=1Y",
    "market/options": "/agent/market?tab=market&view=options&period=1Y",
    "market/futures": "/agent/market?tab=market&view=futures&period=1Y",
  };
  for (const [route, destination] of Object.entries(redirects)) {
    const source = fs.readFileSync(path.join(root, `app/(app)/agent/${route}/page.tsx`), "utf8");
    expect(source).toContain(`redirect("${destination}")`);
  }
});
