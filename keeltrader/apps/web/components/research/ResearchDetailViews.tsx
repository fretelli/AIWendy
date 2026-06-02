"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useParams, useSearchParams } from "next/navigation";
import { ArrowLeft, ExternalLink, FileText, Loader2, MessageSquare, Send, Volume2, Wand2 } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import {
  downloadResearchFile,
  getDigestDetail,
  getReportBriefingStatus,
  getReportDetail,
  getReportNoteState,
  synthesizeReportBriefing,
  submitFeedback,
  triggerReportNote,
  type DigestDetail,
  type ReportBriefingState,
  type ReportDetail,
  type ReportNoteState,
} from "@/lib/research-api";

function formatDate(value?: string | null) {
  if (!value) return "-";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value.slice(0, 10);
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, "0")}-${String(date.getDate()).padStart(2, "0")}`;
}

function titleFromReport(report: ReportDetail) {
  return report.display_title || report.title?.replace(/\.pdf$/i, "") || "研报详情";
}

function summaryPoints(report: ReportDetail) {
  return report.display_summary_points?.length
    ? report.display_summary_points
    : report.note?.display_summary_points?.length
      ? report.note.display_summary_points
      : report.note?.key_points || [];
}

function FeedbackDialog({
  open,
  onOpenChange,
  reportId,
  digestId,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  reportId?: string;
  digestId?: number | null;
}) {
  const [content, setContent] = useState("");
  const [contact, setContact] = useState("");
  const [status, setStatus] = useState("");
  const [submitting, setSubmitting] = useState(false);

  async function submit() {
    const normalized = content.trim().replace(/\s+/g, " ");
    if (normalized.length < 4) {
      setStatus("请补充更具体的反馈内容");
      return;
    }
    setSubmitting(true);
    setStatus("");
    try {
      const result = await submitFeedback({
        category: "report_access",
        content: normalized,
        contact,
        page_path: reportId ? `/research/reports/${reportId}` : `/research/digests/${digestId || ""}`,
        report_id: reportId || "",
        digest_id: digestId || null,
      });
      setContent("");
      setStatus(`已收到反馈 #${result.id}`);
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "提交失败");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>意见反馈</DialogTitle>
        </DialogHeader>
        <div className="space-y-3">
          <div className="space-y-2">
            <Label>反馈内容</Label>
            <Textarea value={content} onChange={(event) => setContent(event.target.value)} placeholder="请描述打不开、摘要错误或其他问题" />
          </div>
          <div className="space-y-2">
            <Label>联系方式</Label>
            <Input value={contact} onChange={(event) => setContact(event.target.value)} placeholder="可选" />
          </div>
          {status ? <div className="text-sm text-muted-foreground">{status}</div> : null}
        </div>
        <DialogFooter>
          <Button onClick={submit} disabled={submitting}>
            {submitting ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Send className="mr-2 h-4 w-4" />}
            提交
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

export function ResearchReportDetailView() {
  const params = useParams<{ id: string }>();
  const searchParams = useSearchParams();
  const [report, setReport] = useState<ReportDetail | null>(null);
  const [noteState, setNoteState] = useState<ReportNoteState | null>(null);
  const [briefing, setBriefing] = useState<ReportBriefingState | null>(null);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState("");
  const [error, setError] = useState("");
  const [feedbackOpen, setFeedbackOpen] = useState(false);
  const reportId = decodeURIComponent(String(params.id || ""));
  const digestId = searchParams.get("digest_id");
  const points = useMemo(() => (report ? summaryPoints(report) : []), [report]);

  useEffect(() => {
    setLoading(true);
    setError("");
    getReportDetail(reportId, digestId)
      .then(setReport)
      .catch((nextError) => setError(nextError instanceof Error ? nextError.message : "研报详情加载失败"))
      .finally(() => setLoading(false));
    getReportNoteState(reportId).then(setNoteState).catch(() => setNoteState(null));
    getReportBriefingStatus(reportId).then(setBriefing).catch(() => setBriefing(null));
  }, [reportId, digestId]);

  async function generateNote() {
    setActionLoading("note");
    try {
      setNoteState(await triggerReportNote(reportId));
    } catch (nextError) {
      setError(nextError instanceof Error ? nextError.message : "AI 解读生成失败");
    } finally {
      setActionLoading("");
    }
  }

  async function generateBriefing() {
    setActionLoading("briefing");
    try {
      setBriefing(await synthesizeReportBriefing(reportId));
    } catch (nextError) {
      setError(nextError instanceof Error ? nextError.message : "音频摘要生成失败");
    } finally {
      setActionLoading("");
    }
  }

  async function downloadPdf() {
    setActionLoading("pdf");
    try {
      const suffix = digestId ? `?digest_id=${encodeURIComponent(String(digestId))}` : "";
      await downloadResearchFile(`/reports/${encodeURIComponent(reportId)}/pdf${suffix}`, `${reportId}.pdf`);
    } catch (nextError) {
      setError(nextError instanceof Error ? nextError.message : "PDF 下载失败");
    } finally {
      setActionLoading("");
    }
  }

  async function downloadBriefingAudio() {
    if (!briefing?.version) return;
    setActionLoading("audio");
    try {
      await downloadResearchFile(
        `/speech/report-briefing/${encodeURIComponent(reportId)}/audio?v=${encodeURIComponent(briefing.version)}`,
        briefing.file_name || `${reportId}-${briefing.version}.mp3`
      );
    } catch (nextError) {
      setError(nextError instanceof Error ? nextError.message : "音频下载失败");
    } finally {
      setActionLoading("");
    }
  }

  return (
    <div className="h-full overflow-y-auto">
      <div className="mx-auto max-w-5xl space-y-5 p-4 md:p-6">
        <Button asChild variant="outline" size="sm">
          <Link href="/research">
            <ArrowLeft className="mr-2 h-4 w-4" />
            返回研报中心
          </Link>
        </Button>
        {loading ? (
          <div className="flex min-h-72 items-center justify-center">
            <Loader2 className="h-8 w-8 animate-spin" />
          </div>
        ) : null}
        {error ? (
          <div className="rounded-md border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900">{error}</div>
        ) : null}
        {report ? (
          <>
            <div className="rounded-md border p-5">
              <div className="flex flex-wrap items-center gap-2">
                {report.broker ? <Badge variant="secondary">{report.broker}</Badge> : null}
                {report.language ? <Badge variant="outline">{report.language}</Badge> : null}
                {report.ingest_status ? <Badge variant="outline">{report.ingest_status}</Badge> : null}
                <span className="text-xs text-muted-foreground">{formatDate(report.report_date)}</span>
              </div>
              <h1 className="mt-4 text-2xl font-bold leading-tight">{titleFromReport(report)}</h1>
              <p className="mt-3 text-sm leading-6 text-muted-foreground">
                {report.note?.overview || report.summary || report.brief || "暂无摘要"}
              </p>
              <div className="mt-4 flex flex-wrap gap-2">
                {(report.tags || []).map((tag) => (
                  <span key={tag} className="rounded bg-muted px-2 py-1 text-xs text-muted-foreground">
                    {tag}
                  </span>
                ))}
              </div>
              <div className="mt-5 flex flex-wrap gap-2">
                {report.pdf_url || report.source_url ? (
                  <Button asChild size="sm">
                    <a href={report.pdf_url || report.source_url} target="_blank" rel="noreferrer">
                      <FileText className="mr-2 h-4 w-4" />
                      打开 PDF / 来源
                    </a>
                  </Button>
                ) : null}
                <Button size="sm" variant="outline" onClick={downloadPdf} disabled={actionLoading === "pdf"}>
                  {actionLoading === "pdf" ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <FileText className="mr-2 h-4 w-4" />}
                  授权下载 PDF
                </Button>
                {report.source_url ? (
                  <Button asChild size="sm" variant="outline">
                    <a href={report.source_url} target="_blank" rel="noreferrer">
                      <ExternalLink className="mr-2 h-4 w-4" />
                      原始链接
                    </a>
                  </Button>
                ) : null}
                <Button size="sm" variant="outline" onClick={() => setFeedbackOpen(true)}>
                  <MessageSquare className="mr-2 h-4 w-4" />
                  意见反馈
                </Button>
                <Button size="sm" variant="outline" onClick={generateNote} disabled={actionLoading === "note"}>
                  {actionLoading === "note" ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Wand2 className="mr-2 h-4 w-4" />}
                  AI 解读
                </Button>
                <Button size="sm" variant="outline" onClick={generateBriefing} disabled={actionLoading === "briefing"}>
                  {actionLoading === "briefing" ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Volume2 className="mr-2 h-4 w-4" />}
                  音频摘要
                </Button>
              </div>
            </div>

            {noteState ? (
              <div className="rounded-md border p-5">
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <div>
                    <h2 className="font-semibold">AI 解读状态</h2>
                    <p className="mt-1 text-sm text-muted-foreground">{noteState.message || noteState.status}</p>
                  </div>
                  <Badge variant={noteState.status === "ready" ? "secondary" : "outline"}>{noteState.status}</Badge>
                </div>
                {noteState.note?.overview ? (
                  <p className="mt-4 text-sm leading-6 text-muted-foreground">{noteState.note.overview}</p>
                ) : null}
                {noteState.note?.conclusion ? (
                  <p className="mt-3 text-sm leading-6 text-muted-foreground">{noteState.note.conclusion}</p>
                ) : null}
              </div>
            ) : null}

            {briefing ? (
              <div className="rounded-md border p-5">
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <div>
                    <h2 className="font-semibold">音频摘要</h2>
                    <p className="mt-1 text-sm text-muted-foreground">{briefing.message || briefing.status}</p>
                  </div>
                  <Badge variant={briefing.status === "ready" ? "secondary" : "outline"}>{briefing.status}</Badge>
                </div>
                {briefing.text ? (
                  <p className="mt-4 whitespace-pre-wrap text-sm leading-6 text-muted-foreground">{briefing.text}</p>
                ) : null}
                {briefing.audio_url ? (
                  <Button asChild className="mt-4" size="sm" variant="outline">
                    <a href={briefing.audio_url} target="_blank" rel="noreferrer">
                      <Volume2 className="mr-2 h-4 w-4" />
                      打开音频
                    </a>
                  </Button>
                ) : null}
                {briefing.version ? (
                  <Button className="mt-4 ml-2" size="sm" variant="outline" onClick={downloadBriefingAudio} disabled={actionLoading === "audio"}>
                    {actionLoading === "audio" ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Volume2 className="mr-2 h-4 w-4" />}
                    下载音频
                  </Button>
                ) : null}
              </div>
            ) : null}

            {points.length ? (
              <div className="rounded-md border p-5">
                <h2 className="font-semibold">核心要点</h2>
                <ul className="mt-3 space-y-2 text-sm leading-6 text-muted-foreground">
                  {points.map((point, index) => (
                    <li key={`${point}-${index}`} className="rounded bg-muted/50 p-3">
                      {point}
                    </li>
                  ))}
                </ul>
              </div>
            ) : null}

            {report.note?.risks?.length ? (
              <div className="rounded-md border p-5">
                <h2 className="font-semibold">风险提示</h2>
                <ul className="mt-3 space-y-2 text-sm leading-6 text-muted-foreground">
                  {report.note.risks.map((risk, index) => (
                    <li key={`${risk}-${index}`}>{risk}</li>
                  ))}
                </ul>
              </div>
            ) : null}

            {report.sections?.length ? (
              <div className="rounded-md border p-5">
                <h2 className="font-semibold">正文片段</h2>
                <div className="mt-3 space-y-4 text-sm leading-7 text-muted-foreground">
                  {report.sections.slice(0, 8).map((section) => (
                    <p key={section.id}>{section.content}</p>
                  ))}
                </div>
              </div>
            ) : null}
          </>
        ) : null}
      </div>
      <FeedbackDialog open={feedbackOpen} onOpenChange={setFeedbackOpen} reportId={reportId} digestId={digestId ? Number(digestId) : null} />
    </div>
  );
}

export function ResearchDigestDetailView() {
  const params = useParams<{ id: string }>();
  const [digest, setDigest] = useState<DigestDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [feedbackOpen, setFeedbackOpen] = useState(false);
  const digestId = decodeURIComponent(String(params.id || ""));

  useEffect(() => {
    setLoading(true);
    setError("");
    getDigestDetail(digestId)
      .then(setDigest)
      .catch((nextError) => setError(nextError instanceof Error ? nextError.message : "期刊详情加载失败"))
      .finally(() => setLoading(false));
  }, [digestId]);

  return (
    <div className="h-full overflow-y-auto">
      <div className="mx-auto max-w-5xl space-y-5 p-4 md:p-6">
        <Button asChild variant="outline" size="sm">
          <Link href="/research?tab=digests">
            <ArrowLeft className="mr-2 h-4 w-4" />
            返回期刊列表
          </Link>
        </Button>
        {loading ? (
          <div className="flex min-h-72 items-center justify-center">
            <Loader2 className="h-8 w-8 animate-spin" />
          </div>
        ) : null}
        {error ? (
          <div className="rounded-md border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900">
            {error}。期刊详情接口需要研报账号授权，请先在研报中心保存 research token。
          </div>
        ) : null}
        {digest ? (
          <>
            <div className="rounded-md border p-5">
              <div className="flex flex-wrap items-center gap-2">
                <Badge>{digest.mode || "digest"}</Badge>
                <Badge variant="outline">{digest.variant || "personalized"}</Badge>
                <span className="text-xs text-muted-foreground">{formatDate(digest.created_at)}</span>
              </div>
              <h1 className="mt-4 text-2xl font-bold leading-tight">{digest.title}</h1>
              <p className="mt-3 text-sm leading-6 text-muted-foreground">{digest.summary || digest.fallback_message || "暂无摘要"}</p>
              <Button className="mt-5" size="sm" variant="outline" onClick={() => setFeedbackOpen(true)}>
                <MessageSquare className="mr-2 h-4 w-4" />
                意见反馈
              </Button>
            </div>
            {digest.body ? (
              <div className="rounded-md border p-5">
                <h2 className="font-semibold">期刊正文</h2>
                <div className="mt-3 whitespace-pre-wrap text-sm leading-7 text-muted-foreground">{digest.body}</div>
              </div>
            ) : null}
            <div className="space-y-3">
              {digest.items.map((item) => (
                <div key={item.id} className="rounded-md border p-4">
                  <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
                    <div>
                      <div className="flex flex-wrap items-center gap-2">
                        {item.broker ? <Badge variant="secondary">{item.broker}</Badge> : null}
                        <span className="text-xs text-muted-foreground">{formatDate(item.report_date)}</span>
                      </div>
                      <Link href={`/research/reports/${encodeURIComponent(item.id)}?digest_id=${digest.id}`} className="mt-2 block font-semibold hover:underline">
                        {item.display_title || item.title}
                      </Link>
                      <p className="mt-2 line-clamp-3 text-sm leading-6 text-muted-foreground">{item.formal_overview || item.brief || item.summary || "暂无摘要"}</p>
                    </div>
                    <Button asChild size="sm" variant="outline">
                      <Link href={`/research/reports/${encodeURIComponent(item.id)}?digest_id=${digest.id}`}>查看研报</Link>
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          </>
        ) : null}
      </div>
      <FeedbackDialog open={feedbackOpen} onOpenChange={setFeedbackOpen} digestId={digest ? digest.id : Number(digestId)} />
    </div>
  );
}
