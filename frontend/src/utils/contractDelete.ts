import type { AppRole, Contract } from '@/types/models'

/** 草稿是否可由当前用户删除（含退回修订后的 draft） */
export function canDeleteContract(
  contract: Contract | null,
  userId: number | undefined,
  role: AppRole,
): boolean {
  if (!contract || contract.status !== 'draft') return false
  if (role === 'admin') return true
  return userId != null && contract.creator_id === userId
}

export const DELETE_DRAFT_CONFIRM_TITLE = '确认删除草稿？'
export const DELETE_DRAFT_CONFIRM_MESSAGE =
  '删除后不可恢复。仅适用于录入错误或放弃本合同，流程启动后的合同无法删除。'
