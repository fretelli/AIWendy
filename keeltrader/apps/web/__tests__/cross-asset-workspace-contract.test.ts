import fs from "node:fs";
import path from "node:path";

const root = path.resolve(__dirname, "..");
const market = fs.readFileSync(path.join(root, "app/(app)/agent/market/page.tsx"), "utf8");

test("market module is evidence-first and refuses synthetic substitutes", () => {
  expect(market).toContain("publication_pending");
  expect(market).toContain("kt_factor_v1 · ${data?.crowding.methodology_key");
  expect(market).toContain("固定权重未重分配");
  expect(market).toContain("不使用代理或反推值");
});

test("legacy cross-asset routes redirect to canonical market tabs", () => {
  const redirects: Record<string, string> = {
    "market/rates": "/agent/market?tab=macro&detail=rates&period=1Y",
    "market/macro": "/agent/market?tab=macro&period=1Y",
    "market/capital": "/agent/market?tab=market&period=1Y",
    "market/options": "/agent/market?tab=market&detail=options&period=1Y",
    "market/futures": "/agent/market?tab=market&detail=futures&period=1Y",
  };
  for (const [route, destination] of Object.entries(redirects)) {
    const source = fs.readFileSync(path.join(root, `app/(app)/agent/${route}/page.tsx`), "utf8");
    expect(source).toContain(`redirect("${destination}")`);
  }
});
