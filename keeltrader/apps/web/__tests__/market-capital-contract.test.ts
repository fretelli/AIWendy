import fs from "node:fs";
import path from "node:path";

const root = path.resolve(__dirname, "..");
const market = fs.readFileSync(path.join(root, "app/(app)/agent/market/page.tsx"), "utf8");
const api = fs.readFileSync(path.join(root, "lib/api/agent-platform.ts"), "utf8");

test("capital data remains traceable inside the canonical market module", () => {
  expect(market).toContain("marketsApi.capital");
  expect(market).toContain("ETF 资金流");
  expect(market).toContain("ESTIMATED FROM SHARES");
  expect(market).toContain("数据解释");
  expect(api).toContain("capital: ()");
});

test("market module exposes the five approved research tabs", () => {
  for (const tab of ["valuation", "correlation", "factors", "macro", "capital"]) {
    expect(market).toContain(`value="${tab}"`);
  }
});
