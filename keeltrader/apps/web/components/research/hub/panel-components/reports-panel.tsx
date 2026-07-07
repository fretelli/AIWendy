"use client";

import { useEffect, useRef, useState } from "react";
import { Loader2, Pause, Play, RefreshCw, SkipBack, SkipForward, Square, Volume2 } from "lucide-react";

import { Button } from "@/components/ui/button";
import {
  createResearchFileObjectUrl,
  getReportBriefingStatus,
  synthesizeReportBriefing,
  trackClientEvent,
  type RecommendationResponse,
  type ReportBriefingState,
  type ReportCardItem,
  type ReportFreshness,
} from "@/lib/research-api";

import { formatNumber } from "../formatters";
import { EmptyState, ErrorState } from "../states";
import { queueItemFromReport, ReportRow, type BriefingQueueItem } from "./report-row";

export function ReportsPanel({
  data,
  freshness,
  mode,
  loading,
  error,
  onReload,
  onModeChange,
}: {
  data: RecommendationResponse | null;
  freshness: ReportFreshness | null;
  mode: "public" | "personalized";
  loading: boolean;
  error: string;
  onReload: () => void;
  onModeChange: (mode: "public" | "personalized") => void;
}) {
  const audioRef = useRef<HTMLAudioElement>(null);
  const [audioQueue, setAudioQueue] = useState<BriefingQueueItem[]>([]);
  const [audioIndex, setAudioIndex] = useState(-1);
  const [audioUrl, setAudioUrl] = useState("");
  const [audioLoadingId, setAudioLoadingId] = useState("");
  const [audioStatus, setAudioStatus] = useState("");
  const [audioPlaying, setAudioPlaying] = useState(false);
  const reports = data?.items || [];
  const currentAudio = audioIndex >= 0 ? audioQueue[audioIndex] : null;

  useEffect(() => () => {
    if (audioUrl) URL.revokeObjectURL(audioUrl);
  }, [audioUrl]);

  function wait(ms: number) {
    return new Promise((resolve) => setTimeout(resolve, ms));
  }

  function readyBriefing(state: ReportBriefingState | null | undefined) {
    if (state?.status === "ready" && state.version) return state as ReportBriefingState & { version: string };
    return null;
  }

  async function resolveBriefing(reportId: string): Promise<ReportBriefingState & { version: string }> {
    let state: ReportBriefingState | null = await getReportBriefingStatus(reportId).catch(() => null);
    const currentReady = readyBriefing(state);
    if (currentReady) return currentReady;
    state = await synthesizeReportBriefing(reportId);
    const synthesizedReady = readyBriefing(state);
    if (synthesizedReady) return synthesizedReady;
    for (let attempt = 0; attempt < 6; attempt += 1) {
      const delaySeconds = Math.max(2, Math.min(8, Number(state?.retry_after_seconds || 3)));
      setAudioStatus(state?.message || "语音摘要生成中");
      await wait(delaySeconds * 1000);
      state = await getReportBriefingStatus(reportId).catch(() => state);
      const polledReady = readyBriefing(state);
      if (polledReady) return polledReady;
    }
    throw new Error(state?.message || "语音摘要仍在生成中，请稍后再试");
  }

  async function playQueueAt(nextQueue: BriefingQueueItem[], nextIndex: number) {
    const item = nextQueue[nextIndex];
    if (!item) return;
    setAudioQueue(nextQueue);
    setAudioIndex(nextIndex);
    setAudioLoadingId(item.id);
    setAudioStatus("准备语音摘要");
    try {
      const state = await resolveBriefing(item.id);
      const result = await createResearchFileObjectUrl(
        `/speech/report-briefing/${encodeURIComponent(item.id)}/audio?v=${encodeURIComponent(state.version)}`,
        state.file_name || `report-${item.id}-${state.version}.mp3`
      );
      setAudioUrl((previous) => {
        if (previous) URL.revokeObjectURL(previous);
        return result.objectUrl;
      });
      setAudioStatus("摘要播放中");
      trackClientEvent({
        event_name: "web_briefing_audio_play_started",
        page_path: "/research?tab=reports",
        report_id: item.id,
        status: "success",
        metadata: { queue_mode: nextQueue.length > 1, queue_index: nextIndex },
      }).catch(() => undefined);
      setTimeout(() => {
        const element = audioRef.current;
        if (!element) return;
        element.src = result.objectUrl;
        element.play().then(() => setAudioPlaying(true)).catch((error) => {
          setAudioStatus(error instanceof Error ? error.message : "浏览器阻止自动播放，请手动点击播放");
          setAudioPlaying(false);
        });
      }, 0);
    } catch (nextError) {
      setAudioStatus(nextError instanceof Error ? nextError.message : "语音摘要播放失败");
      setAudioPlaying(false);
      trackClientEvent({
        event_name: "web_briefing_audio_play_failed",
        page_path: "/research?tab=reports",
        report_id: item.id,
        status: "error",
        message: nextError instanceof Error ? nextError.message : "语音摘要播放失败",
        metadata: { queue_mode: nextQueue.length > 1, queue_index: nextIndex },
      }).catch(() => undefined);
    } finally {
      setAudioLoadingId("");
    }
  }

  function playReport(item: ReportCardItem) {
    const queue = reports.map(queueItemFromReport);
    const startIndex = Math.max(0, queue.findIndex((entry) => entry.id === item.id));
    void playQueueAt(queue.length ? queue : [queueItemFromReport(item)], startIndex);
  }

  function playAll() {
    const queue = reports.map(queueItemFromReport);
    if (!queue.length) {
      setAudioStatus("当前没有可播放的研报");
      return;
    }
    void playQueueAt(queue, 0);
  }

  function playOffset(offset: number) {
    if (!audioQueue.length) return;
    const nextIndex = audioIndex + offset;
    if (nextIndex < 0 || nextIndex >= audioQueue.length) return;
    void playQueueAt(audioQueue, nextIndex);
  }

  function togglePlayback() {
    const element = audioRef.current;
    if (!element) return;
    if (audioPlaying) {
      element.pause();
      setAudioPlaying(false);
      setAudioStatus("已暂停");
      return;
    }
    element.play().then(() => {
      setAudioPlaying(true);
      setAudioStatus("摘要播放中");
    }).catch((error) => setAudioStatus(error instanceof Error ? error.message : "播放失败"));
  }

  function stopPlayback() {
    const element = audioRef.current;
    if (element) {
      element.pause();
      element.removeAttribute("src");
      element.load();
    }
    if (audioUrl) URL.revokeObjectURL(audioUrl);
    setAudioUrl("");
    setAudioPlaying(false);
    setAudioIndex(-1);
    setAudioStatus("");
  }

  function handleAudioEnded() {
    setAudioPlaying(false);
    if (audioIndex >= 0 && audioIndex < audioQueue.length - 1) {
      setAudioStatus("正在播放下一条");
      void playQueueAt(audioQueue, audioIndex + 1);
      return;
    }
    setAudioStatus(audioQueue.length > 1 ? "连续收听完成" : "播放完成，可再次收听");
  }

  return (
    <section className="space-y-4">
      <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
        <div>
          <h2 className="text-lg font-semibold">推荐研报</h2>
          <p className="text-sm text-muted-foreground">对应小程序首页推荐研报，可切换公共推荐和授权后的个性化推荐。</p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Button size="sm" variant={mode === "public" ? "secondary" : "outline"} onClick={() => onModeChange("public")}>
            公共推荐
          </Button>
          <Button size="sm" variant={mode === "personalized" ? "secondary" : "outline"} onClick={() => onModeChange("personalized")}>
            个性化
          </Button>
          <Button size="sm" variant="outline" onClick={onReload} disabled={loading}>
            {loading ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <RefreshCw className="mr-2 h-4 w-4" />}
            刷新
          </Button>
          <Button size="sm" variant="outline" onClick={playAll} disabled={!reports.length || !!audioLoadingId}>
            {audioLoadingId ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Volume2 className="mr-2 h-4 w-4" />}
            连续收听
          </Button>
        </div>
      </div>
      {currentAudio || audioStatus ? (
        <div className="rounded-md border p-4">
          <audio ref={audioRef} className="hidden" onEnded={handleAudioEnded} onPause={() => setAudioPlaying(false)} onPlay={() => setAudioPlaying(true)} />
          <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
            <div className="min-w-0">
              <div className="text-sm font-semibold">{currentAudio?.title || "研报音频摘要"}</div>
              <div className="mt-1 text-xs text-muted-foreground">
                {currentAudio?.broker || "今日发现"} {audioQueue.length > 1 && audioIndex >= 0 ? `· ${audioIndex + 1}/${audioQueue.length}` : ""}
              </div>
              {audioStatus ? <div className="mt-2 text-sm text-muted-foreground">{audioStatus}</div> : null}
            </div>
            <div className="flex flex-wrap gap-2">
              <Button size="sm" variant="outline" onClick={() => playOffset(-1)} disabled={audioIndex <= 0 || !!audioLoadingId}>
                <SkipBack className="mr-2 h-4 w-4" />
                上一条
              </Button>
              <Button size="sm" variant="outline" onClick={togglePlayback} disabled={!audioUrl || !!audioLoadingId}>
                {audioPlaying ? <Pause className="mr-2 h-4 w-4" /> : <Play className="mr-2 h-4 w-4" />}
                {audioPlaying ? "暂停" : "播放"}
              </Button>
              <Button size="sm" variant="outline" onClick={() => playOffset(1)} disabled={audioIndex < 0 || audioIndex >= audioQueue.length - 1 || !!audioLoadingId}>
                <SkipForward className="mr-2 h-4 w-4" />
                下一条
              </Button>
              <Button size="sm" variant="outline" onClick={stopPlayback}>
                <Square className="mr-2 h-4 w-4" />
                停止
              </Button>
            </div>
          </div>
        </div>
      ) : null}
      {freshness ? (
        <div className="grid gap-3 md:grid-cols-4">
          <div className="rounded-md border p-3">
            <div className="text-xs text-muted-foreground">最新研报日</div>
            <div className="mt-1 font-semibold">{freshness.latest_report_date || "-"}</div>
          </div>
          <div className="rounded-md border p-3">
            <div className="text-xs text-muted-foreground">今日研报</div>
            <div className="mt-1 font-semibold">{formatNumber(freshness.today_report_count)}</div>
          </div>
          <div className="rounded-md border p-3">
            <div className="text-xs text-muted-foreground">本周研报</div>
            <div className="mt-1 font-semibold">{formatNumber(freshness.current_week_report_count)}</div>
          </div>
          <div className="rounded-md border p-3">
            <div className="text-xs text-muted-foreground">OCR 待处理</div>
            <div className="mt-1 font-semibold">{formatNumber(freshness.ocr_backlog_count)}</div>
          </div>
        </div>
      ) : null}
      {error ? <ErrorState message={error} onRetry={onReload} /> : null}
      {loading && !data ? <EmptyState title="正在加载推荐研报" description="从 research API 获取最新公共推荐。" /> : null}
      <div className="space-y-3">
        {reports.map((item) => (
          <ReportRow key={item.id} item={item} onPlayBriefing={playReport} audioLoadingId={audioLoadingId} />
        ))}
      </div>
      {data && !data.items.length ? <EmptyState title="暂无推荐" description="当前没有可展示的推荐研报。" /> : null}
    </section>
  );
}
