"use client";

import { useEffect, useRef, useState } from "react";
import { Loader2, X } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import {
  addUserPreferenceTag,
  removeUserPreferenceTag,
  trackClientEvent,
  transcribePreferenceAudio,
  updateAccountProfile,
  updateMiniappDeliveryProfile,
  updateOnboardingProfile,
  updateUserPreferences,
  uploadAvatar,
  type PreferenceOptionsResponse,
  type UserProfileResponse,
} from "@/lib/research-api";

import { EmptyState, ErrorState } from "../states";
import { AvatarPreferenceControls, PromptTemplateEditor } from "./preference-form-sections";
import {
  joinTags,
  normalizeCustomKeywords,
  parseKeywordInput,
  splitTags,
  type PreferenceTagType,
} from "./preference-utils";

export function PreferencesPanel({ profile, preferenceOptions, error, onReload }: { profile: UserProfileResponse | null; preferenceOptions: PreferenceOptionsResponse | null; error: string; onReload: () => void }) {
  const avatarInputRef = useRef<HTMLInputElement>(null);
  const audioInputRef = useRef<HTMLInputElement>(null);
  const [nickname, setNickname] = useState("");
  const [industries, setIndustries] = useState("");
  const [occupation, setOccupation] = useState("");
  const [themes, setThemes] = useState("");
  const [updateFrequency, setUpdateFrequency] = useState("每周");
  const [languagePreference, setLanguagePreference] = useState("");
  const [keywords, setKeywords] = useState("");
  const [keywordDraft, setKeywordDraft] = useState("");
  const [customPrompt, setCustomPrompt] = useState("");
  const [deliveryEnabled, setDeliveryEnabled] = useState(false);
  const [subscriptionStatus, setSubscriptionStatus] = useState("unknown");
  const [status, setStatus] = useState("");
  const [saving, setSaving] = useState(false);
  const [uploading, setUploading] = useState(false);
  const options = preferenceOptions?.options || profile?.options || {
    industries: [],
    themes: [],
    update_frequencies: ["每日", "每周"],
    language_preferences: [],
  };

  useEffect(() => {
    queueMicrotask(() => {
      if (!profile) return;
      setNickname(profile.nickname || "");
      setIndustries((profile.onboarding_profile?.industries?.length ? profile.onboarding_profile.industries : profile.preferences.industries).join("、"));
      setOccupation(profile.onboarding_profile?.occupation || "");
      setThemes(profile.preferences.themes.join("、"));
      setUpdateFrequency(profile.preferences.update_frequency || "每周");
      setLanguagePreference(profile.preferences.language_preference || "");
      setKeywords(profile.preferences.custom_keywords.join("、"));
      setCustomPrompt(profile.preferences.custom_prompt || "");
      setDeliveryEnabled(profile.delivery.enabled);
      setSubscriptionStatus(profile.delivery.subscription_status || "unknown");
    });
  }, [profile]);

  function patchTagField(type: PreferenceTagType, value: string, action: "add" | "remove") {
    const mutate = (raw: string) => {
      const current = splitTags(raw);
      const next = action === "add" ? [...current, value] : current.filter((item) => item !== value);
      return joinTags(next);
    };
    if (type === "industry") setIndustries(mutate);
    if (type === "theme") setThemes(mutate);
    if (type === "custom_keyword") setKeywords(mutate);
  }

  function appendKeywords(rawText: string) {
    const parsed = parseKeywordInput(rawText);
    const normalizedAddition = normalizeCustomKeywords(parsed);
    if (normalizedAddition.error) {
      setStatus(normalizedAddition.error);
      return;
    }
    const addition = normalizedAddition.values;
    if (!addition.length) return;
    const merged = normalizeCustomKeywords([...splitTags(keywords), ...addition]);
    if (merged.error) {
      setStatus(merged.error);
      setKeywords(joinTags(merged.values));
      return;
    }
    setKeywords(joinTags(merged.values));
    setKeywordDraft("");
    setStatus(`已添加 ${addition.join("、")}`);
  }

  async function mutatePreferenceTag(type: PreferenceTagType, value: string, action: "add" | "remove") {
    const normalized = value.trim();
    if (!normalized) return;
    setUploading(true);
    setStatus("");
    try {
      if (action === "add") {
        await addUserPreferenceTag(type, normalized);
      } else {
        await removeUserPreferenceTag(type, normalized);
      }
      patchTagField(type, normalized, action);
      setStatus(action === "add" ? `已添加 ${normalized}` : `已移除 ${normalized}`);
      onReload();
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "偏好标签更新失败");
    } finally {
      setUploading(false);
    }
  }

  async function handleAvatarUpload(file?: File | null) {
    if (!file) return;
    setUploading(true);
    setStatus("");
    try {
      await uploadAvatar(file);
      setStatus("头像已上传");
      trackClientEvent({
        event_name: "web_avatar_uploaded",
        page_path: "/research?tab=preferences",
        metadata: { file_type: file.type, file_size: file.size },
      }).catch(() => undefined);
      onReload();
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "头像上传失败");
    } finally {
      setUploading(false);
      if (avatarInputRef.current) avatarInputRef.current.value = "";
    }
  }

  async function handlePreferenceAudio(file?: File | null) {
    if (!file) return;
    setUploading(true);
    setStatus("");
    try {
      const result = await transcribePreferenceAudio(file);
      const nextTags = joinTags([...splitTags(keywords), ...(result.tags || [])]);
      setKeywords(nextTags);
      if (result.text) {
        setCustomPrompt((prev) => [prev.trim(), `语音偏好：${result.text}`].filter(Boolean).join("\n"));
      }
      setStatus(result.tags?.length ? `语音已识别：${result.tags.join("、")}` : "语音已识别，请检查偏好内容");
      trackClientEvent({
        event_name: "web_preference_audio_transcribed",
        page_path: "/research?tab=preferences",
        metadata: { file_type: file.type, file_size: file.size, tag_count: result.tags?.length || 0 },
      }).catch(() => undefined);
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "语音识别失败");
    } finally {
      setUploading(false);
      if (audioInputRef.current) audioInputRef.current.value = "";
    }
  }

  async function save() {
    if (!profile) return;
    setSaving(true);
    setStatus("");
    try {
      const normalizedNickname = nickname.trim().replace(/\s+/g, " ");
      const normalizedIndustries = splitTags(industries).slice(0, 8);
      const normalizedOccupation = occupation.trim().replace(/\s+/g, " ");
      const normalizedKeywords = normalizeCustomKeywords(splitTags(keywords));
      if (normalizedKeywords.error) {
        setStatus(normalizedKeywords.error);
        setSaving(false);
        return;
      }
      await Promise.all([
        updateAccountProfile({ nickname: normalizedNickname || profile.nickname }),
        updateOnboardingProfile({
          industries: normalizedIndustries.slice(0, 2),
          occupation: normalizedOccupation,
        }),
        updateUserPreferences({
          ...profile.preferences,
          industries: normalizedIndustries,
          themes: splitTags(themes),
          update_frequency: updateFrequency || "每周",
          language_preference: languagePreference || null,
          custom_keywords: normalizedKeywords.values,
          custom_prompt: customPrompt.trim(),
        }),
        updateMiniappDeliveryProfile({
          enabled: deliveryEnabled,
          subscription_status: subscriptionStatus,
        }),
      ]);
      trackClientEvent({
        event_name: "web_preferences_saved",
        page_path: "/research?tab=preferences",
        status: "success",
        metadata: {
          industries_count: normalizedIndustries.length,
          themes_count: splitTags(themes).length,
          custom_keywords_count: normalizedKeywords.values.length,
          update_frequency: updateFrequency || "每周",
          language_preference: languagePreference || null,
        },
      }).catch(() => undefined);
      setStatus("资料、画像、偏好和推送设置已保存");
      onReload();
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "保存失败");
    } finally {
      setSaving(false);
    }
  }

  return (
    <section className="space-y-5">
      <div>
        <h2 className="text-lg font-semibold">兴趣设置 / 资料设置</h2>
        <p className="text-sm text-muted-foreground">对应小程序兴趣设置和资料设置，支持行业、主题、关键词、自定义提示词。</p>
      </div>
      {error ? <ErrorState message={error} /> : null}
      {profile ? (
        <div className="space-y-4 rounded-md border p-4">
          <AvatarPreferenceControls
            profile={profile}
            uploading={uploading}
            avatarInputRef={avatarInputRef}
            audioInputRef={audioInputRef}
            onAvatarFile={handleAvatarUpload}
            onAudioFile={handlePreferenceAudio}
          />
          <div className="grid gap-4 md:grid-cols-2">
            <div className="space-y-2">
              <Label>昵称</Label>
              <Input value={nickname} onChange={(event) => setNickname(event.target.value)} placeholder="用于研报小程序展示" />
            </div>
            <div className="space-y-2">
              <Label>职业 / 身份</Label>
              <Input value={occupation} onChange={(event) => setOccupation(event.target.value)} placeholder="例如：二级市场研究、品牌投资人" />
            </div>
          </div>
          <div className="grid gap-4 md:grid-cols-2">
            <div className="space-y-2">
              <Label>关注行业 / 入门画像行业</Label>
              <Textarea value={industries} onChange={(event) => setIndustries(event.target.value)} placeholder="消费、科技、医药" />
              <div className="flex flex-wrap gap-2">
                {options.industries.slice(0, 12).map((item) => (
                  <Button key={item} type="button" size="sm" variant="outline" onClick={() => mutatePreferenceTag("industry", item, "add")} disabled={uploading}>
                    + {item}
                  </Button>
                ))}
              </div>
            </div>
            <div className="space-y-2">
              <Label>主题</Label>
              <Textarea value={themes} onChange={(event) => setThemes(event.target.value)} placeholder="AI、出海、周期" />
              <div className="flex flex-wrap gap-2">
                {options.themes.slice(0, 12).map((item) => (
                  <Button key={item} type="button" size="sm" variant="outline" onClick={() => mutatePreferenceTag("theme", item, "add")} disabled={uploading}>
                    + {item}
                  </Button>
                ))}
              </div>
            </div>
          </div>
          <div className="grid gap-4 md:grid-cols-2">
            <div className="space-y-2">
              <Label>更新频率</Label>
              <div className="flex flex-wrap gap-2">
                {(options.update_frequencies.length ? options.update_frequencies : ["每日", "每周"]).map((item) => (
                  <Button
                    key={item}
                    type="button"
                    size="sm"
                    variant={updateFrequency === item ? "secondary" : "outline"}
                    onClick={() => setUpdateFrequency(item)}
                  >
                    {item}
                  </Button>
                ))}
              </div>
            </div>
            <div className="space-y-2">
              <Label>语言偏好</Label>
              <select
                className="w-full rounded-md border bg-background px-3 py-2 text-sm"
                value={languagePreference}
                onChange={(event) => setLanguagePreference(event.target.value)}
              >
                <option value="">跟随内容</option>
                {(options.language_preferences || []).map((item) => (
                  <option key={item} value={item}>
                    {item}
                  </option>
                ))}
              </select>
            </div>
          </div>
          <div className="space-y-2">
            <Label>自定义关键词</Label>
            <Input value={keywords} onChange={(event) => setKeywords(event.target.value)} placeholder="用逗号或空格分隔，最多 10 个" />
            <div className="flex flex-col gap-2 sm:flex-row">
              <Input
                value={keywordDraft}
                maxLength={60}
                onChange={(event) => setKeywordDraft(event.target.value)}
                onKeyDown={(event) => {
                  if (event.key === "Enter") appendKeywords(keywordDraft);
                }}
                placeholder="输入一个关注点后添加"
              />
              <Button type="button" variant="outline" onClick={() => appendKeywords(keywordDraft)}>
                添加
              </Button>
            </div>
            <div className="text-xs text-muted-foreground">最多 10 个标签，已选 {splitTags(keywords).length}/10。</div>
            <div className="flex flex-wrap gap-2">
              {splitTags(keywords).slice(0, 12).map((item) => (
                <Button key={item} type="button" size="sm" variant="secondary" onClick={() => mutatePreferenceTag("custom_keyword", item, "remove")} disabled={uploading}>
                  {item}
                  <X className="ml-2 h-3 w-3" />
                </Button>
              ))}
            </div>
          </div>
          <PromptTemplateEditor customPrompt={customPrompt} onCustomPromptChange={setCustomPrompt} onStatusChange={setStatus} />
          <div className="grid gap-4 md:grid-cols-2">
            <label className="flex items-center gap-3 rounded-md border p-3 text-sm">
              <input
                type="checkbox"
                checked={deliveryEnabled}
                onChange={(event) => setDeliveryEnabled(event.target.checked)}
                className="h-4 w-4 rounded border-input"
              />
              <span>
                <span className="block font-medium">接收小程序/公众号推送</span>
                <span className="text-muted-foreground">对应小程序投递订阅设置。</span>
              </span>
            </label>
            <div className="space-y-2">
              <Label>订阅状态</Label>
              <select
                className="w-full rounded-md border bg-background px-3 py-2 text-sm"
                value={subscriptionStatus}
                onChange={(event) => setSubscriptionStatus(event.target.value)}
              >
                <option value="accept">accept</option>
                <option value="reject">reject</option>
                <option value="ban">ban</option>
                <option value="unknown">unknown</option>
              </select>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <Button onClick={save} disabled={saving || uploading}>
              {saving ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : null}
              保存资料与偏好
            </Button>
            {status ? <span className="text-sm text-muted-foreground">{status}</span> : null}
          </div>
        </div>
      ) : (
        <EmptyState title="需要研报账号授权" description="保存研报 token 后，可编辑个性化推荐偏好。" />
      )}
    </section>
  );
}
