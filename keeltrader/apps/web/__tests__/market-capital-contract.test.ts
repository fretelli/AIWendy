import fs from "node:fs";
import path from "node:path";

const root = path.resolve(__dirname, "..");
const market = fs.readFileSync(path.join(root, "app/(app)/agent/market/page.tsx"), "utf8");
const api = fs.readFileSync(path.join(root, "lib/api/agent-platform.ts"), "utf8");

test("the canonical market board uses the four approved same-screen analyses", () => {
  for (const title of ["估值分位矩阵", "大类相关性 60 日滚动", "估值分位排序 · 带时间维度", "因子收益与拥挤度"]) {
    expect(market).toContain(title);
  }
  expect(market).toContain("marketsApi.valuationBoard()");
  expect(market).toContain("marketsApi.correlations(60)");
  expect(market).toContain("marketsApi.factors()");
  expect(market).toContain("item.percentile_change_3m != null");
  expect(market).toContain("historical_coverage_partial");
  expect(api).toContain("valuationBoard: ()");
  expect(api).toContain("correlations: (window = 60)");
  expect(api).toContain("factors: ()");
});

test("market module exposes exactly two approved top-level tabs and professional drilldowns", () => {
  expect(market).toContain('type TopTab = "market" | "macro"');
  expect(market).not.toContain("marketViews");
  expect(market).not.toContain("<Secondary");
  expect(market).not.toContain("<MetricCard");
  for (const detail of ["rates", "futures", "options"]) expect(market).toContain(`"${detail}"`);
  for (const filter of ["全部", "宽基指数", "申万一级", "我的持仓行业"]) expect(market).toContain(filter);
});
