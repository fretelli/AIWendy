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
});

test("derivatives are implementation tools instead of allocation sleeves", () => {
  expect(page).toContain("期货和期权属于实施工具，不增加资产类别");
  expect(page).not.toContain('sleeve_key: "options"');
  expect(page).not.toContain('sleeve_key: "futures"');
});

test("mobile navigation adds allocation without six cramped equal items", () => {
  expect(shell).toContain('href: "/agent/allocation"');
  expect(shell).toContain("mobilePrimary");
  expect(shell).toContain("mobileMore");
  expect(shell).toContain("更多");
});
