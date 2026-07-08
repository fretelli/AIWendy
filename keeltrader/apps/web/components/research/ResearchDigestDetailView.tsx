"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { ArrowLeft, CreditCard, Loader2, MessageSquare, Share2 } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  captureOfficialArticleAttribution,
  createBillingOrder,
  getDigestDetail,
  prepareBillingOrderPayment,
  savePendingInviteFromParams,
  trackClientEvent,
  type DigestDetail,
} from "@/lib/research-api";
import { FeedbackDialog } from "./FeedbackDialog";
import { formatDate, formatMoneyFen } from "./hub/formatters";

export function ResearchDigestDetailView() {
  const params = useParams<{ id: string }>();
  const [digest, setDigest] = useState<DigestDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState("");
  const [error, setError] = useState("");
  const [actionStatus, setActionStatus] = useState("");
  const [feedbackOpen, setFeedbackOpen] = useState(false);
  const digestId = decodeURIComponent(String(params.id || ""));

  useEffect(() => {
    setLoading(true);
    setError("");
    const query = new URLSearchParams(window.location.search);
    const attribution = captureOfficialArticleAttribution(query);
    if (attribution) {
      trackClientEvent({
        event_name: "official_article_digest_open",
        page_path: `/research/digests/${digestId}`,
        digest_id: Number(digestId) || undefined,
        status: "success",
        metadata: {
          source: attribution.source,
          campaign_key: attribution.campaign_key,
          article_type: attribution.article_type,
          entry: attribution.entry,
        },
      }).catch(() => undefined);
    }
    const pendingInvite = savePendingInviteFromParams(query, "digest_share", digestId);
    if (pendingInvite) {
      trackClientEvent({
        event_name: "web_pending_invite_captured",
        page_path: `/research/digests/${digestId}`,
        digest_id: Number(digestId) || undefined,
        status: "success",
        metadata: {
          inviter_user_id: pendingInvite.inviter_user_id || null,
          invite_code: pendingInvite.invite_code || "",
          source_type: pendingInvite.source_type,
          source_id: pendingInvite.source_id,
        },
      }).catch(() => undefined);
    }
    getDigestDetail(digestId)
      .then((data) => {
        setDigest(data);
        trackClientEvent({
          event_name: "web_digest_detail_opened",
          page_path: `/research/digests/${digestId}`,
          digest_id: Number(digestId) || undefined,
          metadata: { can_view_full_digest: data.access?.can_view_full_digest, can_view_history: data.access?.can_view_history },
        }).catch(() => undefined);
      })
      .catch((nextError) => setError(nextError instanceof Error ? nextError.message : "期刊详情加载失败"))
      .finally(() => setLoading(false));
  }, [digestId]);

  async function copyDigestLink() {
    const url = `${window.location.origin}/research/digests/${encodeURIComponent(digestId)}`;
    try {
      await navigator.clipboard.writeText(url);
      setActionStatus("期刊链接已复制");
      trackClientEvent({
        event_name: "web_digest_link_copied",
        page_path: `/research/digests/${digestId}`,
        digest_id: Number(digestId) || undefined,
      }).catch(() => undefined);
    } catch {
      setActionStatus(url);
    }
  }

  async function createDigestAccessOrder(productCode: string) {
    setActionLoading(`order:${productCode}`);
    setActionStatus("");
    try {
      const order = await createBillingOrder({
        product_code: productCode,
        target_type: "digest",
        target_id: digestId,
      });
      const payment = await prepareBillingOrderPayment(order.id);
      const suffix = payment.already_paid
        ? "订单已支付，权益已生效"
        : payment.configured === false
          ? payment.message || "支付暂未配置，订单已创建"
          : payment.message || "订单已创建，请在小程序内完成微信支付";
      setActionStatus(`${order.title} ${formatMoneyFen(order.amount_fen)}。${suffix}`);
      trackClientEvent({
        event_name: "web_digest_access_order_created",
        page_path: `/research/digests/${digestId}`,
        digest_id: Number(digestId) || undefined,
        metadata: { product_code: productCode, order_id: order.id, payment_configured: payment.configured },
      }).catch(() => undefined);
      const nextDigest = await getDigestDetail(digestId).catch(() => null);
      if (nextDigest) setDigest(nextDigest);
    } catch (nextError) {
      setError(nextError instanceof Error ? nextError.message : "创建期刊权益订单失败");
    } finally {
      setActionLoading("");
    }
  }

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
              <div className="mt-5 flex flex-wrap gap-2">
                <Button size="sm" variant="outline" onClick={() => setFeedbackOpen(true)}>
                  <MessageSquare className="mr-2 h-4 w-4" />
                  意见反馈
                </Button>
                <Button size="sm" variant="outline" onClick={copyDigestLink}>
                  <Share2 className="mr-2 h-4 w-4" />
                  复制分享链接
                </Button>
              </div>
            </div>
            {digest.access ? (
              <div className="rounded-md border p-5">
                <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
                  <div>
                    <h2 className="font-semibold">期刊阅读权益</h2>
                    <p className="mt-1 text-sm leading-6 text-muted-foreground">
                      {digest.access.paywall_message || "会员或单期权益会决定是否可查看完整期刊和历史期刊。"}
                    </p>
                    <div className="mt-3 flex flex-wrap gap-2">
                      <Badge variant={digest.access.can_view_full_digest ? "secondary" : "outline"}>
                        {digest.access.can_view_full_digest ? "可读完整期刊" : "期刊受限"}
                      </Badge>
                      <Badge variant={digest.access.can_view_history ? "secondary" : "outline"}>
                        {digest.access.can_view_history ? "可看历史" : "历史受限"}
                      </Badge>
                      <Badge variant="outline">已解锁 {digest.access.unlocked_item_count || 0}</Badge>
                      <Badge variant="outline">锁定 {digest.access.locked_items_count || 0}</Badge>
                      {digest.access.is_member ? <Badge variant="secondary">会员</Badge> : null}
                    </div>
                  </div>
                  {digest.access.membership_product_codes?.length ? (
                    <div className="flex shrink-0 flex-wrap gap-2">
                      {digest.access.membership_product_codes.map((code) => (
                        <Button key={code} size="sm" onClick={() => createDigestAccessOrder(code)} disabled={actionLoading === `order:${code}`}>
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
