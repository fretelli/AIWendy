"use client";

import { useMemo, useState } from "react";
import { CheckCircle2, Copy, CreditCard, Gift, RefreshCw, Share2 } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  trackClientEvent,
  type BillingOverview,
  type BillingOrderDetail,
  type InviteOverview,
  type OfficialBindingStatus,
  type ProductItem,
  type UserProfileResponse,
} from "@/lib/research-api";

import { formatDate, formatDateTime, formatMoneyFen, formatNumber } from "../formatters";
import { EmptyState, ErrorState } from "../states";

export function MembershipPanel({ overview, profile, invite, catalog, officialBinding, orderDetail, orderStatus, error, onCheckIn, onReload, onCreateOrder, onOpenOrder, onRefreshOrderPayment, onGoMall }: {
  overview: BillingOverview | null;
  profile: UserProfileResponse | null;
  invite: InviteOverview | null;
  catalog: ProductItem[];
  officialBinding: OfficialBindingStatus | null;
  orderDetail: BillingOrderDetail | null;
  orderStatus: string;
  error: string;
  onCheckIn: () => void;
  onReload: () => void;
  onCreateOrder: (product: ProductItem) => void;
  onOpenOrder: (orderId: number) => void;
  onRefreshOrderPayment: (orderId: number) => void;
  onGoMall: () => void;
}) {
  const [inviteStatus, setInviteStatus] = useState("");

  const rewardRuleText = useMemo(() => {
    const rule = invite?.summary.reward_rule;
    if (!rule) return invite?.summary.reward_copy || overview?.invite_summary.reward_copy || "每邀请 1 位好友注册，邀请双方可获得奖励积分和 PDF 权益。";
    const inviterPoints = Number(rule.inviter_points || 100);
    const inviteePoints = Number(rule.invitee_points || inviterPoints);
    return `每成功邀请 1 位好友，邀请双方各获得 ${inviterPoints} 积分；新用户获得 ${inviteePoints} 积分后也可兑换 PDF。`;
  }, [invite, overview]);

  function inviteRewardText(record: InviteOverview["records"][number]) {
    const pointReward = record.rewards.find((item) => item.reward_type === "invite_points");
    const pdfReward = record.rewards.find((item) => item.reward_type === "report_pdf_credit");
    const parts: string[] = [];
    const points = Number((pointReward?.reward_value as { points?: number } | undefined)?.points || 0);
    const pdfCredits = Number((pdfReward?.reward_value as { credits?: number } | undefined)?.credits || 0);
    if (points > 0) parts.push(`${points} 积分`);
    if (pdfCredits > 0) parts.push(`${pdfCredits} 次 PDF`);
    return parts.length ? parts.join(" / ") : "待生效";
  }

  async function copyInviteLink() {
    if (!profile?.user_id && !invite?.invite_code) {
      setInviteStatus("需要研报账号授权后才能生成邀请链接");
      return;
    }
    const params = new URLSearchParams();
    if (profile?.user_id) params.set("inviter_id", String(profile.user_id));
    if (invite?.invite_code) params.set("invite_code", invite.invite_code);
    params.set("source", "membership_share");
    params.set("source_id", "membership");
    const url = `${window.location.origin}/research?${params.toString()}`;
    try {
      await navigator.clipboard.writeText(url);
      setInviteStatus("邀请链接已复制");
      trackClientEvent({
        event_name: "web_invite_link_copied",
        page_path: "/research?tab=membership",
        metadata: {
          invite_code: invite?.invite_code || overview?.invite_summary.invite_code || "",
          inviter_id: profile?.user_id || null,
        },
      }).catch(() => undefined);
    } catch {
      setInviteStatus(url);
    }
  }

  return (
    <section className="space-y-5">
      <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
        <div>
          <h2 className="text-lg font-semibold">权益中心 / 我的</h2>
          <p className="text-sm text-muted-foreground">对应小程序权益中心、我的页面、签到、邀请和订单概览。</p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Button size="sm" variant="outline" onClick={onGoMall}>
            <Gift className="mr-2 h-4 w-4" />
            去积分商城
          </Button>
          <Button size="sm" variant="outline" onClick={onReload}>
            <RefreshCw className="mr-2 h-4 w-4" />
            刷新
          </Button>
        </div>
      </div>
      {error ? <ErrorState message={error} /> : null}
      {overview || profile ? (
        <div className="grid gap-4 md:grid-cols-3">
          <div className="rounded-md border p-4">
            <div className="text-sm text-muted-foreground">用户</div>
            <div className="mt-2 text-xl font-semibold">{profile?.nickname || "研报用户"}</div>
            <div className="mt-1 text-sm text-muted-foreground">ID #{profile?.user_id || "-"}</div>
            <div className="mt-1 text-sm text-muted-foreground">
              手机号 {profile?.phone_bound ? profile.phone_masked || "已绑定" : "未绑定"}
            </div>
          </div>
          <div className="rounded-md border p-4">
            <div className="text-sm text-muted-foreground">会员</div>
            <div className="mt-2 text-xl font-semibold">{overview?.active_membership?.is_active ? "已开通" : "未开通"}</div>
            <div className="mt-1 text-sm text-muted-foreground">到期 {formatDate(overview?.active_membership?.expires_at)}</div>
          </div>
          <div className="rounded-md border p-4">
            <div className="text-sm text-muted-foreground">积分</div>
            <div className="mt-2 text-xl font-semibold">{formatNumber(overview?.points_mall?.points?.remaining || 0)}</div>
            <Button className="mt-3" size="sm" onClick={onCheckIn} disabled={overview?.daily_checkin?.checked_in_today}>
              <CheckCircle2 className="mr-2 h-4 w-4" />
              {overview?.daily_checkin?.checked_in_today ? "今日已签到" : `签到 +${overview?.daily_checkin?.reward_points || 0}`}
            </Button>
          </div>
          <div className="rounded-md border p-4 md:col-span-3">
            <div className="text-sm text-muted-foreground">公众号绑定</div>
            <div className="mt-2 flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
              <div>
                <div className="font-semibold">{officialBinding?.bound ? "已绑定" : "未绑定"}</div>
                <div className="text-sm text-muted-foreground">
                  {officialBinding?.binding
                    ? `${officialBinding.binding.official_openid_masked} · ${officialBinding.binding.subscribe_status}`
                    : "对应小程序公众号绑定状态，用于接收推送。"}
                </div>
              </div>
              <Badge variant={officialBinding?.bound ? "secondary" : "outline"}>
                {officialBinding?.binding?.status || "unbound"}
              </Badge>
            </div>
          </div>
        </div>
      ) : (
        <EmptyState title="需要研报账号授权" description="保存研报 token 后，可查看会员、积分、邀请、签到和订单。" />
      )}
      {catalog.length ? (
        <div className="rounded-md border p-4">
          <h3 className="font-semibold">会员商品</h3>
          <div className="mt-3 grid gap-3 md:grid-cols-3">
            {catalog.map((product) => (
              <div key={product.code} className="rounded-md border p-4">
                <div className="flex items-center justify-between gap-2">
                  <div className="font-medium">{product.name}</div>
                  <Badge variant={product.is_active ? "secondary" : "outline"}>{product.product_type}</Badge>
                </div>
                <div className="mt-2 text-2xl font-bold">{formatMoneyFen(product.price_fen)}</div>
                <div className="mt-1 text-xs text-muted-foreground">
                  原价 {formatMoneyFen(product.original_price_fen)} · {product.duration_days ? `${product.duration_days} 天` : "权益商品"}
                </div>
                <Button className="mt-4 w-full" size="sm" disabled={!product.is_active} onClick={() => onCreateOrder(product)}>
                  <CreditCard className="mr-2 h-4 w-4" />
                  创建订单
                </Button>
              </div>
            ))}
          </div>
        </div>
      ) : null}
      {invite ? (
        <div className="rounded-md border p-4">
          <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
            <div>
              <h3 className="font-semibold">邀请奖励</h3>
              <p className="mt-1 text-sm text-muted-foreground">{rewardRuleText}</p>
              {invite.summary.share_message ? <p className="mt-1 text-sm text-muted-foreground">{invite.summary.share_message}</p> : null}
            </div>
            <div className="flex flex-wrap gap-2">
              <Badge variant="secondary">邀请码 {invite.invite_code}</Badge>
              <Button size="sm" variant="outline" onClick={copyInviteLink}>
                <Share2 className="mr-2 h-4 w-4" />
                复制邀请链接
              </Button>
              {invite.invite_code ? (
                <Button size="sm" variant="outline" onClick={() => navigator.clipboard.writeText(invite.invite_code).then(() => setInviteStatus("邀请码已复制")).catch(() => setInviteStatus(invite.invite_code))}>
                  <Copy className="mr-2 h-4 w-4" />
                  复制邀请码
                </Button>
              ) : null}
            </div>
          </div>
          <div className="mt-4 grid gap-3 md:grid-cols-3">
            <div className="rounded-md bg-muted/50 p-3">
              <div className="text-xs text-muted-foreground">已邀请</div>
              <div className="mt-1 font-semibold">{formatNumber(invite.summary.invited_count)}</div>
            </div>
            <div className="rounded-md bg-muted/50 p-3">
              <div className="text-xs text-muted-foreground">已奖励</div>
              <div className="mt-1 font-semibold">{formatNumber(invite.summary.rewarded_count)}</div>
            </div>
            <div className="rounded-md bg-muted/50 p-3">
              <div className="text-xs text-muted-foreground">剩余邀请积分</div>
              <div className="mt-1 font-semibold">{formatNumber(invite.summary.invite_points?.remaining || 0)}</div>
            </div>
            <div className="rounded-md bg-muted/50 p-3">
              <div className="text-xs text-muted-foreground">剩余 PDF 次数</div>
              <div className="mt-1 font-semibold">{formatNumber(invite.summary.pdf_credits?.remaining || 0)}</div>
            </div>
          </div>
          {inviteStatus ? <div className="mt-3 rounded-md bg-muted/50 p-3 text-sm text-muted-foreground">{inviteStatus}</div> : null}
          {invite.records.length ? (
            <div className="mt-4 space-y-2">
              {invite.records.slice(0, 6).map((record) => (
                <div key={record.id} className="flex items-center justify-between border-t pt-2 text-sm">
                  <span>
                    <span className="font-medium">{record.invited_nickname || "匿名用户"}</span>
                    <span className="ml-2 text-xs text-muted-foreground">{inviteRewardText(record)}</span>
                  </span>
                  <span className="text-muted-foreground">{record.status} · {formatDateTime(record.created_at)}</span>
                </div>
              ))}
            </div>
          ) : null}
          {!invite.records.length ? (
            <div className="mt-4 rounded-md border border-dashed p-4 text-sm text-muted-foreground">
              还没有邀请记录。复制邀请链接发给好友，好友授权登录后会在这里显示。
            </div>
          ) : null}
        </div>
      ) : null}
      {overview?.recent_orders?.length ? (
        <div className="rounded-md border p-4">
          <h3 className="font-semibold">近期订单</h3>
          <div className="mt-3 space-y-2">
            {overview.recent_orders.map((order) => (
                <button
                  key={order.id}
                  type="button"
                  className="flex w-full items-center justify-between gap-3 border-t pt-2 text-left text-sm hover:text-primary"
                  onClick={() => onOpenOrder(order.id)}
                >
                  <span>{order.title}</span>
                  <span className="text-muted-foreground">{formatMoneyFen(order.amount_fen)} · {order.payment_status}</span>
                </button>
            ))}
          </div>
        </div>
      ) : null}
      <Dialog open={!!orderDetail} onOpenChange={(open) => !open && onOpenOrder(0)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>订单详情</DialogTitle>
            <DialogDescription>对应小程序权益订单状态，可刷新支付状态。</DialogDescription>
          </DialogHeader>
          {orderDetail ? (
            <div className="space-y-3 text-sm">
              <div className="rounded-md border p-3">
                <div className="font-semibold">{orderDetail.title}</div>
                <div className="mt-1 text-muted-foreground">订单号 {orderDetail.order_no}</div>
              </div>
              <div className="grid gap-3 md:grid-cols-2">
                <div className="rounded-md bg-muted/50 p-3">
                  <div className="text-xs text-muted-foreground">金额</div>
                  <div className="mt-1 font-semibold">{formatMoneyFen(orderDetail.amount_fen)}</div>
                </div>
                <div className="rounded-md bg-muted/50 p-3">
                  <div className="text-xs text-muted-foreground">支付状态</div>
                  <div className="mt-1 font-semibold">{orderDetail.payment_status}</div>
                </div>
                <div className="rounded-md bg-muted/50 p-3">
                  <div className="text-xs text-muted-foreground">订单状态</div>
                  <div className="mt-1 font-semibold">{orderDetail.status}</div>
                </div>
                <div className="rounded-md bg-muted/50 p-3">
                  <div className="text-xs text-muted-foreground">创建时间</div>
                  <div className="mt-1 font-semibold">{formatDateTime(orderDetail.created_at)}</div>
                </div>
              </div>
              <div className="rounded-md bg-muted/50 p-3 text-muted-foreground">
                目标：{orderDetail.target_type || "-"} / {orderDetail.target_id || "-"} · 渠道：{orderDetail.payment_provider || "-"}
              </div>
              {orderStatus ? <div className="rounded-md bg-muted/50 p-3 text-muted-foreground">{orderStatus}</div> : null}
            </div>
          ) : null}
          <DialogFooter>
            {orderDetail ? (
              <Button onClick={() => onRefreshOrderPayment(orderDetail.id)}>
                <RefreshCw className="mr-2 h-4 w-4" />
                刷新支付状态
              </Button>
            ) : null}
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </section>
  );
}
