import fs from "node:fs";
import path from "node:path";

const root = path.resolve(__dirname, "..");
const market = fs.readFileSync(path.join(root, "app/(app)/agent/market/page.tsx"), "utf8");
const macroCard = fs.readFileSync(path.join(root, "components/agentos/macro-card.tsx"), "utf8");
const api = fs.readFileSync(path.join(root, "lib/api/agent-platform.ts"), "utf8");
const shell = fs.readFileSync(path.join(root, "components/agentos/agentos-shell.tsx"), "utf8");
const drilldowns = fs.readFileSync(path.join(root, "components/agentos/market-drilldowns.tsx"), "utf8");

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
  expect(market).toContain('valuation?.metadata.methodology_key === "kt_valuation_percentile_v3"');
  expect(market).toContain('useState<ValuationScope>("broad")');
  expect(market).not.toContain("['all', '全部', 'All']");
  expect(market).toContain("PE-TTM");
  expect(market).toContain("PE（申万源口径）");
  expect(market).toContain("historical_coverage_partial");
  expect(api).toContain("valuationBoard: ()");
  expect(api).toContain("valuationHistory: (code: string");
  expect(api).toContain("heldIndustries: ()");
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
  expect(macroCard).toContain("<MiniLine values={sparkline}");
  expect(market).toContain('marketsApi.macroSeries(selected!, undefined, historyWindow)');
  for (const range of ['"5Y"', '"10Y"', '"ALL"']) expect(market).toContain(range);
  expect(market).toContain('"5Y": 1260');
  expect(market).toContain("FullscreenDataView");
  expect(market).toContain("Math.max(10, Math.min(20");
  expect(market).toContain('event.key === "0"');
  expect(interactive).toContain('chart.on("click"');
  expect(interactive).toContain("itemClickRef.current");
  expect(market).toContain("ValuationDrilldown");
  expect(market).toContain("onSelect={setSelectedValuation}");
  expect(shell).toContain("!isMarketModule ? <div");
  expect(shell).toContain('item.href === "/agent/market" ? item.href');
  expect(shell).toContain('current.href !== "/agent/market"');
  expect(shell).not.toContain("正式历史从 2020 年开始");
  expect(market).toContain('pair ? `markets/correlations/60/history/${range}` : null');
  expect(market).toContain('selected ? `markets/factors/history/${range}` : null');
  expect(market).toContain("范围只控制当前图表");
  expect(market).not.toContain("范围用于历史下钻");
  expect(drilldowns).toContain("当前期货历史范围");
  expect(drilldowns).toContain('useState<HistoryRange>("1Y")');
});

test("market module exposes exactly two approved top-level tabs and professional drilldowns", () => {
  expect(market).toContain('type TopTab = "market" | "macro"');
  expect(market).not.toContain("marketViews");
  expect(market).not.toContain("<Secondary");
  expect(market).not.toContain("<MetricCard");
  for (const detail of ["rates", "futures", "options"]) expect(market).toContain(`"${detail}"`);
  for (const filter of ["宽基指数", "申万一级", "我的持仓行业"]) expect(market).toContain(filter);
});

test("macro v4 separates display range from a selectable point-in-time historical benchmark", () => {
  for (const theme of ["增长与需求", "物价", "信用与货币", "景气与就业", "外贸与外储", "利率与收益率", "财政"]) {
    expect(market).toContain(theme);
  }
  for (const headline of ["GDP 同比", "CPI 同比", "M2 同比", "社会融资增量", "制造业 PMI"]) {
    expect(macroCard).toContain(headline);
  }
  expect(macroCard).toContain("未接入 · 不使用代理");
  expect(macroCard).toContain("Tushare eco_cal · 覆盖门禁");
  expect(macroCard).toContain("已滞后");
  expect(market).toContain("宽基覆盖");
  expect(market).toContain("官方字段白名单");
  expect(market).toContain("年内累计值只用于观察规模和结构");
  expect(market).toContain("marketsApi.macroSeries(selected!, selectedField!)");
  expect(macroCard).toContain("结构快照");
  expect(market).toContain("总览分析");
  expect(market).toContain("细分结构");
  expect(market).toContain("展示范围");
  expect(market).toContain("历史比较基准");
  expect(market).toContain("每个时点只与其此前所选长度的历史比较");
  expect(market).toContain('const HISTORICAL_POSITION_WINDOWS: HistoricalPositionWindow[] = ["5Y", "10Y", "20Y", "ALL"]');
  expect(market).toContain('value === "primary" || value === "historical_position"');
  expect(api).toContain('history_window');
  expect(api).toContain('"historical_position"');
  expect(macroCard).toContain("历史位置 ·");
  expect(macroCard).toContain("查看全部");
  expect(macroCard).toContain("进入完整利率工作台");
  expect(market).toContain('detail=rates&period=1Y');
  expect(market).toContain("<MacroChartPanel kind={kind}");
  expect(market).not.toContain('<MacroChartPanel kind="primary"');
  expect(api).toContain("field_catalog?: MacroFieldMeta[]");
  expect(api).toContain("featured_fields?: MacroFeaturedField[]");
  expect(api).toContain("latest_release?: MacroLatestRelease");
});
