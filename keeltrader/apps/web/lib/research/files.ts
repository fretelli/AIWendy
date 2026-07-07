"use client";

import { createSessionId, getErrorMessage, getResearchToken } from "./client";
import type { ApiErrorPayload } from "./types";

export async function downloadResearchFile(path: string, fallbackFileName: string) {
  const { blob, fileName } = await fetchResearchFileBlob(path, fallbackFileName);
  const objectUrl = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = objectUrl;
  anchor.download = fileName;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  setTimeout(() => URL.revokeObjectURL(objectUrl), 1000);
}

export async function createResearchFileObjectUrl(path: string, fallbackFileName: string) {
  const { blob, fileName } = await fetchResearchFileBlob(path, fallbackFileName);
  return {
    objectUrl: URL.createObjectURL(blob),
    fileName,
    contentType: blob.type,
  };
}

async function fetchResearchFileBlob(path: string, fallbackFileName: string) {
  const token = getResearchToken();
  const headers = new Headers();
  headers.set("X-Session-ID", createSessionId());
  if (token) headers.set("Authorization", `Bearer ${token}`);

  const response = await fetch(`/api/research${path}`, { headers });
  if (!response.ok) {
    const payload = await response.json().catch(() => null);
    const message =
      payload && typeof payload === "object"
        ? getErrorMessage(payload as ApiErrorPayload)
        : null;
    throw new Error(message || response.statusText || "下载失败");
  }

  const blob = await response.blob();
  const disposition = response.headers.get("content-disposition") || "";
  const fileNameMatch = /filename="?([^";]+)"?/i.exec(disposition);
  return {
    blob,
    fileName: fileNameMatch?.[1] || fallbackFileName,
  };
}
