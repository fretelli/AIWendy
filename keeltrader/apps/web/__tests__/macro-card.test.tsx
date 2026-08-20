import { fireEvent, render, screen } from "@testing-library/react";

import { MacroCard } from "@/components/agentos/macro-card";
import type { MacroCatalog } from "@/lib/api/agent-platform";

const metric = { value: 4.7, unit: "%", method: "official" as const, status: "available" };

const gdp: MacroCatalog["items"][number] = {
  key: "gdp",
  label: "GDP 同比",
  domain: "macro",
  theme: "growth",
  available: true,
  fields: ["gdp", "gdp_yoy", "pi", "pi_yoy", "si", "si_yoy", "ti", "ti_yoy"],
  end: "2026Q2",
  source: "tushare.cn_gdp",
  summary: { primary: metric, mom: metric, yoy: metric, percentile_10y: metric },
  field_catalog: [
    { key: "pi_yoy", label: "第一产业同比", unit: "%", group: "产业结构" },
    { key: "si_yoy", label: "第二产业同比", unit: "%", group: "产业结构" },
    { key: "ti_yoy", label: "第三产业同比", unit: "%", group: "产业结构" },
  ],
  featured_fields: [
    { key: "pi_yoy", label: "第一产业同比", unit: "%", group: "产业结构", value: 3.7, period: "2026Q2" },
    { key: "si_yoy", label: "第二产业同比", unit: "%", group: "产业结构", value: 3.9, period: "2026Q2" },
    { key: "ti_yoy", label: "第三产业同比", unit: "%", group: "产业结构", value: 5.2, period: "2026Q2" },
  ],
  quality: { source_type: "structured", status: "available" },
};

test("GDP card exposes the three industries and opens the exact selected field", () => {
  const onOpenField = jest.fn();
  const { container } = render(<MacroCard row={gdp} locale="zh" onOpenAnalysis={jest.fn()} onOpenField={onOpenField} onOpenAll={jest.fn()} />);

  expect(screen.getByText("第一产业同比")).toBeInTheDocument();
  expect(screen.getByText("第二产业同比")).toBeInTheDocument();
  expect(screen.getByText("第三产业同比")).toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: /第一产业同比/ }));
  expect(onOpenField).toHaveBeenCalledWith("pi_yoy");
  expect(container.querySelector("button button")).toBeNull();
});
