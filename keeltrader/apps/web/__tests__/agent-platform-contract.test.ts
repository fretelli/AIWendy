import fs from "node:fs";
import path from "node:path";

const root = path.resolve(__dirname, "..");
const shell = fs.readFileSync(path.join(root, "components/agentos/agentos-shell.tsx"), "utf8");
const provider = fs.readFileSync(path.join(root, "components/agentos/workspace-provider.tsx"), "utf8");
const workspace = fs.readFileSync(path.join(root, "app/(app)/agent/workspace/page.tsx"), "utf8");

describe("AgentOS workspace contract", () => {
  it("keeps one persistent agent runtime across all eight modules", () => {
    for (const route of ["/agent", "/agent/allocation", "/agent/holdings", "/agent/market", "/agent/opportunities", "/agent/decisions", "/agent/research", "/agent/workspace"]) {
      expect(shell).toContain(`href: "${route}"`);
      expect(provider).toContain(`"${route}"`);
    }
    expect(shell).toContain("<AgentDock />");
    expect(provider).toContain("new EventSource");
    expect(provider).toContain("message.delta");
  });

  it("shows safe tool traces without exposing model reasoning or trade execution", () => {
    expect(workspace).toContain("不展示模型思维链");
    expect(workspace).toContain("SAFE TOOL TRACE");
    expect(workspace).not.toMatch(/place_order|cancel_order|execute_trade/);
  });
});
