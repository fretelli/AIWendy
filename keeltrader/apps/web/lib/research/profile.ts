"use client";

import { researchRequest, researchUpload } from "./client";
import type { PreferenceOptionsResponse, UserPreferenceTagType, UserProfileResponse } from "./types";

export function getUserProfile() {
  return researchRequest<UserProfileResponse>("/user/profile", {}, { auth: "required" });
}

export function updateUserPreferences(data: UserProfileResponse["preferences"]) {
  return researchRequest<{ ok: boolean; profile_completed: boolean }>("/user/preferences", {
    method: "PUT",
    body: JSON.stringify(data),
  }, { auth: "required" });
}

export function updateOnboardingProfile(data: { industries: string[]; occupation: string }) {
  return researchRequest<{
    ok: boolean;
    onboarding_completed: boolean;
    onboarding_profile: UserProfileResponse["onboarding_profile"];
  }>("/user/onboarding-profile", {
    method: "PUT",
    body: JSON.stringify(data),
  }, { auth: "required" });
}

export function updateAccountProfile(data: { nickname: string }) {
  return researchRequest<{
    ok: boolean;
    user_id: number;
    nickname: string;
    avatar_url: string;
  }>("/user/account-profile", {
    method: "PUT",
    body: JSON.stringify(data),
  }, { auth: "required" });
}

export function uploadAvatar(file: File) {
  return researchUpload<{
    ok: boolean;
    user_id: number;
    nickname: string;
    avatar_url: string;
  }>("/user/avatar", file, { auth: "required" });
}

export function addUserPreferenceTag(preference_type: UserPreferenceTagType, preference_value: string) {
  return researchRequest<{ ok: boolean; profile_completed: boolean }>("/user/preferences/add-tag", {
    method: "POST",
    body: JSON.stringify({ preference_type, preference_value }),
  }, { auth: "required" });
}

export function removeUserPreferenceTag(preference_type: UserPreferenceTagType, preference_value: string) {
  return researchRequest<{ ok: boolean; profile_completed: boolean }>("/user/preferences/remove-tag", {
    method: "POST",
    body: JSON.stringify({ preference_type, preference_value }),
  }, { auth: "required" });
}

export function updateMiniappDeliveryProfile(data: {
  enabled: boolean;
  subscription_status: "accept" | "reject" | "ban" | "unknown" | string;
}) {
  return researchRequest<{
    ok: boolean;
    delivery: UserProfileResponse["delivery"];
  }>("/user/delivery/miniapp-subscription", {
    method: "POST",
    body: JSON.stringify(data),
  }, { auth: "required" });
}

export function getPreferenceOptions() {
  return researchRequest<PreferenceOptionsResponse>("/user/preference-options", {}, { auth: "optional" });
}

export function transcribePreferenceAudio(file: File) {
  return researchUpload<{ text: string; tags: string[] }>("/speech/transcribe-preference", file, { auth: "required" });
}
