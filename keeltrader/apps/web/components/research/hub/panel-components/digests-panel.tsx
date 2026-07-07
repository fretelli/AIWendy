"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { CheckCircle2, RefreshCw, Settings2 } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { type DigestDetail, type NotificationResponse, type ReportCardItem, type UserProfileResponse } from "@/lib/research-api";

import { digestPeriodKey, digestPeriodKeyFromDate, formatDateTime } from "../formatters";
import { EmptyState, ErrorState } from "../states";
import { ReportRow } from "./report-row";

export function DigestsPanel({
  feed,
  notifications,
  profile,
  publicItems,
  error,
  onReload,
  onRefreshNotifications,
  onMarkRead,
  onMarkAllRead,
  onGoPreferences,
}: {
  feed: DigestDetail | null;
  notifications: NotificationResponse | null;
  profile: UserProfileResponse | null;
  publicItems: ReportCardItem[];
  error: string;
  onReload: () => void;
  onRefreshNotifications: () => void;
  onMarkRead: (id: number) => void;
  onMarkAllRead: () => void;
  onGoPreferences: () => void;
}) {
  const [visibleCount, setVisibleCount] = useState(3);
  const digestItems = useMemo(() => (notifications?.items || []).filter((item) => item.type === "report_digest"), [notifications]);
  const currentMode = profile?.profile_completed && profile.preferences.update_frequency !== "每周" ? "daily" : "weekly";
  const currentPeriodKey = digestPeriodKeyFromDate(currentMode, new Date());
  const currentItems = digestItems.filter((item) => digestPeriodKey(item) === currentPeriodKey);
  const historyItems = digestItems.filter((item) => {
    const key = digestPeriodKey(item);
    return key && key !== currentPeriodKey;
  });
  const visibleHistoryItems = historyItems.slice(0, visibleCount);
  const historyUnreadCount = historyItems.filter((item) => !item.is_read).length;

  useEffect(() => {
    setVisibleCount(3);
  }, [notifications]);

  return (
    <section className="space-y-5">
      <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
        <div>
          <h2 className="text-lg font-semibold">日刊 / 周刊</h2>
          <p className="text-sm text-muted-foreground">对应小程序日刊详情和往期期刊，已授权后展示个性化 feed 与历史通知。</p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Button size="sm" variant="outline" onClick={onRefreshNotifications}>
            <RefreshCw className="mr-2 h-4 w-4" />
            刷新通知
          </Button>
          <Button size="sm" variant="outline" onClick={onMarkAllRead} disabled={!digestItems.length}>
            <CheckCircle2 className="mr-2 h-4 w-4" />
            全部已读
          </Button>
          <Button size="sm" variant="outline" onClick={onReload}>
            重新加载
          </Button>
        </div>
      </div>
      {error ? <ErrorState message={error} /> : null}
      {feed ? (
        <div className="rounded-md border p-4">
          <div className="flex flex-wrap items-center gap-2">
            <Badge>{feed.mode || "digest"}</Badge>
            <span className="text-xs text-muted-foreground">{formatDateTime(feed.created_at)}</span>
          </div>
          <h3 className="mt-3 text-lg font-semibold">{feed.title || "当前期刊"}</h3>
          <p className="mt-2 text-sm leading-6 text-muted-foreground">{feed.summary || feed.fallback_message || "暂无期刊摘要"}</p>
          <div className="mt-4 flex gap-2">
            <Button asChild size="sm">
              <Link href={`/research/digests/${feed.id}`}>查看期刊</Link>
            </Button>
          </div>
        </div>
      ) : null}

      {currentItems.length ? (
        <div className="rounded-md border p-4">
          <div className="flex items-center justify-between gap-3">
            <div>
              <h3 className="font-semibold">当前周期</h3>
              <p className="mt-1 text-sm text-muted-foreground">当前日刊/周刊已在上方显示，历史区会自动排除当前周期。</p>
            </div>
            <Badge variant="outline">{currentItems.length} 条</Badge>
          </div>
        </div>
      ) : null}

      {historyItems.length ? (
        <div className="flex items-center justify-between gap-3 rounded-md border p-3 text-sm">
          <span className="text-muted-foreground">往期期刊 {historyItems.length} 条 · 未读 {historyUnreadCount}</span>
          {historyUnreadCount > 0 ? (
            <Button size="sm" variant="outline" onClick={onMarkAllRead}>
              <CheckCircle2 className="mr-2 h-4 w-4" />
              全部已读
            </Button>
          ) : null}
        </div>
      ) : null}

      <div className="space-y-3">
        {visibleHistoryItems.map((item) => (
          <div key={item.id} className="rounded-md border p-4">
            <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
              <div>
                <div className="flex flex-wrap items-center gap-2">
                  <Badge variant={item.is_read ? "outline" : "secondary"}>{item.is_read ? "已读" : "未读"}</Badge>
                  <span className="text-xs text-muted-foreground">{formatDateTime(item.created_at)}</span>
                  {item.payload?.mode ? <span className="text-xs text-muted-foreground">{item.payload.mode}</span> : null}
                  {item.payload?.anchor ? <span className="text-xs text-muted-foreground">{String(item.payload.anchor).slice(0, 10)}</span> : null}
                </div>
                <h3 className="mt-2 font-semibold">{item.title}</h3>
                <p className="mt-1 text-sm text-muted-foreground">{item.body}</p>
              </div>
              <div className="flex shrink-0 gap-2">
                {!item.is_read ? (
                  <Button size="sm" variant="outline" onClick={() => onMarkRead(item.id)}>
                    标为已读
                  </Button>
                ) : null}
                <Button asChild size="sm" variant="outline">
                  <Link href={`/research/digests/${item.id}`}>打开</Link>
                </Button>
              </div>
            </div>
          </div>
        ))}
      </div>

      {historyItems.length > visibleHistoryItems.length ? (
        <Button className="w-full" variant="outline" onClick={() => setVisibleCount((count) => count + 3)}>
          查看更多往期期刊
        </Button>
      ) : null}

      {!feed && !digestItems.length && publicItems.length ? (
        <div className="space-y-3">
          <div>
            <h3 className="font-semibold">公开精选</h3>
            <p className="mt-1 text-sm text-muted-foreground">未授权时先浏览公开内容；保存研报 token 后可回看个性化往期。</p>
          </div>
          {publicItems.slice(0, 4).map((item) => (
            <ReportRow key={item.id} item={item} />
          ))}
        </div>
      ) : null}

      {!feed && !digestItems.length && !publicItems.length ? (
        <div className="space-y-3">
          <EmptyState title="需要研报账号授权" description="保存研报 token 后，可查看当前日刊/周刊和往期期刊历史。" />
          <Button size="sm" variant="outline" onClick={onGoPreferences}>
            <Settings2 className="mr-2 h-4 w-4" />
            去设置兴趣
          </Button>
        </div>
      ) : null}

      {feed && !historyItems.length ? (
        <div className="space-y-3">
          <EmptyState title="暂无往期期刊" description="这里仅保留过去周期的期刊；当前周期请查看上方当前期刊。" />
          <Button size="sm" variant="outline" onClick={onGoPreferences}>
            <Settings2 className="mr-2 h-4 w-4" />
            去设置兴趣
          </Button>
        </div>
      ) : null}
    </section>
  );
}
