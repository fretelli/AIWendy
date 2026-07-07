"use client";

import { useState } from "react";
import Image from "next/image";
import { Heart, Loader2, RefreshCw, Send } from "lucide-react";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { redeemPointsMallItem, submitFeedback, type PointsMallItem, type PointsMallResponse } from "@/lib/research-api";

import { FALLBACK_MALL_ITEMS } from "../constants";
import { formatDateTime, formatNumber, imageUrl } from "../formatters";
import { ErrorState } from "../states";

export function MallPanel({ mall, error, onReload }: { mall: PointsMallResponse | null; error: string; onReload: () => void }) {
  const [wishOpen, setWishOpen] = useState(false);
  const [redeemItem, setRedeemItem] = useState<PointsMallItem | null>(null);
  const [wishBook, setWishBook] = useState("");
  const [wishNote, setWishNote] = useState("");
  const [wishStatus, setWishStatus] = useState("");
  const [redeemForm, setRedeemForm] = useState({ recipient_name: "", recipient_phone: "", shipping_address: "" });
  const [submitting, setSubmitting] = useState(false);
  const items = mall?.items?.length ? mall.items : FALLBACK_MALL_ITEMS;

  async function submitWish() {
    const normalizedBook = wishBook.trim().replace(/\s+/g, " ");
    const normalizedNote = wishNote.trim().replace(/\s+/g, " ");
    if (normalizedBook.length < 2) {
      setWishStatus("请填写想兑换的书");
      return;
    }
    setSubmitting(true);
    setWishStatus("");
    try {
      await submitFeedback({
        category: "points_mall_wish",
        content: `积分商城许愿：${normalizedBook}${normalizedNote ? `；补充：${normalizedNote}` : ""}`,
        page_path: "/research?tab=mall",
        metadata: {
          wished_book: normalizedBook,
          note: normalizedNote,
        },
      });
      setWishBook("");
      setWishNote("");
      setWishStatus("已收到许愿，可在 research 后台反馈列表看到。");
    } catch (error) {
      setWishStatus(error instanceof Error ? error.message : "许愿提交失败");
    } finally {
      setSubmitting(false);
    }
  }

  async function submitRedeem() {
    if (!redeemItem) return;
    setSubmitting(true);
    try {
      await redeemPointsMallItem({
        item_code: redeemItem.code,
        ...redeemForm,
      });
      setRedeemItem(null);
      setRedeemForm({ recipient_name: "", recipient_phone: "", shipping_address: "" });
      onReload();
    } catch (error) {
      alert(error instanceof Error ? error.message : "兑换失败");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <section className="space-y-5">
      <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
        <div>
          <h2 className="text-lg font-semibold">积分商城</h2>
          <p className="text-sm text-muted-foreground">对应小程序积分商城，书籍信息和许愿入口同步到研报反馈后台。</p>
        </div>
        <div className="flex gap-2">
          <Button size="sm" variant="outline" onClick={() => setWishOpen(true)}>
            <Heart className="mr-2 h-4 w-4" />
            许愿
          </Button>
          <Button size="sm" variant="outline" onClick={onReload}>
            <RefreshCw className="mr-2 h-4 w-4" />
            刷新
          </Button>
        </div>
      </div>
      {error ? <ErrorState message={`${error}。未授权时先展示当前小程序同款书籍，兑换需研报账号授权。`} /> : null}
      <div className="grid gap-4 md:grid-cols-3">
        {items.map((item) => (
          <div key={item.code} className="rounded-md border p-4">
            <div className="relative aspect-[3/4] overflow-hidden rounded-md border bg-muted">
              {item.cover_image ? (
                <Image
                  src={imageUrl(item.cover_image)}
                  alt={item.name}
                  fill
                  unoptimized
                  sizes="(min-width: 768px) 33vw, 100vw"
                  className="object-cover"
                />
              ) : (
                <div className="flex h-full items-center justify-center text-3xl font-bold text-muted-foreground">{item.name.slice(1, 2)}</div>
              )}
            </div>
            <h3 className="mt-4 font-semibold">{item.name}</h3>
            <p className="mt-1 text-sm text-muted-foreground">{item.subtitle}</p>
            <p className="mt-3 min-h-12 text-sm leading-6 text-muted-foreground">{item.description}</p>
            <div className="mt-4 flex items-center justify-between">
              <div>
                <div className="text-lg font-bold">{formatNumber(item.points_cost)} 分</div>
                <div className="text-xs text-muted-foreground">库存 {item.stock}</div>
              </div>
              <Button size="sm" disabled={!item.can_redeem || item.stock <= 0} onClick={() => setRedeemItem(item)}>
                兑换
              </Button>
            </div>
          </div>
        ))}
      </div>
      {mall?.redemptions?.length ? (
        <div className="rounded-md border p-4">
          <h3 className="font-semibold">兑换记录</h3>
          <div className="mt-3 space-y-2">
            {mall.redemptions.map((item) => (
              <div key={item.id} className="flex items-center justify-between border-t pt-2 text-sm">
                <span>{item.item_name}</span>
                <span className="text-muted-foreground">{item.status} · {formatDateTime(item.created_at)}</span>
              </div>
            ))}
          </div>
        </div>
      ) : null}

      <Dialog open={wishOpen} onOpenChange={setWishOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>许愿想兑换的书</DialogTitle>
            <DialogDescription>提交后会进入 research 后台「积分商城许愿」反馈列表。</DialogDescription>
          </DialogHeader>
          <div className="space-y-3">
            <div className="space-y-2">
              <Label>书名 / 作者 / 版本</Label>
              <Input value={wishBook} onChange={(event) => setWishBook(event.target.value)} placeholder="例如：某本中译版书籍" />
            </div>
            <div className="space-y-2">
              <Label>补充说明</Label>
              <Textarea value={wishNote} onChange={(event) => setWishNote(event.target.value)} placeholder="可选：出版社、译者、为什么想兑换" />
            </div>
            {wishStatus ? <div className="text-sm text-muted-foreground">{wishStatus}</div> : null}
          </div>
          <DialogFooter>
            <Button onClick={submitWish} disabled={submitting}>
              {submitting ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Send className="mr-2 h-4 w-4" />}
              提交许愿
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog open={!!redeemItem} onOpenChange={(open) => !open && setRedeemItem(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>兑换 {redeemItem?.name}</DialogTitle>
            <DialogDescription>兑换会消耗积分并生成发货记录。</DialogDescription>
          </DialogHeader>
          <div className="space-y-3">
            <Input value={redeemForm.recipient_name} onChange={(event) => setRedeemForm((prev) => ({ ...prev, recipient_name: event.target.value }))} placeholder="收件人" />
            <Input value={redeemForm.recipient_phone} onChange={(event) => setRedeemForm((prev) => ({ ...prev, recipient_phone: event.target.value }))} placeholder="联系电话" />
            <Textarea value={redeemForm.shipping_address} onChange={(event) => setRedeemForm((prev) => ({ ...prev, shipping_address: event.target.value }))} placeholder="收货地址" />
          </div>
          <DialogFooter>
            <Button onClick={submitRedeem} disabled={submitting}>
              确认兑换
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </section>
  );
}
