import fs from "node:fs";
import path from "node:path";

const root = path.resolve(__dirname, "..");
const read = (relative: string) => fs.readFileSync(path.join(root, relative), "utf8");

test("the eight-module shell matches the approved information architecture", () => {
  const shell = read("components/agentos/agentos-shell.tsx");
  expect(shell).toContain('zhTitle: "市场与宏观"');
  expect(shell).toContain('zh: "大盘 · 行业 · 资金流"');
  expect(shell).toContain('zh: "宏观数据"');
  expect(shell).toContain('zh: "研报"');
  expect(shell).not.toContain('zh: "研究"');
});

test("all module pages preserve real gaps and approved workflows", () => {
  const allocation = read("app/(app)/agent/allocation/page.tsx");
  const holdings = read("app/(app)/agent/holdings/page.tsx");
  const market = read("app/(app)/agent/market/page.tsx");
  const opportunities = read("app/(app)/agent/opportunities/page.tsx");
  const decisions = read("app/(app)/agent/decisions/page.tsx");
  const research = read("app/(app)/agent/research/page.tsx");
  const workspace = read("app/(app)/agent/workspace/page.tsx");
  expect(allocation).toContain("generateAllocationPolicyWithMethod");
  expect(allocation).toContain("publishAllocationPolicyAsSaa");
  expect(holdings).toContain("holdingDetail");
  expect(holdings).toContain("NO SYNTHETIC GREEKS");
  expect(market).toContain('type TopTab = "market" | "macro"');
  expect(opportunities).not.toContain('value="people"');
  expect(opportunities).toContain("Research record created");
  expect(decisions).not.toContain("fundamentals: {}");
  expect(research).toContain("researchLibrary");
  expect(research).toContain("generateBilingualDocument");
  expect(research).toContain("content_brief_sink_enabled");
  expect(research).toContain("submitContentBrief");
  expect(research).toContain('["invalidated", "archived"]');
  expect(workspace).toMatch(/Tushare (?:数据)?调用日志/);
  expect(workspace).not.toMatch(/chain_of_thought\s*:/);
});
