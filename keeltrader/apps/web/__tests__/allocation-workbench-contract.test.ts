import fs from "fs";
import path from "path";

const page = fs.readFileSync(path.join(process.cwd(), "app/(app)/agent/allocation/page.tsx"), "utf8");
const shell = fs.readFileSync(path.join(process.cwd(), "components/research-os-shell.tsx"), "utf8");

test("allocation workbench keeps formal data gate and immutable research handoff", () => {
  expect(page).toContain("资本航路");
  expect(page).toContain("status?.formal_ready");
  expect(page).toContain('resource_type: "allocation_policy"');
  expect(page).toContain("不使用预期收益、评分、因子、均线或百分位");
  expect(page).toContain("不使用代理替代");
  expect(page).toContain("全量 · 未降采样");
  expect(page).toContain("人民币总回报全量月度历史");
  expect(page).toContain("币种暴露");
  expect(page).toContain("不提供换汇换算");
  expect(page).toContain("等待回填");
  expect(page).toContain("历史不足");
  expect(page).toContain("存在缺口");
  expect(page).toContain("已就绪");
});

test("derivatives are implementation tools instead of allocation sleeves", () => {
  expect(page).toContain("期货和期权属于实施工具，不增加资产类别");
  expect(page).not.toContain('sleeve_key: "options"');
  expect(page).not.toContain('sleeve_key: "futures"');
});

test("mobile navigation opens the framework first without hiding the existing engine", () => {
  expect(shell).toContain('href: "/agent/allocation/framework"');
  expect(shell).toContain('label: "资产配置"');
  expect(shell).not.toContain('label: "今日"');
  expect(shell).not.toContain('label: "论点"');
  expect(shell).toContain("mobilePrimary");
  expect(shell).toContain("mobileMore");
  expect(shell).toContain("更多");
});

test("allocation page exposes the versioned methodology", () => {
  expect(page).toContain("资产配置方法论");
  expect(page).toContain("methodology_snapshot");
  expect(page).toContain("Ledoit–Wolf 月度协方差");
  expect(page).toContain("不前向填充缺失值");
  expect(page).toContain("版本内固化 · 可审计");
});
