import fs from "node:fs";
import path from "node:path";

const root = path.resolve(__dirname, "..");
const page = fs.readFileSync(path.join(root, "app/(app)/agent/allocation/page.tsx"), "utf8");
const legacy = fs.readFileSync(path.join(root, "app/(app)/agent/allocation/framework/page.tsx"), "utf8");

test("allocation consolidates SAA TAA rebalance and stress in one module", () => {
  for (const value of ["SAA", "TAA", "rebalance", "stress"]) expect(page).toContain(value);
  expect(page).toContain("NO ORDER EXECUTION");
  expect(page).toContain("不连接券商或创建订单");
  expect(page).toContain("不会用演示权重填充生产页面");
});

test("legacy allocation framework route redirects to the canonical module", () => {
  expect(legacy).toContain('redirect("/agent/allocation")');
});
