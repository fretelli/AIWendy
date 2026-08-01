import fs from "node:fs";
import path from "node:path";

const root = path.resolve(__dirname, "..");
const page = fs.readFileSync(path.join(root, "app/(app)/agent/opportunities/page.tsx"), "utf8");
const legacy = fs.readFileSync(path.join(root, "app/(app)/agent/holders/page.tsx"), "utf8");
const api = fs.readFileSync(path.join(root, "lib/api/agent-platform.ts"), "utf8");

test("holder monitoring lives inside opportunities and uses disclosure evidence", () => {
  expect(page).toContain("跟踪人物/机构");
  expect(page).toContain("持仓变化事件");
  expect(page).toContain("事件只来自正式披露");
  expect(page).toContain("NO SYNTHETIC SCORE");
  expect(api).toContain("holderWatchlist");
  expect(api).toContain("holderEvents");
});

test("legacy holder route redirects to the people tab", () => {
  expect(legacy).toContain('redirect("/agent/opportunities?tab=people")');
});
