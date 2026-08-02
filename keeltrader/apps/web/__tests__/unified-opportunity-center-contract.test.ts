import fs from "node:fs";
import path from "node:path";

const root = path.resolve(__dirname, "..");
const page = fs.readFileSync(path.join(root, "app/(app)/agent/opportunities/page.tsx"), "utf8");
const client = fs.readFileSync(path.join(root, "lib/api/agent-platform.ts"), "utf8");

test("opportunity center keeps two top tabs and embeds tracked people in signals", () => {
  expect(page).toContain('value="signals"');
  expect(page).toContain('value="relative"');
  expect(page).not.toContain('value="people"');
  expect(page).toContain("跟踪人物 / 机构");
  expect(page).toContain("TRIGGER / EVIDENCE / FALSIFIER");
});

test("following is manual and never creates orders", () => {
  expect(client).toContain("followOpportunity");
  expect(page).toContain("onFollow");
  expect(page).not.toMatch(/自动下单|place_order|execute_trade/);
});

test("self-hosting keeps the isolated opportunity worker", () => {
  const compose = fs.readFileSync(path.join(root, "../../docker-compose.selfhost.yml"), "utf8");
  expect(compose).toContain("opportunity-worker:");
  expect(compose).toContain("tasks/opportunity_worker.py");
});
