import fs from "fs";
import path from "path";

const root = path.join(process.cwd());
const page = fs.readFileSync(path.join(root, "app/(app)/agent/market/opportunities/page.tsx"), "utf8");
const client = fs.readFileSync(path.join(root, "lib/api/agent-platform.ts"), "utf8");

test("unified opportunity center keeps the map, private scopes, and manual selection contract", () => {
  expect(page).toContain("机会航图");
  expect(page).toContain("我的公司");
  expect(page).toContain("我的股东");
  expect(page).toContain("已关注");
  expect(page).toContain("window.localStorage.getItem(LAST_SELECTION)");
  expect(page).not.toContain("o.items[0]");
  expect(page).not.toContain("items[0].id");
  expect(page).toContain("没有上次选择时保持总览");
});

test("opportunity actions and evidence snapshots are explicit and never scored", () => {
  expect(client).toContain("followOpportunity");
  expect(client).toContain("updateOpportunityFollow");
  expect(client).toContain("unfollowOpportunity");
  expect(page).toContain("不可变快照航迹");
  expect(page).toContain("evidence: latest?.evidence || selected.evidence || []");
  expect(page).toContain("操作舱");
  expect(page).toContain("默认收起");
  expect(page).toContain("不评分");
  expect(page).not.toMatch(/百分位|均线|Kelly|自动下单/);
});

test("desktop workspace is resizable and mobile remains stacked", () => {
  expect(page).toContain("PanelResizeHandle");
  expect(page).toContain('autoSaveId="opportunity-workspace"');
  expect(page).toContain('className="space-y-4 md:hidden"');
});

test("self-hosting deploys the isolated opportunity worker", () => {
  const compose = fs.readFileSync(path.join(root, "../../docker-compose.selfhost.yml"), "utf8");
  expect(compose).toContain("opportunity-worker:");
  expect(compose).toContain("tasks/opportunity_worker.py");
  expect(compose).toContain("OPPORTUNITY_REFRESH_SECONDS");
});
