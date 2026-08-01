import fs from "node:fs";
import path from "node:path";

const root = path.resolve(__dirname, "..");
const allocation = fs.readFileSync(path.join(root, "app/(app)/agent/allocation/page.tsx"), "utf8");
const shell = fs.readFileSync(path.join(root, "components/agentos/agentos-shell.tsx"), "utf8");

test("wealth framework feeds versioned allocation without automatic orders", () => {
  expect(allocation).toContain("wealthProfile");
  expect(allocation).toContain("saaPolicyVersions");
  expect(allocation).toContain("taaOverlays");
  expect(allocation).toContain("FALSIFIABLE OVERLAY");
  expect(allocation).toContain("No broker connection or order creation");
});

test("allocation is a single top-level AgentOS module", () => {
  expect(shell).toContain('{ no: "02", href: "/agent/allocation"');
  expect(shell).not.toContain("/agent/today");
  expect(shell).not.toContain("/agent/theses");
});
