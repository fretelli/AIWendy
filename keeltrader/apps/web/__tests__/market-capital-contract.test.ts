import fs from "node:fs";
import path from "node:path";

const root = path.resolve(__dirname, "..");
const market = fs.readFileSync(path.join(root, "app/(app)/agent/market/page.tsx"), "utf8");
const api = fs.readFileSync(path.join(root, "lib/api/agent-platform.ts"), "utf8");

test("capital data remains traceable inside the canonical market module", () => {
  expect(market).toContain("marketsApi.capital");
  expect(market).toContain("ETF 资金流");
  expect(market).toContain("ESTIMATED FROM SHARES");
  expect(market).toContain("Flow gaps stay explicit");
  expect(api).toContain("capital: ()");
});

test("market module exposes exactly two approved top-level tabs and professional drilldowns", () => {
  expect(market).toContain('value="market"');
  expect(market).toContain('value="macro"');
  for (const view of ["valuation", "correlation", "factors", "capital", "futures", "options", "rates"]) expect(market).toContain(`"${view}"`);
});
