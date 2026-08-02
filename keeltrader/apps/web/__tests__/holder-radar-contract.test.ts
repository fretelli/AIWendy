import fs from "node:fs";
import path from "node:path";

const root = path.resolve(__dirname, "..");
const page = fs.readFileSync(path.join(root, "app/(app)/agent/opportunities/page.tsx"), "utf8");
const legacy = fs.readFileSync(path.join(root, "app/(app)/agent/holders/page.tsx"), "utf8");
const api = fs.readFileSync(path.join(root, "lib/api/agent-platform.ts"), "utf8");

test("holder monitoring lives inside opportunities and uses disclosure evidence", () => {
  expect(page).toContain("跟踪人物 / 机构");
  expect(page).toContain("最新披露变化");
  expect(page).toContain("只使用正式披露，不用传闻补位");
  expect(page).toContain("DISCLOSURE WATCH");
  expect(api).toContain("holderWatchlist");
  expect(api).toContain("holderEvents");
});

test("legacy holder route redirects to the watchlist panel in signals", () => {
  expect(legacy).toContain('redirect("/agent/opportunities?tab=signals&panel=watchlist")');
});
