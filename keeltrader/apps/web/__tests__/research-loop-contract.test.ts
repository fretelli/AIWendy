import fs from "fs";
import path from "path";

const root = process.cwd();
const shell = fs.readFileSync(path.join(root, "components/research-os-shell.tsx"), "utf8");
const opportunities = fs.readFileSync(path.join(root, "app/(app)/agent/market/opportunities/page.tsx"), "utf8");

test("today and thesis modules are fully retired from the web surface", () => {
  expect(fs.existsSync(path.join(root, "app/(app)/agent/today/page.tsx"))).toBe(false);
  expect(fs.existsSync(path.join(root, "app/(app)/agent/theses/page.tsx"))).toBe(false);
  expect(shell).not.toContain("/agent/today");
  expect(shell).not.toContain("/agent/theses");
  expect(shell).not.toContain("论点与配置");
});

test("global search labels reports as navigation only", () => {
  expect(shell).toContain("globalSearch");
  expect(shell).toContain("仅用于导航，不构成公司研报证据");
});

test("opportunity no longer creates thesis records", () => {
  expect(opportunities).not.toContain("建立论点草稿");
  expect(opportunities).not.toContain("createThesis");
  expect(opportunities).not.toContain("/agent/theses");
});
