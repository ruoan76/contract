import type { AppRole } from '@/types/models'

const VALID_ROLES: AppRole[] = [
  'drafter',
  'approver',
  'legal',
  'finance',
  'executive',
  'archivist',
  'admin',
]

/** 将后端 roles.code 解析为前端 AppRole */
export function parseAppRole(code?: string | null): AppRole | null {
  if (!code) return null
  const normalized = code.toLowerCase() as AppRole
  return VALID_ROLES.includes(normalized) ? normalized : null
}
