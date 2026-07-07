"use client";

import { useState } from "react";
import { Loader2, Send } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { submitFeedback } from "@/lib/research-api";

export function FeedbackPanel() {
  const [category, setCategory] = useState("feature");
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
        category,
        content: normalized,
        contact,
        page_path: "/research?tab=feedback",
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
    <section className="space-y-5">
      <div>
        <h2 className="text-lg font-semibold">意见反馈</h2>
        <p className="text-sm text-muted-foreground">对应小程序意见反馈，提交后进入 research 后台反馈管理。</p>
      </div>
      <div className="space-y-4 rounded-md border p-4">
        <div className="space-y-2">
          <Label>反馈类型</Label>
          <select className="w-full rounded-md border bg-background px-3 py-2 text-sm" value={category} onChange={(event) => setCategory(event.target.value)}>
            <option value="recommendation">内容推荐不准</option>
            <option value="report_access">研报打不开</option>
            <option value="summary_audio">音频/摘要问题</option>
            <option value="feature">功能建议</option>
            <option value="other">其他</option>
          </select>
        </div>
        <div className="space-y-2">
          <Label>反馈内容</Label>
          <Textarea value={content} onChange={(event) => setContent(event.target.value)} placeholder="请描述问题、期待的功能或上下文" />
        </div>
        <div className="space-y-2">
          <Label>联系方式</Label>
          <Input value={contact} onChange={(event) => setContact(event.target.value)} placeholder="可选" />
        </div>
        <div className="flex items-center gap-3">
          <Button onClick={submit} disabled={submitting}>
            {submitting ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Send className="mr-2 h-4 w-4" />}
            提交反馈
          </Button>
          {status ? <span className="text-sm text-muted-foreground">{status}</span> : null}
        </div>
      </div>
    </section>
  );
}
