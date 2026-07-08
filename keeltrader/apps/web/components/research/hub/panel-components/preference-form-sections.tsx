"use client";

import Image from "next/image";
import { Mic, Upload } from "lucide-react";
import type { RefObject } from "react";

import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import type { UserProfileResponse } from "@/lib/research-api";

import { PROMPT_TEMPLATES } from "../constants";

export function AvatarPreferenceControls({
  profile,
  uploading,
  avatarInputRef,
  audioInputRef,
  onAvatarFile,
  onAudioFile,
}: {
  profile: UserProfileResponse;
  uploading: boolean;
  avatarInputRef: RefObject<HTMLInputElement>;
  audioInputRef: RefObject<HTMLInputElement>;
  onAvatarFile: (file?: File | null) => void;
  onAudioFile: (file?: File | null) => void;
}) {
  return (
    <div className="flex flex-col gap-4 rounded-md border bg-muted/20 p-4 md:flex-row md:items-center md:justify-between">
      <div className="flex items-center gap-4">
        <div className="relative h-16 w-16 overflow-hidden rounded-md border bg-background">
          {profile.avatar_url ? (
            <Image
              src={profile.avatar_url}
              alt={profile.nickname || "头像"}
              fill
              unoptimized
              sizes="64px"
              className="object-cover"
            />
          ) : (
            <div className="flex h-full w-full items-center justify-center text-lg font-semibold text-muted-foreground">
              {(profile.nickname || "研").slice(0, 1)}
            </div>
          )}
        </div>
        <div>
          <div className="font-medium">头像与语音偏好</div>
          <div className="mt-1 text-sm text-muted-foreground">对应小程序头像上传和语音录入偏好。</div>
        </div>
      </div>
      <div className="flex flex-wrap gap-2">
        <input
          ref={avatarInputRef}
          type="file"
          accept="image/*"
          className="hidden"
          onChange={(event) => onAvatarFile(event.target.files?.[0])}
        />
        <input
          ref={audioInputRef}
          type="file"
          accept="audio/*"
          className="hidden"
          onChange={(event) => onAudioFile(event.target.files?.[0])}
        />
        <Button size="sm" variant="outline" onClick={() => avatarInputRef.current?.click()} disabled={uploading}>
          <Upload className="mr-2 h-4 w-4" />
          上传头像
        </Button>
        <Button size="sm" variant="outline" onClick={() => audioInputRef.current?.click()} disabled={uploading}>
          <Mic className="mr-2 h-4 w-4" />
          语音偏好
        </Button>
      </div>
    </div>
  );
}

export function PromptTemplateEditor({
  customPrompt,
  onCustomPromptChange,
  onStatusChange,
}: {
  customPrompt: string;
  onCustomPromptChange: (value: string) => void;
  onStatusChange: (value: string) => void;
}) {
  return (
    <div className="space-y-2">
      <Label>自定义推荐要求</Label>
      <div className="grid gap-2 md:grid-cols-4">
        {PROMPT_TEMPLATES.map((template) => (
          <button
            key={template.id}
            type="button"
            onClick={() => {
              onCustomPromptChange(template.prompt);
              onStatusChange(`已应用模板：${template.title}`);
            }}
            className={`rounded-md border p-3 text-left text-sm transition-colors hover:bg-muted/40 ${customPrompt.trim() === template.prompt ? "border-primary bg-muted/50" : ""}`}
          >
            <span className="block font-medium">{template.title}</span>
            <span className="mt-1 block text-xs leading-5 text-muted-foreground">{template.description}</span>
          </button>
        ))}
      </div>
      <Textarea
        value={customPrompt}
        maxLength={500}
        onChange={(event) => onCustomPromptChange(event.target.value)}
        placeholder="例如：更关注商业模式和估值变化"
      />
      <div className="flex items-center justify-between text-xs text-muted-foreground">
        <button type="button" className="hover:text-foreground" onClick={() => onCustomPromptChange("")}>
          清空自定义
        </button>
        <span>{customPrompt.length}/500</span>
      </div>
    </div>
  );
}
