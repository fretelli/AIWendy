"use client";

import { useState } from "react";
import { Loader2, Send } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { submitFeedback } from "@/lib/research-api";

export function FeedbackDialog({
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
