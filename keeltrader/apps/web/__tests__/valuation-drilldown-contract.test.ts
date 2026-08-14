import fs from "node:fs";
import path from "node:path";

const root = path.resolve(__dirname, "..");
const market = fs.readFileSync(path.join(root, "app/(app)/agent/market/page.tsx"), "utf8");
const drilldown = fs.readFileSync(path.join(root, "components/agentos/valuation-drilldown.tsx"), "utf8");
const api = fs.readFileSync(path.join(root, "lib/api/agent-platform.ts"), "utf8");

test("valuation drilldown is lazy, range-aware and honest about partial history", () => {
  expect(market).toContain('dynamic(() => import("@/components/agentos/valuation-drilldown")');
  expect(market).toContain('kind === "held" ? "markets/valuation/held-industries" : null');
  expect(market).toContain("marketsApi.heldIndustries");
  expect(market).toContain("查看${localizedMarketName");
  for (const range of ["1M", "3M", "1Y", "3Y", "5Y"]) expect(drilldown).toContain(`"${range}"`);
  expect(drilldown).toContain("历史补录中");
  expect(drilldown).toContain("不插值、不合成");
  expect(drilldown).toContain("top_constituents");
  expect(api).toContain("ValuationHistory");
  expect(api).toContain("HeldIndustries");
});
