/**
 * Chat module type definitions
 */

// Attachment types supported by the system
export type AttachmentType =
  | 'image'
  | 'audio'
  | 'pdf'
  | 'word'
  | 'excel'
  | 'ppt'
  | 'text'
  | 'code'
  | 'file';

/**
 * Attachment that has been uploaded and is part of a message
 */
export interface ChatAttachment {
  id: string;
  type: AttachmentType;
  fileName: string;
  fileSize: number;
  mimeType: string;
  url: string;
  thumbnailUrl?: string;
  transcription?: string; // For audio files
  extractedText?: string; // For documents (PDF, Word, etc.)
}

/**
 * Attachment being prepared for upload (before sending)
 */
export interface PendingAttachment {
  id: string;
  type: AttachmentType;
  file: File;
  previewUrl: string;
  status: 'pending' | 'uploading' | 'ready' | 'error';
  progress?: number; // Upload progress 0-100
  error?: string;
  // After successful upload
  uploadedUrl?: string;
  uploadedData?: UploadedFile;
}

/**
 * Response from file upload API
 */
export interface UploadedFile {
  id: string;
  fileName: string;
  fileSize: number;
  mimeType: string;
  type: AttachmentType;
  url: string;
  thumbnailBase64?: string;
}

/**
 * Response from text extraction API
 */
export interface TextExtractionResult {
  success: boolean;
  text?: string;
  error?: string;
  fileType?: string;
  pageCount?: number;
}

/**
 * Response from audio transcription API
 */
export interface TranscriptionResult {
  text: string;
  language?: string;
  confidence?: number;
}

/**
 * Voice recording mode
 */
export type VoiceMode = 'transcribe' | 'attachment';

/**
 * Voice recorder state
 */
export interface VoiceRecorderState {
  isRecording: boolean;
  isPaused: boolean;
  duration: number; // In seconds
  audioBlob: Blob | null;
  audioUrl: string | null;
}

/**
 * Message with optional attachments
 */
export interface Message {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: Date;
  isStreaming?: boolean;
  error?: boolean;
  attachments?: ChatAttachment[];
}

/**
 * Message for sending to API (with attachment info)
 */
export interface ApiMessage {
  role: string;
  content: string;
  attachments?: ApiMessageAttachment[];
}

/**
 * Attachment format for API request
 */
export interface ApiMessageAttachment {
  id: string;
  type: string;
  fileName: string;
  fileSize: number;
  mimeType: string;
  url: string;
  base64Data?: string; // For images to send to LLM
  extractedText?: string; // For documents
  transcription?: string; // For audio
}

/**
 * Get file category from MIME type
 */
export function getFileCategory(mimeType: string, fileName: string): AttachmentType {
  // Check by MIME type first
  if (mimeType.startsWith('image/')) return 'image';
  if (mimeType.startsWith('audio/')) return 'audio';
  if (mimeType === 'application/pdf') return 'pdf';
  if (
    mimeType === 'application/vnd.openxmlformats-officedocument.wordprocessingml.document' ||
    mimeType === 'application/msword'
  ) {
    return 'word';
  }
  if (
    mimeType === 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' ||
    mimeType === 'application/vnd.ms-excel' ||
    mimeType === 'text/csv'
  ) {
    return 'excel';
  }
  if (
    mimeType === 'application/vnd.openxmlformats-officedocument.presentationml.presentation' ||
    mimeType === 'application/vnd.ms-powerpoint'
  ) {
    return 'ppt';
  }

  // Check by extension
  const ext = fileName.split('.').pop()?.toLowerCase() || '';
  const textExtensions = ['txt', 'md', 'markdown', 'json', 'xml', 'yaml', 'yml', 'log', 'ini', 'cfg'];
  const codeExtensions = [
    'py', 'js', 'ts', 'jsx', 'tsx', 'vue', 'svelte',
    'java', 'c', 'cpp', 'cc', 'h', 'hpp', 'cs',
    'go', 'rs', 'rb', 'php', 'swift', 'kt', 'scala',
    'sh', 'bash', 'zsh', 'ps1', 'bat', 'cmd',
    'sql', 'r', 'lua', 'dart', 'elm',
    'html', 'css', 'scss', 'sass', 'less',
  ];

  if (textExtensions.includes(ext)) return 'text';
  if (codeExtensions.includes(ext)) return 'code';

  return 'file';
}

/**
 * Format file size for display
 */
export function formatFileSize(bytes: number): string {
  if (bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
}

/**
 * Check if file type can have text extracted
 */
export function canExtractText(type: AttachmentType): boolean {
  return ['pdf', 'word', 'excel', 'ppt', 'text', 'code'].includes(type);
}

/**
 * Check if file is an image that can be sent to vision LLM
 */
export function isImageForVision(type: AttachmentType): boolean {
  return type === 'image';
}
