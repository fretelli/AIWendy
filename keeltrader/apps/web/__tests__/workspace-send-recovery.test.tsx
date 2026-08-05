import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { ApiError } from "@/lib/api/client";
import { AgentDock } from "@/components/agentos/agent-dock";
import { AgentWorkspaceProvider } from "@/components/agentos/workspace-provider";
import { agentPlatformApi } from "@/lib/api/agent-platform";

jest.mock("next/navigation", () => ({
  usePathname: () => "/agent/market",
  useRouter: () => ({ push: jest.fn() }),
}));
jest.mock("@/lib/i18n/provider", () => ({ useI18n: () => ({ locale: "zh" }) }));
jest.mock("@/lib/api/agent-platform", () => ({
  agentPlatformApi: {
    sessions: jest.fn(), agents: jest.fn(), timeline: jest.fn(), sendMessage: jest.fn(),
  },
}));

const api = agentPlatformApi as jest.Mocked<typeof agentPlatformApi>;
const session = { id: "session-1", title: "test", status: "active", interaction_mode: "ask",
  workspace_scope: "research", context_tokens: 0, is_pinned: false,
  last_message_at: "2026-08-05T00:00:00Z", created_at: "2026-08-05T00:00:00Z" } as const;
const agent = { id: "agent-1", name: "Agent", role: "research", model_profile_id: "model-1", tool_names: [] };

beforeEach(() => {
  jest.clearAllMocks();
  api.sessions.mockResolvedValue({ items: [session] });
  api.agents.mockResolvedValue({ items: [agent], builtin_tools: [], mcp_tools: [] });
  api.timeline.mockResolvedValue({ session, messages: [], runs: [] });
});

function setup() {
  render(<AgentWorkspaceProvider><AgentDock compact /></AgentWorkspaceProvider>);
  return screen.findByPlaceholderText("问 Agent…");
}

test.each([
  [new ApiError("busy", 503), true],
  [new TypeError("network"), true],
  [new ApiError("invalid", 422), false],
])("retains input and exposes the correct recovery for %p", async (failure, retryable) => {
  api.sendMessage.mockRejectedValueOnce(failure);
  const input = await setup();
  fireEvent.change(input, { target: { value: "保留这段问题" } });
  fireEvent.submit(input.closest("form")!);
  await waitFor(() => expect(input).toHaveValue("保留这段问题"));
  expect(await screen.findByRole("alert")).toBeInTheDocument();
  if (retryable) expect(screen.getByRole("button", { name: "重试" })).toBeInTheDocument();
  else expect(screen.queryByRole("button", { name: "重试" })).not.toBeInTheDocument();
});

test("retries retained input and prevents a synchronous double submit", async () => {
  let resolveFirst: ((value: unknown) => void) | undefined;
  api.sendMessage
    .mockRejectedValueOnce(new ApiError("busy", 503))
    .mockImplementationOnce(() => new Promise((resolve) => { resolveFirst = resolve; }) as never);
  const input = await setup();
  fireEvent.change(input, { target: { value: "重试问题" } });
  fireEvent.submit(input.closest("form")!);
  const retry = await screen.findByRole("button", { name: "重试" });
  fireEvent.click(retry);
  fireEvent.click(retry);
  expect(api.sendMessage).toHaveBeenCalledTimes(2);
  await act(async () => resolveFirst?.({ run: { id: "run-1", status: "queued" }, session }));
  await waitFor(() => expect(input).toHaveValue(""));
});

test("successful send clears input", async () => {
  api.sendMessage.mockResolvedValue({ run: { id: "run-1", status: "queued" } as never, session });
  const input = await setup();
  fireEvent.change(input, { target: { value: "成功问题" } });
  fireEvent.submit(input.closest("form")!);
  await waitFor(() => expect(input).toHaveValue(""));
  expect(screen.queryByRole("alert")).not.toBeInTheDocument();
});
