// Roundtable discussion types

import type { ApiMessageAttachment, ChatAttachment } from "@/types/chat"

export type KbTiming = "off" | "message" | "round" | "coach" | "moderator"

export interface CoachBrief {
  id: string
  name: string
  avatar_url?: string
  style: string
  description?: string
}

export interface CoachPreset {
  id: string
  name: string
  description?: string
  icon?: string
  coach_ids: string[]
  coaches?: CoachBrief[]
  sort_order: number
  is_active: boolean
}

export interface RoundtableSession {
  id: string
  user_id: string
  project_id?: string | null
  preset_id?: string | null
  title?: string
  coach_ids: string[]
  coaches?: CoachBrief[]
  turn_order?: string[]
  current_turn: number
  message_count: number
  round_count: number
  is_active: boolean
  // Moderator mode fields
  discussion_mode: 'free' | 'moderated'
  moderator_id?: string | null
  moderator?: CoachBrief | null
  // Session-level settings (optional; can be overridden per message)
  llm_config_id?: string | null
  llm_provider?: string | null
  llm_model?: string | null
  llm_temperature?: number | null
  llm_max_tokens?: number | null
  kb_timing?: KbTiming
  kb_top_k?: number
  kb_max_candidates?: number
  created_at: string
  updated_at: string
}

export type MessageType = 'response' | 'opening' | 'summary' | 'closing'

export interface RoundtableMessage {
  id: string
  session_id: string
  coach_id?: string | null
  coach?: CoachBrief | null
  role: 'user' | 'assistant'
  content: string
  attachments?: ChatAttachment[]
  message_type: MessageType
  turn_number?: number
  sequence_in_turn?: number
  created_at: string
}

export interface CreateRoundtableSessionRequest {
  preset_id?: string
  coach_ids?: string[]
  project_id?: string | null
  title?: string
  // Moderator mode settings
  discussion_mode?: 'free' | 'moderated'
  moderator_id?: string  // Default is 'host'
  // Optional session-level settings
  config_id?: string
  provider?: string
  model?: string
  temperature?: number
  max_tokens?: number
  kb_timing?: KbTiming
  kb_top_k?: number
  kb_max_candidates?: number
}

export interface RoundtableChatRequest {
  session_id: string
  content: string
  attachments?: ApiMessageAttachment[]
  max_rounds?: number
  config_id?: string
  provider?: string
  model?: string
  temperature?: number
  max_tokens?: number
  kb_timing?: KbTiming
  kb_top_k?: number
  kb_max_candidates?: number
  should_end?: boolean  // Request moderator closing remarks
  debate_style?: 'converge' | 'clash'
}

export interface SessionDetailResponse {
  session: RoundtableSession
  messages: RoundtableMessage[]
}

// SSE Event types
export type RoundtableEventType =
  | 'round_start'
  | 'coach_start'
  | 'content'
  | 'coach_end'
  | 'round_end'
  | 'moderator_start'
  | 'moderator_end'
  | 'done'
  | 'error'

export interface RoundtableRoundStartEvent {
  type: 'round_start'
  round: number
}

export interface RoundtableCoachStartEvent {
  type: 'coach_start'
  coach_id: string
  coach_name: string
  coach_avatar?: string
}

export interface RoundtableContentEvent {
  type: 'content'
  coach_id: string
  content: string
}

export interface RoundtableCoachEndEvent {
  type: 'coach_end'
  coach_id: string
}

export interface RoundtableRoundEndEvent {
  type: 'round_end'
  round: number
}

export interface RoundtableDoneEvent {
  type: 'done'
}

export interface RoundtableErrorEvent {
  type: 'error'
  message: string
}

// Moderator events
export interface RoundtableModeratorStartEvent {
  type: 'moderator_start'
  message_type: MessageType  // 'opening' | 'summary' | 'closing'
  coach_id: string
  coach_name: string
  coach_avatar?: string
}

export interface RoundtableModeratorEndEvent {
  type: 'moderator_end'
  message_type: MessageType
  coach_id: string
}

export type RoundtableEvent =
  | RoundtableRoundStartEvent
  | RoundtableCoachStartEvent
  | RoundtableContentEvent
  | RoundtableCoachEndEvent
  | RoundtableRoundEndEvent
  | RoundtableModeratorStartEvent
  | RoundtableModeratorEndEvent
  | RoundtableDoneEvent
  | RoundtableErrorEvent

// UI State types
export interface StreamingCoachResponse {
  coach_id: string
  coach_name: string
  coach_avatar?: string
  content: string
  isStreaming: boolean
  message_type?: MessageType  // For moderator messages
}

export interface RoundtableState {
  messages: RoundtableMessage[]
  currentRound: number
  currentCoach: string | null
  isLoading: boolean
  streamingResponses: Record<string, StreamingCoachResponse>
}

// Preset icons mapping
export const PRESET_ICONS: Record<string, string> = {
  stars: '⭐',
  brain: '🧠',
  heart: '❤️',
  swords: '⚔️',
  lightbulb: '💡',
}
