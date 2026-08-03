import fs from "node:fs";
import path from "node:path";

const root = path.resolve(__dirname, "..");
const allocation = fs.readFileSync(path.join(root, "app/(app)/agent/allocation/page.tsx"), "utf8");
const shell = fs.readFileSync(path.join(root, "components/agentos/agentos-shell.tsx"), "utf8");

test("wealth framework feeds versioned allocation without automatic orders", () => {
  expect(allocation).toContain("wealthProfile");
  expect(allocation).toContain("saaPolicyVersions");
  expect(allocation).toContain("taaOverlays");
  expect(allocation).toContain("FALSIFIABLE");
  expect(allocation).toContain("no broker connection or orders");
  expect(allocation).toContain("publishAllocationPolicyAsSaa");
});

test("allocation is a single top-level AgentOS module", () => {
  expect(shell).toMatch(/no:\s*"02",\s*href:\s*"\/agent\/allocation"/);
  expect(shell).not.toContain("/agent/today");
  expect(shell).not.toContain("/agent/theses");
});
