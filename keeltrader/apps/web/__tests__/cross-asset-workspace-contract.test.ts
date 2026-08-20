import fs from "node:fs";
import path from "node:path";

const root = path.resolve(__dirname, "..");
const market = fs.readFileSync(path.join(root, "app/(app)/agent/market/page.tsx"), "utf8");
const drilldowns = fs.readFileSync(path.join(root, "components/agentos/market-drilldowns.tsx"), "utf8");

test("market module is evidence-first and refuses synthetic substitutes", () => {
  expect(market).toContain("publication_pending");
  expect(market).toContain("kt_factor_v1 · ${data?.crowding.methodology_key");
  expect(market).toContain("固定权重未重分配");
  expect(market).toContain("不使用代理或反推值");
});

test("rates drilldown exposes official history and US Treasury term datasets", () => {
  for (const key of ["libor_usd", "hibor", "us_short", "us_long", "us_real_long_average", "wenzhou_private", "guangzhou_private"]) {
    expect(drilldowns).toContain(key);
  }
  expect(drilldowns).toContain("Provider history ends on 2020-06-24");
  expect(drilldowns).toContain("Provider history ends on 2023-03-08");
  expect(drilldowns).toContain("Provider history ends on 2019-03-04");
  expect(drilldowns).toContain("长期复合利率");
  expect(drilldowns).toContain("10年以上实际平均利率");
  expect(drilldowns).toContain('const RATE_HISTORY_RANGES = [...HISTORY_RANGES, "10Y", "ALL"]');
  expect(drilldowns).toContain("民间借贷服务中心");
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
