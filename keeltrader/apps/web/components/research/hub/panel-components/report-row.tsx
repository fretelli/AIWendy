"use client";

import Link from "next/link";
import { Loader2, Volume2 } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { type ReportCardItem } from "@/lib/research-api";

import { formatDate, reportTitle } from "../formatters";

export type BriefingQueueItem = {
  id: string;
  title: string;
  broker: string;
};

export function queueItemFromReport(item: ReportCardItem): BriefingQueueItem {
  return {
    id: String(item.id),
    title: reportTitle(item),
    broker: item.broker || "今日发现",
  };
}

export function ReportRow({
  item,
  digestId,
  onPlayBriefing,
  audioLoadingId,
}: {
  item: ReportCardItem;
  digestId?: number | string | null;
  onPlayBriefing?: (item: ReportCardItem) => void;
  audioLoadingId?: string;
}) {
  const href = `/research/reports/${encodeURIComponent(item.id)}${digestId ? `?digest_id=${encodeURIComponent(String(digestId))}` : ""}`;
  const audioLoading = audioLoadingId === item.id;

  return (
    <div className="rounded-md border p-4 transition-colors hover:bg-muted/40">
      <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
        <div className="min-w-0 space-y-2">
          <div className="flex flex-wrap items-center gap-2">
            {item.broker ? <Badge variant="secondary">{item.broker}</Badge> : null}
            {item.report_date ? <span className="text-xs text-muted-foreground">{formatDate(item.report_date)}</span> : null}
            {item.ingest_status ? <Badge variant="outline">{item.ingest_status}</Badge> : null}
            {item.has_pdf ? <Badge variant="outline">PDF</Badge> : null}
          </div>
          <Link href={href} className="block text-base font-semibold leading-snug hover:underline">
            {reportTitle(item)}
          </Link>
          <p className="line-clamp-3 text-sm leading-6 text-muted-foreground">
            {item.formal_overview || item.brief || item.summary || item.reason || "暂无摘要"}
          </p>
          <div className="flex flex-wrap gap-2">
            {(item.tags || []).slice(0, 5).map((tag) => (
              <span key={tag} className="rounded bg-muted px-2 py-1 text-xs text-muted-foreground">
                {tag}
              </span>
            ))}
          </div>
        </div>
        <div className="flex shrink-0 flex-wrap gap-2">
          {onPlayBriefing ? (
            <Button size="sm" variant="outline" onClick={() => onPlayBriefing(item)} disabled={audioLoading}>
              {audioLoading ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Volume2 className="mr-2 h-4 w-4" />}
              收听
            </Button>
          ) : null}
          <Button asChild size="sm" variant="outline">
            <Link href={href}>查看详情</Link>
          </Button>
        </div>
      </div>
    </div>
  );
}
