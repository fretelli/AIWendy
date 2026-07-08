/**
 * RPG API client
 */

import { apiJson } from '@/lib/api/client'

const API_BASE_URL = '/rpg'

async function fetchAPI<T>(path: string, options?: RequestInit): Promise<T> {
  return apiJson<T>(`${API_BASE_URL}${path}`, options)
}

export interface CharacterData {
  nickname: string
  avatar_settings: Record<string, unknown>
  level: number
  xp: number
  xp_to_next_level: number
  rank: string
  attributes: {
    discipline: number
    patience: number
    risk_management: number
    decisiveness: number
    consistency: number
  }
  achievement_count: number
}

export interface AchievementData {
  id: string
  name: string
  description: string
  category: string
  rarity: string
  icon: string
  xp_reward: number
  unlocked: boolean
  unlocked_at: string | null
}

export interface QuestData {
  id?: string
  quest_id: string
  name: string
  description: string
  quest_type: string
  xp_reward: number
  progress?: { current: number; target: number }
  status?: string
  started_at?: string
  completed_at?: string
}

export interface LeaderboardEntry {
  position: number
  nickname: string
  level: number
  rank: string
  xp: number
  win_rate: number
  profit_factor: number
  achievement_count: number
  is_current_user: boolean
}

export interface RecalculateResult extends Omit<CharacterData, 'nickname' | 'avatar_settings' | 'xp_to_next_level' | 'achievement_count'> {
  newly_unlocked: { id: string; name: string; rarity: string; xp_reward: number }[]
}

export interface WeeklyCardData {
  nickname: string
  level: number
  rank: string
  week_start: string
  stats: {
    total_trades: number
    wins: number
    losses: number
    win_rate: number
    total_pnl: number
  }
  attributes: CharacterData['attributes']
}

export type CharacterCardData = CharacterData & {
  recent_achievements: Pick<AchievementData, 'id' | 'name' | 'icon' | 'rarity'>[]
}

export async function getCharacter(): Promise<CharacterData> {
  return fetchAPI('/character')
}

export async function recalculateCharacter(): Promise<RecalculateResult> {
  return fetchAPI('/character/recalculate', { method: 'POST' })
}

export async function getAchievements(category?: string): Promise<{ achievements: AchievementData[] }> {
  const params = category ? `?category=${category}` : ''
  return fetchAPI(`/achievements${params}`)
}

export async function getQuests(): Promise<{ active: QuestData[]; available: QuestData[]; completed: QuestData[] }> {
  return fetchAPI('/quests')
}

export async function startQuest(questId: string) {
  return fetchAPI(`/quests/${questId}/start`, { method: 'POST' })
}

export async function getQuestProgress(questId: string) {
  return fetchAPI(`/quests/${questId}/progress`)
}

export async function getLeaderboard(period: string = 'weekly'): Promise<{ period: string; period_start: string; entries: LeaderboardEntry[] }> {
  return fetchAPI(`/leaderboard?period=${period}`)
}

export async function getCharacterCard(): Promise<CharacterCardData> {
  return fetchAPI('/card/character')
}

export async function getWeeklyCard(): Promise<WeeklyCardData> {
  return fetchAPI('/card/weekly')
}
