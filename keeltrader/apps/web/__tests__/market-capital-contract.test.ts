import fs from "node:fs";
import path from "node:path";

const root = path.resolve(__dirname, "..");
const market = fs.readFileSync(path.join(root, "app/(app)/agent/market/page.tsx"), "utf8");
const api = fs.readFileSync(path.join(root, "lib/api/agent-platform.ts"), "utf8");

test("the canonical market board uses the four approved same-screen analyses", () => {
  for (const title of ["估值分位矩阵", "大类相关性 60 日滚动", "估值分位排序 · 带时间维度", "因子收益与拥挤度"]) {
    expect(market).toContain(title);
  }
  expect(market).toContain('useSWR<ValuationBoard>');
  expect(market).toContain("marketsApi.valuationBoard");
  expect(market).toContain("marketsApi.correlations(60)");
  expect(market).toContain("marketsApi.factors");
  expect(market).toContain("item.percentile_change_3m != null");
  expect(market).toContain('item.universe === "broad"');
  expect(market).toContain('item.universe === "sw_l1"');
  expect(market).toContain('data?.metadata.methodology_key === "kt_valuation_percentile_v2"');
  expect(market).toContain("historical_coverage_partial");
  expect(api).toContain("valuationBoard: ()");
  expect(api).toContain("correlations: (window = 60)");
  expect(api).toContain("factors: ()");
});

test("major market analysis charts expose zoom reset and fullscreen without changing mini trends", () => {
  const interactive = fs.readFileSync(path.join(root, "components/agentos/interactive-chart.tsx"), "utf8");
  const charts = fs.readFileSync(path.join(root, "components/agentos/market-charts.tsx"), "utf8");
  for (const action of ["放大", "缩小", "复位", "全屏查看", "dataZoom", "dispatchAction"]) {
    expect(interactive).toContain(action);
  }
  expect(charts).toContain('zoomMode="xy"');
  expect(charts).toContain('zoomMode="x"');
  expect(market).toContain("<MiniLine values={sparkline}");
  expect(market).toContain('marketsApi.macroSeries(selected!)');
  for (const range of ['"5Y"', '"10Y"', '"ALL"']) expect(market).toContain(range);
});

test("market module exposes exactly two approved top-level tabs and professional drilldowns", () => {
  expect(market).toContain('type TopTab = "market" | "macro"');
  expect(market).not.toContain("marketViews");
  expect(market).not.toContain("<Secondary");
  expect(market).not.toContain("<MetricCard");
  for (const detail of ["rates", "futures", "options"]) expect(market).toContain(`"${detail}"`);
  for (const filter of ["全部", "宽基指数", "申万一级", "我的持仓行业"]) expect(market).toContain(filter);
});
