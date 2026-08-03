import fs from "node:fs";
import path from "node:path";

const root = path.resolve(__dirname, "..");
const page = fs.readFileSync(path.join(root, "app/(app)/agent/allocation/page.tsx"), "utf8");
const legacy = fs.readFileSync(path.join(root, "app/(app)/agent/allocation/framework/page.tsx"), "utf8");

test("allocation consolidates SAA TAA rebalance and stress in one module", () => {
  for (const value of ["SAA", "TAA", "rebalance", "stress"]) expect(page).toContain(value);
  expect(page).toContain("NO ORDER EXECUTION");
  expect(page).toContain("不连接券商、不创建订单");
  expect(page).toContain("历史不足时不会产生示例权重");
  for (const method of ["black_litterman", "core_satellite", "risk_parity", "all_weather", "lifecycle"]) expect(page).toContain(method);
});

test("legacy allocation framework route redirects to the canonical module", () => {
  expect(legacy).toContain('redirect("/agent/allocation")');
});

test("allocation missing-input reason codes are localized", () => {
  expect(page).toContain('cny_cash: ["人民币计价与现金收益序列"');
});
