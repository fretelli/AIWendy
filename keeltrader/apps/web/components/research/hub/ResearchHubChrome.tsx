import { Bell, RefreshCw, Sparkles, Star } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";

import { MODULES } from "./constants";
import { type TabValue } from "./types";

export function ResearchHubHeader({ onRefresh }: { onRefresh: () => void }) {
  return (
    <div className="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
      <div>
        <div className="flex flex-wrap items-center gap-2">
          <Badge variant="outline">Research Web</Badge>
          <Badge variant="secondary">小程序功能迁移</Badge>
        </div>
        <h1 className="mt-3 text-2xl font-bold">研报中心</h1>
        <p className="mt-2 max-w-3xl text-sm leading-6 text-muted-foreground">
          将研报小程序的首页、期刊、研报详情、机构图鉴、积分商城、权益、偏好和反馈功能整合到 KeelTrader Web。
        </p>
      </div>
      <Button variant="outline" onClick={onRefresh}>
        <RefreshCw className="mr-2 h-4 w-4" />
        全部刷新
      </Button>
    </div>
  );
}

export function ResearchModuleGrid({
  activeTab,
  onChange,
}: {
  activeTab: TabValue;
  onChange: (tab: TabValue) => void;
}) {
  return (
    <div className="grid gap-3 md:grid-cols-7">
      {MODULES.map((item) => {
        const Icon = item.icon;
        return (
          <button
            key={item.value}
            type="button"
            onClick={() => onChange(item.value)}
            className={`rounded-md border p-3 text-left transition-colors hover:bg-muted/40 ${activeTab === item.value ? "border-primary bg-muted/50" : ""}`}
          >
            <Icon className="h-5 w-5" />
            <div className="mt-2 text-sm font-medium">{item.label}</div>
          </button>
        );
      })}
    </div>
  );
}

export function ResearchHubFooter() {
  return (
    <div className="grid gap-4 md:grid-cols-3">
      <div className="rounded-md border p-4">
        <Sparkles className="h-5 w-5" />
        <div className="mt-2 font-medium">公共推荐可匿名访问</div>
        <div className="mt-1 text-sm text-muted-foreground">未授权用户也能阅读公共研报推荐和机构图鉴。</div>
      </div>
      <div className="rounded-md border p-4">
        <Bell className="h-5 w-5" />
        <div className="mt-2 font-medium">个性化功能使用真实接口</div>
        <div className="mt-1 text-sm text-muted-foreground">会员、积分、偏好、历史期刊使用 research API token。</div>
      </div>
      <div className="rounded-md border p-4">
        <Star className="h-5 w-5" />
        <div className="mt-2 font-medium">反馈进入同一后台</div>
        <div className="mt-1 text-sm text-muted-foreground">意见反馈和积分商城许愿都会出现在 research admin。</div>
      </div>
    </div>
  );
}
