import fs from "node:fs";
import path from "node:path";

const root = path.resolve(__dirname, "..");

describe("Claude AgentOS design contract", () => {
  it("locks the accepted dark palette and bundled typography", () => {
    const css = fs.readFileSync(path.join(root, "app/globals.css"), "utf8");
    const layout = fs.readFileSync(path.join(root, "app/layout.tsx"), "utf8");
    const providers = fs.readFileSync(path.join(root, "app/providers.tsx"), "utf8");
    expect(css).toContain('--font-body: "Noto Sans SC"');
    expect(css).toContain('--font-data: "IBM Plex Mono"');
    expect(css).toContain("--agent-page: #050708");
    expect(css).toContain("--agent-canvas: #07090b");
    expect(css).toContain("prefers-reduced-motion");
    expect(layout).toContain('@fontsource-variable/noto-sans-sc');
    expect(layout).toContain('@fontsource/ibm-plex-mono/400.css');
    expect(providers).toContain('forcedTheme="dark"');
  });

  it("preserves the 78/60/384 desktop frame", () => {
    const shell = fs.readFileSync(path.join(root, "components/agentos/agentos-shell.tsx"), "utf8");
    expect(shell).toContain("w-[78px]");
    expect(shell).toContain("h-[60px]");
    expect(shell).toContain("w-[384px]");
  });
});
