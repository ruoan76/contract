/**
 * Centralized storage access module
 * Handles sessionStorage and localStorage with typed helpers
 */

// === Session Storage Keys ===
export const STORAGE_KEYS = {
  TOKEN: 'api_token',
  CURRENT_USER: 'api_current_user',
  ROLE: 'app_role',
  LAST_CONTRACT_ID: 'last_contract_id',
  LAST_FLOW_ID: 'last_flow_id',
  APPROVAL_VIEWED_IDS: 'approval_viewed_contract_ids',
} as const

// === Local Storage Keys ===
export const LOCAL_STORAGE_KEYS = {
  DRAFT: 'contract-draft',
} as const

// === Type Definitions ===
export interface StoredUser {
  id: number
  username: string
  real_name?: string
  role?: string
  department?: string
}

// === Token Helpers ===
export function getToken(): string {
  const raw = sessionStorage.getItem(STORAGE_KEYS.TOKEN)
  return raw ?? ''
}

export function setToken(token: string): void {
  sessionStorage.setItem(STORAGE_KEYS.TOKEN, token || '')
}

export function clearToken(): void {
  sessionStorage.removeItem(STORAGE_KEYS.TOKEN)
}

// === User Helpers ===
export function getUser(): StoredUser | null {
  const raw = sessionStorage.getItem(STORAGE_KEYS.CURRENT_USER)
  if (!raw) return null
  try {
    return JSON.parse(raw) as StoredUser
  } catch {
    return null
  }
}

export function setUser(user: StoredUser): void {
  sessionStorage.setItem(STORAGE_KEYS.CURRENT_USER, JSON.stringify(user))
}

export function clearUser(): void {
  sessionStorage.removeItem(STORAGE_KEYS.CURRENT_USER)
}

// === Role Helpers ===
export function getRole(): string | null {
  const raw = sessionStorage.getItem(STORAGE_KEYS.ROLE)
  return raw
}

export function setRole(role: string): void {
  sessionStorage.setItem(STORAGE_KEYS.ROLE, role)
}

export function clearRole(): void {
  sessionStorage.removeItem(STORAGE_KEYS.ROLE)
}

// === Last Contract ID Helpers ===
export function getLastContractId(): number | null {
  const raw = sessionStorage.getItem(STORAGE_KEYS.LAST_CONTRACT_ID)
  if (!raw) return null
  const id = Number(raw)
  return Number.isNaN(id) ? null : id
}

export function setLastContractId(id: number | null): void {
  if (id == null) {
    sessionStorage.removeItem(STORAGE_KEYS.LAST_CONTRACT_ID)
  } else {
    sessionStorage.setItem(STORAGE_KEYS.LAST_CONTRACT_ID, String(id))
  }
}

export function clearLastContractId(): void {
  sessionStorage.removeItem(STORAGE_KEYS.LAST_CONTRACT_ID)
}

// === Last Flow ID Helpers ===
export function getLastFlowId(): number | null {
  const raw = sessionStorage.getItem(STORAGE_KEYS.LAST_FLOW_ID)
  if (!raw) return null
  const id = Number(raw)
  return Number.isNaN(id) ? null : id
}

export function setLastFlowId(id: number | null): void {
  if (id == null) {
    sessionStorage.removeItem(STORAGE_KEYS.LAST_FLOW_ID)
  } else {
    sessionStorage.setItem(STORAGE_KEYS.LAST_FLOW_ID, String(id))
  }
}

export function clearLastFlowId(): void {
  sessionStorage.removeItem(STORAGE_KEYS.LAST_FLOW_ID)
}

// === Approval Viewed IDs Helpers ===
export function getApprovalViewedIds(): Set<number> {
  const raw = sessionStorage.getItem(STORAGE_KEYS.APPROVAL_VIEWED_IDS)
  if (!raw) return new Set()
  try {
    const arr = JSON.parse(raw) as number[]
    return new Set(arr.filter((n) => typeof n === 'number'))
  } catch {
    return new Set()
  }
}

export function setApprovalViewedIds(ids: Set<number>): void {
  sessionStorage.setItem(STORAGE_KEYS.APPROVAL_VIEWED_IDS, JSON.stringify([...ids]))
}

// === Draft Helpers (localStorage) ===
export interface DraftData {
  title?: string
  contract_type?: string
  counterparty_name?: string
  amount?: number
  content?: string
  mode?: string
}

export function getDraft(): DraftData | null {
  const raw = localStorage.getItem(LOCAL_STORAGE_KEYS.DRAFT)
  if (!raw) return null
  try {
    return JSON.parse(raw) as DraftData
  } catch {
    return null
  }
}

export function saveDraft(draft: DraftData): void {
  localStorage.setItem(LOCAL_STORAGE_KEYS.DRAFT, JSON.stringify(draft))
}

export function clearDraft(): void {
  localStorage.removeItem(LOCAL_STORAGE_KEYS.DRAFT)
}
