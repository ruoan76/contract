import type { ApprovalPendingItem, AppRole } from '@/types/models'
import { client } from './client'
import { loginAsRole } from './auth'

export const approvalsApi = {
  submit: (contractId: number, flowType = 'standard') =>
    client.post<{ flow_id: number }>('/api/v1/approvals/submit', {
      contract_id: contractId,
      flow_type: flowType,
    }),

  approve: (flowId: number, action = 'approve', comment = '', delegateTo?: number) =>
    client.post<unknown>(`/api/v1/approvals/${flowId}/approve`, {
      action,
      comment,
      ...(delegateTo ? { delegate_to: delegateTo } : {}),
    }),

  pending: () =>
    client.get<{ items?: ApprovalPendingItem[] }>('/api/v1/approvals/pending'),

  history: (flowId: number) =>
    client.get<{ total_steps?: number; steps?: unknown[] }>(
      `/api/v1/approvals/${flowId}/history`,
    ),

  approveAllStepsForContract: async (contractId: number, roles?: AppRole[]) => {
    const order: Array<AppRole | 'executive'> = roles || [
      'approver',
      'legal',
      'finance',
      'executive',
    ]
    for (const role of order) {
      if (role === 'executive') {
        await loginAsRole('executive')
      } else {
        await loginAsRole(role)
      }
      const pending = await approvalsApi.pending()
      const item = (pending.items || []).find((x) => x.contract_id === contractId)
      if (item) await approvalsApi.approve(item.flow_id, 'approve')
    }
  },
}
