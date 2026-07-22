import fs from "fs";
import path from "path";

const root = process.cwd();
const today = fs.readFileSync(path.join(root, "app/(app)/agent/today/page.tsx"), "utf8");
const theses = fs.readFileSync(path.join(root, "app/(app)/agent/theses/page.tsx"), "utf8");
const shell = fs.readFileSync(path.join(root, "components/research-os-shell.tsx"), "utf8");
const opportunities = fs.readFileSync(path.join(root, "app/(app)/agent/market/opportunities/page.tsx"), "utf8");

test("today uses source date and detection time without scores", () => {
  expect(today).toContain("源日期");
  expect(today).toContain("发现：");
  expect(today).toContain("不做评分或推荐排序");
  expect(today).not.toMatch(/百分位|均线/);
});

test("thesis logbook is resizable, versioned, and never auto-selects the first row", () => {
  expect(theses).toContain("PanelResizeHandle");
  expect(theses).toContain("不可变版本");
  expect(theses).toContain("没有上次明确选择时保持总览");
  expect(theses).not.toMatch(/items\[0\]|置信分数/);
});

test("global search labels reports as navigation only", () => {
  expect(shell).toContain("globalSearch");
  expect(shell).toContain("仅用于导航，不构成公司研报证据");
});

test("opportunity creates an explicit draft thesis from an immutable snapshot", () => {
  expect(opportunities).toContain("建立论点草稿");
  expect(opportunities).toContain('status: "draft"');
  expect(opportunities).toContain('source_type: "opportunity_snapshot"');
});
