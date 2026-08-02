"use client";

import { Download, FilePlus2, Plus } from "lucide-react";
import { FormEvent, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import { toast } from "sonner";

import { DashboardPage, EmptyPanel, MetricCard, Panel, SectionTitle, StatusDot } from "@/components/agentos/dashboard-ui";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Textarea } from "@/components/ui/textarea";
import { agentOSApi, agentOSDownloadUrl, type Hypothesis, type ResearchDocument, type ResearchLibraryItem } from "@/lib/api/agentos";
import { useUrlTab } from "@/hooks/use-url-tab";
import { useI18n } from "@/lib/i18n/provider";

type Version = { id: string; version: number; locale: string; status: string; content_sha256?: string; size_bytes?: number; download_url: string };

export default function ResearchPage() {
  const params = useSearchParams();
  const { locale, formatNumber } = useI18n();
  const [tab, setTab] = useUrlTab(["thesis", "record", "consensus", "library"], "thesis", { hypotheses: "thesis", judgments: "record", reports: "library" });
  const [hypotheses, setHypotheses] = useState<Hypothesis[]>([]);
  const [consensus, setConsensus] = useState<Array<Record<string, unknown>>>([]);
  const [documents, setDocuments] = useState<ResearchDocument[]>([]);
  const [library, setLibrary] = useState<ResearchLibraryItem[]>([]);
  const [versions, setVersions] = useState<Record<string, Version[]>>({});
  const [hypothesisOpen, setHypothesisOpen] = useState(false);
  const [reportOpen, setReportOpen] = useState(params.get("report") === "1");
  const load = async () => {
    const [hypothesisData, consensusData, documentData, libraryData] = await Promise.all([agentOSApi.hypotheses(), agentOSApi.consensus(), agentOSApi.documents(), agentOSApi.researchLibrary({ limit: 100 })]);
    setHypotheses(hypothesisData.items); setConsensus(consensusData.items); setDocuments(documentData.items); setLibrary(libraryData.items);
    const versionPairs = await Promise.all(documentData.items.map(async (document) => [document.id, (await agentOSApi.documentVersions(document.id)).items] as const));
    setVersions(Object.fromEntries(versionPairs));
  };
  useEffect(() => {
    let cancelled = false;
    void (async () => {
      const [hypothesisData, consensusData, documentData, libraryData] = await Promise.all([agentOSApi.hypotheses(), agentOSApi.consensus(), agentOSApi.documents(), agentOSApi.researchLibrary({ limit: 100 })]);
      const versionPairs = await Promise.all(documentData.items.map(async (document) => [document.id, (await agentOSApi.documentVersions(document.id)).items] as const));
      if (cancelled) return;
      setHypotheses(hypothesisData.items);
      setConsensus(consensusData.items);
      setDocuments(documentData.items);
      setLibrary(libraryData.items);
      setVersions(Object.fromEntries(versionPairs));
    })().catch(() => undefined);
    return () => { cancelled = true; };
  }, []);
  const active = hypotheses.filter((item) => item.status === "active" || item.status === "draft");
  const completed = hypotheses.filter((item) => ["confirmed", "invalidated", "archived"].includes(item.status));
  const conflicts = consensus.filter((item) => item.status === "challenged" || item.status === "conflict");
  return <DashboardPage>
    <div className="flex justify-end gap-2"><Button variant="outline" onClick={() => setHypothesisOpen(true)}><Plus />{locale === "zh" ? "新研究假设" : "New hypothesis"}</Button><Button onClick={() => setReportOpen(true)}><FilePlus2 />{locale === "zh" ? "生成双语报告" : "Generate bilingual report"}</Button></div>
    <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4"><MetricCard label="ACTIVE HYPOTHESES" value={formatNumber(active.length)} note={locale === "zh" ? "正在验证的结构化判断" : "Structured judgments under review"} color="text-agent-blue" /><MetricCard label="COMPLETED JUDGMENTS" value={formatNumber(completed.length)} note={locale === "zh" ? "成立、失效或归档" : "Confirmed, invalidated, or archived"} color="text-agent-mint" /><MetricCard label="CONSENSUS CONFLICTS" value={formatNumber(conflicts.length)} note={locale === "zh" ? "卖方证据与我的假设冲突" : "Sell-side evidence conflicts"} color="text-agent-up" /><MetricCard label="REPORT VERSIONS" value={formatNumber(Object.values(versions).flat().length)} note={`${documents.length} ${locale === "zh" ? "份研究文档" : "research documents"}`} color="text-agent-amber" /></div>
    <Tabs value={tab} onValueChange={setTab} className="flex flex-col gap-3"><TabsList className="h-auto w-fit max-w-full overflow-x-auto border border-agent-border bg-agent-chrome p-1 lg:hidden"><TabsTrigger value="thesis">{locale === "zh" ? "假设检验" : "Hypothesis Tests"}</TabsTrigger><TabsTrigger value="record">{locale === "zh" ? "我的判断记录" : "Judgment Record"}</TabsTrigger><TabsTrigger value="consensus">{locale === "zh" ? "共识与分歧" : "Consensus"}</TabsTrigger><TabsTrigger value="library">{locale === "zh" ? "全部研报" : "All Reports"}</TabsTrigger></TabsList>
      <TabsContent value="thesis" className="mt-0"><HypothesisList items={active} locale={locale} emptyTitle={locale === "zh" ? "没有待验证假设" : "No active hypotheses"} /></TabsContent>
      <TabsContent value="record" className="mt-0"><HypothesisList items={completed} locale={locale} emptyTitle={locale === "zh" ? "没有已完成判断" : "No completed judgments"} /></TabsContent>
      <TabsContent value="consensus" className="mt-0"><Panel><SectionTitle title={locale === "zh" ? "卖方共识 vs 我的持仓假设" : "Sell-side Consensus vs My Hypotheses"} en="TRACEABLE CLAIMS ONLY" />{consensus.length ? <div className="divide-y divide-agent-border">{consensus.map((item) => <div key={String(item.id)} className="grid gap-3 py-4 md:grid-cols-[160px_1fr_120px]"><div><p className="text-xs text-agent-text">{String(item.subject_code)}</p><p className="mt-1 font-data text-[9px] text-agent-dim">{String(item.as_of)}</p></div><div><p className="text-xs leading-6 text-agent-muted">{JSON.stringify(item.summary)}</p><p className="mt-2 font-data text-[9px] text-agent-dim">{Array.isArray(item.claims) ? item.claims.length : 0} independent claims</p></div><span className="font-data text-[10px] text-agent-amber">{String(item.status)}</span></div>)}</div> : <EmptyPanel title={locale === "zh" ? "没有达到门槛的共识快照" : "No consensus snapshot meets the threshold"} detail={locale === "zh" ? "每条主张必须能定位到研报及页码/章节；少于两份独立来源时只展示单篇证据，不汇总为共识。" : "Every claim must cite a report and page/section. Fewer than two independent sources are not aggregated as consensus."} />}</Panel></TabsContent>
      <TabsContent value="library" className="mt-0 grid gap-3 xl:grid-cols-[1.15fr_.85fr]"><ReportLibrary items={library} locale={locale} /><Reports documents={documents} versions={versions} locale={locale} open={() => setReportOpen(true)} /></TabsContent>
    </Tabs>
    <HypothesisDialog open={hypothesisOpen} setOpen={setHypothesisOpen} reload={load} locale={locale} />
    <ReportDialog open={reportOpen} setOpen={setReportOpen} reload={load} locale={locale} />
  </DashboardPage>;
}

function HypothesisList({ items, locale, emptyTitle }: { items: Hypothesis[]; locale: string; emptyTitle: string }) {
  return <Panel><SectionTitle title={locale === "zh" ? "可证伪研究判断" : "Falsifiable Research Judgments"} en="THESIS / COUNTER-EVIDENCE" />{items.length ? <div className="divide-y divide-agent-border">{items.map((item) => <article key={item.id} className="grid gap-3 py-4 lg:grid-cols-[150px_1fr_1fr_90px]"><div><div className="flex items-center gap-2"><StatusDot status={item.status} /><span className="font-data text-[10px] uppercase text-agent-muted">{item.status}</span></div><p className="mt-2 font-data text-[9px] text-agent-dim">v{item.current_version} · {item.review_date || "NO REVIEW"}</p></div><div><h3 className="text-sm text-agent-text">{item.title}</h3><p className="mt-2 text-xs leading-6 text-agent-muted">{item.thesis}</p></div><div className="rounded-md border border-agent-border bg-agent-raised p-3"><p className="font-data text-[8px] uppercase text-agent-up">FALSIFICATION</p><p className="mt-2 text-[10px] leading-5 text-agent-muted">{item.falsification}</p></div><div className="text-right font-data text-[9px] text-agent-dim">{item.evidence.length}<br/>EVIDENCE</div></article>)}</div> : <EmptyPanel title={emptyTitle} detail={locale === "zh" ? "研究假设与旧 Today/Thesis 表无关，使用新的不可变修订模型。" : "Research hypotheses use the new immutable revision model, not the retired Today/Thesis tables."} />}</Panel>;
}

function Reports({ documents, versions, locale, open }: { documents: ResearchDocument[]; versions: Record<string, Version[]>; locale: string; open: () => void }) {
  return <Panel><SectionTitle title={locale === "zh" ? "版本化研究报告" : "Versioned Research Reports"} en="ZH-CN / EN-US PDF" action={<Button size="sm" onClick={open}><FilePlus2 />{locale === "zh" ? "新报告" : "New report"}</Button>} />{documents.length ? <div className="divide-y divide-agent-border">{documents.map((document) => <div key={document.id} className="grid gap-3 py-4 lg:grid-cols-[1fr_100px_1.2fr]"><div><p className="text-sm text-agent-text">{document.title}</p><p className="mt-1 font-data text-[9px] text-agent-dim">{document.document_type} · v{document.current_version} · {document.updated_at.slice(0, 10)}</p></div><span className="font-data text-[10px] uppercase text-agent-mint">{document.status}</span><div className="flex flex-wrap justify-end gap-2">{(versions[document.id] || []).map((version) => <a key={version.id} href={agentOSDownloadUrl(version.download_url)} className="inline-flex items-center gap-2 rounded border border-agent-border px-3 py-2 font-data text-[9px] text-agent-muted hover:border-agent-mint hover:text-agent-mint"><Download />v{version.version} · {version.locale} · {version.size_bytes ? `${Math.round(version.size_bytes / 1024)}KB` : "PDF"}</a>)}</div></div>)}</div> : <EmptyPanel title={locale === "zh" ? "尚无报告版本" : "No report versions"} detail={locale === "zh" ? "每次生成会基于同一事实快照同时输出中文和英文 PDF。" : "Each generation produces Chinese and English PDFs from the same fact snapshot."} action={locale === "zh" ? "生成第一份报告" : "Generate first report"} onAction={open} />}</Panel>;
}

function ReportLibrary({ items, locale }: { items: ResearchLibraryItem[]; locale: string }) {
  return <Panel><SectionTitle title={locale === "zh" ? "全部研报" : "All Research Reports"} en="REPORT-KB · DEDUPLICATED" />{items.length ? <div className="divide-y divide-agent-border">{items.map((item, index) => <article key={item.report_id || item.id || index} className="py-4"><div className="flex gap-3"><span className="rounded bg-agent-mint/10 px-2 py-1 font-data text-[8px] text-agent-mint">{item.broker || "SOURCE"}</span><span className="ml-auto font-data text-[9px] text-agent-dim">{item.report_date || "—"}</span></div><h3 className="mt-3 text-sm text-agent-text">{item.display_title || item.title || (locale === "zh" ? "未命名研报" : "Untitled report")}</h3><p className="mt-2 line-clamp-3 text-xs leading-6 text-agent-muted">{item.summary || item.excerpt || (locale === "zh" ? "等待 report-kb 摘要。" : "Awaiting report-kb summary.")}</p><p className="mt-2 font-data text-[9px] text-agent-dim">{item.sections_count || 0} sections · {(item.company_names || []).join(" / ")}</p></article>)}</div> : <EmptyPanel title={locale === "zh" ? "研报库暂不可用" : "Report library unavailable"} detail={locale === "zh" ? "Research 通过内部网关读取 NAS + report-kb 去重库，不与 Structured Data 合并。" : "Research reads the deduplicated NAS + report-kb library through the internal gateway."} />}</Panel>;
}

function HypothesisDialog({ open, setOpen, reload, locale }: { open: boolean; setOpen: (value: boolean) => void; reload: () => Promise<void>; locale: string }) {
  const [form, setForm] = useState({ title: "", thesis: "", falsification: "", review_date: "" }); const [saving, setSaving] = useState(false);
  const submit = async (event: FormEvent) => { event.preventDefault(); setSaving(true); try { await agentOSApi.createHypothesis({ ...form, review_date: form.review_date || null, evidence: [], outcome: {}, status: "active", created_by: "user" }); await reload(); setOpen(false); toast.success(locale === "zh" ? "研究假设已创建" : "Hypothesis created"); } catch (error) { toast.error(error instanceof Error ? error.message : "Save failed"); } finally { setSaving(false); } };
  return <Dialog open={open} onOpenChange={setOpen}><DialogContent><DialogHeader><DialogTitle>{locale === "zh" ? "新研究假设" : "New research hypothesis"}</DialogTitle><DialogDescription>{locale === "zh" ? "判断和证伪条件必须同时记录；后续修改会创建新版本。" : "Record the thesis and falsifier together. Later edits create new versions."}</DialogDescription></DialogHeader><form onSubmit={submit} className="flex flex-col gap-4"><div><Label htmlFor="hypothesis-title">{locale === "zh" ? "标题" : "Title"}</Label><Input id="hypothesis-title" className="mt-2" value={form.title} onChange={(event) => setForm({ ...form, title: event.target.value })} required /></div><div><Label htmlFor="hypothesis-thesis">{locale === "zh" ? "判断" : "Thesis"}</Label><Textarea id="hypothesis-thesis" className="mt-2" value={form.thesis} onChange={(event) => setForm({ ...form, thesis: event.target.value })} required /></div><div><Label htmlFor="hypothesis-falsification">{locale === "zh" ? "什么情况说明它错了" : "What would falsify it"}</Label><Textarea id="hypothesis-falsification" className="mt-2" value={form.falsification} onChange={(event) => setForm({ ...form, falsification: event.target.value })} required /></div><DialogFooter><Button type="submit" disabled={saving}>{locale === "zh" ? "创建假设" : "Create hypothesis"}</Button></DialogFooter></form></DialogContent></Dialog>;
}

function ReportDialog({ open, setOpen, reload, locale }: { open: boolean; setOpen: (value: boolean) => void; reload: () => Promise<void>; locale: string }) {
  const [form, setForm] = useState({ title: "", citation: "", summary: "" }); const [saving, setSaving] = useState(false);
  const submit = async (event: FormEvent) => { event.preventDefault(); setSaving(true); try { const asOf = new Date().toISOString().slice(0, 10); const document = await agentOSApi.createDocument({ title: form.title, document_type: "research_note" }); await agentOSApi.generateBilingualDocument(document.id, { summary: form.summary, structured: { title: form.title, report_type: "research_note" }, source_snapshot: { as_of: asOf, generated_at: new Date().toISOString(), source: "agentos_immutable_fact_snapshot", citations: [{ label: form.citation, as_of: asOf }] } }); await reload(); setOpen(false); toast.success(locale === "zh" ? "同一事实快照的中英文 PDF 已生成" : "Chinese and English PDFs generated from one fact snapshot"); } catch (error) { toast.error(error instanceof Error ? error.message : "Generation failed"); } finally { setSaving(false); } };
  return <Dialog open={open} onOpenChange={setOpen}><DialogContent><DialogHeader><DialogTitle>{locale === "zh" ? "生成双语研究报告" : "Generate bilingual research report"}</DialogTitle><DialogDescription>{locale === "zh" ? "后台从同一个不可变事实快照生成中文和英文 PDF；无需分别粘贴两份正文。" : "The backend creates both PDFs from one immutable fact snapshot; separate manual bodies are not required."}</DialogDescription></DialogHeader><form onSubmit={submit} className="flex flex-col gap-4"><div><Label htmlFor="report-title">{locale === "zh" ? "报告标题" : "Report title"}</Label><Input id="report-title" className="mt-2" value={form.title} onChange={(event) => setForm({ ...form, title: event.target.value })} required /></div><div><Label htmlFor="report-citation">{locale === "zh" ? "资料引用（报告 ID、标题或链接）" : "Citation (report ID, title, or link)"}</Label><Input id="report-citation" className="mt-2" value={form.citation} onChange={(event) => setForm({ ...form, citation: event.target.value })} required /></div><div><Label htmlFor="report-summary">{locale === "zh" ? "事实摘要（可选）" : "Fact summary (optional)"}</Label><Textarea id="report-summary" className="mt-2 min-h-32" value={form.summary} onChange={(event) => setForm({ ...form, summary: event.target.value })} /></div><DialogFooter><Button type="submit" disabled={saving}>{saving ? (locale === "zh" ? "后台生成中…" : "Generating…") : (locale === "zh" ? "生成双语版本" : "Generate bilingual version")}</Button></DialogFooter></form></DialogContent></Dialog>;
}
