"use client";

import { researchRequest } from "./client";
import type {
  BillingOrderDetail,
  BillingOverview,
  InviteOverview,
  OfficialBindingStatus,
  PointsMallResponse,
  PointsRedemption,
  ProductItem,
} from "./types";

export function getBillingOverview() {
  return researchRequest<BillingOverview>("/billing/me", {}, { auth: "required" });
}

export function getInviteOverview() {
  return researchRequest<InviteOverview>("/billing/invites/me", {}, { auth: "required" });
}

export function getBillingCatalog() {
  return researchRequest<{ items: ProductItem[] }>("/billing/catalog", {}, { auth: "required" });
}


export function createBillingOrder(data: {
  product_code: string;
  target_type?: string | null;
  target_id?: string | null;
}) {
  return researchRequest<BillingOrderDetail>("/billing/orders", {
    method: "POST",
    body: JSON.stringify(data),
  }, { auth: "required" });
}

export function getBillingOrder(orderId: number) {
  return researchRequest<BillingOrderDetail>(`/billing/orders/${orderId}`, {}, { auth: "required" });
}

export function prepareBillingOrderPayment(orderId: number) {
  return researchRequest<{
    ok: boolean;
    already_paid?: boolean;
    provider?: string;
    configured?: boolean;
    message?: string;
    payment_params?: Record<string, unknown> | null;
  }>(`/billing/orders/${orderId}/pay`, {
    method: "POST",
    body: JSON.stringify({}),
  }, { auth: "required" });
}

export function getOfficialBindingStatus() {
  return researchRequest<OfficialBindingStatus>("/user/official-binding", {}, { auth: "required" });
}

export function dailyCheckIn() {
  return researchRequest<{ ok: boolean; awarded: boolean; checked_in_today: boolean; points_awarded: number; remaining_points?: number; message: string; last_checkin_at: string | null }>("/billing/check-in", {
    method: "POST",
    body: JSON.stringify({}),
  }, { auth: "required" });
}

export function getPointsMall() {
  return researchRequest<PointsMallResponse>("/billing/points-mall", {}, { auth: "required" });
}

export function getPointsMallCatalog() {
  return researchRequest<PointsMallResponse>("/billing/points-mall/catalog", {}, { auth: "optional" });
}

export function redeemPointsMallItem(data: {
  item_code: string;
  recipient_name: string;
  recipient_phone: string;
  shipping_address: string;
}) {
  return researchRequest<{ ok: boolean; points: PointsMallResponse["points"]; redemption: PointsRedemption }>("/billing/points-mall/redeem", {
    method: "POST",
    body: JSON.stringify(data),
  }, { auth: "required" });
}
