import fs from "fs";
import path from "path";

const root = process.cwd();
const page = fs.readFileSync(path.join(root, "app/(app)/agent/allocation/framework/page.tsx"), "utf8");
const shell = fs.readFileSync(path.join(root, "components/research-os-shell.tsx"), "utf8");
const marketShell = fs.readFileSync(path.join(root, "app/(app)/agent/capital/_components/market-shell.tsx"), "utf8");
const opportunity = fs.readFileSync(path.join(root, "app/(app)/agent/market/opportunities/page.tsx"), "utf8");
const nextConfig = fs.readFileSync(path.join(root, "next.config.js"), "utf8");

test("opportunity center is top-level and the legacy market URL redirects permanently", () => {
  expect(shell).toContain('href: "/agent/opportunities"');
  expect(shell).toContain('label: "机会中心"');
  expect(marketShell).not.toContain('/agent/market/opportunities", label: "机会"');
  expect(nextConfig).toContain("source: '/agent/market/opportunities', destination: '/agent/opportunities', permanent: true");
  expect(opportunity).toContain('showNavigation={false}');
});

test("household framework includes lifecycle layers buckets goals and core satellite", () => {
  expect(page).toContain("家庭生命周期");
  expect(page).toContain("单人家庭拥有完整功能");
  expect(page).toContain("安全层");
  expect(page).toContain("市场层");
  expect(page).toContain("进取层");
  expect(page).toContain("短期桶");
  expect(page).toContain("中期桶");
  expect(page).toContain("长期桶");
  expect(page).toContain("核心预算");
  expect(page).toContain("卫星预算");
  expect(page).toContain("资金指定");
});

test("SAA and TAA remain manual versioned planning layers without a new optimizer", () => {
  expect(page).toContain("SAA 长期基线");
  expect(page).toContain("TAA 人工覆盖层");
  expect(page).toContain("安全层锁定");
  expect(page).toContain("不自动续期");
  expect(page).toContain("不自动生成仓位");
  expect(page).toContain("创建 TAA 草案");
  expect(page).toContain("maxTaaDelta");
  expect(page).toContain("偏离幅度 % · 上限");
  expect(page).not.toMatch(/优化算法选择|均值方差|Black-Litterman|风险预算选择器/);
});

test("legacy ERC engine stays separately reachable from the framework", () => {
  expect(page).toContain('href="/agent/allocation"');
  const allocation = fs.readFileSync(path.join(root, "app/(app)/agent/allocation/page.tsx"), "utf8");
  expect(allocation).toContain("资本航路");
  expect(allocation).toContain('href="/agent/allocation/framework"');
});
