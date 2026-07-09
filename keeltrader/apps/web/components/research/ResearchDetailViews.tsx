"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useParams, useSearchParams } from "next/navigation";
import { ArrowLeft, CreditCard, ExternalLink, FileText, Loader2, MessageSquare, Share2, Volume2, Wand2 } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  captureOfficialArticleAttribution,
  createBillingOrder,
  downloadResearchFile,
  getReportBriefingStatus,
  getReportDetail,
  getReportNoteState,
  prepareBillingOrderPayment,
  savePendingInviteFromParams,
  synthesizeReportBriefing,
  trackClientEvent,
  triggerReportNote,
  type BillingOrderDetail,
  type ReportBriefingState,
  type ReportDetail,
  type ReportNoteState,
} from "@/lib/research-api";
import { FeedbackDialog } from "./FeedbackDialog";
import { titleFromReport, summaryPoints } from "./detail-formatters";
import { formatDate, formatMoneyFen } from "./hub/formatters";

export function ResearchReportDetailView() {
  const params = useParams<{ id: string }>();
  const searchParams = useSearchParams();
  const [report, setReport] = useState<ReportDetail | null>(null);
  const [noteState, setNoteState] = useState<ReportNoteState | null>(null);
  const [briefing, setBriefing] = useState<ReportBriefingState | null>(null);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState("");
  const [error, setError] = useState("");
  const [actionStatus, setActionStatus] = useState("");
  const [feedbackOpen, setFeedbackOpen] = useState(false);
  const reportId = decodeURIComponent(String(params.id || ""));
  const digestId = searchParams.get("digest_id");
  const points = useMemo(() => (report ? summaryPoints(report) : []), [report]);

  useEffect(() => {
    queueMicrotask(() => {
      setLoading(true);
      setError("");
      const query = new URLSearchParams(window.location.search);
      const attribution = captureOfficialArticleAttribution(query);
      if (attribution) {
        trackClientEvent({
          event_name: "official_article_report_open",
          page_path: `/research/reports/${reportId}`,
          report_id: reportId,
          digest_id: digestId ? Number(digestId) : undefined,
          status: "success",
          metadata: {
            source: attribution.source,
            campaign_key: attribution.campaign_key,
            article_type: attribution.article_type,
            entry: attribution.entry,
          },
        }).catch(() => undefined);
      }
      const pendingInvite = savePendingInviteFromParams(query, "report_share", reportId);
      if (pendingInvite) {
        trackClientEvent({
          event_name: "web_pending_invite_captured",
          page_path: `/research/reports/${reportId}`,
          report_id: reportId,
          digest_id: digestId ? Number(digestId) : undefined,
          status: "success",
          metadata: {
            inviter_user_id: pendingInvite.inviter_user_id || null,
            invite_code: pendingInvite.invite_code || "",
            source_type: pendingInvite.source_type,
            source_id: pendingInvite.source_id,
          },
        }).catch(() => undefined);
      }
      getReportDetail(reportId, digestId)
        .then((data) => {
          setReport(data);
          trackClientEvent({
            event_name: "web_report_detail_opened",
            page_path: `/research/reports/${reportId}`,
            report_id: reportId,
            digest_id: digestId ? Number(digestId) : undefined,
            metadata: { can_view_pdf: data.access?.can_view_pdf, can_view_full_report: data.access?.can_view_full_report },
          }).catch(() => undefined);
        })
        .catch((nextError) => setError(nextError instanceof Error ? nextError.message : "研报详情加载失败"))
        .finally(() => setLoading(false));
      getReportNoteState(reportId).then(setNoteState).catch(() => setNoteState(null));
      getReportBriefingStatus(reportId).then(setBriefing).catch(() => setBriefing(null));
    });
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
      const nextReport = await getReportDetail(reportId, digestId).catch(() => null);
      if (nextReport) setReport(nextReport);
      trackClientEvent({
        event_name: "web_report_pdf_downloaded",
        page_path: `/research/reports/${reportId}`,
        report_id: reportId,
        digest_id: digestId ? Number(digestId) : undefined,
        metadata: { source: report?.access?.can_view_pdf ? "access" : "credit" },
      }).catch(() => undefined);
    } catch (nextError) {
      setError(nextError instanceof Error ? nextError.message : "PDF 下载失败");
    } finally {
      setActionLoading("");
    }
  }

  async function copyShareLink() {
    const url = `${window.location.origin}/research/reports/${encodeURIComponent(reportId)}${digestId ? `?digest_id=${encodeURIComponent(String(digestId))}` : ""}`;
    try {
      await navigator.clipboard.writeText(url);
      setActionStatus("研报链接已复制");
      trackClientEvent({
        event_name: "web_report_link_copied",
        page_path: `/research/reports/${reportId}`,
        report_id: reportId,
        digest_id: digestId ? Number(digestId) : undefined,
      }).catch(() => undefined);
    } catch {
      setActionStatus(url);
    }
  }

  async function createAccessOrder(productCode: string) {
    setActionLoading(`order:${productCode}`);
    setActionStatus("");
    try {
      const order: BillingOrderDetail = await createBillingOrder({
        product_code: productCode,
        target_type: "report",
        target_id: reportId,
      });
      const payment = await prepareBillingOrderPayment(order.id);
      const suffix = payment.already_paid
        ? "订单已支付，权益已生效"
        : payment.configured === false
          ? payment.message || "支付暂未配置，订单已创建"
          : payment.message || "订单已创建，请在小程序内完成微信支付";
      setActionStatus(`${order.title} ${formatMoneyFen(order.amount_fen)}。${suffix}`);
      trackClientEvent({
        event_name: "web_report_access_order_created",
        page_path: `/research/reports/${reportId}`,
        report_id: reportId,
        digest_id: digestId ? Number(digestId) : undefined,
        metadata: { product_code: productCode, order_id: order.id, payment_configured: payment.configured },
      }).catch(() => undefined);
      const nextReport = await getReportDetail(reportId, digestId).catch(() => null);
      if (nextReport) setReport(nextReport);
    } catch (nextError) {
      setError(nextError instanceof Error ? nextError.message : "创建权益订单失败");
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
                <Button size="sm" variant="outline" onClick={copyShareLink}>
                  <Share2 className="mr-2 h-4 w-4" />
                  复制分享链接
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

            {report.access ? (
              <div className="rounded-md border p-5">
                <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
                  <div>
                    <h2 className="font-semibold">阅读与 PDF 权益</h2>
                    <p className="mt-1 text-sm leading-6 text-muted-foreground">
                      {report.access.paywall_message || "会员、PDF 权益或邀请奖励会决定是否可查看完整内容和 PDF 原报告。"}
                    </p>
                    <div className="mt-3 flex flex-wrap gap-2">
                      <Badge variant={report.access.can_view_full_report ? "secondary" : "outline"}>
                        {report.access.can_view_full_report ? "可读全文" : "全文受限"}
                      </Badge>
                      <Badge variant={report.access.can_view_pdf ? "secondary" : "outline"}>
                        {report.access.can_view_pdf ? "可下载 PDF" : "PDF 需权益"}
                      </Badge>
                      <Badge variant="outline">PDF 次数 {report.access.pdf_credit_count || 0}</Badge>
                      {report.access.is_member ? <Badge variant="secondary">会员</Badge> : null}
                    </div>
                  </div>
                  {report.access.membership_product_codes?.length ? (
                    <div className="flex shrink-0 flex-wrap gap-2">
                      {report.access.membership_product_codes.map((code) => (
                        <Button key={code} size="sm" onClick={() => createAccessOrder(code)} disabled={actionLoading === `order:${code}`}>
                          {actionLoading === `order:${code}` ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <CreditCard className="mr-2 h-4 w-4" />}
                          开通 {code}
                        </Button>
                      ))}
                    </div>
                  ) : null}
                </div>
                {actionStatus ? <div className="mt-4 rounded-md bg-muted/50 p-3 text-sm text-muted-foreground">{actionStatus}</div> : null}
              </div>
            ) : null}

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
