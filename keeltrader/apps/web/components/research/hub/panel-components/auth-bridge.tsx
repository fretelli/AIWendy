"use client";

import { useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { getPendingInvite, setResearchToken, trackClientEvent } from "@/lib/research-api";

export function AuthBridge({ onSaved }: { onSaved: () => void }) {
  const [token, setToken] = useState("");
  const [pendingInvite, setPendingInvite] = useState<ReturnType<typeof getPendingInvite>>(null);

  useEffect(() => {
    setToken(localStorage.getItem("research_access_token") || "");
    setPendingInvite(getPendingInvite());
  }, []);

  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="text-base">研报账号授权</CardTitle>
        <CardDescription>
          小程序的会员、积分、个人偏好、日刊历史等接口需要研报服务 token。Web 版会把这里保存的 token 透传给 research API。
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-3">
        {pendingInvite ? (
          <div className="rounded-md border bg-muted/30 p-3 text-sm text-muted-foreground">
            已捕获邀请来源：{pendingInvite.invite_code || pendingInvite.inviter_user_id || "-"} · {pendingInvite.source_type}
          </div>
        ) : null}
        <div className="flex flex-col gap-3 md:flex-row">
          <Input
            value={token}
            onChange={(event) => setToken(event.target.value)}
            placeholder="粘贴 research_access_token"
            type="password"
          />
          <Button
            onClick={() => {
              setResearchToken(token);
              const latestInvite = getPendingInvite();
              trackClientEvent({
                event_name: "web_research_token_saved",
                page_path: "/research",
                status: token.trim() ? "success" : "warning",
                metadata: {
                  has_pending_invite: !!latestInvite,
                  inviter_user_id: latestInvite?.inviter_user_id || null,
                  invite_code: latestInvite?.invite_code || "",
                  invite_source_type: latestInvite?.source_type || "",
                  invite_source_id: latestInvite?.source_id || "",
                },
              }).catch(() => undefined);
              setPendingInvite(latestInvite);
              onSaved();
            }}
            className="shrink-0"
          >
            保存授权
          </Button>
          <Button
            variant="outline"
            onClick={() => {
              setToken("");
              setResearchToken("");
              trackClientEvent({
                event_name: "web_research_token_cleared",
                page_path: "/research",
                status: "success",
              }).catch(() => undefined);
              onSaved();
            }}
            className="shrink-0"
          >
            清空授权
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
