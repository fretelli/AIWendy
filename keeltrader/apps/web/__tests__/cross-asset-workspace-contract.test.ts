import fs from "node:fs";
import path from "node:path";

const root = path.resolve(__dirname, "..");
const market = fs.readFileSync(path.join(root, "app/(app)/agent/market/page.tsx"), "utf8");

test("market module is evidence-first and refuses synthetic substitutes", () => {
  expect(market).toContain("NO SYNTHETIC CURVE");
  expect(market).toContain("不用指数代理或虚构曲线替代");
  expect(market).toContain("当前缺口不会用模拟矩阵填充");
  expect(market).toContain("OBSERVED, NOT SCORED");
});

test("legacy cross-asset routes redirect to canonical market tabs", () => {
  const redirects: Record<string, string> = {
    "market/rates": "/agent/market?tab=rates&period=1Y",
    "market/macro": "/agent/market?tab=macro&period=1Y",
    "market/capital": "/agent/market?tab=capital&period=1Y",
    "market/options": "/agent/market?tab=options&period=1Y",
    "market/futures": "/agent/market?tab=futures&period=1Y",
  };
  for (const [route, destination] of Object.entries(redirects)) {
    const source = fs.readFileSync(path.join(root, `app/(app)/agent/${route}/page.tsx`), "utf8");
    expect(source).toContain(`redirect("${destination}")`);
  }
});
